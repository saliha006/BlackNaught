import pytest
from pg8000.exceptions import DatabaseError

from app.db import Db


@pytest.mark.anyio
async def test_rows_returns_dicts(db_factory):
    rows = await db_factory("bn_agent").rows("SELECT 1 AS a, 'x' AS b")
    assert rows == [{"a": 1, "b": "x"}]


@pytest.mark.anyio
async def test_session_is_utc_and_scoped(db_factory):
    db = db_factory("bn_api")
    assert (await db.run("SHOW TimeZone"))[0][0] == "UTC"
    assert (await db.run("SHOW search_path"))[0][0] == "bn, pg_temp"


@pytest.mark.anyio
async def test_reconnects_after_backend_killed(db_factory, superuser):
    db = db_factory("bn_agent")
    pid = (await db.run("SELECT pg_backend_pid()"))[0][0]
    superuser.run("SELECT pg_terminate_backend(:pid)", pid=pid)
    assert (await db.run("SELECT 42"))[0][0] == 42
    assert (await db.run("SELECT pg_backend_pid()"))[0][0] != pid


@pytest.mark.anyio
async def test_non_idempotent_statement_not_retried(db_factory, superuser):
    db = db_factory("bn_agent")
    pid = (await db.run("SELECT pg_backend_pid()"))[0][0]
    superuser.run("SELECT pg_terminate_backend(:pid)", pid=pid)
    with pytest.raises(Exception):
        await db.run("SELECT 1", idempotent=False)
    assert (await db.run("SELECT 1"))[0][0] == 1


@pytest.mark.anyio
async def test_sql_errors_are_not_swallowed(db_factory):
    with pytest.raises(DatabaseError, match="does not exist"):
        await db_factory("bn_agent").run("SELECT * FROM no_such_table")


def test_close_is_safe_without_connection():
    Db("bn_api").close()
