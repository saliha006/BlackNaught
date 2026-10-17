import os

import pytest

# forced, not setdefault: compose sets BN_DB_NAME=blacknaught and the session fixture drops schema bn
os.environ["BN_DB_NAME"] = TEST_DB = "blacknaught_test"
# the app container runs with BN_WORKERS=1; tests must never start live pollers
os.environ["BN_WORKERS"] = "0"

from app.db import Db, connect  # noqa: E402
from app.migrate import migrate  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


def reset_schema() -> None:
    assert TEST_DB.endswith("_test"), "refusing to drop schema outside a test database"
    conn = connect("postgres", TEST_DB)
    try:
        conn.run("DROP SCHEMA IF EXISTS bn CASCADE")
    finally:
        conn.close()
    migrate(TEST_DB)


@pytest.fixture(scope="session", autouse=True)
def schema():
    reset_schema()
    yield


@pytest.fixture
def superuser():
    conn = connect("postgres", TEST_DB)
    conn.run("SET search_path = bn")
    yield conn
    conn.close()


@pytest.fixture
def db_factory():
    opened: list[Db] = []

    def make(role: str) -> Db:
        db = Db(role, TEST_DB)
        opened.append(db)
        return db

    yield make
    for db in opened:
        db.close()
