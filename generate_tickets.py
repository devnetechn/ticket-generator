import os
import shutil

from PIL import Image, ImageDraw, ImageFont

# ---- User-editable settings ----
ORG_NAME = "IHES Alumni Association"
EVENT_NAME = "2nd Grand Alumni Homecoming"
EVENT_DATE = "December 29, 2026"
SUBTITLE_LINES = [
    "IHESAA Raffle for a Cause",
    "Reconnecting Hearts, Celebrating Memories, Building Legacies",
]
PRIZES = [
    "1st Prize: iPhone 13",
    "2nd Prize: Refrigerator",
    "3rd Prize: Water Dispenser",
]
CONSOLATION_TEXT = "10 Consolation Prizes (5kls. Of Rice)"
PRICE = "\u20b110.00"
PROCEEDS_TEXT = (
    'Proceeds from the cause will be the construction of '
    '"PROJECT I.H.E.S. Identity, Heritage, Excellence, and Signage,".'
)
LOGO_PATH = "assets/watermark.png"  # seal/logo watermark image; if missing, a
                                     # tiled text watermark is drawn instead
SEAL_TEXT = "IHESAA * OFFICIAL RAFFLE TICKET *"  # ring text for the placeholder seal
START_NUMBER = 1
TOTAL_TICKETS = 10000
OUTPUT_DIR = "output"
FONT_PATH = "C:/Windows/Fonts/times.ttf"          # serif body text
BOLD_FONT_PATH = "C:/Windows/Fonts/timesbd.ttf"    # serif bold (ticket number)
ITALIC_FONT_PATH = "C:/Windows/Fonts/timesbi.ttf"  # serif bold italic (subtitle/proceeds)
TITLE_FONT_PATH = "C:/Windows/Fonts/courbd.ttf"    # monospace bold (event title)
STUB_FONT_PATH = "C:/Windows/Fonts/arial.ttf"      # sans (stub labels)
STUB_BOLD_FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"  # sans bold (price tag)
ACCENT_COLOR = (178, 34, 34)
PRICE_BG_COLOR = (250, 218, 200)

# ---- Layout constants (do not need editing) ----
DPI = 300
PAGE_W = int(8.5 * DPI)  # 2550
PAGE_H = int(14 * DPI)   # 4200
COLS, ROWS = 2, 6
MARGIN = 60
TICKET_W = (PAGE_W - 2 * MARGIN) // COLS  # 1215
TICKET_H = (PAGE_H - 1 * MARGIN) // ROWS  # 816
PAD = 15
MAIN_W = int(TICKET_W * 0.58)

FONT_SIZES = {
    "org": 36,
    "title": 54,
    "date": 32,
    "subtitle": 29,
    "prize": 50,
    "ticketno": 44,
    "proceeds": 22,
    "stub_label": 26,
    "price": 30,
    "watermark": 30,
}

LINE_STEP = {
    "org": 42,
    "title": 62,
    "date": 38,
    "subtitle": 35,
    "prize": 42,
    "ticketno": 46,
    "proceeds": 28,
}

FONT_ROLES = {
    "org": "serif",
    "date": "serif",
    "prize": "serif_bold",
    "title": "title",
    "subtitle": "serif_bold_italic",
    "proceeds": "serif_bold_italic",
    "ticketno": "serif_bold",
    "stub_label": "sans",
    "price": "sans_bold",
    "watermark": "serif",
}

STUB_COLUMNS = ["Ticket No.","Name", "Contact No.", "Address", "Signature"]


def default_config():
    return {
        "ORG_NAME": ORG_NAME,
        "EVENT_NAME": EVENT_NAME,
        "EVENT_DATE": EVENT_DATE,
        "SUBTITLE_LINES": SUBTITLE_LINES,
        "PRIZES": PRIZES,
        "CONSOLATION_TEXT": CONSOLATION_TEXT,
        "PRICE": PRICE,
        "PROCEEDS_TEXT": PROCEEDS_TEXT,
        "LOGO_PATH": LOGO_PATH,
        "SEAL_TEXT": SEAL_TEXT,
        "START_NUMBER": START_NUMBER,
        "TOTAL_TICKETS": TOTAL_TICKETS,
        "OUTPUT_DIR": OUTPUT_DIR,
        "FONT_PATH": FONT_PATH,
        "BOLD_FONT_PATH": BOLD_FONT_PATH,
        "ITALIC_FONT_PATH": ITALIC_FONT_PATH,
        "TITLE_FONT_PATH": TITLE_FONT_PATH,
        "STUB_FONT_PATH": STUB_FONT_PATH,
        "STUB_BOLD_FONT_PATH": STUB_BOLD_FONT_PATH,
        "ACCENT_COLOR": ACCENT_COLOR,
        "PRICE_BG_COLOR": PRICE_BG_COLOR,
    }


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        print(f"Warning: font not found at {path}, using default font.")
        return ImageFont.load_default()


