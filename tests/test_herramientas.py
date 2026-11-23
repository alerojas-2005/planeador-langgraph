"""
test_herramientas.py — Pruebas de las herramientas SIN modelo y SIN Ollama.

Las tools son funciones normales de Python: se prueban llamándolas directamente
con .invoke({...}). Si estas pruebas fallan, el agente nunca podrá responder bien.

Ejecutar desde la raíz del repositorio (con el entorno virtual activo):
    python -m pytest tests/test_herramientas.py -v

Parte 1: las mismas cinco pruebas de HerramientasTest.java (taller Spring AI),
         para que las dos implementaciones se verifiquen con los mismos casos.
Parte 2: los valores que deben aparecer en las seis preguntas de prueba.
"""
import pytest

from backend.src import datos
from backend.src.herramientas import (calcular_saldo, consultar_disponibilidad, consultar_pronostico,
                                      crear_reserva, estimar_costo, listar_destinos)


@pytest.fixture(autouse=True)
def datos_limpios():
    """crear_reserva modifica CUPOS y RESERVAS: se restauran después de cada prueba."""
    cupos, reservas = dict(datos.CUPOS), list(datos.RESERVAS)
    yield
    datos.CUPOS.clear(); datos.CUPOS.update(cupos)
    datos.RESERVAS.clear(); datos.RESERVAS.extend(reservas)


# ---------------------------------------------------------------------------
# Parte 1. Las cinco pruebas de la guía (equivalentes a HerramientasTest.java)
# ---------------------------------------------------------------------------
def test_pronostico_acepta_tildes_y_mayusculas():
    r = consultar_pronostico.invoke({"destino": "Guatavita", "dia": "Domingo"})
    assert "lluvioso" in r, r


def test_costo_de_zipaquira_para_cuatro():
    r = estimar_costo.invoke({"destino": "Zipaquirá", "personas": 4})
    assert "$400.000" in r, r


def test_saldo_negativo_dice_cuanto_falta():
    r = calcular_saldo.invoke({"presupuesto": 350000, "costo_total": 400000})
    assert "faltan $50.000" in r, r


def test_no_reserva_sin_cupos():
    r = crear_reserva.invoke({"destino": "Chicaque", "dia": "sabado", "personas": 2, "responsable": "Ana"})
    assert r.startswith("No hay cupo"), r


def test_destino_desconocido_lista_los_validos():
    r = consultar_pronostico.invoke({"destino": "Medellín", "dia": "sabado"})
    assert "Destinos válidos" in r, r


# ---------------------------------------------------------------------------
# Parte 2. Valores verificables de las seis preguntas de prueba
# ---------------------------------------------------------------------------
def test_p1_clima_guatavita_domingo():
    r = consultar_pronostico.invoke({"destino": "Guatavita", "dia": "domingo"})
    assert "lluvioso" in r and "7 °C" in r and "15 °C" in r and "80 %" in r, r


def test_p2_presupuesto_zipaquira_4_con_350000():
    costo = estimar_costo.invoke({"destino": "Zipaquirá", "personas": 4})
    saldo = calcular_saldo.invoke({"presupuesto": 350000, "costo_total": 400000})
    assert "Costo total para 4 personas: $400.000" in costo, costo
    assert saldo.startswith("No alcanza") and "faltan $50.000" in saldo, saldo


def test_p3_villa_de_leyva_sabado_2_personas():
    clima = consultar_pronostico.invoke({"destino": "Villa de Leyva", "dia": "sábado"})
    costo = estimar_costo.invoke({"destino": "Villa de Leyva", "personas": 2})
    assert "soleado" in clima and "5 %" in clima, clima
    assert "$230.000" in costo, costo


def test_p4_suesca_sabado_3_con_250000_si_reserva():
    clima = consultar_pronostico.invoke({"destino": "Suesca", "dia": "sabado"})
    costo = estimar_costo.invoke({"destino": "Suesca", "personas": 3})
    saldo = calcular_saldo.invoke({"presupuesto": 250000, "costo_total": 210000})
    cupos = consultar_disponibilidad.invoke({"destino": "Suesca", "dia": "sabado"})
    reserva = crear_reserva.invoke({"destino": "Suesca", "dia": "sabado", "personas": 3, "responsable": "Laura"})
    assert "15 %" in clima, clima
    assert "$210.000" in costo, costo
    assert "sobran $40.000" in saldo, saldo
    assert "quedan 8 cupos" in cupos, cupos
    assert reserva.startswith("Reserva confirmada RES-") and "Laura" in reserva, reserva
    assert datos.CUPOS[("suesca", "sabado")] == 5          # 8 - 3


def test_p5_suesca_domingo_3_con_150000_no_alcanza():
    costo = estimar_costo.invoke({"destino": "Suesca", "personas": 3})
    saldo = calcular_saldo.invoke({"presupuesto": 150000, "costo_total": 210000})
    assert "$210.000" in costo, costo
    assert saldo.startswith("No alcanza") and "faltan $60.000" in saldo, saldo


# ---------------------------------------------------------------------------
# Casos de borde (normalización y validaciones)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("texto, clave", [
    ("Zipaquirá", "zipaquira"), ("la catedral", "zipaquira"), ("ZIPA", "zipaquira"),
    ("Villa de Leiva", "villa de leyva"), ("rocas de suesca", "suesca"), ("Laguna", "guatavita"),
    ("Medellín", None), ("", None),
])
def test_buscar_destino_normaliza(texto, clave):
    assert datos.buscar_destino(texto) == clave


def test_listar_destinos_tiene_los_cinco():
    r = listar_destinos.invoke({})
    for nombre in ("Guatavita", "Zipaquirá", "Villa de Leyva", "Suesca", "Chicaque"):
        assert nombre in r, r


def test_dia_invalido():
    r = consultar_pronostico.invoke({"destino": "Suesca", "dia": "lunes"})
    assert "sabado" in r and "domingo" in r, r


def test_no_reserva_sin_responsable():
    r = crear_reserva.invoke({"destino": "Suesca", "dia": "sabado", "personas": 3, "responsable": "  "})
    assert r.startswith("Falta el nombre del responsable"), r
    assert datos.CUPOS[("suesca", "sabado")] == 8          # no descontó cupos


def test_no_reserva_mas_personas_que_cupos():
    r = crear_reserva.invoke({"destino": "Villa de Leyva", "dia": "sabado", "personas": 3, "responsable": "Laura"})
    assert r == "No hay cupo suficiente: se piden 3 y quedan 2.", r


def test_personas_cero():
    assert "mayor que cero" in estimar_costo.invoke({"destino": "Suesca", "personas": 0})
