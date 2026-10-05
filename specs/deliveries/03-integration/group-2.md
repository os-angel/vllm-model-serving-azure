# Grupo 2 — Imagen, manifiestos y propuesta de despliegue

**Estado:** preparación autorizada; publicación y despliegue pendientes de revisión humana. No se ejecuta apply ni push en este grupo.

## Recursos concretos propuestos

| Recurso | Configuración | Propiedad y eliminación |
|---|---|---|
| Artifact Registry | `llmresearch-510422/us-central1/nemotron-lab-apps`, Docker privado, tags inmutables, scanning automático deshabilitado para este repositorio | `google_artifact_registry_repository.app`, Terraform; repositorio dedicado, incluyendo sus imágenes, eliminado durante destroy |
| API | `artifactregistry.googleapis.com` | Terraform habilita con flag; queda habilitada al destruir porque es compartida y no factura solo por habilitarla |
| IAM | Reader en ese repositorio para `nemotron-gke-nodes@llmresearch-510422.iam.gserviceaccount.com` | Member aditivo administrado por Terraform, eliminado al destruir; no cambia roles del proyecto |
| Imagen | `us-central1-docker.pkg.dev/llmresearch-510422/nemotron-lab-apps/chat@sha256:<digest publicado>` | Build local `linux/amd64`; digest real se registra después de push |
| Deployment | `inference/nemotron-chat`, una réplica Recreate, selector `workload=cpu` y `kubernetes.io/arch=amd64` | Manifiesto de aplicación, eliminación explícita antes de Terraform |
| Service | `inference/nemotron-chat`, ClusterIP 8080 | Eliminación junto al Deployment; no crea balanceador ni IP pública |

No se agregan nodos, GPU, discos persistentes ni Cloud Build. Requests propuestos 100m CPU, 128Mi RAM y 128Mi ephemeral; límites 500m/512Mi/512Mi. `/tmp` usa emptyDir RAM de 16Mi, contabilizado en memoria. La programación exige suficiente allocatable libre; si no cabe, no ampliar el pool automáticamente, revisar diseño/costo primero.

## Costo incremental de planificación

