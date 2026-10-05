# Tutorial: Plataforma de inferencia con Nemotron, vLLM, GKE y Terraform en GCP

> Laboratorio replicable mediante Spec-Driven Development (SDD).
> Despliega `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8` en un clúster GKE con NVIDIA L4 y ofrece una API de texto compatible con OpenAI para integrar aplicaciones empresariales.

## 1. Propósito y alcance

El equipo de infraestructura administra un modelo de pesos abiertos dentro de su proyecto de GCP. Los desarrolladores reciben un endpoint y un ejemplo de consumo para incorporarlo a chats, extracción de información, resúmenes u otras aplicaciones, sin administrar la GPU ni instalar el modelo.

El laboratorio enseña aprovisionamiento, preparación de GPU, serving operativo, integración por API, medición y limpieza. Usaremos GKE Standard con un pool CPU y un pool GPU, contenedores y manifiestos Kubernetes. VPN, conectividad corporativa, alta disponibilidad y escalado automático quedan fuera del alcance inicial. La infraestructura se paga a GCP: no es hardware físicamente propio.

El procesamiento se realiza en el entorno que administramos, sin enviar los prompts a un proveedor externo de inferencia. Los datos pueden mantenerse privados en GCP mediante controles de acceso, red y tratamiento de logs. Self-hosting no elimina al proveedor cloud: cambia quién opera la inferencia y qué controles administra el equipo. Ni el alojamiento propio ni una API garantizan privacidad automáticamente. Para el laboratorio la interfaz se accederá mediante `kubectl port-forward` autenticado y vLLM tendrá un Service interno ClusterIP; no se guardarán prompts en los logs de la aplicación.

**Terminado cuando:** el modelo responde desde un chat sencillo y desde el SDK de OpenAI, se documentan memoria, latencia, concurrencia y costo, y `terraform destroy` elimina los recursos del laboratorio.

## 2. Arquitectura y recorrido de una petición

1. El usuario abre una interfaz de chat a través de un port-forward local.
2. El backend de la aplicación, desplegado en el pool CPU, recibe los mensajes.
3. El backend llama a `http://vllm:8000/v1/chat/completions` mediante el Service ClusterIP, dentro del mismo namespace.
4. vLLM, en el pool GPU, ejecuta Nemotron y devuelve la respuesta progresivamente.
5. El backend entrega los fragmentos al navegador.

| Capa | Componente | Responsabilidad |
|---|---|---|
| Infraestructura | Terraform | VPC, subred, permisos mínimos, GKE y pools |
| Orquestación | GKE Standard | Scheduling, Services y recuperación de pods |
| CPU | Pool de un nodo `e2-standard-4` | Servicios del clúster, interfaz y backend |
| GPU | Pool de un nodo `g2-standard-4` con L4 | Una réplica de vLLM |
| Habilitación GPU | Instalación administrada de drivers de GKE | Registrar `nvidia.com/gpu` y permitir inferencia |
| Serving | Contenedor de vLLM | Modelo y API compatible con OpenAI |
| Aplicación | Contenedor en CPU | Chat e integración por SDK |

Google administra el plano de control. El nodo CPU ejecuta servicios y aplicación, no el plano de control completo. Un Service organiza acceso y descubrimiento; no agrega autenticación ni cifrado por sí mismo.

### Por qué Kubernetes aquí

Este laboratorio simula una plataforma empresarial: separa aplicación y serving, declara recursos, asigna GPU y permite demostrar reinicio de pods. Una VM directa también sirve el modelo, pero enseña menos sobre operación de servicios separados.

Se usarán selectores/afinidad y taints/tolerations para reservar el pool GPU. vLLM solicita `nvidia.com/gpu: 1`. Un pod de aplicación no debe aterrizar en el nodo caro por accidente.

Con una sola L4, solo habrá una réplica de serving que utiliza toda la GPU. Reiniciar el pod permite recuperación, pero interrumpe solicitudes. El laboratorio **no ofrece alta disponibilidad**. Para actualizar el pod usar estrategia `Recreate` o un rolling update sin surge compatible con una sola GPU; no esperar que dos pods GPU corran simultáneamente en ella.

