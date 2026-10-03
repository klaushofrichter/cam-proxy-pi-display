"""Short texts for times, ages and sizes on a 264 px wide page."""

from __future__ import annotations

from datetime import datetime, tzinfo
from zoneinfo import ZoneInfo

GIB = 1024**3
MIB = 1024**2
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def hhmm(t: datetime) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"


def stamp(t: int | float | datetime, tz: tzinfo | None = None) -> str:
    """The full local date and time, 'Sat Oct 3 10:25' (English names, 24 h).

    `t` is unix milliseconds (shown in `tz`) or an aware datetime (shown as it is).
    The screen may be read a day or more after it was drawn, so every time carries its date.
    """
    if not isinstance(t, datetime):
        t = datetime.fromtimestamp(t / 1000, tz or system_tz())
    return f"{DAYS[t.weekday()]} {MONTHS[t.month - 1]} {t.day} {hhmm(t)}"


def system_tz() -> tzinfo:
    """The system's zone with its DST rules (/etc/localtime), else the current offset."""
    try:
        with open("/etc/localtime", "rb") as f:
            return ZoneInfo.from_file(f)
    except (OSError, ValueError):
        return datetime.now().astimezone().tzinfo


def duration(seconds: float) -> str:
    """'45 s', '12 min', '2 h 5 min', '4 d 18 h'."""
    s = max(0, int(seconds))
    if s < 60:
        return f"{s} s"
    m = s // 60
    if m < 60:
        return f"{m} min"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h} h {m} min" if m else f"{h} h"
    d, h = divmod(h, 24)
    return f"{d} d {h} h" if h else f"{d} d"


def gb(n: int | float) -> str:
    return f"{n / GIB:.1f} GB"


def size(n: int | float) -> str:
    if n >= GIB:
        return gb(n)
    return f"{round(n / MIB)} MB"


def percent(p: float) -> str:
    return f"{p:.1f} %"


def offset_ms(ms: int) -> str:
    """Camera clock minus proxy clock: '-0.4 s', '+3 ms'."""
    if abs(ms) < 1000:
        return f"{ms:+d} ms"
    return f"{ms / 1000:+.1f} s"
