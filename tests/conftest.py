import os
import tempfile

# Point the app at a throwaway database and force mock mode before any app
# module is imported (load_dotenv does not override variables already set).
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENAI_BASE_URL"] = ""
os.environ["SEED_DEMO_DATA"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    from app.database import Base, engine, init_db
    from app.main import app as fastapi_app

    Base.metadata.drop_all(engine)
    init_db()
    with TestClient(fastapi_app) as test_client:
        yield test_client
