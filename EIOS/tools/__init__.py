"""Make ``src/`` importable for ``uv run python -m tools.*`` (the project is not installed)."""

import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.append(_SRC)  # last, so it can never shadow anything already importable
