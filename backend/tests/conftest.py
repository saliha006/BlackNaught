import os

import pytest

os.environ.setdefault("BN_DB_NAME", "blacknaught_test")
TEST_DB = os.environ["BN_DB_NAME"]

from app.db import Db, connect  # noqa: E402
from app.migrate import migrate  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


def reset_schema() -> None:
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
async def db_factory():
    opened: list[Db] = []

    def make(role: str) -> Db:
        db = Db(role, TEST_DB)
        opened.append(db)
        return db

    yield make
    for db in opened:
        db.close()
