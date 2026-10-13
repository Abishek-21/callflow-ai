"""Headless tests of the Streamlit Evaluate page, with the HTTP API faked in-process."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from frontend import api_client, ui
from frontend.views import evaluate as evaluate_view

APP = str(Path(__file__).resolve().parents[1] / "frontend" / "streamlit_app.py")


@pytest.fixture
def fake_api(monkeypatch):
    """Route the frontend's API calls to a FastAPI TestClient instead of HTTP."""
    calls = []

    def create_evaluation(payload):
        calls.append(payload)
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as client:
            resp = client.post("/api/evaluations", json=payload)
        if resp.status_code >= 400:
            raise api_client.ApiError(f"API error {resp.status_code}")
        return resp.json()

    ui.backend_health.clear()
    monkeypatch.setattr(api_client, "health", lambda: {"status": "ok", "evaluation_mode": "mock"})
    monkeypatch.setattr(api_client, "create_evaluation", create_evaluation)
    return calls


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()


def test_demo_evaluation_renders_result(client, fake_api):
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert "Mock evaluation mode" in at.info[0].value

    at.button(key="demo_roofing_strong").click().run()
    assert at.text_input(key="eval_agent").value == "Maya Torres"
    assert at.selectbox(key="eval_business_type").value == "Roofing"

    click(at, "Evaluate call")
    assert not at.exception
    assert not at.error
    assert fake_api[0]["agent_name"] == "Maya Torres"
    assert fake_api[0]["call_date"] == "2026-09-28"
    assert [t.label for t in at.tabs] == ["Scorecard", "CRM record", "Follow-ups", "Transcript"]
    areas = {t.label: t.value for t in at.text_area}
    assert {"CRM note", "SMS", "Email body"} <= set(areas)
    assert areas["SMS"].startswith("Hi Dana")


def test_validation_blocks_empty_submission(client, fake_api):
    at = AppTest.from_file(APP, default_timeout=30).run()
    click(at, "Evaluate call")
    assert "at least" in at.error[0].value
    assert fake_api == []


def test_offline_backend_disables_evaluate(monkeypatch):
    ui.backend_health.clear()
    monkeypatch.setattr(api_client, "health", lambda: None)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert "Can't reach the CallFlow API" in at.error[0].value
    assert next(b for b in at.button if b.label == "Evaluate call").disabled


def test_copy_button_payload_cannot_break_out_of_script(monkeypatch):
    captured = {}
    monkeypatch.setattr(ui.st, "iframe", lambda src, **kw: captured.setdefault("html", src))
    ui.copy_button('</script><img src=x onerror=alert(1)> "quotes"', "Copy")
    script = captured["html"].split("<script>", 1)[1]
    assert "</script><img" not in script
    assert "\\u003c/script>" in script


def test_min_transcript_length_matches_api():
    from app.schemas import EvaluationRequest

    assert evaluate_view.MIN_TRANSCRIPT_CHARS == EvaluationRequest.model_fields["transcript"].metadata[0].min_length


# --- History and dashboard pages ------------------------------------------------

VIEW_SCRIPT = """
from frontend import ui
from frontend.views import {view}
ui.inject_css()
{view}.render()
"""


@pytest.fixture
def live_api(client, monkeypatch):
    """Send every frontend API call to the FastAPI app in-process, with demo data loaded."""
    from app.database import SessionLocal
    from app.services.seeding import seed_demo_data

    with SessionLocal() as db:
        seed_demo_data(db, shift_dates=True)

    def request(method, path, timeout=15, **kwargs):
        resp = client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            raise api_client.ApiError(api_client._error_message(resp))
        return resp.json()

    ui.backend_health.clear()
    monkeypatch.setattr(api_client, "_request", request)
    return client


def view(name):
    return AppTest.from_string(VIEW_SCRIPT.format(view=name), default_timeout=30)


