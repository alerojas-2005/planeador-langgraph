# Evidencias de las pruebas · Taller 1 (LangGraph)

Las pruebas se ejecutaron el 22 de noviembre de 2026 en el computador de Paula (Windows, Python 3.14.6, Ollama local con `qwen2.5:3b`). La bitácora (`../bitacora.pdf`) resume estos archivos.

| Archivo | Contenido |
|---|---|
| `salida_pytest_windows.txt` | Pruebas de las herramientas sin modelo: 23 de 23 aprobadas. |
| `salida_pytest_entorno_linux.txt` | La misma prueba en un entorno Linux: 23 de 23 aprobadas. |
| `modelo_ollama_show.txt` | `ollama show qwen2.5:3b`: confirma la capacidad `tools`. |
| `resultados_langgraph.md` / `.json` | Salida de `tests/ejecutar_pruebas.py`: traza, herramientas llamadas y tiempo de cada una de las seis preguntas. La columna de verificación es automática. |
| `revision_manual_langgraph.md` | **Revisión manual de las seis preguntas (es la válida)**, traza completa de la pregunta 4, causas de los fallos y comprobación desde el frontend. |
| `evidencia_reto_memoria.md` / `.json` | Reto de memoria conversacional por script (dos turnos con el mismo `thread_id`). |
| `revision_manual_reto.md` | Revisión manual del reto, por script y desde el frontend. |
| `frontend_pregunta3.png`, `frontend_pregunta3_traza_uvicorn.png` | Punto de control 6: la pregunta 3 respondida desde el navegador y su traza en uvicorn. |
| `api_docs_fastapi.png` | Documentación de la API en `/docs` (`POST /api/v1/chat`, `GET /health/llm`). |
| `reto_frontend_turno1.png`, `reto_frontend_dos_turnos.png`, `reto_frontend_traza_uvicorn.png` | Reto de memoria desde el frontend y su traza. |

Para repetir las pruebas: `correr_pruebas.bat` en la raíz del repositorio, o `python -m pytest tests/test_herramientas.py -v` y `python -m tests.ejecutar_pruebas --reto --salida docs/evidencias`.

## Ejecución desde el frontend usada en la bitácora

`resultados_frontend.md` resume la tabla de la bitácora y relaciona cada pregunta con sus pantallazos: `frontend_p1.png` a `frontend_p6.png`, `traza_uvicorn_p1.png`, `traza_uvicorn_p2_p3_p4.png`, `traza_uvicorn_p3_a_reto.png` y `reto_frontend_v2.png`. También están `api_docs_post_chat.png`, `descarga_modelo_qwen.png` y `pytest_23_passed_consola.png`.
