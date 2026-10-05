"""Real browser + local HTTP server. No requests to GKE or paid inference."""

import asyncio
import json
import os
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from playwright.sync_api import sync_playwright

from test_chat import Harness, chunk


class DelayedSSE(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield ("data: " + json.dumps(chunk("Primer fragmento ")) + "\n\n").encode()
        await asyncio.sleep(1)
        yield ("data: " + json.dumps(chunk("<img src=x onerror=alert(1)>")) + "\n\n").encode()
        await asyncio.sleep(0.5)
        yield ("data: " + json.dumps(chunk(finish="stop")) + "\n\ndata: [DONE]\n\n").encode()


class BrowserHarness(Harness):
    def upstream(self, request):
        if self.mode == "slow" and request.url.path.endswith("/chat/completions"):
            self.calls.append(json.loads(request.content))
            return httpx.Response(200, stream=DelayedSSE(), headers={"Content-Type": "text/event-stream"})
        return super().upstream(request)


@pytest.fixture
def browser_page():
    h = BrowserHarness("slow")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(h.app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started
    try:
        with sync_playwright() as p:
            executable = os.getenv("CHAT_BROWSER_PATH")
            if executable is None:
                cached = list((Path.home() / "Library/Caches/ms-playwright").glob("chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
                executable = str(cached[-1]) if cached else None
            browser = p.chromium.launch(executable_path=executable, headless=True)
            page = browser.new_page(viewport={"width": 1000, "height": 900})
            page.goto(f"http://127.0.0.1:{port}")
            yield page, h
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


def send(page, question):
    page.locator("#prompt").fill(question)
    page.locator("#send").click()


def screenshot(page, name):
    directory = Path(__file__).resolve().parents[2] / ".local/integration-validation"
    directory.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(directory / name), full_page=True)


def test_progressive_history_parameters_and_safe_text(browser_page):
    page, h = browser_page
    page.wait_for_function("document.querySelector('#service').textContent.includes('Modelo disponible')")
    page.locator("#temperature").fill("0.4")
    page.locator("#max-tokens").fill("256")
    page.locator("#reasoning").select_option("think")
    send(page, "Primera pregunta")
    page.wait_for_function("document.querySelector('.assistant p').textContent === 'Primer fragmento '")
    assert page.locator("#send").is_disabled()  # First fragment arrives before completion.
    page.wait_for_function("!document.querySelector('#send').disabled")
    assert page.locator("#error").inner_text() == ""
    assert page.locator("#messages img").count() == 0
    assert "<img" in page.locator(".assistant p").inner_text()
    assert h.calls[0]["temperature"] == 0.4 and h.calls[0]["max_tokens"] == 256
    assert h.calls[0]["messages"][0]["content"].startswith("/think")
    h.mode = "stop"
    send(page, "Segunda pregunta")
    page.wait_for_function("!document.querySelector('#send').disabled")
    assert [m["role"] for m in h.calls[-1]["messages"]] == ["system", "user", "assistant", "user"]
    assert h.calls[-1]["messages"][1]["content"] == "Primera pregunta"
    screenshot(page, "chat-desktop.png")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    screenshot(page, "chat-mobile.png")
    page.locator("#reset").click()
    assert page.locator(".message").count() == 0
    send(page, "Nueva pregunta")
    page.wait_for_function("!document.querySelector('#send').disabled")
    assert len(h.calls[-1]["messages"]) == 2
    page.reload()
    assert page.locator(".message").count() == 0
    assert page.evaluate("localStorage.length + sessionStorage.length") == 0


def test_error_retry_truncation_and_cancel(browser_page):
    page, h = browser_page
    h.mode = "500"
    send(page, "Pregunta para reintentar")
    page.wait_for_function("!document.querySelector('#retry').hidden")
    assert "error" in page.locator("#error").inner_text()
    assert len(h.calls) == 1
    h.mode = "stop"
    page.locator("#retry").click()
    page.wait_for_function("!document.querySelector('#send').disabled")
    assert len(h.calls) == 2
    assert page.locator(".user").count() == 1
    assert page.locator(".assistant").count() == 1
    assert h.calls[0]["messages"] == h.calls[1]["messages"]
    h.mode = "length"
    send(page, "Respuesta larga")
    page.wait_for_function("!document.querySelector('#retry').hidden")
    assert "truncada" in page.locator("#error").inner_text()
    h.mode = "slow"
    page.locator("#retry").click()
    page.wait_for_function("document.querySelectorAll('.assistant p')[1].textContent === 'Primer fragmento '")
    page.locator("#cancel").click()
    page.wait_for_function("!document.querySelector('#send').disabled")
    assert "cancelada" in page.locator("#error").inner_text()
    h.mode = "stop"
    page.locator("#retry").click()
    page.wait_for_function("!document.querySelector('#send').disabled")
    assert len(h.calls[-1]["messages"]) == 4  # No partial/truncated turn stored.


def test_browser_shows_pruning_and_offline_status(browser_page):
    page, h = browser_page
    h.mode = "stop"
    send(page, "x" * 7000)
    page.wait_for_function("!document.querySelector('#send').disabled")
    send(page, "y" * 7000)
    page.wait_for_function("!document.querySelector('#send').disabled")
    assert "1 turnos" in page.locator("#notice").inner_text()
    assert page.locator(".user").count() == 1
    assert h.calls[-1]["messages"][1]["content"] == "y" * 7000
    h.health = 503
    page.reload()
    page.wait_for_function("document.querySelector('#service').textContent.includes('Modelo no disponible')")