def test_history_lists_calls_and_filters(live_api):
    from app.seed_data import SEED_CALLS

    at = view("history").run()
    assert not at.exception
    assert len(at.dataframe[0].value) == len(SEED_CALLS)

    at.selectbox(key="hist_agent").select("Jake Miller").run()
    table = at.dataframe[0].value
    assert set(table["Agent"]) == {"Jake Miller"}

    at.selectbox(key="hist_booked").select("Booked").run()
    assert "No calls match these filters." in at.info[-1].value

    at.button(key=next(b.key for b in at.button if b.label == "Reset")).click().run()
    assert len(at.dataframe[0].value) == len(SEED_CALLS)


def test_history_opens_call_from_url(live_api):
    target = live_api.get("/api/evaluations", params={"agent_name": "Maya", "limit": 1}).json()[0]
    at = view("history")
    at.query_params["id"] = str(target["id"])
    at.run()
    assert not at.exception
    assert any(f"Call #{target['id']}" in s.value for s in at.subheader)
    assert [t.label for t in at.tabs] == ["Scorecard", "CRM record", "Follow-ups", "Transcript"]


def test_history_unknown_call_shows_warning(live_api):
    at = view("history")
    at.query_params["id"] = "99999"
    at.run()
    assert "not found" in at.warning[0].value


def test_dashboard_shows_metrics_and_tables(live_api):
    at = view("dashboard").run()
    assert not at.exception
    metrics = live_api.get("/api/dashboard/metrics").json()
    page_html = " ".join(h.value for h in at.get("html"))
    assert "Calls evaluated" in page_html and f">{metrics['total_calls']}<" in page_html
    agents, recent = at.dataframe
    assert len(agents.value) == 4
    assert len(recent.value) == 10


def test_dashboard_empty_state(client, monkeypatch):
    def request(method, path, timeout=15, **kwargs):
        return client.request(method, path, **kwargs).json()

    ui.backend_health.clear()
    monkeypatch.setattr(api_client, "_request", request)
    at = view("dashboard").run()
    assert not at.exception
    assert "No calls in this period" in at.info[-1].value


def test_dashboard_renders_charts(live_api):
    at = view("dashboard").run()
    assert not at.exception
    charts = at.get("vega_lite_chart")
    assert len(charts) == 3  # score trend, lead temperature, service type


def test_coaching_page(live_api):
    at = view("coaching").run()
    assert not at.exception
    page = " ".join(m.value for m in at.markdown)
    assert "Value communication" in page or "Lead qualification" in page  # top recurring gaps on demo data
    assert "#### Jake Miller" in page and "#### Maya Torres" in page
    assert len(at.get("vega_lite_chart")) == 1  # heatmap

    at.selectbox(key="coach_agent").select("Maya Torres").run()
    assert not at.exception
    page = " ".join(m.value for m in at.markdown)
    assert "#### Maya Torres" in page and "#### Jake Miller" not in page
    assert "No recurring gaps" in at.success[0].value


def test_coaching_empty_state(client, monkeypatch):
    def request(method, path, timeout=15, **kwargs):
        return client.request(method, path, **kwargs).json()

    ui.backend_health.clear()
    monkeypatch.setattr(api_client, "_request", request)
    at = view("coaching").run()
    assert not at.exception
    assert "No calls in this period" in at.info[-1].value


def test_rolling_average_is_call_weighted_over_calendar_days():
    from frontend.charts import _rolling_average

    points = [
        {"call_date": "2026-10-01", "calls": 1, "average_score": 90},
        {"call_date": "2026-10-02", "calls": 3, "average_score": 50},  # weighted 3x
        {"call_date": "2026-10-10", "calls": 1, "average_score": 20},  # 10-01 and 10-02 are outside its 7 days
    ]
    rolling = list(_rolling_average(points, days=7)["rolling_average"])
    assert rolling == [90, (90 + 3 * 50) / 4, 20]
