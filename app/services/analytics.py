"""Dashboard aggregates over stored evaluations, computed in SQL."""

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.filters import CallFilters
from app.models import CallEvaluation
from app.schemas import (
    AgentStat,
    DashboardAnalytics,
    DashboardMetrics,
    LeadTemperature,
    LeadTemperatureCount,
    ScoreTrendPoint,
    ServiceTypeStat,
)

LOW_SCORE_THRESHOLD = 60

_calls = func.count(CallEvaluation.id)
_avg_score = func.avg(CallEvaluation.overall_score)
_booked = func.sum(case((CallEvaluation.appointment_booked.is_(True), 1), else_=0))


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 1)


def _percent(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def compute_metrics(db: Session, filters: CallFilters) -> DashboardMetrics:
    """Headline numbers for the calls matching `filters`."""
    open_lead = CallEvaluation.lead_temperature.in_([LeadTemperature.HOT.value, LeadTemperature.WARM.value])
    query = filters.apply(
        select(
            _calls,
            _avg_score,
            func.sum(case((CallEvaluation.lead_temperature == LeadTemperature.HOT.value, 1), else_=0)),
            _booked,
            func.sum(case((open_lead & CallEvaluation.appointment_booked.is_(False), 1), else_=0)),
            func.sum(case((CallEvaluation.overall_score < LOW_SCORE_THRESHOLD, 1), else_=0)),
        )
    )
    total, average, hot, booked, follow_ups, low = db.execute(query).one()
    booked = booked or 0
    return DashboardMetrics(
        total_calls=total,
        average_score=_round(average),
        hot_leads=hot or 0,
        appointments_booked=booked,
        booking_rate=_percent(booked, total),
        follow_ups_needed=follow_ups or 0,
        low_score_calls=low or 0,
    )


def compute_analytics(db: Session, filters: CallFilters) -> DashboardAnalytics:
    """Chart breakdowns (trend, services, lead mix, agents) for the calls matching `filters`."""
    trend = db.execute(
        filters.apply(select(CallEvaluation.call_date, _calls, _avg_score))
        .group_by(CallEvaluation.call_date)
        .order_by(CallEvaluation.call_date)
    ).all()

    services = db.execute(
        filters.apply(select(CallEvaluation.service_type, _calls, _avg_score))
        .group_by(CallEvaluation.service_type)
        .order_by(_calls.desc(), CallEvaluation.service_type)
    ).all()

    temperature_counts = dict(
        db.execute(
            filters.apply(select(CallEvaluation.lead_temperature, _calls)).group_by(CallEvaluation.lead_temperature)
        ).all()
    )

    agents = db.execute(
        filters.apply(select(CallEvaluation.agent_name, _calls, _avg_score, _booked))
        .group_by(CallEvaluation.agent_name)
        .order_by(_avg_score.desc(), CallEvaluation.agent_name)
    ).all()

    return DashboardAnalytics(
        score_trend=[ScoreTrendPoint(call_date=d, calls=n, average_score=_round(avg)) for d, n, avg in trend],
        calls_by_service_type=[
            ServiceTypeStat(service_type=s, calls=n, average_score=_round(avg)) for s, n, avg in services
        ],
        lead_temperature_distribution=[
            LeadTemperatureCount(lead_temperature=t, calls=temperature_counts.get(t.value, 0)) for t in LeadTemperature
        ],
        calls_by_agent=[
            AgentStat(
                agent_name=name,
                calls=n,
                average_score=_round(avg),
                appointments_booked=booked or 0,
                booking_rate=_percent(booked or 0, n),
            )
            for name, n, avg, booked in agents
        ],
    )
