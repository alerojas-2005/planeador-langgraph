"""
ejecutar_pruebas.py — Ejecuta las seis preguntas de prueba del taller sobre el grafo
LangGraph y guarda la evidencia para la bitácora.

Por cada pregunta registra:
  - las decisiones del supervisor y la respuesta de cada especialista,
  - las herramientas (tools) que se llamaron, con sus argumentos y resultados,
  - el tiempo total en segundos,
  - una verificación automática contra los valores esperados de la guía
    (es una SUGERENCIA: la persona que prueba confirma el resultado a mano).

Requisitos: Ollama encendido con qwen2.5:3b y el entorno virtual activo.

Uso (desde la raíz del repositorio):
    python -m tests.ejecutar_pruebas              -> las seis preguntas
    python -m tests.ejecutar_pruebas 4            -> solo la pregunta 4
    python -m tests.ejecutar_pruebas 1 3 6        -> varias
    python -m tests.ejecutar_pruebas --reto       -> las seis + evidencia del reto (memoria)
    python -m tests.ejecutar_pruebas --solo-reto  -> solo el reto
    python -m tests.ejecutar_pruebas --salida C:\\ruta\\carpeta  -> guarda la evidencia en otra carpeta

Salida (por defecto en docs/):
    docs/resultados_langgraph.md    tabla + traza de cada pregunta (para la bitácora)
    docs/resultados_langgraph.json  los mismos datos en JSON

Cada pregunta usa su propio thread_id, así la memoria conversacional (reto) no
mezcla una pregunta con otra. Los datos (cupos, reservas) NO se reinician entre
preguntas, igual que en el backend real.
"""
import contextlib
import io
import json
import platform
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler

from backend.src import datos
from backend.src.config import MAX_PASOS, MODELO, OLLAMA_URL

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_DOCS = RAIZ / "docs"

# Las seis preguntas de la guía, con los agentes esperados y los valores verificables.
#   debe_contener:    textos que deben aparecer en la respuesta final
#   no_debe_contener: textos que NO deben aparecer (p. ej. un código de reserva)
PREGUNTAS = [
    {
        "n": 1,
        "pregunta": "¿Cómo estará el clima en Guatavita el domingo?",
        "agentes_esperados": ["clima"],
        "resultado_esperado": "Lluvioso, 7–15 °C, 80 % de lluvia",
        "debe_contener": ["lluvi", "7", "15", "80"],
        "no_debe_contener": [],
    },
    {
        "n": 2,
        "pregunta": "Somos 4 amigos con 350000 pesos. ¿Nos alcanza para ir a Zipaquirá?",
        "agentes_esperados": ["presupuesto"],
        "resultado_esperado": "Costo $400.000; faltan $50.000",
        "debe_contener": ["400.000", "50.000"],
        "no_debe_contener": [],
    },
    {
        "n": 3,
        "pregunta": "Somos 2 y queremos ir a Villa de Leyva el sábado. ¿Cómo estará el clima y cuánto nos cuesta?",
        "agentes_esperados": ["clima", "presupuesto"],
        "resultado_esperado": "Soleado, 5 % de lluvia; $230.000 en total",
        "debe_contener": ["soleado", "5", "230.000"],
        "no_debe_contener": [],
    },
    {
        "n": 4,
        "pregunta": "Somos 3 y tenemos 250000. Si no llueve mucho y nos alcanza, reserva Suesca para el sábado a nombre de Laura.",
        "agentes_esperados": ["clima", "presupuesto", "reservas"],
        "resultado_esperado": "15 % de lluvia; $210.000, sobran $40.000; reserva con código RES-…",
        "debe_contener": ["15", "210.000", "40.000", "RES-"],
        "no_debe_contener": [],
        "debe_reservar": True,
    },
    {
        "n": 5,
        "pregunta": "Somos 3 con 150000. Si nos alcanza, reserva Suesca el domingo a nombre de Laura.",
        "agentes_esperados": ["presupuesto"],          # la guía acepta también reservas, sin reservar
        "agentes_opcionales": ["reservas"],
        "resultado_esperado": "Faltan $60.000; NO debe reservar",
        "debe_contener": ["60.000"],
        "no_debe_contener": ["RES-"],
        "debe_reservar": False,
    },
    {
        "n": 6,
        "pregunta": "¿Quién ganó el mundial de 2022?",
        "agentes_esperados": [],
        "resultado_esperado": "Explica que solo ayuda con salidas de fin de semana",
        "debe_contener": [],
        "no_debe_contener": ["Argentina", "Messi"],    # no debe responder fuera de su dominio
    },
]


