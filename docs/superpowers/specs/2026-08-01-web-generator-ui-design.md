# Web UI for Raffle Ticket Generator — Design

## Purpose

Add a local browser-based form on top of the existing `generate_tickets.py`
so the user can choose event details and the ticket number range (start/end)
per run, instead of editing constants in the script each time. A progress
bar shows generation status, and the resulting PDF auto-downloads when done.

## Tech stack

- Flask (new dependency) for the web server.
- The existing `generate_tickets.py` module is reused as-is for all
  drawing/layout/file-writing logic — no duplicated ticket-drawing code.
- A single Jinja2 template (`templates/index.html`) with inline `<style>`
  and `<script>` — no separate static asset build step.
- Runs only on `127.0.0.1` (localhost) — this is a single-user local tool,
  not exposed to the network. Flask's debug mode stays off.

## Changes to generate_tickets.py

`generate_all(config, on_progress=None)` gains an optional callback
parameter:

- If `on_progress` is `None` (the current CLI behavior), it prints to the
  console exactly as it does today — no behavior change, existing tests
  keep passing unmodified.
- If provided, `on_progress(current, total, phase)` is called at the same
  checkpoints where the function currently prints progress, instead of
  printing. `phase` is the string `"tickets"` while saving individual PNGs,
  and `"pages"` while building page images. `current`/`total` are 1-indexed
  progress within that phase.

No other function in `generate_tickets.py` changes.

## Web app (app.py)

**Routes:**

- `GET /` — renders `templates/index.html` with the form.
- `POST /generate` — reads and validates form fields, resets the in-memory
  job state, starts a background thread running `generate_all` with an
  `on_progress` callback that updates that job state, and returns
  immediately (does not block on generation).
- `GET /progress` — returns a JSON snapshot of the current job state:
  `{"status": "idle"|"running"|"done"|"error", "phase": "tickets"|"pages"|"", "current": int, "total": int, "error": str|None}`.
- `GET /download` — once `status == "done"`, serves `output/tickets.pdf` as
  an attachment (`send_file`). Returns 409 if not yet done.

**Form fields → config mapping:**

| Form field | Maps to config key | Notes |
|---|---|---|
| Event Name | `EVENT_NAME` | text input, required |
| Event Date | `EVENT_DATE` | text input, required |
| Prizes | `PRIZES` | textarea, one prize per non-blank line |
| Start Number | `START_NUMBER` | integer input, required |
| End Number | — | integer input, required; used only to compute `TOTAL_TICKETS` |

`TOTAL_TICKETS = End Number - Start Number + 1`. The endpoint rejects the
request (400, with an error message re-rendered in the form) if End Number
is less than Start Number, or if any required field is missing/non-numeric.

**Job state:** a single module-level dict, since this is a single-user
local tool and only one generation job is expected to run at a time.
Starting a new job while one is already `"running"` is rejected (409) —
no queueing, no concurrent jobs.

## Frontend (templates/index.html)

A single page with:

- The input form described above and a "Generate" button.
- On submit, JavaScript intercepts the form (`fetch` POST to `/generate`,
  `preventDefault` on the native submit), then shows a progress section and
  starts polling `GET /progress` every 1 second.
- The progress bar/text updates from the polled JSON: e.g. "Generating
  tickets... 4500/10000" or "Building pages... 620/1000".
- When `status` becomes `"done"`, polling stops and the browser is
  navigated to `/download` to trigger the PDF download.
- When `status` becomes `"error"`, polling stops and the error message from
  the JSON is shown in place of the progress bar.

## Output

Unchanged from the existing script: `output/tickets/ticket_00001.png ...`
and `output/tickets.pdf`, written relative to wherever `app.py` is run
from. Each new run overwrites the previous run's output (no per-job output
directories) — acceptable since this is a single-user sequential tool.

## Testing / validation

- Unit test: calling `generate_all(config, on_progress=callback)` with a
  small `TOTAL_TICKETS` records the expected sequence of `(current, total,
  phase)` calls, ending with `(total_tickets, total_tickets, "tickets")`
  and `(num_pages, num_pages, "pages")`.
- Flask test-client tests (no real browser needed):
  - `GET /` returns 200 and the response body contains the form's input
    names.
  - `POST /generate` with a valid small range (e.g. start=1, end=3)
    returns 200/202; polling `GET /progress` (synchronously, since tests
    run the generation inline rather than racing a real background thread)
    eventually reports `status == "done"`.
  - `POST /generate` with `end < start` returns 400 with an error message.
  - `GET /download` after a completed small job returns
    `Content-Type: application/pdf` and a non-empty body.
- Manual validation: run `python app.py`, open `http://127.0.0.1:5000` in a
  browser, submit a small range (e.g. 1-20), watch the progress bar, and
  confirm the PDF auto-downloads and matches the entered event details.

## Known trade-offs

- Polling every 1 second is simpler than Server-Sent Events/WebSockets but
  has up to ~1 second of progress-display lag — acceptable for a local
  single-user tool.
- Only one job can run at a time (in-memory global state, no locking
  needed beyond that single-job restriction) — sufficient since this is a
  local tool for one person, not a multi-user server.
- Re-running overwrites the previous `output/` — there is no history of
  past runs. Acceptable since each run is a fresh, complete batch.
