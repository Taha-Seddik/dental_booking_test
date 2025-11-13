from datetime import datetime, timedelta, time
from typing import List, Tuple
from dateutil import parser as dateparser
from ..db import db_conn, dict_cursor
from ..core import config

def parse_business_times(date_obj) -> tuple[datetime, datetime]:
    start_h, start_m = map(int, config.BUSINESS_START.split(":"))
    end_h, end_m = map(int, config.BUSINESS_END.split(":"))
    return datetime.combine(date_obj, time(start_h, start_m)), datetime.combine(date_obj, time(end_h, end_m))

def list_available_slots(date_dt: datetime, provider: str = config.DEFAULT_PROVIDER, duration_minutes: int = config.DEFAULT_APPT_MIN, limit: int = 10) -> List[tuple[datetime, datetime]]:
    target_date = date_dt.date()
    start_dt, end_dt = parse_business_times(target_date)

    # generate slot grid
    slots: List[tuple[datetime, datetime]] = []
    cursor = start_dt
    while cursor + timedelta(minutes=duration_minutes) <= end_dt:
        slots.append((cursor, cursor + timedelta(minutes=duration_minutes)))
        cursor += timedelta(minutes=duration_minutes)

    # existing appts
    with db_conn() as conn, dict_cursor(conn) as cur:
        cur.execute(
            """SELECT start_time, end_time
                   FROM appointments
                   WHERE provider_name = %s
                     AND status IN ('pending','confirmed')
                     AND start_time::date = %s::date""",
            (provider, target_date),
        )
        appts = cur.fetchall()

    def overlaps(a_start, a_end, b_start, b_end):
        return a_start < b_end and b_start < a_end

    available = []
    for s, e in slots:
        if any(overlaps(s, e, a["start_time"], a["end_time"]) for a in appts):
            continue
        available.append((s, e))
        if len(available) >= limit:
            break

    return available

def create_appointment(user_id: str, start_iso: str, duration_minutes: int = config.DEFAULT_APPT_MIN, provider: str = config.DEFAULT_PROVIDER, location: str = config.DEFAULT_LOCATION):
    try:
        start_dt = dateparser.parse(start_iso)
    except Exception:
        raise ValueError("Invalid datetime format. Use ISO 8601 like 2025-11-13T15:00:00")
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    with db_conn() as conn, dict_cursor(conn) as cur:
        cur.execute(
            """INSERT INTO appointments
                   (user_id, chat_session_id, start_time, end_time, status, notes, provider_name, location)
                   VALUES (%s, NULL, %s, %s, 'pending', %s, %s, %s)
                   RETURNING id""",
            (user_id, start_dt, end_dt, "Created via chatbot", provider, location),
        )
        row = cur.fetchone()
        return row["id"], start_dt, end_dt, provider, location
