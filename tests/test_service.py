import copy
import threading

from cam_proxy_pi_display.config import Config
from cam_proxy_pi_display.panel import FakePanel
from cam_proxy_pi_display.service import Service
from tests.fixtures import load_fixture
from tests.scenarios import FETCHED, LOCAL, TZ

MIN = 60.0


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class Api:
    def __init__(self):
        self.health = load_fixture("pi-ok")
        self.error = None
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.error:
            return None, self.error
        return copy.deepcopy(self.health), None

    def problem(self, on: bool):
        cam = self.health["items"][0]
        cam.update(value=not on, text="offline" if on else "online", problem=on)
        self.health["problemCount"] = 1 if on else 0


def make(tmp_path, fonts, t0=FETCHED):
    clock = Clock(t0)
    api = Api()
    panel = FakePanel(tmp_path / "out", clock=clock)
    svc = Service(Config(), panel, fonts, fetch=api, local=lambda: dict(LOCAL), clock=clock, tz=TZ)
    return svc, api, panel, clock


def tick(svc, clock, minutes, step=MIN):
    end = clock.t + minutes * 60
    while clock.t < end:
        svc.step()
        clock.t += step


def test_start_polls_then_draws_the_overview(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)
    svc.step()
    assert api.calls == 1
    assert panel.count == 1
    assert (tmp_path / "out" / "latest.png").exists()
    assert svc.policy.page == "overview"


def test_polls_every_minute_without_drawing(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)
    tick(svc, clock, 10)
    assert api.calls == 10
    assert panel.count == 1


def test_timer_redraws_every_15_minutes(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)
    tick(svc, clock, 31)
    assert panel.count == 3  # start, 15, 30


def test_a_problem_redraws_after_two_polls(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)
    tick(svc, clock, 3)
    api.problem(True)
    tick(svc, clock, 1)
    assert panel.count == 1
    tick(svc, clock, 1)
    assert panel.count == 2
    assert "overview-problem" in sorted(p.name for p in (tmp_path / "out").iterdir())[-2]


def test_unreachable_after_two_polls_and_back(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)
    tick(svc, clock, 2)
    api.error = "connection refused"
    tick(svc, clock, 2)
    assert panel.count == 2
    assert svc.snap.health is None and svc.last_ok is not None
    api.error = None
    tick(svc, clock, 6)
    assert panel.count == 3


def test_key_draws_at_once_with_fresh_data(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)
    svc.step()
    clock.t += 5
    calls = api.calls
    svc.press("camera")
    svc.step()
    assert api.calls == calls + 1
    assert panel.count == 2
    assert svc.policy.page == "camera"


def test_update_redraws_the_page_shown(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)
    svc.step()
    svc.press("pi")
    svc.step()
    svc.press("update")
    svc.step()
    assert svc.policy.page == "pi"
    assert panel.count == 3


def test_queued_presses_last_one_wins(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)
    svc.step()
    for a in ("camera", "proxy", "pi"):
        svc.press(a)
    svc.step()
    assert panel.count == 2
    assert svc.policy.page == "pi"


def test_back_to_overview_10_minutes_after_a_key(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)
    svc.step()
    clock.t += MIN
    svc.press("proxy")
    svc.step()
    tick(svc, clock, 11)
    assert svc.policy.page == "overview"
    assert panel.count == 3


def test_daily_clear_at_03_30(tmp_path, fonts):
    # FETCHED is 10:25 local; start at 03:00 the next day
    t0 = FETCHED + (16 * 60 + 35) * 60
    svc, api, panel, clock = make(tmp_path, fonts, t0=t0)
    tick(svc, clock, 40)
    assert panel.clears == 1
    assert any("-clear" in p.name for p in (tmp_path / "out").iterdir())


def test_long_press_overview(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)
    svc.step()
    svc.press("camera")
    svc.step()
    svc.press("overview")
    svc.step()
    assert svc.policy.page == "overview"
    assert svc.policy.key_at is None


def test_panel_failure_does_not_stop_the_service(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)

    def boom(*a, **k):
        raise OSError("spi gone")

    panel.show = boom
    svc.step()
    clock.t += 1
    svc.step()  # no retry storm: the failed draw counts, the timer tries again
    assert svc.policy.last_draw_at is not None


def test_run_and_stop_draws_the_stopped_page(tmp_path, fonts):
    svc, api, panel, clock = make(tmp_path, fonts)
    t = threading.Thread(target=svc.run)
    t.start()
    svc.request_stop()
    t.join(5)
    assert not t.is_alive()
    assert panel.count >= 1
    assert sorted((tmp_path / "out").glob("*-stopped.png"))
