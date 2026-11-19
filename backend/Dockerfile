FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# El código importa "backend.src...", así que dentro de la imagen debe vivir
# en /app/backend/src (igual que en el repositorio).
COPY src/ ./backend/src/

EXPOSE 8080

CMD ["uvicorn", "backend.src.api:app", "--host", "0.0.0.0", "--port", "8080"]