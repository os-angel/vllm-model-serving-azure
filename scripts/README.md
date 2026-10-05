# Validación de serving

Desde la raíz del repositorio, con `uv`, `kubectl` y `gcloud` disponibles y el contexto Kubernetes apuntando a `nemotron-lab`:

```bash
uv run --no-project python scripts/validate-serving.py --install-sdk --with-recovery
```

`--with-recovery` elimina y recrea el pod existente: interrumpe temporalmente el servicio. Espera hasta 30 minutos por Ready y comprueba de nuevo la API. No elimina el PVC ni la infraestructura.

Para comprobar el servicio sin recrearlo:

```bash
uv run --no-project python scripts/validate-serving.py --install-sdk
```

El script abre y cierra su propio port-forward en un puerto local disponible. El SDK se instala mediante `uv venv` y `uv pip install` en `.local/validation-venv`; se registra la versión usada. La evidencia privada y `report.md` se guardan en `.local/serving-validation/<fecha-hora>/`, ignorado por Git. No modifica automáticamente `validation.md`.

Captura configuración, revisiones, GPU/RAM/disco, estado del PVC, eventos, logs, health, modelos, chat y SSE. Guarda tiempos de llegada de los eventos y prueba el SDK. Con recuperación, compara UID/PV y rutas, tamaños y hashes SHA256 completos de pesos, observando pods cada cinco segundos.

El reporte distingue fallos, resultados parciales y pendientes. Revisar el contenido de las respuestas, logs y ruta efectiva de código remoto; no declarar terminada la fase por un código de salida 0. El espacio anterior al pull y las mediciones sostenidas no pueden reconstruirse con esta ejecución. Los logs capturados se conservan privados y requieren revisión antes de compartirlos.

Pruebas locales del validador:

```bash
uv run --no-project python -m unittest discover -s scripts -p 'test_*.py'
```

Contrato de API y calidad se reportan por separado. `EVIDENCIA` representa capturas, no aceptación. `results.json` permite revisar resultados automáticamente; salida 1 indica FAIL y 2 indica PARCIAL/PENDIENTE. Siempre revisar la matriz por SRV y las limitaciones antes de cerrar la entrega.

Comparación final con razonamiento y presupuesto mayor, sin recrear pod:

```bash
uv run --no-project python scripts/validate-serving.py --install-sdk --reasoning on --max-tokens 2048
```

Este perfil usa `/think`, temperatura 0.6 y top_p 0.95. Guarda `protocol.json` y evalúa calidad sobre la respuesta final después de `</think>`, sin borrar el razonamiento de la evidencia. Si falta el marcador o respuesta final, registra FAIL. No sustituye la ejecución base ni su prueba de recuperación.

La entrega 02 fue cerrada por el propietario con limitaciones aceptadas el 2026-10-04. El validador conserva FAIL/PARCIAL y sus códigos de salida; aprobación de entrega no implica pruebas todas verdes. Evidencia y aceptación en `specs/deliveries/02-serving/validation.md`.
