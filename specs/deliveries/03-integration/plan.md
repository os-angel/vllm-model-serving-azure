# 03 — Integración: plan

**Estado:** APROBADO por el propietario; iniciar Grupo 1. Releer requisitos al iniciar cada grupo. El README exige revisión humana y commit de especificaciones revisadas antes del código.

## Grupo 0 — Revisar diseño

- 0.1 Elegir tecnología y revisar contrato backend/navegador, streaming, estado y errores. Cubre INT-01–INT-04, INT-09.
- 0.2 Resolver estimación de caracteres aprobada, truncamiento, parámetros, razonamiento y límites operativos. Cubre INT-05–INT-06.
- 0.3 Proponer recursos CPU y ruta de build/registry; identificar recursos facturables y responsabilidades de limpieza. Cubre INT-07, INT-10–INT-11.

Salida: decisiones registradas, requisitos y plan revisados; crear rama independiente `03-integration` y registrar especificaciones aprobadas antes de implementar. No incorporar archivos ajenos al commit.

## Grupo 1 — Backend y chat local

- 1.1 Configuración de endpoint/modelo y consumo por SDK; validar parámetros. INT-01, INT-05.
- 1.2 Historial, nueva conversación, presupuesto estimado y presentación segura de texto. INT-02, INT-06, INT-09.
- 1.3 Streaming progresivo con finalización y truncamiento explícitos. INT-03.
- 1.4 Estado, timeout, desconexión, reintento manual y logs sin contenido. INT-04, INT-09.

Salida: pruebas locales de payloads, fronteras de contexto, streaming y errores con servidor controlado; evidencias separadas de las pruebas reales GKE.

## Grupo 2 — Empaquetado y manifiestos

- 2.1 Dependencias fijadas, Dockerfile, Deployment CPU, Service ClusterIP y probes; comprobar build y configuración. INT-07, INT-10.
- 2.2 Preparar instrucciones y plan concreto de publicación/despliegue con costo incremental y eliminación de imágenes/registry. INT-10–INT-11.

Salida: diff y artefactos revisables. Antes de despliegue facturable, presentar recursos y costo al propietario; no aplicar sin revisión.

## Grupo 3 — Integración real y revisión

- 3.1 Tras autorización, verificar pod CPU, DNS interno, salud, respuesta desde aplicación y SDK independiente. INT-01, INT-07–INT-08.
- 3.2 Probar varios turnos, parámetros, nueva conversación y fragmentos progresivos en navegador. INT-02–INT-03, INT-05.
- 3.3 Probar contexto excedido, indisponibilidad y stream interrumpido sin reiniciar vLLM; revisar logs y presentación segura. INT-04, INT-06, INT-09.
- 3.4 Registrar matriz por requisito, limitaciones y revisión humana. Preparar limpieza de aplicación; cierre de sesión incluye cargas/PVC, Terraform e inventario de remanentes. INT-11.

Salida: comportamiento observado y evidencia por ID. Los fallos de calidad heredados se conservan; fase 03 no acredita capacidad, rendimiento ni calidad del modelo.
