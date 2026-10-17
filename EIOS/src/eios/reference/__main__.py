"""python -m eios.reference build --project <id> --icij-entities <nodes-entities.csv> --icij-as-of 2026-09-09
python -m eios.reference lists --project <id>     (reload only the FATF/EU lists and Basel scores)
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from eios.reference.build import build_lists, build_reference


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m eios.reference")
    ap.add_argument("command", choices=["build", "lists"])
    ap.add_argument("--project", required=True)
    ap.add_argument(
        "--icij-entities",
        type=Path,
        help="nodes-entities.csv from the ICIJ bulk download (build only)",
    )
    ap.add_argument(
        "--icij-as-of", help="the date the ICIJ dump was generated, YYYY-MM-DD (build only)"
    )
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if args.command == "lists":
        summary = build_lists(args.project)
        print("warm_reference lists reloaded:", ", ".join(f"{t}={n}" for t, n in summary.items()))
    if not (args.icij_entities and args.icij_as_of):
        sys.stderr.write("error: build needs --icij-entities and --icij-as-of\n")
        return 2
    summary = build_reference(args.project, args.icij_entities, args.icij_as_of)
    print("warm_reference built:", ", ".join(f"{t}={n}" for t, n in summary.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
