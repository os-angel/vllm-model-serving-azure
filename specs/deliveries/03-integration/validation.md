# 03 — Integración: validación

**Estado:** GRUPOS 1 Y 2 IMPLEMENTADOS Y VALIDADOS LOCALMENTE. Entrega 03 abierta; publicación/despliegue y Grupo 3 pendientes.

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
| INT-07 | Scheduling CPU, recursos, probes y acceso interno. | PARCIAL: Deployment/Service CPU con probes y recursos explícitos, dos esquemas válidos. Scheduling/Ready/port-forward GKE pendientes. |
| INT-08 | Cliente SDK independiente: chat y streaming. | PENDIENTE: ejecutar protocolo específico 03. |
| INT-09 | Logs sin contenido, texto seguro e historial efímero. | PARCIAL: pruebas confirman texto HTML inerte, almacenamiento del navegador vacío y errores sin eco de contenido. Código no registra prompts/respuestas/excepciones; auditoría de logs del pod pendiente. |
| INT-10 | Build reproducible, versiones/digest e instrucciones. | PARCIAL: Dockerfile por digest, uv.lock y build linux/amd64 observados; runtime no root/solo lectura probado. Digest de Artifact Registry y despliegue pendientes. |
| INT-11 | Revisión de recursos/costo y evidencia de limpieza. | PARCIAL: propuesta concreta de registry/IAM/manifiestos, costo con fuentes y limpieza en group-2.md. Plan real y revisión antes de apply, recursos cloud y cierre final pendientes. |

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

## Evidencia del Grupo 2

- Autorización recibida: iniciar Grupo 2. Releídos requisitos, plan y validación antes de implementación; diseño registrado en requirements/tech antes de crear Dockerfile, manifiestos y Terraform opcional. Archivos ajenos conservados.
- Docker Desktop estaba detenido: consulta inicial dentro del sandbox falló por permisos; consulta autorizada confirmó motor detenido. Se inició con `docker desktop start --timeout 60`; no son recursos GCP. Motor local permanece disponible y la imagen queda conservada para publicación.
- Bases verificadas mediante `docker buildx imagetools inspect`: Python índice `sha256:5024f48ba9441d4b13a95d3945abc6365538e3a31109833367a1923523c6efed`, amd64 `sha256:88310c082760d93ac7c74d579e95e53a4ab6ea52dd8901abc61a103daf488ac4`, versión observada 3.13.16; uv 0.11.7 índice `sha256:240fb85ab0f263ef12f492d8476aa3a2e4e1e333f7d67fbdd923d00a506a516a`.
- Build: `docker buildx build --platform linux/amd64 --load --tag nemotron-chat:group2 --metadata-file .local/integration-validation/image-build.json app` → exit 0. Contexto transmitido 126.85 kB; entorno runtime instalado con 20 dependencias desde lock, sin paquetes dev. Digest local de índice OCI `sha256:0ae8a46e4259382af207673e946b52695709ba75693a8278f922c606ab22ebdd`; manifest amd64 `sha256:29d4b092755a4fd67a5a2a562554ce69f59ef7e817aca86c2b437454e1b2d4e0`. **No son evidencia de publicación en Artifact Registry.**
- `uv run --no-project python scripts/validate-chat-image.py --image nemotron-chat:group2` → exit 0. Docker informó Size 52,169,163 bytes. Prueba con 0.5 CPU/512Mi, UID 10001, raíz read-only, capacidades retiradas y no-new-privileges: health backend, HTML/JS y estado offline aprobados; petición con marcador controlado devuelve error SSE sin done y no aparece en logs. Escritura en `/app` falla; `/tmp` escribible. Sin pytest, Playwright, uv ni tests dentro del runtime. No prueba límites bajo carga sostenida.
- Reporte privado `.local/integration-validation/image-smoke.json`; `test_container_removed=true`. `docker ps --filter ancestor=nemotron-chat:group2` no devolvió contenedores activos después de la prueba.
- Render para esquema local usando digest **local, no publicado**, en `.local/integration-validation/chat-schema-only.yaml`. No usar ese archivo para aplicar. Kubeconform 0.7.0 por índice `sha256:85dbef6b4b312b99133decc9c6fc9495e9fc5f92293d4ff3b7e1b30f5611823c`, `-strict -summary -kubernetes-version 1.35.0` → **2 recursos, 2 válidos, 0 inválidos, 0 errores, 0 omitidos**, exit 0. Deployment y Service pasan esquema; no es admisión server-side ni scheduling real.
- `terraform fmt -check` → exit 0 después de formatear el nuevo archivo. `terraform validate -no-color` → `Success! The configuration is valid.`, exit 0 con provider Google 7.46.1; primera ejecución sandbox falló al iniciar plugin y se repitió autorizada. No se ejecutó plan ni apply; registry deshabilitado por defecto.
- `uv run --no-project python -m unittest discover -s scripts -p 'test_*.py'` → **8 tests, OK**, exit 0; incluye seis pruebas previas y dos del renderer con subcasos de tags/repository/placeholder/inyección. No se repitieron las 24 pruebas del Grupo 1 porque no cambió backend/chat.
- Plan revisable [group-2.md](group-2.md): API/repository/Reader opcionales, publicación local, acceso interno y limpieza. Costo de referencia USD 0.000136986/GiB-h; ejemplo presupuestado 0.25 GiB, ~USD 0.025/mes sin asumir franquicia. Tarifa consultada en [Artifact Registry](https://cloud.google.com/artifact-registry/pricing); no hay consumo remoto medido.

No se hizo push, no se creó registry, no se concedió IAM y no se aplicaron manifiestos. Capacidad libre CPU, permisos efectivos de publicación/pull, plan Terraform real, digest remoto y API/chat en GKE quedan pendientes. El cierre de infraestructura heredada continúa pendiente de INF-10 durante la sesión continua autorizada; no se atribuye limpieza cloud al retiro del contenedor local.