def fit_font(path, size, min_size, text, max_width):
    font = load_font(path, size)
    while size > min_size and text_size(text, font)[0] > max_width:
        size -= 2
        font = load_font(path, size)
    return font


def build_fonts(config):
    role_paths = {
        "serif": config["FONT_PATH"],
        "serif_bold": config["BOLD_FONT_PATH"],
        "serif_bold_italic": config["ITALIC_FONT_PATH"],
        "title": config["TITLE_FONT_PATH"],
        "sans": config["STUB_FONT_PATH"],
        "sans_bold": config["STUB_BOLD_FONT_PATH"],
    }
    fonts = {
        key: load_font(role_paths[role], FONT_SIZES[key])
        for key, role in FONT_ROLES.items()
    }

    avail_w = MAIN_W - 2 * PAD
    fonts["title"] = fit_font(
        role_paths["title"], FONT_SIZES["title"], 22, config["EVENT_NAME"], avail_w,
    )
    if config["SUBTITLE_LINES"]:
        longest = max(config["SUBTITLE_LINES"], key=len)
        fonts["subtitle"] = fit_font(
            role_paths["serif_bold_italic"], FONT_SIZES["subtitle"], 14, longest, avail_w,
        )
    prize_lines = list(config["PRIZES"]) + [config["CONSOLATION_TEXT"]]
    if prize_lines:
        longest = max(prize_lines, key=len)
        fonts["prize"] = fit_font(
            role_paths["serif_bold"], FONT_SIZES["prize"], 18, longest, avail_w,
        )
    return fonts


def text_size(text, font):
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = dummy.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def vertical_text_size(text, font):
    tw, th = text_size(text, font)
    return th + 4, tw + 4  # (width, height) once rotated 90 degrees


def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        w, _ = text_size(candidate, font)
        if w <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_vertical_text(img, x, y, text, font, fill):
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = dummy.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    text_img = Image.new("RGBA", (tw + 4, th + 4), (255, 255, 255, 0))
    ImageDraw.Draw(text_img).text((2 - bbox[0], 2 - bbox[1]), text, font=font, fill=fill)
    rotated = text_img.rotate(90, expand=True)
    img.paste(rotated, (x, y), rotated)


def draw_dashed_vline(draw, x, y_top, y_bottom, dash_len=10, gap_len=6):
    dy = y_top
    while dy < y_bottom:
        draw.line([(x, dy), (x, min(dy + dash_len, y_bottom))], fill="black", width=2)
        dy += dash_len + gap_len


