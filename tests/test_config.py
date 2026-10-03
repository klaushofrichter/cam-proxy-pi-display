import pytest

from cam_proxy_pi_display import config
from cam_proxy_pi_display.config import Config, ConfigError, from_dict, load, parse_hhmm


def test_defaults_match_the_design():
    c = Config()
    assert c.api.url == "http://127.0.0.1:8480/api/local/health"
    assert c.api.timeout_s == 5
    assert c.api.poll_interval_s == 60
    assert c.keys.pins == (5, 6, 13, 19)
    assert c.keys.long_press_s == 2
    assert c.refresh.timer_min == 15
    assert c.refresh.return_to_overview_min == 10
    assert c.refresh.problem_confirm_polls == 2
    assert c.refresh.problem_min_interval_min == 5
    assert c.refresh.problem_max_per_hour == 6
    assert c.refresh.daily_clear == "03:30"


def test_missing_default_file_gives_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DEFAULT_PATH", tmp_path / "nope.toml")
    assert load() == Config()


def test_missing_explicit_file_is_an_error(tmp_path):
    with pytest.raises(ConfigError):
        load(tmp_path / "nope.toml")


def test_reads_a_file(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text(
        '[api]\nurl = "http://localhost:9999/x"\ntimeout_s = 3\n'
        "[keys]\npins = [26, 20, 21, 16]\nlong_press_s = 1.5\n"
        '[refresh]\ntimer_min = 30\ndaily_clear = "04:05"\n'
    )
    c = load(p)
    assert c.api.url == "http://localhost:9999/x"
    assert c.api.timeout_s == 3.0
    assert c.keys.pins == (26, 20, 21, 16)
    assert c.keys.long_press_s == 1.5
    assert c.refresh.timer_min == 30
    assert c.refresh.daily_clear == "04:05"


def test_unknown_keys_are_ignored(caplog):
    c = from_dict({"api": {"nope": 1}, "other": {}})
    assert c == Config()
    assert "unknown" in caplog.text


@pytest.mark.parametrize(
    "raw",
    [
        {"keys": {"pins": [5, 6, 13]}},
        {"keys": {"pins": [5, 6, 13, 13]}},
        {"keys": {"pins": [5, 6, 13, 99]}},
        {"api": {"timeout_s": 0}},
        {"api": {"timeout_s": "5"}},
        {"api": {"url": "ftp://x"}},
        {"refresh": {"daily_clear": "25:00"}},
        {"refresh": {"problem_max_per_hour": 0}},
        {"refresh": {"problem_confirm_polls": 1.5}},
        {"api": "x"},
    ],
)
def test_bad_values_are_rejected(raw):
    with pytest.raises(ConfigError):
        from_dict(raw)


def test_bad_toml(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text("[api\n")
    with pytest.raises(ConfigError):
        load(p)


def test_parse_hhmm():
    assert parse_hhmm("03:30") == (3, 30)
    with pytest.raises(ConfigError):
        parse_hhmm("3.30")
