from datetime import datetime, timedelta, time
from dateutil import parser as dateparser
from .scheduling import list_available_slots, create_appointment

def chat_rule_based(message: str, user_id: str) -> str:
    """Simple fallback when LLM is disabled."""
    text = message.lower()
    reply_text = None

    # Try to detect a token that parses to a date (YYYY-MM-DD or similar)
    date_candidate = None
    for token in text.replace(",", " ").split():
        try:
            dt = dateparser.parse(token, fuzzy=False)
            date_candidate = dt.date()
            break
        except Exception:
            continue

    if any(k in text for k in ["slot", "available", "availability", "book", "schedule"]):
        target_date = date_candidate or (datetime.utcnow() + timedelta(days=1)).date()
        slots = list_available_slots(datetime.combine(target_date, time(0,0)))
        if not slots:
            reply_text = f"No available 30-min slots on {target_date.isoformat()}. Try another day?"
        else:
            human = ", ".join(s.strftime("%H:%M") for s, _ in slots[:6])
            reply_text = (
                f"Here are available 30-min slots on {target_date.isoformat()}: {human}. "
                f"Tell me which time you prefer (e.g., '{target_date.isoformat()} 15:00')."
            )
    else:
        reply_text = "I can help you check availability and create appointments. Try: 'Show me slots tomorrow' or 'Book me on 2025-11-15 10:30'."

    # If user gave a datetime like '2025-11-15 10:30', try to create
    try:
        dt = dateparser.parse(message, fuzzy=True)
        appt_id, s, e, provider, location = create_appointment(user_id, dt.isoformat())
        reply_text += f"\nI tentatively created an appointment (pending) on {s.strftime('%Y-%m-%d %H:%M')} with {provider} at {location}. ID: {appt_id}."
    except Exception:
        pass

    return reply_text
