# Web UI for Raffle Ticket Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local Flask web form on top of the existing `generate_tickets.py` so the user can set event details and a start/end ticket number range per run, watch a progress bar, and auto-download the resulting PDF — without editing script constants.

**Architecture:** `generate_tickets.py` gains an optional `on_progress` callback on `generate_all` (default `None` keeps today's console-printing CLI behavior unchanged). A new `app.py` (Flask) reuses every existing drawing/layout function unmodified, tracks a single in-memory job dict, runs generation in a background thread, and exposes `/`, `/generate`, `/progress`, `/download`. A single `templates/index.html` holds the form, progress bar, and polling JavaScript.

**Tech Stack:** Python 3, Pillow (existing), Flask (new), pytest + Flask's test client for tests.

## Global Constraints

- No changes to ticket drawing/layout logic — `draw_ticket`, `create_ticket_image`, `create_page`, `chunk_numbers` stay exactly as they are.
- `generate_all(config, on_progress=None)` — when `on_progress` is `None`, behavior is byte-for-byte the same as today (console prints); existing tests in `tests/test_generate_tickets.py` must keep passing unmodified.
- `on_progress(current, total, phase)` is called once per ticket saved (`phase="tickets"`) and once per page built (`phase="pages"`), 1-indexed.
- Form fields: Event Name, Event Date, Prizes (textarea, one per non-blank line), Start Number, End Number. `TOTAL_TICKETS = End Number - Start Number + 1`. No separate quantity field.
- Reject (400) if Event Name/Date missing, Start/End aren't whole numbers, or End < Start.
- Only one job runs at a time — a second `POST /generate` while `status == "running"` returns 409.
- Flask app binds to `127.0.0.1` only, `debug=False`.
- `GET /download` only serves the PDF once `status == "done"`; otherwise 409.
- Output paths unchanged: `OUTPUT_DIR/tickets/ticket_NNNNN.png`, `OUTPUT_DIR/tickets.pdf`.

---

### Task 1: Add progress-callback support to generate_all

**Files:**
- Modify: `generate_tickets.py:145-177` (the `generate_all` function)
- Test: `tests/test_generate_tickets.py` (append)

**Interfaces:**
- Consumes: existing `build_fonts`, `create_ticket_image`, `create_page`, `chunk_numbers` (unchanged).
- Produces: `generate_all(config: dict, on_progress: Callable[[int, int, str], None] | None = None) -> None`. When `on_progress` is given, it's called instead of printing, with `phase` being `"tickets"` or `"pages"`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_generate_tickets.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_generate_tickets.py -v -k reports_progress`
Expected: FAIL with `TypeError: generate_all() got an unexpected keyword argument 'on_progress'`

- [ ] **Step 3: Modify generate_all**

Replace the existing `generate_all` function in `generate_tickets.py` with:

```python
def generate_all(config, on_progress=None):
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
        if on_progress is not None:
            on_progress(i, total, "tickets")
        elif i % 500 == 0 or i == total:
            print(f"Generated {i}/{total} tickets...")

    page_chunks = chunk_numbers(start, total)
    num_pages = len(page_chunks)
    page_paths = []
    for page_num, numbers in enumerate(page_chunks, start=1):
        page_img = create_page(numbers, config, fonts)
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
```

- [ ] **Step 4: Run the new test and the full suite**

Run: `pytest tests/test_generate_tickets.py -v`
Expected: PASS (all 11 tests, including the pre-existing `test_generate_all_creates_expected_files` unmodified)

- [ ] **Step 5: Commit**

```bash
git add generate_tickets.py tests/test_generate_tickets.py
git commit -m "feat: add on_progress callback support to generate_all"
```

---

### Task 2: Flask web app (backend + form template)

**Files:**
- Create: `app.py`
- Create: `templates/index.html`
- Test: `tests/test_app.py`
- Modify: `requirements.txt` (add Flask)

**Interfaces:**
- Consumes: `generate_tickets.default_config()`, `generate_tickets.generate_all(config, on_progress)`, `generate_tickets.OUTPUT_DIR` from Task 1 and the existing module.
- Produces: a Flask app (`app.app`) with routes `GET /`, `POST /generate`, `GET /progress`, `GET /download`, and a module-level `JOB` dict.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_app.py`:

```python
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as flask_app_module


def wait_for_job(client, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = client.get("/progress").get_json()
        if data["status"] in ("done", "error"):
            return data
        time.sleep(0.05)
    raise TimeoutError("job did not finish in time")


def make_client(tmp_path, monkeypatch):
    monkeypatch.setattr(flask_app_module.gt, "OUTPUT_DIR", str(tmp_path))
    flask_app_module.app.config.update(TESTING=True)
    return flask_app_module.app.test_client()


def test_index_renders_form_fields(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    for field in ["event_name", "event_date", "prizes", "start_number", "end_number"]:
        assert f'name="{field}"' in body


def test_generate_rejects_end_before_start(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.post("/generate", data={
        "event_name": "Test Raffle",
        "event_date": "Jan 1, 2027",
        "prizes": "1st Prize: Test",
        "start_number": "10",
        "end_number": "5",
    })
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_generate_rejects_missing_event_name(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.post("/generate", data={
        "event_name": "",
        "event_date": "Jan 1, 2027",
        "prizes": "1st Prize: Test",
        "start_number": "1",
        "end_number": "3",
    })
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_generate_rejects_when_job_already_running(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    flask_app_module.JOB["status"] = "running"
    try:
        response = client.post("/generate", data={
            "event_name": "Test Raffle",
            "event_date": "Jan 1, 2027",
            "prizes": "1st Prize: Test",
            "start_number": "1",
            "end_number": "3",
        })
        assert response.status_code == 409
    finally:
        flask_app_module.JOB["status"] = "idle"


def test_download_without_completed_job_returns_409(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    flask_app_module.JOB["status"] = "idle"
    response = client.get("/download")
    assert response.status_code == 409


def test_generate_runs_job_and_download_serves_pdf(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.post("/generate", data={
        "event_name": "Test Raffle",
        "event_date": "Jan 1, 2027",
        "prizes": "1st Prize: Test\n2nd Prize: Test 2",
        "start_number": "1",
        "end_number": "3",
    })
    assert response.status_code == 202

    final_status = wait_for_job(client)
    assert final_status["status"] == "done"

    download_response = client.get("/download")
    assert download_response.status_code == 200
    assert download_response.content_type == "application/pdf"
    assert len(download_response.data) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'` (or `No module named 'flask'` if Flask isn't installed yet)

- [ ] **Step 3: Add Flask to requirements.txt**

Update `requirements.txt` to:

```
Pillow>=10.0.0
pytest>=7.0.0
Flask>=3.0.0
```

Run: `pip install -r requirements.txt`

- [ ] **Step 4: Create templates/index.html**

Create `templates/index.html`:

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Raffle Ticket Generator</title>
  <style>
    body { font-family: sans-serif; max-width: 480px; margin: 40px auto; }
    label { display: block; margin-top: 12px; font-weight: bold; }
    input, textarea { width: 100%; box-sizing: border-box; padding: 6px; margin-top: 4px; }
    textarea { height: 100px; }
    button { margin-top: 16px; padding: 10px 20px; }
    #progress-section { display: none; margin-top: 20px; }
    #error { color: red; margin-top: 12px; }
  </style>
</head>
<body>
  <h1>Raffle Ticket Generator</h1>
  <form id="ticket-form">
    <label for="event_name">Event Name</label>
    <input type="text" id="event_name" name="event_name" required>

    <label for="event_date">Event Date</label>
    <input type="text" id="event_date" name="event_date" required>

    <label for="prizes">Prizes (one per line)</label>
    <textarea id="prizes" name="prizes"></textarea>

    <label for="start_number">Start Number</label>
    <input type="number" id="start_number" name="start_number" required min="1">

    <label for="end_number">End Number</label>
    <input type="number" id="end_number" name="end_number" required min="1">

    <button type="submit">Generate</button>
  </form>

  <div id="error"></div>

  <div id="progress-section">
    <progress id="progress-bar" value="0" max="100"></progress>
    <p id="progress-text"></p>
  </div>

  <script>
    const form = document.getElementById("ticket-form");
    const errorDiv = document.getElementById("error");
    const progressSection = document.getElementById("progress-section");
    const progressBar = document.getElementById("progress-bar");
    const progressText = document.getElementById("progress-text");
    let pollTimer = null;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      errorDiv.textContent = "";

      const response = await fetch("/generate", {
        method: "POST",
        body: new FormData(form),
      });
      const data = await response.json();

      if (!response.ok) {
        errorDiv.textContent = data.error || "Something went wrong.";
        return;
      }

      progressSection.style.display = "block";
      pollTimer = setInterval(pollProgress, 1000);
    });

    async function pollProgress() {
      const response = await fetch("/progress");
      const data = await response.json();

      if (data.status === "running") {
        const pct = data.total > 0 ? Math.round((data.current / data.total) * 100) : 0;
        progressBar.value = pct;
        const label = data.phase === "pages" ? "Building pages" : "Generating tickets";
        progressText.textContent = `${label}... ${data.current}/${data.total}`;
      } else if (data.status === "done") {
        clearInterval(pollTimer);
        progressText.textContent = "Done! Downloading PDF...";
        window.location = "/download";
      } else if (data.status === "error") {
        clearInterval(pollTimer);
        errorDiv.textContent = data.error;
      }
    }
  </script>
</body>
</html>
```

- [ ] **Step 5: Create app.py**

Create `app.py`:

```python
import os
import threading

from flask import Flask, jsonify, render_template, request, send_file

import generate_tickets as gt

app = Flask(__name__)

JOB = {
    "status": "idle",  # idle | running | done | error
    "phase": "",
    "current": 0,
    "total": 0,
    "error": None,
}


def run_job(config):
    def on_progress(current, total, phase):
        JOB["phase"] = phase
        JOB["current"] = current
        JOB["total"] = total

    try:
        gt.generate_all(config, on_progress=on_progress)
        JOB["status"] = "done"
    except Exception as exc:
        JOB["status"] = "error"
        JOB["error"] = str(exc)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    if JOB["status"] == "running":
        return jsonify({"error": "A generation job is already running."}), 409

    event_name = request.form.get("event_name", "").strip()
    event_date = request.form.get("event_date", "").strip()
    prizes = [
        line.strip()
        for line in request.form.get("prizes", "").splitlines()
        if line.strip()
    ]

    if not event_name or not event_date:
        return jsonify({"error": "Event name and date are required."}), 400

    try:
        start_number = int(request.form.get("start_number", ""))
        end_number = int(request.form.get("end_number", ""))
    except ValueError:
        return jsonify({"error": "Start and end number must be whole numbers."}), 400

    if end_number < start_number:
        return jsonify({"error": "End number must be greater than or equal to start number."}), 400

    config = gt.default_config()
    config["EVENT_NAME"] = event_name
    config["EVENT_DATE"] = event_date
    config["PRIZES"] = prizes
    config["START_NUMBER"] = start_number
    config["TOTAL_TICKETS"] = end_number - start_number + 1

    JOB.update({"status": "running", "phase": "", "current": 0, "total": 0, "error": None})
    threading.Thread(target=run_job, args=(config,), daemon=True).start()

    return jsonify({"status": "started"}), 202


@app.route("/progress")
def progress():
    return jsonify(JOB)


@app.route("/download")
def download():
    if JOB["status"] != "done":
        return jsonify({"error": "No completed job to download."}), 409
    pdf_path = os.path.join(gt.OUTPUT_DIR, "tickets.pdf")
    return send_file(pdf_path, as_attachment=True, download_name="tickets.pdf")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_app.py -v`
Expected: PASS (6 passed)

- [ ] **Step 7: Run the full test suite**

Run: `pytest -v`
Expected: PASS (all tests in `tests/test_generate_tickets.py` and `tests/test_app.py`)

- [ ] **Step 8: Commit**

```bash
git add app.py templates/index.html requirements.txt tests/test_app.py
git commit -m "feat: add Flask web UI with progress bar and PDF auto-download"
```

---

### Task 3: README update and manual end-to-end smoke test

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `app.py` from Task 2.
- Produces: updated usage docs; no new code interfaces.

- [ ] **Step 1: Update README.md**

Add a new section to `README.md`, after the existing "## Run" section:

```markdown
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
```

- [ ] **Step 2: Manual smoke test**

Run: `python app.py`, then open `http://127.0.0.1:5000` in a browser.

Fill in:
- Event Name: `Smoke Test Raffle`
- Event Date: `Jan 1, 2027`
- Prizes: `1st Prize: Test\n2nd Prize: Test 2` (two lines)
- Start Number: `1`
- End Number: `20`

Click Generate.

Expected: the progress bar appears and updates roughly once per second
through "Generating tickets... X/20" then "Building pages... X/2"; the
browser then downloads `tickets.pdf`. Open it and confirm 2 pages of 10
tickets each, with the entered event name/date/prizes and a dashed
main/stub divider on each ticket. Stop the server with Ctrl+C.

- [ ] **Step 3: Run the full automated test suite one more time**

Run: `pytest -v`
Expected: PASS (all tests)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document the web UI usage"
```
