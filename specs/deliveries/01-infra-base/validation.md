# 01 — Infraestructura base: validación

**Estado general:** APROBADA OPERATIVAMENTE para avanzar a la entrega 02 por decisión expresa del propietario (2026-10-04). INF-01–INF-06, INF-08 e INF-09 tienen evidencia PASS. INF-07 queda pendiente y transferido a la comprobación de descarga/caché del modelo en serving; INF-10 queda pendiente para el cierre final del laboratorio. La infraestructura permanece desplegada por instrucción expresa durante la sesión continua. INF-02 también tiene evidencia PASS posterior al despliegue.

## Registro de evidencia por requisito

| ID | Comprobación prevista | Evidencia que se conservará | Estado |
|---|---|---|---|
| INF-01 | Confirmar proyecto, `us-central1-a`, facturación, cuota y oferta G2/L4 antes del plan. | Facturación `True` el 2026-10-02 y cuotas/oferta reconfirmadas el 2026-10-03. El 2026-10-04 el clúster del proyecto/zona previstos está RUNNING; el nodo GPU Ready anuncia una GPU asignable y Compute identifica una `nvidia-l4`. La capacidad física quedó observada en esta sesión, sin garantizar disponibilidad futura. | PASS |
| INF-02 | Comparar red prevista con recursos existentes y plan Terraform. | 2026-10-03: inventario sin solapamientos conocidos y plan de VPC/subred. El 2026-10-04, `gcloud compute networks describe` confirmó `nemotron-lab-vpc` con `autoCreateSubnetworks: false`; `subnets describe` confirmó `nemotron-lab-us-central1`, primario `10.80.0.0/20`, secundarios `nemotron-pods` `10.81.0.0/20` y `nemotron-services` `10.82.0.0/22`. Redes externas al proyecto siguen fuera del inventario. | PASS |
| INF-03 | Revisar plan y consultar versión e imagen de nodos GKE. | 2026-10-04, salida del propietario: clúster `nemotron-lab` RUNNING, canal STABLE y control `1.35.6-gke.1250000`; dos nodos Ready con la misma versión, Container-Optimized OS y containerd `2.1.7`; ambos pools reportan `COS_CONTAINERD`. [Detalle](group-3.md). | PASS |
| INF-04 | Consultar pool y nodo CPU. | 2026-10-04, salida del propietario: nodo `gke-nemotron-lab-cpu-9c917b27-6bgj` Ready; pool `cpu` RUNNING, `e2-standard-4`, `COS_CONTAINERD`, `pd-balanced` 50 GB y versión `1.35.6-gke.1250000`. Falta inventario independiente del disco en Compute; su uso corresponde a INF-07. | PASS |
| INF-05 | Consultar pool y nodo GPU. | 2026-10-04, salida del propietario: nodo `gke-nemotron-lab-gpu-3c0bdecc-bxn9` Ready; pool `gpu` RUNNING y `g2-standard-4`; `nvidia.com/gpu` asignable = 1. Compute reporta `guestAccelerators` con una `nvidia-l4`; el pod diagnóstico observó `NVIDIA L4` y 23034 MiB. | PASS |
| INF-06 | Revisar configuración de driver y atributos del nodo. | 2026-10-04: nodo GPU con `workload=gpu` y taint observado `dedicated=gpu:NoSchedule`; Terraform configura driver administrado `DEFAULT`. El pod diagnóstico ejecutó `nvidia-smi` y observó driver `580.159.04` con NVIDIA L4. No se instaló driver manual ni GPU Operator en los manifiestos de esta entrega; no se adjuntó inventario completo de pods del sistema. | PASS |
| INF-07 | Revisar tipo y tamaño de discos, uso y caché prevista. | 2026-10-04: ambos pools reportan boot disk `pd-balanced` de 50 GB. Compute confirmó que el disco GPU es `pd-balanced` de 50 GB; dentro del pod GPU, `df -h /` mostró overlay de 46G, 21G usados y 25G disponibles (46%). La ruta y el uso de caché tras descargar el modelo siguen pendientes. | PENDIENTE |
| INF-08 | Probar acceso administrativo e inventariar Services. | 2026-10-04: `kubectl` devolvió nodos y Services; ninguno es `LoadBalancer` (hay un NodePort `default-http-backend` de `kube-system`). El propietario confirmó que `masterAuthorizedNetworksConfig` contiene únicamente su CIDR vigente `/32`, con `gcpPublicCidrsAccessEnabled: false`; el valor concreto se omite. | PASS |
| INF-09 | Revisar plan y costo antes de aplicar. | Plan `7 to add` y estimación bruta USD 0.964554116/h; 30 min USD 0.482277058, más consumo variable y posible pool transitorio. El propietario indicó el 2026-10-03: «Plan y estimación de costos revisados y aprobados». [Grupo 2](group-2.md). Reconfirmar entradas dinámicas antes de aplicar. | PASS |
| INF-10 | Inspeccionar cierre Kubernetes, destrucción e inventario final. | Salida resumida del plan de destrucción, estado final e inventario de clúster, pools, discos, IP, redes y remanentes. | PENDIENTE |

