"""Forward-only migration runner with a checksum drift guard.

Usage: python -m app.migrate [database]
Each db/migrations/NNNN_*.sql file runs in one transaction as bn_migrator (acting as bn_owner).
"""
import hashlib
import sys
from pathlib import Path

import pg8000.native

from .config import settings
from .db import connect


class MigrationDrift(RuntimeError):
    pass


def migration_files(directory: Path) -> list[tuple[int, Path]]:
    files = []
    for path in sorted(directory.glob("*.sql")):
        files.append((int(path.name.split("_", 1)[0]), path))
    return files


def applied(conn: pg8000.native.Connection) -> dict[int, str]:
    exists = conn.run("SELECT to_regclass('bn.schema_migrations') IS NOT NULL")[0][0]
    if not exists:
        return {}
    return {v: sha for v, sha in conn.run("SELECT version, sha256 FROM bn.schema_migrations")}


def migrate(database: str | None = None, directory: Path | None = None) -> list[int]:
    directory = directory or settings().migrations_dir
    conn = connect("bn_migrator", database)
    try:
        conn.run("SET ROLE bn_owner")
        done = applied(conn)
        ran = []
        for version, path in migration_files(directory):
            sql = path.read_text()
            digest = hashlib.sha256(sql.encode()).hexdigest()
            if version in done:
                if done[version] != digest:
                    raise MigrationDrift(f"{path.name} changed after it was applied")
                continue
            conn.run("BEGIN")
            try:
                conn.execute_simple(sql)
                conn.run(
                    "INSERT INTO bn.schema_migrations (version, sha256) VALUES (:v, :s)",
                    v=version,
                    s=digest,
                )
                conn.run("COMMIT")
            except Exception:
                conn.run("ROLLBACK")
                raise
            ran.append(version)
        return ran
    finally:
        conn.close()


if __name__ == "__main__":
    print("applied:", migrate(sys.argv[1] if len(sys.argv) > 1 else None))
