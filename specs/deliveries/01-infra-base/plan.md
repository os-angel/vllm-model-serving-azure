# 01 — Infraestructura base: plan

**Estado:** entrega aprobada operativamente por el propietario el 2026-10-04 para avanzar a serving. INF-01–INF-06 e INF-08 tienen evidencia PASS; INF-07 se transfiere a la validación de caché durante la entrega 02 e INF-10 al cierre final del laboratorio. El propietario reportó `terraform apply` exitoso y confirmó el clúster, pools, driver, red y acceso. El Grupo 4 queda pospuesto expresamente; no destruir infraestructura durante la sesión continua autorizada.

## Grupo 0 — Cerrar entradas y costo

1. Usar `us-central1-a` como zona principal y conservar evidencia reciente de facturación, cuota regional L4, oferta G2/L4, cuotas CPU/IP y APIs necesarias. La capacidad efectiva se observará al crear el nodo. Si falla, evaluar `us-central1-b/c` mediante plan nuevo revisado.
2. Planear discos de arranque `pd-balanced` de 50 GB para ambos nodos y estimar espacio para imágenes/caché. Evaluar 80–100 GB en GPU solo si las pruebas posteriores muestran saturación.
3. Elegir canal/parche GKE, versión COS y estrategia de driver administrado. Comprobar compatibilidad prevista con el contenedor vLLM antes de fijar versiones.
4. Obtener la IP pública actual del operador para Master Authorized Networks, definir salida a registros/modelo, permisos mínimos, ubicación del estado Terraform y presupuesto de sesión.

**Salida revisable:** evidencia de prerrequisitos y estimación de costo; decisiones pendientes actualizadas en `specs/tech.md`. **Cubre:** INF-01, INF-07, INF-08, INF-09. **Bloquea:** grupos 1 y 2 si faltan facturación, permisos, IP autorizada o versión compatible.

| Tarea del Grupo 0 | Requisito | Comprobación observable |
|---|---|---|
| 0.1 Proyecto, facturación, cuotas, oferta y APIs | INF-01 | Consultas `gcloud` recientes; capacidad física sigue para despliegue futuro. |
| 0.2 Disco y espacio | INF-07 | Tamaño publicado del checkpoint y cálculo de espacio; uso real sigue para nodo futuro. |
| 0.3 Canal, parche, COS y driver | INF-03, INF-06 | Documentación y consulta `get-server-config`; mapeo y driver efectivos siguen para nodo futuro. |
| 0.4 CIDR, salida, permisos, estado y presupuesto | INF-08, INF-09 | Decisiones registradas, estimación con fuentes y revisión antes de `apply`. |

La evidencia y los límites constan en [group-0.md](group-0.md) y [validation.md](validation.md). El propietario eligió IPv4 efímeras y estado local fuera de Git. El CIDR dinámico se proporcionará como entrada no versionada antes de cada plan. Se habilitó Kubernetes Engine API con autorización, se comprobó el parche Stable candidato y la lista pública COS/driver, y se probaron permisos efectivos principales. La versión del nodo y la compatibilidad real se validarán después del despliegue autorizado.

## Grupo 1 — Red y estado

1. Diseñar VPC, subred y rangos secundarios en `us-central1` para GKE sin solapamientos con redes existentes.
2. Definir APIs y permisos mínimos necesarios y cómo se protegerá el estado Terraform.
3. Preparar la futura configuración de red y revisar formato, validación y plan sin crear recursos.

**Salida revisable:** diff y plan de VPC/subred, con nombres, rangos y costos identificados. **Cubre:** INF-02 y parte de INF-08. **Depende de:** grupo 0.

| Tarea del Grupo 1 | Requisito | Comprobación observable |
|---|---|---|
| 1.1 Inventario y rangos | INF-02 | Inventario `gcloud` de VPC/subredes/rutas y cálculo de solapamiento para `10.80.0.0/20`, `10.81.0.0/20`, `10.82.0.0/22`. |
| 1.2 APIs, permisos y estado | INF-02, INF-09 | APIs habilitadas, permisos efectivos principales comprobados, backend local y exclusiones de Git verificados. |
| 1.3 VPC y subred en Terraform | INF-02, INF-08 | `terraform fmt -check`, `validate` y plan con exactamente una VPC y una subred con dos secundarios; sin GKE, NAT ni `apply`. |

**Decisión de diseño:** crear `nemotron-lab-vpc` y `nemotron-lab-us-central1` con los tres rangos indicados en [tech.md](../../tech.md). Esta decisión se registra antes de escribir Terraform. Usar provider Google fijado y archivo de bloqueo versionado.

**Resultado:** [group-1.md](group-1.md) registra inventario, diff, plan `2 to add`, verificaciones y límites. No hubo `apply`.

