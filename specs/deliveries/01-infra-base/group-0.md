# Grupo 0 — Entradas, compatibilidad y costo

**Consultas:** 2026-10-02 y 2026-10-03. **Decisiones del propietario:** 2026-10-03, America/Guatemala. **Estado:** Grupo 0 completado con límites documentados; sin despliegue ni plan Terraform.

## Evidencia local de prerrequisitos

Todas las consultas usaron `--project=llmresearch-510422` o el ID del proyecto como argumento; ninguna creó recursos.

| Entrada | Comando o fuente | Resultado observado | Límite |
|---|---|---|---|
| Facturación | `gcloud billing projects describe llmresearch-510422 --format='value(billingEnabled)'` | `True` | No verifica presupuesto o saldo. |
| Cuotas regionales | `gcloud compute regions describe us-central1 --project=llmresearch-510422 --format='json(quotas)'` | `NVIDIA_L4_GPUS`: límite 1, uso 0; `E2_CPUS`: 24/0; `CPUS`: 200/0; `IN_USE_ADDRESSES`: 8/0; `STATIC_ADDRESSES`: 8/0. | La cuota no reserva capacidad; reconsultar antes del plan. |
| Oferta zonal | `gcloud compute accelerator-types list --filter='name=nvidia-l4 AND zone:us-central1-a' --project=llmresearch-510422 --format='value(name,zone)'` | `nvidia-l4 us-central1-a` | Catálogo, no disponibilidad efectiva. |
| APIs | `gcloud services list --enabled --project=llmresearch-510422 --filter='config.name:(compute.googleapis.com container.googleapis.com)' --format='value(config.name)'` | El 2026-10-02 solo `compute.googleapis.com`. Tras autorización del propietario, `gcloud services enable container.googleapis.com --project=llmresearch-510422` terminó correctamente el 2026-10-03; la consulta posterior mostró `container.googleapis.com` habilitada. | No se creó clúster ni nodo. |
| Versiones GKE | `gcloud container get-server-config --zone=us-central1-a --project=llmresearch-510422 --format=json` | Canal Stable: versión predeterminada y válida `1.35.6-gke.1250000`. | Reconfirmar disponibilidad antes del plan; versión efectiva solo tras desplegar. |
| IAM de la cuenta activa | `gcloud projects get-iam-policy llmresearch-510422 --format='json(bindings)'`, comparado sin exponer la identidad con `gcloud auth list`; después `projects.testIamPermissions` para permisos específicos | Ningún rol directo visible. La prueba efectiva devolvió concedidos `serviceusage.services.enable`, `container.clusters.create`, `compute.networks.create`, `compute.subnetworks.create`, `compute.firewalls.create`, `iam.serviceAccounts.create` e `iam.serviceAccounts.actAs`. | `container.nodePools.create` no es válido en el recurso proyecto para esta prueba; comprobar la creación del pool en el plan y despliegue futuros. Los permisos pueden cambiar. |

## Compatibilidad y espacio