### Drivers y sistema operativo

Usar la habilitación GPU administrada de GKE y verificar la versión compatible con CUDA/vLLM. No instalar en paralelo GPU Operator y drivers manuales sobre la misma pila. El GPU Operator del tutorial AKS no se copia automáticamente: GKE ofrece su propia ruta administrada.

GKE usa imágenes de nodo administradas y containerd. Se propone `COS_CONTAINERD`, sujeto a validar drivers y versión del clúster. Esto sustituye la VM Ubuntu 22.04 del diseño anterior: no se instala Docker ni se configura una imagen Ubuntu genérica en los nodos. Docker puede utilizarse localmente para construir imágenes OCI.

## 3. Infraestructura seleccionada

| Recurso | Selección |
|---|---|
| Clúster | GKE Standard zonal, para limitar costo del laboratorio |
| Región | `us-central1` |
| Zona | Una zona con G2/L4 y capacidad, configurable |
| Pool CPU | 1 nodo `e2-standard-4`, 4 vCPU y 16 GiB |
| Pool GPU | 1 nodo `g2-standard-4`, 4 vCPU, 16 GiB y 1 L4 de 24 GB nominales |
| Imagen de nodos | `COS_CONTAINERD`, administrada por GKE |
| Discos | CPU `pd-balanced` de 50 GB; GPU `pd-balanced` de 100 GB; pesos HF en un PVC `pd-balanced` de 50 GiB |
| Serving | Una réplica de vLLM; una GPU solicitada |
| Modelo | `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8` |
| Acceso de laboratorio | ClusterIP y `kubectl port-forward` |
| Escalado | Tamaño fijo inicial; autoscaling como evolución futura |

Registrar versión de Kubernetes/GKE, imagen de nodo, driver observado, runtime CUDA, imagen/digest de vLLM y revisión del modelo. GKE puede actualizar componentes según la política de mantenimiento; documentar la versión efectiva y la política elegida. Fijar versiones no significa impedir indefinidamente actualizaciones del servicio administrado.

La compatibilidad exacta de Nemotron FP8 con la L4 sigue pendiente de validación. Aprobación de cuotas no garantiza disponibilidad de capacidad.

## 4. Modelo y arquitectura híbrida

Nemotron Nano 9B v2 es un modelo de texto con razonamiento y seguimiento de instrucciones. La ficha de NVIDIA describe 56 capas: **27 Mamba-2, 25 MLP y 4 de atención**.

En el checkpoint FP8, las capas Mamba y MLP están cuantizadas, mientras las cuatro capas de atención y las convoluciones de Mamba permanecen en BF16. Por eso no se debe calcular todo el modelo como si cada parámetro ocupara exactamente un byte.

NVIDIA recomienda el estado SSM de Mamba en FP32 para preservar calidad. La API básica de chat es la primera entrega; tool calling y parsers especializados pueden añadirse después.

## 5. Cálculos de memoria

### Unidades y límites

- 1 GB = 1,000,000,000 bytes.
- 1 GiB = 1,073,741,824 bytes; 1 MiB = 1,048,576 bytes.
- BF16/FP16: 2 bytes por elemento; FP8: 1 byte; FP32: 4 bytes.

La memoria nominal de la L4 debe contrastarse con `nvidia-smi`. No se mezclan GB y GiB al calcular el presupuesto. La RAM del host es otro recurso y no se suma a la VRAM.

### Pesos: aproximación por precisión

Usando **9 mil millones de parámetros** como cifra redondeada:

| Supuesto | Operación | GB decimales | GiB |
|---|---|---:|---:|
| Todos en BF16 | `9e9 × 2` | 18.00 | 16.76 |
| Todos en FP8 | `9e9 × 1` | 9.00 | 8.38 |
| 80% FP8 / 20% BF16, ejemplo ilustrativo | `9e9 × (0.8 × 1 + 0.2 × 2)` | 10.80 | 10.06 |

El ejemplo 80/20 **no es la distribución verificada del checkpoint**. El tamaño real incluye capas sin cuantizar, escalas y otros tensores. Si `P8`, `P16` y `P32` son los parámetros almacenados en cada tipo:

