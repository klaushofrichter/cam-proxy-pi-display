"""The e-paper panel (Waveshare 2.7 inch HAT, V1 driver) or a fake that writes PNGs.

Measured on the HAT (2026-10-03): init + Clear 18.3 s, a full draw 2.5 s. So a draw never
clears first; only the daily anti-ghosting clear does. The panel sleeps after every draw
(the driver's sleep also releases SPI), and keeps its image without power.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Protocol

from PIL import Image

log = logging.getLogger(__name__)


class Panel(Protocol):
    def show(self, image: Image.Image, *, clear_first: bool = False) -> None: ...

    def close(self) -> None: ...


class EpdPanel:
    """The real panel through the vendored Waveshare epd2in7 (V1) driver."""

    def __init__(self):
        # Imported here: the driver touches GPIO and SPI at import (Pi only).
        from .vendor.waveshare_epd import epd2in7

        self._epd = epd2in7.EPD()
        log.info("panel: Waveshare epd2in7 (V1), %dx%d landscape", self._epd.height, self._epd.width)

    def show(self, image: Image.Image, *, clear_first: bool = False) -> None:
        t0 = time.monotonic()
        if self._epd.init() == -1:
            raise RuntimeError("e-paper init failed")
        if clear_first:
            self._epd.Clear(0xFF)
        self._epd.display(self._epd.getbuffer(image))
        self._epd.sleep()
        log.info("panel: drawn in %.1f s%s", time.monotonic() - t0, " (with clear)" if clear_first else "")

    def close(self) -> None:
        try:
            from .vendor.waveshare_epd import epdconfig

            epdconfig.module_exit(cleanup=True)
        except Exception:  # noqa: BLE001 (best effort at exit)
            log.debug("panel: module_exit failed", exc_info=True)


class FakePanel:
    """Writes each draw as a PNG (for the Mac and CI): NNNN-<label>.png and latest.png."""

    def __init__(self, directory: Path, clock=time.time):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.count = 0
        self.clears = 0
        self.label = "page"
        self._clock = clock
        self.images: list[Image.Image] = []

    def show(self, image: Image.Image, *, clear_first: bool = False) -> None:
        self.count += 1
        if clear_first:
            self.clears += 1
        self.images.append(image.copy())
        stamp = datetime.fromtimestamp(self._clock()).strftime("%H%M%S")
        name = f"{self.count:04d}-{stamp}-{self.label}{'-clear' if clear_first else ''}.png"
        image.save(self.dir / name)
        image.save(self.dir / "latest.png")
        log.info("fake panel: wrote %s", self.dir / name)

    def close(self) -> None:
        pass