class TrazaTools(BaseCallbackHandler):
    """Registra cada llamada a una tool (nombre, argumentos y resultado).

    El callback se pasa al grafo en config; LangChain lo propaga a los agentes
    internos (create_agent) y a sus tools.
    """

    def __init__(self):
        self.llamadas: list[dict] = []
        self._abiertas: dict = {}

    def on_tool_start(self, serialized, input_str, *, run_id, inputs=None, **kwargs):
        nombre = (serialized or {}).get("name") or kwargs.get("name") or "tool"
        llamada = {"tool": nombre, "argumentos": inputs if inputs is not None else input_str, "resultado": None}
        self._abiertas[run_id] = llamada
        self.llamadas.append(llamada)

    def on_tool_end(self, output, *, run_id, **kwargs):
        llamada = self._abiertas.pop(run_id, None)
        if llamada is not None:
            llamada["resultado"] = getattr(output, "content", output)
            if not isinstance(llamada["resultado"], str):
                llamada["resultado"] = str(llamada["resultado"])

    def on_tool_error(self, error, *, run_id, **kwargs):
        llamada = self._abiertas.pop(run_id, None)
        if llamada is not None:
            llamada["resultado"] = f"ERROR: {error}"


class Tee(io.TextIOBase):
    """Escribe en la consola y a la vez guarda el texto (para la traza)."""

    def __init__(self, consola):
        self.consola, self.buffer = consola, io.StringIO()

    def write(self, texto):
        self.consola.write(texto)
        self.consola.flush()
        return self.buffer.write(texto)


def verificar(caso: dict, respuesta: str, consultados: list[str], reservas_nuevas: int) -> tuple[bool, list[str]]:
    """Compara con lo esperado. Devuelve (correcta_sugerida, observaciones)."""
    obs = []

    def norm(t: str) -> str:
        """Quita separadores de miles (400.000, 400,000 -> 400000) para comparar cifras."""
        return re.sub(r"(?<=\d)[.,](?=\d{3}\b)", "", (t or "").lower())

    texto = norm(respuesta)
    faltan = [v for v in caso["debe_contener"] if norm(v) not in texto]
    if faltan:
        obs.append(f"No aparece en la respuesta: {', '.join(faltan)}")
    if re.search(r"\d,\d{3}\b", respuesta or ""):
        obs.append("Formato de cifras con coma (400,000) en lugar de punto (400.000)")
    sobran = [v for v in caso["no_debe_contener"] if norm(v) in texto]
    if sobran:
        obs.append(f"Aparece y no debería: {', '.join(sobran)}")

    permitidos = set(caso["agentes_esperados"]) | set(caso.get("agentes_opcionales", []))
    innecesarios = [a for a in consultados if a not in permitidos]
    no_llamados = [a for a in caso["agentes_esperados"] if a not in consultados]
    if innecesarios:
        obs.append(f"Llamó agentes innecesarios: {', '.join(innecesarios)}")
    if no_llamados:
        obs.append(f"No llamó a: {', '.join(no_llamados)}")

    if "debe_reservar" in caso:
        if caso["debe_reservar"] and reservas_nuevas == 0:
            obs.append("Debía reservar y no creó la reserva")
        if not caso["debe_reservar"] and reservas_nuevas > 0:
            obs.append("Creó una reserva cuando NO debía")

    if not respuesta or not respuesta.strip():
        obs.append("Respuesta vacía")

    correcta = not (faltan or sobran or no_llamados or ("Respuesta vacía" in obs)
                    or any("reserva" in o.lower() for o in obs))
    if correcta and innecesarios:
        obs.append("Resultado correcto, pero con un agente de más")
    return correcta, obs


