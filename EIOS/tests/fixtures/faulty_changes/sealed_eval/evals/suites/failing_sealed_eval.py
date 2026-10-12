"""Overlay suite: sealed evaluation failed: release candidate below baseline"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SUITE_ID = "failing-sealed-eval"
REPORT = Path("evals") / "reports" / f"{SUITE_ID}.json"


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"suite": SUITE_ID, "passed": False}) + "\n", encoding="utf-8")
    print("sealed evaluation failed: release candidate below baseline", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
