#!/usr/bin/env python3
"""Render the review set of pages as PNGs, scaled up (nearest neighbour) for reading on a screen.

    python3 scripts/render_review.py OUT_DIR [--scale 3] [--all]

--all renders every golden state instead of the review set. Needs the DejaVu fonts
(fonts-dejavu-core, or CPPD_FONTS_DIR pointing at DejaVuSans.ttf and DejaVuSans-Bold.ttf).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from cam_proxy_pi_display.fonts import Fonts  # noqa: E402
from cam_proxy_pi_display.render import render  # noqa: E402
from tests.scenarios import GOLDEN, NOW, REVIEW, view  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    fonts = Fonts()
    if fonts.dir is None:
        print("DejaVu fonts not found", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    for name, page, v in GOLDEN if args.all else REVIEW:
        img = render(page, view(v), NOW, fonts)
        big = img.convert("L").resize((img.width * args.scale, img.height * args.scale), Image.Resampling.NEAREST)
        big.save(args.out / f"{name}.png")
        print(args.out / f"{name}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
