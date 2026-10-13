"""Pydantic schemas: API request/response shapes and the structured evaluation result.

EvaluationResult is the contract both evaluators (mock and LLM) must satisfy.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_CATEGORY_SCORE = 5


class BusinessType(str, Enum):
    ROOFING = "Roofing"
    HVAC = "HVAC"
    PLUMBING = "Plumbing"
    GENERIC = "Generic Home Services"


class LeadTemperature(str, Enum):
    HOT = "Hot"
    WARM = "Warm"
    COLD = "Cold"


class Urgency(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RubricCategory(str, Enum):
    OPENING_RAPPORT = "Opening and rapport"
    LEAD_QUALIFICATION = "Lead qualification"
    PROBLEM_DISCOVERY = "Problem discovery"
    SERVICE_AREA_URGENCY = "Service-area and urgency confirmation"
    VALUE_COMMUNICATION = "Value communication"
    OBJECTION_HANDLING = "Objection handling"
    APPOINTMENT_ATTEMPT = "Appointment booking attempt"
    CLEAR_NEXT_STEP = "Clear next step"
    PROFESSIONAL_COMMUNICATION = "Professional communication"


# One actionable tip per rubric category (mock coaching text and coaching insights).
COACHING_TIPS = {
    RubricCategory.OPENING_RAPPORT: "Use a consistent opening: greet the caller, give your name and company, and acknowledge their problem before asking questions.",
    RubricCategory.LEAD_QUALIFICATION: "Before ending any call, confirm the customer's full name, best callback number, email, service address, and that they own the property.",
    RubricCategory.PROBLEM_DISCOVERY: "Ask at least three discovery questions (when it started, how severe it is, and what has been tried) before discussing next steps.",
    RubricCategory.SERVICE_AREA_URGENCY: "Confirm the service address early and ask how urgent the issue is, so the lead can be routed and prioritized correctly.",
    RubricCategory.VALUE_COMMUNICATION: "Explain why to choose us (free inspection, licensed technicians, workmanship warranty) before the customer asks about price.",
    RubricCategory.OBJECTION_HANDLING: "When cost comes up, acknowledge the concern, explain what the free inspection or estimate includes, and mention financing before moving on.",
    RubricCategory.APPOINTMENT_ATTEMPT: "Always ask for the appointment directly: offer two specific time slots instead of waiting for the customer to ask.",
    RubricCategory.CLEAR_NEXT_STEP: "End every call by restating the next step, the time it will happen, and how the customer will be contacted.",
    RubricCategory.PROFESSIONAL_COMMUNICATION: "Keep language professional and courteous; avoid filler and dismissive phrases, and close with a thank-you.",
}


class RubricScoreItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: RubricCategory
    score: int = Field(ge=0, le=MAX_CATEGORY_SCORE)
    feedback: str


def compute_overall_score(rubric_scores: list[RubricScoreItem]) -> int:
    """Sum of category scores scaled to 0-100."""
    if not rubric_scores:
        return 0
    total = sum(r.score for r in rubric_scores)
    return round(total / (len(rubric_scores) * MAX_CATEGORY_SCORE) * 100)


def follow_up_timing(lead_temperature: LeadTemperature, appointment_booked: bool) -> str:
    if appointment_booked:
        return "Send confirmation now; reminder 24 hours before the visit"
    return {
        LeadTemperature.HOT: "Within 1 hour",
        LeadTemperature.WARM: "Within 24 hours",
        LeadTemperature.COLD: "Within 3 days",
    }[lead_temperature]


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    transcript: str = Field(min_length=50, max_length=50_000)
    business_type: BusinessType = BusinessType.GENERIC
    agent_name: str = Field(min_length=1, max_length=100)
    call_date: date | None = None


class EvaluationResult(BaseModel):
    """Structured output of a transcript evaluation.

    overall_score is always recomputed from rubric_scores, so an evaluator
    (including an LLM) cannot report a total that disagrees with its own rubric.
    """

    customer_name: str | None
    customer_phone: str | None
    customer_email: str | None
    service_type: str
    location: str | None
    customer_problem: str
    urgency: Urgency
    lead_temperature: LeadTemperature
    appointment_booked: bool
    appointment_time: str | None
    overall_score: int = Field(ge=0, le=100)
    rubric_scores: list[RubricScoreItem]
    strengths: list[str]
    missed_opportunities: list[str]
    coaching_recommendation: str
    risk_flags: list[str]
    crm_note: str
    recommended_next_action: str
    sms_follow_up: str
    email_subject: str
    email_follow_up: str

    @model_validator(mode="after")
    def _rubric_complete_and_score_consistent(self) -> "EvaluationResult":
        categories = [r.category for r in self.rubric_scores]
        if len(categories) != len(set(categories)):
            raise ValueError("rubric_scores contains duplicate categories")
        missing = set(RubricCategory) - set(categories)
        if missing:
            names = ", ".join(sorted(c.value for c in missing))
            raise ValueError(f"rubric_scores is missing categories: {names}")
        self.overall_score = compute_overall_score(self.rubric_scores)
        return self


class EvaluationRead(EvaluationResult):
    """A stored evaluation, as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    call_date: date
    agent_name: str
    business_type: BusinessType
    transcript: str
    evaluation_mode: str


