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
