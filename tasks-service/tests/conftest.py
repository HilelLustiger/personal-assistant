import os

# Must be before any app imports — db/session.py reads DATABASE_URL at module level
_DEFAULT_TEST_DB = (
    "postgresql+psycopg://postgres:postgres@localhost:5432/personal_assistant_test"
)
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", _DEFAULT_TEST_DB)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
from db.models import (  # noqa: E402, F401 — registers all table metadata
    Goal,
    Habit,
    HabitLog,
    Reminder,
    Task,
)
from db.session import engine  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.exc import ProgrammingError  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402


def _ensure_test_database_exists():
    parsed_url = make_url(TEST_DATABASE_URL)
    db_name = parsed_url.database
    admin_url = parsed_url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE {db_name}"))
    except ProgrammingError:
        pass  # already exists
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    _ensure_test_database_exists()
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def clear_tables():
    with Session(engine) as session:
        for table_name in ["habit_logs", "tasks", "habits", "reminders", "goals"]:
            session.exec(text(f"DELETE FROM {table_name}"))
        session.commit()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
