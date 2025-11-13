from fastapi import FastAPI
from .models import ChatRequest, ChatResponse
from .db import db_conn
from .core import config
from .services.sessions import ensure_session, log_message, get_history, touch_session
from .services.rules import chat_rule_based

app = FastAPI(title="Dental LangChain Chat Service (modular)")

@app.get("/health")
def health():
    try:
        with db_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok", "db": db_ok, "llm": config.USE_LLM}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    print("PYTHON /chat payload:", req.model_dump())
    session_id = ensure_session(req.userId, req.sessionId)
    log_message(session_id, "user", req.message)

    history_rows = get_history(session_id, limit=10)

    if config.USE_LLM:
        try:
            from .services.llm import chat_with_llm
            reply_text = chat_with_llm(req.message, req.userId, history_rows)
        except Exception as e:
            # Fallback to rule-based if LLM path fails for any reason
            reply_text = chat_rule_based(req.message, req.userId)
    else:
        reply_text = chat_rule_based(req.message, req.userId)

    log_message(session_id, "assistant", reply_text)
    touch_session(session_id)

    return ChatResponse(reply=reply_text, sessionId=session_id)
