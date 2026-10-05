# 03 — Integración: validación

**Estado:** ENTREGA 03 CERRADA POR EL PROPIETARIO CON LIMITACIÓN ACEPTADA. Recuperación del serving tras interrupción/reintento fallida; resultado original conservado. Limpieza final autorizada y en ejecución.

## Inicio del Grupo 3 — preflight y revisión pendiente

El propietario solicitó continuar Grupo 3. Se releyeron contexto y requisitos; Git conserva sin cambios los archivos ajenos `AGENTS.md`, `Aprendizajes.md` y `Diagrama.md`. Se consultaron GKE/Artifact Registry y se generó el plan real, sin crear recursos ni publicar imágenes. Evidencia resumida y protocolo en [group-3.md](group-3.md).

- INT-07: nodo CPU Ready/amd64 y capacidad de requests suficiente para la propuesta; aplicación todavía no desplegada.
- INT-11: plan real **3 to add, 0 to change, 0 to destroy**, exclusivamente API Artifact Registry, repositorio e IAM Reader. Plan/log/JSON privados en `.local/terraform-state/phase03-registry*`, excluidos de Git. Costo reconfirmado con fuente oficial y presentado para revisión; aprobación de apply pendiente.
- Serving observado 1/1 Ready con Service ClusterIP. Esto no demuestra respuesta de inferencia en esta ejecución. INT-01/08 y pruebas de navegador reales siguen pendientes.
- Consultas iniciales fallaron por restricciones del sandbox y se repitieron con escalación autorizada. Lectura de plan JSON también requirió ejecución del provider fuera del sandbox; repetición exitosa. No son fallos del despliegue.
- No apply, push ni manifiestos aplicados. Sin recursos nuevos que limpiar; INF-10 y cierre heredado permanecen pendientes de la sesión continua.

## Inicio

Se leyeron README, AGENTS, misión, diseño técnico, roadmap y especificaciones/evidencia de las entregas anteriores. No existía directorio de entrega 03. Rama observada: `02-serving`. Archivos ajenos sin seguimiento: `AGENTS.md`, `Aprendizajes.md`, `Diagrama.md`; conservados.

La evidencia de serving procede de fase 02; no se consultó nuevamente GCP ni se verificó disponibilidad actual. No se crearon recursos cloud, no se ejecutó apply y no se cerró la sesión continua del laboratorio.

## Matriz

Decisión recibida del propietario: backend FastAPI, priorizando facilidad de prueba. Esta aprobación de tecnología no equivale a aprobación completa del borrador ni a evidencia funcional.

| ID | Comprobación prevista | Resultado y evidencia |
|---|---|---|
| INT-01 | DNS interno, SDK backend y respuesta real. | PASS OBSERVADO: backend configurado `http://vllm:8000/v1`, conversación real de dos turnos completada; modelo solicitado coincide con SDK independiente. No acredita disponibilidad sostenida. |
| INT-02 | Payload de varios turnos y reinicio de conversación. | PASS REAL: navegador envía user/assistant/user en orden, incluido contenido exacto del primer assistant; reset y recarga borran historial; petición posterior al reset sin historial anterior. Payloads privados en `group3-live/`. |
| INT-03 | Fragmentos visibles y estados de cierre/truncamiento. | PASS REAL: fragmento antes del cierre con Enviar deshabilitado; conversación stop, max_tokens=1 truncado, cancelación y desconexión inesperada con error visible, sin guardar éxito falso. Salida vacía/falta de DONE además probadas localmente. |
| INT-04 | Salud separada, timeout, desconexión y reintento. | PARCIAL REAL: backend Ready con URL de serving inválida; timeout controlado y reintento manual sin duplicación ni reenvío automático. FAIL de recuperación de inferencia tras desconexión/reintento: vLLM falla y reinicia automáticamente; el chat muestra error. Causa pendiente, no corregida fuera de alcance. |
| INT-05 | Validación de controles y parámetros enviados. | PASS REAL + LOCAL: navegador envía temperature=0, max_tokens=2048, reasoning=think; payload SDK independiente registrado. Backend rechaza 2.1/0/fraccionario con 422. Payload backend→SDK probado localmente; no se instrumentó el tráfico interno con contenido en logs. |
| INT-06 | Estimación de caracteres, fronteras y retiro de turnos completos. | PASS REAL contra decisión aprobada: meta 4095 + salida 1 = 4096, un carácter adicional → 422; par antiguo retirado completo, meta 25 y removed_turns=1. Aviso visible en navegador con historial sintético inyectado en la petición real. No acredita tokenizer exacto. |
| INT-07 | Scheduling CPU, recursos, probes y acceso interno. | PASS REAL: chat 1/1 Ready en CPU amd64, cero reinicios del pod final; requests/limits/probes previstos; Service ClusterIP 8080, port-forward funcional y diff final sin diferencias. |
| INT-08 | Cliente SDK independiente: chat y streaming. | PASS REAL: chat no vacío/modelo correcto/stop y streaming de 183 chunks/stop; `/think`, temperature=0, max_tokens=2048. No atribuye calidad general. |
| INT-09 | Logs sin contenido, texto seguro e historial efímero. | PASS EN MUESTRA: 28 entradas cloud de todos los pods del chat, sin marcadores de prompts/respuesta ni access logs; código sin contenido/Secret/token Kubernetes. JS desplegado idéntico al validado localmente con HTML inerte; recarga sin historial/storage. No es auditoría exhaustiva de seguridad ni de logs de vLLM. |
| INT-10 | Build reproducible, versiones/digest e instrucciones. | PASS REAL: reconstrucción amd64/smoke, push y digest remoto confirmado, Deployment por digest; lock/bases fijados e instrucciones reproducibles. |
| INT-11 | Revisión de recursos/costo y evidencia de limpieza. | PARCIAL: aprobación explícita antes de apply, tres recursos creados sin modificar infraestructura heredada; limpieza documentada y manifiesto restaurado. Cierre cloud/registry/PVC/Terraform no ejecutado aún en sesión continua. |

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