```text
Memoria de pesos ≈ P8 × 1 + P16 × 2 + P32 × 4 + metadatos/escalas
```

Un valor de unos 11 GB puede utilizarse para un escenario de planificación, pero no se presenta como medición. Se registrará el tamaño del checkpoint y, por separado, la memoria que vLLM reporta al cargarlo. Tamaño en disco y VRAM de ejecución no son equivalentes.

### KV cache de las cuatro capas de atención

La configuración publicada tiene **8 heads KV**, dimensión por head **128**, y cuatro capas de atención. Suponiendo KV en BF16 y sin compartir prefijos:

```text
KV por token = 2 (K y V) × 4 capas × 8 heads KV × 128 × 2 bytes
             = 16,384 bytes = 16 KiB por token
KV por conversación = tokens retenidos × 16 KiB
```

Se usan los **8 heads KV**, no los 40 heads de consulta. Los tokens retenidos incluyen prompt, historial, instrucciones y generación; no solo la última pregunta.

| Tokens retenidos por conversación | KV BF16 | KV FP8, si está soportado y validado |
|---:|---:|---:|
| 2,048 | 32 MiB | 16 MiB |
| 4,096 | 64 MiB | 32 MiB |
| 8,192 | 128 MiB | 64 MiB |
| 16,384 | 256 MiB | 128 MiB |
| 32,768 | 512 MiB | 256 MiB |

La tabla FP8 es solo una comparación aritmética, no la configuración inicial. La cuantización FP8 de los **pesos** no implica que la KV cache también sea FP8. Bloques, alineación y políticas de caché añaden diferencias frente a estos valores ideales.

### Estado recurrente Mamba

Mamba también consume memoria. Para un estado SSM convencional por secuencia, con los valores del `config.json`:

```text
SSM por secuencia ≈ 27 capas × 128 heads × 80 elementos/head
                   × 128 dimensiones de estado × 4 bytes FP32
                 = 141,557,760 bytes = 135 MiB
```

Este cálculo describe **una copia del estado recurrente de cada capa por secuencia**. Es aproximadamente constante respecto al largo de la secuencia bajo ese supuesto, pero crece con las secuencias activas. No incluye estados convolucionales, estados adicionales para prefix caching, buffers, bloques ni reservas específicas de vLLM. El consumo real depende de la versión y la política de caché.

### Ejemplos de conversaciones simultáneas

Con KV BF16 y una copia del estado SSM por secuencia:

| Conversaciones activas | Tokens por conversación | KV total | SSM estimado | KV + SSM |
|---:|---:|---:|---:|---:|
| 1 | 4,096 | 64 MiB | 135 MiB | 199 MiB |
| 4 | 4,096 | 256 MiB | 540 MiB | 796 MiB |
| 8 | 4,096 | 512 MiB | 1,080 MiB | 1,592 MiB |
| 8 | 16,384 | 2,048 MiB | 1,080 MiB | 3,128 MiB |
| 16 | 16,384 | 4,096 MiB | 2,160 MiB | 6,256 MiB |

**Esto no predice cuántos usuarios soporta el servicio.** Faltan pesos, activaciones, buffers, CUDA graphs y otras asignaciones; además, una carga puede cumplir el presupuesto de memoria y fallar en latencia.

### Presupuesto de la GPU

```text
VRAM requerida = pesos + KV cache + estados Mamba
                 + activaciones/buffers/runtime + CUDA graphs + margen
```

Si la medición fuese 24 GiB y configuramos `--gpu-memory-utilization 0.90`, el presupuesto solicitado a vLLM sería 21.6 GiB y quedarían 2.4 GiB fuera de él. Es un ejemplo condicional: se debe sustituir 24 por la memoria realmente reportada. El parámetro no es una garantía de ausencia de OOM y puede haber asignaciones externas al presupuesto.

No se afirma que “24 menos 11” esté íntegramente disponible para conversaciones. La validación registrará memoria de pesos, capacidad de caché reportada y picos de VRAM durante prefill y generación.

## 6. Configuración inicial de serving en Kubernetes

