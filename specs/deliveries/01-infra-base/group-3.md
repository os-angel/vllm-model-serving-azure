# Grupo 3 — Acceso y validación operativa

**Estado al 2026-10-04, tras el despliegue reportado:** validación operativa parcial. El propietario compartió la salida de `terraform apply`: `Apply complete! Resources: 7 added, 0 changed, 0 destroyed.` El estado local existe en `.local/terraform-state/terraform.tfstate` con permisos `0600`. Ya se observaron clúster, nodos, GPU, driver, Master Authorized Networks, disco GPU y eliminación del pod diagnóstico. Falta comprobar ruta de caché y espacio tras descargar el modelo; la comprobación y limpieza final de infraestructura siguen pendientes. Las consultas 404 siguientes ocurrieron antes del despliegue y se conservan como evidencia histórica.

## Evidencia observada

### Después del `apply` — salidas compartidas por el propietario el 2026-10-04

| Comprobación | Resultado | Límite |
|---|---|---|
| `kubectl get nodes -o wide` | Dos nodos Ready: `gke-nemotron-lab-cpu-9c917b27-6bgj` y `gke-nemotron-lab-gpu-3c0bdecc-bxn9`; ambos `v1.35.6-gke.1250000`, Container-Optimized OS, kernel `6.12.85+`, containerd `2.1.7`. | No muestra tipo de acelerador, versión del driver ni uso de disco. |
| `kubectl get nodes -l cloud.google.com/gke-nodepool=gpu` con JSONPath | Nodo GPU con `nvidia.com/gpu` asignable = 1, `workload=gpu` y taint `dedicated=gpu:NoSchedule`. | No demuestra que `nvidia-smi` funcione dentro de un pod. |
| `kubectl get services --all-namespaces -o wide` | Ningún Service `LoadBalancer`; Services internos y `default-http-backend` NodePort de `kube-system`. | No prueba por sí solo las redes autorizadas del endpoint de control. |
| `gcloud container clusters describe` | `nemotron-lab` RUNNING, STABLE, control `1.35.6-gke.1250000`. | El formato compartido omitió `masterAuthorizedNetworksConfig`. |
| `gcloud container node-pools describe cpu/gpu` | Ambos pools RUNNING, `COS_CONTAINERD`, `pd-balanced` 50 GB, versión `1.35.6-gke.1250000`; CPU `e2-standard-4`, GPU `g2-standard-4` con etiqueta y taint previstos. | La salida no mostró `guestAccelerators` ni la configuración de instalación del driver; falta inspección de instancia, disco y uso real. |
| `kubectl logs pod/gpu-infra-check` tras corregir el manifiesto | `NVIDIA L4, 580.159.04, 23034 MiB`; `df -h /` mostró overlay 46G, 21G usados y 25G disponibles (46%). | El espacio es previo a descargar vLLM/modelo y no identifica la ruta de caché. No se recibió prueba de eliminación del pod. |
| `gcloud compute instances describe` del nodo GPU | `g2-standard-4`, un `guestAccelerators` de tipo `nvidia-l4`; disco persistente NVME de 50 GB. | La salida compartida no incluye el tipo del disco (`pd-balanced`); el pool sí lo declara. |
| `gcloud container clusters describe` con Master Authorized Networks | Un único CIDR IPv4 `/32` vigente del operador, omitido de la documentación; `gcpPublicCidrsAccessEnabled: false`. | No se probó acceso desde una red no autorizada; no es necesario para el criterio actual. |
| Consulta de Compute Engine del disco GPU | Disco `pd-balanced` de 50 GB en `us-central1-a`. | La ruta y ocupación de caché del modelo siguen pendientes. |
| `kubectl get pod gpu-infra-check` tras la eliminación | `No resources found in default namespace`. | Comprueba la eliminación del pod diagnóstico, no de la infraestructura Terraform. |

**Decisión:** INF-01, INF-03–INF-06 e INF-08 tienen evidencia suficiente para PASS. INF-07 sigue PENDIENTE de medir la caché del modelo. La versión del driver se observó dentro de un pod GPU; no se infiere solo del plan.

### Antes del `apply` — evidencia histórica

| Comprobación | Resultado | Límite |
|---|---|---|
| `gcloud container clusters list --project=llmresearch-510422 --zone=us-central1-a` | Lista vacía (salida tabular sin filas), 2026-10-04. | Inventario de esa zona con las credenciales activas; no demuestra el estado de Terraform local. |
| `gcloud container clusters describe nemotron-lab --project=llmresearch-510422 --zone=us-central1-a` | Error 404: no hay clúster con ese nombre, 2026-10-04. | Impide obtener credenciales, inspeccionar nodos o comprobar el driver. |
| Nueva ejecución del mismo `gcloud container clusters describe` el 2026-10-04 | Error 404: `No cluster named 'nemotron-lab' in llmresearch-510422`. | Confirma la ausencia en esa zona al momento de la consulta; no sustituye un inventario completo de recursos facturables. |

## Procedimiento cuando exista el clúster

Ejecutar desde la red cuya IPv4 `/32` se autorizó. Guardar las salidas resumidas y la fecha en `validation.md`; omitir la IP concreta, identidades, tokens y kubeconfig de archivos versionados. `get-credentials` modifica el kubeconfig local: ejecutarlo solo cuando el clúster exista y el operador esté listo para usar ese contexto. Si el CIDR cambió, el acceso puede fallar aunque el clúster esté sano. Corregirlo mediante un plan revisado antes de atribuir el fallo a Kubernetes.

### 3.1 Inventario y acceso — INF-03, INF-08

