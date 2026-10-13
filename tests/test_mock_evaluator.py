import pytest

from app.sample_data import DEMO_CALLS
from app.schemas import BusinessType, LeadTemperature, RubricCategory, Urgency, compute_overall_score
from app.services.mock_evaluator import TIME_RE, evaluate_transcript_mock, parse_transcript

DEMOS = {c["key"]: c for c in DEMO_CALLS}


def run(key):
    c = DEMOS[key]
    return evaluate_transcript_mock(c["transcript"], c["business_type"], c["agent_name"])


def scores(result):
    return {r.category: r.score for r in result.rubric_scores}


def test_demo_calls_rank_by_quality():
    roofing, plumbing, hvac = run("roofing_strong"), run("plumbing_objection"), run("hvac_weak")
    assert roofing.overall_score > plumbing.overall_score > hvac.overall_score
    assert roofing.overall_score >= 85
    assert hvac.overall_score <= 40


@pytest.mark.parametrize("key", list(DEMOS))
def test_rubric_complete_and_overall_consistent(key):
    result = run(key)
    assert {r.category for r in result.rubric_scores} == set(RubricCategory)
    assert all(0 <= r.score <= 5 and r.feedback for r in result.rubric_scores)
    assert result.overall_score == compute_overall_score(result.rubric_scores)


@pytest.mark.parametrize("key", list(DEMOS))
def test_is_deterministic(key):
    assert run(key).model_dump() == run(key).model_dump()


def test_strong_roofing_call_extracts_lead_and_booking():
    r = run("roofing_strong")
    assert r.customer_name == "Dana Whitfield"
    assert r.customer_phone == "(512) 555-0143"
    assert r.customer_email == "dana.whitfield@example.com"
    assert r.location == "1420 Maple Ridge Drive, Lakeview Springs"
    assert r.service_type == "Storm damage roof repair"
    assert r.urgency == Urgency.HIGH
    assert r.lead_temperature == LeadTemperature.HOT
    assert r.appointment_booked is True
    assert r.appointment_time == "Today at 3 PM"
    assert r.risk_flags == []
    assert "confirmed" in r.email_subject.lower()


def test_weak_hvac_call_flags_missed_appointment():
    r = run("hvac_weak")
    s = scores(r)
    assert r.appointment_booked is False
    assert s[RubricCategory.APPOINTMENT_ATTEMPT] == 0
    assert s[RubricCategory.OBJECTION_HANDLING] <= 2
    assert r.lead_temperature == LeadTemperature.HOT
    assert any("no appointment booked" in f for f in r.risk_flags)
    assert any(m.startswith(RubricCategory.APPOINTMENT_ATTEMPT.value) for m in r.missed_opportunities)
    assert r.customer_problem.startswith("My AC stopped cooling")  # leading "Hi, yeah," stripped
    assert "within 1 hour" in r.recommended_next_action


def test_plumbing_objection_handled_with_callback():
    r = run("plumbing_objection")
    s = scores(r)
    assert s[RubricCategory.OBJECTION_HANDLING] >= 4
    assert s[RubricCategory.APPOINTMENT_ATTEMPT] == 3
    assert r.appointment_booked is False
    assert r.appointment_time is None
    assert r.urgency == Urgency.MEDIUM
    assert r.lead_temperature == LeadTemperature.WARM
    assert "tomorrow at 10 AM" in r.recommended_next_action
    assert "tomorrow at 10 AM" in r.sms_follow_up


@pytest.mark.parametrize("key", list(DEMOS))
def test_follow_ups_thank_customer_and_include_call_to_action(key):
    r = run(key)
    first_name = r.customer_name.split()[0]
    for text in (r.sms_follow_up, r.email_follow_up):
        assert first_name in text
        assert "thank" in text.lower()
        assert "555-0199" in text
    assert r.customer_problem in r.email_follow_up
    assert ".." not in r.sms_follow_up + r.email_follow_up + r.crm_note


def test_unlabeled_transcript_is_flagged_but_still_evaluated():
    transcript = (
        "Thanks for calling, how can I help? My water heater is leaking all over the garage floor. "
        "I'm sorry to hear that. Can we schedule a technician tomorrow at 9 a.m.?"
    )
    r = evaluate_transcript_mock(transcript, BusinessType.PLUMBING, "Sam")
    assert r.service_type == "Water heater service"
    assert any("no speaker labels" in f for f in r.risk_flags)


def test_agent_first_name_label_is_recognized_as_agent():
    parsed = parse_transcript("Maya: Thanks for calling.\nDana: My roof is leaking.", "Maya Torres")
    assert parsed.agent_lines == ["Thanks for calling."]
    assert parsed.customer_lines == ["My roof is leaking."]


def test_single_line_transcript_is_split_on_speaker_labels():
    parsed = parse_transcript(
        "Agent: Thanks for calling, this is Sam. Customer: My gutter is overflowing. Agent: Sorry to hear that.",
        "Sam Lee",
    )
    assert parsed.labeled
    assert parsed.agent_lines == ["Thanks for calling, this is Sam.", "Sorry to hear that."]
    assert parsed.customer_lines == ["My gutter is overflowing."]


def test_time_match_starts_at_nearest_day_word():
    m = TIME_RE.search("You'll get an email today, and I'll call you tomorrow at 10 a.m. to follow up.")
    assert m.group(0) == "tomorrow at 10 a.m."
