# 02 — Serving con vLLM: requisitos

**Estado actual: CERRADA CON LIMITACIONES ACEPTADAS** por el propietario el 2026-10-04. Serving y PVC desplegados: CPU 50 GB, GPU real 100 GB, PVC 50 GiB. Licencia/acceso y ClusterIP sin API key aprobados. Evidencia, fallos y criterios parciales conservados en `validation.md`; no se ejecuta Terraform apply.

**Estado:** revisión de diseño aprobada por el propietario (2026-10-04): NVIDIA Open Model License y acceso aceptados; Service interno sin API key; conservar los boot disks existentes de 50 GB y almacenar pesos/cache en PVC dedicado de 50 GiB `pd-balanced`. Los manifiestos se diseñan/versionan en esta entrega, pero no se aplican en GCP en este paso.

Desplegar una réplica de vLLM en el pool GPU del clúster `nemotron-lab`, cargar `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8` y publicar la API OpenAI-compatible mediante un Service interno. La entrega depende de la infraestructura 01, aprobada operativamente. INF-07 de la entrega 01 se comprueba aquí durante la descarga del modelo; INF-10 permanece aplazado al cierre final del laboratorio.

## Alcance

- Namespace `inference` y Deployment de una réplica con vLLM.
- Una NVIDIA L4 reservada mediante el selector y la toleration ya validados.
- Checkpoint FP8 Nemotron Nano 9B v2, modelo de texto y endpoint `/v1/chat/completions`.
- Service Kubernetes `ClusterIP` en puerto 8000 y acceso de prueba desde operador mediante `kubectl port-forward`.
- PVC dinámico dedicado a los pesos y la caché HF, montado en `/root/.cache/huggingface`; medir su uso y el espacio restante del nodo para la imagen OCI.

Quedan fuera la interfaz web, backend de aplicación, autenticación empresarial, alta disponibilidad, escalado automático, publicación por LoadBalancer/Ingress, tuning de concurrencia y mediciones de capacidad sostenida. La única GPU implica interrupción durante carga y reinicio.

## Decisiones heredadas de la infraestructura aprobada

- Clúster zonal `nemotron-lab`, proyecto `llmresearch-510422`, zona `us-central1-a`; GKE `1.35.6-gke.1250000` observado.
- Pool GPU de un nodo `g2-standard-4`, GPU L4, `COS_CONTAINERD`, driver administrado observado `580.159.04`.
- Etiqueta `workload=gpu`; taint `dedicated=gpu:NoSchedule`; `nvidia.com/gpu: 1` asignable.
- El boot disk CPU es `pd-balanced` de 50 GB; el disco GPU se amplió directamente a 100 GB. Los pesos/cache usan un PVC de 50 GiB. La plantilla del pool existente conserva 50 GB para evitar un surge con cuota de una L4. La imagen vLLM permanece en el almacenamiento efímero local del nodo; su tamaño materializado debe medirse antes de confirmar carga estable.
- Serving inicial heredado de `tech.md`: una GPU, `--tensor-parallel-size 1`, `--gpu-memory-utilization 0.90`, `--mamba_ssm_cache_dtype float32`, `--max-model-len 4096` y `--max-num-seqs 1`.
- Sin recursos Kubernetes `LoadBalancer`; el Service de vLLM será interno. INF-10 se pospone al cierre final del laboratorio por instrucción del propietario.

## Requisitos y criterios de aceptación

