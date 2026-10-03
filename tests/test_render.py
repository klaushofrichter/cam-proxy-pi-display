"""Renderer: golden images per page and state, plus what each page says.

Regenerate the goldens after an intended change (and look at them):
    UPDATE_GOLDEN=1 pytest tests/test_render.py
"""

import copy
import os
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from cam_proxy_pi_display.collector import Snapshot
from cam_proxy_pi_display.render import HEIGHT, WIDTH, View, compose, render
from tests.fixtures import load_fixture
from tests.scenarios import FETCHED, GOLDEN, LOCAL, NOW, view

GOLDEN_DIR = Path(__file__).parent / "golden"
# FreeType versions may move a few anti-aliasing-threshold pixels; a changed word moves hundreds.
MAX_DIFF_PIXELS = 40


@pytest.mark.parametrize(("name", "page", "state"), GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden(name, page, state, fonts):
    img = render(page, view(state), NOW, fonts)
    assert img.mode == "1"
    assert img.size == (WIDTH, HEIGHT)
    path = GOLDEN_DIR / f"{name}.png"
    if os.environ.get("UPDATE_GOLDEN") == "1":
        img.save(path)
    assert path.exists(), f"no golden image {path.name}; run with UPDATE_GOLDEN=1"
    want = Image.open(path).convert("1")
    diff = ImageChops.difference(img.convert("L"), want.convert("L"))
    changed = WIDTH * HEIGHT - diff.histogram()[0]
    if changed > MAX_DIFF_PIXELS:
        out = Path(os.environ.get("GOLDEN_FAIL_DIR", "/tmp")) / f"{name}.actual.png"
        img.save(out)
        pytest.fail(f"{name}: {changed} pixels differ from the golden image (actual saved to {out})")


def labels(ls):
    return [label for label, _, _ in ls]


def test_header_has_page_name_and_update_time(fonts):
    ls = compose("camera", view("ok"), NOW, fonts).lines
    assert ls[0] == ("Camera", "updated Sat Oct 3 10:25", False)


def test_header_on_another_day_names_the_day(fonts):
    v = View(Snapshot(load_fixture("pi-ok"), None, FETCHED - 86400, LOCAL))
    assert compose("overview", v, NOW, fonts).lines[0] == ("Overview", "updated Fri Oct 2 10:25", False)


def test_overview_shows_items_as_given_and_the_summary(fonts):
    ls = compose("overview", view("ok"), NOW, fonts).lines
    assert ("Disk", "11.4 % of 228.6 GB", False) in ls
    assert ("Version", "2026.10.03.2", False) in ls
    assert ls[-1] == ("All OK", "", False)


def test_overview_inverts_problems(fonts):
    ls = compose("overview", view("problems"), NOW, fonts).lines
    assert ("Camera", "offline", True) in ls
    assert ("CPU temperature", "78.2 °C", True) in ls
    assert ("Under-voltage", "no", False) in ls
    assert ls[-1] == ("5 problems", "", True)


def test_overview_changing_often(fonts):
    ls = compose("overview", view("changing-often"), NOW, fonts).lines
    assert ls[-1] == ("5 problems · changing often", "", True)


def test_overview_cluster_has_no_pi_lines(fonts):
    ls = compose("overview", view("cluster"), NOW, fonts).lines
    assert "CPU temperature" not in labels(ls)
    assert "Under-voltage" not in labels(ls)
    assert ("Camera FTP upload", "no clip for 6 h", True) in ls
    assert ls[-1] == ("1 problem", "", True)


def test_overview_unreachable_shows_the_pi_from_local_figures(fonts):
    ls = compose("overview", view("unreachable"), NOW, fonts).lines
    assert ls[1] == ("Proxy unreachable", "", True)
    assert ("Reason", "connection refused", False) in ls
    assert ("Last data", "Sat Oct 3 10:21", False) in ls
    assert ("CPU temp", "53.1 °C", False) in ls
    assert ("Uptime", "4 d 18 h", False) in ls
    assert ls[-1] == ("1 problem", "", True)


def test_proxy_page_starts_with_the_full_version(fonts):
    ls = compose("proxy", view("ok"), NOW, fonts).lines
    assert ls[1] == ("Version", "2026.10.03.2", False)
    ls = compose("proxy", view("unreachable"), NOW, fonts).lines
    assert ls[1] == ("Version", "unreachable", True)


def test_proxy_page_details(fonts):
    ls = compose("proxy", view("ok"), NOW, fonts).lines
    assert ("Up since", "Sat Oct 3 08:37", False) in ls
    assert ("Retention run", "Sat Oct 3 09:40", False) in ls
    assert ("Inventory run", "Sat Oct 3 07:20", False) in ls
    assert ("Rec. cache", "700 MB of 2.0 GB, 6 files", False) in ls
    assert ("Viewers", "2", False) in ls
    assert ("Inventory", "clips: ok", False) in ls


def test_camera_page(fonts):
    ls = compose("camera", view("ok"), NOW, fonts).lines
    assert ("Yard", "online", False) in ls
    assert ("Since", "Sat Oct 3 08:37", False) in ls
    assert ("Address", "192.0.2.10, clock -412 ms", False) in ls
    assert ("Stream", "up, frame Sat Oct 3 10:24", False) in ls
    assert ("FTP", "on", False) in ls
    assert ("Last clip", "Sat Oct 3 09:53", False) in ls
    assert ("Firmware", "v3.1.0.4054_2409213180", False) in ls
    assert ("Stall check", "ok", False) in ls
    assert ("PoE switch", "sscpoe-web port 8", False) in ls
    ls = compose("camera", view("problems"), NOW, fonts).lines
    assert ("Yard", "offline (timeout)", True) in ls
    assert ("Since", "Sat Oct 3 10:13", False) in ls
    assert ("Stream", "down, frame Sat Oct 3 10:12", True) in ls
    ls = compose("camera", view("cluster"), NOW, fonts).lines
    assert ("Stall check", "no clip for 6 h, 4 events", True) in ls
    assert ("Last clip", "Sat Oct 3 03:26", False) in ls
    assert "PoE switch" not in labels(ls)


def test_null_figures_are_left_off(fonts):
    h = load_fixture("pi-ok")
    h["camera"].update(model=None, firmware=None, clockOffsetMs=None, poeSwitch=None)
    h["host"].update(memory=None, load=None, cpuTempC=None)
    h["startedAt"] = None
    v = View(Snapshot(h, None, FETCHED, {}))
    cam = labels(compose("camera", v, NOW, fonts).lines)
    assert not {"Model", "Firmware", "PoE switch"} & set(cam)
    assert ("Address", "192.0.2.10", False) in compose("camera", v, NOW, fonts).lines
    pi = labels(compose("pi", v, NOW, fonts).lines)
    assert not {"Memory", "Load", "CPU temp", "IP address"} & set(pi)
    assert "Up since" not in labels(compose("proxy", v, NOW, fonts).lines)


def test_pi_page_prefers_the_api_and_falls_back_to_local(fonts):
    ls = compose("pi", view("ok"), NOW, fonts).lines
    assert ("CPU temp", "53.6 °C", False) in ls  # the API's, not the local 53.1
    assert ("IP address", "192.0.2.20", False) in ls
    ls = compose("pi", view("unreachable"), NOW, fonts).lines
    assert ("Proxy", "unreachable", True) in ls
    assert ("CPU temp", "53.1 °C", False) in ls


def test_local_fallback_uses_the_last_known_thresholds(fonts):
    hot = dict(LOCAL, cpuTempC=71.0)
    last = copy.deepcopy(load_fixture("pi-ok"))
    last["thresholds"]["tempC"] = 70
    v = View(Snapshot(None, "timeout", FETCHED, hot), last_ok=Snapshot(last, None, FETCHED - 60, LOCAL))
    assert ("CPU temp", "71.0 °C", True) in compose("pi", v, NOW, fonts).lines
    v = View(Snapshot(None, "timeout", FETCHED, hot))
    assert ("CPU temp", "71.0 °C", False) in compose("pi", v, NOW, fonts).lines  # default 75


def test_stopped_page(fonts):
    ls = compose("stopped", view("ok"), NOW, fonts).lines
    assert ls[0] == ("Display stopped", "Sat Oct 3 10:25", False)
    assert ("Display stopped", "", False) in ls
    assert ("Sat Oct 3 10:25", "", False) in ls
    assert ls[-1] == ("Last data Sat Oct 3 10:25: All OK", "", False)


def test_long_texts_are_cut_not_overflowing(fonts):
    h = load_fixture("pi-ok")
    h["items"][0]["text"] = "a very long camera state text that cannot fit on the line"
    img = render("overview", View(Snapshot(h, None, FETCHED, {})), NOW, fonts)
    assert img.size == (WIDTH, HEIGHT)


def test_unknown_page(fonts):
    with pytest.raises(ValueError):
        render("nope", view("ok"), NOW, fonts)


def test_without_dejavu_the_default_font_still_renders(monkeypatch, tmp_path):
    from cam_proxy_pi_display import fonts as fonts_mod

    monkeypatch.setattr(fonts_mod, "SEARCH", ())
    monkeypatch.delenv("CPPD_FONTS_DIR", raising=False)
    f = fonts_mod.Fonts(str(tmp_path))
    assert f.dir is None
    img = render("overview", view("ok"), NOW, f)
    assert img.size == (WIDTH, HEIGHT)


def test_problems_come_from_the_flags_not_from_local_rules(fonts):
    # cam-proxy decides what is a problem (e.g. FTP "not set up" while the proxy takes clips).
    h = load_fixture("pi-ok")
    ftp = next(i for i in h["items"] if i["id"] == "ftp")
    ftp.update(value="not_set_up", text="not set up", problem=True)
    h["ftp"]["cameraUpload"] = "not_set_up"
    h.update(ok=False, problemCount=1)
    v = View(Snapshot(h, None, FETCHED, LOCAL))
    assert ("Camera FTP upload", "not set up", True) in compose("overview", v, NOW, fonts).lines
    assert ("FTP", "not set up", True) in compose("camera", v, NOW, fonts).lines
    ftp.update(problem=False)
    assert ("FTP", "not set up", False) in compose("camera", v, NOW, fonts).lines


def test_last_data_from_yesterday_carries_its_date(fonts):
    ls = compose("overview", view("unreachable-yesterday"), NOW, fonts).lines
    assert ("Last data", "Fri Oct 2 18:02", False) in ls
    assert ls[0] == ("Overview", "updated Sat Oct 3 10:25", False)


@pytest.mark.parametrize("title", ["Overview", "Camera", "Proxy", "Pi"])
def test_header_fits_with_the_widest_date(title, fonts):
    from cam_proxy_pi_display.render import Canvas

    c = Canvas(fonts)
    widest = max(
        (
            f"updated {d} {m} 28 23:59"
            for d in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
            for m in ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        ),
        key=lambda t: c.width(t, fonts.get("regular", 11)),
    )
    c.header(title, widest)
    assert c.header_title_drawn == title


def test_stopped_header_fits(fonts):
    from cam_proxy_pi_display.render import Canvas

    c = Canvas(fonts)
    c.header("Display stopped", "Wed May 28 23:59")
    assert c.header_title_drawn == "Display stopped"
