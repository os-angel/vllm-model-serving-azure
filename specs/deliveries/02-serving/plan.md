# 02 — Serving con vLLM: plan

**Estado actual: CERRADA CON LIMITACIONES ACEPTADAS** por el propietario el 2026-10-04. Serving y PVC desplegados: CPU 50 GB, GPU real 100 GB, PVC 50 GiB. Licencia/acceso y ClusterIP sin API key aprobados. Evidencia, fallos y criterios parciales conservados en `validation.md`; no se ejecuta Terraform apply.

## Dependencias y puerta de entrada

- Entrega 01 aprobada operativamente; nodo GPU Ready con una L4, driver `580.159.04`, taint `dedicated=gpu:NoSchedule` y etiqueta `workload=gpu`.
- INF-07 se transfiere a SRV-05/SRV-10. El nodo GPU reportó 25 GB libres antes de descargar modelo e imagen vLLM; la imagen pesa 9.8 GB comprimida y el checkpoint ~10.3 GB.
- No cambiar el pool GPU: está limitado a una L4 y su `SURGE maxSurge=1` intentaría reservar temporalmente una segunda L4 durante el recambio.
- El PVC `inference/vllm-cache` de 50 GiB ya aprovisionó un disco zonal `pd-balanced` por `standard-rwo` con `WaitForFirstConsumer`; el recurso se factura desde su aprovisionamiento hasta borrarlo. Estimación pública bruta: 50 GiB × USD 0.00013699/GiB-h ≈ USD 0.00685/h o USD 5.00/mes a 730 h. Revisar costo y autorizar antes de aplicar.
- Infraestructura y PVC existentes siguen facturando. Esta revisión valida esos recursos.

## Grupo 0 — Resolver entradas que bloquean manifiestos

1. Registrar licencia/acceso aceptados y configuración interna sin API key; si HF solicita token, usar Secret externo a Git. (SRV-02, SRV-11, SRV-12)
2. Fijar digest vLLM y los commits del checkpoint y del código remoto; revisar el código que activa `--trust-remote-code`. (SRV-01, SRV-02, SRV-06)
3. Confirmar StorageClass `standard-rwo` y especificar PVC 50 GiB `pd-balanced` con `ReadWriteOnce`, `WaitForFirstConsumer` y montaje HF. Estimar costo y revisar antes de cualquier apply. (SRV-05, SRV-10, SRV-14)
4. Confirmar allocatable GPU; fijar requests iniciales CPU/RAM/ephemeral y probes a partir de valores observados, dejando su ajuste sujeto a medición de arranque. (SRV-05, SRV-07)

**Salida comprobable:** tabla de versiones/digests y SHA, licencia/acceso resueltos, manifiesto PVC 50 GiB con costo informado, clase de almacenamiento confirmada y configuración/probes trazadas. Diseño inicial: boot disk GPU 50 GB. Estado posterior: disco real 100 GB; medir uso real de imagen OCI al desplegar y detener si el espacio cae bajo el margen acordado.

## Grupo 1 — Preparar manifiestos versionados

1. Crear namespace `inference` y PVC `vllm-cache` 50 GiB `standard-rwo` (`pd-balanced`, `ReadWriteOnce`). (SRV-03, SRV-14)
2. Crear Service `ClusterIP` `vllm` puerto 8000 y Deployment de una réplica, estrategia `Recreate`, con image/model/code fijados. Montar PVC en `/root/.cache/huggingface` y configurar `HF_HOME` al mismo punto. (SRV-01–SRV-03, SRV-06, SRV-08, SRV-13, SRV-14)
3. Aplicar `nodeSelector workload=gpu`, toleration exacta `dedicated=gpu:NoSchedule` y límite GPU `nvidia.com/gpu: 1`. (SRV-04)
4. Configurar requests/limits iniciales, probes, Service interno y logging sin contenido; credenciales HF solo desde Secret externo si fueran necesarias. No incluir kubeconfig, token ni CIDR en Git. (SRV-05, SRV-07, SRV-11)

**Salida comprobable:** manifiestos de namespace, PVC, Deployment y Service versionados contra SRV-01–SRV-15; no ejecutar `kubectl apply` hasta revisión de costo y autorización humana de despliegue.

## Grupo 2 — Desplegar y validar carga/API

### Revisión de validation as code autorizada por el propietario

1. Reconciliar documentación y Terraform con boot disk CPU 50 GB, GPU real 100 GB y PVC 50 GiB. El disco GPU se amplió directamente; el pool GKE conserva la plantilla antigua. Declarar 100 GB para futuras creaciones y excluir únicamente actualizaciones del tamaño del boot disk del pool existente para evitar surge de una segunda L4. No ejecutar Terraform apply. (SRV-10/SRV-15)
2. Ejecutar salud, catálogo, chat, SSE y SDK como comprobaciones independientes con errores explícitos y estados por requisito. Exigir respuesta no vacía y final natural `stop`; `length` es fallo. Registrar solicitudes y modo de razonamiento. (SRV-07–SRV-09)
3. Mantener el caso original FP8 y añadir verificaciones deterministas de contenido/formato para tareas pequeñas en español; no aceptar FP16 como respuesta a FP8. Investigar tokenizer, plantilla y motor antes de cambios de serving. (SRV-06/SRV-09)
4. Verificar configuración remota y checkpoint por revisión/hash; comprobar selección del módulo nativo de vLLM para no exigir un módulo HF que el motor no usa. Guardar limitaciones de observación en procesos independientes. (SRV-01/SRV-02)
5. Ejecutar script mediante uv, incluida recuperación controlada, y registrar hashes de pesos, PVC/PV, Ready, métricas y llamadas tras recuperación. Cada captura es evidencia, no PASS de criterio por sí sola. No finalizar la entrega con requisitos requeridos FAIL/PENDIENTE. (SRV-03–SRV-15)

