# 03 — Integración: requisitos

**Estado:** PLAN APROBADO por el propietario. Grupo 1 autorizado; despliegue pendiente de revisión concreta de recursos y costo.

## Contexto y decisiones

Decisiones heredadas: aplicación en el pool CPU, namespace `inference`, vLLM por `http://vllm:8000/v1`, modelo `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8`, contexto 4096 y una secuencia activa del motor. Acceso externo por port-forward; sin LoadBalancer ni Ingress. La entrega 02 está cerrada con limitaciones aceptadas; los fallos de calidad permanecen y esta entrega no modifica el serving para corregirlos.

Decisión del propietario al iniciar fase 03: usar FastAPI para un backend sencillo de probar. Interfaz propuesta: HTML/JavaScript sencillo, SDK compatible con OpenAI en el backend y ejecución Python mediante `uv`. Historial en memoria del navegador, sin persistencia. No resumir con el modelo; retirar pares completos de turnos antiguos con aviso visible. Decisión aprobada: estimar tokens con ceil(caracteres/4), añadir 8 tokens estimados por mensaje y reservar max_tokens de salida dentro de 4096. Retirar pares completos antiguos; rechazar si la última pregunta más instrucciones y salida reservada no caben. Esta aproximación no garantiza el conteo real del tokenizer; errores de contexto de vLLM se muestran sin ocultarlos.

## Requisitos trazados

| ID | Requisito y comprobación observable | Tarea |
|---|---|---|
| INT-01 | Backend consume el modelo por DNS interno usando el SDK; una respuesta real no vacía y el modelo solicitado quedan comprobados. | 1.1, 3.1 |
| INT-02 | Chat permite varios turnos y nueva conversación; inspección del payload confirma orden y contenido del historial, y nueva conversación elimina el anterior. | 1.2, 3.2 |
| INT-03 | Navegador muestra fragmentos antes del cierre; detecta fin normal, salida truncada y stream incompleto sin declarar éxito falso. | 1.3, 3.2 |
| INT-04 | Estado distingue backend disponible de serving disponible; indisponibilidad, timeout y errores aparecen con acción de reintento manual, sin duplicar turnos ni reenvío automático. | 1.4, 3.3 |
| INT-05 | Controles por petición para `temperature` y `max_tokens`, validados también por backend; payload prueba su transmisión. temperature: 0–2, inicial 0.6; max_tokens: 1–2048, inicial 1024. Modo visible /no_think inicial, /think seleccionable; no garantiza calidad ni finalización. | 0.2, 1.1, 3.2 |
| INT-06 | Presupuesto estimado (caracteres/4 más 8 por mensaje) y salida reservada no supera 4096; pruebas de frontera, turno demasiado largo y retiro de turnos completos. Interfaz avisa qué historial se retiró. | 0.2, 1.2, 3.3 |
| INT-07 | Una réplica de aplicación Ready en pool CPU, requests/limits y probes explícitos; sin GPU ni toleration dedicada GPU. Service ClusterIP y port-forward de aplicación funcionales. | 2.1, 3.1 |
| INT-08 | Cliente SDK independiente mediante port-forward de vLLM comprueba chat y streaming; registra parámetros, contenido, motivo de finalización y resultado sin atribuir calidad general. | 3.1 |
| INT-09 | Sin prompts, respuestas ni secretos en logs de aplicación o archivos versionados; texto del modelo se presenta como texto, sin ejecutar HTML. Historial se elimina al recargar o iniciar conversación. | 1.2, 1.4, 3.3 |
| INT-10 | Dockerfile, dependencias fijadas, configuración de URL/modelo, instrucciones locales, build, despliegue y eliminación permiten reproducir la aplicación. Imagen compatible con nodos y referencia por digest antes de desplegar. | 2.1, 2.2 |
| INT-11 | Antes del despliegue se revisan manifiestos, capacidad CPU, destino de imagen y costo incremental concreto. Limpieza incluye aplicación y cualquier registry creado; cierre Kubernetes/PVC precede a Terraform. | 0.3, 2.2, 3.4 |

## Pendientes de revisión

- Backend FastAPI en CPU aprobado; HTML/JavaScript sencillo y estimación de caracteres aprobados con el plan.
- Valores iniciales de implementación arriba; modo de razonamiento visible. La comparación 02 completó técnicamente con `/think` y 2048 tokens, pero falló calidad; no demuestra que esos valores resuelvan el problema.
- Destino de imagen, versiones, recursos CPU y límites de timeout/tamaño de petición.

Fuera de alcance: autenticación empresarial, persistencia de conversaciones, HA, autoscaling, tuning del motor y pruebas de capacidad sostenida de fase 04.
