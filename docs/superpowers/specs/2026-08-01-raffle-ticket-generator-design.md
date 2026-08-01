# Raffle Ticket Generator — Design

## Purpose

Generate large batches (10,000+) of sequentially numbered raffle tickets for
print. Each ticket has a main stub and a tear-off stub sharing the same
number, separated by a dashed cut line. Output is both individual PNG images
per ticket and a single print-ready PDF (legal size, 10 tickets per page).

## Tech stack

- Python 3
- Pillow (PIL) only — no other dependencies
- Single script: `generate_tickets.py`
- A `CONFIG` section at the top of the script holds all user-editable values
  (event name, date, prizes, ticket range, colors, font, output folder). No
  code changes needed to reuse for a different event.

## Ticket layout

- Page size: Legal (8.5in x 14in) at 300 DPI → 2550x4200 px canvas.
- 10 tickets per page, arranged 2 columns x 5 rows.
- Thin cut-guide lines between tickets on the page for scissor-cutting.
- Each ticket is split into:
  - **Main part** (~75% width): event name, date, prizes list, large ticket
    number in a corner, blank "Name: ______________" line for the buyer to
    fill in.
  - **Stub part** (~25% width): event name (smaller), the same ticket
    number, and a smaller blank "Name: ______" line — kept by the organizer
    for the draw.
  - A dashed vertical line separates main and stub, indicating where to tear.
- A solid border outlines the whole ticket.

## Config (user-editable constants)

```python
EVENT_NAME = "Sample Raffle Draw"
EVENT_DATE = "December 25, 2026"
PRIZES = ["1st Prize: iPhone 17", "2nd Prize: Smart TV", "3rd Prize: Aircon"]
START_NUMBER = 1
TOTAL_TICKETS = 10000
OUTPUT_DIR = "output"
FONT_PATH = "C:/Windows/Fonts/arial.ttf"  # falls back to Pillow default font if missing
ACCENT_COLOR = (178, 34, 34)  # ticket number / accent color, RGB
```

Ticket numbers are zero-padded to 5 digits (e.g. `00001`).

## Architecture / functions

- `load_font(path, size)` — loads the TTF font, falls back to Pillow's
  built-in default font with a printed warning if the path is missing.
- `draw_ticket(draw, x, y, w, h, number, config)` — draws one ticket
  (main + stub + dashed divider + border) onto an existing image at a given
  position/size.
- `create_ticket_image(number, config)` — creates a standalone
  ticket-sized `Image`, calls `draw_ticket` on it, returns the image. Used
  for the individual PNG output.
- `create_page(ticket_numbers, config)` — creates one legal-size page
  `Image`, places up to 10 tickets on it via `draw_ticket`, adds cut-guide
  lines, returns the image. Used for the PDF output.
- `generate_all(config)` — main driver:
  1. Iterates `START_NUMBER` .. `START_NUMBER + TOTAL_TICKETS - 1`.
  2. Saves each ticket as `output/tickets/ticket_00001.png`, etc.
  3. Batches tickets into groups of 10 and builds page images.
  4. Saves all pages as a single multi-page PDF via Pillow's
     `im.save(..., save_all=True, append_images=[...])`.
  5. Prints progress every 500 tickets (e.g. `Generated 500/10000...`).

## Output structure

```
output/
  tickets/
    ticket_00001.png
    ticket_00002.png
    ...
  tickets.pdf   # legal size, 10 tickets/page, print-ready
```

## Known trade-offs

- Rasterized PDF (not vector) — fine for print at 300 DPI, but text is not
  selectable/searchable in the PDF.
- 10,000 individual PNGs + a ~1,000-page PDF can take a few minutes to
  generate and consume noticeable disk space (roughly 1-3 GB depending on
  resolution). A progress indicator is printed so the run is not silent.

## Testing / validation

- First run with a small `TOTAL_TICKETS` (e.g. 20) to visually check the
  layout of both the individual PNGs and the generated PDF page.
- Once layout is confirmed correct, re-run with the full `TOTAL_TICKETS`
  (10,000 or more).
- No automated test suite — this is a single-purpose generation script;
  validation is visual (open a few PNGs + the PDF and inspect).
