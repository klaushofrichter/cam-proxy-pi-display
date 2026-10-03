from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from cam_proxy_pi_display import fmt

TZ = timezone(timedelta(hours=-5))
NOW = datetime(2026, 10, 3, 10, 25, tzinfo=TZ)


def ms(dt):
    return int(dt.timestamp() * 1000)


def test_stamp_is_the_full_date():
    assert fmt.stamp(ms(datetime(2026, 10, 3, 8, 31, tzinfo=TZ)), TZ) == "Sat Oct 3 08:31"
    assert fmt.stamp(ms(datetime(2026, 9, 28, 18, 2, tzinfo=TZ)), TZ) == "Mon Sep 28 18:02"
    assert fmt.stamp(ms(datetime(2026, 12, 31, 23, 59, tzinfo=TZ)), TZ) == "Thu Dec 31 23:59"


def test_stamp_at_midnight():
    assert fmt.stamp(ms(datetime(2026, 10, 3, 23, 59, 59, tzinfo=TZ)), TZ) == "Sat Oct 3 23:59"
    assert fmt.stamp(ms(datetime(2026, 10, 4, 0, 0, tzinfo=TZ)), TZ) == "Sun Oct 4 00:00"


def test_stamp_of_a_datetime():
    assert fmt.stamp(NOW) == "Sat Oct 3 10:25"


def test_stamp_across_the_dst_change():
    chicago = ZoneInfo("America/Chicago")
    # 2026-11-01 02:00 CDT -> 01:00 CST: 01:30 happens twice, an hour apart.
    first = datetime(2026, 11, 1, 6, 30, tzinfo=UTC)  # 01:30 CDT
    second = datetime(2026, 11, 1, 7, 30, tzinfo=UTC)  # 01:30 CST
    assert fmt.stamp(ms(first), chicago) == "Sun Nov 1 01:30"
    assert fmt.stamp(ms(second), chicago) == "Sun Nov 1 01:30"
    # Before and after, each with its own offset (not the offset of "now").
    assert fmt.stamp(ms(datetime(2026, 10, 31, 23, 2, tzinfo=UTC)), chicago) == "Sat Oct 31 18:02"
    assert fmt.stamp(ms(datetime(2026, 11, 2, 0, 2, tzinfo=UTC)), chicago) == "Sun Nov 1 18:02"


def test_system_tz_has_the_rules_not_just_an_offset():
    tz = fmt.system_tz()
    summer = datetime(2026, 7, 1, 12, tzinfo=UTC).astimezone(tz)
    assert summer.utcoffset() == datetime.fromtimestamp(summer.timestamp()).astimezone().utcoffset()


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


def test_sizes():
    assert fmt.gb(245457289216) == "228.6 GB"
    assert fmt.size(734003200) == "700 MB"
    assert fmt.size(2147483648) == "2.0 GB"
    assert fmt.percent(11.4) == "11.4 %"


def test_offset():
    assert fmt.offset_ms(-412) == "-412 ms"
    assert fmt.offset_ms(3) == "+3 ms"
    assert fmt.offset_ms(-2412) == "-2.4 s"
