# Raffle Ticket Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single Python script that generates 10,000+ sequentially numbered raffle tickets (main + tear-off stub) as individual PNGs and a combined print-ready legal-size PDF.

**Architecture:** One script, `generate_tickets.py`, with pure drawing/layout functions (testable without file I/O) and a thin `generate_all` driver that does the file I/O (saving PNGs, assembling the PDF). Fonts are loaded once and passed explicitly into drawing functions rather than reloaded per ticket.

**Tech Stack:** Python 3, Pillow (PIL) only for runtime; pytest for tests.

## Global Constraints

- Runtime dependency: Pillow only. No ReportLab, no pdf2image, no other imaging libs.
- All user-editable values (event name, date, prizes, ticket range, colors, font, output dir) live as module-level constants at the top of `generate_tickets.py` — reusing for a new event means editing constants, not code.
- Page size: Legal (8.5in x 14in) at 300 DPI → 2550x4200 px. 10 tickets per page (2 columns x 5 rows).
- Ticket numbers are zero-padded to 5 digits (e.g. `00001`), formatted as `No. 00001`.
- Each ticket = main part (~75% width) + stub part (~25% width) separated by a dashed line, both showing the same number and a blank `Name:` line.
- Output: `OUTPUT_DIR/tickets/ticket_00001.png ...` (one file per ticket) and `OUTPUT_DIR/tickets.pdf` (one multi-page PDF). No other files should remain in `OUTPUT_DIR` after a run.
- Progress must print to console periodically (every 500 tickets, and every 100 pages) — a 10,000-ticket run is not silent.
- Memory: never hold more than one full-resolution page image decoded in memory at a time during PDF assembly (10,000 tickets → ~1,000 pages; holding all of them decoded simultaneously would use tens of GB). Pages must be written to disk and re-opened lazily when building the PDF.

---

### Task 1: Project scaffolding, config, and font loading

**Files:**
- Create: `generate_tickets.py`
- Create: `requirements.txt`
- Test: `tests/test_generate_tickets.py`