| ID | Requisito | Criterio observable | Tarea del plan |
|---|---|---|---|
| SRV-01 | Fijar una imagen vLLM compatible y reproducible. | El manifiesto usa `vllm/vllm-openai@sha256:c62343ee72f094ef574ab3af2717d0c60fec5e0808b238f19ac4c0d22fd152f7`; se registra versión vLLM, CUDA y digest. Compatibilidad en L4 aún por probar. | 0.1, 1.1 |
| SRV-02 | Fijar la revisión exacta del checkpoint y cumplir su licencia. | Fijar `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8` al commit `8bc5eece2eb5514c4bca7f2ec655b91eb554f4c0` para modelo/tokenizer y su código remoto referenciado en `nvidia/NVIDIA-Nemotron-Nano-9B-v2` al commit `6533e8de2c68e4536bf7c411d7a3ce5734111476`, usando `--revision`, `--tokenizer-revision` y `--code-revision`. Licencia aceptada por el propietario y revisión estática documentada; no descargar desde `main` flotante. | 0.1 |
| SRV-03 | Desplegar una única réplica de serving en el namespace `inference`. | Deployment observado con una réplica Ready y exactamente un pod vLLM; estrategia de actualización impide dos pods GPU simultáneos (`Recreate`). | 1.1, 2.1 |
| SRV-04 | Reservar la L4 usando el contrato de scheduling validado. | Pod ubicado en nodo con `workload=gpu`, tolera `dedicated=gpu:NoSchedule` y declara `limits.nvidia.com/gpu: 1`; nodo GPU queda con una GPU asignable y el pod la consume. | 1.1, 2.1 |
| SRV-05 | Configurar CPU, RAM y almacenamiento efímero de manera compatible con el nodo real. | Requests explícitos no superan recursos allocatable; se observan requests, uso en carga de modelo y eventos de eviction/OOM. Cualquier límite de ephemeral storage y `emptyDir.sizeLimit` se fija después de revisar el espacio del nodo y el tamaño de imagen/pesos. | 0.2, 1.2, 2.2 |
| SRV-06 | Servir el checkpoint con configuración inicial validada. | Logs de arranque identifican el modelo y muestran carga completa sin error; el proceso usa host `0.0.0.0`, puerto 8000, modelo indicado y parámetros heredados en esta especificación. Se registran argumentos y revisión reales. | 1.1, 2.2 |
| SRV-07 | Permitir el inicio lento por descarga/carga del modelo y detectar fallos después. | `startupProbe` evita reinicios durante la ventana de carga acordada; readiness solo pasa cuando `/health` responde; liveness no mata el proceso antes de que complete startup. Probes probadas con la imagen fijada. | 1.2, 2.2 |
| SRV-08 | Exponer solo un endpoint interno. | Service `ClusterIP` `vllm:8000`, sin NodePort, LoadBalancer ni Ingress. `kubectl port-forward -n inference svc/vllm 8000:8000` permite la prueba local. | 1.3, 2.3 |
| SRV-09 | Responder por la API compatible con OpenAI. | `GET /v1/models` identifica el modelo esperado; una petición `POST /v1/chat/completions` genera respuesta no vacía y otra con `stream: true` entrega fragmentos y termina correctamente. | 2.3 |
| SRV-10 | Medir PVC/cache y uso efímero del nodo. | Se registra el tamaño de los pesos, `df` del PVC antes/después, espacio libre del boot disk antes/después del pull de imagen y eventos del nodo; no hay `DiskPressure`, eviction ni falta de espacio. El PVC almacena el modelo; la imagen OCI permanece en el boot disk GPU. | 0.2, 2.2 |
| SRV-11 | Evitar exposición pública y no guardar prompts o secretos en el repositorio/logs. | Credenciales HF, si fueran necesarias, llegan desde un Secret no versionado; no aparecen en YAML ni logs. Logging de solicitudes con contenido está deshabilitado en la versión elegida. Service continúa ClusterIP. | 0.1, 1.2, 2.3 |
| SRV-12 | Documentar el límite de seguridad del endpoint sin API key. | Se registra explícitamente que ClusterIP y port-forward no añaden autenticación a las llamadas dentro del clúster; acceso operativo externo se hace por credenciales de Kubernetes. No anunciar como endpoint de producción. | 0.1, 2.3 |
| SRV-13 | Probar recuperación controlada en una sola GPU. | En prueba acordada se elimina/recrea el pod, se registra indisponibilidad y tiempo de descarga/carga; nunca hay dos pods GPU activos a la vez. Al terminar esta entrega, el propietario decide si serving queda activo para la Entrega 03 o si se eliminan sus cargas Kubernetes; la infraestructura se conserva hasta el cierre final. | 2.4, 3.1 |
| SRV-14 | Mantener los pesos/cache HF en un volumen persistente separado del boot disk GPU. | PVC `inference/vllm-cache` de 50 GiB con `ReadWriteOnce` y StorageClass `standard-rwo` (`pd-balanced`) montado en `/root/.cache/huggingface`; `HF_HOME` apunta al montaje. Cache sobrevive a recrear el pod; se registra tamaño/espacio y, al cierre, se elimina el PVC/PV/disco facturable después de borrar la carga. | 0.2, 1.2, 2.2, 2.4, 3.1 |
| SRV-15 | Evitar otra asignación de L4 durante el serving inicial y sus recreaciones. | Deployment con una réplica y estrategia `Recreate`; no hay dos pods vLLM simultáneos. El PVC `ReadWriteOnce` se vuelve a montar después de recrear el pod y los datos cacheados siguen disponibles. | 1.2, 2.1, 2.4 |

