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
