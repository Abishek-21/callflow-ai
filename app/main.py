"""FastAPI entry point. Run with: uvicorn app.main:app --reload"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import config
from app.database import SessionLocal, init_db
from app.routers import coaching, dashboard, evaluations
from app.services.seeding import seed_demo_data

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if config.SEED_DEMO_DATA:
        with SessionLocal() as db:
            added = seed_demo_data(db)
        if added:
            logger.info("Loaded %d fictional demo calls (SEED_DEMO_DATA is on).", added)
    yield


app = FastAPI(
    title="CallFlow AI",
    description=(
        "Portfolio prototype: AI call-quality review, lead follow-up, and sales coaching "
        "for a fictional home-services call center. All data is fictional."
    ),
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(evaluations.router)
app.include_router(dashboard.router)
app.include_router(coaching.router)


@app.get("/health", tags=["system"])
def health() -> dict:
    if not config.llm_enabled():
        return {"status": "ok", "evaluation_mode": "mock", "provider": None, "model": None}
    return {
        "status": "ok",
        "evaluation_mode": "llm",
        "provider": config.llm_provider(),
        "model": config.OPENAI_MODEL,
    }
