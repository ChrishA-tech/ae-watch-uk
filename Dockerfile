# Multi-purpose Production Container for AE-Watch UK (FastAPI + Streamlit + Pipeline)
# Author: CHRISH PEP FELIX A
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app

WORKDIR /app

# Install system dependencies for LightGBM, PostGIS clients, and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for deterministic fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
COPY data/regulatory_docs/ ./data/regulatory_docs/
COPY dbt_ae_watch/ ./dbt_ae_watch/
COPY docs/ ./docs/

RUN mkdir -p data/raw data/processed data/quarantine mlruns

EXPOSE 8000 8501

CMD ["uv", "run", "uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
