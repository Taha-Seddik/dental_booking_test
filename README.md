# Dental Appointment Chatbot – MVP

AI-powered appointment assistant for a dental clinic.  
Full stack: **Next.js** (chat UI) + **Node/Express** (auth, API, service gateway) + **FastAPI + LangChain** (chat + tools) + **PostgreSQL** (users, sessions, appointments).  
Runs locally with **Docker Compose**.

---

## 1) Intro (what this does)

- **Chat UI** for patients to ask for availability (“slots for tomorrow?”) and book appointments (“book me tomorrow 09:30”).
- **Node/Express backend**
  - Login + JWT
  - Mints a **short-lived chat token** for the web client
  - Proxies chat messages to the Python/LangChain service
  - Rate limiting, request logging
- **Python FastAPI service**
  - LangChain model with **tool calling**
  - Tools:
    - `check_availability(date)`
    - `schedule_appointment(start_iso)`
    - `normalize_datetime(text)` (deterministic NL → ISO converter)
  - **Timezone-aware, future-biased** parsing so “tomorrow” doesn’t become 2023
  - Logs conversation turns and analytics to Postgres
- **PostgreSQL**
  - `users`, `chat_sessions`, `chat_messages`, `appointments`
  - Simple seed data (Alice + Dr. Bob)

---

## 2) Tech Stack

- **Frontend:** Next.js (React), Tailwind
- **Backend:** Node.js + Express, JWT, rate-limit middleware
- **AI Service:** FastAPI, LangChain (OpenAI compatible), `dateparser`, `tzdata`
- **DB:** PostgreSQL (psycopg2)
- **Infra:** Docker Compose
- **Quality:** structured logs, healthchecks, deterministic tool responses

---

## 3) Architecture

```
[Browser/Next.js]
     |
     |  (Authorization: Bearer <access token> → mint short chat token)
     v
[Node/Express API]
  /api/auth/login                -> issues long-lived access token
  /api/chatbot/token (POST)      -> issues 5-min chat token (JWT)
  /api/chat (POST)               -> validates chat token, sends {userId,sessionId,message}
                                    to Python service
     |
     |  (HTTP JSON)
     v
[FastAPI + LangChain]
  /chat                          -> tool-calling: availability, booking
     |
     v
[PostgreSQL]                     -> users, sessions, messages, appointments
```

---

## 4) Project Structure

```
.
├─ docker-compose.yml
├─ client/                      # Next.js frontend
├─ backend/                     # Node/Express API
│  ├─ src/
│  │  ├─ routes/ (auth, chat, chatbot-token)
│  │  ├─ middleware/ (auth, rateLimiter)
│  │  └─ config.js
│  └─ .env                      # see sample below
├─ python-service/              # FastAPI + LangChain service
│  ├─ app/
│  │  ├─ api.py                 # routes /health, /chat
│  │  ├─ main.py                # ASGI entrypoint (re-exports app)
│  │  ├─ services/
│  │  │  ├─ llm.py              # LLM + tools + deterministic rendering + logs
│  │  │  ├─ scheduling.py       # tz-aware slot calc + inserts
│  │  │  └─ rules.py            # fallback (if no LLM key)
│  │  ├─ core/config.py         # envs & flags
│  │  └─ db.py                  # psycopg connection helpers
│  └─ .env                      # see sample below
├─ sql/
│  ├─ schema.sql
│  └─ sample_data.sql
└─ README.md
```

---

## 5) Environment Variables (samples)

### 5.1 Backend (`backend/.env`)
```env
# App
NODE_ENV=development
PORT=4000
LOG_LEVEL=info

# Postgres (matches docker-compose)
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=dental_chatbot

# Service wiring (use service name inside Compose)
PYTHON_SERVICE_URL=http://python-service:8000

# JWT secrets (generate random strings for local dev)
ACCESS_TOKEN_SECRET=dev_access_secret_please_change
CHAT_TOKEN_SECRET=dev_chat_secret_please_change

# Rate limiting (optional)
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX=30
```

### 5.2 Python service (`python-service/.env`)
```env
# OpenAI (optional – if empty, service can use fallback rules)
OPENAI_API_KEY=YOUR_KEY_HERE
OPENAI_MODEL=gpt-4o-mini

# Postgres (matches docker-compose)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=dental_chatbot

# Timezone & logs
TZ_NAME=Asia/Dubai
LOG_LEVEL=INFO
```

### 5.3 Frontend (`client/.env.local`)
```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:4000
```

---

## 6) Run locally (Docker Compose)

```bash
# 0) Create env files as shown above

# 1) Build & start
docker compose up -d --build

# 2) Load schema + sample data (one-time)
docker cp sql/schema.sql dental_postgres:/schema.sql
docker exec -it dental_postgres psql -U postgres -d dental_chatbot -f /schema.sql

docker cp sql/sample_data.sql dental_postgres:/sample_data.sql
docker exec -it dental_postgres psql -U postgres -d dental_chatbot -f /sample_data.sql

# (Optional) set demo password for Alice to match frontend login
docker exec -it dental_postgres psql -U postgres -d dental_chatbot \
  -c "UPDATE users SET password_hash='password123' WHERE email='alice@example.com';"

# 3) Open the app
# Frontend: http://localhost:3000
# Backend:  http://localhost:4000/health
# Python:   http://localhost:8000/health
```

