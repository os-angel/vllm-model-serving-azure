"""Explicit live checks; run with uv from app's locked environment.

Writes request/response evidence only to a Git-ignored .local directory.
Does not provision, mutate Kubernetes, or claim model quality.
"""

import argparse
import json
import os
import time
from pathlib import Path

import httpx
from openai import OpenAI
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-url", default="http://127.0.0.1:8080")
    parser.add_argument("--vllm-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--output", required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--context-only", action="store_true")
    args = parser.parse_args()
    out = Path(args.output).resolve()
    root = Path(__file__).resolve().parents[1]
    if not out.is_relative_to(root / ".local"):
        parser.error("Evidence must be under this repository's .local directory")
    out.mkdir(parents=True, exist_ok=True)
    report = {}

    def save(name, data):
        (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def check(name, action):
        try:
            detail = action()
            report[name] = {"result": "PASS", "evidence": detail}
        except Exception as exc:
            # Exception strings may contain content; don't print them.
            report[name] = {"result": "FAIL", "exception_type": type(exc).__name__}
        save("results.json", report)
        print(name, report[name]["result"], flush=True)

    with httpx.Client(timeout=310, trust_env=False) as http:
        def health():
            state = http.get(args.app_url + "/api/status").json()
            save("status.json", state)
            assert http.get(args.app_url + "/health").json() == {"backend": "available"}
            assert state["serving"] == ("unavailable" if args.offline else "available")
            return state
        check("health_separation", health)
        if report["health_separation"]["result"] != "PASS":
            return 2  # Do not submit inference while serving readiness is unverified.

        def boundaries():
            base = {"messages": [{"role": "user", "content": "x" * 16300}], "max_tokens": 2048}
            response = http.post(args.app_url + "/api/chat", json=base)
            assert response.status_code == 422
            for field, value in [("temperature", 2.1), ("max_tokens", 0), ("max_tokens", 1.5)]:
                payload = {"messages": [{"role": "user", "content": "Hola"}], field: value}
                assert http.post(args.app_url + "/api/chat", json=payload).status_code == 422
            return {"oversized_question": 422, "invalid_parameters": [422, 422, 422]}
        check("backend_rejection", boundaries)

        if not args.offline:
            def context_budget():
                # /no_think instructions: 16 estimated tokens; user overhead: 8.
                # 16284 chars / 4 + 16 + 8 + one output token = 4096.
                payload = {"messages": [{"role": "user", "content": "x" * 16284}], "max_tokens": 1}
                response = http.post(args.app_url + "/api/chat", json=payload)
                save("context-boundary.json", {"status": response.status_code, "sse": response.text})
                assert response.status_code == 200
                frames = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
                assert frames[0]["estimated_prompt_tokens"] + 1 == 4096
                payload["messages"][0]["content"] += "x"
                assert http.post(args.app_url + "/api/chat", json=payload).status_code == 422
                payload = {"messages": [{"role": "user", "content": "x" * 8300},
                                        {"role": "assistant", "content": "y" * 8300},
                                        {"role": "user", "content": "Hola"}], "max_tokens": 1}
                response = http.post(args.app_url + "/api/chat", json=payload)
                save("context-pruning.json", {"status": response.status_code, "sse": response.text})
                frames = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
                assert frames[0]["removed_turns"] == 1
                return {"estimated_boundary": 4096, "one_character_over": 422, "complete_pair_removed": 1,
                        "synthetic_history": True, "exact_tokenizer_count": False}
            check("deployed_context_budget", context_budget)

    if args.context_only:
        return 1 if any(value["result"] == "FAIL" for value in report.values()) else 0

    if not args.offline:
        sdk = OpenAI(base_url=args.vllm_url, api_key="unused", max_retries=0, timeout=180)
        request = {"model": "nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8",
                   "messages": [{"role": "system", "content": "/think\nResponde en español."},
                                {"role": "user", "content": "¿Cuál es la capital de Francia? Responde brevemente."}],
                   "temperature": 0, "max_tokens": 2048}
        save("sdk-request.json", request)

        def sdk_chat():
            response = sdk.chat.completions.create(**request)
            save("sdk-chat.json", response.model_dump())
            assert response.model == request["model"]
            assert response.choices[0].message.content.strip()
            assert response.choices[0].finish_reason == "stop"
            return {"finish_reason": "stop", "nonempty": True, "model": response.model}
        check("independent_sdk_chat", sdk_chat)

        def sdk_stream():
            start = time.monotonic()
            chunks = []
            with sdk.chat.completions.create(**request, stream=True) as stream:
                for chunk in stream:
                    chunks.append({"elapsed": time.monotonic() - start, "chunk": chunk.model_dump()})
            save("sdk-stream.json", chunks)
            text = "".join(c["chunk"]["choices"][0]["delta"].get("content") or "" for c in chunks if c["chunk"]["choices"])
            finishes = [c["chunk"]["choices"][0]["finish_reason"] for c in chunks if c["chunk"]["choices"] and c["chunk"]["choices"][0]["finish_reason"]]
            assert text.strip() and finishes == ["stop"]
            return {"chunks": len(chunks), "nonempty": True, "finish_reason": finishes[-1]}
        check("independent_sdk_stream", sdk_stream)
        sdk.close()

    with sync_playwright() as playwright:
        cached = list((Path.home() / "Library/Caches/ms-playwright").glob("chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        executable = os.getenv("CHAT_BROWSER_PATH") or (str(cached[-1]) if cached else None)
        browser = playwright.chromium.launch(executable_path=executable, headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 900})
        page.set_default_timeout(310000)
        payloads = []
        page.on("request", lambda req: payloads.append(req.post_data_json) if req.url.endswith("/api/chat") and req.method == "POST" else None)
        page.goto(args.app_url)

        def send(question):
            page.locator("#prompt").fill(question)
            page.locator("#send").click()

        def finish():
            page.wait_for_function("!document.querySelector('#send').disabled")

        if args.offline:
            def offline():
                page.wait_for_function("document.querySelector('#service').textContent.includes('Modelo no disponible')")
                send("Prueba de indisponibilidad controlada")
                finish()
                assert page.locator("#error").inner_text()
                assert page.locator("#retry").is_visible()
                assert len(payloads) == 1
                page.wait_for_timeout(1500)
                assert len(payloads) == 1
                page.locator("#retry").click()
                finish()
                assert len(payloads) == 2 and payloads[0] == payloads[1]
                assert page.locator(".user").count() == 1
                return {"automatic_retries": 0, "manual_retry": True, "no_duplicate_turn": True}
            check("offline_browser_retry", offline)
        else:
            def conversation():
                page.wait_for_function("document.querySelector('#service').textContent.includes('Modelo disponible')")
                page.locator("#temperature").fill("0")
                page.locator("#max-tokens").fill("2048")
                page.locator("#reasoning").select_option("think")
                send("¿Cuál es la capital de Francia? Responde brevemente.")
                page.wait_for_function("document.querySelector('.assistant p').textContent.length > 0")
                progressive = page.locator("#send").is_disabled()
                finish()
                first = page.locator(".assistant p").inner_text()
                save("browser-first.json", {"answer": first, "error": page.locator("#error").inner_text(), "progressive": progressive})
                assert progressive and not page.locator("#error").inner_text()
                send("¿De qué país estamos hablando? Responde brevemente.")
                finish()
                save("browser-payloads.json", payloads)
                assert len(payloads[-1]["messages"]) == 3
                assert [m["role"] for m in payloads[-1]["messages"]] == ["user", "assistant", "user"]
                assert payloads[-1]["messages"][1]["content"] == first
                assert payloads[-1]["temperature"] == 0 and payloads[-1]["max_tokens"] == 2048 and payloads[-1]["reasoning"] == "think"
                assert not page.locator("#error").inner_text()
                page.screenshot(path=str(out / "chat-real-desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=str(out / "chat-real-mobile.png"), full_page=True)
                page.locator("#reset").click()
                assert page.locator(".message").count() == 0
                return {"progressive": progressive, "ordered_history": True, "parameters": True, "reset": True}
            check("real_browser_conversation", conversation)

            def truncated():
                page.locator("#reset").click()
                page.locator("#max-tokens").fill("1")
                send("Explica Terraform en varias frases.")
                finish()
                assert "truncada" in page.locator("#error").inner_text()
                assert page.locator("#retry").is_visible()
                page.locator("#reset").click()
                return {"max_tokens": 1, "truncation_visible": True}
            check("real_truncation", truncated)

            def cancel():
                page.locator("#max-tokens").fill("2048")
                send("Explica detalladamente cómo funciona Kubernetes.")
                page.wait_for_function("document.querySelector('.assistant p').textContent.length > 0")
                page.locator("#cancel").click()
                finish()
                assert "cancelada" in page.locator("#error").inner_text()
                assert page.locator("#retry").is_visible()
                return {"partial_output": True, "cancel_visible": True}
            check("real_stream_cancel", cancel)

            def reload():
                page.reload()
                assert page.locator(".message").count() == 0
                assert page.evaluate("localStorage.length + sessionStorage.length") == 0
                return {"history_cleared": True, "browser_storage_empty": True}
            check("reload_ephemeral_history", reload)
        save("browser-payloads.json", payloads)
        browser.close()
    return 1 if any(value["result"] == "FAIL" for value in report.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
