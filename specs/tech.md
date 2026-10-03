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
| Clúster | GKE Standard zonal; zona ya elegida por el propietario, identificador aún no registrado aquí |
| Nodos | Un pool CPU `e2-standard-4` y uno GPU `g2-standard-4` con una L4, según el README |
| Orquestación | Manifiestos Kubernetes versionados; vLLM en GPU y backend/interfaz en CPU |
| Acceso | Service `ClusterIP` interno y `kubectl port-forward`; sin VPN, alta disponibilidad ni escalado automático inicial |
| Modelo | `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8`; inferencia de texto |
| Ciclo | Terraform para infraestructura, limpieza de cargas antes de `terraform destroy` |

## Línea base propuesta, todavía no validada

- **GKE:** canal Stable 1.35 con `COS_CONTAINERD` y driver NVIDIA administrado. Elegir el parche disponible y comprobar que el driver real satisface la imagen de vLLM; R570 o posterior es el objetivo conservador para CUDA 12.8.1. No instalar en paralelo drivers manuales y administrados.
- **vLLM:** usar `v0.10.1` como primer candidato porque NVIDIA lo documenta para este checkpoint. Hay versiones posteriores; cambiar de versión exige repetir la prueba de carga del modelo y API. Fijar imagen por digest y revisión del modelo después de validarlas.
- **Serving inicial:** una GPU, `--mamba_ssm_cache_dtype float32`, `--max-model-len 4096`, `--max-num-seqs 1` y `--gpu-memory-utilization 0.90`, según el README. Los parámetros son un punto de partida, no una capacidad garantizada. Validar la sintaxis con la imagen elegida.
- **Almacenamiento:** 50 GB informados como tamaño inicial. Si «HDD» significa `pd-standard` para el nodo G2, entra en conflicto con la compatibilidad de G2; `pd-balanced` de 50 GB es la opción del README, sujeta a comprobar espacio para imagen, modelo y caché.

## Hipótesis por validar

- El checkpoint FP8 carga y responde correctamente en una L4 con la combinación de imagen, CUDA y driver seleccionada.
- El espacio del nodo y la ruta de descarga/caché permiten recrear el modelo sin conservar volúmenes facturables.
- La cuota informada de una L4 se aplica al proyecto y zona elegidos y hay capacidad disponible. Cuota aprobada no equivale a reserva de GPU.
- Las estimaciones de pesos, KV y estado Mamba del README caben en la VRAM observada; latencia y throughput pueden limitar la concurrencia antes que la memoria.

## Conflictos y decisiones pendientes

1. Registrar la **zona exacta** ya establecida y comprobar cuota, disponibilidad y versiones GKE ofrecidas allí.
2. Aclarar si «50G HDD» describe `pd-standard`, el disco de arranque GPU, ambos nodos o solo una restricción de tamaño. G2 no admite `pd-standard`.
3. Fijar parche GKE, versión efectiva COS, driver, digest de vLLM y revisión del modelo tras la comprobación de compatibilidad. La versión del README todavía no es una combinación probada.
4. Definir acceso de salida para descargar imagen y pesos, gestión de caché, permisos mínimos y ubicación del estado Terraform.
5. Elegir tecnología de backend/interfaz y umbrales de latencia, errores y duración para las pruebas de concurrencia.

## Criterios técnicos de validación

Comprobar nodos Ready, `nvidia.com/gpu: 1`, colocación de pods, carga del modelo, respuesta mediante SDK y chat, streaming, historial y errores. Registrar VRAM en reposo y durante prefill/generación, primer token, p50/p95, tokens/s, cola y concurrencia sostenida. Verificar después la eliminación de cargas y recursos facturables. Los resultados reales irán en `specs/deliveries/<entrega>/validation.md`.
