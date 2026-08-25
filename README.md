# Raffle Ticket Generator

Generates sequentially numbered raffle tickets (main + tear-off stub) as
individual PNGs and a single print-ready legal-size PDF (10 tickets per page).

## Setup

```
pip install -r requirements.txt
```

## Configure

Edit the constants at the top of `generate_tickets.py`:

- `ORG_NAME`, `EVENT_NAME`, `EVENT_DATE`, `SUBTITLE_LINES`, `PRIZES`,
  `CONSOLATION_TEXT`, `PRICE`, `PROCEEDS_TEXT` — text shown on every ticket.
- `LOGO_PATH` — optional path to a seal/logo image shown on the stub. Leave
  blank (or point at a missing file) to leave that space empty.
- `START_NUMBER`, `TOTAL_TICKETS` — the numbered range to generate. The
  ticket number is auto-filled on both the main ticket and the stub (no
  hand-writing needed), so they stay matched for the draw.
- `OUTPUT_DIR` — where `tickets/` (PNGs) and `tickets.pdf` are written.
- `FONT_PATH`, `BOLD_FONT_PATH`, `ITALIC_FONT_PATH` — paths to `.ttf` font
  files. Each falls back to a basic default font if its path doesn't exist.
- `ACCENT_COLOR` — RGB tuple used for the ticket number and price tag text.
- `PRICE_BG_COLOR` — RGB tuple used for the price tag strip background.

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

## Run (web UI)

Instead of editing constants and running the CLI, you can use the local
web form:

```
python app.py
```

Then open `http://127.0.0.1:5000` in a browser. Fill in the event name,
date, prizes (one per line), and the start/end ticket number range, then
click Generate. A progress bar tracks the run, and `tickets.pdf`
auto-downloads when it finishes. Individual PNGs are still written to
`output/tickets/` on the machine running the server.

The web UI only listens on `127.0.0.1` (this machine only) and runs one
generation job at a time.
