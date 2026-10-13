from datetime import date

import pytest

from app.sample_data import DEMO_CALLS

DEMOS = {c["key"]: c for c in DEMO_CALLS}


def payload(key, **overrides):
    c = DEMOS[key]
    body = {
        "transcript": c["transcript"],
        "business_type": c["business_type"].value,
        "agent_name": c["agent_name"],
        "call_date": c["call_date"].isoformat(),
    }
    return {**body, **overrides}


@pytest.fixture
def seeded(client):
    """Store all three demo calls; return {key: created evaluation}."""
    return {key: client.post("/api/evaluations", json=payload(key)).json() for key in DEMOS}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "evaluation_mode": "mock", "provider": None, "model": None}


def test_swagger_docs_available(client):
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/api/evaluations", "/api/evaluations/{evaluation_id}", "/health"} <= set(paths)


def test_create_evaluation(client):
    resp = client.post("/api/evaluations", json=payload("roofing_strong"))
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] > 0
    assert body["evaluation_mode"] == "mock"
    assert body["notice"] is None
    assert body["call_date"] == "2026-09-28"
    assert body["business_type"] == "Roofing"
    assert body["customer_name"] == "Dana Whitfield"
    assert body["appointment_booked"] is True
    assert body["overall_score"] == 98
    assert len(body["rubric_scores"]) == 9
    assert body["sms_follow_up"] and body["email_follow_up"] and body["crm_note"]


def test_call_date_defaults_to_today(client):
    body = client.post("/api/evaluations", json=payload("hvac_weak", call_date=None)).json()
    assert body["call_date"] == date.today().isoformat()


@pytest.mark.parametrize(
    "overrides",
    [
        {"transcript": "Too short to evaluate."},
        {"agent_name": ""},
        {"business_type": "Landscaping"},
        {"call_date": "not-a-date"},
    ],
)
def test_create_rejects_invalid_input(client, overrides):
    assert client.post("/api/evaluations", json=payload("roofing_strong", **overrides)).status_code == 422


def test_get_evaluation_by_id(client, seeded):
    created = seeded["plumbing_objection"]
    resp = client.get(f"/api/evaluations/{created['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript"] == DEMOS["plumbing_objection"]["transcript"].strip()
    assert body["rubric_scores"] == created["rubric_scores"]
    assert body["overall_score"] == created["overall_score"]
    assert "notice" not in body


def test_get_missing_evaluation_returns_404(client):
    resp = client.get("/api/evaluations/9999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_list_is_newest_call_first(client, seeded):
    rows = client.get("/api/evaluations").json()
    assert [r["call_date"] for r in rows] == ["2026-10-03", "2026-10-01", "2026-09-28"]
    assert "transcript" not in rows[0]  # summaries only


@pytest.mark.parametrize(
    ("params", "expected_agents"),
    [
        ({"lead_temperature": "Hot"}, {"Maya Torres", "Jake Miller"}),
        ({"appointment_booked": "true"}, {"Maya Torres"}),
        ({"appointment_booked": "false"}, {"Jake Miller", "Priya Shah"}),
        ({"min_score": 80}, {"Maya Torres", "Priya Shah"}),
        ({"agent_name": "jake"}, {"Jake Miller"}),
        ({"business_type": "Plumbing"}, {"Priya Shah"}),
        ({"service_type": "AC repair"}, {"Jake Miller"}),
        ({"start_date": "2026-10-01"}, {"Jake Miller", "Priya Shah"}),
        ({"end_date": "2026-10-01"}, {"Maya Torres", "Jake Miller"}),
        ({"start_date": "2026-10-01", "end_date": "2026-10-01"}, {"Jake Miller"}),
        ({"lead_temperature": "Cold"}, set()),
    ],
)
def test_list_filters(client, seeded, params, expected_agents):
    resp = client.get("/api/evaluations", params=params)
    assert resp.status_code == 200
    assert {r["agent_name"] for r in resp.json()} == expected_agents


def test_list_pagination(client, seeded):
    first = client.get("/api/evaluations", params={"limit": 2}).json()
    rest = client.get("/api/evaluations", params={"limit": 2, "offset": 2}).json()
    assert len(first) == 2 and len(rest) == 1
    assert {r["id"] for r in first}.isdisjoint({r["id"] for r in rest})


def test_list_rejects_invalid_filters(client):
    assert client.get("/api/evaluations", params={"min_score": 101}).status_code == 422
    assert client.get("/api/evaluations", params={"lead_temperature": "Lukewarm"}).status_code == 422