- [Notas de GKE](https://docs.cloud.google.com/kubernetes-engine/docs/release-notes): el parche Stable candidato `1.35.6-gke.1250000` corresponde públicamente a `cos-125-19216-395-109`. La consulta del proyecto confirmó el parche como válido en `us-central1-a`.
- [GPU en GKE](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/gpus) y [lista de drivers de COS para esa imagen](https://storage.googleapis.com/cos-tools/19216.395.109/lakitu/gpu_driver_versions.textproto): instalación administrada; para L4, `DEFAULT` aparece como `580.159.04`. Es versión prevista, no observada. No se instalará un segundo driver manual ni GPU Operator.
- [Notas CUDA 12.8](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-toolkit-release-notes/index.html): R570 es la referencia de driver de CUDA 12.8. La compatibilidad efectiva de vLLM y L4 requiere prueba posterior.
- [Archivos del modelo](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8/tree/main): repositorio de aproximadamente 10.3 GB. Con 50 GB de boot disk GPU queda una diferencia aritmética de 39.7 GB antes de sistema, imagen OCI, caché temporal y logs; **no es espacio libre medido**. Mantener 50 GB y comprobar `df` y la caché real antes de servir el modelo.

## Estimación bruta para revisión

Tarifas públicas en USD de pago por uso para Iowa (`us-central1`), consultadas el 2026-10-02. Es una estimación, no una cotización de la cuenta ni costo observado.

| Recurso previsto | Cantidad | USD/h aproximados | Fuente |
|---|---:|---:|---|
| `g2-standard-4`, L4 incluida | 1 | 0.706832276 | [G2](https://cloud.google.com/products/compute/pricing/accelerator-optimized) |
| `e2-standard-4` | 1 | 0.134022840 | [E2](https://cloud.google.com/products/compute/pricing/general-purpose) |
| Gestión de clúster GKE | 1 | 0.100000000 | [GKE](https://cloud.google.com/kubernetes-engine/pricing) |
| Boot disks `pd-balanced` de 50 GiB | 2 | 0.013699000 | [Discos](https://cloud.google.com/compute/disks-image-pricing) |
| **Subtotal identificable** | | **0.954554116** | Suma aritmética; sin créditos. |
| IPv4 externas efímeras, una por nodo según la decisión | 2 | 0.010000000 | [VPC](https://cloud.google.com/vpc/network-pricing) |

La decisión del propietario es usar dos IPv4 externas efímeras; el subtotal identificable pasa a **USD 0.964554116/h**. Para la duración máxima de **30 minutos** indicada por el propietario, el subtotal es **USD 0.482277058** antes de tráfico, logs y otros cargos variables. Este límite de tiempo no autoriza un despliegue. Los posibles créditos de gestión GKE se descuentan por separado si la cuenta resulta elegible; no se suponen. El precio de G2 ya incluye la L4 y no debe sumarse una segunda tarifa GPU.

## Decisiones y comprobaciones pendientes

| Punto | Situación | Siguiente comprobación |
|---|---|---|
| CIDR del operador | El propietario proporcionó un CIDR `/32` dinámico el 2026-10-03; se validó como una sola IPv4 y se retiró su valor de los archivos versionables a petición del propietario. | Reconfirmar desde la red de `kubectl` inmediatamente antes de cada plan y pasarlo como `TF_VAR_operator_cidr` en el entorno del proceso, sin escribirlo en documentos o `.tfvars` versionables; nunca `0.0.0.0/0`. El plan y el estado local contendrán el valor y deben permanecer fuera de Git. |
| Salida de nodos | Decididas IPv4 externas efímeras en ambos nodos; no Cloud NAT inicial. | Comprobar descarga de imagen OCI y Hugging Face en una sesión futura; no abrir entrada pública a la inferencia. |
| Estado Terraform | Decidido backend local en `.local/terraform-state/`, excluido de Git. Directorio creado con modo `0700`; crear archivos con `umask 077`. | Configurar backend en Grupo 1, preservar estado hasta terminar `destroy` y comprobar limpieza. Si el equipo pierde el estado, la recuperación requerirá inventario/importación o limpieza manual. |
| Permisos | Prueba efectiva de permisos de creación principales concedidos en el proyecto; no fue posible probar `container.nodePools.create` en el recurso proyecto. | Repetir antes del despliegue si cambian los grants y comprobar recursos concretos en el plan. La [guía GKE](https://docs.cloud.google.com/kubernetes-engine/docs/quickstarts/create-cluster) enumera Compute Admin, Kubernetes Engine Admin y Service Account User para crear clúster; [Service Usage Admin](https://docs.cloud.google.com/iam/docs/creating-custom-roles) permite habilitar APIs. No se concedieron roles nuevos. |
| GKE API y versión | API habilitada con autorización del propietario; parche Stable candidato y correspondencia pública COS/driver registrados. | Reconfirmar versiones antes del plan y observar COS/driver efectivos en el nodo. |
| Presupuesto de sesión | Duración máxima de 30 minutos indicada por el propietario; subtotal calculado con dos IPv4 externas. | Revisar costo completo y definir una alerta de presupuesto antes del despliegue facturable. |

**Puerta del Grupo 1:** releer los requisitos y comparar los rangos propuestos con el inventario de redes existente. El CIDR dinámico se obtiene antes de cada plan y queda fuera de Git. La compatibilidad real del parche/driver queda para el nodo futuro. Ningún `terraform apply` está autorizado por esta evaluación.
