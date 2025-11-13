import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..db import db_conn, dict_cursor

def ensure_session(user_id: str, session_id: Optional[str]) -> str:
    """Return existing session_id or create a new chat_sessions row."""
    with db_conn() as conn, dict_cursor(conn) as cur:
        if session_id:
            return session_id
        cur.execute(
            """INSERT INTO chat_sessions (user_id, status, started_at, last_message_at, metadata)
                 VALUES (%s, 'active', NOW(), NOW(), %s)
                 RETURNING id""",
            (user_id, json.dumps({"channel": "web"})),
        )
        return cur.fetchone()["id"]

def log_message(session_id: str, sender: str, content: str) -> None:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO chat_messages (chat_session_id, sender_type, content)
                   VALUES (%s, %s, %s)""",
            (session_id, sender, content),
        )

def get_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    with db_conn() as conn, dict_cursor(conn) as cur:
        cur.execute(
            """SELECT sender_type, content
                   FROM chat_messages
                   WHERE chat_session_id = %s
                   ORDER BY created_at ASC
                   LIMIT %s""",
            (session_id, limit),
        )
        return cur.fetchall()

def touch_session(session_id: str) -> None:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE chat_sessions SET last_message_at = NOW() WHERE id = %s", (session_id,))
