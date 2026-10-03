# Hoja de ruta del laboratorio

Las entregas siguen el orden del [README](../README.md). Cada una tendrá `requirements.md`, `plan.md` y `validation.md` en `specs/deliveries/<entrega>/`. Los documentos de especificación se revisarán antes del código. No hay entregas implementadas ni validadas todavía.

## Hechos, decisiones y supuestos de planificación

- **Hecho:** el repositorio solo contiene documentación; todavía no existe infraestructura ni evidencia operativa.
- **Decisión:** trabajar por entregas verificables, registrar resultados por requisito y destruir los recursos al final de cada sesión del laboratorio.
- **Dato informado por el propietario:** `gcloud` mostró cuota regional activa de una L4 y oferta del acelerador en `us-central1-a/b/c`. Se utilizará `us-central1-a`; capacidad efectiva y versiones disponibles se comprobarán antes de la implementación facturable.

## 1. Infraestructura

**Objetivo:** red, permisos mínimos, GKE Standard en `us-central1-a` y pools CPU/GPU administrados con Terraform. **Salida verificable:** ambos nodos Ready, discos de arranque `pd-balanced` de 50 GB y una GPU `nvidia.com/gpu` asignable; plan y costo revisados. **Dependencias:** comprobar capacidad efectiva, parche GKE, driver e IP autorizada del operador. Mantener el estado y los planes fuera de Git.

## 2. Serving

**Objetivo:** desplegar vLLM con el checkpoint FP8 en la L4 y exponerlo por Service interno. **Salida verificable:** modelo cargado, pod ubicado en GPU, respuesta y streaming desde un cliente compatible con OpenAI; tiempo de recuperación tras reinicio documentado. **Dependencias:** fijar digest de imagen, revisión del modelo, acceso a pesos y espacio de caché. Una sola GPU implica interrupción durante reinicios.

## 3. Integración

**Objetivo:** backend e interfaz de chat en CPU, con historial, respuesta progresiva, estado, errores y parámetros por petición `temperature` y `max_tokens`. **Salida verificable:** conversación de varios turnos desde la interfaz y llamada independiente por SDK. **Dependencia:** elegir tecnología de aplicación y reglas para truncar o resumir historial dentro de 4096 tokens.

## 4. Evaluación y cierre

**Objetivo:** medir memoria, latencia, throughput, concurrencia y costo; después eliminar cargas Kubernetes y destruir infraestructura. **Salida verificable:** tabla de resultados con condiciones de prueba y umbrales, costo bruto y créditos separados, evidencia de recursos eliminados. **Dependencia:** acordar umbrales de latencia y errores antes de medir. Las cotas aritméticas del README no cuentan como capacidad publicada.

## Puertas de revisión

Antes de implementar cada entrega, revisar sus requisitos y plan. Antes de un despliegue facturable, revisar recursos y costo concretos. Al validar, registrar PASS solo con evidencia observada; corregir el código frente a la especificación aprobada o revisar la especificación cuando cambie el diseño.
