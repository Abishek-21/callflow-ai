"""Thin HTTP client for the CallFlow FastAPI backend."""

from typing import Any

import requests

from app.config import API_BASE_URL


class ApiError(Exception):
    """A readable error message suitable for showing in the UI."""


def _error_message(resp: requests.Response) -> str:
    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        detail = resp.text
    if isinstance(detail, list):  # FastAPI/Pydantic validation errors
        parts = []
        for err in detail:
            loc = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query"))
            parts.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
        detail = "; ".join(parts)
    return f"API error {resp.status_code}: {detail}"


def _request(method: str, path: str, timeout: float = 15, **kwargs: Any) -> Any:
    try:
        resp = requests.request(method, f"{API_BASE_URL}{path}", timeout=timeout, **kwargs)
    except requests.RequestException as exc:
        raise ApiError(
            f"Can't reach the CallFlow API at {API_BASE_URL}. "
            "Start it with `uvicorn app.main:app --reload`."
        ) from exc
    if resp.status_code >= 400:
        raise ApiError(_error_message(resp))
    return resp.json()


def health() -> dict | None:
    """Backend health, or None if it is unreachable."""
    try:
        return _request("GET", "/health", timeout=3)
    except ApiError:
        return None


def create_evaluation(payload: dict) -> dict:
    # Generous timeout: the LLM path can take a while on long transcripts.
    return _request("POST", "/api/evaluations", json=payload, timeout=120)


def _params(filters: dict[str, Any]) -> dict[str, Any]:
    """Drop unset filters; send dates as ISO strings and booleans as true/false."""
    params = {}
    for key, value in filters.items():
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            value = str(value).lower()
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        params[key] = value
    return params


def list_evaluations(**filters: Any) -> list[dict]:
    return _request("GET", "/api/evaluations", params=_params(filters))


def get_evaluation(evaluation_id: int) -> dict:
    return _request("GET", f"/api/evaluations/{evaluation_id}")


def dashboard_metrics(**filters: Any) -> dict:
    return _request("GET", "/api/dashboard/metrics", params=_params(filters))


def dashboard_analytics(**filters: Any) -> dict:
    return _request("GET", "/api/dashboard/analytics", params=_params(filters))


def coaching_insights(**filters: Any) -> dict:
    return _request("GET", "/api/coaching/insights", params=_params(filters))
