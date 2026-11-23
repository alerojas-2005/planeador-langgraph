"""
agentes.py — Los tres agentes especialistas.

Cada agente = modelo + herramientas + instrucciones (system prompt).
create_agent() construye por dentro un pequeño grafo de LangGraph con el ciclo
ReAct: el modelo piensa -> pide una tool -> recibe el resultado -> vuelve a
pensar... hasta que responde sin pedir más tools.
"""
from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from backend.src.config import MODELO, OLLAMA_URL
from backend.src.herramientas import (calcular_saldo, consultar_disponibilidad, consultar_pronostico,
                          crear_reserva, estimar_costo, listar_destinos)


def crear_modelo() -> ChatOllama:
    """Modelo local servido por Ollama. temperature=0 => respuestas más estables."""
    return ChatOllama(model=MODELO, base_url=OLLAMA_URL, temperature=0)


PROMPT_CLIMA = """Eres el AGENTE DE CLIMA de un planeador de salidas de fin de semana cerca de Bogotá.
Tu único trabajo es informar el pronóstico del tiempo.
- Usa SIEMPRE la herramienta consultar_pronostico. Nunca inventes datos del clima.
- Si el usuario no dice el día, consulta sábado y domingo.
- Ignora las partes de la pregunta que no son de clima (dinero, reservas).
- Responde en español, en máximo 3 frases, con una recomendación práctica (ropa, impermeable...)."""

PROMPT_PRESUPUESTO = """Eres el AGENTE DE PRESUPUESTO de un planeador de salidas de fin de semana.
Tu único trabajo es calcular cuánto cuesta el plan y si el dinero alcanza.
- Usa estimar_costo para obtener el costo total. Nunca hagas las cuentas de memoria.
- Si el usuario dio un presupuesto, usa calcular_saldo con ese presupuesto y el costo total.
- Escribe los valores en pesos como números enteros (300000, no 300.000) al llamar las herramientas.
- Ignora las partes de la pregunta que no son de dinero.
- Responde en español, en máximo 3 frases."""

PROMPT_RESERVAS = """Eres el AGENTE DE RESERVAS de un planeador de salidas de fin de semana.
Tu único trabajo es consultar cupos y crear reservas.
- Usa consultar_disponibilidad antes de reservar.
- Usa crear_reserva SOLO si el usuario pidió reservar explícitamente y dio el nombre del responsable.
- Si el usuario condicionó la reserva (por ejemplo "si no llueve" o "si nos alcanza") y los
  resultados de otros agentes muestran que la condición NO se cumple, NO reserves y explica por qué.
- Responde en español, en máximo 3 frases. Si reservaste, incluye el código de la reserva."""


agente_clima = create_agent(
    model=crear_modelo(),
    tools=[listar_destinos, consultar_pronostico],
    system_prompt=PROMPT_CLIMA,
)

agente_presupuesto = create_agent(
    model=crear_modelo(),
    tools=[estimar_costo, calcular_saldo],
    system_prompt=PROMPT_PRESUPUESTO,
)

agente_reservas = create_agent(
    model=crear_modelo(),
    tools=[consultar_disponibilidad, crear_reserva],
    system_prompt=PROMPT_RESERVAS,
)