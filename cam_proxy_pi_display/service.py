"""One process: poll the API, decide (policy), render, drive the panel, take keys.

Only the main loop touches the panel, so it is never driven twice at once. Key callbacks
(gpiozero threads) only queue actions; presses during a draw wait, and the last one wins.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from datetime import datetime, tzinfo

from . import fmt, localstats
from .collector import Snapshot, fetch_health, problem_set
from .config import Config
from .fonts import Fonts
from .panel import Panel
from .policy import RefreshPolicy
from .render import View, render

log = logging.getLogger(__name__)

STOP = "__stop__"


class Service:
    def __init__(
        self,
        cfg: Config,
        panel: Panel,
        fonts: Fonts,
        *,
        fetch: Callable[[], tuple[dict | None, str | None]] | None = None,
        local: Callable[[], dict] = localstats.read,
        clock: Callable[[], float] = time.time,
        tz: tzinfo | None = None,
    ):
        self.cfg = cfg
        self.panel = panel
        self.fonts = fonts
        self.fetch = fetch or (lambda: fetch_health(cfg.api.url, cfg.api.timeout_s))
        self.local = local
        self.clock = clock
        self.tz = tz  # None: the system's zone
        self._system_tz = fmt.system_tz()
        self.q: queue.Queue[str] = queue.Queue()
        self.stopping = threading.Event()
        now = clock()
        self.policy = RefreshPolicy(cfg.refresh, now, self.local_time(now))
        self.snap: Snapshot | None = None
        self.last_ok: Snapshot | None = None
        self.next_poll = now

    # --- time -----------------------------------------------------------------------

    def local_time(self, t: float) -> datetime:
        # The zone with its DST rules, so older timestamps get their own offset.
        return datetime.fromtimestamp(t, self.tz or self._system_tz)

    # --- inputs ------------------------------------------------------------------------

    def press(self, action: str) -> None:
        """From the key threads."""
        self.q.put(action)

    def request_stop(self) -> None:
        self.stopping.set()
        self.q.put(STOP)

    def poll(self, now: float) -> Snapshot:
        health, err = self.fetch()
        try:
            local = self.local()
        except Exception:  # noqa: BLE001 (local figures are optional)
            log.exception("reading the local figures failed")
            local = {}
        snap = Snapshot(health=health, error=err, fetched_at=now, local=local)
        if health is not None:
            if self.snap is not None and self.snap.health is None:
                log.info("proxy reachable again")
            self.last_ok = snap
        elif self.snap is None or self.snap.health is not None:
            log.warning("proxy unreachable: %s", err)
        self.snap = snap
        self.policy.observe(problem_set(snap), now)
        self.next_poll = now + self.cfg.api.poll_interval_s
        return snap

    # --- drawing -------------------------------------------------------------------------

    def draw(self, page: str, reason: str, now: float, *, clear: bool = False) -> None:
        assert self.snap is not None
        view = View(self.snap, self.last_ok, self.policy.changing_often(now))
        img = render(page, view, self.local_time(now), self.fonts)
        if hasattr(self.panel, "label"):
            self.panel.label = f"{page}-{reason}"
        try:
            self.panel.show(img, clear_first=clear)
        except Exception:  # noqa: BLE001 (keep running; the next timer tries again)
            log.exception("drawing %s (%s) failed", page, reason)
        else:
            log.info("drew %s (%s), problems: %s", page, reason, sorted(problem_set(self.snap)) or "none")
        self.policy.drawn(page, problem_set(self.snap), now, reason)

    def key(self, action: str, now: float) -> None:
        page = self.policy.page if action == "update" else action
        log.info("key: %s -> %s", action, page)
        self.poll(now)  # a key always shows fresh data
        self.draw(page, "key", now)

    # --- the loop ----------------------------------------------------------------------------

    def _drain(self, first: str | None = None) -> list[str]:
        actions = [first] if first else []
        while True:
            try:
                actions.append(self.q.get_nowait())
            except queue.Empty:
                return actions

    def step(self, first_action: str | None = None) -> None:
        """One turn: keys first (the last press wins), then poll, the daily clear, what's due."""
        actions = [a for a in self._drain(first_action) if a != STOP]
        now = self.clock()
        if actions and not self.stopping.is_set():
            if len(actions) > 1:
                log.info("keys: %d presses queued, the last wins", len(actions))
            self.key(actions[-1], now)
            return
        if now >= self.next_poll:
            self.poll(now)
        local_now = self.local_time(now)
        due = self.policy.due(now)
        if self.policy.clear_due(local_now):
            self.draw(due.page if due else self.policy.page, "clear", now, clear=True)
            self.policy.cleared(local_now)
            return
        if due:
            self.draw(due.page, due.reason, now)

    def run(self) -> None:
        while not self.stopping.is_set():
            self.step()
            try:
                first = self.q.get(timeout=1.0)
            except queue.Empty:
                continue
            if first == STOP:
                break
            self.q.put(first)  # step() drains it with the rest
        self.shutdown()

    def shutdown(self) -> None:
        now = self.clock()
        if self.snap is None:
            self.snap = Snapshot(None, "not started", now, {})
        log.info("stopping: drawing the stopped page")
        try:
            img = render("stopped", View(self.snap, self.last_ok), self.local_time(now), self.fonts)
            if hasattr(self.panel, "label"):
                self.panel.label = "stopped"
            self.panel.show(img)
        except Exception:  # noqa: BLE001
            log.exception("drawing the stopped page failed")
        finally:
            self.panel.close()
