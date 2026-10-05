# 03 — Integración: validación

**Estado:** PLAN APROBADO; Grupo 1 autorizado, implementación y pruebas pendientes.

## Inicio

Se leyeron README, AGENTS, misión, diseño técnico, roadmap y especificaciones/evidencia de las entregas anteriores. No existía directorio de entrega 03. Rama observada: `02-serving`. Archivos ajenos sin seguimiento: `AGENTS.md`, `Aprendizajes.md`, `Diagrama.md`; conservados.

La evidencia de serving procede de fase 02; no se consultó nuevamente GCP ni se verificó disponibilidad actual. No se crearon recursos cloud, no se ejecutó apply y no se cerró la sesión continua del laboratorio.

## Matriz

Decisión recibida del propietario: backend FastAPI, priorizando facilidad de prueba. Esta aprobación de tecnología no equivale a aprobación completa del borrador ni a evidencia funcional.

| ID | Comprobación prevista | Resultado y evidencia |
|---|---|---|
| INT-01 | DNS interno, SDK backend y respuesta real. | PENDIENTE: aplicación sin implementar. |
| INT-02 | Payload de varios turnos y reinicio de conversación. | PENDIENTE: aplicación sin implementar. |
| INT-03 | Fragmentos visibles y estados de cierre/truncamiento. | PENDIENTE: aplicación sin implementar. |
| INT-04 | Salud separada, timeout, desconexión y reintento. | PENDIENTE: aplicación sin implementar. |
| INT-05 | Validación de controles y parámetros enviados. | PENDIENTE: rangos y valores por revisar. |
| INT-06 | Estimación de caracteres, fronteras y retiro de turnos completos. | PENDIENTE: método por resolver y aprobar. |
| INT-07 | Scheduling CPU, recursos, probes y acceso interno. | PENDIENTE: manifiestos y autorización de despliegue. |
| INT-08 | Cliente SDK independiente: chat y streaming. | PENDIENTE: ejecutar protocolo específico 03. |
| INT-09 | Logs sin contenido, texto seguro e historial efímero. | PENDIENTE: implementación y revisión. |
| INT-10 | Build reproducible, versiones/digest e instrucciones. | PENDIENTE: tecnología y destino de imagen por revisar. |
| INT-11 | Revisión de recursos/costo y evidencia de limpieza. | PENDIENTE: plan concreto de despliegue y cierre final. |

Para cada ejecución registrar fecha/hora, tarea, comando o procedimiento, resultado observado, ubicación de evidencia y límites. Pruebas simuladas no acreditan integración real. Crear estos documentos no acredita ningún requisito funcional.

## Aprobación del plan

El propietario aprobó fase 03, FastAPI en CPU, estimación aproximada de cuatro caracteres por token y límite 4096, rama `03-integration` y commit de especificaciones antes del Grupo 1. No autoriza despliegue facturable todavía. Se conserva como límite que el presupuesto estimado puede diferir del tokenizer real.