## Formato para cada ejecución

```text
ID:
Fecha/hora y zona:
Comando o fuente:
Resultado observado:
Evidencia (archivo/enlace/fragmento sin secretos):
Estado: PENDIENTE | PASS | FAIL | BLOQUEADO
Limitaciones y siguiente acción:
```

## Reglas de evaluación

- `terraform fmt -check`, `validate` y `plan` comprueban archivos y propuesta; no demuestran nodos Ready ni GPU utilizable.
- La cuota de una L4 informada por el propietario no confirma disponibilidad al momento de crear el nodo.
- Un `apply` exitoso no demuestra instalación del driver ni `nvidia.com/gpu` asignable. Requiere evidencia del nodo real.
- No declarar limpieza completa solo por `terraform destroy`: comprobar recursos creados por controladores y cualquier recurso fuera del estado.
- No guardar credenciales, tokens, prompts, estado Terraform ni planes en el repositorio.

## Comprobaciones locales del Grupo 0 — 2026-10-02

| Comprobación | Resultado observado | Límite |
|---|---|---|
| `git diff --check` | Salida vacía, código de salida 0. | Comprueba espacios en archivos seguidos por Git; no valida arquitectura ni recursos. |
| Recálculo con `python3 -c` de las cinco tarifas de [group-0.md](group-0.md) | `subtotal=0.954554116 con_ipv4=0.964554116 media_hora=0.482277058`. | Tarifas públicas aproximadas; no incluye consumo variable ni descuentos de la cuenta. |
| `git status --short` | Los cambios ajenos iniciales `AGENTS.md` y `README.md` se conservaron. | No existe configuración Terraform; `fmt`, `validate` y `plan` no aplican aún. |

No se ejecutó `terraform apply` ni se creó infraestructura. Kubernetes Engine API se habilitó el 2026-10-03 con autorización expresa para consultar versiones. Las limitaciones del Grupo 0 constan en [group-0.md](group-0.md).

## Decisiones y comprobaciones locales — 2026-10-03

| Comprobación | Resultado observado | Límite |
|---|---|---|
| Decisiones del propietario | IPv4 efímeras en nodos; estado local fuera de Git; sesión de 30 minutos. | No equivalen a revisión de un plan Terraform ni autorizan `apply`. |
| `git check-ignore -v` para estado, `.terraform/`, plan y `.tfvars` | Cada ruta de prueba coincidió con una regla de `.gitignore`. | No se ha creado estado ni plan real. |
| `stat -f '%Sp %N' .local .local/terraform-state` | Ambos directorios `drwx------` (`0700`). | En Grupo 1 se deberá usar `umask 077` al crear archivos de estado y planes. |
| `git diff --check` | Salida vacía, código de salida 0. | No comprueba archivos nuevos sin seguimiento ni la seguridad de la infraestructura. |
| `python3 -c` con `ipaddress.ip_network(<CIDR recibido>, strict=True)` | Una dirección IPv4 con prefijo `/32`; valor omitido de la documentación. | Valida sintaxis, no confirma que sea la IP de salida vigente del operador. |
| `gcloud projects get-iam-policy` y `gcloud auth list`, comparados sin exponer la identidad | No apareció un rol directo del usuario activo en la política del proyecto. | No descarta permisos heredados o por grupo. |
| `projects.testIamPermissions` sobre el proyecto | Concedidos: `serviceusage.services.enable`, `container.clusters.create`, `compute.networks.create`, `compute.subnetworks.create`, `compute.firewalls.create`, `iam.serviceAccounts.create` e `iam.serviceAccounts.actAs`. | `container.nodePools.create` no es válido para probarlo contra el recurso proyecto. Grants pueden cambiar; no se crearon recursos. |
| `gcloud services enable container.googleapis.com` y consulta posterior de servicios habilitados | Operación terminada correctamente; `container.googleapis.com` aparece habilitada. | Habilitar API no valida nodos ni garantiza disponibilidad de L4. |
| `gcloud container get-server-config --zone=us-central1-a` | Stable `1.35.6-gke.1250000` predeterminada y válida. | Reconfirmar antes del plan; COS y driver efectivos requieren nodo. |
| Búsqueda del valor de la IP proporcionada en archivos del proyecto | Sin coincidencias después de retirarla; no se hizo commit de ese valor. | El plan y estado Terraform locales contendrán el CIDR cuando se cree el clúster; mantenerlos fuera de Git. |

