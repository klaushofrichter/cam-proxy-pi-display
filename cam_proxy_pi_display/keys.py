"""The HAT's four keys (left side in landscape, top to bottom).

Keys 1-3 show the Camera, Proxy and Pi pages; key 4 (bottom) is Update on a short press
and the Overview on a long press. gpiozero calls back from its own threads; the actions
go to a callback (the service puts them on its queue).
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from .config import KeysConfig

log = logging.getLogger(__name__)

PAGE_KEYS = ("camera", "proxy", "pi")
UPDATE = "update"
OVERVIEW = "overview"


class KeyLogic:
    """Turns press/held/release of key index 0-3 into actions."""

    def __init__(self, emit: Callable[[str], None]):
        self._emit = emit
        self._held = False

    def pressed(self, index: int) -> None:
        if index < len(PAGE_KEYS):
            self._emit(PAGE_KEYS[index])
        else:
            self._held = False

    def held(self, index: int) -> None:
        if index == len(PAGE_KEYS):
            self._held = True
            self._emit(OVERVIEW)

    def released(self, index: int) -> None:
        if index == len(PAGE_KEYS):
            if not self._held:
                self._emit(UPDATE)
            self._held = False


class Keys:
    """gpiozero Buttons on the configured pins (active low, pull-ups)."""

    def __init__(self, cfg: KeysConfig, emit: Callable[[str], None], pin_factory=None):
        from gpiozero import Button  # Debian: python3-gpiozero (lgpio backend)

        self.logic = KeyLogic(emit)
        self.buttons = []
        for i, pin in enumerate(cfg.pins):
            b = Button(
                pin,
                pull_up=True,
                bounce_time=cfg.bounce_s,
                hold_time=cfg.long_press_s,
                pin_factory=pin_factory,
            )
            b.when_pressed = lambda _b=None, i=i: self.logic.pressed(i)
            b.when_held = lambda _b=None, i=i: self.logic.held(i)
            b.when_released = lambda _b=None, i=i: self.logic.released(i)
            self.buttons.append(b)
        log.info("keys on GPIO %s (top to bottom), long press %.1f s", list(cfg.pins), cfg.long_press_s)

    def close(self) -> None:
        for b in self.buttons:
            b.close()
