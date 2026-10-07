"""The page states the golden images and the review set are drawn from."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cam_proxy_pi_display.collector import Snapshot
from cam_proxy_pi_display.render import View
from tests.fixtures import GENERATED_AT_MS, load_fixture

# A fixed zone (UTC-5, like America/Chicago in October) without tzdata.
TZ = timezone(timedelta(hours=-5))
NOW = datetime.fromtimestamp(GENERATED_AT_MS / 1000, TZ)  # 2026-10-03 10:25
FETCHED = GENERATED_AT_MS / 1000

# What the service reads itself (documentation address).
LOCAL = {
    "disk": {"sizeBytes": 245457289216, "freeBytes": 205078347776, "usedBytes": 26414358528, "usedPercent": 11.4},
    "cpuTempC": 53.1,
    "uptimeS": 412233,
    "model": "Raspberry Pi 4 Model B Rev 1.5",
    "ip": "192.0.2.20",
}


def snap(name: str | None, *, error: str | None = None, at: float = FETCHED, local: dict | None = None) -> Snapshot:
    return Snapshot(
        health=load_fixture(name) if name else None,
        error=error,
        fetched_at=at,
        local=LOCAL if local is None else local,
    )


def with_sd(name: str, *, inventory_failed: bool = False) -> Snapshot:
    """The Pi as cam-proxy answers since #199: the Archive item and the camera's SD card (12 items)."""
    s = snap(name)
    items = s.health["items"]
    at = next(i for i, it in enumerate(items) if it["id"] == "ftp") + 1
    items.insert(
        at,
        {
            "id": "sd",
            "label": "SD card",
            "value": "overwrite_off",
            "text": "Overwrite is off: the camera stops recording to its SD card when it is full",
            "problem": False,
            "warning": True,
        },
    )
    at = next(i for i, it in enumerate(items) if it["id"] == "disk") + 1
    items.insert(
        at,
        {
            "id": "archive",
            "label": "Archive",
            "value": 0.1,
            "text": "3 clips, 0.2 GB (0.1 % of disk)",
            "problem": False,
        },
    )
    if inventory_failed:
        inv = next(it for it in items if it["id"] == "inventory")
        inv.update(value="failed", text="clips: failed", problem=True)
        s.health["ok"], s.health["problemCount"] = False, 1
    return s


def view(name: str) -> View:
    if name == "ok":
        return View(snap("pi-ok"))
    if name == "sd":
        return View(with_sd("pi-ok"))
    if name == "sd-inventory-failed":
        return View(with_sd("pi-ok", inventory_failed=True))
    if name == "problems":
        return View(snap("pi-problems"))
    if name == "cluster":
        return View(snap("cluster", local={}))
    if name == "unreachable":
        return View(snap(None, error="connection refused"), last_ok=snap("pi-ok", at=FETCHED - 240))
    if name == "unreachable-yesterday":  # last answer Fri 18:02, read Sat 10:25
        return View(snap(None, error="timeout"), last_ok=snap("pi-ok", at=FETCHED - (16 * 60 + 23) * 60))
    if name == "unreachable-cold":  # never answered since the start
        return View(snap(None, error="timeout"))
    if name == "changing-often":
        return View(snap("pi-problems"), changing_often=True)
    raise KeyError(name)


# (golden name, page, view name)
GOLDEN = [
    ("overview-ok", "overview", "ok"),
    ("overview-sd", "overview", "sd"),
    ("overview-problems", "overview", "problems"),
    ("overview-cluster", "overview", "cluster"),
    ("overview-unreachable", "overview", "unreachable"),
    ("overview-changing-often", "overview", "changing-often"),
    ("overview-unreachable-yesterday", "overview", "unreachable-yesterday"),
    ("camera-ok", "camera", "ok"),
    ("camera-problems", "camera", "problems"),
    ("camera-cluster", "camera", "cluster"),
    ("camera-unreachable", "camera", "unreachable"),
    ("proxy-ok", "proxy", "ok"),
    ("proxy-problems", "proxy", "problems"),
    ("proxy-unreachable", "proxy", "unreachable"),
    ("proxy-unreachable-cold", "proxy", "unreachable-cold"),
    ("pi-ok", "pi", "ok"),
    ("pi-problems", "pi", "problems"),
    ("pi-cluster", "pi", "cluster"),
    ("pi-unreachable", "pi", "unreachable"),
    ("stopped", "stopped", "ok"),
    ("stopped-unreachable", "stopped", "unreachable"),
]

# The set Klaus reviews: (file name, page, view name)
REVIEW = [
    ("overview-ok", "overview", "ok"),
    ("overview-problems", "overview", "problems"),
    ("camera", "camera", "ok"),
    ("proxy", "proxy", "ok"),
    ("pi", "pi", "ok"),
    ("proxy-unreachable", "overview", "unreachable"),
    ("proxy-unreachable-yesterday", "overview", "unreachable-yesterday"),
    ("changing-often", "overview", "changing-often"),
    ("stopped", "stopped", "ok"),
]
