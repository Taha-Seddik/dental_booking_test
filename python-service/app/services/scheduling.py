# app/services/scheduling.py

import os
from datetime import datetime, time, timedelta
from typing import List, Tuple
from zoneinfo import ZoneInfo

from dateutil import parser as du
from psycopg2.extras import RealDictCursor

from ..core import config
from ..db import db_conn


def _clinic_tz() -> ZoneInfo:
    tz_name = os.getenv("TZ_NAME", "Asia/Dubai")
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def _to_tz(dt: datetime, tz: ZoneInfo) -> datetime:
    """Attach/convert timezone so all comparisons are tz-aware and consistent."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def parse_business_times(date_dt: datetime) -> Tuple[datetime, datetime]:
    """
    Build tz-aware business-hour bounds for the given date in clinic TZ.
    date_dt may be naive or aware – we'll normalize to clinic tz.
    """
    tz = date_dt.tzinfo or _clinic_tz()
    start_h, start_m = map(int, config.BUSINESS_START.split(":"))
    end_h, end_m = map(int, config.BUSINESS_END.split(":"))

    start = datetime.combine(date_dt.date(), time(start_h, start_m, tzinfo=tz))
    end = datetime.combine(date_dt.date(), time(end_h, end_m, tzinfo=tz))
    return start, end


def list_available_slots(
    date_dt: datetime,
    provider: str = config.DEFAULT_PROVIDER,
    duration_minutes: int = config.DEFAULT_APPT_MIN,
    limit: int = 10,
) -> List[Tuple[datetime, datetime]]:
    """
    Return up to `limit` 30-min slots (or duration_minutes) in clinic TZ for the given date.
    Avoids conflicts with existing pending/confirmed appointments.
    """
    tz = date_dt.tzinfo or _clinic_tz()
    start_dt, end_dt = parse_business_times(_to_tz(date_dt, tz))

    # Build slot grid (tz-aware)
    slots: List[Tuple[datetime, datetime]] = []
    step = timedelta(minutes=duration_minutes)
    cursor = start_dt
    while cursor + step <= end_dt:
        slots.append((cursor, cursor + step))
        cursor += step

    # Fetch existing appts (DB may store naive timestamps; reattach tz)
    with db_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT start_time, end_time
            FROM appointments
            WHERE provider_name = %s
              AND status IN ('pending','confirmed')
              AND start_time::date = %s::date
            """,
            (provider, start_dt.date()),
        )
        appts = cur.fetchall()

    appts_tz = [(_to_tz(a["start_time"], tz), _to_tz(a["end_time"], tz)) for a in appts]

    def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
        return a_start < b_end and b_start < a_end

    available: List[Tuple[datetime, datetime]] = []
    for s, e in slots:
        if any(overlaps(s, e, a_s, a_e) for a_s, a_e in appts_tz):
            continue
        available.append((s, e))
        if len(available) >= limit:
            break

    return available


def create_appointment(
    user_id: str,
    start_iso: str,
    duration_minutes: int = config.DEFAULT_APPT_MIN,
    provider: str = config.DEFAULT_PROVIDER,
    location: str = config.DEFAULT_LOCATION,
):
    """
    Insert a pending appointment. Accepts ISO or natural-language-ish datetime.
    Normalizes to clinic TZ for consistency with availability math.
    """
    tz = _clinic_tz()
    # Parse and normalize to clinic tz
    start_dt = du.parse(start_iso)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=tz)
    else:
        start_dt = start_dt.astimezone(tz)

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    with db_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO appointments
                (user_id, chat_session_id, start_time, end_time, status, notes, provider_name, location)
            VALUES
                (%s, NULL, %s, %s, 'pending', %s, %s, %s)
            RETURNING id
            """,
            (user_id, start_dt, end_dt, "Created via chatbot", provider, location),
        )
        row = cur.fetchone()

    return row["id"], start_dt, end_dt, provider, location
