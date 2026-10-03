"""Pure renderer: a view of the data + a page + the time -> a 264x176 1-bit image.

Every page has a header with the page name and "updated HH:MM" (the time of its data:
the panel keeps an image without power, so a stale screen shows its age). Problem lines
are inverted (white on black), like the red lines on cam-proxy's Status page. A figure
that is null in the API (or can't be read locally) is left off.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PIL import Image, ImageDraw

from . import fmt
from .collector import Snapshot
from .fonts import Fonts

WIDTH, HEIGHT = 264, 176
BLACK, WHITE = 0, 255
HEADER_H = 18
ROW_H = 14
MARGIN = 4

PAGES = ("overview", "camera", "proxy", "pi")
TITLES = {"overview": "Overview", "camera": "Camera", "proxy": "Proxy", "pi": "Pi", "stopped": "Display stopped"}
DEFAULT_THRESHOLDS = {"diskPercent": 90, "tempC": 75}


@dataclass(frozen=True)
class View:
    snap: Snapshot  # the newest look at the proxy (may be unreachable)
    last_ok: Snapshot | None = None  # the newest one that answered
    changing_often: bool = False


class Canvas:
    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.img = Image.new("1", (WIDTH, HEIGHT), WHITE)
        self.d = ImageDraw.Draw(self.img)
        self.y = HEADER_H + 2
        self.lines: list[tuple[str, str, bool]] = []
        self.header_title_drawn = ""  # (label, text, problem) as drawn, for the tests
        self.regular = fonts.get("regular", 12)
        self.bold = fonts.get("bold", 12)

    def width(self, text: str, font) -> float:
        return self.d.textlength(text, font=font)

    def fit(self, text: str, font, max_w: float) -> str:
        if self.width(text, font) <= max_w:
            return text
        while text and self.width(text + "…", font) > max_w:
            text = text[:-1]
        return text + "…"

    def header(self, title: str, right: str) -> None:
        self.lines.append((title, right, False))
        self.d.rectangle((0, 0, WIDTH - 1, HEADER_H - 1), fill=BLACK)
        small = self.fonts.get("regular", 11)
        right_w = self.width(right, small)
        self.d.text((WIDTH - MARGIN, 13), right, font=small, fill=WHITE, anchor="rs")
        title_font = self.fonts.get("bold", 13)
        self.header_title_drawn = self.fit(title, title_font, WIDTH - 3 * MARGIN - right_w)
        self.d.text(
            (MARGIN, 13),
            self.header_title_drawn,
            font=title_font,
            fill=WHITE,
            anchor="ls",
        )

    def room(self, h: int = ROW_H) -> bool:
        return self.y + h <= HEIGHT

    def row(
        self,
        label: str,
        text: str = "",
        *,
        problem: bool = False,
        bold: bool = False,
        col: int = 112,
        bar: tuple[int, int, float] | None = None,
    ) -> None:
        """One line: label at the left margin, text from `col`; inverted when `problem`."""
        if not self.room():
            return
        self.lines.append((label, text, problem))
        fg = WHITE if problem else BLACK
        if problem:
            self.d.rectangle((0, self.y, WIDTH - 1, self.y + ROW_H - 1), fill=BLACK)
        base = self.y + 11
        lab_font = self.bold if bold else self.regular
        if text or bar:
            label = self.fit(label, lab_font, (bar[0] if bar else col) - MARGIN - 4)
        else:
            label = self.fit(label, lab_font, WIDTH - 2 * MARGIN)
        self.d.text((MARGIN, base), label, font=lab_font, fill=fg, anchor="ls")
        if bar:
            x0, x1, pct = bar
            top, bottom = self.y + 3, self.y + ROW_H - 4
            self.d.rectangle((x0, top, x1, bottom), outline=fg)
            fill_to = x0 + round((x1 - x0) * max(0.0, min(100.0, pct)) / 100)
            if fill_to > x0:
                self.d.rectangle((x0, top, fill_to, bottom), fill=fg)
        if text:
            font = self.bold if bold else self.regular
            self.d.text((col, base), self.fit(text, font, WIDTH - MARGIN - col), font=font, fill=fg, anchor="ls")
        self.y += ROW_H

    def big(self, text: str, *, problem: bool = False, size: int = 16) -> None:
        h = size + 8
        if not self.room(h):
            return
        self.lines.append((text, "", problem))
        font = self.fonts.get("bold", size)
        fg = WHITE if problem else BLACK
        if problem:
            self.d.rectangle((0, self.y, WIDTH - 1, self.y + h - 1), fill=BLACK)
        self.d.text(
            (WIDTH // 2, self.y + h // 2), self.fit(text, font, WIDTH - 2 * MARGIN), font=font, fill=fg, anchor="mm"
        )
        self.y += h

    def gap(self, h: int = 3) -> None:
        self.y += h

    def footer(self, text: str, *, problem: bool = False, bold: bool = True) -> None:
        """A last line at the bottom edge (the summary)."""
        self.y = max(self.y, HEIGHT - ROW_H)
        self.row(text, problem=problem, bold=bold)


# --- helpers -----------------------------------------------------------------------


def _items(health: dict) -> dict[str, dict]:
    return {i.get("id"): i for i in health.get("items", []) if isinstance(i, dict)}


def _thresholds(view: View) -> dict:
    src = view.snap.health or (view.last_ok.health if view.last_ok else None) or {}
    t = dict(DEFAULT_THRESHOLDS)
    t.update({k: v for k, v in (src.get("thresholds") or {}).items() if isinstance(v, (int, float))})
    return t


def _at(ms: int | float, now: datetime) -> str:
    """A timestamp on a page: always the full date ("Sat Oct 3 10:25"), in now's zone."""
    return fmt.stamp(ms, now.tzinfo)


