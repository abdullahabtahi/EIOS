"""``python -m tools.open_decision_check [--repo-root DIR]``; exits 0 pass, 1 findings, 2 error."""

from __future__ import annotations

import sys

from tools.open_decision_check.engine import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