```sh
gcloud container clusters describe nemotron-lab --project=llmresearch-510422 --zone=us-central1-a --format='yaml(name,status,currentMasterVersion,releaseChannel,networkingMode,masterAuthorizedNetworksConfig)'
gcloud container clusters get-credentials nemotron-lab --project=llmresearch-510422 --zone=us-central1-a
kubectl cluster-info
kubectl get nodes -o wide
kubectl get services --all-namespaces -o wide
```

Confirmar que la lista autorizada contiene solo el CIDR `/32` vigente del operador y que `gcpPublicCidrsAccessEnabled` es falso. `kubectl` debe responder desde la red autorizada. Un Service `LoadBalancer` inesperado requiere identificar propietario y costo antes del cierre. Las versiones e imagen reales se registran, aunque GKE las haya actualizado respecto del plan.

### 3.2 Nodos y discos — INF-03, INF-04, INF-05, INF-07

```sh
gcloud container node-pools describe cpu --cluster=nemotron-lab --project=llmresearch-510422 --zone=us-central1-a --format='yaml(name,status,version,initialNodeCount,config.machineType,config.imageType,config.diskType,config.diskSizeGb)'
gcloud container node-pools describe gpu --cluster=nemotron-lab --project=llmresearch-510422 --zone=us-central1-a --format='yaml(name,status,version,initialNodeCount,config.machineType,config.imageType,config.diskType,config.diskSizeGb,config.guestAccelerators,config.labels,config.taints)'
kubectl get nodes -l cloud.google.com/gke-nodepool=cpu -o wide
kubectl get nodes -l cloud.google.com/gke-nodepool=gpu -o wide
kubectl describe nodes
```

Exigir un nodo Ready por pool. Comparar `e2-standard-4`, `g2-standard-4`, `COS_CONTAINERD` y discos `pd-balanced` de 50 GB con el plan. Para verificar los discos efectivos, leer `spec.providerID` de cada nodo, identificar zona e instancia y consultar sus discos de arranque en Compute:

```sh
kubectl get node NOMBRE -o jsonpath='{.spec.providerID}'
gcloud compute instances describe INSTANCIA --project=llmresearch-510422 --zone=ZONA --format='yaml(disks)'
gcloud compute disks describe DISCO --project=llmresearch-510422 --zone=ZONA --format='yaml(type,sizeGb)'
```

El segundo pod diagnóstico observó 21G usados y 25G libres en el overlay del nodo GPU antes de descargar el modelo; Compute confirmó `pd-balanced` de 50 GB. INF-07 sigue pendiente hasta definir y medir la ruta de caché durante la entrega de serving.

### 3.3 GPU y driver — INF-05, INF-06

```sh
kubectl get nodes -l cloud.google.com/gke-nodepool=gpu -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{.status.allocatable.nvidia\.com/gpu}{"\n"}{.metadata.labels.workload}{"\n"}{range .spec.taints[*]}{.key}={.value}:{.effect}{"\n"}{end}{end}'
kubectl -n kube-system get pods -o wide
```

La GPU debe aparecer como `nvidia.com/gpu: 1` asignable; la etiqueta `workload=gpu` y el taint `dedicated=gpu:NoSchedule` deben observarse. Comprobar en el pool que la instalación administrada está en `DEFAULT`. La versión **efectiva** del driver requiere la salida de `nvidia-smi` dentro de un pod diagnóstico que use la L4 o evidencia equivalente del host. No registrar `580.159.04` como observado por su aparición en la lista pública de COS. Si GKE añadió taints, conservarlos para definir las tolerations de la entrega 02. Eliminar cualquier pod diagnóstico antes de cerrar la sesión.

El manifiesto versionado [gpu-infra-check.yaml](../../../k8s/diagnostics/gpu-infra-check.yaml) solicita una GPU, tolera el taint observado y ejecuta la utilidad que GKE monta desde el host en `/usr/local/nvidia/bin/nvidia-smi`, con `PATH` y `LD_LIBRARY_PATH` explícitos. `df -h /` muestra el filesystem que respalda la capa del contenedor en el nodo GPU; es una medición inicial de espacio, pero no identifica por sí sola la ruta futura de caché del modelo. El primer intento del 2026-10-04 terminó con código 127 (`nvidia-smi: not found`) porque el `PATH` del contenedor no incluía esa ruta; esto no demuestra una falla del driver. La corrección sigue pendiente de prueba. Ejecutar desde la raíz del repositorio:

```sh
kubectl delete pod gpu-infra-check --ignore-not-found --wait=true
kubectl apply -f k8s/diagnostics/gpu-infra-check.yaml
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/gpu-infra-check --timeout=180s
kubectl logs pod/gpu-infra-check
kubectl get pod gpu-infra-check -o wide
kubectl delete -f k8s/diagnostics/gpu-infra-check.yaml --wait=true
```

Si el pod no llega a `Succeeded`, inspeccionar `kubectl describe pod gpu-infra-check` y sus eventos antes de eliminarlo. La ruta de caché futura del modelo no se observa con este pod y sigue para la entrega de serving.

### 3.4 Registro y decisión — INF-03–INF-08

Para cada ID, registrar fecha, comando, salida resumida, PASS/FAIL/PENDIENTE/BLOQUEADO y limitación en `validation.md`. Si el nodo GPU no se crea por capacidad, si no está Ready o si falta `nvidia.com/gpu`, no avanzar a serving. Si el tamaño del disco resulta insuficiente, documentar uso y caché antes de proponer 80–100 GB y revisar un nuevo plan y costo. Ejecutar el Grupo 4 de limpieza en toda sesión que haya creado recursos, incluso si esta validación falla.
