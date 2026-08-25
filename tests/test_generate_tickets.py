import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generate_tickets as gt


def test_default_config_has_all_required_keys():
    config = gt.default_config()
    required_keys = {
        "ORG_NAME", "EVENT_NAME", "EVENT_DATE", "SUBTITLE_LINES", "PRIZES",
        "CONSOLATION_TEXT", "PRICE", "PROCEEDS_TEXT", "LOGO_PATH", "SEAL_TEXT",
        "START_NUMBER", "TOTAL_TICKETS", "OUTPUT_DIR", "FONT_PATH",
        "BOLD_FONT_PATH", "ITALIC_FONT_PATH", "TITLE_FONT_PATH",
        "STUB_FONT_PATH", "STUB_BOLD_FONT_PATH", "ACCENT_COLOR", "PRICE_BG_COLOR",
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

    gt.draw_ticket(img, draw, 0, 0, gt.TICKET_W, gt.TICKET_H, 42, config, fonts)

    # Border line should be drawn near the top-left corner
    assert img.getpixel((5, 1)) != (255, 255, 255)

    # More than just background white should be present (text/border drawn)
    colors = img.getcolors(maxcolors=2_000_000)
    assert len(colors) > 1


def test_create_ticket_image_has_expected_size():
    config = gt.default_config()
    fonts = gt.build_fonts(config)
    img = gt.create_ticket_image(7, config, fonts)
    assert img.size == (gt.TICKET_W, gt.TICKET_H)


def test_create_page_has_expected_page_size():
    config = gt.default_config()
    fonts = gt.build_fonts(config)
    page = gt.create_page([1, 2, 3], config, fonts)
    assert page.size == (gt.PAGE_W, gt.PAGE_H)


def test_create_page_handles_partial_last_page():
    config = gt.default_config()
    fonts = gt.build_fonts(config)
    page = gt.create_page([1], config, fonts)
    assert page.size == (gt.PAGE_W, gt.PAGE_H)


def test_chunk_numbers_splits_into_groups_of_ten():
    chunks = gt.chunk_numbers(1, 25)
    assert len(chunks) == 3
    assert chunks[0] == list(range(1, 11))
    assert chunks[1] == list(range(11, 21))
    assert chunks[2] == list(range(21, 26))


def test_generate_all_creates_expected_files(tmp_path):
    config = gt.default_config()
    config["OUTPUT_DIR"] = str(tmp_path)
    config["START_NUMBER"] = 1
    config["TOTAL_TICKETS"] = 3

    gt.generate_all(config)

    tickets_dir = tmp_path / "tickets"
    assert (tickets_dir / "ticket_00001.png").exists()
    assert (tickets_dir / "ticket_00002.png").exists()
    assert (tickets_dir / "ticket_00003.png").exists()
    assert len(list(tickets_dir.glob("*.png"))) == 3

    pdf_path = tmp_path / "tickets.pdf"
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0

    # Intermediate working directory must not leak into the output
    assert not (tmp_path / "pages").exists()


def test_generate_all_reports_progress_via_callback(tmp_path):
    config = gt.default_config()
    config["OUTPUT_DIR"] = str(tmp_path)
    config["START_NUMBER"] = 1
    config["TOTAL_TICKETS"] = 3

    calls = []
    gt.generate_all(
        config,
        on_progress=lambda current, total, phase: calls.append((current, total, phase)),
    )

    ticket_calls = [c for c in calls if c[2] == "tickets"]
    page_calls = [c for c in calls if c[2] == "pages"]

    assert ticket_calls == [(1, 3, "tickets"), (2, 3, "tickets"), (3, 3, "tickets")]
    assert page_calls == [(1, 1, "pages")]
