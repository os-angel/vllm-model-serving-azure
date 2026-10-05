# 03 — Integración: validación

**Estado:** GRUPO 1 IMPLEMENTADO Y VALIDADO LOCALMENTE. Entrega 03 abierta; Grupos 2 y 3 pendientes.

## Inicio

Se leyeron README, AGENTS, misión, diseño técnico, roadmap y especificaciones/evidencia de las entregas anteriores. No existía directorio de entrega 03. Rama observada: `02-serving`. Archivos ajenos sin seguimiento: `AGENTS.md`, `Aprendizajes.md`, `Diagrama.md`; conservados.

La evidencia de serving procede de fase 02; no se consultó nuevamente GCP ni se verificó disponibilidad actual. No se crearon recursos cloud, no se ejecutó apply y no se cerró la sesión continua del laboratorio.

## Matriz

Decisión recibida del propietario: backend FastAPI, priorizando facilidad de prueba. Esta aprobación de tecnología no equivale a aprobación completa del borrador ni a evidencia funcional.

| ID | Comprobación prevista | Resultado y evidencia |
|---|---|---|
| INT-01 | DNS interno, SDK backend y respuesta real. | PARCIAL: SDK real probado con transporte HTTP controlado; DNS/pod/respuesta de Nemotron pendientes Grupo 3. |
| INT-02 | Payload de varios turnos y reinicio de conversación. | PASS LOCAL: navegador envía user/assistant/user en orden; nueva conversación y recarga borran historial. GKE pendiente. |
| INT-03 | Fragmentos visibles y estados de cierre/truncamiento. | PASS LOCAL: primer fragmento visible antes de completar; stop, length, salida vacía y falta de DONE diferenciados. GKE pendiente. |
| INT-04 | Salud separada, timeout, desconexión y reintento. | PASS LOCAL: backend disponible con serving 503; timeout, 400/500, cancelación y reintento manual comprobados; sin duplicación ni retry SDK. GKE pendiente. |
| INT-05 | Validación de controles y parámetros enviados. | PASS LOCAL: controles y payload SDK verificados; rangos inválidos y max_tokens fraccionario rechazados sin invocar serving. |
| INT-06 | Estimación de caracteres, fronteras y retiro de turnos completos. | PASS LOCAL contra decisión aprobada: frontera estimada 4096, exceso de un carácter, retiro de pares y aviso visible. No acredita conteo real del tokenizer. |
| INT-07 | Scheduling CPU, recursos, probes y acceso interno. | PENDIENTE: manifiestos y autorización de despliegue. |
| INT-08 | Cliente SDK independiente: chat y streaming. | PENDIENTE: ejecutar protocolo específico 03. |
| INT-09 | Logs sin contenido, texto seguro e historial efímero. | PARCIAL: pruebas confirman texto HTML inerte, almacenamiento del navegador vacío y errores sin eco de contenido. Código no registra prompts/respuestas/excepciones; auditoría de logs del pod pendiente. |
| INT-10 | Build reproducible, versiones/digest e instrucciones. | PARCIAL: pyproject y uv.lock, ejecución local e instrucciones disponibles. Dockerfile/build OCI/digest pendientes Grupo 2. |
| INT-11 | Revisión de recursos/costo y evidencia de limpieza. | PENDIENTE: plan concreto de despliegue y cierre final. |

Para cada ejecución registrar fecha/hora, tarea, comando o procedimiento, resultado observado, ubicación de evidencia y límites. Pruebas simuladas no acreditan integración real. Crear estos documentos no acredita ningún requisito funcional.

## Aprobación del plan

El propietario aprobó fase 03, FastAPI en CPU, estimación aproximada de cuatro caracteres por token y límite 4096, rama `03-integration` y commit de especificaciones antes del Grupo 1. No autoriza despliegue facturable todavía. Se conserva como límite que el presupuesto estimado puede diferir del tokenizer real.

## Evidencia del Grupo 1

- Rama creada: `03-integration`; commit de especificaciones anterior al código: `d1a4da4` (`docs(integration): approve phase 03 specifications`). Archivos ajenos conservados sin seguimiento.
- `uv sync` y `uv add --dev playwright==1.55.0` completados. Python observado 3.13.2; FastAPI 0.115.12, SDK OpenAI 1.109.1, HTTPX 0.28.1, Uvicorn 0.35.0; dependencias transitivas en `app/uv.lock`.
- Ejecución final desde `app/`: `uv run pytest -q` → **24 passed, 1 warning in 10.30s**, exit 0. Incluye 21 casos de backend y 3 de navegador con Chromium local ya instalado; sin descargar otro navegador.
- Warning observado: alias `anyio.abc.BlockingPortal` deprecado en Starlette TestClient. No impidió las pruebas; no representa un fallo de serving.
- `node --check app/static/chat.js` → exit 0. `git diff --check` → exit 0; revisión de archivos nuevos complementada por las pruebas.
- `app/tests/test_chat.py`: SDK real frente a MockTransport HTTP, payload/configuración, SSE, truncamiento, stream incompleto/falta de DONE, timeout, errores 400/500, validación y fronteras estimadas de contexto.
- `app/tests/test_browser.py`: servidor HTTP local y Chromium; stream con pausas controladas demuestra fragmento visible mientras Enviar sigue deshabilitado; historial de varios turnos, parámetros, texto HTML inerte, nueva conversación, recarga, reintento sin duplicación, cancelación y aviso de recorte. Tamaños 1000×900 y 390×844, sin desbordamiento horizontal móvil.
- Capturas privadas, revisadas visualmente: `.local/integration-validation/chat-desktop.png` y `chat-mobile.png`. El contenido y estado del modelo en esas capturas son simulados por el endpoint controlado; no corresponden a una respuesta de Nemotron.

No se consultó ni modificó GCP/GKE durante Grupo 1; no hay nuevos recursos facturables. Los servidores de pruebas fueron detenidos por el fixture. No se cambió vLLM ni se corrigieron sus fallos de calidad. DNS interno, colocación CPU, logs de pod y respuestas reales siguen pendientes. La infraestructura heredada conserva el cierre final pendiente de INF-10 durante la sesión continua autorizada.