Tarifa consultada: almacenamiento Artifact Registry USD 0.000136986/GiB-h, aproximadamente USD 0.10/GiB-mes. La franquicia 0.5 GiB se comparte por cuenta y no se asume disponible. Entrada a GCP y transferencia dentro de la misma ubicación son gratuitas según [precios oficiales](https://cloud.google.com/artifact-registry/pricing). La propuesta coloca registry y GKE en us-central1; tráfico fuera de esa ubicación requiere otra estimación.

Para `S` GiB almacenados: `S × 0.000136986 × horas`. Ejemplo de planificación, **no medición**: 0.25 GiB → USD 0.00003425/h, USD 0.025/mes a 730 h. Docker informó 52,169,163 bytes para la imagen local; es su campo Size, no una medición del almacenamiento de Artifact Registry. Varias revisiones suman consumo. Mantener 0.25 GiB como presupuesto ilustrativo conservador, revisable tras publicar.

Costo adicional de nodos: USD 0 solo si el pod cabe en el pool existente sin escalar. El clúster, nodos y PVC heredados siguen facturando durante la sesión. Logs y otros consumos variables no están medidos; access log desactivado. Scanning automático se deshabilita en el repositorio propuesto para no activar ese cargo; no habilitar APIs de scanning ni Cloud Build en esta ruta.

## Antes de revisión de apply

1. Confirmar proyecto, contexto y CIDR vigente del operador. No guardar CIDR/token en Git. Comprobar que `nemotron-lab-apps` no exista o sea propiedad de esta configuración; si existe, detener y revisar importación, sin borrarlo ni sobrescribirlo.
2. Confirmar permisos del operador para crear registry/IAM/habilitar API y publicar imágenes. Terraform no concede Writer al operador automáticamente. Si falta, presentar rol acotado para revisión.
3. Comprobar nodo CPU `workload=cpu`, arquitectura amd64, allocatable y requests ya asignados: `kubectl get nodes -l workload=cpu` y `kubectl describe node <nodo-cpu>`. Verificar `inference` y Service vLLM existentes.
4. Preparar plan Terraform con flag true. La expectativa de configuración es **tres recursos adicionales** (API, repositorio y miembro IAM); no es un plan ejecutado. Revisar salida real: no aceptar cambios de pools/GPU, red o discos para publicar el chat. Si la API ya está habilitada, revisar su adopción en el estado.

Desde `terraform/infra`, después de confirmar `TF_VAR_operator_cidr` como entrada privada:

```bash
export TF_VAR_enable_app_registry=true
umask 077
terraform fmt -check
terraform validate
terraform plan -out=../../.local/terraform-state/phase03-registry.tfplan
```

Mantener `TF_VAR_enable_app_registry=true` en futuras operaciones mientras exista el registry; volver a false propone eliminarlo. Mostrar el plan resumido y costo al propietario. `terraform apply ../../.local/terraform-state/phase03-registry.tfplan` solo después de esa revisión. No usar `-target` para ocultar otros cambios y no versionar planes/estado. Revisión humana exigida por [AGENTS.md](../../../AGENTS.md).

## Build y publicación después de aprobación

Desde la raíz del repositorio:

```bash
docker buildx build --platform linux/amd64 --load --tag nemotron-chat:group2 --metadata-file .local/integration-validation/image-build.json app
uv run --no-project python scripts/validate-chat-image.py --image nemotron-chat:group2
```

Crear previamente el directorio privado `.local/integration-validation` si no existe. La prueba corre sin vLLM, verifica estado offline, health, estáticos, error de chat, UID no root, raíz de solo lectura y ausencia de paquetes dev. Su contenedor temporal se borra; la imagen local se conserva para publicación.

Tras el apply revisado, con permisos de publicación confirmados:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
APP_IMAGE_REPO=us-central1-docker.pkg.dev/llmresearch-510422/nemotron-lab-apps/chat
APP_IMAGE_TAG="phase03-$(git rev-parse --short HEAD)"
docker tag nemotron-chat:group2 "$APP_IMAGE_REPO:$APP_IMAGE_TAG"
docker push "$APP_IMAGE_REPO:$APP_IMAGE_TAG"
gcloud artifacts docker images describe "$APP_IMAGE_REPO:$APP_IMAGE_TAG" --project=llmresearch-510422 --format='value(image_summary.digest)'
```

Tags inmutables: usar un tag nuevo por artefacto; si existe, verificar digest o elegir otro tag sin sobrescribir. Copiar el digest **observado en Artifact Registry**, no el image ID de Docker ni el digest de las bases:

```bash
APP_IMAGE_DIGEST='<digest sha256 observado>'
APP_IMAGE_REF="$APP_IMAGE_REPO@$APP_IMAGE_DIGEST"
uv run --no-project python scripts/render-chat-manifest.py --image "$APP_IMAGE_REF" --output .local/integration-validation/chat.yaml
kubectl apply --dry-run=server -f .local/integration-validation/chat.yaml
kubectl diff -f .local/integration-validation/chat.yaml
```

Validación de esquema local, sin consultar GKE:

```bash
docker run --rm --volume "$PWD/.local/integration-validation:/manifests:ro" ghcr.io/yannh/kubeconform:v0.7.0@sha256:85dbef6b4b312b99133decc9c6fc9495e9fc5f92293d4ff3b7e1b30f5611823c -strict -summary -kubernetes-version 1.35.0 /manifests/chat.yaml
```

El render valida sintaxis y repositorio, no comprueba existencia remota ni compatibilidad. `kubectl diff` exit 1 significa diferencias, no aprobación ni despliegue. Registrar digest y diff concreto antes del paso siguiente.

## Despliegue y comprobación — Grupo 3 autorizado por separado

```bash
kubectl apply -f .local/integration-validation/chat.yaml
kubectl -n inference rollout status deployment/nemotron-chat --timeout=120s
kubectl -n inference get pods -l app.kubernetes.io/name=nemotron-chat -o wide
kubectl -n inference get service nemotron-chat
kubectl -n inference port-forward svc/nemotron-chat 8080:8080
```

Abrir `http://localhost:8080`; verificar nodo CPU, probes, health/status, conversación de varios turnos, streaming, parámetros y errores reales. Auditar logs sin guardar prompts. Una réplica Recreate interrumpe chat durante actualizaciones; el grace period de 330 s permite terminar peticiones, no garantiza disponibilidad. Readiness/liveness consultan backend para que una caída de vLLM sea visible en la interfaz y no provoque reinicios en cadena.

Reader de registry corresponde a la identidad del nodo que descarga la imagen, no al ServiceAccount del pod. Referencia: [cuentas de servicio GKE](https://docs.cloud.google.com/kubernetes-engine/security/configure-node-service-accounts). No se monta token Kubernetes ni se crea Secret de imagen en el pod.

## Eliminación al cierre

Mientras el clúster siga accesible:

```bash
kubectl -n inference delete deployment/nemotron-chat service/nemotron-chat --ignore-not-found
kubectl -n inference get deployment,service,pods -l app.kubernetes.io/name=nemotron-chat
```

Detener pruebas y port-forwards, eliminar serving y su Service, después PVC y esperar eliminación PV/disco. Seguir el cierre de fases 01/02. Antes de destruir clúster, comprobar que no quedan recursos cloud de controladores.

Con el flag del registry todavía true, revisar `terraform plan -destroy` y ejecutar cierre autorizado `terraform destroy`; el repositorio dedicado y su Reader se destruyen en el mismo estado. No borrar manualmente repositorios ajenos ni imágenes antes de verificar su propiedad. La API de Artifact Registry permanece habilitada y se documenta como remanente no facturable por sí solo. Confirmar mediante inventario que desaparecieron registry, clúster, nodos, discos, IP y demás recursos facturables; registrar cualquier remanente.

Consulta final del registry:

```bash
gcloud artifacts repositories list --project=llmresearch-510422 --location=us-central1 --filter='name:nemotron-lab-apps'
```

Una lista vacía solo acredita el registry de ese filtro; no sustituye el inventario global del cierre. No se ejecuta esta eliminación durante la preparación del Grupo 2.
