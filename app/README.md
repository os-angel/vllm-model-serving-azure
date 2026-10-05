# Chat local — Grupo 1

Backend FastAPI y chat HTML/JavaScript. Desde `app/`:

```bash
uv sync
VLLM_BASE_URL=http://localhost:8000/v1 uv run uvicorn main:app --host 127.0.0.1 --port 8080 --no-access-log
```

Abrir `http://localhost:8080`. Para el servicio existente, ejecutar por separado el port-forward autorizado:

```bash
kubectl -n inference port-forward svc/vllm 8000:8000
```

Sin port-forward el chat abre y muestra modelo no disponible. La URL predeterminada del backend es `http://vllm:8000/v1` para el futuro pod CPU. `VLLM_MODEL` cambia el identificador; `VLLM_API_KEY` solo si el serving requiere autenticación. `unused` no aporta seguridad. `VLLM_TIMEOUT_SECONDS` (120) limita espera de red; `CHAT_TIMEOUT_SECONDS` (300) limita la solicitud completa. SDK sin reintentos automáticos.

El historial vive en memoria del navegador: recargar o nueva conversación lo borra. En cada solicitud se estima `ceil(caracteres/4) + 8` por mensaje, incluidas instrucciones; se reserva `max_tokens` y se retiran pares antiguos hasta encajar en 4096. No es conteo real: vLLM puede rechazar contexto. Solo respuestas no vacías con final `stop` pasan al historial. Respuestas truncadas/parciales permanecen visibles con error y se pueden reintentar manualmente. `/think` puede consumir el presupuesto antes de una respuesta final; la calidad tiene fallos heredados de fase 02.

Contrato local: `/health` comprueba backend; `/api/status` consulta salud de serving; `/api/chat` acepta historial alternado terminado en user y devuelve eventos SSE JSON `meta`, `delta`, `done` o `error`. No persiste prompts ni registra excepciones con contenido. Texto del modelo se dibuja con `textContent`.

```bash
uv run pytest
```

Las pruebas de navegador requieren Chromium de Playwright. Si no está instalado, ejecutar `uv run playwright install chromium`; también puede indicarse una instalación existente con `CHAT_BROWSER_PATH`. Las capturas de pruebas quedan ignoradas por Git en `.local/integration-validation/`.

Las pruebas locales usan un endpoint controlado; no acreditan GKE, calidad ni capacidad real. Manifiestos y empaquetado de imagen corresponden al Grupo 2. El cierre cloud sigue el orden Kubernetes/PVC y Terraform descrito en las especificaciones.

Referencias de implementación consultadas: [SDK Python de OpenAI](https://developers.openai.com/api/reference/python) y [StreamingResponse de FastAPI](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse). El backend utiliza Chat Completions contra vLLM, sin llamadas a OpenAI.