def ejecutar_caso(app, estado_inicial, caso: dict) -> dict:
    traza = TrazaTools()
    reservas_antes = len(datos.RESERVAS)
    config = {"configurable": {"thread_id": f"prueba-{caso['n']}-{uuid.uuid4().hex[:8]}"},
              "callbacks": [traza]}

    print(f"\n{'=' * 78}\nPregunta {caso['n']}: {caso['pregunta']}\n{'=' * 78}")
    tee = Tee(sys.stdout)
    error = None
    estado = {}
    inicio = time.perf_counter()
    with contextlib.redirect_stdout(tee):
        try:
            estado = app.invoke(estado_inicial(caso["pregunta"]), config)
        except Exception as e:                       # se registra el fallo, no se oculta
            error = f"{type(e).__name__}: {e}"
            print(f"   [ERROR] {error}")
    segundos = time.perf_counter() - inicio

    respuesta = estado.get("respuesta_final", "")
    consultados = list(estado.get("consultados", []))
    reservas_nuevas = len(datos.RESERVAS) - reservas_antes
    correcta, obs = verificar(caso, respuesta, consultados, reservas_nuevas)
    if error:
        correcta, obs = False, [f"Error de ejecución: {error}"] + obs

    print(f"\nRespuesta final ({segundos:.1f} s):\n{respuesta}")
    print(f"\nVerificación sugerida: {'CORRECTA' if correcta else 'REVISAR'}"
          + (f" — {'; '.join(obs)}" if obs else ""))

    return {
        "n": caso["n"],
        "pregunta": caso["pregunta"],
        "agentes_esperados": caso["agentes_esperados"],
        "agentes_llamados": consultados,
        "resultado_esperado": caso["resultado_esperado"],
        "respuesta": respuesta,
        "tiempo_s": round(segundos, 1),
        "correcta_sugerida": correcta,
        "observaciones": obs,
        "tools": traza.llamadas,
        "resultados_agentes": list(estado.get("resultados", [])),
        "traza_consola": tee.buffer.getvalue(),
        "reservas_creadas": datos.RESERVAS[reservas_antes:],
    }


def escribir_markdown(resultados: list[dict], ruta: Path) -> None:
    def celda(t: str) -> str:
        return str(t).replace("|", "\\|").replace("\n", " ")

    lineas = [
        "# Resultados de las pruebas — LangGraph",
        "",
        f"- Fecha: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Modelo: `{MODELO}` en `{OLLAMA_URL}` · MAX_PASOS = {MAX_PASOS}",
        f"- Equipo: {platform.system()} {platform.release()} · {platform.processor() or platform.machine()} · Python {platform.python_version()}",
        "",
        "La columna **¿Correcta?** es una verificación automática contra la guía; "
        "se confirma a mano revisando la respuesta y la traza.",
        "",
        "| # | Agentes que llamó el supervisor | ¿Respuesta correcta? | Tiempo (s) | Observaciones |",
        "|---|---|---|---|---|",
    ]
    for r in resultados:
        agentes = ", ".join(r["agentes_llamados"]) or "ninguno"
        lineas.append(f"| {r['n']} | {agentes} | {'Sí' if r['correcta_sugerida'] else 'Revisar'} | "
                      f"{r['tiempo_s']:.1f} | {celda('; '.join(r['observaciones']) or '—')} |")
    tiempos = [r["tiempo_s"] for r in resultados]
    aciertos = sum(r["correcta_sugerida"] for r in resultados)
    lineas += ["", f"**Aciertos:** {aciertos}/{len(resultados)} · "
                   f"**Tiempo promedio:** {sum(tiempos) / len(tiempos):.1f} s", ""]

    for r in resultados:
        lineas += [
            f"## Pregunta {r['n']}", "",
            f"**Pregunta:** {r['pregunta']}  ",
            f"**Agentes esperados:** {', '.join(r['agentes_esperados']) or 'ninguno'} · "
            f"**Agentes llamados:** {', '.join(r['agentes_llamados']) or 'ninguno'}  ",
            f"**Resultado esperado:** {r['resultado_esperado']}  ",
            f"**Tiempo:** {r['tiempo_s']:.1f} s", "",
            "**Herramientas llamadas:**", "",
        ]
        if r["tools"]:
            for t in r["tools"]:
                lineas.append(f"- `{t['tool']}({json.dumps(t['argumentos'], ensure_ascii=False)})` → {t['resultado']}")
        else:
            lineas.append("- (ninguna)")
        lineas += ["", "**Traza (supervisor y especialistas):**", "", "```text",
                   r["traza_consola"].strip() or "(sin salida)", "```", "",
                   "**Respuesta final:**", "", r["respuesta"] or "(vacía)", ""]

    ruta.write_text("\n".join(lineas), encoding="utf-8")