## Decisiones, supuestos e hipótesis

### Decisiones heredadas/aprobadas

- GKE Standard y L4 ya desplegados; mantener la infraestructura durante la sesión continua.
- Modelo, interfaz OpenAI-compatible, una GPU, contexto inicial de 4096 tokens y concurrencia inicial de una secuencia.
- No exponer por IP pública. Service interno y `kubectl port-forward`.
- El modelo usa `--trust-remote-code` y estado Mamba SSM en FP32, según la ficha de NVIDIA.

### Configuración de implementación

- Corrección SRV-06 aprobada por el propietario: declarar `LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/cuda/lib64` para localizar NVML y conservar la ruta CUDA observada. Verificar detección CUDA, carga del modelo y API después del reemplazo del pod.
- Configurar `enableServiceLinks: false` en el pod para impedir que el Service `vllm` inyecte `VLLM_PORT` como URI y colisione con la variable interna numérica de vLLM. El acceso al Service usa DNS. Comprobar que el motor supera este error durante el arranque. (SRV-06/SRV-08)

- Usar la imagen `vllm/vllm-openai` por digest `sha256:c62343ee72f094ef574ab3af2717d0c60fec5e0808b238f19ac4c0d22fd152f7`; la compatibilidad con el modelo/L4 se valida al desplegar.
- Fijar el repo HF del checkpoint y el repo de código remoto mediante `--revision` y `--code-revision`; el código revisado y los SHA constan arriba.
- Usar `standard-rwo` para un PVC dinámico zonal `pd-balanced` de 50 GiB, `ReadWriteOnce`, montado en `/root/.cache/huggingface`, con `HF_HOME` al mismo path. `WaitForFirstConsumer` vincula el volumen cuando el pod GPU programa en la zona; la caché sobrevive recreaciones del pod. La persistencia evita volver a bajar los pesos, aunque no ofrece acceso simultáneo desde dos nodos.
- Requests de CPU/RAM/ephemeral storage iniciales se comparan con allocatable observado; la startup probe parte de 30 minutos y se ajustará con duración real de carga. No se configura `emptyDir` para los pesos; usan el PVC.
- El propietario aprobó no configurar `--api-key` para el laboratorio; toda llamada desde otro pod del clúster podrá llegar al Service según la conectividad de red.

### Supuestos e hipótesis pendientes

- Supuesto: los nodos pueden descargar la imagen OCI y los pesos desde sus IPv4 externas efímeras.
- El propietario confirmó aceptación de NVIDIA Open Model License y acceso al checkpoint (2026-10-04). Si la descarga finalmente solicita token, inyectarlo desde un Secret fuera de Git; no incluir credenciales en manifiestos.
- Hipótesis: vLLM `v0.10.1` con CUDA 12.8.1 y driver observado `580.159.04` carga y sirve el checkpoint en L4. La prueba `nvidia-smi` confirmó el driver, no la compatibilidad de vLLM.
- El propietario amplió directamente el disco GPU a 100 GB; no se actualizó la plantilla del pool GKE (50 GB) para evitar un surge. Terraform declara 100 GB para futuras creaciones e ignora únicamente cambios de ese campo en el pool existente.
- `standard-rwo` es la clase CSI de GKE para discos balanceados; confirmar que está presente en el clúster antes de aplicar el PVC. El PVC crea un recurso de almacenamiento facturable al programarse el pod y debe eliminarse en el cierre autorizado.
- Pendiente: límites explícitos de CPU/RAM/ephemeral storage y ventana de probes tras medir el arranque real. Allocatable observado: 3920m CPU, 13591704Ki de memoria y 18828602911 bytes de almacenamiento efímero.

