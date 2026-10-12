"""Overlay suite: resilience check failed: service did not recover after restart"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SUITE_ID = "resilience-failing-restart"
REPORT = Path("evals") / "reports" / f"{SUITE_ID}.json"


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"suite": SUITE_ID, "passed": False}) + "\n", encoding="utf-8")
    print("resilience check failed: service did not recover after restart", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