# ---------------------------------------------------------------------------
# Reto implementado en este repositorio: MEMORIA CONVERSACIONAL (InMemorySaver).
# Evidencia: dos turnos en el MISMO thread_id; el segundo no repite el destino.
# ---------------------------------------------------------------------------
RETO_TURNOS = [
    "¿Cómo estará el clima en Suesca el sábado?",
    "¿Y el domingo?",
]
# Datos de la guía para Suesca: sábado soleado 15 % · domingo tormentas en la tarde 70 %.
RETO_ESPERADO_TURNO2 = ["tormenta", "70"]


def ejecutar_reto(app, estado_inicial) -> dict:
    thread_id = f"reto-memoria-{uuid.uuid4().hex[:8]}"
    turnos = []
    for i, pregunta in enumerate(RETO_TURNOS, start=1):
        traza = TrazaTools()
        config = {"configurable": {"thread_id": thread_id}, "callbacks": [traza]}
        print(f"\n{'=' * 78}\nReto (memoria) turno {i}: {pregunta}\n{'=' * 78}")
        tee = Tee(sys.stdout)
        estado, error = {}, None
        inicio = time.perf_counter()
        with contextlib.redirect_stdout(tee):
            try:
                estado = app.invoke(estado_inicial(pregunta), config)
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                print(f"   [ERROR] {error}")
        segundos = time.perf_counter() - inicio
        respuesta = estado.get("respuesta_final", "")
        print(f"\nRespuesta ({segundos:.1f} s):\n{respuesta}")
        turnos.append({"turno": i, "pregunta": pregunta, "respuesta": respuesta,
                       "agentes_llamados": list(estado.get("consultados", [])),
                       "tools": traza.llamadas, "tiempo_s": round(segundos, 1),
                       "traza_consola": tee.buffer.getvalue(), "error": error})
    texto2 = (turnos[-1]["respuesta"] or "").lower()
    faltan = [v for v in RETO_ESPERADO_TURNO2 if v not in texto2]
    tools2 = turnos[-1]["tools"]
    uso_suesca = any("suesca" in json.dumps(t["argumentos"], ensure_ascii=False).lower() for t in tools2)
    obs = []
    if faltan:
        obs.append(f"En el turno 2 no aparece: {', '.join(faltan)}")
    if tools2 and not uso_suesca:
        obs.append("En el turno 2 la tool no se llamó con Suesca")
    funciona = not faltan and not any(t["error"] for t in turnos)
    print(f"\nVerificación sugerida del reto: {'FUNCIONA' if funciona else 'REVISAR'}"
          + (f" — {'; '.join(obs)}" if obs else ""))
    return {"thread_id": thread_id, "turnos": turnos, "funciona_sugerido": funciona,
            "observaciones": obs, "esperado_turno2": "Suesca domingo: tormentas en la tarde, 8–17 °C, 70 % de lluvia"}