## Grupo 2 — GKE y pools

1. Preparar la futura configuración de GKE Standard zonal en `us-central1-a`, con `COS_CONTAINERD` y Master Authorized Networks limitado al CIDR del operador.
2. Definir pool CPU de un `e2-standard-4` y pool GPU de un `g2-standard-4` con una L4; ambos con boot disk `pd-balanced` de 50 GB.
3. Configurar instalación administrada de drivers NVIDIA, etiquetas y taints del pool GPU; definir el contrato de tolerations para la entrega de serving. Evitar instalación manual, Docker en nodos y GPU Operator.
4. Validar sintaxis y revisar el plan consolidado, recursos y costo. Presentarlo para revisión humana **antes** de cualquier `apply`.

**Salida revisable:** plan completo y revisión registrada. **Cubre:** INF-03 a INF-07 e INF-09. **Depende de:** grupos 0 y 1.

| Tarea del Grupo 2 | Requisito | Comprobación observable |
|---|---|---|
| 2.1 Clúster zonal y acceso | INF-01, INF-03, INF-08 | Plan identifica proyecto/zona, versión/canal, rangos VPC-native y solo el CIDR `/32` vigente para el endpoint. |
| 2.2 Cuenta de servicio y pool CPU | INF-04, INF-07 | Plan muestra cuenta con rol mínimo, un `e2-standard-4` y `pd-balanced` 50 GB. |
| 2.3 Pool GPU y contrato de scheduling | INF-05, INF-06, INF-07 | Plan muestra un `g2-standard-4`, una `nvidia-l4`, driver `DEFAULT`, etiqueta, taint y disco de 50 GB; contrato de toleration documentado. |
| 2.4 Validación y revisión de costo | INF-03–INF-09 | `fmt`, `validate`, plan consolidado y estimación registrados con sus límites; revisión humana antes de `apply`. |

**Resultado:** [group-2.md](group-2.md) registra el plan `7 to add`, la comprobación de configuración, costo y límites. El propietario aprobó el plan y la estimación el 2026-10-03 y reportó `apply` exitoso el 2026-10-04. La comprobación operativa está registrada en [validation.md](validation.md); INF-07 se transfiere a serving.

## Grupo 3 — Acceso y validación operativa

Tras el despliegue reportado, obtener credenciales GKE, inspeccionar la lista de CIDR autorizados y verificar que el operador puede usar `kubectl`. Comprobar nodos Ready, tipo de máquina, boot disk, imagen/versión de nodo, driver efectivo y GPU asignable. Registrar salidas y discrepancias por ID en `validation.md`. El modelo y la aplicación corresponden a entregas posteriores.

**Cubre:** INF-03 a INF-08. **Depende de:** grupo 2 y despliegue autorizado.

| Tarea del Grupo 3 | Requisito | Comprobación observable |
|---|---|---|
| 3.1 Inventario y acceso al control | INF-03, INF-08 | Clúster existente, lista de CIDR `/32` autorizados, acceso `kubectl` desde la red del operador y ausencia de Service `LoadBalancer` del laboratorio. |
| 3.2 Nodos y discos | INF-03, INF-04, INF-05, INF-07 | Dos nodos Ready en los pools correctos; tipos, versiones, imagen, discos y uso real observados. |
| 3.3 GPU y driver | INF-05, INF-06 | Configuración de instalación administrada, etiqueta y taint efectivos, `nvidia.com/gpu: 1` asignable y versión del driver observada en el nodo. |
| 3.4 Evidencia y discrepancias | INF-03–INF-08 | Registro por ID de salidas resumidas, fecha, estado y limitaciones en `validation.md`; sin PASS inferido del plan. |

El procedimiento y las salidas aportadas por el propietario se registran en [group-3.md](group-3.md) y [validation.md](validation.md). Las tareas 3.1–3.4 confirmaron control, nodos, red, driver y GPU. INF-07 queda como dependencia para la descarga del modelo; INF-10 se reserva para el cierre final por decisión del propietario.

## Grupo 4 — Limpieza y cierre

Eliminar primero cualquier carga o recurso Kubernetes creado en la sesión mientras el clúster sea accesible; esperar la eliminación de recursos cloud asociados. Revisar el plan de destrucción, ejecutar el cierre autorizado y comprobar inventario de clúster, nodos, discos, IP, redes y otros recursos facturables. Registrar remanentes, costo observado y evidencia en `validation.md`.

**Cubre:** INF-10. **Depende de:** grupo 3 o de cualquier sesión que haya creado recursos.

## Control de cambios

Implementar los grupos en orden. Si una comprobación contradice un supuesto, detener el grupo afectado, actualizar especificaciones y revisar de nuevo el plan. No avanzar con un PASS inferido de una estimación o de la mera creación de archivos.
