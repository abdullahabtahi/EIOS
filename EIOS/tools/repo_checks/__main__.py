"""``python -m tools.repo_checks [service-docs|forbidden-artifacts] [--repo-root DIR]``; exits 0, 1 findings, 2 error.

Without a subcommand every enabled hygiene check runs; ``service-docs`` runs only the service
documentation check (FR-039); ``forbidden-artifacts`` runs only the tracked plan/state/key guard.
"""

from __future__ import annotations

import sys

from tools.repo_checks.runner import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
