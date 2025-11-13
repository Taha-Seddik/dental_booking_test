# python-service/Dockerfile  (uv-based, no OS tzdata needed)
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Install Python deps via uv (tzdata + dateparser must be in pyproject.toml)
COPY pyproject.toml ./
RUN uv sync

# Copy source
COPY . .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=UTC \
    TZ_NAME=UTC

EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]