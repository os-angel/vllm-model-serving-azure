# Misión del laboratorio

## Propósito

Construir un laboratorio replicable en GCP que sirva `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8` mediante vLLM en GKE Standard y exponga una API de texto compatible con OpenAI. Una interfaz de chat permitirá probarlo; la evaluación registrará funcionamiento, memoria, latencia, concurrencia y costo. El cierre eliminará las cargas y los recursos facturables del laboratorio.

## Hechos verificados

- El repositorio contiene documentación y un commit inicial de la constitución; aún no hay infraestructura, aplicación ni pruebas.
- El [README](../README.md) declara que esta combinación todavía no se ha desplegado ni medido. Las cifras de capacidad son cálculos de planificación.
- La [ficha oficial del modelo](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8) documenta su uso con vLLM y el estado Mamba en FP32.

## Decisiones confirmadas

- Proyecto GCP: `llmresearch-510422` (dato proporcionado por el propietario; acceso y configuración del proyecto aún sin comprobar).
- GKE Standard zonal con un pool CPU y un pool GPU G2/L4. Kubernetes forma parte del aprendizaje del laboratorio.
- Serving de texto con vLLM y API compatible con OpenAI; interfaz, medición y limpieza son parte del alcance.
- VPN y alta disponibilidad quedan fuera del alcance inicial. El plano de control GKE tendrá endpoint público restringido por Master Authorized Networks a la IP del operador; las cargas usarán Service interno y `kubectl port-forward`, sin LoadBalancer público de inferencia.
- `specs/tech.md` es el documento técnico único; cumple la función de `techstack.md`.

## Supuestos y límites

- El propietario informó una cuota activa de una L4 en `us-central1` y oferta del acelerador en `us-central1-a`, `us-central1-b` y `us-central1-c`, consultadas con `gcloud`. La capacidad física al crear el nodo no está reservada. La VRAM nominal es 24 GB; VRAM utilizable y capacidad de servicio se medirán en ejecución.
- La línea base usa discos de arranque `pd-balanced` de 50 GB en ambos nodos. La suficiencia para la imagen y la caché del modelo sigue por comprobar.
- Este laboratorio no acredita por sí solo privacidad empresarial, autenticación de producción ni una capacidad determinada de usuarios.

## Resultado aceptable

Una persona podrá reproducir el despliegue desde especificaciones revisadas, obtener respuestas desde el chat y un cliente SDK, examinar evidencia de las mediciones y confirmar la eliminación de recursos. Ningún resultado se marcará como aprobado sin observación registrada.
