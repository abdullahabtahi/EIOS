"""Plan, verify and load the regulatory corpus into the knowledge index (Phase 3).

``uv run python -m tools.ingest_regulations --project <id> --data-store <id> --bucket <name>`` verifies the files and
prints the plan; nothing is uploaded or imported. Add ``--execute`` to upload and start the import, which is the step
that costs: the data store parses every page. The import runs on the service; poll the printed operation name or
query the index to see when documents are searchable.
"""

from __future__ import annotations

import argparse
import sys

from eios.knowledge import ingest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--data-store", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument(
        "--execute", action="store_true", help="upload the files and start the import (costs money)"
    )
    args = parser.parse_args(argv)

    chosen = ingest.plan(args.bucket, args.data_store)
    for doc in chosen.documents:
        ingest.fetch(doc)  # downloads what is missing and checks every checksum
    print(chosen.describe())
    if not args.execute:
        print("Plan only. Re-run with --execute to upload and import.")
        return 0
    ingest.upload(chosen)
    print("import started:", ingest.start_import(chosen, args.project))
    return 0


if __name__ == "__main__":
    sys.exit(main())
