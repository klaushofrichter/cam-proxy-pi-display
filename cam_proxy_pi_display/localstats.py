"""The Pi's own figures, read directly (no shell-outs), for when the proxy can't answer.

Every figure is None when it can't be read (e.g. on a Mac): None is left off the page.
"""

from __future__ import annotations

import fcntl
import os
import socket
import struct
from pathlib import Path

SIOCGIFADDR = 0x8915


def read(proc: Path = Path("/proc"), sys: Path = Path("/sys"), disk_path: str = "/") -> dict:
    return {
        "disk": disk(disk_path),
        "cpuTempC": cpu_temp(sys),
        "uptimeS": uptime(proc),
        "model": model(proc),
        "ip": ip_address(proc),
    }


def disk(path: str = "/") -> dict | None:
    """Like the API's `disk`: used percent as df's Use%."""
    try:
        st = os.statvfs(path)
    except OSError:
        return None
    size = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    if used + free <= 0:
        return None
    return {
        "sizeBytes": size,
        "freeBytes": free,
        "usedBytes": used,
        "usedPercent": round(used * 100 / (used + free), 1),
    }


def cpu_temp(sys: Path = Path("/sys")) -> float | None:
    """hwmon `cpu_thermal` temp1_input in °C, one decimal."""
    base = sys / "class" / "hwmon"
    try:
        entries = sorted(base.iterdir())
    except OSError:
        return None
    for d in entries:
        try:
            if (d / "name").read_text().strip() != "cpu_thermal":
                continue
            return round(int((d / "temp1_input").read_text().strip()) / 1000, 1)
        except (OSError, ValueError):
            continue
    return None


def uptime(proc: Path = Path("/proc")) -> int | None:
    try:
        return int(float((proc / "uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return None


def model(proc: Path = Path("/proc")) -> str | None:
    try:
        for line in (proc / "cpuinfo").read_text().splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "Model" and value.strip():
                return value.strip()
    except OSError:
        pass
    return None


def default_interface(proc: Path = Path("/proc")) -> str | None:
    """The interface of the default route, from /proc/net/route."""
    try:
        lines = (proc / "net" / "route").read_text().splitlines()[1:]
    except OSError:
        return None
    best = None
    for line in lines:
        f = line.split()
        if len(f) < 7 or f[1] != "00000000":
            continue
        try:
            metric = int(f[6])
        except ValueError:
            continue
        if best is None or metric < best[1]:
            best = (f[0], metric)
    return best[0] if best else None


def ip_address(proc: Path = Path("/proc")) -> str | None:
    """The IPv4 address of the default route's interface (ioctl, no packets sent)."""
    iface = default_interface(proc)
    if not iface:
        return None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            packed = fcntl.ioctl(s.fileno(), SIOCGIFADDR, struct.pack("256s", iface[:15].encode()))
        return socket.inet_ntoa(packed[20:24])
    except OSError:
        return None