def _updated(view: View, now: datetime) -> str:
    return f"updated {_at(view.snap.fetched_at * 1000, now)}"


def _summary(c: Canvas, n: int, changing_often: bool) -> None:
    text = "All OK" if n == 0 else f"{n} problem" + ("" if n == 1 else "s")
    if changing_often:
        text += " · changing often"
    c.footer(text, problem=n > 0)


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


# --- pages -----------------------------------------------------------------------------


def _overview(c: Canvas, view: View, now: datetime) -> None:
    h = view.snap.health
    if h is None:
        _unreachable_block(c, view, now)
        _local_rows(c, view, col=96)
        _summary(c, 1, view.changing_often)
        return
    items = [i for i in h.get("items", []) if isinstance(i, dict)]
    # The text column starts after the widest label (labels are shown as the API gives them).
    widest = max((c.width(str(i.get("label", "")), c.regular) for i in items), default=0)
    col = int(min(132, MARGIN + widest + 8))
    for it in items:
        label, text, problem = str(it.get("label", "")), str(it.get("text", "")), it.get("problem") is True
        if it.get("id") == "disk" and _num(it.get("value")):
            c.row(label, text, problem=problem, col=col, bar=(40, col - 8, float(it["value"])))
        else:
            c.row(label, text, problem=problem, col=col)
    count = h.get("problemCount")
    if not isinstance(count, int):
        count = sum(1 for i in items if i.get("problem") is True)
    _summary(c, count, view.changing_often)


def _unreachable_block(c: Canvas, view: View, now: datetime) -> None:
    c.big("Proxy unreachable", problem=True)
    c.row("Reason", view.snap.error or "no answer", col=96)
    if view.last_ok is not None:
        c.row("Last data", _at(view.last_ok.fetched_at * 1000, now), col=96)


def _local_rows(c: Canvas, view: View, col: int) -> None:
    """The Pi's own figures (the service reads them itself)."""
    loc = view.snap.local or {}
    th = _thresholds(view)
    disk = loc.get("disk")
    if isinstance(disk, dict) and _num(disk.get("usedPercent")):
        p = float(disk["usedPercent"])
        c.row(
            "Disk",
            f"{fmt.percent(p)}, {fmt.gb(disk['freeBytes'])} free",
            problem=p >= th["diskPercent"],
            col=col + 0,
            bar=(44, col - 6, p),
        )
    if _num(loc.get("cpuTempC")):
        t = float(loc["cpuTempC"])
        c.row("CPU temp", f"{t:.1f} °C", problem=t >= th["tempC"], col=col)
    if _num(loc.get("uptimeS")):
        c.row("Uptime", fmt.duration(loc["uptimeS"]), col=col)
    if loc.get("ip"):
        c.row("IP address", str(loc["ip"]), col=col)


