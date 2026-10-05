# Misión del laboratorio

## Propósito

Construir un laboratorio replicable en GCP que sirva `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8` mediante vLLM en GKE Standard y exponga una API de texto compatible con OpenAI. Una interfaz de chat permitirá probarlo; la evaluación registrará funcionamiento, memoria, latencia, concurrencia y costo. El cierre eliminará las cargas y los recursos facturables del laboratorio.

## Hechos verificados

- Infraestructura, serving y aplicación CPU fueron desplegados y comprobados; pruebas en validación 01–03. Fases 02 y 03 cerradas con limitaciones aceptadas. Grupo 3 comprobó SDK, varios turnos y errores; observó dos reinicios automáticos del serving por fallo de caché Mamba durante interrupción/reintento. Al cierre autorizado se eliminaron cargas/PVC/disco y los diez recursos Terraform; estado vacío e inventario final sin recursos del laboratorio.
- El modelo responde por la API interna y externa mediante port-forward. Las cifras de concurrencia del README siguen siendo cálculos de planificación, no capacidad validada.
- La [ficha oficial del modelo](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8) documenta su uso con vLLM y el estado Mamba en FP32.

## Decisiones confirmadas

- Proyecto GCP: `llmresearch-510422` (dato proporcionado por el propietario; acceso y configuración del proyecto aún sin comprobar).
- GKE Standard zonal con un pool CPU y un pool GPU G2/L4. Kubernetes forma parte del aprendizaje del laboratorio.
- Serving de texto con vLLM y API compatible con OpenAI; interfaz, medición y limpieza son parte del alcance.
- VPN y alta disponibilidad quedan fuera del alcance inicial. El plano de control GKE tendrá endpoint público restringido por Master Authorized Networks a la IP del operador; las cargas usarán Service interno y `kubectl port-forward`, sin LoadBalancer público de inferencia.
- `specs/tech.md` es el documento técnico único; cumple la función de `techstack.md`.

## Supuestos y límites

- El propietario informó una cuota activa de una L4 en `us-central1` y oferta del acelerador en `us-central1-a`, `us-central1-b` y `us-central1-c`, consultadas con `gcloud`. La capacidad física al crear el nodo no está reservada. La VRAM nominal es 24 GB; VRAM utilizable y capacidad de servicio se medirán en ejecución.
- Boot disks `pd-balanced`: CPU 50 GB y GPU 100 GB, este último ampliado directamente por el propietario y confirmado por la evidencia del 2026-10-04. Los pesos del modelo se almacenan en un PVC dedicado `pd-balanced` de 50 GiB. La plantilla del pool existente conserva 50 GB; reconciliación controlada en `tech.md`.
- Este laboratorio no acredita por sí solo privacidad empresarial, autenticación de producción ni una capacidad determinada de usuarios.

## Resultado aceptable

Una persona podrá reproducir el despliegue desde especificaciones revisadas, obtener respuestas desde el chat y un cliente SDK, examinar evidencia de las mediciones y confirmar la eliminación de recursos. Ningún resultado se marcará como aprobado sin observación registrada.
