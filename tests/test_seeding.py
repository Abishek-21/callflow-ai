from datetime import date

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import CallEvaluation, RubricScore
from app.seed_data import SEED_CALLS
from app.services.mock_evaluator import evaluate_transcript_mock
from app.services.seeding import seed_demo_data
from scripts import seed_demo


def counts():
    with SessionLocal() as db:
        return db.scalar(select(func.count(CallEvaluation.id))), db.scalar(select(func.count(RubricScore.id)))


def test_seed_adds_all_calls_once(client):
    with SessionLocal() as db:
        assert seed_demo_data(db) == len(SEED_CALLS)
        assert seed_demo_data(db) == 0  # already populated: no duplicates
    assert counts() == (len(SEED_CALLS), len(SEED_CALLS) * 9)


def test_reset_replaces_existing_rows_without_orphans(client):
    client.post(
        "/api/evaluations",
        json={"transcript": SEED_CALLS[0]["transcript"], "agent_name": "Someone Else"},
    )
    with SessionLocal() as db:
        assert seed_demo_data(db, reset=True) == len(SEED_CALLS)
        agents = set(db.scalars(select(CallEvaluation.agent_name)))
    assert "Someone Else" not in agents
    assert counts() == (len(SEED_CALLS), len(SEED_CALLS) * 9)


def test_dates_shift_so_newest_call_is_today(client):
    with SessionLocal() as db:
        seed_demo_data(db)
        newest = db.scalar(select(func.max(CallEvaluation.call_date)))
        oldest = db.scalar(select(func.min(CallEvaluation.call_date)))
    original = sorted(c["call_date"] for c in SEED_CALLS)
    assert newest == date.today()
    assert newest - oldest == original[-1] - original[0]


def test_keep_dates(client):
    with SessionLocal() as db:
        seed_demo_data(db, shift_dates=False)
        dates = set(db.scalars(select(CallEvaluation.call_date)))
    assert dates == {c["call_date"] for c in SEED_CALLS}


def test_demo_dataset_covers_every_dashboard_dimension():
    results = [evaluate_transcript_mock(c["transcript"], c["business_type"], c["agent_name"]) for c in SEED_CALLS]
    scores = [r.overall_score for r in results]
    assert len({c["key"] for c in SEED_CALLS}) == len(SEED_CALLS)
    assert len({c["agent_name"] for c in SEED_CALLS}) >= 4
    assert {c["business_type"].value for c in SEED_CALLS} == {"Roofing", "HVAC", "Plumbing", "Generic Home Services"}
    assert {r.lead_temperature.value for r in results} == {"Hot", "Warm", "Cold"}
    assert min(scores) < 40 and max(scores) > 90
    assert any(r.appointment_booked for r in results) and not all(r.appointment_booked for r in results)
    assert len({r.service_type for r in results}) >= 8


def test_cli(client, capsys):
    seed_demo.main([])
    assert f"Added {len(SEED_CALLS)} demo calls" in capsys.readouterr().out
    seed_demo.main([])
    assert "nothing added" in capsys.readouterr().out
    seed_demo.main(["--reset", "--keep-dates"])
    assert f"Added {len(SEED_CALLS)} demo calls" in capsys.readouterr().out


def test_startup_seeds_empty_database_when_enabled(monkeypatch):
    from fastapi.testclient import TestClient

    from app import config
    from app.database import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    monkeypatch.setattr(config, "SEED_DEMO_DATA", True)
    with TestClient(app) as client:
        assert client.get("/api/dashboard/metrics").json()["total_calls"] == len(SEED_CALLS)
    with TestClient(app) as client:  # second startup: already populated, nothing added
        assert client.get("/api/dashboard/metrics").json()["total_calls"] == len(SEED_CALLS)


def test_startup_does_not_seed_by_default(client):
    assert client.get("/api/dashboard/metrics").json()["total_calls"] == 0
