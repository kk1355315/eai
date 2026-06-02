import os
from pathlib import Path

import pytest


TEST_DATABASE = Path("test_fruit_health.db")

os.environ["DATABASE_URL"] = f"sqlite:///./{TEST_DATABASE.name}"


def pytest_sessionstart(session) -> None:
    TEST_DATABASE.unlink(missing_ok=True)


def pytest_sessionfinish(session, exitstatus) -> None:
    from app.db import engine

    engine.dispose()
    TEST_DATABASE.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def reset_database() -> None:
    from sqlmodel import Session

    from app.db import engine, init_db
    from app.seed import seed_reference_data

    engine.dispose()
    TEST_DATABASE.unlink(missing_ok=True)
    init_db()

    with Session(engine) as db_session:
        seed_reference_data(db_session)

    yield

    engine.dispose()
    TEST_DATABASE.unlink(missing_ok=True)
