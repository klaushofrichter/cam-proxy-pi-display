import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

from cam_proxy_pi_display.__main__ import main

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"


def unreachable_config(tmp_path) -> Path:
    p = tmp_path / "c.toml"
    p.write_text('[api]\nurl = "http://127.0.0.1:9/api/local/health"\ntimeout_s = 1\n')
    return p


def test_once_from_a_file_writes_a_png(tmp_path, fonts):
    out = tmp_path / "out"
    rc = main(
        [
            "--config",
            str(unreachable_config(tmp_path)),
            "--fake-panel",
            str(out),
            "--once",
            "proxy",
            "--health-file",
            str(FIXTURES / "pi-ok.json"),
        ]
    )
    assert rc == 0
    pngs = sorted(out.glob("0001-*-proxy.png"))
    assert len(pngs) == 1
    img = Image.open(pngs[0])
    assert img.size == (264, 176)


def test_once_unreachable(tmp_path, fonts):
    out = tmp_path / "out"
    rc = main(["--config", str(unreachable_config(tmp_path)), "--fake-panel", str(out), "--once", "overview"])
    assert rc == 0
    assert (out / "latest.png").exists()


def test_bad_config_exits_2(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text("[keys]\npins = [1]\n")
    assert main(["--config", str(p), "--fake-panel", str(tmp_path), "--once", "pi"]) == 2


def test_service_stops_on_sigterm_with_the_stopped_page(tmp_path, fonts):
    out = tmp_path / "out"
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "cam_proxy_pi_display",
            "--config",
            str(unreachable_config(tmp_path)),
            "--fake-panel",
            str(out),
            "--no-keys",
        ],
        env=env,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not list(out.glob("0001-*.png")):
            time.sleep(0.1)
        assert list(out.glob("0001-*-overview-start.png")), "no start page"
        proc.send_signal(signal.SIGTERM)
        _, err = proc.communicate(timeout=15)
    finally:
        proc.kill()
    assert proc.returncode == 0, err
    assert list(out.glob("*-stopped.png"))
    assert "proxy unreachable" in err
