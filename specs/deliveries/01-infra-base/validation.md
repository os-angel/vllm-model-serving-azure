# 01 — Infraestructura base: validación

**Estado general:** PENDIENTE. Al crear este archivo no hay Terraform ni recursos desplegados desde esta entrega. Ningún criterio está aprobado. Completar fecha, evidencia concreta y limitaciones después de cada comprobación.

## Registro de evidencia por requisito

| ID | Comprobación prevista | Evidencia que se conservará | Estado |
|---|---|---|---|
| INF-01 | Confirmar proyecto, `us-central1-a`, facturación, cuota y oferta G2/L4 antes del plan. | Salida reciente de `gcloud` para cuota regional y oferta zonal, plan con zona principal; capacidad efectiva observada al crear el nodo. Si se usa `us-central1-b/c`, conservar plan nuevo revisado. | PENDIENTE |
| INF-02 | Comparar red prevista con recursos existentes y plan Terraform. | Rangos VPC/subred/secundarios y extracto del plan; inventario después del despliegue. | PENDIENTE |
| INF-03 | Revisar plan y consultar versión e imagen de nodos GKE. | Canal/parche planeados y versiones reales del clúster, nodo y `COS_CONTAINERD`. | PENDIENTE |
| INF-04 | Consultar pool y nodo CPU. | Un nodo Ready; tipo `e2-standard-4`, disco y pool observados. | PENDIENTE |
| INF-05 | Consultar pool y nodo GPU. | Un nodo Ready `g2-standard-4`; `nvidia.com/gpu: 1` asignable y salida de verificación GPU cuando esté disponible. | PENDIENTE |
| INF-06 | Revisar configuración de driver y atributos del nodo. | Versión NVIDIA efectiva, evidencia de instalación administrada y etiquetas/taints; ausencia de Operator o instalador paralelo. Tolerations de vLLM quedan para entrega 02. | PENDIENTE |
| INF-07 | Revisar tipo y tamaño de discos, uso y caché prevista. | Plan e inventario con boot disks `pd-balanced` de 50 GB en ambos nodos; medición de espacio antes de servir el modelo. Si se amplía GPU a 80–100 GB, registrar saturación y nuevo plan. | PENDIENTE |
| INF-08 | Probar acceso administrativo e inventariar Services. | Master Authorized Networks con CIDR del operador y sin `0.0.0.0/0`; consulta `kubectl get nodes` autorizada y verificación de restricción; inventario sin LoadBalancer de inferencia. | PENDIENTE |
| INF-09 | Revisar plan y costo antes de aplicar. | Plan identificado, estimación de costo, recursos concretos y constancia de revisión previa. | PENDIENTE |
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
