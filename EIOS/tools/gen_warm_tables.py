"""Write the warm tier's table layout for Terraform, generated from the contracts (docs/warm-tier.md).

PYTHONPATH=src uv run python -m tools.gen_warm_tables          # rewrite the file
PYTHONPATH=src uv run python -m tools.gen_warm_tables --check  # fail if it is out of date (CI and tests)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from eios.warm.schema import all_specs, to_bigquery_schema

TARGET = Path(__file__).resolve().parents[1] / "infra" / "modules" / "bigquery_warm" / "tables.json"


def render() -> str:
    tables = [
        {
            "dataset": s.dataset,
            "table": s.table,
            "partition_field": s.partition_field,
            "cluster_fields": list(s.cluster_fields),
            "schema": to_bigquery_schema(s),
        }
        for s in all_specs()
    ]
    return json.dumps(tables, indent=2) + "\n"


def main(argv: list[str]) -> int:
    text = render()
    if "--check" in argv:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != text:
            print(f"{TARGET} is out of date: run python -m tools.gen_warm_tables", file=sys.stderr)
            return 1
        return 0
    TARGET.write_text(text, encoding="utf-8")
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
