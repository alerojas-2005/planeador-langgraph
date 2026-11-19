
"""
api.py — API REST del planeador multiagente con LangGraph.

Expone los mismos endpoints que el proyecto pruebachat
para reutilizar su frontend.
"""

import json
import os
import time
import urllib.request
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.src.config import OLLAMA_URL


app = FastAPI(title="Planeador de fin de semana - LangGraph")


# Permite que el frontend se comunique con esta API. Se puede cambiar con la
# variable CORS_ORIGINS (lista separada por comas).
ORIGENES_PERMITIDOS = [
    origen.strip()
    for origen in os.getenv(
        "CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200"
    ).split(",")
    if origen.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_PERMITIDOS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    sessionId: str | None = None


@app.post("/api/v1/chat")
def chat(req: ChatRequest):
    """
    Recibe una pregunta y solicita la respuesta al grafo multiagente.

    La importación se realiza aquí porque el grafo todavía
    está en desarrollo.
    """
    try:
        from backend.src.grafo import planear

        inicio = time.perf_counter()
        respuesta = planear(req.question, req.sessionId or "default")
        elapsed_ms = int((time.perf_counter() - inicio) * 1000)

        status = "ok" if respuesta and respuesta.strip() else "error"

        cuerpo = {
            "requestId": str(uuid.uuid4()),
            "answer": respuesta or "",
            "elapsedMs": elapsed_ms,
            "status": status
        }

        return JSONResponse(
            cuerpo,
            status_code=200 if status == "ok" else 502
        )

    except Exception as error:
        return JSONResponse(
            {
                "requestId": str(uuid.uuid4()),
                "answer": "",
                "status": "error",
                "error": str(error)
            },
            status_code=502
        )


@app.get("/health/llm")
def health_llm():
    """
    Comprueba que el servidor Ollama está disponible
    y devuelve los modelos instalados.
    """
    endpoint = OLLAMA_URL.rstrip("/") + "/api/tags"

    try:
        with urllib.request.urlopen(endpoint, timeout=5) as response:
            return {
                "ok": True,
                "endpoint": endpoint,
                "result": json.load(response)
            }

    except Exception as error:
        return JSONResponse(
            {
                "ok": False,
                "error": str(error)
            },
            status_code=502
        )
