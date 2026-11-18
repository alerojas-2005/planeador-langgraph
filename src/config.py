
"""
config.py — Configuración central del taller.

Todo lo que se quiera cambiar (modelo, URL de Ollama,
límite de pasos del supervisor) vive aquí.
"""

import os

# Modelo de Ollama. Debe soportar la capacidad tools.
MODELO = os.getenv("MODELO_OLLAMA", "qwen2.5:3b")

# Dirección del servidor local de Ollama.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Máximo de agentes especialistas que puede consultar el supervisor.
MAX_PASOS = 3
