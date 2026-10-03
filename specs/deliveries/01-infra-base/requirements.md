# 01 — Infraestructura base: requisitos

## Estado y propósito

**Estado:** especificación propuesta; sin Terraform, despliegue ni evidencia operativa. Esta entrega prepara la plataforma mínima para la entrega de serving. Se rige por [mission.md](../../mission.md), [tech.md](../../tech.md) y [roadmap.md](../../roadmap.md).

## Alcance

VPC y subred de laboratorio, clúster GKE Standard en `us-central1-a`, un pool CPU y un pool GPU G2/L4 de un nodo cada uno, imagen `COS_CONTAINERD`, drivers GPU administrados por GKE, endpoint público de control restringido por Master Authorized Networks y procedimiento de limpieza verificable. La infraestructura se gestionará con Terraform cuando se autorice su implementación.

## Exclusiones

No incluye vLLM, descarga del modelo, aplicación, Service de inferencia, mediciones de rendimiento, VPN, alta disponibilidad, autoscaling, LoadBalancer público ni GPU Operator. No se copiará la instalación de Docker de una VM Ubuntu: los nodos GKE usarán imagen administrada y containerd. Tampoco se trasladará GPU Operator de AKS: se eligió la instalación administrada de drivers de GKE. Cualquier cambio de este enfoque requiere una justificación y revisión de `tech.md`.

## Dependencias y decisiones por cerrar

- **Confirmado por el propietario:** proyecto `llmresearch-510422`; zona principal `us-central1-a`; cuota regional activa de una L4 y oferta del acelerador en `us-central1-a/b/c` observadas con `gcloud`; L4 de 24 GB nominales; discos de arranque `pd-balanced` de 50 GB en ambos nodos. Esta especificación no incluye salidas de `gcloud` ni prueba de capacidad física.
- **Zonas de respaldo:** `us-central1-b` y `us-central1-c` solo si falla la capacidad en la zona principal; cualquier cambio exige actualizar la zona de Terraform, revisar el plan y su costo antes de aplicar. La cuota regional no reserva una L4.
- **Almacenamiento:** si imagen y pesos saturan el nodo GPU, evaluar 80–100 GB `pd-balanced` mediante cambio revisado. `pd-standard` no es una opción para G2.
- **Candidato técnico documentado:** canal Stable `1.35.6-gke.1250000` disponible en `us-central1-a` el 2026-10-03, asociado en documentación pública a `cos-125-19216-395-109`; para L4, la lista de COS etiqueta `580.159.04` como driver `DEFAULT`. Confirmar disponibilidad antes del plan y observar COS y driver efectivos tras crear el nodo. La compatibilidad con vLLM sigue pendiente de prueba.
- **Decisión del propietario (2026-10-03):** nodos con IPv4 externas efímeras para descargar imágenes y pesos; estado Terraform local en este equipo, excluido de Git. No se usarán Cloud NAT ni un backend remoto en esta entrega. El estado local debe conservarse hasta completar `destroy` y la comprobación de limpieza.
- **CIDR del operador:** la IP es dinámica. Confirmar la IPv4 de salida desde la red de `kubectl` inmediatamente antes de cada plan y pasarla como CIDR `/32` mediante entrada no versionada. No incluir la dirección concreta en documentación ni código de Git. Comprobar permisos de creación. Las IPv4 de los nodos no amplían el acceso al endpoint de control ni justifican un LoadBalancer de inferencia.
- **Diseño del Grupo 1 (2026-10-03):** VPC propia `nemotron-lab-vpc`, subred `nemotron-lab-us-central1` en modo personalizado, primario `10.80.0.0/20`, secundario Pods `10.81.0.0/20` y secundario Services `10.82.0.0/22`. La red `default` existente queda fuera de Terraform. El inventario de subredes del proyecto no mostró solapamientos; redes externas no inventariadas siguen como límite.

## Requisitos y criterios de aceptación

| ID | Requisito | Criterio observable |
|---|---|---|
| INF-01 | La configuración apunta al proyecto y zona aprobados. | Plan identifica `llmresearch-510422` y `us-central1-a`; se conserva evidencia de facturación, cuota y oferta G2/L4. La capacidad real se confirma al crear el nodo. Cambiar a `us-central1-b/c` requiere un plan nuevo revisado. |
| INF-02 | Crear VPC y subred para el laboratorio bajo Terraform. | Plan e inventario muestran VPC, subred y rangos secundarios necesarios para el clúster; no hay solapamientos conocidos. |
| INF-03 | Crear un clúster GKE Standard zonal con imagen administrada `COS_CONTAINERD`. | Plan fija canal/parche elegidos; clúster y nodos reportan versiones e imagen efectivas. |
| INF-04 | Crear un pool CPU de un nodo `e2-standard-4`. | Un nodo CPU está Ready y su tipo, tamaño de disco y pool coinciden con el plan. |
| INF-05 | Crear un pool GPU de un nodo `g2-standard-4` con una L4. | Un nodo GPU está Ready, coincide con el plan y anuncia `nvidia.com/gpu: 1` asignable. |
| INF-06 | Usar drivers NVIDIA administrados por GKE y reservar el pool GPU para cargas que los soliciten. | Configuración y versión de driver observadas; etiquetas/taints del pool definidos y ausencia de instalación paralela manual u Operator. Las tolerations de vLLM se validarán en la entrega 02. |
| INF-07 | Usar discos de arranque compatibles y comprobar espacio para la siguiente entrega. | El plan muestra `pd-balanced` de 50 GB en cada nodo; se registra uso real y ruta de caché antes de servir el modelo. Aumentar GPU a 80–100 GB requiere evidencia de saturación y plan revisado. |
| INF-08 | Restringir el endpoint público de control GKE a la IP del operador y mantener las cargas internas. | La lista de clientes de Master Authorized Networks incluye solo el CIDR autorizado del operador, sin `0.0.0.0/0`; `kubectl` consulta nodos con credenciales autorizadas; no existe LoadBalancer público de inferencia. |
| INF-09 | Revisar recursos y costo antes de cualquier `apply`. | Plan y estimación de costo presentados para revisión; aprobación registrada antes de crear recursos facturables. |
| INF-10 | Limpiar las cargas y la infraestructura al cerrar la sesión. | Tras el cierre, inventario y estado confirman ausencia de clúster, pools, discos, IP y otros recursos facturables del laboratorio; remanentes se documentan. |

## Regla de evidencia

Cada criterio se vincula con su fila en [validation.md](validation.md). Un comando exitoso o un plan sin despliegue solo valida la parte que observa; no demuestra por sí mismo GPU operativa, costo real ni limpieza. Los estados permitidos son **PENDIENTE**, **PASS**, **FAIL** y **BLOQUEADO**, acompañados por fecha, comando o fuente, salida resumida y limitaciones.
