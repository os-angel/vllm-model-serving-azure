# 02 — Serving con vLLM: validación

## Cierre aprobado por el propietario — 2026-10-04

**Estado: CERRADA CON LIMITACIONES ACEPTADAS.** El propietario aprobó la revisión y dio por cerrada la entrega 02 el 2026-10-04. Aceptó expresamente SRV-05, SRV-10 y SRV-11 PARCIAL y los fallos de calidad FP8/aritmética como limitaciones documentadas de esta fase. Se conservan estados, respuestas, códigos de salida y límites originales; la aceptación no convierte FAIL/PARCIAL en PASS ni determina la causa de la mala inferencia.

**Cierre cloud posterior:** al cerrar fase 03, el propietario autorizó finalizar la sesión. Deployment/Service vLLM y PVC/PV/disco eliminados antes de Terraform; infraestructura y registry destruidos, estado vacío e inventario final sin recursos del laboratorio. Evidencia en [validación 03](../03-integration/validation.md). En integración se observaron dos reinicios automáticos por `IndexError: pop from empty list` en caché Mamba; limitación aceptada sin alterar los resultados históricos de esta entrega.

## Ejecuciones

- Base: `20261004-210214`, `/no_think`, temperatura 0, 128 tokens, recuperación incluida; exit 1.
- Comparación única: `20261004-211139`, `/think`, temperatura 0.6, top_p 0.95, 2048 tokens; exit 1 por calidad. Sin recuperación adicional.
- Intento previo `20261004-210020`: error del validador al inspeccionar registro vLLM; corregido. No recreó el pod.
- Seis pruebas locales mediante UV, normales y con `-O`, todas OK. No son pruebas del servicio.

## Comparación de respuestas

| Caso | Base antes de recuperación | Razonamiento 2048 tokens |
|---|---|---|
| fp8 | length; 128 tokens; calidad FAIL | stop; 1273 tokens; calidad FAIL |
| arithmetic | stop; 3 tokens; calidad FAIL | stop; 272 tokens; calidad FAIL |
| capital | stop; 8 tokens; calidad PASS | stop; 139 tokens; calidad PASS |

El presupuesto mayor permitió finalización natural en estas llamadas. FP8 sigue sustituyéndose por FP16 y la tarea 2 + 2 sigue respondiendo sobre 1 + 1. Se conservaron solicitudes/respuestas completas. No se conoce todavía la causa concreta de la mala inferencia; no se atribuye automáticamente a FP8, hardware, tokenizer o motor.

## Matriz por requisito

| ID | Resultado | Evidencia / límites |
|---|---|---|
| SRV-01 | PASS | Imagen por digest, vLLM/CUDA capturados y código nativo comparado con v0.10.1. |
| SRV-02 | PASS | Revisiones fijadas; hashes completos de los diez shards y configuración cacheada coinciden con publicación. Registro nativo inspeccionado en proceso independiente: no introspección del engine en vivo. |
| SRV-03 | PASS | Una réplica Ready; Recreate; snapshots antes/después/final. |
| SRV-04 | PASS | GPU 1, selector, toleration, etiqueta/taint del nodo y asignable verificados. |
| SRV-05 | PARCIAL | Requests dentro de allocatable; RAM/GPU muestreadas; sin OOM en logs revisados. Capturas y peak cgroup no constituyen perfil completo por etapa de arranque/prefill/decode. |
| SRV-06 | PASS | CUDA disponible, carga completa en logs; argumentos/revisiones registrados. Calidad de inferencia permanece fallida, separada abajo. |
| SRV-07 | PASS | Probes presentes; health 200; recuperación Ready sin reinicios observados. |
| SRV-08 | PASS | ClusterIP 8000, sin Ingress/NodePort/LoadBalancer en inference; port-forward propio funciona. |
| SRV-09 | PASS técnico | Con /think y 2048 tokens: catálogo, tres chats, SSE y SDK chat/stream completan con stop; SSE cierra DONE. Base /no_think 128 tokens falla por length. Calidad se mantiene FAIL. |
| SRV-10 | PARCIAL | Boot disk GPU real 100 GB; PVC/df/pesos capturados. Faltan ocupación OCI exacta y medición comparable antes/después del pull; no se reconstruyen. |
| SRV-11 | PARCIAL | Flags de logging deshabilitados. Búsqueda acotada en logs privados de patrones de credenciales/prompts/OOM sin hallazgos; no auditoría exhaustiva de repositorio/logs. |
| SRV-12 | PASS | Sin API key aprobado; documentado acceso desde cargas con conectividad y credenciales Kubernetes para port-forward. |
| SRV-13 | PASS | Recuperación medida: 199.1 s hasta observación Ready; sondeo aproximadamente cada 5 s más latencia kubectl. |
| SRV-14 | PASS | PVC Bound 50Gi RWO standard-rwo, montaje HF_HOME y zona verificados; mismo PVC/PV y SHA256 antes/después. Limpieza aplazada al cierre autorizado. |
| SRV-15 | PASS | Recreate y una réplica; nunca más de un pod en muestras de recuperación. Sondeo no observa cada instante; sin Terraform apply ni segunda recuperación. |

