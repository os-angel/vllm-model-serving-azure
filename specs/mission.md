# Misión del laboratorio

## Propósito

Construir un laboratorio replicable en GCP que sirva `nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8` mediante vLLM en GKE Standard y exponga una API de texto compatible con OpenAI. Una interfaz de chat permitirá probarlo; la evaluación registrará funcionamiento, memoria, latencia, concurrencia y costo. El cierre eliminará las cargas y los recursos facturables del laboratorio.

## Hechos verificados

- El repositorio contiene `README.md` y `AGENTS.md`; aún no hay infraestructura, aplicación, pruebas ni historial Git en este directorio.
- El [README](../README.md) declara que esta combinación todavía no se ha desplegado ni medido. Las cifras de capacidad son cálculos de planificación.
- La [ficha oficial del modelo](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8) documenta su uso con vLLM y el estado Mamba en FP32.

## Decisiones confirmadas

- Proyecto GCP: `llmresearch-510422` (dato proporcionado por el propietario; acceso y configuración del proyecto aún sin comprobar).
- GKE Standard zonal con un pool CPU y un pool GPU G2/L4. Kubernetes forma parte del aprendizaje del laboratorio.
- Serving de texto con vLLM y API compatible con OpenAI; interfaz, medición y limpieza son parte del alcance.
- VPN y alta disponibilidad quedan fuera del alcance inicial. El acceso previsto es `kubectl port-forward` y un Service interno para vLLM.
- `specs/tech.md` es el documento técnico único; cumple la función de `techstack.md`.

## Supuestos y límites

- La cuota informada es una L4 y la VRAM nominal es 24 GB. La cuota y la disponibilidad efectiva en la zona se comprobarán antes de planificar recursos; la VRAM utilizable y la capacidad de servicio se medirán en ejecución.
- Se informó un disco de 50 GB como «HDD». Su tipo, ubicación y suficiencia para imágenes y caché del modelo siguen por definir.
- Este laboratorio no acredita por sí solo privacidad empresarial, autenticación de producción ni una capacidad determinada de usuarios.

## Resultado aceptable

Una persona podrá reproducir el despliegue desde especificaciones revisadas, obtener respuestas desde el chat y un cliente SDK, examinar evidencia de las mediciones y confirmar la eliminación de recursos. Ningún resultado se marcará como aprobado sin observación registrada.