## Comprobaciones locales del Grupo 1 — 2026-10-03

| Comprobación | Resultado observado | Límite |
|---|---|---|
| Inventario `gcloud compute networks`, `subnets` y `routes`; comparación de intervalos IPv4 | Una VPC `default` en modo automático, 42 subredes, ninguna secundaria; cero solapamientos con los tres CIDR propuestos. | Redes externas al proyecto no inventariadas. |
| `terraform fmt -check` y `terraform validate -no-color` | Ambos terminaron con código 0; `validate` indicó `Success! The configuration is valid.` | Comprobación local, sin recursos. |
| `terraform init -input=false` | Backend local inicializado y provider Google `7.46.1` instalado; lock file creado. | La primera ejecución falló por DNS del sandbox; la repetición autorizada pasó. |
| `terraform plan -input=false -no-color -out=../../.local/terraform-state/group-1.tfplan` | `Plan: 2 to add, 0 to change, 0 to destroy`: VPC `nemotron-lab-vpc` y subred `nemotron-lab-us-central1` con primario y dos secundarios previstos. | El primer intento carecía de ADC; la repetición pasó con token temporal de `gcloud` en memoria. No se aplicó. |
| `stat` y `git check-ignore` | Directorio del plan `0700`, plan `0600` y ruta ignorada por Git. | Reconfirmar antes de futuras operaciones; no guardar token, plan ni estado en Git. |

## Comprobaciones locales del Grupo 2 — 2026-10-03

| Comprobación | Resultado observado | Límite |
|---|---|---|
| `terraform fmt -check -diff`, `terraform validate -no-color`, `git diff --check` | Formato y diff sin observaciones; `Success! The configuration is valid.` | No demuestra que GCP pueda crear nodos. |
| `gcloud container get-server-config`, consultas de APIs, cuota y oferta zonal | Stable `1.35.6-gke.1250000` válida; Compute, Container e IAM habilitadas; L4 0/1 y oferta `nvidia-l4` en `us-central1-a`. | Cuota y catálogo no reservan capacidad; versión del nodo aún desconocida. |
| `terraform plan -input=false -no-color -out=../../.local/terraform-state/group-2.tfplan` | `7 to add, 0 to change, 0 to destroy`; contenido resumido en [group-2.md](group-2.md). | Plan sin `apply`; el CIDR dinámico debe refrescarse antes de cualquier despliegue. |
| Inspección del JSON local del plan | Un clúster zonal y dos pools de un nodo; CPU E2, GPU G2/L4, ambos COS y `pd-balanced` 50 GB; GPU `DEFAULT` y taint previsto; un solo CIDR `/32`, sin acceso adicional desde IP públicas de GCP. | No prueba driver, GPU asignable, espacio real ni acceso `kubectl`. |
| Permisos de archivos locales | Plan, log y JSON `0600`, bajo `.local/terraform-state/` ignorado por Git. | Proteger y conservar futuros archivos de estado hasta terminar la limpieza. |

El primer intento del plan falló por ruta de `gcloud` ausente en el `PATH` del proceso; el segundo pasó con la ruta absoluta. La primera lectura JSON dentro del sandbox no pudo iniciar el provider; se repitió fuera del sandbox. No se ejecutó `apply`; INF-03–INF-08 siguen PENDIENTE como requisitos completos. El propietario aprobó el plan y costo el 2026-10-03, cumpliendo la revisión exigida por [AGENTS.md](../../../AGENTS.md).

## Comprobaciones del Grupo 3 — 2026-10-04

### Decisión de almacenamiento para la Entrega 02 (histórico)

Tras considerar inicialmente aumentar el boot disk GPU, el propietario decidió conservar el disco actual `pd-balanced` de 50 GB y usar un PVC independiente `pd-balanced` de 50 GiB para pesos/cache. La decisión evita modificar el node pool con `SURGE maxSurge=1` ante cuota de una L4. En esa decisión inicial el PVC aún no estaba creado. Posteriormente se autorizó y desplegó el PVC de 50 GiB y el propietario amplió directamente el boot disk GPU a 100 GB. La plantilla del pool conserva 50 GB; Terraform declara 100 GB para nuevos pools e ignora cambios de ese campo en el pool existente para evitar surge. Evidencia y límites aceptados en la entrega 02, cerrada el 2026-10-04; INF-07 conserva la limitación de ocupación OCI/medición previa al pull (SRV-10 PARCIAL), no se atribuye un PASS nuevo.

### Despliegue y resultados operativos

