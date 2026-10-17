"""Export the frozen contracts: python -m app.contracts <out_dir>"""
import json
import sys
from pathlib import Path

import yaml
from pydantic import TypeAdapter

from .events import Event
from .main import app


def export(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "openapi.yaml").write_text(yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    schema = TypeAdapter(Event).json_schema()
    (out / "events.schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    export(Path(sys.argv[1] if len(sys.argv) > 1 else "/contracts"))
