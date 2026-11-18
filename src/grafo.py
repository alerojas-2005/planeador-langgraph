"""
grafo.py — El sistema multiagente como un grafo de LangGraph.

                 ┌──────────────┐
     START ────► │  supervisor  │ ◄──────────────┐
                 └──────┬───────┘                │
          (arista condicional: ¿quién sigue?)    │
        ┌───────────┬───┴────────┬──────────┐    │
        ▼           ▼            ▼          ▼    │
     clima    presupuesto    reservas   sintetizador ──► END
        │           │            │
        └───────────┴────────────┘
          (vuelven al supervisor)
"""
import operator
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from src.agentes import agente_clima, agente_presupuesto, agente_reservas, crear_modelo
from src.config import MAX_PASOS


# 1. ESTADO: la "memoria compartida" que viaja por todos los nodos.
#    Annotated[list, operator.add] = REDUCER: lo que devuelve un nodo se
#    AGREGA a la lista en lugar de reemplazarla.
class EstadoPlaneador(TypedDict):
    pregunta: str
    resultados: Annotated[list[str], operator.add]
    consultados: Annotated[list[str], operator.add]
    siguiente: str
    respuesta_final: str


# 2. SALIDA ESTRUCTURADA del supervisor: en vez de texto libre, el modelo
#    debe devolver un objeto con estos campos. Así el enrutamiento es confiable.
class Decision(BaseModel):
    siguiente: Literal["clima", "presupuesto", "reservas", "fin"] = Field(
        description="Agente que debe trabajar ahora, o 'fin' si ya se puede responder.")
    motivo: str = Field(description="Explicación breve de la decisión.")


PROMPT_SUPERVISOR = """Eres el SUPERVISOR de un planeador de salidas de fin de semana cerca de Bogotá.
Coordinas a tres agentes especialistas:
- clima: pronóstico del tiempo de un destino para el sábado o el domingo.
- presupuesto: costo del plan para un grupo y si el dinero alcanza.
- reservas: cupos disponibles y creación de reservas.

Lee la pregunta del usuario y los resultados que ya existen, y decide quién trabaja ahora.
Reglas:
1. Elige solo agentes que la pregunta realmente necesita y que no hayan sido consultados.
2. Si el usuario quiere reservar con una condición (clima, dinero), consulta primero esos agentes
   y deja "reservas" de último.
3. Si ya hay información suficiente, o la pregunta no trata de estos temas, responde "fin"."""

PROMPT_SINTETIZADOR = """Eres el asistente final de un planeador de salidas de fin de semana.
Redacta la respuesta para el usuario usando SOLO los resultados de los agentes.
- No inventes datos que no estén en los resultados.
- Organiza la respuesta en un párrafo corto o en viñetas, en español y con tono amable.
- Si se hizo una reserva, muestra el código.
- Si no hay resultados, explica que puedes ayudar con clima, presupuesto y reservas
  para Guatavita, Zipaquirá, Villa de Leyva, Suesca y Chicaque."""

modelo_supervisor = crear_modelo().with_structured_output(Decision)
modelo_sintetizador = crear_modelo()


def _contexto(estado: EstadoPlaneador) -> str:
    """Texto con la pregunta y lo que ya respondieron los agentes."""
    previos = "\n".join(estado["resultados"]) or "(todavía no hay resultados)"
    return f"Pregunta del usuario: {estado['pregunta']}\n\nResultados de otros agentes:\n{previos}"


# 3. NODOS: funciones que reciben el estado y devuelven SOLO lo que cambian.
def nodo_supervisor(estado: EstadoPlaneador) -> dict:
    consultados = estado["consultados"]
    if len(consultados) >= MAX_PASOS:          # límite de autonomía
        return {"siguiente": "fin"}

    mensaje = (_contexto(estado) +
               f"\n\nAgentes ya consultados: {', '.join(consultados) or 'ninguno'}")
    try:
        decision = modelo_supervisor.invoke([("system", PROMPT_SUPERVISOR), ("human", mensaje)])
        siguiente = decision.siguiente
        print(f"   [supervisor] -> {siguiente} ({decision.motivo})")
    except Exception as error:                 # el modelo no devolvió un JSON válido
        print(f"   [supervisor] decisión inválida ({error}); se pasa a la respuesta final")
        siguiente = "fin"

    if siguiente in consultados:               # evita ciclos infinitos
        siguiente = "fin"
    return {"siguiente": siguiente}


def crear_nodo_especialista(nombre: str, agente):
    """Fábrica de nodos: envuelve un agente (create_agent) como nodo del grafo."""
    def nodo(estado: EstadoPlaneador) -> dict:
        resultado = agente.invoke({"messages": [{"role": "user", "content": _contexto(estado)}]})
        texto = resultado["messages"][-1].content
        print(f"   [{nombre}] {texto}")
        return {"resultados": [f"[{nombre}] {texto}"], "consultados": [nombre]}
    return nodo


def nodo_sintetizador(estado: EstadoPlaneador) -> dict:
    respuesta = modelo_sintetizador.invoke([("system", PROMPT_SINTETIZADOR), ("human", _contexto(estado))])
    return {"respuesta_final": respuesta.content}


# 4. ARISTA CONDICIONAL: lee el estado y dice a qué nodo ir.
def enrutar(estado: EstadoPlaneador) -> str:
    return estado["siguiente"]


# 5. CONSTRUCCIÓN Y COMPILACIÓN DEL GRAFO
def construir_grafo():
    grafo = StateGraph(EstadoPlaneador)

    grafo.add_node("supervisor", nodo_supervisor)
    grafo.add_node("clima", crear_nodo_especialista("clima", agente_clima))
    grafo.add_node("presupuesto", crear_nodo_especialista("presupuesto", agente_presupuesto))
    grafo.add_node("reservas", crear_nodo_especialista("reservas", agente_reservas))
    grafo.add_node("sintetizador", nodo_sintetizador)

    grafo.add_edge(START, "supervisor")
    grafo.add_conditional_edges("supervisor", enrutar, {
        "clima": "clima",
        "presupuesto": "presupuesto",
        "reservas": "reservas",
        "fin": "sintetizador",
    })
    for especialista in ("clima", "presupuesto", "reservas"):
        grafo.add_edge(especialista, "supervisor")
    grafo.add_edge("sintetizador", END)

    return grafo.compile()


def estado_inicial(pregunta: str) -> dict:
    return {"pregunta": pregunta, "resultados": [], "consultados": []}


app = construir_grafo()


def planear(pregunta: str) -> str:
    """Punto de entrada usado por main.py y api.py."""
    estado_final = app.invoke(estado_inicial(pregunta))
    return estado_final["respuesta_final"]