## Fuentes técnicas

- [Ficha oficial del checkpoint y receta vLLM](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8): vLLM `>=0.10.1`, `--trust-remote-code` y `--mamba_ssm_cache_dtype float32`; incluye NVIDIA Open Model License.
- [Referencia vLLM v0.10.1 para `serve`](https://docs.vllm.ai/en/v0.10.1/cli/serve.html) y [health endpoint](https://docs.vllm.ai/en/v0.10.1/api/vllm/entrypoints/openai/api_server.html).
- [Precios de Persistent Disk en us-central1](https://cloud.google.com/compute/disks-image-pricing): precio bruto de referencia del PVC, antes de descuentos/créditos.
- [Guía de GPU en GKE Standard](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/gpus).
- [Persistent volumes en GKE](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/persistent-volumes) y [driver CSI de discos persistentes](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/gce-pd-csi-driver): `standard-rwo`, `pd-balanced`, `ReadWriteOnce`, aprovisionamiento dinámico y `WaitForFirstConsumer`.
- Decisiones locales de arquitectura y parámetros: [tech.md](../../tech.md), [README](../../../README.md) y [validación de infraestructura](../01-infra-base/validation.md).

## Protocolo automatizado de revisión (grupos 2 y 3)

SRV-09 se comprueba separando contrato de API y contenido: HTTP exitoso, contenido no vacío, final natural `stop`; SSE requiere fragmentos y `[DONE]`; SDK se comprueba por separado. `length` sigue siendo fallo de finalización. Los casos de contenido en `scripts/serving-validation-cases.json` registran FP8, aritmética y capital de Francia con modo `/no_think`, temperatura 0 y límite de 128 tokens. Son diagnósticos acotados para revisión humana; no equivalen a evaluación general del modelo. Una comparación correcta con FP16 no se rechaza por mencionar ese término: se requiere responder sobre FP8.

SRV-02 compara revisiones y hashes publicados del checkpoint y configuración cacheada; la selección nativa de vLLM se inspecciona en un proceso independiente, con ese límite explícito. SRV-13–SRV-15 comparan PVC/PV y SHA256 completos antes/después de recuperar; muestreo cada cinco segundos no prueba ausencia absoluta de solapamiento entre muestras. Mediciones anteriores al pull que no existan se mantienen pendientes, sin reconstruirlas como observaciones.

## Comparación final autorizada por el propietario

Tras la ejecución base `/no_think` con 128 tokens, ejecutar una sola comparación `/think` con `max_tokens=2048`, temperatura 0.6 y top_p 0.95; conservar las mismas preguntas y criterios de contenido. Evaluar formato/contenido sobre la respuesta final después de `</think>`, conservando el texto completo como evidencia. Mantener `stop` y cierre SSE como criterios técnicos. No cambiar Deployment ni recrear de nuevo el pod. No encadenar más variantes: consolidar ambos reportes y presentar bloqueos para revisión humana antes de entregar 02. Parámetros de razonamiento basados en la [ficha oficial NVIDIA](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8).

## Aceptación de cierre

El propietario aprobó la revisión y dio por cerrada la entrega 02 el 2026-10-04. Aceptó expresamente SRV-05, SRV-10 y SRV-11 PARCIAL y los fallos de calidad FP8/aritmética como limitaciones documentadas de esta fase. Se conservan estados, respuestas, códigos de salida y límites originales; la aceptación no convierte FAIL/PARCIAL en PASS ni determina la causa de la mala inferencia.

Esta aceptación es una excepción explícita del propietario a la puerta de cierre que exigía todos los criterios completos. Los criterios técnicos y las comprobaciones automatizadas permanecen; no se ajustan para producir PASS. Entrega 03 habilitada como siguiente trabajo, sin implementarla en este cierre.
