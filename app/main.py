"""Local chat backend. Only the configured vLLM endpoint receives messages."""

import asyncio
import json
import math
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI, APIConnectionError, APIStatusError, APITimeoutError
from pydantic import BaseModel, ConfigDict, Field, model_validator

MODEL = "nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8"
CONTEXT = 4096
STATIC = Path(__file__).parent / "static"


class TrackedStream(httpx.AsyncByteStream):
    """Observe the upstream SSE terminator without buffering the response."""

    def __init__(self, inner, response):
        self.inner = inner
        self.response = response

    async def __aiter__(self):
        tail = b"\n"
        async for part in self.inner:
            window = tail + part
            if re.search(rb"(?:\r?\n)data: *\[DONE\]\r?\n", window):
                self.response.extensions["sse_done"] = True
            tail = window[-32:]
            yield part

    async def aclose(self):
        await self.inner.aclose()


async def track_sse(response):
    if "text/event-stream" in response.headers.get("content-type", ""):
        response.extensions["sse_done"] = False
        response.stream = TrackedStream(response.stream, response)


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=16384)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    messages: list[Message] = Field(min_length=1, max_length=101)
    temperature: float = Field(default=0.6, ge=0, le=2, allow_inf_nan=False)
    max_tokens: int = Field(default=1024, ge=1, le=2048, strict=True)
    reasoning: Literal["no_think", "think"] = "no_think"

    @model_validator(mode="after")
    def ordered_conversation(self):
        if len(self.messages) % 2 != 1:
            raise ValueError("La conversación debe terminar con una pregunta.")
        for index, message in enumerate(self.messages):
            if message.role != ("user" if index % 2 == 0 else "assistant"):
                raise ValueError("El historial debe alternar usuario y asistente.")
            if not message.content.strip():
                raise ValueError("Los mensajes no pueden estar vacíos.")
        return self


def estimate(messages):
    return sum(math.ceil(len(message["content"]) / 4) + 8 for message in messages)


def prepare(payload: ChatRequest):
    system = {"role": "system", "content": f"/{payload.reasoning}\nResponde en español."}
    history = [message.model_dump() for message in payload.messages]
    removed = 0
    while estimate([system, *history]) + payload.max_tokens > CONTEXT:
        if len(history) == 1:
            raise HTTPException(422, "La pregunta y la salida reservada exceden el presupuesto estimado de 4096 tokens. Reduce la pregunta o max_tokens.")
        history = history[2:]
        removed += 1
    return [system, *history], removed


def error_message(exc):
    # Never relay exception strings: upstream errors can contain prompts or secrets.
    if isinstance(exc, (APITimeoutError, TimeoutError)):
        return "El servicio agotó el tiempo de espera. Puedes reintentar manualmente."
    if isinstance(exc, APIStatusError) and exc.status_code == 400:
        return "vLLM rechazó la petición; el contexto real puede superar la estimación. Reduce el historial o max_tokens."
    return "El servicio de inferencia no está disponible o devolvió un error. Puedes reintentar manualmente."


def event(kind, **data):
    return "data: " + json.dumps({"type": kind, **data}, ensure_ascii=False) + "\n\n"


def create_app(client=None, health_client=None):
    base_url = os.getenv("VLLM_BASE_URL", "http://vllm:8000/v1").rstrip("/")
    model = os.getenv("VLLM_MODEL", MODEL)
    timeout = float(os.getenv("VLLM_TIMEOUT_SECONDS", "120"))
    total_timeout = float(os.getenv("CHAT_TIMEOUT_SECONDS", "300"))
    if timeout <= 0 or total_timeout <= 0:
        raise ValueError("Los tiempos de espera deben ser positivos.")

    @asynccontextmanager
    async def lifespan(app):
        app.state.sdk = client or AsyncOpenAI(
            base_url=base_url, api_key=os.getenv("VLLM_API_KEY", "unused"),
            timeout=timeout, max_retries=0,
            http_client=httpx.AsyncClient(event_hooks={"response": [track_sse]}, trust_env=False),
        )
        app.state.health = health_client or httpx.AsyncClient(timeout=5, trust_env=False)
        try:
            yield
        finally:
            if client is None:
                await app.state.sdk.close()
            if health_client is None:
                await app.state.health.aclose()

    app = FastAPI(title="Nemotron Chat", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # FastAPI's default error response includes the invalid input content.
        return JSONResponse(status_code=422, content={"detail": "Petición inválida: revisa el historial, temperature (0–2) y max_tokens (1–2048)."})

    @app.get("/")
    async def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/health")
    async def health():
        return {"backend": "available"}

    @app.get("/api/status")
    async def status():
        available = False
        try:
            response = await app.state.health.get(base_url.removesuffix("/v1") + "/health")
            available = response.status_code == 200
        except httpx.HTTPError:
            pass
        return {"backend": "available", "serving": "available" if available else "unavailable", "model": model, "context": CONTEXT}

    @app.post("/api/chat")
    async def chat(payload: ChatRequest, request: Request):
        messages, removed = prepare(payload)

        async def generate():
            stream = None
            finish = None
            content = False
            yield event("meta", removed_turns=removed, estimated_prompt_tokens=estimate(messages), context=CONTEXT)
            try:
                async with asyncio.timeout(total_timeout):
                    stream = await app.state.sdk.chat.completions.create(
                        model=model, messages=messages, temperature=payload.temperature,
                        max_tokens=payload.max_tokens, stream=True,
                    )
                    async for chunk in stream:
                        if await request.is_disconnected():
                            return
                        if not chunk.choices:
                            continue
                        choice = chunk.choices[0]
                        if choice.delta.content:
                            content = content or bool(choice.delta.content.strip())
                            yield event("delta", content=choice.delta.content)
                        if choice.finish_reason:
                            finish = choice.finish_reason
                    if finish == "stop" and content and stream.response.extensions.get("sse_done"):
                        yield event("done", finish_reason=finish)
                    elif finish == "length":
                        yield event("error", code="truncated", message="Respuesta truncada por max_tokens. No se añadió al historial; aumenta el límite o acorta la pregunta.")
                    else:
                        yield event("error", code="incomplete", message="La respuesta está vacía o el stream terminó sin finalización normal. Puedes reintentar manualmente.")
            except (APITimeoutError, APIConnectionError, APIStatusError, TimeoutError) as exc:
                yield event("error", code="upstream", message=error_message(exc))
            except Exception:
                yield event("error", code="stream", message="El stream se interrumpió. Puedes reintentar manualmente.")
            finally:
                if stream is not None:
                    try:
                        await stream.close()
                    except Exception:
                        pass  # Do not log an upstream exception containing request data.

        return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    return app


app = create_app()
