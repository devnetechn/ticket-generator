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
