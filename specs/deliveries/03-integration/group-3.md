# Grupo 3 — Plan real para revisión de despliegue

**Estado:** cerrada por el propietario con fallo de recuperación del serving aceptado y conservado. Commit y destrucción limpia autorizados; evidencia final en validation.md. Inicio 2026-10-04, hora local America/Guatemala.

El propietario respondió «si, demosle» a la revisión del plan de tres recursos, publicación y despliegue. Preferencia de ejecución: usar siempre `uv` para Python y dependencias. Apply observado: 3 added, 0 changed, 0 destroyed. Esta aprobación cubre el despliegue y sus pruebas, no acredita sus resultados.

## Observaciones y alcance

- Contexto comprobado: `gke_llmresearch-510422_us-central1-a_nemotron-lab`; proyecto `llmresearch-510422`.
- Nodo CPU `gke-nemotron-lab-cpu-9c917b27-6bgj` Ready, amd64, etiqueta `workload=cpu`, sin taints. Allocatable CPU 3920m; requests asignados 1038m; quedan 2882m antes del chat. Memoria allocatable 13,591,704 Ki; requests 1,341,262,720 bytes. Sin requests de almacenamiento efímero asignados; allocatable 18,828,602,911 bytes. Esto acredita espacio de scheduling para 100m/128Mi/128Mi, no rendimiento bajo carga. Límites CPU existentes suman 230%; no equivalen a consumo real.
- `inference/vllm`: Deployment 1/1, pod Running/Ready, cero reinicios del pod observado; Service ClusterIP 8000. No se probó una nueva respuesta todavía.
- Inventario regional Artifact Registry vacío: no existe `nemotron-lab-apps`. No se requiere importación de un repositorio existente.
- CIDR autorizado leído del clúster y pasado como entrada privada al plan; no se registra aquí. No se modifica la red autorizada.

## Plan concreto generado

`terraform plan -input=false` con `enable_app_registry=true` produjo **3 to add, 0 to change, 0 to destroy**. La inspección JSON confirma únicamente:

| Dirección Terraform | Acción y alcance |
|---|---|
| `google_project_service.artifact_registry[0]` | Administrar habilitación de `artifactregistry.googleapis.com`; no deshabilitarla al destruir |
| `google_artifact_registry_repository.app[0]` | Crear Docker privado `nemotron-lab-apps` en `us-central1`, tags inmutables, scanning deshabilitado |
| `google_artifact_registry_repository_iam_member.nodes_reader[0]` | Reader del repositorio para `nemotron-gke-nodes@llmresearch-510422.iam.gserviceaccount.com` |

Plan binario, log y JSON están excluidos de Git en `.local/terraform-state/phase03-registry.tfplan`, `phase03-registry-plan.log` y `phase03-registry-plan.json`. Ningún cambio propuesto de pools, discos, GPU, red o serving. No se ha ejecutado apply.

El párrafo anterior describe la revisión previa. Después de aprobarla, apply creó los tres recursos; imagen publicada por digest `sha256:a8f4b0b7f77652121dc0b6065d8a4f48fa5e8bf46dc24bd9347a95b3c487c1fc`, Deployment/Service aplicados y chat Ready en CPU. Resultados reales, fixtures fallidos/corregidos y auditoría en [validation.md](validation.md). Se restauró la configuración normal tras fallos controlados y se cerraron port-forwards propios. No se hizo limpieza cloud en la sesión continua.

Limitación de revisión: vLLM registró `IndexError: pop from empty list` en caché Mamba y dos reinicios automáticos. El reintento tras interrupción inesperada conservó payload/sin duplicación, pero falló inferencia; no se declara recuperación PASS. Se comprobó Ready de nuevo sin modificar vLLM. SDK/chat de dos turnos/streaming/parámetros y controles de contexto/errores sí tienen evidencia observada. Limpieza y aceptación humana de resultados parciales siguen pendientes.

Después de aprobación: aplicar el plan guardado, publicar la imagen amd64 ya validada, consultar digest remoto, renderizar Deployment/Service y comprobar admisión server-side/diff antes de desplegar. Una réplica `inference/nemotron-chat`, CPU 100m/128Mi/128Mi requests y 500m/512Mi/512Mi limits; ClusterIP 8080, sin balanceador público. No aumentar nodos ni permisos del proyecto si falla un prerequisito. Permisos efectivos de push/pull se observarán al ejecutar; no se atribuye PASS por generar el plan.

## Costo y limpieza revisables

Tarifa oficial reconfirmada: USD 0.000136986/GiB-h. Presupuesto ilustrativo 0.25 GiB: USD 0.00003425/h, aproximadamente USD 0.025 por 730 h. No se asume franquicia disponible ni almacenamiento remoto medido. Entrada y transferencia dentro de la misma ubicación gratuitas según [precios oficiales de Artifact Registry](https://cloud.google.com/artifact-registry/pricing). Nodos adicionales: ninguno; costo incremental de nodos USD 0 para esta configuración. El clúster, GPU y PVC heredados siguen facturando; logs y consumos variables no medidos.

Al cierre: retirar aplicación, serving y PVC mientras GKE esté accesible; esperar eliminación de PV/disco, destruir Terraform conservando flag true, comprobar inventario de remanentes y desaparición del repositorio dedicado. API compartida puede quedar habilitada, sin cargo por habilitación. Este preflight no termina la sesión continua autorizada ni acredita limpieza cloud.

## Protocolo posterior a aprobación

| Tarea / IDs | Evidencia requerida |
|---|---|
| 3.1 / INT-01, INT-07, INT-08, INT-10 | Digest remoto, admisión, rollout, nodo CPU, probes, health/status, respuesta no vacía desde DNS interno; SDK independiente por port-forward de vLLM con chat/stream, parámetros y finish_reason |
| 3.2 / INT-02, INT-03, INT-05 | Navegador real: fragmentos antes del cierre, varios turnos y payload ordenado, parámetros, nueva conversación y recarga; distinguir stop/length/incompleto |
| 3.3 / INT-04, INT-06, INT-09 | Fronteras de presupuesto, rechazo/recorte, reintento manual, cancelación/stream interrumpido e indisponibilidad controlada sin reiniciar vLLM; auditar logs sin versionar contenido; presentación de texto inerte |
| 3.4 / INT-11 | Matriz real con resultados, fallos y límites; revisión humana; limpieza registrada al cierre |

Los controles simulados previos no sustituyen las comprobaciones GKE. Fallos de calidad heredados permanecen. Si una prueba no se ejecuta, queda pendiente.
