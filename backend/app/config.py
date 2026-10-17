"""Runtime settings. Secrets are read from files (compose secrets), never from env values."""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def read_secret(name: str) -> str:
    path = Path(os.environ.get("BN_SECRETS_DIR", "/run/secrets")) / name
    value = path.read_text().strip()
    if not value:
        raise RuntimeError(f"secret {name} is empty")
    return value


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    migrations_dir: Path
    fixtures_dir: Path
    model_path: Path
    signer_url: str | None
    risk_model_path: Path


@lru_cache
def settings() -> Settings:
    return Settings(
        db_host=os.environ.get("BN_DB_HOST", "127.0.0.1"),
        db_port=int(os.environ.get("BN_DB_PORT", "5432")),
        db_name=os.environ.get("BN_DB_NAME", "blacknaught"),
        migrations_dir=Path(os.environ.get("BN_MIGRATIONS_DIR", "/db/migrations")),
        fixtures_dir=Path(os.environ.get("BN_FIXTURES_DIR", "/fixtures")),
        model_path=Path(os.environ.get("BN_MODEL_PATH", "/srv/models/km_enwl.json")),
        signer_url=os.environ.get("BN_SIGNER_URL") or None,
        risk_model_path=Path(os.environ.get("BN_RISK_MODEL_PATH", "/srv/models/climatology_enwl.json")),
    )
