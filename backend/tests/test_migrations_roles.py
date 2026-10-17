import pytest
from pg8000.exceptions import DatabaseError

from app.migrate import MigrationDrift, migrate, migration_files
from conftest import TEST_DB, reset_schema


def test_migrations_are_numbered_and_ordered(schema):
    from app.config import settings

    versions = [v for v, _ in migration_files(settings().migrations_dir)]
    assert versions == sorted(versions) and len(versions) == len(set(versions))


def test_rerun_applies_nothing(schema):
    assert migrate(TEST_DB) == []


def test_drift_guard_refuses_changed_file(schema, tmp_path, superuser):
    from app.config import settings

    for _, path in migration_files(settings().migrations_dir):
        (tmp_path / path.name).write_text(path.read_text())
    first = sorted(tmp_path.glob("*.sql"))[0]
    first.write_text(first.read_text() + "\n-- edited\n")
    with pytest.raises(MigrationDrift):
        migrate(TEST_DB, tmp_path)


def test_failed_migration_rolls_back(schema, tmp_path, superuser):
    from app.config import settings

    for _, path in migration_files(settings().migrations_dir):
        (tmp_path / path.name).write_text(path.read_text())
    (tmp_path / "9999_broken.sql").write_text("CREATE TABLE bn.half_done (x int); SELECT broken_syntax(;")
    with pytest.raises(DatabaseError):
        migrate(TEST_DB, tmp_path)
    assert superuser.run("SELECT to_regclass('bn.half_done')")[0][0] is None
    assert superuser.run("SELECT count(*) FROM bn.schema_migrations WHERE version = 9999")[0][0] == 0


@pytest.mark.anyio
async def test_api_role_cannot_read_register(db_factory):
    with pytest.raises(DatabaseError, match="permission denied"):
        await db_factory("bn_api").run("SELECT * FROM patient")


@pytest.mark.anyio
async def test_api_role_reads_views(db_factory):
    assert await db_factory("bn_api").run("SELECT count(*) FROM v_outage_public") == [[0]]


@pytest.mark.anyio
async def test_ingest_cannot_touch_audit_log(db_factory):
    with pytest.raises(DatabaseError, match="permission denied"):
        await db_factory("bn_ingest").run("DELETE FROM audit_log")


@pytest.mark.anyio
async def test_ingest_cannot_read_register(db_factory):
    with pytest.raises(DatabaseError, match="permission denied"):
        await db_factory("bn_ingest").run("SELECT * FROM patient")


def test_register_rejects_non_synthetic_rows(superuser):
    with pytest.raises(DatabaseError, match="check"):
        superuser.run(
            "INSERT INTO patient (patient_id, household_id, cell_l1, postcode_bidx, contact_ct, device,"
            " reserve_h, other_backup, severity, synthetic) VALUES (gen_random_uuid(), gen_random_uuid(),"
            " 'L1:0:0', '\\x00', '\\x00', 'o2', 1, false, 3, false)"
        )


def test_owner_update_blocked_by_trigger(superuser):
    superuser.run("SELECT audit_append('{\"kind\":\"test\"}')")
    with pytest.raises(DatabaseError, match="append-only"):
        superuser.run("UPDATE audit_log SET body = 'x'")
    with pytest.raises(DatabaseError, match="append-only"):
        superuser.run("DELETE FROM audit_log")
    # plain TRUNCATE already fails on the checkpoint FK; CASCADE is the real attack and must hit the trigger
    with pytest.raises(DatabaseError, match="append-only"):
        superuser.run("TRUNCATE audit_log CASCADE")
    assert superuser.run("SELECT count(*) > 0 FROM audit_log")[0][0]


def test_full_rebuild_from_zero():
    reset_schema()
    assert migrate(TEST_DB) == []