def escribir_reto_markdown(reto: dict, ruta: Path) -> None:
    lineas = [
        "# Evidencia del reto — Memoria conversacional (LangGraph)", "",
        f"- Fecha: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Modelo: `{MODELO}` · thread_id: `{reto['thread_id']}` (el mismo en los dos turnos)", "",
        "Hicimos dos preguntas seguidas en la misma conversación. En la segunda no repetimos el destino: "
        "si la memoria funciona, el sistema entiende que seguimos hablando de Suesca.", "",
        f"**Resultado esperado del turno 2:** {reto['esperado_turno2']}  ",
        f"**Verificación sugerida:** {'Funciona' if reto['funciona_sugerido'] else 'Revisar'}"
        + (f" ({'; '.join(reto['observaciones'])})" if reto["observaciones"] else ""), "",
    ]
    for t in reto["turnos"]:
        lineas += [f"## Turno {t['turno']}: {t['pregunta']}", "",
                   f"**Agentes llamados:** {', '.join(t['agentes_llamados']) or 'ninguno'} · **Tiempo:** {t['tiempo_s']:.1f} s", "",
                   "**Herramientas llamadas:**", ""]
        lineas += [f"- `{x['tool']}({json.dumps(x['argumentos'], ensure_ascii=False)})` → {x['resultado']}"
                   for x in t["tools"]] or ["- (ninguna)"]
        lineas += ["", "**Traza:**", "", "```text", t["traza_consola"].strip() or "(sin salida)", "```", "",
                   "**Respuesta:**", "", t["respuesta"] or "(vacía)", ""]
    ruta.write_text("\n".join(lineas), encoding="utf-8")


def main(argv: list[str]) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Pruebas del taller LangGraph")
    parser.add_argument("preguntas", nargs="*", type=int, help="números de pregunta (vacío = las seis)")
    parser.add_argument("--reto", action="store_true", help="ejecutar también la evidencia del reto (memoria)")
    parser.add_argument("--solo-reto", action="store_true", help="ejecutar solo el reto")
    parser.add_argument("--salida", default=str(CARPETA_DOCS), help="carpeta donde guardar la evidencia")
    args = parser.parse_args(argv)

    seleccion = set(args.preguntas)
    casos = [] if args.solo_reto else [c for c in PREGUNTAS if not seleccion or c["n"] in seleccion]
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    print(f"Cargando grafo (modelo {MODELO})...")
    from backend.src.grafo import app, estado_inicial

    if casos:
        resultados = [ejecutar_caso(app, estado_inicial, caso) for caso in casos]
        sufijo = "" if not seleccion else "_" + "-".join(str(n) for n in sorted(seleccion))
        ruta_md = salida / f"resultados_langgraph{sufijo}.md"
        ruta_json = salida / f"resultados_langgraph{sufijo}.json"
        escribir_markdown(resultados, ruta_md)
        ruta_json.write_text(json.dumps(resultados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        print(f"\n{'=' * 78}\nResumen")
        for r in resultados:
            print(f"  P{r['n']}: {', '.join(r['agentes_llamados']) or 'ninguno':<32} "
                  f"{r['tiempo_s']:>6.1f} s  {'OK' if r['correcta_sugerida'] else 'REVISAR'}")
        print(f"\nEvidencia guardada en:\n  {ruta_md}\n  {ruta_json}")

    if args.reto or args.solo_reto:
        reto = ejecutar_reto(app, estado_inicial)
        ruta_reto = salida / "evidencia_reto_memoria.md"
        escribir_reto_markdown(reto, ruta_reto)
        (salida / "evidencia_reto_memoria.json").write_text(
            json.dumps(reto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"\nEvidencia del reto guardada en:\n  {ruta_reto}")


if __name__ == "__main__":
    main(sys.argv[1:])
