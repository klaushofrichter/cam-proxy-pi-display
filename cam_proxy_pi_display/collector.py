"""Reads cam-proxy's local health API (schema 1) and the Pi's own figures."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field

SCHEMA = 1
UNREACHABLE = "proxy-unreachable"


@dataclass(frozen=True)
class Snapshot:
    """One look at the proxy: its health answer, or why there is none."""

    health: dict | None
    error: str | None
    fetched_at: float  # unix seconds
    local: dict = field(default_factory=dict)  # localstats.read() at the same time

    @property
    def reachable(self) -> bool:
        return self.health is not None


def fetch_health(url: str, timeout: float) -> tuple[dict | None, str | None]:
    """GET the health answer. Returns (health, None) or (None, short reason)."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (URL from the admin's config)
            body = resp.read(1_000_000)
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return None, _reason(e.reason)
    except TimeoutError:
        return None, "timeout"
    except OSError as e:
        return None, _reason(e)
    return parse_health(body)


def parse_health(body: bytes | str) -> tuple[dict | None, str | None]:
    """Check an answer: JSON, schema 1, with items."""
    try:
        health = json.loads(body)
    except ValueError:
        return None, "bad answer"
    if not isinstance(health, dict):
        return None, "bad answer"
    if health.get("schema") != SCHEMA:
        if "schema" in health:
            return None, f"API schema {health['schema']} not supported"
        return None, "bad answer"
    if not isinstance(health.get("items"), list):
        return None, "bad answer"
    return health, None


def _reason(r) -> str:
    if isinstance(r, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(r, ConnectionRefusedError):
        return "connection refused"
    if isinstance(r, socket.gaierror):
        return "name not found"
    if isinstance(r, OSError) and r.strerror:
        return r.strerror.lower()
    return str(r)[:40] or "error"


def problem_set(snap: Snapshot) -> frozenset[str]:
    """The ids of the items with problem: true; an unreachable proxy is a problem of its own."""
    if snap.health is None:
        return frozenset({UNREACHABLE})
    return frozenset(
        str(i.get("id")) for i in snap.health.get("items", []) if isinstance(i, dict) and i.get("problem") is True
    )
