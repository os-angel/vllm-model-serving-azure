# 01 — Infraestructura base: validación

**Estado general:** PENDIENTE. El Grupo 0 se completó con consultas y estimación documentadas el 2026-10-02 y 2026-10-03. No hay Terraform ni infraestructura desplegada desde esta entrega. Ningún requisito completo está aprobado.

## Registro de evidencia por requisito

| ID | Comprobación prevista | Evidencia que se conservará | Estado |
|---|---|---|---|
| INF-01 | Confirmar proyecto, `us-central1-a`, facturación, cuota y oferta G2/L4 antes del plan. | 2026-10-02: facturación `True`; L4 1/0, E2 24/0, CPU 200/0, IP en uso 8/0; catálogo `nvidia-l4` en `us-central1-a`. Comandos y límites en [group-0.md](group-0.md). Faltan plan y capacidad efectiva. | PENDIENTE |
| INF-02 | Comparar red prevista con recursos existentes y plan Terraform. | 2026-10-03: inventario de una VPC `default` y 42 subredes; cálculo de cero solapamientos con `10.80.0.0/20`, `10.81.0.0/20`, `10.82.0.0/22`. Plan Terraform `2 to add`: VPC propia, subred y dos secundarios. Detalles en [group-1.md](group-1.md). Inventario posterior al despliegue pendiente. | PENDIENTE |
| INF-03 | Revisar plan y consultar versión e imagen de nodos GKE. | 2026-10-03: con `container.googleapis.com` habilitada por autorización del propietario, `get-server-config --zone=us-central1-a` devolvió `1.35.6-gke.1250000` como versión Stable predeterminada y válida. GKE publica `cos-125-19216-395-109` para ese parche. Plan y versión real del nodo pendientes. | PENDIENTE |
| INF-04 | Consultar pool y nodo CPU. | Un nodo Ready; tipo `e2-standard-4`, disco y pool observados. | PENDIENTE |
| INF-05 | Consultar pool y nodo GPU. | Un nodo Ready `g2-standard-4`; `nvidia.com/gpu: 1` asignable y salida de verificación GPU cuando esté disponible. | PENDIENTE |
| INF-06 | Revisar configuración de driver y atributos del nodo. | 2026-10-03: lista pública de `cos-125-19216-395-109` indica driver `DEFAULT` `580.159.04` para L4; supera referencia R570 para CUDA 12.8. Versión efectiva, taints y GPU asignable pendientes del nodo real. | PENDIENTE |
| INF-07 | Revisar tipo y tamaño de discos, uso y caché prevista. | 2026-10-02: modelo publicado de ~10.3 GB y cálculo de 50 GB en [group-0.md](group-0.md); imagen y espacio real desconocidos. Plan, disco y medición pendientes. | PENDIENTE |
| INF-08 | Probar acceso administrativo e inventariar Services. | 2026-10-03: propietario decidió IPv4 efímeras en nodos y comunicó un CIDR dinámico `/32`. Se validó que representa una dirección IPv4; su valor se retiró de los archivos versionables. Grupo 1 no agregó ingress ni LoadBalancer. Reconfirmar IP antes de cada plan; configuración y prueba de `kubectl` pendientes. | PENDIENTE |
| INF-09 | Revisar plan y costo antes de aplicar. | 2026-10-02: tarifas públicas consultadas; 2026-10-03: propietario eligió dos IPv4 efímeras y estado local. Subtotal USD 0.964554116/h; 30 min USD 0.482277058, sin variables de uso. Fuentes y límites en [group-0.md](group-0.md). Faltan plan y revisión previa a `apply`. | PENDIENTE |
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
