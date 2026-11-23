# Resultados desde el frontend · Taller 1 (LangGraph)

Estas son las ejecuciones que usa la bitácora (`../bitacora.pdf`, Tabla 2 y Fig. 3–5). Las hicimos el 22 de noviembre de 2026 desde http://localhost:4200, con la API en `uvicorn backend.src.api:app --port 8080`, recargando la página antes de cada pregunta. El tiempo es el de backend que muestra el frontend.

| # | Agentes que llamó el supervisor (esperados) | ¿Correcta? | Tiempo (s) | Pantallazo de la respuesta | Pantallazo de la traza |
|---|---|---|---:|---|---|
| 1 | clima (clima) | Parcial: omite el 80 % de lluvia | 61,1 | `frontend_p1.png` | `traza_uvicorn_p1.png` |
| 2 | presupuesto (presupuesto) | Sí | 70,3 | `frontend_p2.png` | `traza_uvicorn_p2_p3_p4.png` |
| 3 | clima (clima, presupuesto) | No: sin costo | 42,8 | `frontend_p3_v2.png` | `traza_uvicorn_p2_p3_p4.png` |
| 4 | clima (clima, presupuesto, reservas) | No: código inventado «LAR250000» | 51,5 | `frontend_p4.png` | `traza_uvicorn_p2_p3_p4.png` |
| 5 | clima, presupuesto (presupuesto) | Parcial | 78,0 | `frontend_p5.png` | `traza_uvicorn_p3_a_reto.png` |
| 6 | ninguno (ninguno) | Sí | 19,0 | `frontend_p6.png` | `traza_uvicorn_p3_a_reto.png` |
| Reto | clima, en los dos turnos | La memoria resuelve «¿Y el domingo?»; datos del domingo correctos, sin el 70 % | 49,2 / 51,0 | `reto_frontend_v2.png` | `traza_uvicorn_p3_a_reto.png` |

La ejecución previa por script (`resultados_langgraph.md` y `revision_manual_langgraph.md`) dio las mismas decisiones y respuestas en P1–P6, con temperatura 0. En dos intentos anteriores del reto desde el frontend (`reto_frontend_dos_turnos.png`, `reto_frontend_traza_uvicorn.png`), el sistema entendió la referencia, pero respondió el domingo con los datos del sábado.
