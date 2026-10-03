import pytest

from cam_proxy_pi_display.fonts import Fonts


@pytest.fixture(scope="session")
def fonts():
    f = Fonts()
    if f.dir is None:
        pytest.fail("DejaVu fonts not found: install fonts-dejavu-core or set CPPD_FONTS_DIR")
    return f
