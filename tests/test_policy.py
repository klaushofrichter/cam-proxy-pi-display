from datetime import datetime, timedelta, timezone

from cam_proxy_pi_display.config import RefreshConfig
from cam_proxy_pi_display.policy import Draw, RefreshPolicy

MIN = 60.0
OK = frozenset()
CAM = frozenset({"camera"})
CAM_DISK = frozenset({"camera", "disk"})
TZ = timezone(timedelta(hours=-5))


def started(t=0.0, cfg=None):
    p = RefreshPolicy(cfg or RefreshConfig(), now=t)
    assert p.due(t) == Draw("overview", "start")
    p.observe(OK, t)
    p.drawn("overview", OK, t, "start")
    return p


def run(p, t0, t1, problems, step=MIN):
    """Poll once a minute from t0 to t1 (exclusive) and draw what is due; returns the draws."""
    draws = []
    t = t0
    while t < t1:
        p.observe(problems(t) if callable(problems) else problems, t)
        d = p.due(t)
        if d:
            draws.append((t, d))
            p.drawn(d.page, p.latest, t, d.reason)
        t += step
    return draws


def test_first_draw_is_the_overview():
    p = RefreshPolicy(RefreshConfig(), now=0)
    assert p.due(0) == Draw("overview", "start")


def test_nothing_due_right_after_a_draw():
    p = started()
    assert p.due(1) is None


def test_timer_every_15_minutes_on_the_page_shown():
    p = started()
    draws = run(p, MIN, 31 * MIN, OK)
    assert [(t, d.reason) for t, d in draws] == [(15 * MIN, "timer"), (30 * MIN, "timer")]
    assert all(d.page == "overview" for _, d in draws)


def test_a_one_minute_blip_draws_nothing():
    p = started()
    draws = run(p, MIN, 14 * MIN, lambda t: CAM if t == 3 * MIN else OK)
    assert draws == []


def test_a_problem_needs_two_polls_in_a_row():
    p = started()
    draws = run(p, MIN, 10 * MIN, lambda t: CAM if t >= 3 * MIN else OK)
    assert [(t, d) for t, d in draws] == [(4 * MIN, Draw("overview", "problem"))]


def test_a_cleared_problem_is_drawn_too():
    p = started()
    draws = run(p, MIN, 14 * MIN, lambda t: CAM if 3 * MIN <= t < 9 * MIN else OK)
    assert [t for t, _ in draws] == [4 * MIN, 10 * MIN]


def test_changes_inside_5_minutes_wait_and_coalesce():
    p = started()

    def problems(t):
        if t < 3 * MIN:
            return OK
        if t < 5 * MIN:
            return CAM
        return CAM_DISK  # the second change, confirmed at 6 min, inside the 5 minutes

    draws = run(p, MIN, 14 * MIN, problems)
    # 4 min: CAM drawn; CAM_DISK confirmed at 6 min, waits until 9 min (4 + 5)
    assert [t for t, _ in draws] == [4 * MIN, 9 * MIN]


def test_change_and_change_back_inside_the_wait_draws_nothing():
    p = started()

    def problems(t):
        if 3 * MIN <= t < 5 * MIN:
            return CAM
        if 5 * MIN <= t < 7 * MIN:
            return OK
        if 7 * MIN <= t < 9 * MIN:
            return CAM
        return OK

    draws = run(p, MIN, 14 * MIN, problems)
    # CAM at 4; OK confirmed at 6 waits; CAM again at 8 == shown; OK again at 10 -> drawn at 10 (>= 9)
    assert [t for t, _ in draws] == [4 * MIN, 10 * MIN]


def test_hourly_cap_then_changing_often_and_the_timer():
    p = started()
    # flapping: 2 minutes CAM, 3 minutes OK, ... a confirmed change every 2-3 minutes
    pattern = [CAM, CAM, OK, OK, OK]

    def problems(t):
        return pattern[int(t // MIN) % 5]

    draws = run(p, MIN, 60 * MIN, problems)
    problem_draws = [t for t, d in draws if d.reason == "problem"]
    assert len(problem_draws) == 6
    assert all(b - a >= 5 * MIN for a, b in zip(problem_draws, problem_draws[1:], strict=False))
    t_cap = problem_draws[-1]
    assert p.changing_often(t_cap + MIN)
    later = [d for t, d in draws if t > t_cap]
    assert later and all(d.reason == "timer" for d in later)


def test_changing_often_ends_when_the_hour_has_room():
    p = started()
    for i in range(6):
        p.drawn("overview", CAM if i % 2 == 0 else OK, i * 5 * MIN, "problem")
    assert p.changing_often(30 * MIN)
    assert not p.changing_often(61 * MIN)


def test_key_draws_at_once_and_returns_to_overview_after_10_minutes():
    p = started()
    p.observe(OK, 2 * MIN)
    p.drawn("camera", OK, 2 * MIN, "key")
    assert p.page == "camera"
    draws = run(p, 3 * MIN, 13 * MIN, OK)
    assert draws == [(12 * MIN, Draw("overview", "return"))]
    assert p.page == "overview"


def test_timer_on_a_key_page_keeps_the_page():
    cfg = RefreshConfig(timer_min=5, return_to_overview_min=10)
    p = started(cfg=cfg)
    p.drawn("pi", OK, 0, "key")
    draws = run(p, MIN, 11 * MIN, OK)
    assert [(t, d) for t, d in draws] == [(5 * MIN, Draw("pi", "timer")), (10 * MIN, Draw("overview", "return"))]


def test_a_problem_on_a_key_page_shows_the_overview():
    p = started()
    p.drawn("proxy", OK, 0, "key")
    draws = run(p, MIN, 5 * MIN, lambda t: CAM if t >= 2 * MIN else OK)
    assert draws == [(3 * MIN, Draw("overview", "problem"))]


def test_unreachable_counts_as_a_problem_change():
    p = started()
    down = frozenset({"proxy-unreachable"})
    draws = run(p, MIN, 5 * MIN, lambda t: down if t >= 2 * MIN else OK)
    assert draws == [(3 * MIN, Draw("overview", "problem"))]


def test_daily_clear_once_at_03_30():
    start = datetime(2026, 10, 3, 10, 0, tzinfo=TZ)
    p = RefreshPolicy(RefreshConfig(), now=0, local_now=start)
    assert not p.clear_due(start)
    assert not p.clear_due(datetime(2026, 10, 4, 3, 29, tzinfo=TZ))
    assert p.clear_due(datetime(2026, 10, 4, 3, 30, tzinfo=TZ))
    p.cleared(datetime(2026, 10, 4, 3, 30, tzinfo=TZ))
    assert not p.clear_due(datetime(2026, 10, 4, 3, 31, tzinfo=TZ))
    assert not p.clear_due(datetime(2026, 10, 4, 23, 0, tzinfo=TZ))
    assert p.clear_due(datetime(2026, 10, 5, 4, 0, tzinfo=TZ))


def test_daily_clear_today_when_started_before_03_30():
    start = datetime(2026, 10, 3, 1, 0, tzinfo=TZ)
    p = RefreshPolicy(RefreshConfig(), now=0, local_now=start)
    assert p.clear_due(datetime(2026, 10, 3, 3, 30, tzinfo=TZ))
