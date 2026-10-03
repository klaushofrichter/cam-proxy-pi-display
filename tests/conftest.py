import os
from pathlib import Path

import pytest

from cam_proxy_pi_display.fonts import Fonts

# The golden images are drawn with Debian's DejaVu build (scripts/fetch-test-fonts.sh).
_FONTS = Path(__file__).resolve().parent.parent / ".fonts"
if "CPPD_FONTS_DIR" not in os.environ and (_FONTS / "DejaVuSans.ttf").is_file():
    os.environ["CPPD_FONTS_DIR"] = str(_FONTS)


@pytest.fixture(scope="session")
def fonts():
    f = Fonts()
    if f.dir is None:
        pytest.fail("DejaVu fonts not found: run scripts/fetch-test-fonts.sh (or set CPPD_FONTS_DIR)")
    return f
