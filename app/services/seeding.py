"""Load the demo dataset (app.seed_data) into the database.

Demo calls are scored with the mock evaluator so seeding is instant, free, and
deterministic (no API key or rate limits involved). They are stored with
evaluation_mode "mock" so the UI labels them honestly.
"""

from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import CallEvaluation, RubricScore
from app.routers.evaluations import save_evaluation
from app.schemas import EvaluationRequest
from app.seed_data import SEED_CALLS
from app.services.evaluator import EvaluationOutcome
from app.services.mock_evaluator import evaluate_transcript_mock


def date_shift(today: date | None = None) -> timedelta:
    """Offset that moves the newest demo call to `today`, keeping the spacing between calls."""
    return (today or date.today()) - max(c["call_date"] for c in SEED_CALLS)


def seed_demo_data(db: Session, *, reset: bool = False, shift_dates: bool = True) -> int:
    """Insert the demo calls. Returns how many were added.

    Without `reset`, does nothing if the database already has evaluations. With
    `shift_dates`, call dates move so the newest demo call lands on today, which
    keeps "last 7 days" style views populated whenever the demo is run.
    """
    if reset:
        # Bulk deletes skip ORM cascades (and SQLite doesn't enforce foreign keys), so clear both tables.
        db.execute(delete(RubricScore))
        db.execute(delete(CallEvaluation))
        db.commit()
    elif db.scalar(select(func.count(CallEvaluation.id))):
        return 0

    shift = date_shift() if shift_dates else timedelta(0)
    for call in sorted(SEED_CALLS, key=lambda c: c["call_date"]):
        request = EvaluationRequest(
            transcript=call["transcript"],
            business_type=call["business_type"],
            agent_name=call["agent_name"],
            call_date=call["call_date"] + shift,
        )
        result = evaluate_transcript_mock(request.transcript, request.business_type, request.agent_name)
        save_evaluation(db, request, EvaluationOutcome(result=result, mode="mock"))
    return len(SEED_CALLS)
