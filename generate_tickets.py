import os
import shutil

from PIL import Image, ImageDraw, ImageFont

# ---- User-editable settings ----
EVENT_NAME = "Sample Raffle Draw"
EVENT_DATE = "December 25, 2026"
PRIZES = ["1st Prize: iPhone 17", "2nd Prize: Smart TV", "3rd Prize: Aircon"]
START_NUMBER = 1
TOTAL_TICKETS = 10000
OUTPUT_DIR = "output"
FONT_PATH = "C:/Windows/Fonts/arial.ttf"
ACCENT_COLOR = (178, 34, 34)

# ---- Layout constants (do not need editing) ----
DPI = 300
PAGE_W = int(8.5 * DPI)  # 2550
PAGE_H = int(14 * DPI)   # 4200
COLS, ROWS = 2, 5
MARGIN = 60
TICKET_W = (PAGE_W - 2 * MARGIN) // COLS  # 1215
TICKET_H = (PAGE_H - 2 * MARGIN) // ROWS  # 816

FONT_SIZES = {
    "title": 40,
    "number": 34,
    "normal": 26,
    "small": 20,
    "stub_normal": 18,
    "stub_small": 14,
}

LINE_STEP = {
    "title": 50,
    "normal": 34,
    "small": 26,
    "stub_normal": 24,
    "stub_small": 20,
}


def default_config():
    return {
        "EVENT_NAME": EVENT_NAME,
        "EVENT_DATE": EVENT_DATE,
        "PRIZES": PRIZES,
        "START_NUMBER": START_NUMBER,
        "TOTAL_TICKETS": TOTAL_TICKETS,
        "OUTPUT_DIR": OUTPUT_DIR,
        "FONT_PATH": FONT_PATH,
        "ACCENT_COLOR": ACCENT_COLOR,
    }


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        print(f"Warning: font not found at {path}, using default font.")
        return ImageFont.load_default()


def build_fonts(config):
    return {key: load_font(config["FONT_PATH"], size) for key, size in FONT_SIZES.items()}


def draw_ticket(draw, x, y, w, h, number, config, fonts):
    pad = 15
    stub_w = int(w * 0.25)
    main_w = w - stub_w

    draw.rectangle([x, y, x + w - 1, y + h - 1], outline="black", width=3)

    divider_x = x + main_w
    dash_len, gap_len = 10, 6
    dy = y
    while dy < y + h:
        draw.line(
            [(divider_x, dy), (divider_x, min(dy + dash_len, y + h))],
            fill="black", width=2,
        )
        dy += dash_len + gap_len

    number_text = f"No. {number:05d}"

    # --- Main section ---
    mx, my = x + pad, y + pad
    draw.text((mx, my), config["EVENT_NAME"], font=fonts["title"], fill="black")

    bbox = draw.textbbox((0, 0), number_text, font=fonts["number"])
    number_w = bbox[2] - bbox[0]
    draw.text(
        (x + main_w - pad - number_w, my), number_text,
        font=fonts["number"], fill=config["ACCENT_COLOR"],
    )

    my += LINE_STEP["title"]
    draw.text((mx, my), config["EVENT_DATE"], font=fonts["normal"], fill="black")
    my += LINE_STEP["normal"]
    for prize in config["PRIZES"]:
        draw.text((mx, my), prize, font=fonts["small"], fill="black")
        my += LINE_STEP["small"]

    name_y = y + h - LINE_STEP["normal"] - pad
    draw.text(
        (mx, name_y), "Name: _______________________",
        font=fonts["normal"], fill="black",
    )

    # --- Stub section ---
    sx, sy = divider_x + pad, y + pad
    draw.text((sx, sy), number_text, font=fonts["stub_normal"], fill=config["ACCENT_COLOR"])
    sy += LINE_STEP["stub_normal"]
    draw.text((sx, sy), config["EVENT_NAME"], font=fonts["stub_small"], fill="black")

    stub_name_y = y + h - LINE_STEP["stub_small"] - pad
    draw.text((sx, stub_name_y), "Name: ______", font=fonts["stub_small"], fill="black")


def create_ticket_image(number, config, fonts):
    img = Image.new("RGB", (TICKET_W, TICKET_H), "white")
    draw = ImageDraw.Draw(img)
    draw_ticket(draw, 0, 0, TICKET_W, TICKET_H, number, config, fonts)
    return img


def create_page(ticket_numbers, config, fonts):
    page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    draw = ImageDraw.Draw(page)
    for i, number in enumerate(ticket_numbers):
        col = i % COLS
        row = i // COLS
        x = MARGIN + col * TICKET_W
        y = MARGIN + row * TICKET_H
        draw_ticket(draw, x, y, TICKET_W, TICKET_H, number, config, fonts)
    return page


def chunk_numbers(start, total, page_size=10):
    numbers = list(range(start, start + total))
    return [numbers[i:i + page_size] for i in range(0, len(numbers), page_size)]


def generate_all(config):
    tickets_dir = os.path.join(config["OUTPUT_DIR"], "tickets")
    pages_dir = os.path.join(config["OUTPUT_DIR"], "pages")
    os.makedirs(tickets_dir, exist_ok=True)
    os.makedirs(pages_dir, exist_ok=True)
    fonts = build_fonts(config)

    start = config["START_NUMBER"]
    total = config["TOTAL_TICKETS"]

    for i, number in enumerate(range(start, start + total), start=1):
        img = create_ticket_image(number, config, fonts)
        img.save(os.path.join(tickets_dir, f"ticket_{number:05d}.png"))
        if i % 500 == 0 or i == total:
            print(f"Generated {i}/{total} tickets...")

    page_chunks = chunk_numbers(start, total)
    page_paths = []
    for page_num, numbers in enumerate(page_chunks, start=1):
        page_img = create_page(numbers, config, fonts)
        page_path = os.path.join(pages_dir, f"page_{page_num:04d}.png")
        page_img.save(page_path)
        page_paths.append(page_path)
        if page_num % 100 == 0 or page_num == len(page_chunks):
            print(f"Built {page_num}/{len(page_chunks)} pages...")

    pdf_path = os.path.join(config["OUTPUT_DIR"], "tickets.pdf")
    first_page = Image.open(page_paths[0]).convert("RGB")
    rest_pages = (Image.open(p).convert("RGB") for p in page_paths[1:])
    first_page.save(pdf_path, save_all=True, append_images=rest_pages)
    print(f"Saved PDF: {pdf_path} ({len(page_paths)} pages)")

    shutil.rmtree(pages_dir)
