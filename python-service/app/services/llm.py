import json
import os
from typing import List, Dict, Any
from datetime import datetime, time
from dateutil import parser as dateparser
from ..core import config
from .scheduling import list_available_slots, create_appointment

# We import LangChain lazily inside the function to avoid import errors when OPENAI_API_KEY is missing.

def chat_with_llm(message: str, user_id: str, history_rows: List[Dict[str, Any]]) -> str:
    if not config.USE_LLM:
        raise RuntimeError("LLM disabled (no OPENAI_API_KEY).")

    # Lazy imports
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
    from langchain_core.tools import tool

    @tool
    def check_availability(date: str) -> str:
        """Return JSON list of up to 10 available 30-min slots for date (YYYY-MM-DD)."""
        try:
            date_obj = dateparser.parse(date).date()
        except Exception:
            return json.dumps({"error": "Invalid date. Use YYYY-MM-DD."})
        slots = list_available_slots(datetime.combine(date_obj, time(0,0)))
        out = [{"start": s.isoformat(), "end": e.isoformat()} for s, e in slots]
        return json.dumps({"slots": out})

    @tool
    def schedule_appointment(user_id: str, start_iso: str, duration_minutes: int = config.DEFAULT_APPT_MIN) -> str:
        """Create a pending appointment for the user starting at start_iso (ISO 8601)."""
        try:
            appt_id, s, e, provider, location = create_appointment(user_id, start_iso, duration_minutes)
            return json.dumps({
                "appointment_id": appt_id,
                "start": s.isoformat(),
                "end": e.isoformat(),
                "provider": provider,
                "location": location,
                "status": "pending"
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    tools = [check_availability, schedule_appointment]
    llm_with_tools = llm.bind_tools(tools)

    system = SystemMessage(
        content=(
            "You are a helpful assistant for a dental clinic. "
            "Your primary tasks are: (1) check availability for a given date, "
            "(2) schedule appointments using the provided tools. "
            "Prefer 30-min slots during business hours. "
            "Be concise and confirm details clearly."
        )
    )

    messages = [system]
    for row in history_rows[-6:]:
        if row["sender_type"] == "user":
            messages.append(HumanMessage(content=row["content"])) 
        else:
            messages.append(AIMessage(content=row["content"])) 
    messages.append(HumanMessage(content=message))

    first = llm_with_tools.invoke(messages)

    tool_outputs = []
    if hasattr(first, "tool_calls") and first.tool_calls:
        for call in first.tool_calls:
            name = call["name"]
            args = call["args"]
            if name == "check_availability":
                result = check_availability.invoke(args)
            elif name == "schedule_appointment":
                uid = user_id
                start_iso = args.get("start_iso")
                duration = int(args.get("duration_minutes", config.DEFAULT_APPT_MIN))
                result = schedule_appointment.invoke({"user_id": uid, "start_iso": start_iso, "duration_minutes": duration})
            else:
                result = json.dumps({"error": f"Unknown tool {name}"})
            tool_outputs.append(ToolMessage(content=result, tool_call_id=call["id"])) 

        final = llm.invoke(messages + [first] + tool_outputs)
        return final.content
    else:
        return first.content
