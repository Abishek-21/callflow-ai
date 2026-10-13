from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import CallEvaluation, RubricScore
from app.sample_data import DEMO_CALLS
from app.schemas import EvaluationRequest, EvaluationResult
from app.services.mock_evaluator import evaluate_transcript_mock


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_evaluation_round_trips_through_database(db):
    call = DEMO_CALLS[0]
    result = evaluate_transcript_mock(call["transcript"], call["business_type"], call["agent_name"])
    data = result.model_dump(mode="json", exclude={"rubric_scores"})
    row = CallEvaluation(
        call_date=call["call_date"],
        agent_name=call["agent_name"],
        business_type=call["business_type"].value,
        transcript=call["transcript"],
        evaluation_mode="mock",
        **data,
        rubric_scores=[
            RubricScore(category=r.category.value, score=r.score, feedback=r.feedback)
            for r in result.rubric_scores
        ],
    )
    db.add(row)
    db.commit()

    saved = db.scalars(select(CallEvaluation)).one()
    assert saved.created_at is not None
    assert saved.call_date == date(2026, 9, 28)
    assert saved.strengths == result.strengths  # JSON list column
    assert len(saved.rubric_scores) == 9

    db.delete(saved)
    db.commit()
    assert db.scalars(select(RubricScore)).all() == []  # rubric rows cascade


def test_result_rejects_incomplete_rubric_and_recomputes_overall():
    call = DEMO_CALLS[0]
    data = evaluate_transcript_mock(call["transcript"], call["business_type"], call["agent_name"]).model_dump()

    data["overall_score"] = 12  # disagrees with the rubric; validator corrects it
    assert EvaluationResult(**data).overall_score == 98

    data["rubric_scores"] = data["rubric_scores"][:-1]
    with pytest.raises(ValidationError, match="missing categories"):
        EvaluationResult(**data)


def test_request_validation():
    with pytest.raises(ValidationError):
        EvaluationRequest(transcript="too short", agent_name="Maya")
    with pytest.raises(ValidationError):
        EvaluationRequest(transcript="x" * 60, agent_name="   ")
    req = EvaluationRequest(transcript="x" * 60, agent_name=" Maya ", business_type="HVAC")
    assert req.agent_name == "Maya"
    assert req.call_date is None
