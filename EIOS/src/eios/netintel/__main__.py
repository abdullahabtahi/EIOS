"""python -m eios.netintel build --project <id> [--ipinfo-file <ipinfo_lite.csv.gz>]

Builds the address-check snapshot into `warm_reference`. Without `--ipinfo-file` the Lite database is downloaded with
the token in EIOS_IPINFO_TOKEN (a free IPinfo token; it is used here only and never ships with the service).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from eios.netintel.store import build_snapshot, download_ipinfo


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m eios.netintel")
    ap.add_argument("command", choices=["build"])
    ap.add_argument("--project", required=True)
    ap.add_argument("--ipinfo-file", type=Path, help="an already downloaded ipinfo_lite.csv.gz")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    path = args.ipinfo_file
    if path is None:
        token = os.environ.get("EIOS_IPINFO_TOKEN", "")
        if not token:
            ap.error("set EIOS_IPINFO_TOKEN or pass --ipinfo-file")
        path = download_ipinfo(token)
    summary = build_snapshot(args.project, path)
    print("address-check snapshot built:", ", ".join(f"{t}={n}" for t, n in summary.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
