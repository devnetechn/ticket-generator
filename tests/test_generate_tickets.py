import os
import sys

from PIL import ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generate_tickets as gt


def test_default_config_has_all_required_keys():
    config = gt.default_config()
    required_keys = {
        "EVENT_NAME", "EVENT_DATE", "PRIZES", "START_NUMBER",
        "TOTAL_TICKETS", "OUTPUT_DIR", "FONT_PATH", "ACCENT_COLOR",
    }
    assert required_keys.issubset(config.keys())


def test_load_font_returns_truetype_font_when_path_exists():
    font = gt.load_font("C:/Windows/Fonts/arial.ttf", 20)
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_load_font_falls_back_to_default_when_path_missing():
    font = gt.load_font("C:/does/not/exist.ttf", 20)
    assert font is not None