Los argumentos siguientes se trasladarán al Deployment de vLLM. No ejecutar este comando manualmente en el nodo. Verificar sintaxis con la imagen fijada:

```bash
vllm serve nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8 \
  --trust-remote-code \
  --mamba_ssm_cache_dtype float32 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 4096 \
  --max-num-seqs 1
```

Primero validar una petición. Después probar contextos de 8K y 16K y concurrencia creciente, variando un parámetro a la vez. Fijar la revisión del modelo y revisar el código remoto requerido por `--trust-remote-code`. Registrar si fue necesario desactivar CUDA graphs u otro ajuste; no añadirlo sin evidencia.

## 7. Integración para desarrolladores

Se entregarán la URL base, identificador del modelo, mecanismo de acceso y ejemplo. Para el ejemplo externo, crear un port-forward del Service de vLLM: `kubectl -n inference port-forward svc/vllm 8000:8000`. Dentro del clúster, el backend utiliza el DNS del Service:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")
response = client.chat.completions.create(
    model="nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8",
    messages=[{"role": "user", "content": "Resume qué es Terraform en dos frases."}],
    max_tokens=256,
)
print(response.choices[0].message.content)
```

`unused` es un valor de ejemplo para un servidor local sin API key configurada; no otorga seguridad. Si se configura autenticación en el servidor, utilizar la credencial real mediante una variable de entorno.

## 8. Validación final

Construir una interfaz sencilla de chat que muestre respuesta progresiva, estado del servicio y errores. Permitir modificar `temperature` y `max_tokens` por petición. Contexto máximo y concurrencia son ajustes del servidor; cualquier cambio que requiera reinicio debe indicarse.

Validar:

1. GPU visible desde el host y el contenedor; modelo cargado sin errores.
2. API funcional desde un cliente independiente y desde la interfaz.
3. Historial enviado correctamente en una conversación de varios turnos.
4. Respuestas coherentes en un conjunto pequeño de tareas en español; registrar si razonamiento está activado.
5. Streaming, errores y reconexión visibles en la interfaz.
6. Memoria en reposo, prefill y generación; latencia al primer token, latencia p50/p95 y tokens/s.
7. Capacidad simultánea con 1, 2, 4, 8 y más solicitudes si los resultados lo permiten.

En las pruebas de concurrencia fijar largo del prompt, largo de salida, modo de razonamiento y duración. Definir antes un umbral aceptable de latencia y errores. Reportar la mayor concurrencia sostenida que lo cumple, no usuarios registrados. Incluir pruebas de prompts largos porque el prefill puede producir un pico distinto al decode.

## 9. Costos y FinOps del clúster

El monto anterior de USD 520.99/mes correspondía a una sola VM GPU con disco. **No es el precio de todo este laboratorio GKE.** Confirmar tarifas, zona, tamaños y servicios antes de cada despliegue.

| Concepto | Tratamiento |
|---|---|
| Nodo G2/L4 | Referencia previa: aproximadamente USD 0.7068/h de cómputo |
| Nodo CPU `e2-standard-4` | Consultar tarifa vigente en la zona/región seleccionada |
| Gestión GKE | Tarifa base publicada: USD 0.10 por clúster-hora |
| Dos discos de nodos | Añadir tarifa de almacenamiento y tiempo de existencia |
| Logs, red, registry, almacenamiento de pesos | Añadir consumo aplicable |
| Créditos gratuitos GKE | Verificar elegibilidad y saldo; no asumirlos |

El nivel gratuito puede compensar parte de la gestión de clústeres zonales elegibles mediante créditos mensuales por cuenta de facturación. Reportar costo bruto y créditos efectivos por separado. Usar el período estándar de soporte para evitar cargos de soporte extendido.

```text
H = costo/h del nodo GPU + nodo CPU + gestión GKE
    + discos y servicios prorrateados