class EvaluationCreated(EvaluationRead):
    """Response to POST /api/evaluations: the stored evaluation plus any notice
    about how it was produced (e.g. why the LLM path fell back to mock)."""

    notice: str | None = None


class EvaluationSummary(BaseModel):
    """One row of the call-history list (full details via GET /api/evaluations/{id})."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    call_date: date
    agent_name: str
    business_type: BusinessType
    customer_name: str | None
    service_type: str
    urgency: Urgency
    lead_temperature: LeadTemperature
    appointment_booked: bool
    overall_score: int
    evaluation_mode: str


# --- Dashboard -----------------------------------------------------------------


class DashboardMetrics(BaseModel):
    """Headline numbers for the calls matching the request's filters."""

    total_calls: int
    average_score: float | None = Field(description="Mean overall score; null when there are no calls")
    hot_leads: int
    appointments_booked: int
    booking_rate: float | None = Field(description="Percent of calls with an appointment booked")
    follow_ups_needed: int = Field(description="Hot or warm leads without a booked appointment")
    low_score_calls: int = Field(description="Calls scoring under 60 (recommended for manager review)")


class ScoreTrendPoint(BaseModel):
    call_date: date
    calls: int
    average_score: float


class ServiceTypeStat(BaseModel):
    service_type: str
    calls: int
    average_score: float


class LeadTemperatureCount(BaseModel):
    lead_temperature: LeadTemperature
    calls: int


class AgentStat(BaseModel):
    agent_name: str
    calls: int
    average_score: float
    appointments_booked: int
    booking_rate: float


class DashboardAnalytics(BaseModel):
    """Breakdowns for the dashboard charts, for the calls matching the request's filters."""

    score_trend: list[ScoreTrendPoint] = Field(description="Average score per call date, oldest first")
    calls_by_service_type: list[ServiceTypeStat] = Field(description="Most common service first")
    lead_temperature_distribution: list[LeadTemperatureCount] = Field(description="Hot, Warm, Cold (zeros included)")
    calls_by_agent: list[AgentStat] = Field(description="Highest average score first")


# --- Coaching ------------------------------------------------------------------


class GapExample(BaseModel):
    evaluation_id: int
    call_date: date
    agent_name: str
    score: int
    feedback: str


class AgentGapCount(BaseModel):
    agent_name: str
    gap_calls: int


class RecurringGap(BaseModel):
    """A rubric category that scored at or below the gap threshold on several calls."""

    category: RubricCategory
    gap_calls: int
    gap_rate: float = Field(description="Percent of calls with this gap")
    agents: list[AgentGapCount] = Field(description="Agents with this gap, most affected first")
    coaching_tip: str
    examples: list[GapExample] = Field(description="Most recent calls with this gap")


class CategoryInsight(BaseModel):
    category: RubricCategory
    average_score: float
    calls: int
    gap_calls: int
    gap_rate: float


class AgentCategoryScore(BaseModel):
    category: RubricCategory
    average_score: float


class AgentCoaching(BaseModel):
    agent_name: str
    calls: int
    average_score: float
    category_scores: list[AgentCategoryScore] = Field(description="All nine categories, in rubric order")
    focus_areas: list[RubricCategory] = Field(description="Categories averaging under 3 / 5, weakest first (max 3)")
    strongest_area: RubricCategory | None = Field(description="Best category if it averages 4 / 5 or more")
    coaching_tip: str | None = Field(description="Tip for the weakest focus area; null when there is none")


class CoachingInsights(BaseModel):
    total_calls: int
    gap_threshold: int = Field(description="A category score at or below this counts as a gap")
    recurring_gaps: list[RecurringGap] = Field(description="Most frequent first")
    category_insights: list[CategoryInsight] = Field(description="Weakest category first")
    agents: list[AgentCoaching] = Field(description="Lowest average score first")
