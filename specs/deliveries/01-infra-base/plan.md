# 01 — Infraestructura base: plan

**Estado:** plan de trabajo, no ejecutado. Implementar solo después de revisar [requirements.md](requirements.md) y resolver las decisiones que condicionan el diseño. Cada grupo termina con una comprobación y un cambio revisable. Esta fase de especificación no escribe Terraform.

## Grupo 0 — Cerrar entradas y costo

1. Usar `us-central1-a` como zona principal y conservar evidencia reciente de facturación, cuota regional L4, oferta G2/L4, cuotas CPU/IP y APIs necesarias. La capacidad efectiva se observará al crear el nodo. Si falla, evaluar `us-central1-b/c` mediante plan nuevo revisado.
2. Planear discos de arranque `pd-balanced` de 50 GB para ambos nodos y estimar espacio para imágenes/caché. Evaluar 80–100 GB en GPU solo si las pruebas posteriores muestran saturación.
3. Elegir canal/parche GKE, versión COS y estrategia de driver administrado. Comprobar compatibilidad prevista con el contenedor vLLM antes de fijar versiones.
4. Obtener la IP pública actual del operador para Master Authorized Networks, definir salida a registros/modelo, permisos mínimos, ubicación del estado Terraform y presupuesto de sesión.

**Salida revisable:** evidencia de prerrequisitos y estimación de costo; decisiones pendientes actualizadas en `specs/tech.md`. **Cubre:** INF-01, INF-07, INF-08, INF-09. **Bloquea:** grupos 1 y 2 si faltan facturación, permisos, IP autorizada o versión compatible.

## Grupo 1 — Red y estado

1. Diseñar VPC, subred y rangos secundarios en `us-central1` para GKE sin solapamientos con redes existentes.
2. Definir APIs y permisos mínimos necesarios y cómo se protegerá el estado Terraform.
3. Preparar la futura configuración de red y revisar formato, validación y plan sin crear recursos.

**Salida revisable:** diff y plan de VPC/subred, con nombres, rangos y costos identificados. **Cubre:** INF-02 y parte de INF-08. **Depende de:** grupo 0.

## Grupo 2 — GKE y pools

1. Preparar la futura configuración de GKE Standard zonal en `us-central1-a`, con `COS_CONTAINERD` y Master Authorized Networks limitado al CIDR del operador.
2. Definir pool CPU de un `e2-standard-4` y pool GPU de un `g2-standard-4` con una L4; ambos con boot disk `pd-balanced` de 50 GB.
3. Configurar instalación administrada de drivers NVIDIA, etiquetas y taints del pool GPU; definir el contrato de tolerations para la entrega de serving. Evitar instalación manual, Docker en nodos y GPU Operator.
4. Validar sintaxis y revisar el plan consolidado, recursos y costo. Presentarlo para revisión humana **antes** de cualquier `apply`.

**Salida revisable:** plan completo y revisión registrada. **Cubre:** INF-03 a INF-07 e INF-09. **Depende de:** grupos 0 y 1.

## Grupo 3 — Acceso y validación operativa

Tras el despliegue autorizado en una sesión futura, obtener credenciales GKE, inspeccionar la lista de CIDR autorizados y verificar que el operador puede usar `kubectl`. Comprobar nodos Ready, tipo de máquina, boot disk, imagen/versión de nodo, driver efectivo y GPU asignable. Registrar salidas y discrepancias por ID en `validation.md`. El modelo y la aplicación corresponden a entregas posteriores.

**Cubre:** INF-03 a INF-08. **Depende de:** grupo 2 y despliegue autorizado.

## Grupo 4 — Limpieza y cierre

Eliminar primero cualquier carga o recurso Kubernetes creado en la sesión mientras el clúster sea accesible; esperar la eliminación de recursos cloud asociados. Revisar el plan de destrucción, ejecutar el cierre autorizado y comprobar inventario de clúster, nodos, discos, IP, redes y otros recursos facturables. Registrar remanentes, costo observado y evidencia en `validation.md`.

**Cubre:** INF-10. **Depende de:** grupo 3 o de cualquier sesión que haya creado recursos.

## Control de cambios

Implementar los grupos en orden. Si una comprobación contradice un supuesto, detener el grupo afectado, actualizar especificaciones y revisar de nuevo el plan. No avanzar con un PASS inferido de una estimación o de la mera creación de archivos.
