"""Coaching endpoint: recurring rubric gaps across calls and per-agent focus areas."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.filters import CallFilters
from app.models import CallEvaluation, RubricScore
from app.schemas import CoachingInsights, RubricCategory
from app.services.coaching import ScoreRow, build_insights

router = APIRouter(prefix="/api/coaching", tags=["coaching"])


@router.get("/insights", response_model=CoachingInsights, summary="Recurring gaps and per-agent coaching focus")
def coaching_insights(filters: CallFilters = Depends(), db: Session = Depends(get_db)) -> CoachingInsights:
    query = filters.apply(
        select(
            CallEvaluation.id,
            CallEvaluation.call_date,
            CallEvaluation.agent_name,
            CallEvaluation.overall_score,
            RubricScore.category,
            RubricScore.score,
            RubricScore.feedback,
        ).join(RubricScore, RubricScore.evaluation_id == CallEvaluation.id)
    ).order_by(CallEvaluation.call_date.desc(), CallEvaluation.id.desc(), RubricScore.id)
    rows = [
        ScoreRow(cid, call_date, agent, overall, RubricCategory(category), score, feedback)
        for cid, call_date, agent, overall, category, score, feedback in db.execute(query)
    ]
    return build_insights(rows)
