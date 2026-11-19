# Planeador de fin de semana multiagente

Sistema multiagente para la planeación de salidas de fin de semana, desarrollado con **LangGraph, LangChain y Ollama**. El proyecto permite analizar solicitudes de viaje mediante un supervisor y agentes especializados en clima, presupuesto y reservas.

## 1. Objetivo

Construir un asistente que ayude a planear salidas de fin de semana a diferentes destinos, teniendo en cuenta las condiciones climáticas, el presupuesto disponible y la posibilidad de realizar reservas.

## 2. Tecnologías utilizadas

- Python 3.12
- LangGraph
- LangChain
- LangChain Ollama
- Ollama
- Modelo local `qwen2.5:3b`
- FastAPI
- Uvicorn
- HTML, CSS y JavaScript

## 3. Estructura del proyecto

```text
planeador-langgraph/
│
├── frontend/
│   ├── Dockerfile
│   └── src/
│       └── index.html
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── prueba_ollama.py
│   ├── datos.py
│   ├── herramientas.py
│   ├── agentes.py
│   ├── grafo.py
│   ├── main.py
│   └── api.py
│
├── docs/
├── tests/
├── requirements.txt
├── README.md
└── .gitignore
```

## 4. Requisitos previos

Antes de ejecutar el proyecto se necesita:

- Python 3.12 o superior.
- Ollama instalado.
- Git.
- El modelo `qwen2.5:3b` descargado.
- Visual Studio Code (recomendado).

## 5. Instalación y configuración

Clonar el repositorio:

```bash
git clone https://github.com/alerojas-2005/planeador-langgraph.git
cd planeador-langgraph
```

Crear y activar el entorno virtual en Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalar las dependencias:

```powershell
pip install -r requirements.txt
```

Descargar el modelo de Ollama:

```powershell
ollama pull qwen2.5:3b
```

Verificar que Ollama tenga disponible el modelo:

```powershell
ollama list
```

## 6. Configuración del modelo

La configuración principal se encuentra en `src/config.py`.

Actualmente se utilizan las siguientes variables:

- `MODELO_OLLAMA`: nombre del modelo local. Por defecto, `qwen2.5:3b`.
- `OLLAMA_URL`: dirección del servicio Ollama. Por defecto, `http://localhost:11434`.
- `MAX_PASOS`: máximo de especialistas que puede consultar el supervisor. Su valor inicial es 3.

## 7. Ejecución del proyecto

### 7.1. Verificar conexión con Ollama

Con el entorno virtual activo, ejecutar:

```powershell
python -m src.prueba_ollama
```

### 7.2. Iniciar el backend

Desde la raíz del proyecto:

```powershell
python -m uvicorn src.api:app --host 0.0.0.0 --port 8080 --reload
```

La documentación interactiva de la API estará disponible en:

http://localhost:8080/docs

### 7.3. Iniciar el frontend

Abrir otra terminal de PowerShell, ubicarse en la raíz del proyecto y ejecutar:

```powershell
python -m http.server 4200 --directory frontend/src
```

Abrir en el navegador:

http://localhost:4200

## 8. Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/health/llm` | Verifica la conexión con Ollama. |
| POST | `/api/v1/chat` | Recibe una pregunta y devuelve la respuesta del planeador. |

Ejemplo de solicitud para el chat:

```json
{
  "question": "Quiero visitar Guatavita el domingo. ¿Cómo estará el clima?"
}
```

La respuesta incluye información como:

- Identificador de la solicitud (`requestId`).
- Respuesta del asistente (`answer`).
- Tiempo de ejecución (`elapsedMs`).
- Estado de la operación (`status`).

**Nota:** el endpoint de chat requiere que la función `planear` esté implementada e integrada en `src/grafo.py`.

## 9. Destinos disponibles

El proyecto utiliza datos simulados para los siguientes destinos:

| Destino | Costo por persona |
|---|---:|
| Guatavita | $90.000 |
| Zipaquirá | $100.000 |
| Villa de Leyva | $115.000 |
| Suesca | $70.000 |
| Chicaque | $90.000 |

Los datos de clima, presupuesto y reservas se gestionan mediante las herramientas definidas en el proyecto.

## 10. Estado del desarrollo

El proyecto se encuentra en desarrollo e integración. Los componentes se implementan de acuerdo con la distribución de responsabilidades del equipo.

La funcionalidad completa estará disponible cuando se integren los agentes, el grafo multiagente, las pruebas y la API.

## 11. Equipo de trabajo

Proyecto académico desarrollado para el taller de construcción de agentes multiagente con LangGraph y Ollama, de la Universidad El Bosque.