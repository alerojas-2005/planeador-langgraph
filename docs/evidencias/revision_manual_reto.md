# Taller 1 · Revisión manual del reto: memoria conversacional

- **Ejecución:** 22 de noviembre de 2026, computador de Paula, modelo `qwen2.5:3b`.
- **Conversación:** `thread_id = reto-memoria-2ee74a49`, el mismo en los dos turnos.
- **Evidencia original:** `evidencia_reto_memoria.md` y `evidencia_reto_memoria.json`, en esta misma carpeta.

## Prueba 1 · Por script (`EJECUTAR_TALLER1_LangGraph.bat`): la memoria funciona

| Turno | Pregunta | Herramienta llamada | Resultado de la herramienta | Tiempo |
|---|---|---|---|---:|
| 1 | ¿Cómo estará el clima en Suesca el sábado? | `consultar_pronostico(destino="Suesca", dia="sabado")` | Rocas de Suesca el sabado: soleado, entre 7 °C y 21 °C, probabilidad de lluvia 15 %. | 43,8 s |
| 2 | ¿Y el domingo? | `consultar_pronostico(destino="Suesca", dia="domingo")` | Rocas de Suesca el domingo: tormentas en la tarde, entre 8 °C y 17 °C, probabilidad de lluvia 70 %. | 48,8 s |

**Esta es la prueba de que funciona:** en el turno 2 la pregunta solo dice "¿Y el domingo?", sin mencionar ningún destino, y aun así el agente llamó la herramienta con `destino="Suesca"`. Ese dato solo pudo salir del historial que guarda el `InMemorySaver` para ese `thread_id`. Además, el supervisor explicó su decisión así: *"La pregunta del usuario trata sobre el clima del domingo en Suesca"*.

**Respuesta del turno 2:**

> El sábado en Suesca será soleado con una temperatura entre 7 °C y 21 °C y una probabilidad de lluvia del 15 %. Ideal para caminar sin impermeable.
>
> El domingo en Suesca será con tormentas en la tarde. Lo mejor será llevar una chaqueta impermeable. La temperatura rondará entre 8 °C y 17 °C.

## Observaciones

- **El agente de clima omitió el 70 % de lluvia del domingo** al resumir, aunque la herramienta sí lo devolvió. Por eso la verificación automática marcó "Revisar". Es la misma limitación de pérdida de cifras que vimos en las preguntas 1 y 4; el mecanismo de memoria no tiene que ver con ella.
- **El sintetizador repitió el pronóstico del sábado** en la respuesta del turno 2. Esto pasa porque tiene el historial en su contexto. No es incorrecto, pero la respuesta queda más larga de lo necesario.
- **En los dos turnos el supervisor intentó repetir clima** y la protección contra ciclos pasó a `fin` (la misma limitación de las preguntas 1 a 4).

## Prueba 2 · Desde el frontend (http://localhost:4200): entiende la referencia, pero da datos equivocados

Repetimos la conversación desde el navegador, con el backend levantado (`uvicorn backend.src.api:app --port 8080`). El frontend envía el mismo `sessionId` en toda la pestaña, y `api.py` lo usa como `thread_id`.

| Turno | Pregunta | Respuesta del sistema | Datos reales (tabla de la guía) | Tiempo backend |
|---|---|---|---|---:|
| 1 | ¿Cómo estará el clima en Suesca el sábado? | Soleado, entre 7 °C y 21 °C, probabilidad de lluvia 15 %. | Soleado, 7–21 °C, 15 % | 47,6 s |
| 2 | ¿Y el domingo? | "El domingo también será soleado con las mismas temperaturas. La probabilidad de lluvia es del 15 %." | **Tormentas en la tarde, 8–17 °C, 70 %** | 52,7 s |

- **Entendió la referencia.** En la traza de uvicorn, el supervisor explicó: *"La pregunta del usuario trata sobre el clima para el domingo en Suesca"*. La memoria resolvió "¿Y el domingo?" como Suesca el domingo.
- **Pero los datos del domingo son incorrectos.** El agente de clima respondió *"Rocas de Suesca el domingo será soleado con temperaturas entre 7°C y 21°C. La probabilidad de lluvia es del 1[5]%"*, que son los datos del sábado. La traza de uvicorn no registra las llamadas a herramientas, así que no podemos saber si el agente no llamó `consultar_pronostico` y copió los datos del turno anterior del historial, o si la llamó con el día equivocado.
- **El mismo error apareció en una conversación anterior** que quedó en la misma traza: también respondió el domingo como soleado con 15 %.
- **Capturas:** `reto_frontend_turno1.png`, `reto_frontend_dos_turnos.png` y `reto_frontend_traza_uvicorn.png`.

## Conclusión sobre el reto

El mecanismo de memoria funciona: con el mismo `thread_id`, el sistema entiende que "¿Y el domingo?" se refiere a Suesca, por script y desde el frontend. La exactitud de los datos no es confiable con `qwen2.5:3b`:
- **Por script:** el agente llamó la herramienta con Suesca y domingo, y obtuvo los datos correctos (aunque omitió el 70 %).
- **Desde el frontend:** respondió con los datos del sábado en las dos conversaciones.

**Causa probable:** cuando el historial ya contiene un pronóstico, el modelo pequeño tiende a reutilizarlo en lugar de consultar la herramienta para el nuevo día.

**Mitigación propuesta:** pasar al sintetizador el resultado literal de las herramientas, y no solo el resumen del agente; o validar que, en cada turno que pregunta por clima, se haya llamado `consultar_pronostico` con el día pedido.
