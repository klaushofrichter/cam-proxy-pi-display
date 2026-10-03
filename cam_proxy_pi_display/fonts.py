"""DejaVu Sans (Debian: fonts-dejavu-core), with Pillow's own font as the fallback."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

log = logging.getLogger(__name__)

SEARCH = (
    "/usr/share/fonts/truetype/dejavu",  # Debian, Ubuntu
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/TTF",
    "~/Library/Fonts",
    "/Library/Fonts",
)
FILES = {"regular": "DejaVuSans.ttf", "bold": "DejaVuSans-Bold.ttf"}


def find_dir(fonts_dir: str = "") -> Path | None:
    """The first directory with both DejaVu files: the configured one, $CPPD_FONTS_DIR, then SEARCH."""
    candidates = [fonts_dir, os.environ.get("CPPD_FONTS_DIR", ""), *SEARCH]
    for c in candidates:
        if not c:
            continue
        d = Path(c).expanduser()
        if all((d / f).is_file() for f in FILES.values()):
            return d
    return None


class Fonts:
    def __init__(self, fonts_dir: str = ""):
        self.dir = find_dir(fonts_dir)
        if self.dir is None:
            log.warning("DejaVu fonts not found (install fonts-dejavu-core); using Pillow's default font")

    @lru_cache(maxsize=16)  # noqa: B019 (one Fonts per process)
    def get(self, weight: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if self.dir is not None:
            return ImageFont.truetype(str(self.dir / FILES[weight]), size)
        return ImageFont.load_default(size)
