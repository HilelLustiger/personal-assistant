import os

# Set before any app imports — main.py reads these at module level
_DEFAULT_TEST_DB = "postgresql+psycopg://postgres:postgres@localhost:5432/personal_assistant_test"
os.environ.setdefault("DATABASE_URL", _DEFAULT_TEST_DB)
# No TELEGRAM_BOT_TOKEN → main.py skips Telegram init in lifespan (test mode)
os.environ.pop("TELEGRAM_BOT_TOKEN", None)

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
