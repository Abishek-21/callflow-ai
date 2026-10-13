"""Dashboard endpoints, checked against aggregates computed directly in Python."""

from statistics import mean

import pytest

from app.database import SessionLocal
from app.seed_data import SEED_CALLS
from app.services.mock_evaluator import evaluate_transcript_mock
from app.services.seeding import seed_demo_data

EXPECTED = [
    {**c, "result": evaluate_transcript_mock(c["transcript"], c["business_type"], c["agent_name"])}
    for c in SEED_CALLS
]


@pytest.fixture
def seeded(client):
    with SessionLocal() as db:
        seed_demo_data(db, shift_dates=False)
    return client


def expected_metrics(calls):
    scores = [c["result"].overall_score for c in calls]
    booked = [c for c in calls if c["result"].appointment_booked]
    return {
        "total_calls": len(calls),
        "average_score": round(mean(scores), 1),
        "hot_leads": sum(c["result"].lead_temperature.value == "Hot" for c in calls),
        "appointments_booked": len(booked),
        "booking_rate": round(100 * len(booked) / len(calls), 1),
        "follow_ups_needed": sum(
            c["result"].lead_temperature.value in ("Hot", "Warm") and not c["result"].appointment_booked
            for c in calls
        ),
        "low_score_calls": sum(s < 60 for s in scores),
    }


def test_metrics_on_empty_database(client):
    assert client.get("/api/dashboard/metrics").json() == {
        "total_calls": 0,
        "average_score": None,
        "hot_leads": 0,
        "appointments_booked": 0,
        "booking_rate": None,
        "follow_ups_needed": 0,
        "low_score_calls": 0,
    }


def test_metrics_match_python_aggregates(seeded):
    assert seeded.get("/api/dashboard/metrics").json() == expected_metrics(EXPECTED)


@pytest.mark.parametrize(
    ("params", "keep"),
    [
        ({"agent_name": "jake"}, lambda c: c["agent_name"] == "Jake Miller"),
        ({"business_type": "HVAC"}, lambda c: c["business_type"].value == "HVAC"),
        ({"start_date": "2026-10-01", "end_date": "2026-10-07"}, lambda c: "2026-10-01" <= c["call_date"].isoformat() <= "2026-10-07"),
        ({"min_score": 80}, lambda c: c["result"].overall_score >= 80),
    ],
)
def test_metrics_respect_filters(seeded, params, keep):
    assert seeded.get("/api/dashboard/metrics", params=params).json() == expected_metrics(list(filter(keep, EXPECTED)))


def test_metrics_reject_invalid_filters(client):
    assert client.get("/api/dashboard/metrics", params={"min_score": 101}).status_code == 422
    assert client.get("/api/dashboard/analytics", params={"lead_temperature": "Lukewarm"}).status_code == 422


def test_analytics_breakdowns(seeded):
    body = seeded.get("/api/dashboard/analytics").json()

    trend = body["score_trend"]
    assert [p["call_date"] for p in trend] == sorted({c["call_date"].isoformat() for c in EXPECTED})
    first_day = [c for c in EXPECTED if c["call_date"].isoformat() == trend[0]["call_date"]]
    assert trend[0]["calls"] == len(first_day)
    assert trend[0]["average_score"] == round(mean(c["result"].overall_score for c in first_day), 1)

    services = body["calls_by_service_type"]
    assert sum(s["calls"] for s in services) == len(EXPECTED)
    assert [s["calls"] for s in services] == sorted((s["calls"] for s in services), reverse=True)
    assert {s["service_type"] for s in services} == {c["result"].service_type for c in EXPECTED}

    temps = body["lead_temperature_distribution"]
    assert [t["lead_temperature"] for t in temps] == ["Hot", "Warm", "Cold"]
    for t in temps:
        assert t["calls"] == sum(c["result"].lead_temperature.value == t["lead_temperature"] for c in EXPECTED)

    agents = body["calls_by_agent"]
    assert [a["average_score"] for a in agents] == sorted((a["average_score"] for a in agents), reverse=True)
    maya = next(a for a in agents if a["agent_name"] == "Maya Torres")
    maya_calls = [c for c in EXPECTED if c["agent_name"] == "Maya Torres"]
    assert maya["calls"] == len(maya_calls)
    assert maya["appointments_booked"] == sum(c["result"].appointment_booked for c in maya_calls)
    assert agents[0]["agent_name"] == "Maya Torres" and agents[-1]["agent_name"] == "Jake Miller"


def test_analytics_on_empty_database(client):
    body = client.get("/api/dashboard/analytics").json()
    assert body["score_trend"] == [] and body["calls_by_service_type"] == [] and body["calls_by_agent"] == []
    assert [t["calls"] for t in body["lead_temperature_distribution"]] == [0, 0, 0]


def test_dashboard_endpoints_in_docs(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/api/dashboard/metrics", "/api/dashboard/analytics"} <= set(paths)
