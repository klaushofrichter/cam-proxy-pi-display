from datetime import datetime, timedelta, timezone

import pytest

from cam_proxy_pi_display import fmt

TZ = timezone(timedelta(hours=-5))
NOW = datetime(2026, 10, 3, 10, 25, tzinfo=TZ)


def ms(dt):
    return int(dt.timestamp() * 1000)


def test_clock_today_and_other_days():
    assert fmt.clock(ms(datetime(2026, 10, 3, 8, 31, tzinfo=TZ)), NOW) == "08:31"
    assert fmt.clock(ms(datetime(2026, 10, 2, 23, 5, tzinfo=TZ)), NOW) == "2 Oct 23:05"


@pytest.mark.parametrize(
    ("s", "text"),
    [
        (-3, "0 s"),
        (45, "45 s"),
        (720, "12 min"),
        (7500, "2 h 5 min"),
        (7200, "2 h"),
        (412233, "4 d 18 h"),
        (86400, "1 d"),
    ],
)
def test_duration(s, text):
    assert fmt.duration(s) == text


def test_ago():
    assert fmt.ago(ms(NOW) - 31 * 60_000, NOW) == "31 min ago"


def test_sizes():
    assert fmt.gb(245457289216) == "228.6 GB"
    assert fmt.size(734003200) == "700 MB"
    assert fmt.size(2147483648) == "2.0 GB"
    assert fmt.percent(11.4) == "11.4 %"


def test_offset():
    assert fmt.offset_ms(-412) == "-412 ms"
    assert fmt.offset_ms(3) == "+3 ms"
    assert fmt.offset_ms(-2412) == "-2.4 s"
