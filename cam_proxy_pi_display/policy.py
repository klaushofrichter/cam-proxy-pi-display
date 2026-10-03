"""When to drive the panel (pure; the caller passes the time).

The rules (design, "Refresh policy"):
- a timer draws the page shown every `timer_min`;
- the API is polled every minute without touching the panel; a change of the set of
  problems redraws the Overview, but only after it held for `problem_confirm_polls`
  polls in a row, at most once per `problem_min_interval_min` (a change inside that time
  is drawn when it ends, as one redraw), and at most `problem_max_per_hour` times an
  hour; past that only the timer draws and the Overview says "changing often";
- keys draw at once (the caller does that and reports it with `drawn(..., "key")`);
  `return_to_overview_min` after a key the Overview comes back;
- a full clear once a day at `daily_clear` (local time) against ghosting.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .config import RefreshConfig, parse_hhmm

OVERVIEW = "overview"
HOUR = 3600.0


@dataclass(frozen=True)
class Draw:
    page: str
    reason: str  # start, key, timer, problem, return, clear


class RefreshPolicy:
    def __init__(self, cfg: RefreshConfig, now: float, local_now: datetime | None = None):
        self.cfg = cfg
        self.page = OVERVIEW
        self.last_draw_at: float | None = None
        self.key_at: float | None = None
        self.shown: frozenset[str] | None = None
        self.latest: frozenset[str] | None = None
        self._count = 0
        self.confirmed: frozenset[str] | None = None
        self._problem_draws: deque[float] = deque()
        self._clear_hm = parse_hhmm(cfg.daily_clear)
        self._last_clear: date | None = None
        if local_now is not None:
            today_clear = local_now.replace(hour=self._clear_hm[0], minute=self._clear_hm[1], second=0, microsecond=0)
            self._last_clear = local_now.date() if local_now >= today_clear else local_now.date() - timedelta(days=1)

    # --- inputs ---------------------------------------------------------------

    def observe(self, problems: frozenset[str], now: float) -> None:
        """One poll's (or a key's fresh fetch's) set of problems."""
        if problems == self.latest:
            self._count += 1
        else:
            self.latest = problems
            self._count = 1
        if self._count >= self.cfg.problem_confirm_polls:
            self.confirmed = problems

    def drawn(self, page: str, problems: frozenset[str] | None, now: float, reason: str) -> None:
        """The panel now shows `page` drawn from data with these problems."""
        self.page = page
        self.last_draw_at = now
        self.shown = problems
        if reason == "key" and page != OVERVIEW:
            self.key_at = now
        elif page == OVERVIEW:
            self.key_at = None
        if reason == "problem":
            self._problem_draws.append(now)

    def cleared(self, local_now: datetime) -> None:
        self._last_clear = local_now.date()

    # --- decisions --------------------------------------------------------------

    def _prune(self, now: float) -> None:
        while self._problem_draws and now - self._problem_draws[0] >= HOUR:
            self._problem_draws.popleft()

    def changing_often(self, now: float) -> bool:
        self._prune(now)
        return len(self._problem_draws) >= self.cfg.problem_max_per_hour

    def problem_pending(self) -> bool:
        """A confirmed set of problems the panel doesn't show yet (and the latest poll agrees)."""
        return self.confirmed is not None and self.latest == self.confirmed and self.confirmed != self.shown

    def due(self, now: float) -> Draw | None:
        if self.last_draw_at is None:
            return Draw(OVERVIEW, "start")
        if self.problem_pending() and not self.changing_often(now):
            last = self._problem_draws[-1] if self._problem_draws else None
            if last is None or now - last >= self.cfg.problem_min_interval_min * 60:
                return Draw(OVERVIEW, "problem")
        returning = self.page != OVERVIEW and self.key_at is not None
        if returning and now - self.key_at >= self.cfg.return_to_overview_min * 60:
            return Draw(OVERVIEW, "return")
        if now - self.last_draw_at >= self.cfg.timer_min * 60:
            return Draw(self.page, "timer")
        return None

    def clear_due(self, local_now: datetime) -> bool:
        h, m = self._clear_hm
        if (local_now.hour, local_now.minute) < (h, m):
            return False
        return self._last_clear != local_now.date()
