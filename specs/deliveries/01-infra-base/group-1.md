# Grupo 1 — Red y estado

**Fecha:** 2026-10-03, America/Guatemala. **Estado:** configuración y verificaciones locales completadas; sin `apply` ni recursos creados.

## Inventario y rangos

Las consultas de solo lectura `gcloud compute networks list`, `gcloud compute networks subnets list` y `gcloud compute routes list`, todas con `--project=llmresearch-510422`, mostraron una sola VPC existente (`default`, modo automático), 42 subredes primarias y ninguna secundaria. La subred existente de `us-central1` usa `10.128.0.0/20`. No se observaron peerings en la VPC listada. Hay una ruta predeterminada a Internet y rutas de subredes de la red `default`.

| Uso previsto | Nombre | CIDR | Resultado del cotejo |
|---|---|---|---|
| Nodos | `nemotron-lab-us-central1` | `10.80.0.0/20` | Sin solapamiento con 42 subredes inventariadas. |
| Pods | `nemotron-pods` | `10.81.0.0/20` | Sin solapamiento con inventario ni otros rangos propuestos. |
| Services | `nemotron-services` | `10.82.0.0/22` | Sin solapamiento con inventario ni otros rangos propuestos. |

El cálculo comparó los intervalos IPv4 de los tres CIDR con todas las subredes devueltas por `gcloud` y entre sí: cero pares solapados. No hay inventario de redes externas al proyecto; reconfirmar antes de un despliegue si aparece peering, VPN o un nuevo rango.

## Configuración revisable

- [Terraform](../../../terraform/infra/network.tf) define `nemotron-lab-vpc` en modo personalizado y una subred regional con dos rangos secundarios. La red `default` no se administra ni modifica.
- `terraform/infra/versions.tf` fija `hashicorp/google` `7.46.1`; `.terraform.lock.hcl` conserva hashes del provider. El backend local apunta a `../../.local/terraform-state/terraform.tfstate` desde `terraform/infra`.
- `compute.googleapis.com` y `container.googleapis.com` están habilitadas. La cuenta activa pasó las pruebas principales de permisos del [Grupo 0](group-0.md). El Grupo 1 no crea cuentas, grants, reglas de firewall, NAT, IP externas ni clúster.
- Los nodos con IPv4 efímeras se configurarán en el Grupo 2. Esta red conserva la ruta predeterminada a Internet; las reglas de entrada y los recursos GKE se revisarán con el plan consolidado.

## Verificaciones locales

| Comando | Resultado observado | Límite |
|---|---|---|
| `terraform fmt -check` | Código de salida 0. | Solo formato. |
| `terraform init -input=false` | Backend local inicializado; provider `hashicorp/google v7.46.1` instalado y bloqueado. | No crea recursos GCP. |
| `terraform validate -no-color` | `Success! The configuration is valid.` | No valida capacidad real ni permisos al aplicar. |
| `terraform plan -input=false -no-color -out=../../.local/terraform-state/group-1.tfplan` | `Plan: 2 to add, 0 to change, 0 to destroy`: `google_compute_network.lab` y `google_compute_subnetwork.lab` en `llmresearch-510422/us-central1`, con los tres CIDR previstos. | Plan local sin ejecución; repetir frente al inventario vigente antes de cualquier `apply`. |
| `stat` y `git check-ignore` | Directorio del plan modo `0700`, plan modo `0600`, ruta ignorada por Git. | El plan contiene datos de configuración y permanece local. |

La primera invocación de `init` dentro del sandbox no pudo resolver `registry.terraform.io`; la repetición autorizada terminó correctamente. `validate` requirió ejecutar el provider descargado fuera del sandbox. El primer `plan` no encontró Application Default Credentials; la repetición usó `GOOGLE_OAUTH_ACCESS_TOKEN` en el entorno del proceso, obtenido de la sesión activa de `gcloud` sin imprimirlo ni guardarlo. El token es temporal y se deberá obtener de nuevo para futuras operaciones.

## Costo y pendientes

El plan no propone nodos, discos, IPv4 externas, NAT ni GKE. La [tabla pública de precios de VPC](https://cloud.google.com/vpc/network-pricing) identifica cargos de tráfico y direcciones externas, no un cargo horario para la VPC y subred por sí mismas. El subtotal de USD 0.482277058 para 30 minutos del laboratorio completo sigue siendo preliminar; no se interpreta como costo de este plan ni como autorización de despliegue.

**Pendientes del Grupo 2:** configurar GKE y pools, aportar el CIDR dinámico del operador solo como entrada no versionada, comprobar plan y costo consolidados, y presentarlos para revisión antes de `apply`. No se ha probado ningún nodo, driver o GPU.
