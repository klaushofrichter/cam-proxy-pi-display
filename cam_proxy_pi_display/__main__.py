"""cam-proxy-pi-display: cam-proxy's health on the e-paper HAT.

python3 -m cam_proxy_pi_display [--config FILE] [--fake-panel DIR] [--once PAGE] [--health-file FILE]
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from . import config as config_mod
from . import localstats
from .collector import Snapshot, fetch_health, parse_health
from .fonts import Fonts
from .panel import FakePanel
from .render import RENDERERS, View, render

log = logging.getLogger("cam_proxy_pi_display")


def installed_version() -> str:
    p = Path(__file__).resolve().parent.parent / "VERSION"
    try:
        return p.read_text().strip() or "dev"
    except OSError:
        return "dev"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="cam-proxy-pi-display", description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, help=f"config file (default {config_mod.DEFAULT_PATH}, optional)")
    ap.add_argument("--fake-panel", type=Path, metavar="DIR", help="write PNGs to DIR instead of driving the panel")
    ap.add_argument(
        "--once",
        choices=sorted(RENDERERS),
        metavar="PAGE",
        help="draw one page (overview, camera, proxy, pi, stopped) and exit",
    )
    ap.add_argument(
        "--health-file",
        type=Path,
        metavar="FILE",
        help="read the health answer from a JSON file instead of the API (with --once)",
    )
    ap.add_argument("--no-keys", action="store_true", help="don't watch the keys")
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap.parse_args(argv)


def make_panel(args):
    if args.fake_panel:
        return FakePanel(args.fake_panel)
    from .panel import EpdPanel

    return EpdPanel()


def once(args, cfg, fonts) -> int:
    now = time.time()
    if args.health_file:
        health, err = parse_health(args.health_file.read_bytes())
    else:
        health, err = fetch_health(cfg.api.url, cfg.api.timeout_s)
    snap = Snapshot(health=health, error=err, fetched_at=now, local=localstats.read())
    img = render(args.once, View(snap, snap if health else None), time_now(now), fonts)
    panel = make_panel(args)
    if isinstance(panel, FakePanel):
        panel.label = args.once
    try:
        panel.show(img)
    finally:
        panel.close()
    return 0


def time_now(t: float):
    from datetime import datetime

    from .fmt import system_tz

    return datetime.fromtimestamp(t, system_tz())


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        cfg = config_mod.load(args.config)
    except config_mod.ConfigError as e:
        log.error("%s", e)
        return 2
    fonts = Fonts(cfg.display.fonts_dir)
    log.info("cam-proxy-pi-display %s, API %s, fonts %s", installed_version(), cfg.api.url, fonts.dir or "default")
    if args.once:
        return once(args, cfg, fonts)

    from .service import Service

    panel = make_panel(args)
    svc = Service(cfg, panel, fonts)
    keys = None
    if not args.no_keys:
        try:
            from .keys import Keys

            keys = Keys(cfg.keys, svc.press)
        except Exception as e:  # noqa: BLE001 (no GPIO here: run without keys)
            log.warning("keys not available (%s); running without keys", e)

    def on_signal(signum, _frame):
        log.info("signal %s: stopping", signal.Signals(signum).name)
        svc.request_stop()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    try:
        svc.run()
    finally:
        if keys is not None:
            keys.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
