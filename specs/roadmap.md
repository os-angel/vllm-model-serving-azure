# Hoja de ruta del laboratorio

Las entregas siguen el orden del [README](../README.md). Las fases 01–03 fueron ejecutadas; fases 02 y 03 cerradas por el propietario con limitaciones aceptadas y fallos conservados. Sesión cloud finalizada: cargas/PVC/disco retirados antes de destruir diez recursos Terraform; estado vacío e inventario final sin recursos del laboratorio. INF-10 completado. La evaluación sostenida de fase 04 no se ejecutó; una nueva sesión requiere revisar despliegue/costo otra vez. Evidencia en las validaciones 01–03 y retrospectiva en [Aprendizaje.md](../Aprendizaje.md).

## Hechos, decisiones y supuestos de planificación

- **Hecho histórico:** GKE, pools, serving y chat fueron desplegados y comprobados, después eliminados al cierre autorizado. Boot disk GPU ampliado directamente a 100 GB; plantilla del pool en 50 GB durante aquella sesión, excepción documentada en `tech.md`.
- **Decisión:** trabajar por entregas verificables, registrar resultados por requisito y destruir los recursos al final de cada sesión del laboratorio.
- **Dato informado por el propietario:** `gcloud` mostró cuota regional activa de una L4 y oferta del acelerador en `us-central1-a/b/c`. Se utilizará `us-central1-a`; capacidad efectiva y versiones disponibles se comprobarán antes de la implementación facturable.

## 1. Infraestructura

**Objetivo:** red, permisos mínimos, GKE Standard en `us-central1-a` y pools CPU/GPU administrados con Terraform. **Salida verificable:** ambos nodos Ready con discos `pd-balanced`: CPU 50 GB y GPU real 100 GB y una GPU `nvidia.com/gpu` asignable; plan y costo revisados. **Dependencias:** comprobar capacidad efectiva, parche GKE, driver e IP autorizada del operador. Mantener el estado y los planes fuera de Git.

## 2. Serving

**Estado:** cerrada con limitaciones aceptadas el 2026-10-04; se conservan resultados FAIL/PARCIAL observados.

**Objetivo:** desplegar vLLM con el checkpoint FP8 en la L4 y exponerlo por Service interno. **Salida verificable:** modelo cargado, pod ubicado en GPU, respuesta y streaming desde un cliente compatible con OpenAI; tiempo de recuperación tras reinicio documentado. **Dependencias:** revisión de las especificaciones 02, fijar digest de imagen y revisión del modelo, autorización/licencia de pesos y confirmar espacio de caché durante descarga. Una sola GPU implica interrupción durante reinicios. Serving e infraestructura fueron eliminados en el cierre final; INF-10 verificado.

## 3. Integración

**Objetivo:** backend e interfaz de chat en CPU, con historial, respuesta progresiva, estado, errores y parámetros por petición `temperature` y `max_tokens`. **Salida verificable:** conversación de varios turnos desde la interfaz y llamada independiente por SDK. **Estado:** cerrada por el propietario; SDK y conversación real de dos turnos observados. Fallo de recuperación de serving aceptado: dos reinicios automáticos por caché Mamba e inferencia no completada tras interrupción/reintento. No se ajustó vLLM. Limpieza de aplicación, serving/PVC, infraestructura y registry completada.

## 4. Evaluación y cierre

**Estado:** limpieza final ejecutada y verificada al cerrar fase 03. Evaluación sostenida de capacidad/rendimiento y factura real pendientes; no se declara completada esta entrega.

**Objetivo:** medir memoria, latencia, throughput, concurrencia y costo; después eliminar cargas Kubernetes y destruir infraestructura. **Salida verificable:** tabla de resultados con condiciones de prueba y umbrales, costo bruto y créditos separados, evidencia de recursos eliminados. **Dependencia:** acordar umbrales de latencia y errores antes de medir. Las cotas aritméticas del README no cuentan como capacidad publicada.

## Puertas de revisión

Antes de implementar cada entrega, revisar sus requisitos y plan. Antes de un despliegue facturable, revisar recursos y costo concretos. Al validar, registrar PASS solo con evidencia observada; corregir el código frente a la especificación aprobada o revisar la especificación cuando cambie el diseño.