## Revisión del propietario

El propietario aprobó la revisión y dio por cerrada la entrega 02 el 2026-10-04. Aceptó expresamente SRV-05, SRV-10 y SRV-11 PARCIAL y los fallos de calidad FP8/aritmética como limitaciones documentadas de esta fase. Se conservan estados, respuestas, códigos de salida y límites originales; la aceptación no convierte FAIL/PARCIAL en PASS ni determina la causa de la mala inferencia. No se iniciarán más variantes en el cierre. Serving, PVC e infraestructura se conservan durante la sesión continua ya autorizada; no se aplica Terraform. Cerrar esta entrega no es cerrar la sesión del laboratorio. La limpieza Kubernetes/PVC y después Terraform sigue pendiente para el cierre final (INF-10). La siguiente entrega es 03-integración.

Reportes privados: `.local/serving-validation/20261004-210214/report.md`, `.local/serving-validation/20261004-211139/report.md`; consolidado `.local/serving-validation/phase02-review.md`. Archivos `results.json`, `requirements.json`, respuestas, hashes y muestras permanecen ignorados por Git.

## Historial conservado

## Revisión actual — pasos 1, 2 y 3 autorizados

Paso 1: reconciliados estado actual y almacenamiento en requisitos/plan/roadmap; conservados apartados históricos. Paso 2: cuatro pruebas unitarias con subcasos positivos/negativos ejecutadas mediante UV, todas OK; sintaxis y ayuda del validador OK. Verifican rechazo de truncación, salida vacía, respuesta incorrecta, múltiples oraciones y SSE sin cierre. Estas pruebas validan la lógica local, no el servicio GKE. Paso 3: ejecución contra GKE por iniciar; todavía no hay nuevos PASS del servicio.

La tabla y los apartados siguientes conservan evidencia histórica; no representan todos el estado más reciente. La ejecución privada `20261004-202152` observó recuperación (~210 s), mismo PVC/PV y metadatos de pesos; registró FAIL de API antes/después por final `length` y respuesta sobre FP16 a una solicitud FP8. No produjo pruebas SSE/SDK completas debido al fallo acoplado. Boot disk real observado: 100 GB. El validador revisado separa comprobaciones, conserva fallos y compara SHA256; su nueva ejecución se registrará aquí, sin declarar cerrada la fase.

## Automatización preparada (histórico)

Se creó `scripts/validate-serving.py` por solicitud del propietario. Ejecución, entorno y dependencias mediante `uv`, según su instrucción. El modo predeterminado consulta el servicio y envía solicitudes de prueba; `--with-recovery` autoriza explícitamente recrear el pod durante la ejecución. Guarda evidencia/reporte privados en `.local/serving-validation/`. Se comprobaron sintaxis y ayuda localmente; no se ejecutó todavía este script contra GKE y no se atribuyen nuevos PASS a su creación. Calidad de respuesta, revisión efectiva de código remoto, logs y límites de medición se mantienen explícitos en el reporte.

