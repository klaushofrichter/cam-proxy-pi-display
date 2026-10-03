"""Short texts for times, ages and sizes on a 264 px wide page."""

from __future__ import annotations

from datetime import datetime

GIB = 1024**3
MIB = 1024**2
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def hhmm(t: datetime) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"


def clock(ms: int | float, now: datetime) -> str:
    """'08:31' today, else '2 Oct 08:31' (in now's time zone)."""
    t = datetime.fromtimestamp(ms / 1000, now.tzinfo)
    if t.date() == now.date():
        return hhmm(t)
    return f"{t.day} {MONTHS[t.month - 1]} {hhmm(t)}"


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


def ago(ms: int | float, now: datetime) -> str:
    return duration(now.timestamp() - ms / 1000) + " ago"


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
