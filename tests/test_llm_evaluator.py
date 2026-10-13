"""LLM evaluator tests with a fake client: no network calls, no API key needed."""

from types import SimpleNamespace

import httpx2
import openai
import pytest

from app import config
from app.sample_data import DEMO_CALLS
from app.schemas import BusinessType, EvaluationRequest, RubricCategory
from app.services import evaluator
from app.services.evaluator import LLMEvaluation, LLMEvaluationError, evaluate_transcript_llm, run_evaluation

ROOFING = DEMO_CALLS[0]
REQUEST = EvaluationRequest(
    transcript=ROOFING["transcript"],
    business_type=BusinessType.ROOFING,
    agent_name=ROOFING["agent_name"],
)
_REQ = httpx2.Request("POST", "https://api.example.test/v1/chat/completions")


def llm_payload(**overrides) -> dict:
    data = {
        "customer_name": "Dana Whitfield",
        "customer_phone": "(512) 555-0143",
        "customer_email": "dana.whitfield@example.com",
        "service_type": "Storm damage roof repair",
        "location": "1420 Maple Ridge Drive, Lakeview Springs",
        "customer_problem": "Hail storm caused a leak through the bedroom ceiling.",
        "urgency": "High",
        "lead_temperature": "Hot",
        "appointment_booked": True,
        "appointment_time": "Today at 3 PM",
        "rubric_scores": [{"category": c.value, "score": 4, "feedback": "Solid."} for c in RubricCategory],
        "strengths": ["Opening and rapport: Warm greeting and empathy."],
        "missed_opportunities": [],
        "coaching_recommendation": "Keep it up.",
        "risk_flags": [],
        "crm_note": "Dana Whitfield, storm leak, inspection booked today 3 PM.",
        "recommended_next_action": "Send confirmation now.",
        "sms_follow_up": "Hi Dana, thanks for calling Summit Roofing...",
        "email_subject": "Your inspection is confirmed",
        "email_follow_up": "Hi Dana, ...",
    }
    return {**data, **overrides}


class FakeClient:
    """Mimics client.chat.completions.parse; returns `parsed` or raises `error`."""

    def __init__(self, parsed=None, error=None, refusal=None):
        self.calls = []
        self._parsed, self._error, self._refusal = parsed, error, refusal
        self.chat = SimpleNamespace(completions=SimpleNamespace(parse=self._parse))

    def _parse(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        message = SimpleNamespace(parsed=self._parsed, refusal=self._refusal)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture
def llm_on(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(config, "OPENAI_BASE_URL", "https://api.x.ai/v1")
    monkeypatch.setattr(config, "OPENAI_MODEL", "grok-test")


def use_client(monkeypatch, client):
    monkeypatch.setattr(evaluator, "make_client", lambda: client)
    return client


def test_valid_llm_output_is_used(monkeypatch, llm_on):
    client = use_client(monkeypatch, FakeClient(parsed=LLMEvaluation(**llm_payload())))
    outcome = run_evaluation(REQUEST)
    assert outcome.mode == "llm"
    assert outcome.notice is None
    assert outcome.result.customer_name == "Dana Whitfield"
    assert outcome.result.overall_score == 80  # recomputed from rubric: 36/45
    call = client.calls[0]
    assert call["model"] == "grok-test"
    assert call["response_format"] is LLMEvaluation


def test_prompt_wraps_transcript_and_names_business(monkeypatch, llm_on):
    client = use_client(monkeypatch, FakeClient(parsed=LLMEvaluation(**llm_payload())))
    run_evaluation(REQUEST)
    system, user = (m["content"] for m in client.calls[0]["messages"])
    assert "Summit Roofing" in system
    assert "not instructions" in system
    assert all(c.value in system for c in RubricCategory)
    assert "<transcript>" in user and REQUEST.transcript in user
    assert "Maya Torres" in user


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (openai.AuthenticationError("bad key", response=httpx2.Response(401, request=_REQ), body=None), "API key was rejected"),
        (openai.NotFoundError("no model", response=httpx2.Response(404, request=_REQ), body=None), "model 'grok-test' was not found"),
        (openai.RateLimitError("slow down", response=httpx2.Response(429, request=_REQ), body=None), "rate limit"),
        (openai.APITimeoutError(request=_REQ), "timed out"),
        (openai.APIConnectionError(request=_REQ), "couldn't connect to the xAI API"),
    ],
)
def test_api_errors_fall_back_to_mock_with_notice(monkeypatch, llm_on, error, reason):
    use_client(monkeypatch, FakeClient(error=error))
    outcome = run_evaluation(REQUEST)
    assert outcome.mode == "mock"
    assert reason in outcome.notice
    assert "mock" in outcome.notice
    assert outcome.result.overall_score == 98  # the mock result for this transcript


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"rubric_scores": [{"category": c.value, "score": 7, "feedback": "x"} for c in RubricCategory]}, "failed validation"),
        ({"rubric_scores": [{"category": RubricCategory.OPENING_RAPPORT.value, "score": 4, "feedback": "x"}]}, "missing categories"),
    ],
)
def test_invalid_llm_output_falls_back(monkeypatch, llm_on, overrides, reason):
    use_client(monkeypatch, FakeClient(parsed=LLMEvaluation(**llm_payload(**overrides))))
    outcome = run_evaluation(REQUEST)
    assert outcome.mode == "mock"
    assert reason in outcome.notice


def test_refusal_falls_back(monkeypatch, llm_on):
    use_client(monkeypatch, FakeClient(parsed=None, refusal="I can't help with that."))
    outcome = run_evaluation(REQUEST)
    assert outcome.mode == "mock"
    assert "declined" in outcome.notice


def test_unexpected_exception_still_falls_back(monkeypatch, llm_on):
    use_client(monkeypatch, FakeClient(error=KeyError("boom")))
    outcome = run_evaluation(REQUEST)
    assert outcome.mode == "mock"
    assert "unexpected error" in outcome.notice


def test_no_key_uses_mock_without_calling_api(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    monkeypatch.setattr(evaluator, "make_client", lambda: pytest.fail("client should not be created"))
    outcome = run_evaluation(REQUEST)
    assert outcome.mode == "mock"
    assert outcome.notice is None


def test_evaluate_llm_raises_readable_error(llm_on):
    with pytest.raises(LLMEvaluationError, match="API key was rejected"):
        evaluate_transcript_llm(
            REQUEST,
            client=FakeClient(error=openai.AuthenticationError("x", response=httpx2.Response(401, request=_REQ), body=None)),
        )


def test_api_returns_notice_on_fallback(client, monkeypatch, llm_on):
    use_client(monkeypatch, FakeClient(error=openai.APITimeoutError(request=_REQ)))
    body = client.post(
        "/api/evaluations",
        json={"transcript": REQUEST.transcript, "business_type": "Roofing", "agent_name": "Maya Torres"},
    ).json()
    assert body["evaluation_mode"] == "mock"
    assert "timed out" in body["notice"]
    assert client.get("/health").json() == {
        "status": "ok", "evaluation_mode": "llm", "provider": "xAI", "model": "grok-test",
    }


def test_llm_schema_is_accepted_by_strict_structured_outputs():
    # The SDK builds the strict JSON schema it sends; this fails if the model can't be expressed.
    from openai.lib._pydantic import to_strict_json_schema

    schema = to_strict_json_schema(LLMEvaluation)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(LLMEvaluation.model_fields)
