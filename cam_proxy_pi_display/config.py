"""Settings from /etc/cam-proxy-pi-display.toml (all optional)."""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_PATH = Path("/etc/cam-proxy-pi-display.toml")


@dataclass(frozen=True)
class ApiConfig:
    url: str = "http://127.0.0.1:8480/api/local/health"
    timeout_s: float = 5.0
    poll_interval_s: float = 60.0


@dataclass(frozen=True)
class KeysConfig:
    # BCM GPIO numbers, top to bottom in landscape. The bottom key is Update.
    pins: tuple[int, int, int, int] = (5, 6, 13, 19)
    long_press_s: float = 2.0
    bounce_s: float = 0.05


@dataclass(frozen=True)
class RefreshConfig:
    timer_min: float = 15.0
    return_to_overview_min: float = 10.0
    problem_confirm_polls: int = 2
    problem_min_interval_min: float = 5.0
    problem_max_per_hour: int = 6
    daily_clear: str = "03:30"


@dataclass(frozen=True)
class DisplayConfig:
    # Empty: look in the usual places for fonts-dejavu-core.
    fonts_dir: str = ""


@dataclass(frozen=True)
class Config:
    api: ApiConfig = field(default_factory=ApiConfig)
    keys: KeysConfig = field(default_factory=KeysConfig)
    refresh: RefreshConfig = field(default_factory=RefreshConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)


class ConfigError(ValueError):
    pass


def _section(cls, raw: dict, name: str):
    if not isinstance(raw, dict):
        raise ConfigError(f"[{name}] must be a table")
    known = {f.name: f for f in fields(cls)}
    kwargs = {}
    for key, value in raw.items():
        if key not in known:
            log.warning("config: unknown setting %s.%s ignored", name, key)
            continue
        default = getattr(cls(), key)
        kwargs[key] = _coerce(value, default, f"{name}.{key}")
    return cls(**kwargs)


def _coerce(value, default, name: str):
    if isinstance(default, bool):
        if not isinstance(value, bool):
            raise ConfigError(f"{name} must be true or false")
        return value
    if isinstance(default, int) and not isinstance(default, bool):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{name} must be an integer")
        return value
    if isinstance(default, float):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ConfigError(f"{name} must be a positive number")
        return float(value)
    if isinstance(default, str):
        if not isinstance(value, str):
            raise ConfigError(f"{name} must be a string")
        return value
    if isinstance(default, tuple):
        if not isinstance(value, list) or len(value) != len(default):
            raise ConfigError(f"{name} must be a list of {len(default)} entries")
        if not all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 27 for v in value):
            raise ConfigError(f"{name} must be BCM GPIO numbers (0-27)")
        if len(set(value)) != len(value):
            raise ConfigError(f"{name} must not repeat a pin")
        return tuple(value)
    raise ConfigError(f"{name}: unsupported type")  # pragma: no cover


def parse_hhmm(text: str) -> tuple[int, int]:
    try:
        hh, mm = text.split(":")
        h, m = int(hh), int(mm)
    except ValueError as e:
        raise ConfigError(f"time {text!r} must be HH:MM") from e
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ConfigError(f"time {text!r} must be HH:MM")
    return h, m


def from_dict(raw: dict) -> Config:
    sections = {"api": ApiConfig, "keys": KeysConfig, "refresh": RefreshConfig, "display": DisplayConfig}
    kwargs = {}
    for name, value in raw.items():
        if name not in sections:
            log.warning("config: unknown section [%s] ignored", name)
            continue
        kwargs[name] = _section(sections[name], value, name)
    cfg = Config(**kwargs)
    parse_hhmm(cfg.refresh.daily_clear)
    if not cfg.api.url.startswith(("http://", "https://")):
        raise ConfigError("api.url must be an http(s) URL")
    if cfg.refresh.problem_confirm_polls < 1 or cfg.refresh.problem_max_per_hour < 1:
        raise ConfigError("refresh.problem_confirm_polls and problem_max_per_hour must be at least 1")
    return cfg


def load(path: Path | None = None) -> Config:
    """Read the config file; a missing file means all defaults."""
    p = path or DEFAULT_PATH
    try:
        with open(p, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        if path is not None:
            raise ConfigError(f"config file {p} not found") from None
        log.info("config: %s not found, using the defaults", p)
        return Config()
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{p}: {e}") from e
    return from_dict(raw)
