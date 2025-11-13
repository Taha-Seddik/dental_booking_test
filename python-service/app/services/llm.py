# app/services/llm.py

import json
import os
import sys
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..core import config
from .scheduling import list_available_slots, create_appointment

# ---------- Logging ----------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    stream=sys.stdout,
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("python-service.llm")

# ---------- Time helpers: timezone-aware + future-biased ----------

def _now_tz() -> datetime:
    tz_name = os.getenv("TZ_NAME", "Asia/Dubai")  # set in docker-compose
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz)

def _has_year(text: str) -> bool:
    import re
    return bool(re.search(r"\b20\d{2}\b", text or ""))

def _coerce_future(dt: datetime, now: datetime, original_text: str) -> datetime:
    if dt >= now:
        return dt
    if not _has_year(original_text):
        for _ in range(3):
            try:
                dt = dt.replace(year=dt.year + 1)
            except ValueError:
                dt = dt + timedelta(days=365)
            if dt >= now:
                return dt
    while dt < now:
        dt += timedelta(days=1)
    return dt

def _try_dateparser(text: str, now: datetime) -> Optional[datetime]:
    try:
        import dateparser as dp
    except Exception:
        return None
    settings = {
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": now,
        "TIMEZONE": str(now.tzinfo) if now.tzinfo else "UTC",
        "RETURN_AS_TIMEZONE_AWARE": True,
    }
    return dp.parse(text, settings=settings)

def parse_user_date(text: str) -> datetime:
    """Parse natural language date → midnight in clinic TZ, coerced to future."""
    now = _now_tz()
    dt = _try_dateparser(text, now)
    if dt is None:
        lower = (text or "").lower()
        if "tomorrow" in lower:
            dt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif "today" in lower:
            dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            from dateutil import parser as du
            dt = du.parse(text, default=now)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=now.tzinfo)
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    dt = _coerce_future(dt, now, text)
    parsed = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    logger.info("[parse_user_date] raw=%r -> parsed=%s", text, parsed.isoformat())
    return parsed

def parse_user_datetime(text: str) -> datetime:
    """Parse natural language datetime → tz-aware, coerced to future."""
    now = _now_tz()
    dt = _try_dateparser(text, now)
    if dt is None:
        lower = (text or "").lower()
        if "tomorrow" in lower:
            base = (now + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
            dt = base.replace(hour=9)  # default hour if none provided
        elif "today" in lower:
            dt = now.replace(minute=0, second=0, microsecond=0)
        else:
            from dateutil import parser as du
            dt = du.parse(text, default=now)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=now.tzinfo)
    dt = _coerce_future(dt, now, text)
    logger.info("[parse_user_datetime] raw=%r -> parsed=%s", text, dt.isoformat())
    return dt

# ---------- LLM path (LLM chooses tools; we render final reply) ----------

