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
