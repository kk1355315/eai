from collections.abc import Iterator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings


engine = create_engine(settings.database_url, echo=False)


def init_db() -> None:
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _ensure_schema_updates()


def _ensure_schema_updates() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("nutrition_facts"):
        return

    columns = {
        column["name"] for column in inspector.get_columns("nutrition_facts")
    }
    pending_columns = []
    if "fdc_id" not in columns:
        pending_columns.append("ADD COLUMN fdc_id INTEGER")
    if "source_url" not in columns:
        pending_columns.append("ADD COLUMN source_url TEXT")

    if not pending_columns:
        return

    with engine.begin() as connection:
        for statement in pending_columns:
            connection.execute(text(f"ALTER TABLE nutrition_facts {statement}"))


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
