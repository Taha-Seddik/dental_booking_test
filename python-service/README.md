# Dental Python Service (FastAPI + uv, modular)

**Goal:** readable, testable structure. LangChain is optional (enabled if `OPENAI_API_KEY` is set).

```
app/
  __init__.py
  main.py            # ASGI entry that exposes `app`
  api.py             # FastAPI routes
  core/
    __init__.py
    config.py        # env loading + flags
  db.py              # psycopg connection factory
  models.py          # Pydantic request/response models
  services/
    __init__.py
    sessions.py      # session CRUD + chat logs
    scheduling.py    # business hours, slots, create appointment
    rules.py         # rule-based fallback responses
    llm.py           # LangChain tool-calling path (optional)
```

## Local dev (uv)

```powershell
irm https://astral.sh/uv/install.ps1 | iex
uv sync
copy .env.example .env  # adjust if needed
uv run uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
docker build -t dental-python-service .
docker run -p 8000:8000 --env-file .env dental-python-service
```

In docker-compose, set the service as `python-service` and ensure the backend points to `http://python-service:8000`.
