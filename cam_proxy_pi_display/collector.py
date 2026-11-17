"""Reads cam-proxy's local health API (schema 1) and the Pi's own figures."""

from __future__ import annotations

import http.client
import json
import logging
import socket
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

SCHEMA = 1
UNREACHABLE = "proxy-unreachable"

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Snapshot:
    """One look at the proxy: its health answer, or why there is none."""

    health: dict | None
    error: str | None
    fetched_at: float  # unix seconds
    local: dict = field(default_factory=dict)  # localstats.read() at the same time


def snapshot(fetch: Callable[[], tuple[dict | None, str | None]], local: Callable[[], dict], now: float) -> Snapshot:
    """Ask the proxy (`fetch`) and read the Pi's own figures (`local`, optional: a failure leaves them out)."""
    health, err = fetch()
    try:
        figures = local()
    except Exception:  # noqa: BLE001 (local figures are optional)
        log.exception("reading the local figures failed")
        figures = {}
    return Snapshot(health=health, error=err, fetched_at=now, local=figures)


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
    except OSError as e:  # TimeoutError too: _reason maps it
        return None, _reason(e)
    except http.client.HTTPException:  # BadStatusLine, LineTooLong, IncompleteRead: not HTTP as expected
        return None, "bad answer"
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
    if isinstance(r, TimeoutError):  # socket.timeout is TimeoutError
        return "timeout"
    if isinstance(r, ConnectionRefusedError):
        return "connection refused"
    if isinstance(r, socket.gaierror):
        return "name not found"
    if isinstance(r, OSError) and r.strerror:
        return r.strerror.lower()
    return str(r)[:40] or "error"


def valid_items(health: dict) -> list[dict]:
    """The answer's items, without entries that are not objects."""
    return [i for i in health.get("items", []) if isinstance(i, dict)]


def is_problem(item: dict) -> bool:
    """The API's problem flag (cam-proxy decides what is a problem)."""
    return item.get("problem") is True


def problem_count(health: dict) -> int:
    """The answer's problemCount, else the number of items with problem: true (all of them, shown or not)."""
    n = health.get("problemCount")
    if isinstance(n, int) and not isinstance(n, bool) and n >= 0:
        return n
    return sum(1 for i in valid_items(health) if is_problem(i))


def problem_set(snap: Snapshot) -> frozenset[str]:
    """The ids of the items with problem: true; an unreachable proxy is a problem of its own."""
    if snap.health is None:
        return frozenset({UNREACHABLE})
    return frozenset(str(i.get("id")) for i in valid_items(snap.health) if is_problem(i))
