"""Transcript evaluation endpoints: create, list (with filters), and fetch one."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.filters import CallFilters
from app.models import CallEvaluation, RubricScore
from app.schemas import EvaluationCreated, EvaluationRead, EvaluationRequest, EvaluationSummary
from app.services.evaluator import EvaluationOutcome, run_evaluation

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


def save_evaluation(db: Session, request: EvaluationRequest, outcome: EvaluationOutcome) -> CallEvaluation:
    result = outcome.result
    row = CallEvaluation(
        call_date=request.call_date or date.today(),
        agent_name=request.agent_name,
        business_type=request.business_type.value,
        transcript=request.transcript,
        evaluation_mode=outcome.mode,
        **result.model_dump(mode="json", exclude={"rubric_scores"}),
        rubric_scores=[
            RubricScore(category=r.category.value, score=r.score, feedback=r.feedback)
            for r in result.rubric_scores
        ],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("", response_model=EvaluationCreated, status_code=201, summary="Evaluate and store a transcript")
def create_evaluation(request: EvaluationRequest, db: Session = Depends(get_db)) -> EvaluationCreated:
    outcome = run_evaluation(request)
    row = save_evaluation(db, request, outcome)
    return EvaluationCreated.model_validate(row).model_copy(update={"notice": outcome.notice})


@router.get("", response_model=list[EvaluationSummary], summary="List evaluations (newest call first)")
def list_evaluations(
    filters: CallFilters = Depends(),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[CallEvaluation]:
    query = filters.apply(select(CallEvaluation))
    query = query.order_by(CallEvaluation.call_date.desc(), CallEvaluation.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(query))


@router.get("/{evaluation_id}", response_model=EvaluationRead, summary="Get one evaluation with rubric and follow-ups")
def get_evaluation(evaluation_id: int, db: Session = Depends(get_db)) -> CallEvaluation:
    row = db.scalar(
        select(CallEvaluation)
        .options(selectinload(CallEvaluation.rubric_scores))
        .where(CallEvaluation.id == evaluation_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Evaluation {evaluation_id} not found")
    return row