**Estado histórico:** SERVING OPERATIVO tras las correcciones de rutas NVIDIA y Service links. Pod `vllm-647999fb94-shqb7` `1/1 Running`, cero reinicios observados. Sesión continua con infraestructura y serving activos por autorización del propietario; quedan pendientes pruebas de recuperación, mediciones completas y limpieza al cierre.

## Resultado de la verificación tras ambas correcciones

### Validación externa reportada por el propietario — 2026-10-04

Fuente: resumen compartido por el propietario en esta conversación tras ejecutar el protocolo desde su equipo, con acceso local mediante port-forward. Esta comprobación no fue ejecutada nuevamente por Codex; no se adjuntaron respuestas completas ni marcas de tiempo individuales.

| Paso / requisitos | Evidencia reportada | Resultado |
|---|---|---|
| Salud y catálogo / SRV-07–SRV-09 | `/health` HTTP 200; `/v1/models` devuelve `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8`, `max_model_len: 4096`. | PASS reportado: acceso externo y catálogo esperado. |
| Chat / SRV-09 | HTTP 200, 40 tokens de prompt y 24 de salida, `finish_reason: stop`. Propietario declara cumplidos los criterios del protocolo. | PASS reportado para finalización; el resumen no incluye el texto de la respuesta para revisar su calidad de forma independiente. |
| Streaming / SRV-09 | 193 eventos `data: {...}` observados progresivamente sobre HTTP y final `data: [DONE]`. | PASS reportado. Número de eventos no equivale necesariamente a número de tokens; no se midió latencia. |
| Estabilidad / SRV-03/SRV-05 | Pod `vllm-647999fb94-shqb7`, `1/1 Running`, `RESTARTS: 0` después de las solicitudes. | PASS para el estado observado; no prueba estabilidad sostenida ni picos de RAM. |
| Volumen / SRV-14 | PVC `vllm-cache` `Bound`, 50 GiB, StorageClass `standard-rwo`. | Binding confirmado; persistencia tras recreación y uso final pendientes. |

Con esta evidencia se cubre la prueba externa por curl/port-forward. Siguen pendientes el cliente SDK, la revisión efectiva del código remoto (SRV-02), las mediciones finales (SRV-05/SRV-10), recuperación (SRV-13), persistencia tras recreación (SRV-14) y cierre autorizado. La entrega completa aún no se declara terminada.

### Comprobaciones ejecutadas directamente por Codex

- SRV-03/SRV-06/SRV-07: una réplica Ready, CUDA detectada, modelo cargado y startup completa a `2026-10-05T01:53:57Z` (2026-10-04 hora local). Logs: descarga de pesos `104.517253 s`, carga de pesos `36.50 s`, carga del modelo `142.076410 s`; no sumar estas duraciones porque se solapan.
- Memoria reportada por vLLM: pesos `9.3808 GiB`; GPU total `22.03 GiB`; presupuesto al 90% `19.83 GiB`; pico de activaciones PyTorch del perfil `1.16 GiB`; memoria no PyTorch `0.13 GiB`. Son valores del arranque, no picos de carga sostenida. El cálculo de concurrencia `146.65x` del log NO es capacidad validada; `max-num-seqs` sigue en 1.
- SRV-08: Service observado `ClusterIP`, puerto `8000/TCP`, sin IP externa. Comprobaciones mediante DNS `http://vllm.inference.svc.cluster.local:8000` desde un cliente Python dentro del pod.
- SRV-09: `/health` HTTP 200; `/v1/models` HTTP 200 identifica el checkpoint esperado y contexto 4096. Chat HTTP 200 devuelve texto no vacío en español explicando Terraform, `finish_reason=stop`. Streaming HTTP 200, 48 eventos `data:` y final `data: [DONE]`. Solicitudes de prueba: system `/no_think`, `max_tokens=128`, `temperature=0`; sin API key. La comprobación streaming leyó el cuerpo completo: confirma eventos/final, no latencia por fragmento ni entrega progresiva en un cliente externo.
- Límites: no se probó port-forward en esta intervención, recuperación, concurrencia sostenida ni medición final de disco/RAM. Los logs de la primera petición avisan descarga de `configuration_nemotron_h.py` desde el repo base; no se verificó en esta intervención qué commit utilizó esa ruta de chat. SRV-02 conserva pendiente la comprobación efectiva del código remoto, aunque los argumentos de revisión están declarados.

