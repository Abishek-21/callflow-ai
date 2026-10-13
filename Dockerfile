# One image for both services; docker-compose.yml runs the API and the UI from it.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# SQLite lives on a mounted volume so data survives container restarts.
RUN mkdir -p /data
ENV DATABASE_URL=sqlite:////data/callflow.db

EXPOSE 8000 8501
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