def _camera(c: Canvas, view: View, now: datetime) -> None:
    h = view.snap.health
    if h is None:
        _unreachable_block(c, view, now)
        return
    it = _items(h)
    cam = h.get("camera") or {}
    stream = h.get("stream") or {}
    events = h.get("events") or {}
    ftp = h.get("ftp") or {}
    col = 80

    cam_item = it.get("camera", {})
    state = str(cam_item.get("text", "online" if cam.get("online") else "offline"))
    if not cam.get("online") and cam.get("error"):
        state += f" ({cam['error']})"
    name = str(cam.get("name") or cam.get("id") or "Camera")
    c.row(name, state, problem=cam_item.get("problem") is True, col=col)
    if _num(cam.get("since")):
        c.row("Since", _at(cam["since"], now), col=col)
    if cam.get("model"):
        c.row("Model", str(cam["model"]), col=col)
    if cam.get("firmware"):
        c.row("Firmware", str(cam["firmware"]), col=col)
    address = str(cam.get("address") or "")
    if _num(cam.get("clockOffsetMs")):
        address += (", " if address else "") + f"clock {fmt.offset_ms(int(cam['clockOffsetMs']))}"
    if address:
        c.row("Address", address, col=col)

    st_item = it.get("stream", {})
    st = str(st_item.get("text", ""))
    if stream.get("enabled") and _num(stream.get("lastFrameAt")):
        st += f", frame {_at(stream['lastFrameAt'], now)}"
    c.row("Stream", st, problem=st_item.get("problem") is True, col=col)

    ev_item = it.get("events", {})
    ev = str(ev_item.get("text", events.get("onvif", "")))
    if _num(events.get("resubscribes")):
        n = int(events["resubscribes"])
        ev += f", {n} resubscribe" + ("" if n == 1 else "s")
    c.row("Events", ev, problem=ev_item.get("problem") is True, col=col)

    ftp_item = it.get("ftp", {})
    stalled = ftp.get("stalled") is True
    if ftp.get("enabled") is False:
        c.row("FTP", str(ftp_item.get("text", "off in the proxy")), problem=ftp_item.get("problem") is True, col=col)
    else:
        upload = ftp.get("cameraUpload")
        text = str(ftp_item.get("text", "")) if not stalled else (str(upload) if upload else "")
        c.row("FTP", text, problem=ftp_item.get("problem") is True and not stalled, col=col)
        if _num(ftp.get("lastClipAt")):
            c.row("Last clip", _at(ftp["lastClipAt"], now), col=col)
        if stalled:
            n = ftp.get("eventsWithoutClip")
            hours = (h.get("thresholds") or {}).get("ftpStalledHours")
            stall = f"no clip for {hours} h" if _num(hours) else str(ftp_item.get("text", "stalled"))
            if _num(n) and n:
                stall += f", {int(n)} events"
            c.row("Stall check", stall, problem=True, col=col)
        else:
            c.row("Stall check", "ok", col=col)

    poe = cam.get("poeSwitch")
    if isinstance(poe, dict) and poe.get("model"):
        text = str(poe["model"])
        if _num(poe.get("port")):
            text += f" port {int(poe['port'])}"
        c.row("PoE switch", text, col=col)


def _proxy(c: Canvas, view: View, now: datetime) -> None:
    h = view.snap.health
    col = 102
    if h is None:
        c.row("Version", "unreachable", problem=True, bold=True, col=col)
        c.row("Reason", view.snap.error or "no answer", col=col)
        if view.last_ok is not None:
            c.row("Last data", _at(view.last_ok.fetched_at * 1000, now), col=col)
        return
    it = _items(h)
    proxy = h.get("proxy") or {}
    ftp = h.get("ftp") or {}
    c.row("Version", str(h.get("version", "?")), bold=True, col=col)
    if _num(h.get("startedAt")):
        c.row("Up since", _at(h["startedAt"], now), col=col)
    if _num(ftp.get("clipsStored")):
        c.row("Clips stored", str(int(ftp["clipsStored"])), col=col)
    if _num(ftp.get("failures")):
        c.row("FTP failures", str(int(ftp["failures"])), col=col)
    storage = it.get("storage")
    if storage:
        c.row("Storage", str(storage.get("text", "")), problem=storage.get("problem") is True, col=col)
    cache = proxy.get("recordingsCache")
    if isinstance(cache, dict) and _num(cache.get("bytes")) and _num(cache.get("capBytes")):
        files = cache.get("files")
        text = f"{fmt.size(cache['bytes'])} of {fmt.size(cache['capBytes'])}"
        if _num(files):
            text += f", {int(files)} file" + ("" if files == 1 else "s")
        c.row("Rec. cache", text, col=col)
    if _num(proxy.get("sseClients")):
        c.row("Viewers", str(int(proxy["sseClients"])), col=col)
    if _num(proxy.get("lastRetentionRun")):
        c.row("Retention run", _at(proxy["lastRetentionRun"], now), col=col)
    inv = it.get("inventory")
    if inv:
        c.row("Inventory", str(inv.get("text", "")), problem=inv.get("problem") is True, col=col)
        last = proxy.get("lastInventory")
        if isinstance(last, dict) and _num(last.get("startedAt")):
            c.row("Inventory run", _at(last["startedAt"], now), col=col)


