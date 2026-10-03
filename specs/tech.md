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
| Acceso de administración | Endpoint público de control GKE con Master Authorized Networks restringido a la IP dinámica del operador; proporcionar el CIDR `/32` al preparar cada plan, sin guardarlo en archivos versionables; `kubectl` directo, sin VPN ni bastion |
| Acceso de cargas | Service `ClusterIP` interno y `kubectl port-forward`; sin LoadBalancer público, alta disponibilidad ni escalado automático inicial |
| Modelo | `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8`; inferencia de texto |
| Ciclo | Terraform para infraestructura, limpieza de cargas antes de `terraform destroy` |
| Salida de nodos | IPv4 externas efímeras en los dos nodos para descargar imágenes y pesos; sin Cloud NAT inicial (decisión del propietario, 2026-10-03) |
| Estado Terraform | Backend local en este equipo, en `.local/terraform-state/` bajo la raíz del repositorio y excluido de Git; conservar hasta verificar `destroy` (decisión del propietario, 2026-10-03) |

## Línea base propuesta, todavía no validada

- **GKE:** canal Stable, parche candidato `1.35.6-gke.1250000` disponible en `us-central1-a` al consultar el proyecto el 2026-10-03. La [tabla pública de GKE](https://docs.cloud.google.com/kubernetes-engine/docs/release-notes) asocia ese parche predeterminado a `cos-125-19216-395-109`; la [lista de drivers de esa imagen COS para L4](https://storage.googleapis.com/cos-tools/19216.395.109/lakitu/gpu_driver_versions.textproto) etiqueta `580.159.04` como `DEFAULT`. Elegir instalación administrada `DEFAULT`; comprobar imagen y driver reales en el nodo antes de considerarlos validados. No instalar en paralelo drivers manuales y administrados.
- **vLLM:** usar `v0.10.1` como primer candidato porque NVIDIA lo documenta para este checkpoint. Hay versiones posteriores; cambiar de versión exige repetir la prueba de carga del modelo y API. Fijar imagen por digest y revisión del modelo después de validarlas.
- **Serving inicial:** una GPU, `--mamba_ssm_cache_dtype float32`, `--max-model-len 4096`, `--max-num-seqs 1` y `--gpu-memory-utilization 0.90`, según el README. Los parámetros son un punto de partida, no una capacidad garantizada. Validar la sintaxis con la imagen elegida.
- **Almacenamiento:** discos de arranque `pd-balanced` de 50 GB en ambos pools. Si la imagen de vLLM y los pesos saturan el nodo GPU, evaluar 80–100 GB `pd-balanced` mediante cambio revisado; no se aumenta preventivamente.

## Hipótesis por validar

- El checkpoint FP8 carga y responde correctamente en una L4 con la combinación de imagen, CUDA y driver seleccionada.
- El espacio del nodo y la ruta de descarga/caché permiten recrear el modelo sin conservar volúmenes facturables.
- El propietario informó, tras consultar `gcloud`, cuota regional activa de una L4 y oferta del acelerador en `us-central1-a/b/c`. Esta conversación no conserva la salida de esos comandos. La cuota no reserva capacidad física: se observará al crear el nodo en `us-central1-a`.
- Las estimaciones de pesos, KV y estado Mamba del README caben en la VRAM observada; latencia y throughput pueden limitar la concurrencia antes que la memoria.

## Conflictos y decisiones pendientes

1. Comprobar en un nodo la imagen COS y el driver realmente instalados para el parche candidato; después probar la compatibilidad con el digest de vLLM y la revisión del modelo que se fijen. La línea base propuesta todavía no es una combinación probada.
2. Confirmar la IP pública dinámica del operador antes de cada plan de GKE y pasar el CIDR `/32` como entrada no versionada. No abrir `0.0.0.0/0`.
3. Verificar la descarga real de imagen y pesos por las IPv4 efímeras, la gestión de caché y los permisos mínimos. Proteger el estado local con permisos de archivo restrictivos y conservarlo hasta comprobar la limpieza.
4. Elegir tecnología de backend/interfaz y umbrales de latencia, errores y duración para las pruebas de concurrencia.

## Observaciones del Grupo 0 (2026-10-02)

- Las consultas de solo lectura confirmaron facturación habilitada, cuota regional `NVIDIA_L4_GPUS` 1/0 usada, `E2_CPUS` 24/0, `CPUS` 200/0 e `IN_USE_ADDRESSES` 8/0 en `us-central1`. `gcloud compute accelerator-types list` devolvió `nvidia-l4` para `us-central1-a`. La oferta y la cuota no prueban capacidad física disponible al crear el nodo.
- `compute.googleapis.com` estaba habilitada. `container.googleapis.com` estaba deshabilitada el 2026-10-02 y se habilitó el 2026-10-03 con autorización del propietario, sin crear clústeres. La consulta zonal posterior confirmó el parche Stable `1.35.6-gke.1250000`.
- GKE publica `cos-125-19216-395-109` para ese parche y COS lista `580.159.04` como driver `DEFAULT` para L4. Es una correspondencia documental, no una versión observada en un nodo. Supera la referencia conservadora R570 para CUDA 12.8; la compatibilidad con vLLM continúa como hipótesis hasta la prueba real.
- El repositorio del modelo muestra aproximadamente 10.3 GB de archivos. Los 50 GB del disco GPU son una hipótesis inicial: faltan tamaño descomprimido de la imagen OCI, caché de descarga, espacio del sistema y medición en el nodo. No se aumenta el disco sin evidencia ni plan revisado.

Las fuentes, comandos y estimación de costo del Grupo 0 están en [su evaluación](deliveries/01-infra-base/group-0.md). La salida y el estado se decidieron el 2026-10-03; el CIDR dinámico se pasará como entrada no versionada antes de cada plan.

## Diseño de red y estado del Grupo 1 (2026-10-03)

- Crear la VPC `nemotron-lab-vpc` en modo personalizado, con una sola subred `nemotron-lab-us-central1` en `us-central1`. La red `default` existente no se modifica.
- Rangos elegidos: primario de nodos `10.80.0.0/20`, secundario `nemotron-pods` `10.81.0.0/20` y secundario `nemotron-services` `10.82.0.0/22`. Los dos secundarios se reservarán explícitamente para un clúster VPC-native en el Grupo 2. El inventario de 42 subredes del proyecto no mostró solapamientos; no se conoce el direccionamiento de redes externas al proyecto.
- Usar el backend Terraform local en `.local/terraform-state/` con permisos `0700`, sin archivos de estado ni planes en Git. El directorio de trabajo futuro será `terraform/infra`; el backend apuntará a `../../.local/terraform-state/terraform.tfstate`. El archivo `.terraform.lock.hcl` se versionará para fijar el provider.
- `compute.googleapis.com` y `container.googleapis.com` están habilitadas. La prueba `projects.testIamPermissions` concedió los permisos principales para API, VPC, subred, firewall, clúster y cuentas de servicio. No se conceden roles nuevos en el Grupo 1; los permisos se comprobarán de nuevo si cambian las credenciales o el diseño.

Este diseño no agrega Cloud NAT ni recursos de GKE en el Grupo 1. La red y la subred no tienen un cargo horario identificado en la [tabla de red](https://cloud.google.com/vpc/network-pricing); tráfico y futuros nodos/IP sí pueden generar cargos. No se hará `apply` sin revisión previa.

La configuración del Grupo 1 fija `hashicorp/google` `7.46.1` y produjo un plan local de una VPC y una subred (`2 to add, 0 to change, 0 to destroy`), descrito en [group-1.md](deliveries/01-infra-base/group-1.md). No se aplicó.

## Criterios técnicos de validación

Comprobar nodos Ready, `nvidia.com/gpu: 1`, colocación de pods, carga del modelo, respuesta mediante SDK y chat, streaming, historial y errores. Registrar VRAM en reposo y durante prefill/generación, primer token, p50/p95, tokens/s, cola y concurrencia sostenida. Verificar después la eliminación de cargas y recursos facturables. Los resultados reales irán en `specs/deliveries/<entrega>/validation.md`.
