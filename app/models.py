"""SQLAlchemy database models."""

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CallEvaluation(Base):
    __tablename__ = "call_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    call_date: Mapped[date] = mapped_column(Date, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), index=True)
    business_type: Mapped[str] = mapped_column(String(40), index=True)
    transcript: Mapped[str] = mapped_column(Text)
    # "mock" or "llm", so mock results can always be labeled as such.
    evaluation_mode: Mapped[str] = mapped_column(String(10), default="mock")

    customer_name: Mapped[str | None] = mapped_column(String(120))
    customer_phone: Mapped[str | None] = mapped_column(String(40))
    customer_email: Mapped[str | None] = mapped_column(String(200))
    service_type: Mapped[str] = mapped_column(String(100), index=True)
    location: Mapped[str | None] = mapped_column(String(200))
    customer_problem: Mapped[str] = mapped_column(Text)
    urgency: Mapped[str] = mapped_column(String(10))
    lead_temperature: Mapped[str] = mapped_column(String(10), index=True)
    appointment_booked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    appointment_time: Mapped[str | None] = mapped_column(String(100))
    overall_score: Mapped[int] = mapped_column(Integer, index=True)

    strengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    missed_opportunities: Mapped[list[str]] = mapped_column(JSON, default=list)
    coaching_recommendation: Mapped[str] = mapped_column(Text)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    crm_note: Mapped[str] = mapped_column(Text)
    recommended_next_action: Mapped[str] = mapped_column(Text)
    sms_follow_up: Mapped[str] = mapped_column(Text)
    email_subject: Mapped[str] = mapped_column(String(200))
    email_follow_up: Mapped[str] = mapped_column(Text)

    rubric_scores: Mapped[list["RubricScore"]] = relationship(
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="RubricScore.id",
    )


class RubricScore(Base):
    __tablename__ = "rubric_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(
        ForeignKey("call_evaluations.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(60), index=True)
    score: Mapped[int] = mapped_column(Integer)
    feedback: Mapped[str] = mapped_column(Text)

    evaluation: Mapped[CallEvaluation] = relationship(back_populates="rubric_scores")
