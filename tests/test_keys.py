import time

import pytest

from cam_proxy_pi_display.config import KeysConfig
from cam_proxy_pi_display.keys import KeyLogic, Keys


def logic():
    out = []
    return KeyLogic(out.append), out


@pytest.mark.parametrize(("index", "page"), [(0, "camera"), (1, "proxy"), (2, "pi")])
def test_page_keys_act_on_press(index, page):
    k, out = logic()
    k.pressed(index)
    assert out == [page]
    k.released(index)
    assert out == [page]


def test_bottom_short_press_is_update():
    k, out = logic()
    k.pressed(3)
    assert out == []
    k.released(3)
    assert out == ["update"]


def test_bottom_long_press_is_overview_once():
    k, out = logic()
    k.pressed(3)
    k.held(3)
    k.released(3)
    assert out == ["overview"]
    k.pressed(3)
    k.released(3)
    assert out == ["overview", "update"]


def test_held_on_a_page_key_does_nothing_extra():
    k, out = logic()
    k.pressed(1)
    k.held(1)
    k.released(1)
    assert out == ["proxy"]


@pytest.fixture
def mock_factory():
    gpiozero = pytest.importorskip("gpiozero")
    from gpiozero.pins.mock import MockFactory

    f = MockFactory()
    yield f
    f.reset()
    gpiozero.Device.pin_factory = None


def _wait(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_gpiozero_buttons_on_configured_pins(mock_factory):
    out = []
    cfg = KeysConfig(pins=(5, 6, 13, 19), long_press_s=0.3, bounce_s=0.001)
    keys = Keys(cfg, out.append, pin_factory=mock_factory)
    try:
        # active low: pressing pulls the pin down
        for pin, page in ((5, "camera"), (6, "proxy"), (13, "pi")):
            p = mock_factory.pin(pin)
            p.drive_low()
            assert _wait(lambda page=page: out and out[-1] == page)
            p.drive_high()
        bottom = mock_factory.pin(19)
        bottom.drive_low()
        time.sleep(0.05)
        bottom.drive_high()
        assert _wait(lambda: out[-1] == "update")
        bottom.drive_low()
        assert _wait(lambda: out[-1] == "overview")
        bottom.drive_high()
        time.sleep(0.1)
        assert out == ["camera", "proxy", "pi", "update", "overview"]
    finally:
        keys.close()


def test_other_pins_are_configurable(mock_factory):
    out = []
    keys = Keys(KeysConfig(pins=(26, 20, 21, 16), bounce_s=0.001), out.append, pin_factory=mock_factory)
    try:
        mock_factory.pin(21).drive_low()
        assert _wait(lambda: out == ["pi"])
    finally:
        keys.close()