def draw_tiled_watermark(img, x, y, w, h, text, font, fill=(0, 0, 0, 30)):
    tw, th = text_size(text, font)
    tile = Image.new("RGBA", (tw + 30, th + 30), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((15, 15), text, font=font, fill=fill)
    rotated = tile.rotate(30, expand=True)
    rw, rh = rotated.size
    step_x, step_y = rw + 50, rh + 40

    clip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    row = 0
    yy = -rh
    while yy < h:
        offset = (row % 2) * (step_x // 2)
        xx = -rw + offset
        while xx < w:
            clip.paste(rotated, (int(xx), int(yy)), rotated)
            xx += step_x
        yy += step_y
        row += 1

    img.paste(clip, (x, y), clip)


def load_logo(path, max_size=140, fade=0.55):
    if not path or not os.path.exists(path):
        return None
    logo = Image.open(path).convert("RGBA")
    logo.thumbnail((max_size, max_size))
    r, g, b, a = logo.split()
    a = a.point(lambda v: int(v * fade))
    return Image.merge("RGBA", (r, g, b, a))


def draw_tiled_image(img, x, y, w, h, tile_img, spacing=26):
    tw, th = tile_img.size
    step_x, step_y = tw + spacing, th + spacing
    clip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    row = 0
    yy = -th // 2
    while yy < h:
        offset = (row % 2) * (step_x // 2)
        xx = -offset
        while xx < w:
            clip.paste(tile_img, (int(xx), int(yy)), tile_img)
            xx += step_x
        yy += step_y
        row += 1
    img.paste(clip, (x, y), clip)


def draw_centered(draw, cx, y, text, font, fill):
    lw, _ = text_size(text, font)
    draw.text((cx - lw // 2, y), text, font=font, fill=fill)


def draw_ticket(img, draw, x, y, w, h, number, config, fonts, logo_img=None):
    pad = 15
    main_w = int(w * 0.58)
    price_w = int(w * 0.08)
    stub_w = w - main_w - price_w
    col_w = stub_w // len(STUB_COLUMNS)

    draw.rectangle([x, y, x + w - 1, y + h - 1], outline="black", width=3)

    divider1_x = x + main_w
    divider2_x = divider1_x + price_w

    if logo_img is not None:
        draw_tiled_image(img, x, y, main_w, h, logo_img)
    else:
        draw_tiled_watermark(img, x, y, main_w, h, config["ORG_NAME"], fonts["watermark"])

    number_text = f"{number:05d}"

    # --- Main section ---
    # Everything centered horizontally. The gaps between blocks (header,
    # subtitle, prizes, ticket no, proceeds) are scaled up to use whatever
    # vertical room this ticket has, so the actual content reaches all the
    # way down instead of stopping partway with blank space below it.
    proceeds_lines = wrap_text(config["PROCEEDS_TEXT"], fonts["proceeds"], main_w - 2 * pad)
    num_prizes = len(config["PRIZES"])

    fixed_content_h = (
        LINE_STEP["org"] + LINE_STEP["title"] + LINE_STEP["date"]
        + LINE_STEP["subtitle"] * len(config["SUBTITLE_LINES"])
        + LINE_STEP["prize"] * (num_prizes + 1)
        + LINE_STEP["ticketno"]
        + LINE_STEP["proceeds"] * len(proceeds_lines)
    )
    gap_after_date, gap_before_prizes, gap_per_prize = 10, 20, 4
    gap_after_consolation, gap_after_ticketno = 12, 10
    base_gaps = (
        gap_after_date + gap_before_prizes + gap_per_prize * num_prizes
        + gap_after_consolation + gap_after_ticketno
    )
    available_h = h - 2 * pad
    leftover = available_h - fixed_content_h - base_gaps
    # Expand gaps to fill spare room when content is short; shrink them
    # (down to a floor, never below 0) when content runs long, so extra
    # prizes/proceeds text compress the spacing instead of overflowing
    # past the bottom of the ticket.
    scale = max(0, (base_gaps + leftover) / base_gaps) if base_gaps else 1

    mx, my = x + pad, y + pad
    main_cx = mx + (main_w - 2 * pad) // 2

    draw_centered(draw, main_cx, my, config["ORG_NAME"], fonts["org"], "black")
    my += LINE_STEP["org"]
    draw_centered(draw, main_cx, my, config["EVENT_NAME"], fonts["title"], "black")
    my += LINE_STEP["title"]
    draw_centered(draw, main_cx, my, config["EVENT_DATE"], fonts["date"], "black")
    my += LINE_STEP["date"] + gap_after_date * scale
    for line in config["SUBTITLE_LINES"]:
        draw_centered(draw, main_cx, my, line, fonts["subtitle"], "black")
        my += LINE_STEP["subtitle"]
    my += gap_before_prizes * scale
    for prize in config["PRIZES"]:
        draw_centered(draw, main_cx, my, prize, fonts["prize"], "black")
        my += LINE_STEP["prize"] + gap_per_prize * scale
    draw_centered(draw, main_cx, my, config["CONSOLATION_TEXT"], fonts["prize"], "black")
    my += LINE_STEP["prize"] + gap_after_consolation * scale

    draw_centered(
        draw, main_cx, my, f"Ticket No.: {number_text}",
        fonts["ticketno"], config["ACCENT_COLOR"],
    )
    my += LINE_STEP["ticketno"] + gap_after_ticketno * scale

    for line in proceeds_lines:
        draw_centered(draw, main_cx, my, line, fonts["proceeds"], "black")
        my += LINE_STEP["proceeds"]

    # --- Dividers ---
    draw_dashed_vline(draw, divider1_x, y, y + h)
    draw.line([(divider2_x, y), (divider2_x, y + h)], fill="black", width=2)

    # --- Price tag strip ---
    draw.rectangle(
        [divider1_x + 1, y + 1, divider2_x - 1, y + h - 1],
        fill=config["PRICE_BG_COLOR"],
    )
    price_w_r, price_h_r = vertical_text_size(config["PRICE"], fonts["price"])
    draw_vertical_text(
        img, divider1_x + (price_w - price_w_r) // 2, y + (h - price_h_r) // 2,
        config["PRICE"], fonts["price"], config["ACCENT_COLOR"],
    )

    # --- Stub section ---
    # A tiled watermark covers the whole stub background, same treatment as
    # the main section, instead of a small blank logo box.
    if logo_img is not None:
        draw_tiled_image(img, divider2_x, y, stub_w, h, logo_img)
    else:
        draw_tiled_watermark(img, divider2_x, y, stub_w, h, config["SEAL_TEXT"], fonts["watermark"])

    for i, label in enumerate(STUB_COLUMNS):
        col_x = divider2_x + i * col_w
        if i > 0:
            draw.line([(col_x, y), (col_x, y + h)], fill="black", width=1)

        if i == 0:
            label_text = f"{label}: {number_text}"
            fill = config["ACCENT_COLOR"]
        else:
            label_text = f"{label}:"
            fill = "black"

        rot_w, rot_h = vertical_text_size(label_text, fonts["stub_label"])
        text_x = col_x + (col_w - rot_w) // 2
        text_y = y + h - pad - rot_h
        draw_vertical_text(img, text_x, text_y, label_text, fonts["stub_label"], fill)


def create_ticket_image(number, config, fonts, logo_img=None):
    img = Image.new("RGB", (TICKET_W, TICKET_H), "white")
    draw = ImageDraw.Draw(img)
    draw_ticket(img, draw, 0, 0, TICKET_W, TICKET_H, number, config, fonts, logo_img)
    return img


def create_page(ticket_numbers, config, fonts, logo_img=None):
    page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    draw = ImageDraw.Draw(page)
    for i, number in enumerate(ticket_numbers):
        col = i % COLS
        row = i // COLS
        x = MARGIN + col * TICKET_W
        y = MARGIN + row * TICKET_H
        draw_ticket(page, draw, x, y, TICKET_W, TICKET_H, number, config, fonts, logo_img)
    return page


def chunk_numbers(start, total, page_size=10):
    numbers = list(range(start, start + total))
    return [numbers[i:i + page_size] for i in range(0, len(numbers), page_size)]


def generate_all(config, on_progress=None):
    tickets_dir = os.path.join(config["OUTPUT_DIR"], "tickets")
    pages_dir = os.path.join(config["OUTPUT_DIR"], "pages")
    os.makedirs(tickets_dir, exist_ok=True)
    os.makedirs(pages_dir, exist_ok=True)
    fonts = build_fonts(config)
    logo_img = load_logo(config.get("LOGO_PATH", ""))

    start = config["START_NUMBER"]
    total = config["TOTAL_TICKETS"]

    for i, number in enumerate(range(start, start + total), start=1):
        img = create_ticket_image(number, config, fonts, logo_img)
        img.save(os.path.join(tickets_dir, f"ticket_{number:05d}.png"))
        if on_progress is not None:
            on_progress(i, total, "tickets")
        elif i % 500 == 0 or i == total:
            print(f"Generated {i}/{total} tickets...")

    page_chunks = chunk_numbers(start, total, page_size=10)
    num_pages = len(page_chunks)
    page_paths = []
    for page_num, numbers in enumerate(page_chunks, start=1):
        page_img = create_page(numbers, config, fonts, logo_img)
        page_path = os.path.join(pages_dir, f"page_{page_num:04d}.png")
        page_img.save(page_path)
        page_paths.append(page_path)
        if on_progress is not None:
            on_progress(page_num, num_pages, "pages")
        elif page_num % 100 == 0 or page_num == num_pages:
            print(f"Built {page_num}/{num_pages} pages...")

    pdf_path = os.path.join(config["OUTPUT_DIR"], "tickets.pdf")
    first_page = Image.open(page_paths[0]).convert("RGB")
    rest_pages = (Image.open(p).convert("RGB") for p in page_paths[1:])
    first_page.save(pdf_path, save_all=True, append_images=rest_pages)
    if on_progress is None:
        print(f"Saved PDF: {pdf_path} ({len(page_paths)} pages)")

    shutil.rmtree(pages_dir)


if __name__ == "__main__":
    generate_all(default_config())