**Interfaces:**
- Produces: `default_config() -> dict` with keys `EVENT_NAME, EVENT_DATE, PRIZES, START_NUMBER, TOTAL_TICKETS, OUTPUT_DIR, FONT_PATH, ACCENT_COLOR`.
- Produces: `load_font(path: str, size: int) -> PIL.ImageFont.ImageFont` (falls back to `ImageFont.load_default()` if `path` doesn't exist, printing a warning — never raises).
- Produces module-level constants used by later tasks: `DPI, PAGE_W, PAGE_H, COLS, ROWS, MARGIN, TICKET_W, TICKET_H, FONT_SIZES, LINE_STEP`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_generate_tickets.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_generate_tickets.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generate_tickets'`

- [ ] **Step 3: Create requirements.txt**

```
Pillow>=10.0.0
pytest>=7.0.0
```

- [ ] **Step 4: Implement generate_tickets.py scaffolding**

Create `generate_tickets.py`:

```python
import os

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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_generate_tickets.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add generate_tickets.py requirements.txt tests/test_generate_tickets.py
git commit -m "feat: add config scaffolding and font loading"
```

---

### Task 2: Ticket drawing (main + stub + divider)

**Files:**
- Modify: `generate_tickets.py` (append after `load_font`)
- Test: `tests/test_generate_tickets.py` (append)

**Interfaces:**
- Consumes: `default_config() -> dict`, `load_font(path, size)`, constants `TICKET_W, TICKET_H, FONT_SIZES, LINE_STEP` from Task 1.
- Produces: `build_fonts(config: dict) -> dict[str, ImageFont]` keyed by the same keys as `FONT_SIZES`.
- Produces: `draw_ticket(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, number: int, config: dict, fonts: dict) -> None` — draws directly onto `draw`'s image, no return value.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_generate_tickets.py`:

```python
from PIL import Image, ImageDraw


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_generate_tickets.py -v -k "build_fonts or draw_ticket"`
Expected: FAIL with `AttributeError: module 'generate_tickets' has no attribute 'build_fonts'`

- [ ] **Step 3: Implement build_fonts and draw_ticket**

Append to `generate_tickets.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_generate_tickets.py -v -k "build_fonts or draw_ticket"`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add generate_tickets.py tests/test_generate_tickets.py
git commit -m "feat: draw ticket main/stub layout with divider"
```

---

### Task 3: Standalone ticket image (PNG output unit)

**Files:**
- Modify: `generate_tickets.py` (append after `draw_ticket`)
- Test: `tests/test_generate_tickets.py` (append)

**Interfaces:**
- Consumes: `draw_ticket(draw, x, y, w, h, number, config, fonts)`, constants `TICKET_W, TICKET_H` from Tasks 1-2.
- Produces: `create_ticket_image(number: int, config: dict, fonts: dict) -> PIL.Image.Image` sized `(TICKET_W, TICKET_H)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_generate_tickets.py`:

```python
def test_create_ticket_image_has_expected_size():
    config = gt.default_config()
    fonts = gt.build_fonts(config)
    img = gt.create_ticket_image(7, config, fonts)
    assert img.size == (gt.TICKET_W, gt.TICKET_H)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_generate_tickets.py -v -k create_ticket_image`
Expected: FAIL with `AttributeError: module 'generate_tickets' has no attribute 'create_ticket_image'`

- [ ] **Step 3: Implement create_ticket_image**

Append to `generate_tickets.py`:

```python
def create_ticket_image(number, config, fonts):
    img = Image.new("RGB", (TICKET_W, TICKET_H), "white")
    draw = ImageDraw.Draw(img)
    draw_ticket(draw, 0, 0, TICKET_W, TICKET_H, number, config, fonts)
    return img
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_generate_tickets.py -v -k create_ticket_image`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add generate_tickets.py tests/test_generate_tickets.py
git commit -m "feat: add standalone ticket image creation"
```

---

### Task 4: Page composition (10 tickets per legal page)

**Files:**
- Modify: `generate_tickets.py` (append after `create_ticket_image`)
- Test: `tests/test_generate_tickets.py` (append)

**Interfaces:**
- Consumes: `draw_ticket(...)`, constants `PAGE_W, PAGE_H, COLS, ROWS, MARGIN, TICKET_W, TICKET_H`.
- Produces: `create_page(ticket_numbers: list[int], config: dict, fonts: dict) -> PIL.Image.Image` sized `(PAGE_W, PAGE_H)`, placing up to 10 tickets in a 2x5 grid. Fewer than 10 numbers is valid (partial last page).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate_tickets.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_generate_tickets.py -v -k create_page`
Expected: FAIL with `AttributeError: module 'generate_tickets' has no attribute 'create_page'`

- [ ] **Step 3: Implement create_page**

Append to `generate_tickets.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_generate_tickets.py -v -k create_page`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add generate_tickets.py tests/test_generate_tickets.py
git commit -m "feat: compose legal-size pages of 10 tickets"
```

---

### Task 5: Batch driver (PNGs + memory-safe PDF assembly)

**Files:**
- Modify: `generate_tickets.py` (append after `create_page`)
- Test: `tests/test_generate_tickets.py` (append)

**Interfaces:**
- Consumes: `create_ticket_image(number, config, fonts)`, `create_page(ticket_numbers, config, fonts)`, `build_fonts(config)`.
- Produces: `chunk_numbers(start: int, total: int, page_size: int = 10) -> list[list[int]]`.
- Produces: `generate_all(config: dict) -> None` — writes `config["OUTPUT_DIR"]/tickets/ticket_NNNNN.png` for every ticket and `config["OUTPUT_DIR"]/tickets.pdf`, printing progress every 500 tickets and every 100 pages, and removes its intermediate `pages/` working directory when done.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate_tickets.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_generate_tickets.py -v -k "chunk_numbers or generate_all"`
Expected: FAIL with `AttributeError: module 'generate_tickets' has no attribute 'chunk_numbers'`

- [ ] **Step 3: Implement chunk_numbers and generate_all**

Append to `generate_tickets.py` (also add `import shutil` to the top imports alongside `import os`):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_generate_tickets.py -v -k "chunk_numbers or generate_all"`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full test suite**

Run: `pytest tests/test_generate_tickets.py -v`
Expected: PASS (all tests so far pass)

- [ ] **Step 6: Commit**

```bash
git add generate_tickets.py tests/test_generate_tickets.py
git commit -m "feat: add batch driver with memory-safe PDF assembly"
```

---

### Task 6: CLI entry point, README, and manual smoke test

**Files:**
- Modify: `generate_tickets.py` (append at the very end)
- Create: `README.md`

**Interfaces:**
- Consumes: `default_config()`, `generate_all(config)`.
- Produces: running `python generate_tickets.py` generates the full configured batch.

- [ ] **Step 1: Add the CLI entry point**

Append to the very end of `generate_tickets.py`:

```python
if __name__ == "__main__":
    generate_all(default_config())
```

- [ ] **Step 2: Write README.md**

```markdown
# Raffle Ticket Generator

Generates sequentially numbered raffle tickets (main + tear-off stub) as
individual PNGs and a single print-ready legal-size PDF (10 tickets per page).

## Setup

```
pip install -r requirements.txt
```

## Configure

Edit the constants at the top of `generate_tickets.py`:

- `EVENT_NAME`, `EVENT_DATE`, `PRIZES` — text shown on every ticket.
- `START_NUMBER`, `TOTAL_TICKETS` — the numbered range to generate.
- `OUTPUT_DIR` — where `tickets/` (PNGs) and `tickets.pdf` are written.
- `FONT_PATH` — path to a `.ttf` font file. Falls back to a basic default
  font if the path doesn't exist.
- `ACCENT_COLOR` — RGB tuple used for the ticket number.

## Run

**Try a small batch first** (e.g. set `TOTAL_TICKETS = 20`) to check the
layout before generating the full run — 10,000 tickets takes a few minutes
and produces a large PDF.

```
python generate_tickets.py
```

Output:

```
output/tickets/ticket_00001.png ...
output/tickets.pdf
```
```

- [ ] **Step 3: Manual smoke test with a small batch**

Temporarily edit `generate_tickets.py`, setting `TOTAL_TICKETS = 20`, then run:

Run: `python generate_tickets.py`
Expected: Console prints `Generated 20/20 tickets...` and `Saved PDF: output/tickets.pdf (2 pages)`. Open `output/tickets/ticket_00001.png` and `output/tickets.pdf` and visually confirm: event name, date, prizes, ticket number, dashed divider, and blank Name line all appear correctly on both main and stub sections, and the PDF has 2 pages of 10 tickets each (2 columns x 5 rows).

Revert `TOTAL_TICKETS` back to `10000` (or the real desired count) afterward.

- [ ] **Step 4: Run the full automated test suite one more time**

Run: `pytest tests/test_generate_tickets.py -v`
Expected: PASS (all tests pass)

- [ ] **Step 5: Commit**

```bash
git add generate_tickets.py README.md
git commit -m "feat: add CLI entry point and usage README"
```