## Corrección aplicada y comprobación de arranque — 2026-10-04

Autorización del propietario: aplicar la corrección y validar arranque en el Deployment existente; conservar infraestructura durante la sesión. El manifiesto local ya contenía `LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/cuda/lib64` al comenzar esta intervención; se conservó y aplicó con `kubectl apply -f k8s/serving/vllm.yaml`.

- SRV-06, descubrimiento GPU RESUELTO: en pod `vllm-6dddbf78f8-fqpz8`, `ctypes.CDLL("libnvidia-ml.so.1")` carga sin error; `torch.cuda.is_available()` devuelve `True`; dispositivo `NVIDIA L4`. vLLM registra `Automatically detected platform cuda` y versión `0.10.1`.
- SRV-14, montaje observado: PVC `vllm-cache` `Bound`, capacidad `50Gi`, `standard-rwo`, RWO; `/root/.cache/huggingface` montado en `/dev/nvme0n2`. `df -h` reportó 49G de filesystem, 33M usados, 49G disponibles al comienzo de la carga. Persistencia entre recreaciones y uso final siguen pendientes.
- La comprobación de Ready de 50 segundos expiró. El proceso avanzó hasta arquitectura `NemotronHForCausalLM`, ModelOpt FP8 y motor V0, pero falló con `ValueError: VLLM_PORT 'tcp://…:8000' appears to be a URI`. Salida del contenedor `1`, motivo `Error`; no evidencia de OOM en esa terminación.
- SRV-06/SRV-08: se especificó y aplicó `enableServiceLinks: false` para evitar la variable de Service `VLLM_PORT`, conservando acceso por DNS. [vLLM documenta esta colisión de nombres](https://docs.vllm.ai/en/v0.10.1/configuration/env_vars.html). Se mantiene una réplica `Recreate`, GPU/PVC existentes y Service `ClusterIP`; no se añadieron recursos facturables.

La disponibilidad y pruebas HTTP/chat/streaming siguen pendientes de completar el arranque. No marcar SRV-06 completo por haber resuelto la detección de CUDA.

Comprobación posterior: la segunda aplicación se hizo cuando `LD_LIBRARY_PATH` ya había desaparecido del archivo local y del Deployment; el pod `vllm-6666c56897-2vwk7` volvió al error de detección. Se restauró la ruta en YAML y se reaplicó; consulta del Deployment confirmó juntas `enableServiceLinks=false` y las rutas NVIDIA/CUDA. No se determinó el origen del cambio concurrente del archivo.

Pod resultante `vllm-647999fb94-shqb7`: cero reinicios observados; CUDA detectada, Flash Attention inicializado y `Starting to load model` con formato `*.safetensors`, superando la colisión de `VLLM_PORT`. PVC pasó de 33M a 7.3G usados, con 42G disponibles (`df -h`), evidencia de progreso de descarga; no representa el tamaño final de los pesos. Ready aún pendiente en esa observación.

## Diagnóstico GPU solicitado por el propietario — 2026-10-04

### Causa confirmada mediante DEBUG e inspección del contenedor

Por solicitud del propietario se activó temporalmente `VLLM_LOGGING_LEVEL=DEBUG` en el Deployment. El pod nuevo `vllm-6c689b8b49-hrw7m` registró `Exception happens when checking CUDA platform: NVML Shared Library Not Found`. La inspección con `kubectl exec` observó:

- `LD_LIBRARY_PATH=/usr/local/cuda/lib64`.
- `NVIDIA_VISIBLE_DEVICES=all` y `NVIDIA_DRIVER_CAPABILITIES=compute,utility` ya presentes en el entorno efectivo, aunque no declarados en el YAML.
- Dispositivos `/dev/nvidia0`, `/dev/nvidiactl`, `/dev/nvidia-uvm` y otros presentes.
- `/usr/local/nvidia/lib64/libnvidia-ml.so.1` y biblioteca versionada `libnvidia-ml.so.580.159.04` presentes.
- `ctypes.CDLL("libnvidia-ml.so.1")` falló con `OSError: libnvidia-ml.so.1: cannot open shared object file: No such file or directory`.

SRV-06: causa del fallo de detección identificada: el cargador no encuentra NVML por nombre porque la ruta del driver montado no está en `LD_LIBRARY_PATH`. Añadir las dos variables NVIDIA propuestas no aborda esta causa; ya están presentes. Corrección indicada: declarar `LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/cuda/lib64`, preservando la ruta CUDA observada. Aplicación de la corrección, detección CUDA posterior, carga del modelo y API permanecen PENDIENTES; este diagnóstico no demuestra compatibilidad completa. Se retiró el DEBUG temporal del Deployment mediante `kubectl set env ... VLLM_LOGGING_LEVEL-`; no se aplicó la corrección ni se modificó el manifiesto durante este análisis.

La inspección inicial de solo lectura que sigue actualizó la evidencia de despliegue de los apartados históricos: el Deployment ya existe, pero serving aún no está operativo. La comprobación posterior con DEBUG consta arriba.

| Requisitos | Evidencia observada | Resultado y límites |
|---|---|---|
| SRV-01/SRV-04/SRV-06 | Pod `vllm-f77bdcd8f-pkb8j` en el nodo GPU, `0/1 CrashLoopBackOff`; imageID coincide con el digest fijado. Recursos observados incluyen request/limit `nvidia.com/gpu: 1`. Logs anteriores muestran `UnspecifiedPlatform` y `Failed to infer device type`. | Carga FALLIDA; aún no hay evidencia de API ni carga del checkpoint. El mensaje no identifica la causa concreta del fallo de detección. |
| SRV-04 | Plugin `nvidia-gpu-device-plugin-small-cos-xbl5d` `3/3 Running`; nodo anuncia `nvidia.com/gpu: 1`. | Registro/scheduling GPU observado; no prueba acceso a CUDA/NVML dentro de vLLM. |
| SRV-05/SRV-10 | Nodo Ready, `DiskPressure=False`, ephemeral-storage allocatable `66387424310` bytes. | Allocatable es presupuesto de scheduling, no espacio libre. El propietario informa redimensionamiento a 100 GB; tamaño del disco, uso real y ocupación de imagen no se midieron aquí. El diseño local todavía declara boot disk de 50 GB; reconciliación pendiente de confirmar el cambio real y su gestión en Terraform. |
| SRV-06 | Pod declara solamente `HF_HOME` en `spec.containers[0].env`. Intento de inspeccionar entorno efectivo, dispositivos y carga NVML mediante `kubectl exec` falló con `container not found ("vllm")` por el ciclo de reinicios. | Diagnóstico interno PENDIENTE. Ausencia de variables en YAML no demuestra ausencia de valores heredados de la imagen o inyectados por el runtime. |

La propuesta de añadir `NVIDIA_VISIBLE_DEVICES=all` y `NVIDIA_DRIVER_CAPABILITIES=compute,utility` no está validada como solución. NVIDIA documenta `compute,utility` como capacidades predeterminadas cuando la variable no está definida ([Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html)). vLLM 0.10.1 detecta CUDA mediante inicialización NVML y conteo de dispositivos; registra la excepción concreta con nivel DEBUG ([código de detección](https://docs.vllm.ai/en/v0.10.1/api/vllm/platforms/index.html)). GKE documenta que las bibliotecas montadas en `/usr/local/nvidia/lib64` pueden no estar en `LD_LIBRARY_PATH` ([diagnóstico GKE](https://docs.cloud.google.com/kubernetes-engine/docs/troubleshooting/gpus#the_nvidia-smi_command_fails)).

Siguiente comprobación SRV-06, Grupo 2: obtener la excepción DEBUG de detección o inspeccionar NVML/dispositivos dentro de un contenedor con la misma imagen y asignación GPU. Si se confirma biblioteca NVML no encontrada y montaje existente, corregir `LD_LIBRARY_PATH` conservando las rutas necesarias de la imagen. Confirmar después detección CUDA, carga completa, readiness y API antes de declarar resuelto. No se modificó el manifiesto ni se creó otro pod GPU.

**Estado histórico antes del despliegue:** DISEÑO PVC APROBADO; DESPLIEGUE PENDIENTE. El propietario aceptó NVIDIA Open Model License, confirmó acceso y aprobó API interna sin API key (2026-10-04). Decidió conservar el boot disk GPU en 50 GB y usar un PVC `pd-balanced` de 50 GiB para pesos/cache, evitando el surge que podría requerir otra L4. El estado actual y la evidencia posterior constan al inicio de este documento.

## Registro por requisito (histórico anterior a los nuevos reportes)

| ID | Comprobación y evidencia requerida | Estado | Resultado/limitaciones |
|---|---|---|---|
| SRV-01 | Digest OCI exacto y versión vLLM/CUDA observada en el pod. | PENDIENTE | Docker Hub publica `vllm/vllm-openai:v0.10.1` para `linux/amd64` con digest `sha256:c62343ee72f094ef574ab3af2717d0c60fec5e0808b238f19ac4c0d22fd152f7`, CUDA 12.8.1 y tamaño comprimido 9.8 GB ([Docker Hub](https://hub.docker.com/layers/vllm/vllm-openai/v0.10.1/images/sha256-c62343ee72f094ef574ab3af2717d0c60fec5e0808b238f19ac4c0d22fd152f7)). Es una referencia de manifiesto, no prueba de compatibilidad/carga en L4; falta observar la imagen desde el pod. |
| SRV-02 | Commit SHA del modelo, revisión del código remoto y aceptación de licencia/acceso documentadas. | PENDIENTE | Propietario aceptó NVIDIA Open Model License y confirmó acceso (2026-10-04). Checkpoint fijado a `8bc5eece2eb5514c4bca7f2ec655b91eb554f4c0`; `config.json` dirige el código remoto al repo base, fijado a `6533e8de2c68e4536bf7c411d7a3ce5734111476` mediante `--code-revision`. Revisión estática acotada de los módulos Python: imports observados limitados a `re`, PyTorch y Transformers, sin llamadas visibles a red, procesos o escritura de archivos; no equivale a auditoría de seguridad. No se descargaron pesos. |
| SRV-03 | `kubectl get deploy,pods -n inference`: una réplica Ready y estrategia de reemplazo sin solapamiento GPU. | PASS | Manifiesto de una réplica `Recreate`; Codex observó un pod Ready y el propietario confirma `vllm-647999fb94-shqb7` `1/1 Running`, cero reinicios. Prueba medida de recuperación separada en SRV-13. |
| SRV-04 | YAML observado del pod/nodo: `workload=gpu`, toleration `dedicated=gpu:NoSchedule`, GPU limit 1 y pod asignado al nodo GPU. | PENDIENTE | Infra 01 observó etiqueta, taint y `nvidia.com/gpu: 1` asignable. |
| SRV-05 | Requests de CPU/RAM/ephemeral storage frente a allocatable y uso bajo carga, sin OOM/eviction. | PENDIENTE | Consulta de solo lectura del nodo (2026-10-04): allocatable CPU `3920m`, memoria `13591704Ki`, ephemeral storage `18828602911` bytes. Falta medir uso/picos del pod de serving y fijar requests/probes. |
| SRV-06 | Args del proceso, logs de carga completa y modelo/revisión servidos. | PENDIENTE | Parámetros base están en `requirements.md`; compatibilidad vLLM/L4 no probada. |
| SRV-07 | Startup/readiness/liveness probes durante carga y después de Ready. | PENDIENTE | La ruta `/health` se confirmará contra digest seleccionado. |
| SRV-08 | Tipo/puerto del Service, ausencia de NodePort/LB/Ingress, port-forward funcional. | PARCIAL | Codex observó Service ClusterIP puerto 8000 sin IP externa; propietario reporta protocolo externo por port-forward exitoso. Falta inventario explícito de ausencia de Ingress/otros recursos de exposición. |
| SRV-09 | Salidas HTTP de `/v1/models`, una petición chat JSON y una petición streaming que completa. | PASS | Prueba interna ejecutada por Codex con respuesta no vacía y final SSE; propietario confirma prueba externa: HTTP 200, modelo esperado, chat 40+24 tokens con `stop`, 193 eventos SSE progresivos y `[DONE]`. Texto de respuesta externa no adjuntado; sin medición de latencia. |
| SRV-10 | Tamaño/cache del PVC, `df` antes/después, espacio libre en boot disk e incidentes. | PENDIENTE | PVC especificado en 50 GiB `pd-balanced` para pesos/cache; aún no existe en GCP. Los 25 GB libres observados en boot disk quedan para la imagen/uso efímero. La imagen publicada ocupa 9.8 GB comprimida; falta medir su ocupación real en el nodo. INF-07 sigue en validación durante el pull. |
| SRV-11 | Inspección de manifiestos/Secret y logs; no aparecen tokens o contenido de prompt. | PENDIENTE | Secret solo si el repo exige autenticación; no versionar credenciales. |
| SRV-12 | Confirmar acceso solo por red interna/port-forward y registrar alcance de llamadas desde pods del clúster. | PENDIENTE | Propietario aprobó sin API key (2026-10-04). Falta verificar Service ClusterIP y registrar que workloads con conectividad al Service pueden invocarlo. |
| SRV-13 | Hora de eliminación y hora de Ready tras recreación; comprobar que no coexistieron dos pods GPU. | PENDIENTE | Interrupción esperada en pool de una L4. El propietario puede aplazar esta prueba. |
| SRV-14 | PVC `vllm-cache` de 50 GiB, `standard-rwo`, montado en `/root/.cache/huggingface`; cache persiste tras recreación del pod. | PARCIAL | Codex observó binding, capacidad, clase y montaje; propietario confirma `Bound` 50 GiB `standard-rwo` tras solicitudes. Falta confirmar zona, ocupación final y persistencia tras recreación. |
| SRV-15 | Una réplica `Recreate` sin pods GPU simultáneos y sin surge de nodos. | PENDIENTE | Manifiesto fija una réplica y estrategia `Recreate`; no se desplegó. |

## Evidencia previa de infraestructura reutilizable

El propietario compartió resultados del 2026-10-04: nodo GPU Ready `g2-standard-4`; L4 NVIDIA reportada por `nvidia-smi`, driver `580.159.04`, VRAM reportada `23034 MiB`; taint `dedicated=gpu:NoSchedule`; etiqueta `workload=gpu`; una GPU asignable; disco `pd-balanced` de 50 GB. Antes de bajar vLLM y el modelo, un pod diagnóstico observó overlay 46G, 21G usados y 25G libres. El pod diagnóstico fue eliminado. Esta evidencia valida el nodo, no la carga del modelo.

## Revisión documental del Grupo 0 — 2026-10-04

| Requisito | Resultado observado | Estado | Limitación/acción |
|---|---|---|---|
| SRV-01 | Docker Hub reporta para `vllm/vllm-openai:v0.10.1` el digest `sha256:c62343ee72f094ef574ab3af2717d0c60fec5e0808b238f19ac4c0d22fd152f7`, arquitectura `linux/amd64`, tamaño comprimido 9.8 GB y CUDA 12.8.1. | PENDIENTE | Digest fijado como objetivo del manifiesto; aún falta confirmar versión/CUDA dentro del pod y probar compatibilidad con modelo/L4. NVIDIA documenta `v0.10.1` ([ficha del modelo](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8)). |
| SRV-02 | La ficha del checkpoint identifica NVIDIA Open Model License Agreement y documenta el uso con `--trust-remote-code`. | PENDIENTE | Aceptación/acceso confirmados por el propietario; SHA del checkpoint y del código remoto están fijados y revisión estática acotada registrada en el encabezado. Falta confirmar carga con esta combinación en L4. No se descargaron pesos. |
| SRV-05/SRV-10/SRV-14 | 25 GB libres antes del pull; imagen publicada 9.8 GB comprimida, checkpoint ~10.3 GB. | PENDIENTE | Diseño coloca pesos/cache en PVC 50 GiB `pd-balanced` y deja el boot disk para la imagen/efímero. Falta probar la ocupación real de la imagen en el nodo; no aplicar si el espacio no conserva margen. |
| SRV-12 | La propuesta de requisitos conserva ClusterIP sin API key y advierte acceso desde cargas con conectividad al Service. | PENDIENTE | Frontera aprobada por el propietario (2026-10-04); falta observar el Service y verificar la conectividad desde workloads. |

| SRV-05/SRV-10/SRV-15 | Consultas de solo lectura `kubectl get nodes` y `gcloud container node-pools describe gpu` (2026-10-04) | PENDIENTE | Allocatable: `3920m` CPU, `13591704Ki` memoria y `18828602911` bytes ephemeral. Pool GPU actual: `g2-standard-4`, disco `pd-balanced` 50 GB, estrategia `SURGE`, `maxSurge: 1`. El propietario confirmó cuota de una L4 y eligió PVC para no cambiar el pool ni disparar un surge. |
| SRV-14 costo | Precio público `pd-balanced` en us-central1: USD `0.00013699/GiB-h`; un disco de 50 GiB cuesta aproximadamente USD `0.00685/h` o `5.00/mes` a 730 h mientras exista. | PENDIENTE DE REVISIÓN ANTES DE APPLY | Estimación bruta, sin descuentos/créditos; facturación del disco dinámico empieza al aprovisionarse y continúa hasta eliminar el PVC/PV. Fuentes: [precios de discos GCP](https://cloud.google.com/compute/disks-image-pricing) y [volúmenes persistentes de GKE](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/persistent-volumes). No se ha creado el PVC. |

Fuente del digest y tamaño: [Docker Hub, vllm/vllm-openai:v0.10.1](https://hub.docker.com/layers/vllm/vllm-openai/v0.10.1/images/sha256-c62343ee72f094ef574ab3af2717d0c60fec5e0808b238f19ac4c0d22fd152f7). La inspección web confirma metadatos publicados, no una descarga o prueba local.

## Decisiones a registrar al aprobar

- Aprobación/revisión del propietario y fecha.
- Digest de imagen elegido y SHA del modelo.
- Confirmación de licencia y acceso HF: propietario aceptó licencia y confirmó acceso el 2026-10-04.
- Aceptación del Service sin API key dentro del clúster: aprobada el 2026-10-04.
- PVC de 50 GiB `pd-balanced` elegido para persistir pesos/cache y evitar el surge del pool GPU; costo estimado ~USD 5/mes, sin apply.
- Requests/limits y ventana de probes pendientes de medición en el despliegue autorizado.
- Continuar con serving en la sesión continua; la infraestructura permanece activa. INF-10 se documentará al cierre final del laboratorio.