def _pi(c: Canvas, view: View, now: datetime) -> None:
    h = view.snap.health
    loc = view.snap.local or {}
    col = 100
    th = _thresholds(view)
    platform = (h or {}).get("platform") or {}
    host = (h or {}).get("host") or {}
    it = _items(h) if h else {}

    model = platform.get("model") or loc.get("model")
    if model:
        c.row(str(model), bold=True)
    if h is None:
        c.row("Proxy", "unreachable", problem=True, col=col)

    disk = (h or {}).get("disk") or loc.get("disk")
    if isinstance(disk, dict) and _num(disk.get("usedPercent")):
        p = float(disk["usedPercent"])
        problem = it["disk"].get("problem") is True if "disk" in it else p >= th["diskPercent"]
        c.row("Disk", fmt.percent(p), problem=problem, col=col + 62, bar=(col, col + 56, p))
        if _num(disk.get("freeBytes")) and _num(disk.get("sizeBytes")):
            c.row("Free", f"{fmt.gb(disk['freeBytes'])} of {fmt.gb(disk['sizeBytes'])}", col=col)

    temp = host.get("cpuTempC") if _num(host.get("cpuTempC")) else loc.get("cpuTempC")
    if _num(temp):
        problem = it["cpuTemp"].get("problem") is True if "cpuTemp" in it else temp >= th["tempC"]
        c.row("CPU temp", f"{float(temp):.1f} °C", problem=problem, col=col)

    mem = host.get("memory")
    if isinstance(mem, dict) and _num(mem.get("usedPercent")) and _num(mem.get("totalBytes")):
        c.row("Memory", f"{fmt.percent(mem['usedPercent'])} of {fmt.gb(mem['totalBytes'])}", col=col)

    up = host.get("uptimeS") if _num(host.get("uptimeS")) else loc.get("uptimeS")
    if _num(up):
        c.row("Uptime", fmt.duration(up), col=col)

    load = host.get("load")
    if isinstance(load, dict) and all(_num(load.get(k)) for k in ("m1", "m5", "m15")):
        c.row("Load", f"{load['m1']:.2f}  {load['m5']:.2f}  {load['m15']:.2f}", col=col)

    uv = it.get("underVoltage")
    if uv:
        c.row("Under-voltage", str(uv.get("text", "")), problem=uv.get("problem") is True, col=col)

    if loc.get("ip"):
        c.row("IP address", str(loc["ip"]), col=col)

    if h is not None and not platform.get("pi") and not host:
        c.row("Proxy host", "not a Raspberry Pi", col=col)


def _stopped(c: Canvas, view: View, now: datetime) -> None:
    c.gap(8)
    c.big("Display stopped", size=17)
    c.big(fmt.stamp(now), size=17)
    c.gap(4)
    c.row("This screen is no longer updated.")
    c.row("The service cam-proxy-pi-display")
    c.row("is not running.")
    snap = view.snap if view.snap.health is not None else view.last_ok
    if snap is not None and snap.health is not None:
        n = snap.health.get("problemCount", 0)
        state = "All OK" if not n else f"{n} problem" + ("" if n == 1 else "s")
        c.footer(f"Last data {_at(snap.fetched_at * 1000, now)}: {state}", bold=False)
    elif view.snap.health is None:
        c.footer("Last data: proxy unreachable", bold=False)


RENDERERS = {"overview": _overview, "camera": _camera, "proxy": _proxy, "pi": _pi, "stopped": _stopped}


def render(page: str, view: View, now: datetime, fonts: Fonts) -> Image.Image:
    return compose(page, view, now, fonts).img


def compose(page: str, view: View, now: datetime, fonts: Fonts) -> Canvas:
    if page not in RENDERERS:
        raise ValueError(f"unknown page {page!r}")
    c = Canvas(fonts)
    if page == "stopped":
        c.header(TITLES[page], fmt.stamp(now))
    else:
        c.header(TITLES[page], _updated(view, now))
    RENDERERS[page](c, view, now)
    return c
