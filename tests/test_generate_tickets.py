import os
import sys

from PIL import Image, ImageDraw, ImageFont

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


def test_build_fonts_returns_all_font_size_keys():
    config = gt.default_config()
    fonts = gt.build_fonts(config)
    assert set(fonts.keys()) == set(gt.FONT_SIZES.keys())


def test_draw_ticket_draws_border_and_content():
    config = gt.default_config()
    fonts = gt.build_fonts(config)
    img = Image.new("RGB", (gt.TICKET_W, gt.TICKET_H), "white")
    draw = ImageDraw.Draw(img)

    gt.draw_ticket(draw, 0, 0, gt.TICKET_W, gt.TICKET_H, 42, config, fonts)

    # Border line should be drawn near the top-left corner
    assert img.getpixel((5, 1)) != (255, 255, 255)

    # More than just background white should be present (text/border drawn)
    colors = img.getcolors(maxcolors=2_000_000)
    assert len(colors) > 1
