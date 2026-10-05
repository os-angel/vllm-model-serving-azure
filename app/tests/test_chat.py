import json

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from openai import AsyncOpenAI

from main import ChatRequest, create_app, estimate, prepare, track_sse


def chunk(text=None, finish=None):
    return {"id": "test", "object": "chat.completion.chunk", "created": 0,
            "model": "test", "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": finish}]}


class Harness:
    def __init__(self, mode="stop", health=200):
        self.calls = []
        self.mode = mode
        self.health = health
        self.sdk_http = httpx.AsyncClient(transport=httpx.MockTransport(self.upstream), event_hooks={"response": [track_sse]})
        self.health_http = httpx.AsyncClient(transport=httpx.MockTransport(self.upstream))
        self.sdk = AsyncOpenAI(base_url="http://controlled/v1", api_key="unused",
                               http_client=self.sdk_http, max_retries=0)
        self.app = create_app(self.sdk, self.health_http)

    def upstream(self, request):
        if request.url.path.endswith("/health"):
            return httpx.Response(self.health)
        self.calls.append(json.loads(request.content))
        if self.mode == "timeout":
            raise httpx.ReadTimeout("private prompt must never appear", request=request)
        if self.mode == "400":
            return httpx.Response(400, json={"error": {"message": "private prompt must never appear"}})
        if self.mode == "500":
            return httpx.Response(500, json={"error": {"message": "private prompt must never appear"}})
        chunks = [chunk("Hola "), chunk("mundo")]
        if self.mode == "empty":
            chunks = []
        if self.mode != "incomplete":
            chunks.append(chunk(finish="length" if self.mode == "length" else "stop"))
        body = "".join("data: " + json.dumps(c) + "\n\n" for c in chunks)
        return httpx.Response(200, stream=httpx.ByteStream((body + ("" if self.mode == "missing_done" else "data: [DONE]\n\n")).encode()), headers={"Content-Type": "text/event-stream"})


def events(response):
    return [json.loads(frame[6:]) for frame in response.text.split("\n\n") if frame.startswith("data: ")]


def payload(**options):
    return {"messages": [{"role": "user", "content": "Hola"}], **options}


def test_real_sdk_payload_and_stream():
    h = Harness()
    with TestClient(h.app) as client:
        response = client.post("/api/chat", json=payload(temperature=0.4, max_tokens=300, reasoning="think"))
    data = events(response)
    assert [e["type"] for e in data] == ["meta", "delta", "delta", "done"]
    assert "".join(e["content"] for e in data if e["type"] == "delta") == "Hola mundo"
    assert h.calls == [{"messages": [{"role": "system", "content": "/think\nResponde en español."}, {"role": "user", "content": "Hola"}],
                        "model": "nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8", "temperature": 0.4, "max_tokens": 300, "stream": True}]


@pytest.mark.parametrize("mode,code", [("length", "truncated"), ("incomplete", "incomplete"), ("missing_done", "incomplete"), ("empty", "incomplete"), ("timeout", "upstream"), ("400", "upstream"), ("500", "upstream")])
def test_failures_never_claim_success_or_leak(mode, code):
    h = Harness(mode)
    with TestClient(h.app) as client:
        response = client.post("/api/chat", json=payload())
    data = events(response)
    assert data[-1]["type"] == "error" and data[-1]["code"] == code
    assert not any(e["type"] == "done" for e in data)
    assert "private prompt" not in response.text
    assert len(h.calls) == 1  # SDK retries disabled even for 500/timeouts.


@pytest.mark.parametrize("options", [{"temperature": 2.1}, {"temperature": -1}, {"max_tokens": 0}, {"max_tokens": 2049}, {"max_tokens": 1.5}, {"reasoning": "other"}, {"messages": []}, {"messages": [{"role": "system", "content": "private input"}]}, {"messages": [{"role": "user", "content": " "}]}])
def test_invalid_request_does_not_call_upstream(options):
    h = Harness()
    with TestClient(h.app) as client:
        response = client.post("/api/chat", json=payload(**options))
    assert response.status_code == 422
    assert "private input" not in response.text
    assert h.calls == []


def test_budget_boundary_and_oversized_last_turn():
    system = {"role": "system", "content": "/no_think\nResponde en español."}
    max_tokens = 1024
    characters = (4096 - max_tokens - estimate([system]) - 8) * 4
    request = ChatRequest(**payload(messages=[{"role": "user", "content": "x" * characters}]))
    messages, removed = prepare(request)
    assert removed == 0 and estimate(messages) + max_tokens == 4096
    request.messages[0].content += "x"
    with pytest.raises(HTTPException) as exc:
        prepare(request)
    assert exc.value.status_code == 422


def test_history_prunes_whole_turns_and_preserves_order():
    h = Harness()
    history = [{"role": "user", "content": "x" * 8000}, {"role": "assistant", "content": "y" * 8000},
               {"role": "user", "content": "Primer turno"}, {"role": "assistant", "content": "Respuesta"},
               {"role": "user", "content": "Segunda pregunta"}]
    with TestClient(h.app) as client:
        response = client.post("/api/chat", json=payload(messages=history))
    assert events(response)[0]["removed_turns"] == 1
    assert h.calls[0]["messages"][1:] == history[2:]


@pytest.mark.parametrize("health,expected", [(200, "available"), (503, "unavailable")])
def test_status_separates_backend_and_serving(health, expected):
    h = Harness(health=health)
    with TestClient(h.app) as client:
        assert client.get("/health").json() == {"backend": "available"}
        assert client.get("/api/status").json()["serving"] == expected
        assert client.get("/").status_code == 200
        assert client.get("/static/chat.js").status_code == 200
