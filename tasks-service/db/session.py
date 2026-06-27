import os
from typing import Generator

from sqlmodel import Session, create_engine

_raw_url = os.environ["DATABASE_URL"]
# Railway provides postgresql://, SQLAlchemy+psycopg3 requires postgresql+psycopg://
DATABASE_URL = (
    _raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if _raw_url.startswith("postgresql://")
    else _raw_url
)
engine = create_engine(DATABASE_URL)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
