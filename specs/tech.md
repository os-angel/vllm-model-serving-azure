# Diseño técnico

Este archivo cumple la función de `techstack.md`. Distingue documentación comprobada, decisiones del laboratorio y puntos que aún requieren validación. No representa infraestructura ya desplegada.

## Hechos verificados en documentación

- GCP documenta que `g2-standard-4` tiene 4 vCPU, 16 GB de RAM y una L4 de 24 GB; la serie G2 admite FP8. No admite discos `pd-standard`; sí `pd-balanced` y `pd-ssd`. [G2 y discos compatibles](https://docs.cloud.google.com/compute/docs/accelerator-optimized-machines)
- GKE Standard admite pools GPU L4 y recomienda instalación automática de drivers en nodos COS. La versión efectiva del driver depende de la versión del nodo y debe comprobarse. [GPU en GKE](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/gpus)
- La ficha de NVIDIA documenta vLLM `>=0.10.1`, el ejemplo `vllm/vllm-openai:v0.10.1`, `--trust-remote-code` y `--mamba_ssm_cache_dtype float32`. [Ficha del modelo](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8)
- El [Dockerfile de vLLM v0.10.1](https://github.com/vllm-project/vllm/blob/v0.10.1/docker/Dockerfile) usa CUDA 12.8.1 por defecto e incluye arquitectura GPU 8.9. NVIDIA documenta la relación entre CUDA 12.8 y drivers de la serie R570, aunque existen reglas de compatibilidad menor con limitaciones. [Notas CUDA 12.8](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-toolkit-release-notes/index.html)
- Al revisar las [notas de GKE](https://docs.cloud.google.com/kubernetes-engine/docs/release-notes), 1.35 está disponible en el canal Stable. La versión exacta disponible en la zona y el driver asociado se verificarán antes de fijarlos.

## Decisiones confirmadas

| Componente | Decisión |
|---|---|
| Proyecto | `llmresearch-510422`, informado por el propietario |
| Clúster | GKE Standard en `us-central1-a`; `us-central1-b` o `us-central1-c` son alternativas solo tras revisar un plan nuevo |
| Nodos | Un pool CPU `e2-standard-4` y uno GPU `g2-standard-4` con una L4, según el README |
| Discos de arranque | `pd-balanced` de 50 GB para cada nodo; evaluar 80–100 GB en GPU si las pruebas muestran falta de espacio |
| Orquestación | Manifiestos Kubernetes versionados; vLLM en GPU y backend/interfaz en CPU |
| Acceso de administración | Endpoint público de control GKE con Master Authorized Networks restringido a la IP pública del operador; `kubectl` directo, sin VPN ni bastion |
| Acceso de cargas | Service `ClusterIP` interno y `kubectl port-forward`; sin LoadBalancer público, alta disponibilidad ni escalado automático inicial |
| Modelo | `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8`; inferencia de texto |
| Ciclo | Terraform para infraestructura, limpieza de cargas antes de `terraform destroy` |

## Línea base propuesta, todavía no validada

- **GKE:** canal Stable 1.35 con `COS_CONTAINERD` y driver NVIDIA administrado. Elegir el parche disponible y comprobar que el driver real satisface la imagen de vLLM; R570 o posterior es el objetivo conservador para CUDA 12.8.1. No instalar en paralelo drivers manuales y administrados.
- **vLLM:** usar `v0.10.1` como primer candidato porque NVIDIA lo documenta para este checkpoint. Hay versiones posteriores; cambiar de versión exige repetir la prueba de carga del modelo y API. Fijar imagen por digest y revisión del modelo después de validarlas.
- **Serving inicial:** una GPU, `--mamba_ssm_cache_dtype float32`, `--max-model-len 4096`, `--max-num-seqs 1` y `--gpu-memory-utilization 0.90`, según el README. Los parámetros son un punto de partida, no una capacidad garantizada. Validar la sintaxis con la imagen elegida.
- **Almacenamiento:** discos de arranque `pd-balanced` de 50 GB en ambos pools. Si la imagen de vLLM y los pesos saturan el nodo GPU, evaluar 80–100 GB `pd-balanced` mediante cambio revisado; no se aumenta preventivamente.

## Hipótesis por validar

- El checkpoint FP8 carga y responde correctamente en una L4 con la combinación de imagen, CUDA y driver seleccionada.
- El espacio del nodo y la ruta de descarga/caché permiten recrear el modelo sin conservar volúmenes facturables.
- El propietario informó, tras consultar `gcloud`, cuota regional activa de una L4 y oferta del acelerador en `us-central1-a/b/c`. Esta conversación no conserva la salida de esos comandos. La cuota no reserva capacidad física: se observará al crear el nodo en `us-central1-a`.
- Las estimaciones de pesos, KV y estado Mamba del README caben en la VRAM observada; latencia y throughput pueden limitar la concurrencia antes que la memoria.

## Conflictos y decisiones pendientes

1. Fijar parche GKE, versión efectiva COS, driver, digest de vLLM y revisión del modelo tras comprobar compatibilidad en `us-central1-a`. La línea base propuesta todavía no es una combinación probada.
2. Registrar la IP pública actual del operador como CIDR autorizado en el plan de GKE; si cambia, actualizar el plan antes de administrar el clúster. No abrir `0.0.0.0/0`.
3. Definir acceso de salida para descargar imagen y pesos, gestión de caché, permisos mínimos y ubicación del estado Terraform.
4. Elegir tecnología de backend/interfaz y umbrales de latencia, errores y duración para las pruebas de concurrencia.

## Criterios técnicos de validación

Comprobar nodos Ready, `nvidia.com/gpu: 1`, colocación de pods, carga del modelo, respuesta mediante SDK y chat, streaming, historial y errores. Registrar VRAM en reposo y durante prefill/generación, primer token, p50/p95, tokens/s, cola y concurrencia sostenida. Verificar después la eliminación de cargas y recursos facturables. Los resultados reales irán en `specs/deliveries/<entrega>/validation.md`.
