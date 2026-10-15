"""python -m eios.reference build --project <id> --icij-entities <nodes-entities.csv> --icij-as-of 2026-09-09"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from eios.reference.build import build_reference


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m eios.reference")
    ap.add_argument("command", choices=["build"])
    ap.add_argument("--project", required=True)
    ap.add_argument(
        "--icij-entities",
        type=Path,
        required=True,
        help="nodes-entities.csv from the ICIJ bulk download",
    )
    ap.add_argument(
        "--icij-as-of", required=True, help="the date the ICIJ dump was generated (YYYY-MM-DD)"
    )
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    summary = build_reference(args.project, args.icij_entities, args.icij_as_of)
    print("warm_reference built:", ", ".join(f"{t}={n}" for t, n in summary.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
