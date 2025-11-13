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

## 5)  How to Run the Project (All Services via Docker Compose)

> **Prerequisites**
> - Docker Desktop (or Docker Engine + Compose)
> - Ports available: Postgres `5432`, Backend `4000`, Python `8000`, Frontend `3000`

### 5.1) Clone
```bash
git clone <your-repo-url> dental-chatbot-mvp
cd dental-chatbot-mvp
```

### 5.2) Create env files 

**`backend/.env`**
```env
# App
PORT=4000
LOG_LEVEL=info

# Postgres (use docker-compose service name, NOT localhost)
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=dental_chatbot

# Python service (service name, NOT localhost)
PYTHON_SERVICE_URL=http://python-service:8000

# JWT secrets (demo values — change in real use)
ACCESS_TOKEN_SECRET=supersecret_access
CHAT_TOKEN_SECRET=supersecret_chat
```

**`python-service/.env`**
```env
# Optional LLM (leave OPENAI_API_KEY empty to use rules-only fallback)
# OPENAI_API_KEY=YOUR_OPENAI_KEY
OPENAI_MODEL=gpt-4o-mini

# Postgres (service name)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=dental_chatbot

# Service
PORT=8000

# Timezone & logs (keeps "tomorrow" future & consistent)
TZ_NAME=Asia/Dubai
LOG_LEVEL=INFO

# Scheduler defaults
DEFAULT_PROVIDER=Dr. Bob Dentist
DEFAULT_LOCATION=Downtown Dental Clinic
DEFAULT_APPT_MINUTES=30
BUSINESS_START=09:00
BUSINESS_END=17:00
```

**`client/.env.local`**
```env
# From the browser’s perspective this is your host port mapping
NEXT_PUBLIC_BACKEND_URL=http://localhost:4000
```

> **Why service names?** Inside Docker networks, containers reach each other by **service name** (e.g., `postgres`, `python-service`). `localhost` would point to the container itself.

### 5.3) Build & start all services
```bash
docker compose up -d --build
```


### 5.4) Run SQL scripts (under postgres scripts folder)

---


## 6) Test Scenarios (manual checks to screenshot)

1) **Login + token mint**
   - Login as `alice@example.com` / `password123`.
   - Call `POST /api/chatbot/token` to receive chat token.
   - Screenshot: successful token response.
  
<img width="1914" height="400" alt="image" src="https://github.com/user-attachments/assets/b553603c-0185-49a1-8cda-5e7f1c899461" />

2) **Availability – tomorrow**
   - In the chat UI: “slots for tomorrow?”
   - Expected: list of 30-min slots for **future** date (your `TZ_NAME`), not 2023.  
   - Screenshot: reply with slot list.

<img width="1919" height="400" alt="image" src="https://github.com/user-attachments/assets/4d040742-ced2-482f-9715-e5bc6a0d1db5" />
  
3) **Book specific time**
   - “book me tomorrow at 09:30”
   - Expected: reply confirms **pending** appointment with start/end, provider, location, and ID.
   - DB: `appointments` has a new row for Alice.
   - Screenshot: chat confirmation + DBeaver row.

<img width="1919" height="400" alt="image" src="https://github.com/user-attachments/assets/17d84ab1-c592-4f3c-8525-279cb3448cba" />