La prueba experimental eager se retiró por corrección de alcance del propietario: completar primero el validador y ejecutar los criterios sobre la configuración aprobada. No adoptar cambios de motor para obtener PASS. Los fallos de calidad se registran y mantienen abierta la entrega hasta corregir su causa.

Automatización solicitada: `scripts/validate-serving.py` captura configuración, GPU/RAM/disco, revisiones cacheadas, API externa, SDK y streaming; genera evidencia y reporte en `.local/serving-validation/`. Recuperación requiere `--with-recovery`, mide reemplazo/Ready y compara PVC y pesos antes/después. Instalación local del SDK requiere `--install-sdk`. Las mediciones posteriores al pull no reconstruyen el espacio previo; calidad del texto, auditoría de código remoto y logs requieren revisión humana. El reporte no declara completada la entrega ni modifica Terraform o elimina infraestructura. (SRV-01–SRV-15)

Por instrucción del propietario, usar siempre `uv` para ejecutar Python, crear entornos e instalar dependencias. Comando completo: `uv run --no-project python scripts/validate-serving.py --install-sdk --with-recovery`.

Corrección de arranque SRV-06 autorizada por el propietario: conservar en el manifiesto la ruta NVIDIA y CUDA en `LD_LIBRARY_PATH`; aplicar al Deployment existente y verificar NVML/CUDA, logs de carga, readiness y API. Usa la misma réplica, GPU y PVC; no añade recursos facturables.

El arranque posterior reveló una colisión de `VLLM_PORT` inyectado por Kubernetes con el puerto interno del motor. Desactivar `enableServiceLinks`, conservar descubrimiento por DNS y repetir carga/API. (SRV-06/SRV-08)

1. Aplicar namespace, Deployment y Service; observar rollout y que exactamente un pod consume la GPU. (SRV-03–SRV-08)
2. Medir pull de imagen, descarga/cache del checkpoint, disco antes/después, memoria VRAM y RAM host; confirmar logs sin prompts/secrets. (SRV-05, SRV-06, SRV-10, SRV-11)
3. Esperar probes Ready; comprobar `GET /v1/models`, chat completion y streaming mediante `kubectl port-forward`. (SRV-07–SRV-09)
4. Registrar combinación exacta: GKE/nodo/driver, imagen vLLM y digest, CUDA, commit del modelo, argumentos, duración de carga, uso de disco/VRAM/RAM y limitaciones. (SRV-01, SRV-02, SRV-06, SRV-09, SRV-10)

**Puerta:** no pasar a integración si el modelo no carga, falla CUDA, no cabe en disco/VRAM, no devuelve respuesta o la API queda pública.

## Grupo 3 — Recuperación y cierre de la entrega

1. Con el propietario presente, recrear el pod una vez y medir indisponibilidad y tiempo hasta Ready. Una L4 significa interrupción; nunca iniciar un segundo pod GPU en paralelo. (SRV-03, SRV-13)
2. Validar que el Service sigue interno, logs no incluyen contenido, y registrar resultado por ID en `validation.md`. (SRV-08, SRV-11, SRV-12)
3. Mantener serving activo para la Entrega 03 solo por instrucción del propietario. Al cerrar serving, borrar primero Deployment/Service y después el PVC; verificar que desaparecieron el PV y el disco facturable. No destruir Terraform en esta entrega; INF-10 es el cierre final del laboratorio.

**Criterio de salida:** SRV-01–SRV-15 con evidencia de ejecución. SRV-13 queda PASS tras prueba medida o PENDIENTE si el propietario prefiere no interrumpir el servicio. INF-07 se cierra con las medidas de imagen/PVC y queda trazado aquí y en validación 01.

## Comparación final autorizada por el propietario

Tras la ejecución base `/no_think` con 128 tokens, ejecutar una sola comparación `/think` con `max_tokens=2048`, temperatura 0.6 y top_p 0.95; conservar las mismas preguntas y criterios de contenido. Evaluar formato/contenido sobre la respuesta final después de `</think>`, conservando el texto completo como evidencia. Mantener `stop` y cierre SSE como criterios técnicos. No cambiar Deployment ni recrear de nuevo el pod. No encadenar más variantes: consolidar ambos reportes y presentar bloqueos para revisión humana antes de entregar 02. Parámetros de razonamiento basados en la [ficha oficial NVIDIA](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8).

## Resultado de pasos 1, 2 y 3

Documentación reconciliada; seis pruebas locales UV OK (incluido -O); ejecutados reporte base con recuperación y única comparación con razonamiento. Matriz actual y limitaciones en `validation.md`. No iniciar más variantes automáticas. Fase 02 cerrada por aceptación explícita del propietario de calidad fallida y mediciones/revisión parciales.

## Aceptación de cierre

El propietario aprobó la revisión y dio por cerrada la entrega 02 el 2026-10-04. Aceptó expresamente SRV-05, SRV-10 y SRV-11 PARCIAL y los fallos de calidad FP8/aritmética como limitaciones documentadas de esta fase. Se conservan estados, respuestas, códigos de salida y límites originales; la aceptación no convierte FAIL/PARCIAL en PASS ni determina la causa de la mala inferencia.

Esta aceptación es una excepción explícita del propietario a la puerta de cierre que exigía todos los criterios completos. Los criterios técnicos y las comprobaciones automatizadas permanecen; no se ajustan para producir PASS. Entrega 03 habilitada como siguiente trabajo, sin implementarla en este cierre.
