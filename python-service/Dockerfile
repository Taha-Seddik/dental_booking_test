# python-service (uv-based) - modular
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Leverage layer caching for deps
COPY pyproject.toml ./
RUN uv sync

# Copy source
COPY . .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Use uv-created venv
CMD ["/app/.venv/bin/uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