Costo sesión = H × horas, ajustando componentes por consumo real
Costo mensual ilustrativo = H × 730
Costo por usuario-hora a plena ocupación = H / C
```

`C` es la concurrencia sostenida validada. Ejemplo **solo aritmético**: si H fuese USD 1.00/h y C fuese 8, serían USD 0.125 por usuario-hora a plena ocupación. No es una cotización ni capacidad confirmada. Sin solicitudes el clúster sigue facturando.

No crear programas de instantáneas para el laboratorio. `port-forward` evita necesitar un LoadBalancer público; si se añade uno, incluir su costo y limpieza. Crear una alerta de presupuesto como respaldo: no detiene el gasto automáticamente.

## 10. SDD para hacer el laboratorio replicable

SDD registra intención, decisiones, tareas y criterios de aceptación para que otra persona o agente reproduzca el despliegue y compruebe el resultado.

| Documento propuesto | Contenido |
|---|---|
| `specs/mission.md` | Propósito, usuarios, alcance y resultado esperado |
| `specs/tech.md` | Arquitectura, revisiones, versiones y parámetros |
| `specs/roadmap.md` | Entregas y dependencias |
| `specs/deliveries/<entrega>/requirements.md` | Requisitos verificables |
| `specs/deliveries/<entrega>/plan.md` | Diseño y tareas pequeñas |
| `specs/deliveries/<entrega>/validation.md` | Pruebas y evidencia |

Entregas:

1. **Infraestructura:** GKE, red, pools CPU/GPU y GPU anunciada a Kubernetes.
2. **Serving:** Deployment GPU de Nemotron FP8, Service interno y API funcional.
3. **Integración:** aplicación en pool CPU, chat web y consumo de la API interna.
4. **Evaluación y cierre:** memoria, concurrencia, costos y eliminación.

Antes de cada entrega revisar sus especificaciones; implementar en una rama, validar, registrar evidencia e integrar. Si cambia una decisión, actualizar la especificación. Si el código incumple un requisito correcto, corregir el código.

## 11. Requisitos y ciclo Terraform

Necesitas un proyecto con facturación, APIs Compute Engine y Kubernetes Engine, permisos mínimos adecuados, cuotas G2/L4, CPU e IP suficientes, una zona con capacidad, Google Cloud CLI, plugin de autenticación GKE, kubectl y Terraform. Fijar versiones en las especificaciones. Una cuota aprobada no garantiza disponibilidad.

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project TU_PROJECT_ID
```

Una vez implementada la infraestructura, desde su directorio:

```bash
terraform fmt -check
terraform init
terraform validate
terraform plan -out=tfplan
```

Revisar el plan antes de `terraform apply tfplan`. Un apply exitoso no demuestra que el driver ni el modelo estén listos. No publicar credenciales, estado o planes en Git.

## 12. Cierre obligatorio: Kubernetes y terraform destroy

Al terminar cada sesión, detener pruebas y eliminar primero las cargas administradas por Kubernetes mientras el clúster sigue accesible. Si se crearon Services LoadBalancer, Ingress o PVC, esperar la limpieza de los recursos cloud asociados antes de destruir GKE. Luego, desde el estado de infraestructura:

```bash
terraform plan -destroy
terraform destroy
```

La infraestructura debe estar bajo gestión de Terraform. Las cargas Kubernetes deben tener manifiestos versionados y una rutina explícita de eliminación. Se propone separar `terraform/infra` de manifiestos `k8s/` para evitar dependencias de providers Kubernetes contra un clúster ya destruido. Terraform destroy no sustituye la comprobación de recursos creados por controladores de Kubernetes. Confirmar que no queden clúster, pools/VM, discos, IP reservadas, balanceadores, instantáneas, registry/buckets del laboratorio u otros recursos facturables que debían eliminarse. Los recursos externos al estado requieren limpieza explícita.

Detener la VM no elimina todos los cargos. Destruir recursos evita su consumo futuro; los cargos ya incurridos permanecen. Configurar una alerta de presupuesto como respaldo, recordando que no detiene el gasto automáticamente.

## 13. Estado y fuentes

Documento de diseño: aún no se ha desplegado ni medido esta combinación en L4. Los documentos de especificación indicados son la estructura propuesta y deben crearse antes de implementar.

