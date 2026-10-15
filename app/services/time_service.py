"""
Local-date helpers.

Entries are stored with naive UTC timestamps (datetime.utcnow). To group them
by the user's own calendar days, the browser sets a non-sensitive `mt_tz`
cookie with its UTC offset in minutes (see static/js/app.js). Without the
cookie everything falls back to UTC.
"""
from datetime import date, datetime, timedelta

TZ_COOKIE = 'mt_tz'
MAX_OFFSET_MINUTES = 14 * 60


def tz_offset_minutes(req=None) -> int:
    """User's offset from UTC in minutes (e.g. +330 for India), clamped to a valid range."""
    if req is None:
        try:
            from flask import request as req
            req.cookies  # noqa: B018 - raises outside a request context
        except Exception:
            return 0
    raw = req.cookies.get(TZ_COOKIE)
    if raw is None:
        # Behind Firebase Hosting only the session cookie arrives; /tz stores the offset there.
        try:
            from flask import session
            raw = session.get('tz_offset', 0)
        except Exception:
            raw = 0
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return max(-MAX_OFFSET_MINUTES, min(MAX_OFFSET_MINUTES, value))


def to_local(dt_utc: datetime, offset: int) -> datetime:
    return dt_utc + timedelta(minutes=offset)


def local_today(offset: int) -> date:
    return to_local(datetime.utcnow(), offset).date()


def utc_range_for_local_days(first_day: date, last_day: date, offset: int):
    """UTC [start, end) covering local calendar days first_day..last_day inclusive."""
    start_local = datetime.combine(first_day, datetime.min.time())
    end_local = datetime.combine(last_day + timedelta(days=1), datetime.min.time())
    return start_local - timedelta(minutes=offset), end_local - timedelta(minutes=offset)