| ID | Fuente | Resultado observado | Estado | Limitación y siguiente acción |
|---|---|---|---|---|
| INF-01–INF-08 | Salida de `terraform apply` compartida por el propietario el 2026-10-04 | `google_container_node_pool.cpu: Creation complete after 1m2s` y `Apply complete! Resources: 7 added, 0 changed, 0 destroyed.` El estado local existe con permisos `0600`. | PENDIENTE en ese momento; resultados posteriores completan la validación | Esta fila conserva la evidencia del apply; la validación posterior por requisito está resumida arriba. No compartir estado Terraform ni CIDR concreto. |
| INF-06–INF-07 | Primer intento de `kubectl logs pod/gpu-infra-check` compartido por el propietario | Exit Code 127: `/bin/sh: 1: nvidia-smi: not found`. | FAIL en el primer intento, corregido | El contenedor no tenía la ruta del binario en PATH. Se corrigió el diagnóstico para usar la utilidad del host montada por GKE; el segundo intento confirmó driver y GPU. El fallo inicial no indica un fallo del driver. |
| INF-05–INF-07 | Segundo pod diagnóstico y `gcloud compute instances describe` compartidos por el propietario | `NVIDIA L4, 580.159.04, 23034 MiB`; overlay 46G, 21G usados, 25G disponibles. Compute: `g2-standard-4`, disco 50 GB y una `nvidia-l4`. | PASS para GPU/driver; INF-07 transferido | La observación inicial de disco precede a la descarga del modelo. Tipo `pd-balanced`, eliminación del pod y red autorizada se confirmaron en las salidas posteriores. |
| INF-07–INF-08 | Consultas de GKE/Compute y comprobación de Kubernetes compartidas por el propietario el 2026-10-04 | `gpu-infra-check` eliminado (`No resources found in default namespace`); Master Authorized Networks contiene solo el CIDR `/32` vigente del operador y `gcpPublicCidrsAccessEnabled: false`; el disco GPU en Compute es `pd-balanced` de 50 GB. | INF-08 PASS; INF-07 PENDIENTE | La IP concreta se omitió. Falta observar la caché y el espacio tras descargar el modelo; la eliminación del pod diagnóstico sí quedó confirmada. |
| INF-02 | Salidas de `gcloud compute networks describe` y `networks subnets describe` compartidas por el propietario el 2026-10-04 | VPC `nemotron-lab-vpc` en modo personalizado; subred `nemotron-lab-us-central1` con primario `10.80.0.0/20`, Pods `10.81.0.0/20` y Services `10.82.0.0/22`, con los nombres previstos. | PASS | Confirma los recursos del proyecto después del despliegue; no inventaría redes externas. |

Las filas siguientes documentan comprobaciones **anteriores** al `apply`; sus estados BLOQUEADO describen aquel momento y no son el estado actual.

| ID | Comando o fuente | Resultado observado | Estado | Limitación y siguiente acción |
|---|---|---|---|---|
| INF-03–INF-08 | `gcloud container clusters list --project=llmresearch-510422 --zone=us-central1-a` y `gcloud container clusters describe nemotron-lab` | La lista no mostró clústeres y la consulta por nombre devolvió 404. [Detalle y procedimiento](group-3.md). | BLOQUEADO para validación operativa | No existen nodos que permitan observar Ready, discos, imagen, driver, GPU o acceso `kubectl`. Reconfirmar el CIDR dinámico y revisar el plan efectivo antes de que el propietario ejecute Terraform; luego realizar 3.1–3.4. |
| INF-03–INF-08 | Nueva ejecución de `gcloud container clusters describe nemotron-lab --project=llmresearch-510422 --zone=us-central1-a --format=json`, 2026-10-04 15:51 Guatemala | GKE devolvió 404: `No cluster named 'nemotron-lab' in llmresearch-510422`. No hay archivo `terraform.tfstate` en `.local/terraform-state/`; solo planes y registros locales previos. | BLOQUEADO para validación operativa | El 404 comprueba la ausencia del clúster esperado en esa zona, no un inventario completo de recursos. No se obtuvieron credenciales ni se ejecutaron comandos sobre nodos. |
| INF-07 | Configuración del pool en el plan del Grupo 2 | Discos solicitados de 50 GB; uso real y ruta de caché no medidos. | PENDIENTE | Requiere inspección del nodo o pod diagnóstico después del despliegue. |
| INF-09 | Aprobación registrada el 2026-10-03 | Plan y costo de entonces aprobados. | PASS | La revisión previa debe repetirse si cambian entradas, versión, zona, recursos o costo del plan efectivo. |

En la consulta previa al `apply` no se ejecutaron comandos de Terraform y el clúster aún no existía. La evidencia posterior registrada arriba confirma la aprobación operativa de la entrega 01. INF-07 sigue transferido a la prueba de descarga/caché del modelo; INF-10 queda pendiente para el cierre final del laboratorio y no se ejecuta durante esta sesión continua autorizada.