def chat_with_llm(message: str, user_id: str, history_rows: List[Dict[str, Any]]) -> str:
    if not config.USE_LLM:
        raise RuntimeError("LLM disabled (no OPENAI_API_KEY).")

    # Lazy imports
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
    from langchain_core.tools import tool

    @tool
    def normalize_datetime(text: str) -> str:
        """
        Normalize natural language like 'tomorrow 09:30' to an ISO datetime (clinic TZ, future).
        Useful for debugging what the model thinks the datetime is.
        """
        try:
            dt = parse_user_datetime(text)
            payload = {"input": text, "normalized": dt.isoformat()}
            logger.info("[normalize_datetime] payload=%s", payload)
            return json.dumps(payload)
        except Exception as e:
            err = {"input": text, "error": str(e)}
            logger.warning("[normalize_datetime] failed: %s", err)
            return json.dumps(err)

    @tool
    def check_availability(date: str) -> str:
        """
        Return JSON slots for the given date (YYYY-MM-DD or 'tomorrow').
        Always interpreted in clinic timezone, preferring future dates.
        """
        try:
            logger.info("[check_availability] raw date arg=%r", date)
            date_dt = parse_user_date(date)
            slots = list_available_slots(date_dt)
            out = [{"start": s.isoformat(), "end": e.isoformat()} for s, e in slots]
            payload = {"slots": out, "date": date_dt.date().isoformat()}
            logger.info("[check_availability] parsed=%s slots=%d", date_dt.isoformat(), len(out))
            return json.dumps(payload)
        except Exception as e:
            logger.exception("[check_availability] error for arg=%r", date)
            return json.dumps({"error": f"Could not parse date '{date}': {e}"})

    @tool
    def schedule_appointment(start_iso: str, duration_minutes: int = config.DEFAULT_APPT_MIN) -> str:
        """
        Create a pending appointment for the CURRENT AUTHENTICATED USER.
        Accepts natural language like 'tomorrow 09:30' or full ISO.
        Interprets in clinic timezone and coerces to future.
        """
        uid = user_id
        if not uid:
            return json.dumps({"error": "AUTH_MISSING_USER_ID"})
        if not start_iso:
            return json.dumps({"error": "Missing start_iso (e.g., 'tomorrow 09:30')."})
        try:
            logger.info("[schedule_appointment] raw start arg=%r user_id=%s", start_iso, uid)
            start_dt = parse_user_datetime(start_iso)
            appt_id, s, e, provider, location = create_appointment(uid, start_dt.isoformat(), duration_minutes)
            payload = {
                "appointment_id": appt_id,
                "start": s.isoformat(),
                "end": e.isoformat(),
                "provider": provider,
                "location": location,
                "status": "pending",
            }
            logger.info("[schedule_appointment] created id=%s start=%s end=%s", appt_id, s.isoformat(), e.isoformat())
            return json.dumps(payload)
        except Exception as e:
            logger.exception("[schedule_appointment] error")
            return json.dumps({"error": str(e)})

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    tools = [normalize_datetime, check_availability, schedule_appointment]
    llm_with_tools = llm.bind_tools(tools)

    tz_name = os.getenv("TZ_NAME", "Asia/Dubai")
    system = SystemMessage(
        content=(
            "You are a helpful assistant for a dental clinic. "
            "The authenticated user is known; NEVER ask for IDs or email. "
            f"ALWAYS use the clinic timezone '{tz_name}' and prefer FUTURE dates. "
            "When you need a concrete datetime, first call the 'normalize_datetime' tool "
            "to convert natural language to an ISO datetime, then call the appropriate tool. "
            "Base responses on tool outputs; do not invent dates or times."
        )
    )

    # Build short context
    messages = [system]
    for row in history_rows[-6:]:
        if row.get("sender_type") == "user":
            messages.append(HumanMessage(content=row.get("content", "")))
        else:
            messages.append(AIMessage(content=row.get("content", "")))
    messages.append(HumanMessage(content=message))

    logger.info("chat_with_llm: user_id=%s message=%r", user_id, message)

    first = llm_with_tools.invoke(messages)

    # Inspect the model's tool intent
    tool_calls = getattr(first, "tool_calls", None) or getattr(first, "additional_kwargs", {}).get("tool_calls", None)
    try:
        logger.info("LLM tool_calls: %s", json.dumps(tool_calls, default=str))
    except Exception:
        logger.info("LLM tool_calls: %r", tool_calls)

    if tool_calls:
        availability_json = None
        booking_json = None
        normalization_json = None
        tool_msgs: List[ToolMessage] = []

        for call in tool_calls:
            name = call.get("name")
            args = call.get("args", {}) or {}
            logger.info("TOOL CALL -> %s ARGS=%s", name, json.dumps(args))

            if name == "normalize_datetime":
                result = normalize_datetime.invoke(args)
                normalization_json = json.loads(result)
                tool_msgs.append(ToolMessage(content=result, tool_call_id=call.get("id")))
                logger.info("TOOL RESULT <- normalize_datetime: %s", result)

            elif name == "check_availability":
                result = check_availability.invoke(args)
                availability_json = json.loads(result)
                tool_msgs.append(ToolMessage(content=result, tool_call_id=call.get("id")))
                logger.info("TOOL RESULT <- check_availability: %s", result)

            elif name == "schedule_appointment":
                start_iso = args.get("start_iso")
                duration = int(args.get("duration_minutes", config.DEFAULT_APPT_MIN))
                result = schedule_appointment.invoke({"start_iso": start_iso, "duration_minutes": duration})
                booking_json = json.loads(result)
                tool_msgs.append(ToolMessage(content=result, tool_call_id=call.get("id")))
                logger.info("TOOL RESULT <- schedule_appointment: %s", result)

        # ----- Deterministic rendering (no second LLM pass) -----
        parts = []

        if normalization_json:
            # purely for visibility; usually we don't show this to the end user
            if "normalized" in normalization_json:
                logger.info("Normalized datetime: %s", normalization_json["normalized"])

        if availability_json:
            if "error" in availability_json:
                parts.append("Sorry, I couldn't parse that date. Try 'YYYY-MM-DD' or 'tomorrow'.")
            else:
                date_str = availability_json.get("date")
                slots = availability_json.get("slots", [])
                if slots:
                    times = ", ".join(
                        datetime.fromisoformat(s["start"]).strftime("%H:%M") for s in slots[:8]
                    )
                    parts.append(f"Available 30-min slots on {date_str}: {times}.")
                else:
                    parts.append(f"No available 30-min slots on {date_str}. Try another day?")

        if booking_json:
            if "error" in booking_json:
                parts.append(f"Couldn't create the appointment: {booking_json['error']}")
            else:
                start_h = datetime.fromisoformat(booking_json["start"]).strftime("%Y-%m-%d %H:%M")
                parts.append(
                    f"Booked a pending appointment for {start_h} with "
                    f"{booking_json['provider']} at {booking_json['location']} "
                    f"(ID: {booking_json['appointment_id']})."
                )

        if parts:
            final_reply = " ".join(parts)
            logger.info("Final reply: %s", final_reply)
            return final_reply

        # Fallback if tools returned nothing meaningful
        logger.warning("No meaningful tool results; returning model text.")
        return first.content

    # No tool call; just return the model text
    logger.info("No tool calls; returning model text.")
    return first.content