- [Ficha oficial del checkpoint FP8](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8)
- [Configuración usada para las dimensiones de memoria](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8/blob/main/config.json)
- [Ficha original y recomendación SSM FP32](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2)
- [Receta vLLM](https://recipes.vllm.ai/nvidia/NVIDIA-Nemotron-Nano-9B-v2)
- [Instalación GPU de vLLM](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)
- [Máquinas GCP optimizadas para aceleradores](https://docs.cloud.google.com/compute/docs/accelerator-optimized-machines)

## 14. Escenarios de capacidad y contexto por usuario

Los cálculos siguientes estiman un **límite de memoria**, no capacidad de servicio comprobada. El throughput y la latencia pueden limitar el servicio mucho antes. Se asume una secuencia activa por persona y sin compartir prefijos.

Escenario ilustrativo, que debe sustituirse por mediciones:

- VRAM utilizable: **24 GiB hipotéticos**.
- Presupuesto al 90%: **21.6 GiB**.
- Pesos: **11 GB decimales = 10.245 GiB**, supuesto de planificación.
- Reserva adicional dentro del presupuesto: **3 GiB** para runtime, buffers y otras asignaciones; no es un valor medido.
- Resto para KV + una copia del estado SSM: **8.355 GiB ≈ 8,556 MiB**.
- Fuera del presupuesto: 2.4 GiB de margen; las asignaciones reales pueden exceder estas reservas.

```text
Memoria ideal por secuencia (MiB) = 135 + tokens / 64
Límite ilustrativo = floor(8556 / memoria ideal por secuencia)
```

| Ventana total por persona | KV + SSM ideal por persona | Límite ilustrativo por memoria |
|---:|---:|---:|
| 4,096 tokens | 199 MiB | 42 secuencias |
| 8,192 tokens | 263 MiB | 32 secuencias |
| 16,384 tokens | 391 MiB | 21 secuencias |
| 32,768 tokens | 647 MiB | 13 secuencias |

**No anunciar que la L4 soporta 42 usuarios.** Es una cota simplificada bajo supuestos de pesos, reservas y caché; omite diferencias del gestor híbrido, cachés adicionales y rendimiento. Si alguno de los supuestos cambia, se recalcula la tabla. La capacidad publicada del tutorial será únicamente la mayor concurrencia sostenida que pase las pruebas.

### Ventana inicial y reparto de tokens

Para el laboratorio, iniciar con **4,096 tokens totales por conversación y una secuencia simultánea**. Después probar 2, 4 y 8 secuencias, y ampliar contexto si los resultados lo permiten.

Ejemplo de presupuesto por petición:

| Uso | Tokens presupuestados |
|---|---:|
| Instrucciones, plantilla, historial y pregunta | Hasta 3,072 |
| Respuesta, incluyendo razonamiento si se activa | Hasta 1,024 |
| Total | 4,096 |

Contar los tokens después de aplicar la plantilla real. Si el historial supera el presupuesto, la aplicación debe truncarlo o resumirlo antes de enviar la petición. vLLM no conserva automáticamente una conversación: la aplicación envía los mensajes de cada turno. Los usuarios conectados e inactivos no equivalen a secuencias activas; la memoria retenida después de una petición depende de la política de caché.

Para **8 peticiones activas de 4,096 tokens**, el mínimo ideal KV + SSM es `8 × 199 = 1,592 MiB`, aproximadamente **1.55 GiB**. Para **8 de 16,384**, sería **3.05 GiB**. Ninguna cifra incluye los pesos ni los demás gastos del servidor.

`--max-num-seqs` limita secuencias que el motor procesa simultáneamente; no representa por sí solo un límite de usuarios registrados o conexiones. Puede haber peticiones en cola. Registrar tiempo de espera además de tiempo de generación.

## 15. Proceso SDD obligatorio del laboratorio

### Fase 0: contexto global

El humano comunica el objetivo y revisa decisiones; Codex identifica ambigüedades y prepara `mission.md`, `tech.md` y `roadmap.md`. `tech.md` cumple la función que el curso llama `techstack.md`; se utiliza un solo nombre para evitar duplicación.

Revisar y corregir los documentos, distinguir decisiones de hipótesis y registrar la revisión en Git antes de escribir implementación. Estos archivos son una constitución **versionada y modificable mediante revisión**, no reglas eternamente inmutables. El roadmap es vivo.

### Ciclo por entrega

1. Crear una rama independiente para la entrega.
2. **Especificar:** Codex prepara requisitos, plan por grupos de tareas y scorecard de validación. Cada requisito tiene identificador y una comprobación asociada. El humano revisa el alcance y hace que se registre el commit de especificaciones revisadas antes del código.
3. **Implementar:** Codex relee los documentos y ejecuta los grupos secuencialmente, con cambios y commits manejables. Antes de despliegues facturables presenta el plan y los recursos concretos para revisión.
4. **Validar:** comprobar sintaxis, API y comportamiento según la entrega; registrar por requisito la evidencia, resultado y limitaciones. La ausencia de una prueba no cuenta como PASS. El humano revisa diff y resultado funcional.
5. **Cerrar:** corregir fallos, actualizar estado y notas relevantes, y fusionar cuando la entrega cumpla el contrato revisado. La infraestructura provisionada se destruye al final de cada sesión del laboratorio.
6. **Replanificar:** revisar aprendizajes y el siguiente hito; actualizar documentos afectados. Si cambian principios globales, tratar esa actualización como un cambio revisable separado antes de la siguiente implementación.

Si el código tiene un bug, corregirlo contra la especificación correcta. Si cambia el diseño acordado, revisar la especificación y alinear el código; no modificar los criterios para justificar un fallo.

Una sesión nueva debe leer archivos, estado de Git y evidencia existente. Limpiar contexto con un comando de la herramienta es opcional, no un requisito universal de SDD. Los subagentes y skills son opcionales; los controles centrales son especificar, revisar, implementar, validar y replanificar.

**Estado:** este README define el flujo. Las especificaciones, commits y pruebas no se han ejecutado todavía; no se afirma que el proyecto ya haya completado SDD.

## 16. ¿Qué significa privacidad al alojar el modelo en GCP?

Estar en GCP **no significa que los datos sean públicos**. El proyecto utiliza infraestructura cloud contratada y administrada por el equipo: los prompts se procesan en su servidor de inferencia, en lugar de enviarse a una API de inferencia administrada por otro proveedor.

La diferencia es el control operativo y la distribución de responsabilidades. En self-hosting, el equipo administra endpoint, credenciales, almacenamiento, logs, revisiones del modelo y eliminación. GCP sigue proporcionando la infraestructura y su tratamiento de datos depende de sus servicios y condiciones. En una API administrada, el proveedor opera el modelo y aplica sus políticas de retención, acceso y uso de datos. Algunas APIs empresariales ofrecen controles sólidos y no utilizan datos para entrenar por defecto; no se debe asumir lo contrario para todas las APIs.

Este tutorial demuestra despliegue e integración, no una evaluación completa de seguridad empresarial ni soberanía de datos. Mantener la privacidad requiere configurar el acceso y documentar dónde se guarda información. El laboratorio utiliza acceso por port-forward y evita logs de contenido; una API key aislada no equivale a una arquitectura de producción completa.

### Ventajas y desventajas frente a contratar una API

| Aspecto | Modelo alojado en nuestro proyecto GCP | API de inferencia administrada |
|---|---|---|
| Control del modelo | Elegimos pesos, revisión, runtime y parámetros | Dependemos de modelos y opciones ofrecidos |
| Flujo de información | Procesamiento en nuestro servidor; administramos contenido y logs | Enviamos solicitudes al proveedor de inferencia; revisar sus políticas |
| Privacidad | Podemos aplicar nuestros controles; debemos configurarlos y mantenerlos | Puede ofrecer garantías empresariales; dependen del contrato y producto |
| Costos | Pagamos capacidad encendida, incluso sin solicitudes; puede convenir con utilización sostenida | Habitualmente pagamos por uso/tokens; suele ser práctico con carga baja o variable |
| Capacidad | Limitada por la GPU y el rendimiento medido; escalar exige recursos | Capacidad operada por el proveedor, sujeta a cuotas y límites |
| Operación | Somos responsables de drivers, parches, disponibilidad, monitoreo y fallos | El proveedor administra gran parte de esa operación |
| Rendimiento | Controlamos ajustes y colas, pero debemos medir y dimensionar | Inicio rápido; latencia, versiones y capacidad dependen del servicio |
| Calidad | La calidad depende del modelo elegido; tener pesos no garantiza mejores respuestas | Puede dar acceso a modelos de mayor tamaño sin comprar su infraestructura |
| Personalización | Podemos explorar fine-tuning o adaptadores cuando modelo, licencia y recursos lo permitan | Disponible solo en las opciones que ofrece el servicio |
| Puesta en marcha | Más trabajo inicial y mantenimiento | Integración inicial generalmente más sencilla |

No se afirma que self-hosting sea siempre más económico: la comparación requiere carga, throughput, horas encendido, costos operativos y calidad equivalente. Para este laboratorio, su valor es enseñar cómo ofrecer un modelo de pesos abiertos como API, medir sus límites y controlar su ciclo de vida.

Fuentes de contexto:

- [Privacidad de datos en Google Cloud](https://cloud.google.com/privacy)
- [Privacidad empresarial y de API de OpenAI, como ejemplo de un proveedor administrado](https://openai.com/enterprise-privacy/)

## 17. Criterios de validación específicos de GKE

- Un nodo CPU y un nodo GPU Ready; tamaños y conteos coinciden con el plan.
- El nodo GPU anuncia una unidad asignable `nvidia.com/gpu`.
- El pod vLLM cae en el pool GPU; la aplicación cae en CPU.
- Requests/limits CPU y RAM dejan margen a componentes del sistema; los recursos allocatable son inferiores al hardware nominal.
- Probes del serving toleran descarga/carga inicial y luego detectan fallos; el backend maneja indisponibilidad sin ocultarla.
- El Service interno resuelve desde el backend; una llamada por SDK produce respuesta correcta.
- Eliminar un pod de vLLM en una prueba controlada y medir tiempo de recuperación. Registrar interrupción y recarga; no afirmar cero downtime.
- Repetir las pruebas de memoria/concurrencia en el pod real: Kubernetes no multiplica la capacidad de una L4.
- La publicación de capacidad incluye tokens de entrada/salida, contexto, modo de razonamiento, latencia y duración. Hasta medir, solo existen escenarios aritméticos.
- La rutina de limpieza elimina cargas, infraestructura y remanentes de controladores en el orden correcto.

### Replicabilidad operativa

El repositorio contendrá specs, Terraform, manifiestos, código de interfaz/backend, Dockerfile de aplicación, scripts de verificación/carga/limpieza y versiones efectivas. Registrar cómo recrear la caché del modelo. No conservar volúmenes facturables tras el laboratorio salvo decisión explícita. Si la imagen de aplicación se guarda en Artifact Registry, definir propiedad y eliminación del repositorio creado para el laboratorio.

Fuentes de GKE:

- [GPU L4 y drivers en GKE Standard](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/gpus)
- [Precios y créditos de gestión GKE](https://cloud.google.com/kubernetes-engine/pricing)

## 18. Human-in-the-loop y herramientas explícitas

El humano revisa decisiones, especificaciones, planes y evidencia. El agente debe entrevistarle al detectar alternativas relevantes de arquitectura, costo u operación; usar `UserAskQuestions` cuando esté disponible, su equivalente o preguntas en el chat. No asumir decisiones materiales pendientes ni repetir las ya resueltas.

Herramientas: **gcloud CLI** para autenticación, proyecto, credenciales GKE e inventario; **Terraform CLI** para infraestructura; **kubectl** para despliegues, inspección y pruebas Kubernetes. gcloud no reemplaza IaC: evitar crear manualmente recursos que deben pertenecer al estado Terraform.

En la modalidad guiada de este tutorial, el agente prepara archivos, comandos y resultados esperados; el participante ejecuta autenticación, plan, apply, despliegues, validaciones y destroy. El agente interpreta la evidencia compartida y propone correcciones. No marca PASS sin resultados observados.
