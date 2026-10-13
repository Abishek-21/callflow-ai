"""Application settings, read from environment variables (and .env if present)."""

import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

# Any OpenAI-compatible provider works: leave OPENAI_BASE_URL blank for OpenAI,
# or set it to e.g. https://api.x.ai/v1 for xAI Grok.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "").strip() or "gpt-4o-mini"
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "").strip() or "60")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./callflow.db").strip()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").strip()
# Load the fictional demo calls on startup when the database is empty.
SEED_DEMO_DATA = os.getenv("SEED_DEMO_DATA", "").strip().lower() in {"1", "true", "yes"}


def llm_enabled() -> bool:
    """True when an API key is configured; otherwise the mock evaluator is used."""
    return bool(OPENAI_API_KEY)


def llm_provider() -> str:
    """Human-readable provider name derived from the base URL."""
    if not OPENAI_BASE_URL:
        return "OpenAI"
    host = urlparse(OPENAI_BASE_URL).hostname or OPENAI_BASE_URL
    return {"api.x.ai": "xAI", "api.groq.com": "Groq"}.get(host, host)