## Evidencia del Grupo 3 — ejecución aprobada

El propietario aprobó aplicar el plan de tres recursos, publicar imagen y desplegar chat con «si, demosle». Esta aprobación llegó después de presentar recursos/costo. Se usó `uv` para toda ejecución Python. No se modificaron archivos ajenos.

- Terraform apply del plan revisado → **3 added, 0 changed, 0 destroyed**: API Artifact Registry, repositorio `nemotron-lab-apps` y Reader de nodos. Plan/estado privados; no se versionan. Imagen local `group2` ausente: reconstruida como `nemotron-chat:group3`, conservando manifest amd64 `sha256:29d4b092755a4fd67a5a2a562554ce69f59ef7e817aca86c2b437454e1b2d4e0`; smoke con uv → PASS, contenedor de prueba eliminado.
- Push de `phase03-d736446-group3` → exit 0. Digest remoto confirmado con gcloud: `sha256:a8f4b0b7f77652121dc0b6065d8a4f48fa5e8bf46dc24bd9347a95b3c487c1fc`. Dry-run server → Deployment/Service admitidos; diff exit 1 mostró únicamente creación de esos dos objetos. Apply/rollout → exitosos. GKE añadió anotación NEG de Ingress al Service; no se creó Ingress ni LoadBalancer en esta entrega.
- Chat inicial `nemotron-chat-85844494c4-lzhhd` 1/1 Ready en nodo CPU `gke-nemotron-lab-cpu-9c917b27-6bgj`. Final tras fallos controlados: `nemotron-chat-85844494c4-hpmqk`, 1/1 Ready, cero reinicios del contenedor. `VLLM_BASE_URL=http://vllm:8000/v1`, timeout total 300 s restaurados; `kubectl diff` contra manifiesto aprobado → exit 0.
- Evidencia de deploy/pods/service/build/registry en `.local/integration-validation/group3-*.json`. Registry informa `imageSizeBytes=52166495` para manifest amd64 y 1819 para atestación. Son campos del API, no factura ni almacenamiento total medido. Presupuesto de 0.25 GiB (~USD 0.025/730 h) permanece ilustrativo; fuente reconfirmada en [precios de Artifact Registry](https://cloud.google.com/artifact-registry/pricing).
- Port-forwards de pruebas: 18080→chat:8080 y 18000→vLLM:8000, dirección 127.0.0.1. Puertos 8000/IPv4 8080 ya ocupados; no se detuvieron procesos ajenos. Los port-forwards propios se retiran al cerrar las pruebas.
- `uv run --project app python scripts/validate-integration.py ... --output .local/integration-validation/group3-live` → exit 0, ocho comprobaciones aprobadas: salud, rechazo, SDK chat/stream, conversación navegador, truncación, cancelación, recarga. SDK de 183 chunks con finish stop; navegador dos turnos y parámetros en payload. Capturas reales desktop/mobile revisadas; sin overflow horizontal a 390×844. Texto de razonamiento se muestra como texto; la segunda respuesta vuelve a responder sobre París en lugar de identificar Francia: fallo de calidad conservado, no evaluado como PASS de calidad.
- Indisponibilidad controlada: cambiar **solo chat** a URL `http://127.0.0.1:9/v1`, rollout, `--offline` → tres comprobaciones PASS. Backend Ready/modelo no disponible; un reintento manual con payload igual y un turno visible; cero retries automáticos observados. Timeout controlado: restaurar URL interna y timeout total 0.001 s → mensaje de espera agotada y botón de reintento visibles. Después restaurar timeout 300 s. No se cambió Deployment/PVC/configuración de vLLM.
- Contexto: recheck secuencial `--context-only --output .../group3-context-recheck` → tres PASS. Petición de 16284 caracteres y salida reservada 1: meta 4095/4096; añadir un carácter → 422. Historial sintético de 8300+8300 caracteres: retirada de un par completo, meta 25/removed_turns=1. Ambas inferencias finalizan con error de truncación esperado para salida 1, sin fingir éxito. Aviso del navegador comprobado con historial sintético en payload de petición real; `group3-pruning-browser-recheck.json`.
- Auditoría cloud: `group3-cloud-chat-logs.json`, 28 entradas desde despliegue, sin marcadores de seis preguntas de pruebas ni frase representativa de respuesta, sin access logs de chat. `group3-log-audit.json`: JS desplegado coincide byte a byte con `app/static/chat.js`, SHA256 `42654a3f2e3548e8f4f343a5381414a12da09d508c59cde7e19a949f48a3d922`; prueba local de HTML inerte corresponde al mismo código. Muestreo de marcadores no demuestra ausencia de todo contenido posible ni reemplaza auditoría de secretos.

### Fallos y limitaciones conservados

1. Primera prueba de contexto (`group3-context/`) tuvo FAIL del fixture: dos mensajes de 8000 caracteres con salida 1 no exceden el presupuesto y no deben recortarse. Se corrigió a 8300, sin cambiar requisitos ni código de aplicación. También hubo upstream errors durante esa ejecución. Primera preparación del aviso por asignación de variable desde Playwright no produjo recorte; fixture corregido inyectando el historial en payload real. Se conservan JSON fallidos y rechecks, no se atribuyen al backend como fallos corregidos.
2. **Fallo real de vLLM:** durante pruebas finales se observó `IndexError: pop from empty list` en `constant_size_cache.py`, `_assign_seq_id_to_cache_index`, con `MQEngineDeadError`. Pod conservó UID, pero restartCount pasó de 0 a 2. Primera observación coincidió con peticiones de contexto y stream iniciadas solapadamente; no demuestra causalidad ni es una prueba de concurrencia sostenida. Segunda observación ocurrió al interrumpir un port-forward propio tras primer fragmento y reintentar, ejecutada después de recuperar serving. No se solicitó ningún reinicio de vLLM; reinicios automáticos observados.
3. Interrupción inesperada: navegador mostró `network error`, habilitó reintento manual, conservó el mismo payload y no duplicó turnos. Reintento terminó con «El stream se interrumpió. Puedes reintentar manualmente.» y el motor volvió a reiniciar. Prueba privada `check-disconnect.py` → exit 1; `group3-disconnect/results.json` conserva error del reintento. **No se declara recuperación de inferencia PASS.** Causa específica/corrección del motor pendientes y fuera del alcance aprobado de integración; no se cambiaron versión ni parámetros para ocultar el fallo.
4. Esperas de recuperación automática comprobaron Ready de nuevo. Estado final capturado: chat y vLLM 1/1 Ready, vLLM con dos reinicios; `/api/status` backend/serving available. Ready no demuestra que el defecto esté corregido. Pruebas con `/think` y 2048 pasan técnicamente; no garantizan finalización ni calidad de valores iniciales `/no_think`/1024.

### Cierre de las pruebas y revisión pendiente

Se restauró manifiesto normal y se retiraron contenedores temporales/port-forwards propios. Permanecen aplicación, serving, PVC e infraestructura en la **sesión continua autorizada**; no se ejecutó destroy ni se acredita limpieza cloud. INT-11/INF-10 continúan pendientes. Al cierre final: eliminar chat, serving y PVC mientras GKE esté accesible; esperar limpieza de discos/controladores; Terraform destroy y comprobar registry/recursos remanentes. Mantener flag registry true para futuras operaciones mientras exista.

Grupo 3 tiene implementación y evidencia real; entrega 03 **no está cerrada ni totalmente aprobada**. Revisión humana pendiente para INT-04 parcial/fallo de recuperación, limitaciones de calidad y limpieza final. No se ampliaron criterios ni se cambió serving para convertir fallos en PASS.

## Aceptación y cierre de fase 03

El propietario declaró: «Acepto la limitación y cierro la fase 03 con el fallo documentado en validation.md. Procede con el commit de cierre de la fase 03 y ejecuta la destrucción limpia de la infraestructura para no acumular costos.»

La entrega queda cerrada con INT-04 PARCIAL y el fallo de recuperación del serving aceptados; se conservan FAIL, trazas, códigos de salida y limitaciones de calidad originales. La aceptación no convierte la recuperación en PASS ni corrige su causa. Se autorizó explícitamente el commit y el cierre de la sesión: eliminar cargas/PVC antes de Terraform, destruir repositorio e infraestructura del laboratorio y comprobar recursos externos al estado. Evidencia de limpieza se añade al terminar, sin anticipar resultados.