**DBeaver connection** (optional):  
Host `localhost`, Port `5432`, DB `dental_chatbot`, User `postgres`, Password `postgres`.

---

## 7) Endpoints (quick reference)

### Backend
- `POST /api/auth/login` → `{ email, password }` → returns **access token**
- `POST /api/chatbot/token` → header `Authorization: Bearer <access token>` → returns **chat token** (5 min)
- `POST /api/chat`  
  Headers: `Authorization: Bearer <chat token>`  
  Body: `{ message: string, sessionId?: string }`  
  → proxies to Python `/chat` with `{ userId, sessionId, message }`

### Python
- `GET /health` → `{ status, db, llm }`
- `POST /chat` → `{ userId: UUID, sessionId?: UUID | null, message: string }`  
  - Decides tool calls (availability / booking)  
  - Logs both user & assistant messages to DB  
  - Returns `{ reply, sessionId }` to the backend

---

## 8) How it interprets dates (the “tomorrow” fix)

- Python uses `dateparser` **+ clinic timezone** (env `TZ_NAME`) and coerces results to the **future**.
- Tools:
  - `normalize_datetime(text)` → deterministic NL → ISO (e.g., “tomorrow 09:30” → `2025-11-14T09:30:00+04:00`)
  - `check_availability(date)` → slots for that day (tz-aware)
  - `schedule_appointment(start_iso)` → inserts **pending** appointment (tz-aware)
- Final response is **constructed from tool outputs**, not free-text hallucinations.

---

## 9) Test Scenarios (manual checks to screenshot)

1) **Login + token mint**
   - Login as `alice@example.com` / `password123`.
   - Call `POST /api/chatbot/token` to receive chat token.
   - Screenshot: successful token response.

2) **Availability – tomorrow**
   - In the chat UI: “slots for tomorrow?”
   - Expected: list of 30-min slots for **future** date (your `TZ_NAME`), not 2023.  
   - Screenshot: reply with slot list.

3) **Book specific time**
   - “book me tomorrow at 09:30”
   - Expected: reply confirms **pending** appointment with start/end, provider, location, and ID.
   - DB: `appointments` has a new row for Alice.
   - Screenshot: chat confirmation + DBeaver row.

4) **Conflict handling**
   - Seed or create an appointment that overlaps (e.g., 09:00–09:30).
   - Ask for availability: that slot should be missing.
   - Screenshot: slot list without the conflicting time.

5) **Short-lived chat token**
   - Wait >5 minutes or set `expiresIn` shorter; call `/api/chat`.
   - Expected: backend 401/403 for expired chat token.
   - Screenshot: error toast / backend log.

6) **Rate limiting**
   - Fire many requests quickly (e.g., spam the Send button).
   - Expected: 429 from backend (depending on your limiter values).
   - Screenshot: network/error log.

7) **Fallback (no OpenAI key)**
   - Remove `OPENAI_API_KEY` from Python env and restart python-service.
   - Chat still works with **rules** (simple parser + booking).
   - Screenshot: availability/booking replies without LLM.

8) **Timezone sanity**
   - Set `TZ_NAME` to a different zone, rebuild python-service.
   - Ask “normalize ‘tomorrow 09:30’ ” (or watch logs).
   - Confirm the normalized ISO shows new offset.
   - Screenshot: log snippet.

---

## 10) Troubleshooting

- **Backend says**: `ECONNREFUSED to http://localhost:8000/chat`  
  Inside Docker, `localhost` is the container itself.  
  Set `PYTHON_SERVICE_URL=http://python-service:8000` (service name) and restart backend.

- **“Please provide user ID”**  
  Tools no longer accept `user_id`; Python **always** uses the authenticated `userId` from Node. Ensure Node sends it (logs show `Calling Python with: { userId: ... }`).

- **“tomorrow” becomes 2023 / wrong year**  
  Fixed by **future-bias + timezone** and deterministic rendering. Ensure python env has:
  `TZ_NAME=Asia/Dubai` (or your zone) and `dateparser` is installed.

- **`can't compare offset-naive and offset-aware datetimes`**  
  Use the provided **tz-aware `scheduling.py`**. Rebuild python-service.

- **Duplicate chat messages in DB**  
  Log turns in **one place**. We keep logging in **Python** and removed Node’s duplicates.

- **DB schema missing**  
  Run `schema.sql` and `sample_data.sql` into the **same** Postgres used by containers (service name `postgres`). Re-run seed update for Alice’s password if needed.

- **DBeaver connection**
  Host `localhost`, Port `5432`, DB `dental_chatbot`, User `postgres`, Password `postgres`.

---

## 11) Commands (handy)

```bash
# Tail logs
docker logs -f dental_backend
docker logs -f dental_python_service
docker logs -f dental_postgres

# Health checks
curl -s http://localhost:4000/health | jq
curl -s http://localhost:8000/health | jq

# Call Python /chat directly (paste Alice UUID)
docker exec -it dental_backend sh -lc \
'curl -sS -X POST http://python-service:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"userId\":\"<ALICE_UUID>\",\"sessionId\":null,\"message\":\"slots for tomorrow?\"}" | jq'
```

---

## 12) Security/Next steps

- Replace demo password logic with **bcrypt**.
- Add **refresh tokens** & CSRF/runtime protection.
- Add a **confirmation flow** (pending → confirmed), provider calendars, reminders.
- Observability: Prometheus metrics, structured JSON logs, trace IDs across services.
