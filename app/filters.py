"""Query filters shared by the evaluation list and the dashboard endpoints."""

from datetime import date

from fastapi import Query
from sqlalchemy import Select

from app.models import CallEvaluation
from app.schemas import BusinessType, LeadTemperature


class CallFilters:
    """FastAPI dependency: optional filters applied to call_evaluations queries."""

    def __init__(
        self,
        start_date: date | None = Query(None, description="Earliest call date (inclusive)"),
        end_date: date | None = Query(None, description="Latest call date (inclusive)"),
        agent_name: str | None = Query(None, description="Case-insensitive partial match"),
        business_type: BusinessType | None = None,
        service_type: str | None = Query(None, description="Exact match, e.g. 'AC repair'"),
        lead_temperature: LeadTemperature | None = None,
        appointment_booked: bool | None = None,
        min_score: int | None = Query(None, ge=0, le=100, description="Minimum overall score"),
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.agent_name = agent_name.strip() if agent_name else None
        self.business_type = business_type
        self.service_type = service_type
        self.lead_temperature = lead_temperature
        self.appointment_booked = appointment_booked
        self.min_score = min_score

    def apply(self, query: Select) -> Select:
        if self.start_date:
            query = query.where(CallEvaluation.call_date >= self.start_date)
        if self.end_date:
            query = query.where(CallEvaluation.call_date <= self.end_date)
        if self.agent_name:
            query = query.where(CallEvaluation.agent_name.ilike(f"%{self.agent_name}%"))
        if self.business_type:
            query = query.where(CallEvaluation.business_type == self.business_type.value)
        if self.service_type:
            query = query.where(CallEvaluation.service_type == self.service_type)
        if self.lead_temperature:
            query = query.where(CallEvaluation.lead_temperature == self.lead_temperature.value)
        if self.appointment_booked is not None:
            query = query.where(CallEvaluation.appointment_booked == self.appointment_booked)
        if self.min_score is not None:
            query = query.where(CallEvaluation.overall_score >= self.min_score)
        return query
