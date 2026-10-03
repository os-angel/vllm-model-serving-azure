# Grupo 2 — GKE y pools de nodos

**Fecha:** 2026-10-03, America/Guatemala. **Estado:** configuración y plan local completados; plan y estimación aprobados por el propietario el 2026-10-03. No se creó infraestructura.

## Diseño implementado

El plan usa el proyecto `llmresearch-510422` y la zona `us-central1-a`. Agrega `nemotron-lab` (GKE Standard zonal, canal Stable, parche `1.35.6-gke.1250000`) a la VPC y subred del Grupo 1, con rangos secundarios explícitos para Pods y Services. El pool predeterminado se elimina durante la creación. GKE puede crear un nodo transitorio de ese pool antes de retirarlo.

| Recurso | Configuración propuesta | Requisito |
|---|---|---|
| `google_container_cluster.lab` | VPC-native, endpoint público con un único CIDR IPv4 `/32` del operador en Master Authorized Networks; acceso adicional desde IP públicas de GCP deshabilitado; `deletion_protection=false`. | INF-03, INF-08 |
| `google_container_node_pool.cpu` | Un `e2-standard-4`, `COS_CONTAINERD`, boot disk `pd-balanced` 50 GB, etiqueta `workload=cpu`. | INF-04, INF-07 |
| `google_container_node_pool.gpu` | Un `g2-standard-4`, una `nvidia-l4`, instalación administrada `DEFAULT`, `COS_CONTAINERD`, boot disk `pd-balanced` 50 GB, etiqueta `workload=gpu`, taint `dedicated=gpu:NO_SCHEDULE`. | INF-05–INF-07 |
| `google_service_account.gke_nodes` y `google_project_iam_member.gke_node_role` | Cuenta exclusiva de nodos con `roles/container.defaultNodeServiceAccount`, rol mínimo documentado por GKE; ambos pools la usan. | INF-04–INF-06 |

Para serving, vLLM deberá seleccionar `workload=gpu`, solicitar `nvidia.com/gpu: 1` y tolerar `dedicated=gpu:NoSchedule`. Se comprobarán los taints efectivos antes de desplegarlo. Este grupo no instala driver manual, GPU Operator, NAT ni un LoadBalancer público.

## Comprobaciones observadas

| Comprobación | Resultado | Límite |
|---|---|---|
| `terraform fmt -check -diff`; `terraform validate -no-color` | Salida de formato vacía y `Success! The configuration is valid.` | Valida sintaxis y esquema, no capacidad GCP. El provider necesitó ejecutarse fuera del sandbox local. |
| `gcloud container get-server-config --zone=us-central1-a --project=llmresearch-510422` | Stable predeterminada y válida `1.35.6-gke.1250000`; `COS_CONTAINERD` aparece como imagen predeterminada. | Versión y driver efectivos requieren un nodo real. |
| `gcloud services list --enabled` para Compute, Container e IAM | Las tres APIs estaban habilitadas. | No prueba que la creación futura esté autorizada. |
| Cuotas regionales y catálogo de aceleradores | Uso/límite: L4 `0/1`, E2 CPU `0/24`, CPU `0/200`, direcciones en uso `0/8`; catálogo lista `nvidia-l4` en `us-central1-a`. | No reserva capacidad física. |
| `terraform plan -input=false -no-color -out=../../.local/terraform-state/group-2.tfplan` | `Plan: 7 to add, 0 to change, 0 to destroy`: VPC, subred, clúster, pools CPU/GPU, cuenta de servicio y vínculo IAM. La revisión de JSON confirmó tipos, disco, GPU, driver, taint, versión y un solo CIDR `/32`; `gcp_public_cidrs_access_enabled=false`. | Plan local no ejecutado. El CIDR puede cambiar antes del `apply`; regenerar el plan con la IP vigente. |
| Permisos de archivos del plan | `.tfplan`, log y JSON bajo `.local/terraform-state/` con modo `0600`; directorio protegido e ignorado por Git. | Conservar el estado local hasta `destroy`; no publicar los planes ni el CIDR. |

La primera invocación del plan falló porque el `PATH` del proceso no incluía `gcloud`; no cambió recursos. El segundo intento utilizó su ruta absoluta, un token temporal en memoria y el CIDR obtenido en el mismo proceso desde la salida IPv4 pública. El CIDR no se registra aquí. La lectura JSON del plan también necesitó ejecutar el provider fuera del sandbox. No se ejecutó `apply`.

## Recursos y costo para revisión

Las tarifas brutas de [Grupo 0](group-0.md) siguen como referencia de pago por uso para Iowa: GPU G2/L4 USD 0.706832276/h, CPU E2 USD 0.134022840/h, gestión GKE USD 0.10/h, dos discos USD 0.013699/h y dos IPv4 externas USD 0.01/h. **Subtotal estimado: USD 0.964554116/h; 30 minutos: USD 0.482277058.** Se excluyen tráfico, logs, descarga del modelo, otros consumos variables, descuentos y créditos. La cuenta de servicio y el vínculo IAM no agregan un cargo horario identificado. El pool predeterminado transitorio puede agregar un pequeño cargo de arranque; la estimación no lo cuantifica. Las tarifas G2, GKE e IPv4 se contrastaron de nuevo con las [páginas oficiales de G2](https://cloud.google.com/products/compute/pricing/accelerator-optimized), [GKE](https://cloud.google.com/kubernetes-engine/pricing) y [VPC](https://cloud.google.com/vpc/network-pricing) el 2026-10-03.

**Revisión humana:** el propietario indicó el 2026-10-03: «Plan y estimación de costos revisados y aprobados». Antes de cualquier `apply` se deberán reconfirmar CIDR, cuota, versión y precio, y definir la alerta de presupuesto. Después de crear el clúster, el Grupo 3 debe observar nodos Ready, imagen, driver, GPU asignable, espacio y acceso por `kubectl`. INF-03–INF-08 siguen PENDIENTE como requisitos completos.
