from datetime import date

import pytest

from app.database import SessionLocal
from app.schemas import COACHING_TIPS, RubricCategory
from app.services.coaching import ScoreRow, build_insights
from app.services.seeding import seed_demo_data

CATS = list(RubricCategory)


def call(evaluation_id, agent, scores, day=1, overall=None):
    """Score rows for one call; `scores` maps category -> score (others default to 4)."""
    return [
        ScoreRow(
            evaluation_id=evaluation_id,
            call_date=date(2026, 10, day),
            agent_name=agent,
            overall_score=overall if overall is not None else 70,
            category=c,
            score=scores.get(c, 4),
            feedback=f"{c.value} feedback on call {evaluation_id}",
        )
        for c in CATS
    ]


VALUE, BOOKING, OPENING = (
    RubricCategory.VALUE_COMMUNICATION,
    RubricCategory.APPOINTMENT_ATTEMPT,
    RubricCategory.OPENING_RAPPORT,
)


def test_gap_on_two_calls_is_recurring_but_one_is_not():
    rows = (
        call(3, "Ann", {VALUE: 1, BOOKING: 2}, day=3)
        + call(2, "Bob", {VALUE: 2}, day=2)
        + call(1, "Ann", {VALUE: 3}, day=1)
    )  # newest first, as the endpoint orders them
    insights = build_insights(rows)
    assert insights.total_calls == 3
    assert [g.category for g in insights.recurring_gaps] == [VALUE]
    gap = insights.recurring_gaps[0]
    assert gap.gap_calls == 2 and gap.gap_rate == pytest.approx(66.7)
    assert [(a.agent_name, a.gap_calls) for a in gap.agents] == [("Ann", 1), ("Bob", 1)]
    assert [e.evaluation_id for e in gap.examples] == [3, 2]  # newest first
    assert gap.coaching_tip == COACHING_TIPS[VALUE]


def test_examples_are_capped():
    rows = [r for i in range(5, 0, -1) for r in call(i, "Ann", {VALUE: 0}, day=i)]
    gap = build_insights(rows).recurring_gaps[0]
    assert gap.gap_calls == 5
    assert [e.evaluation_id for e in gap.examples] == [5, 4, 3]


def test_category_insights_weakest_first():
    insights = build_insights(call(1, "Ann", {VALUE: 0, BOOKING: 1}) + call(2, "Ann", {VALUE: 2, BOOKING: 1}))
    first, second = insights.category_insights[:2]
    assert (first.category, first.average_score, first.gap_calls) == (VALUE, 1.0, 2)
    assert (second.category, second.average_score) == (BOOKING, 1.0)  # tie keeps rubric order
    assert len(insights.category_insights) == 9


def test_agent_focus_areas_and_strength():
    rows = call(1, "Ann", {VALUE: 1, BOOKING: 2, OPENING: 2, RubricCategory.CLEAR_NEXT_STEP: 2}, overall=40)
    rows += call(2, "Bob", {c: 5 for c in CATS}, overall=100)
    rows += call(3, "Cy", {c: 3 for c in CATS}, overall=60)
    ann, cy, bob = build_insights(rows).agents  # lowest average first
    assert ann.agent_name == "Ann" and ann.average_score == 40
    assert ann.focus_areas == [VALUE, OPENING, BOOKING]  # weakest first, ties in rubric order, max 3
    assert ann.coaching_tip == COACHING_TIPS[VALUE]
    assert ann.strongest_area == RubricCategory.LEAD_QUALIFICATION  # first 4.0 in rubric order
    assert bob.focus_areas == [] and bob.coaching_tip is None
    assert cy.strongest_area is None  # nothing averages 4+
    assert [s.category for s in ann.category_scores] == CATS


def test_no_rows():
    insights = build_insights([])
    assert insights.total_calls == 0
    assert insights.recurring_gaps == [] and insights.category_insights == [] and insights.agents == []


# --- Endpoint, on the demo dataset ----------------------------------------------


@pytest.fixture
def seeded(client):
    with SessionLocal() as db:
        seed_demo_data(db, shift_dates=False)
    return client


def test_insights_endpoint_on_demo_data(seeded):
    body = seeded.get("/api/coaching/insights").json()
    assert body["total_calls"] == 18
    assert body["gap_threshold"] == 2
    counts = [g["gap_calls"] for g in body["recurring_gaps"]]
    assert counts == sorted(counts, reverse=True)
    agents = {a["agent_name"]: a for a in body["agents"]}
    assert [a["agent_name"] for a in body["agents"]] == ["Jake Miller", "Chris Novak", "Priya Shah", "Maya Torres"]
    assert agents["Chris Novak"]["focus_areas"][0] == "Value communication"
    assert agents["Maya Torres"]["focus_areas"] == []
    assert agents["Jake Miller"]["strongest_area"] is None


def test_insights_respect_filters(seeded):
    body = seeded.get("/api/coaching/insights", params={"agent_name": "Maya Torres"}).json()
    assert body["total_calls"] == 5
    assert [a["agent_name"] for a in body["agents"]] == ["Maya Torres"]
    assert body["recurring_gaps"] == []


def test_insights_on_empty_database(client):
    body = client.get("/api/coaching/insights").json()
    assert body["total_calls"] == 0 and body["agents"] == [] and body["recurring_gaps"] == []


def test_insights_in_docs(client):
    assert "/api/coaching/insights" in client.get("/openapi.json").json()["paths"]
