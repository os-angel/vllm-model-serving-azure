# Aprendizaje — Retrospectiva de la fase 03

La fase 03 quedó cerrada por el propietario con el fallo de recuperación del serving aceptado. La infraestructura fue eliminada al finalizar la sesión. Esta retrospectiva se basa en [la validación real](specs/deliveries/03-integration/validation.md); distingue omisiones del plan, detalles operativos insuficientes y problemas del procedimiento de pruebas.

## Qué faltó contemplar desde el inicio

### 1. Cancelar una respuesta puede afectar al motor de inferencia

El plan sí incluía cancelación, stream interrumpido y reintento manual. Faltó tratar esos escenarios como pruebas de estabilidad del motor, además de pruebas de interfaz. Durante la ejecución, vLLM registró `IndexError: pop from empty list` en la caché Mamba y tuvo dos reinicios automáticos. El navegador mostró el error y evitó duplicar turnos, pero el reintento no completó la inferencia.

Para una próxima entrega, validar primero una secuencia pequeña: petición completada, cancelación, comprobación de salud y nueva petición que termine correctamente. Registrar UID, restartCount y respuesta después de cada paso. Un SDK compatible con OpenAI y una respuesta inicial correcta no demuestran que la combinación modelo/runtime gestione bien abortos. La causa concreta del fallo observado permanece sin confirmar.

### 2. Las pruebas debían tener orden y barreras explícitas

El serving estaba configurado con una secuencia activa. Sin embargo, el plan no especificaba cómo coordinar los clientes de validación ni cuándo empezar la siguiente prueba. Dos comprobaciones finales iniciaron peticiones solapadas; el primer fallo del motor coincidió con esa ejecución. Eso no demuestra que el solapamiento sea la causa. La segunda caída ocurrió al interrumpir y reintentar un stream después de recuperar serving.

Desde el inicio debió quedar establecido: pruebas funcionales de inferencia secuenciales, barrera de finalización entre casos y detención de nuevas peticiones si falla la salud. Reservar las pruebas simultáneas para un protocolo separado, con condiciones y resultados identificables. `max-num-seqs=1` no coordina los procesos de prueba externos.

### 3. Faltaba un protocolo operativo de fallos controlados

La indisponibilidad y el timeout estaban previstos, pero faltaba concretar cómo provocarlos sin alterar vLLM, cómo restaurar el chat y cómo demostrar que quedó restaurado. Fue necesario cambiar temporalmente la URL del backend y su timeout, hacer rollouts y reconectar los port-forwards. Para la desconexión inesperada se interrumpió un port-forward propio.

La próxima planificación debe incluir un procedimiento con restauración garantizada aunque falle una aserción: capturar configuración inicial, provocar un solo fallo, comprobar la interfaz, restaurar, comparar contra el manifiesto y verificar salud. Separar cancelación voluntaria, pérdida de transporte y caída del serving: pueden verse parecidas en pantalla, pero ejercitan rutas distintas.

### 4. Había que validar los fixtures antes de consumir GPU

La fórmula de presupuesto y las pruebas de frontera sí estaban aprobadas. El problema fue del procedimiento: el primer historial sintético, con dos mensajes de 8000 caracteres y salida reservada de un token, no superaba el presupuesto; por tanto, esperar su recorte era incorrecto. Se corrigió a 8300 caracteres por mensaje. Otro intento de preparar historial desde el navegador no produjo el payload esperado; el aviso se comprobó después inyectando explícitamente el historial sintético en la petición real.

Antes de GKE, comprobar la aritmética de cada fixture y capturar el payload que realmente saldrá del navegador. Identificar los datos sintéticos como tales. Mantener las ejecuciones fallidas y sus correcciones en la evidencia; no cambiar el requisito ni culpar al backend por una expectativa de prueba equivocada.

### 5. El preflight local necesitaba más comprobaciones

El empaquetado estaba previsto, pero al retomar el trabajo el tag local del grupo 2 ya no existía y hubo que reconstruir la imagen. Los puertos 8000 y el IPv4 de 8080 estaban ocupados; se usaron puertos aislados. `uv` y Terraform también requirieron acceso fuera del sandbox para sus cachés/provider o las consultas cloud.

Incluir un preflight reproducible: imagen local disponible o ruta de reconstrucción, arquitectura/digest, Docker activo, entorno de `uv`, Chromium disponible, puertos libres y permisos de herramientas. No asumir que el estado local de un grupo anterior continúa intacto ni detener procesos ajenos para liberar un puerto. Un port-forward debe reconectarse cuando el rollout sustituye el pod al que estaba unido.

### 6. Faltaba una matriz real de perfiles de razonamiento y salida

El plan sí definía `/no_think` y 1024 como valores iniciales, y `/think` seleccionable. La conversación y el SDK que completaron técnicamente se probaron con `/think` y 2048 tokens. Eso no acredita que el perfil inicial termine bien, ni que cambiar el razonamiento corrija la calidad. En el segundo turno, el modelo volvió a responder sobre París cuando se preguntaba por el país; transmitir historial correctamente no garantiza usarlo correctamente.

Planificar casos reales separados para los perfiles inicial y alternativo. Evaluar por separado transmisión de parámetros, finalización y contenido de la respuesta. Mostrar el razonamiento como texto no sustituye una evaluación de la respuesta final ni debe consumir un presupuesto que se suponga disponible íntegramente para ella.

### 7. La aceptación parcial y el cierre necesitaban una salida explícita

El plan exigía revisión humana y limpieza, pero faltaba concretar qué hacer si la aplicación cumple y el serving falla en recuperación. El propietario aceptó expresamente esa limitación y cerró la fase. Se conservó INT-04 PARCIAL y el fallo observado; la aprobación no convirtió el resultado en PASS ni autorizó implícitamente cambiar vLLM.

Definir de antemano las opciones de salida: corregir dentro del alcance, proponer una intervención sobre serving, o aceptar una limitación documentada. Después actualizar estado, crear el commit y decidir explícitamente si la sesión cloud continúa o se destruye. Así se evita prolongar pruebas y costos sin una decisión sobre el objetivo pendiente.

## Lo que sí estaba en el plan y se confirmó

La limpieza de cargas Kubernetes y PVC antes de Terraform, la revisión de costo antes de desplegar y la búsqueda de remanentes fuera del estado **ya eran requisitos**. No fueron descubrimientos nuevos. La ejecución reforzó que deben tener comprobaciones concretas: PV/disco ausentes antes de borrar GKE, plan de diez recursos destruido, estado vacío e inventario final sin recursos del laboratorio. El proceso completo incluyó varios minutos de espera por GKE; enviar el comando no significaba que la eliminación hubiera terminado.

El inventario final no es una factura. Permite afirmar que no se observaron recursos del laboratorio en las categorías consultadas; no permite certificar un costo acumulado de USD 0 ni descartar cargos anteriores que todavía no aparezcan en facturación. APIs habilitadas, logs históricos, evidencia privada e imagen local quedaron como remanentes intencionales.

Las pruebas locales simuladas también estaban previstas. Resultaron útiles para presupuesto, payloads y presentación de texto, pero no detectaron el fallo de caché Mamba que apareció con inferencia real. Conviene probar un recorrido real mínimo y su recuperación antes de ampliar toda la batería de navegador.
