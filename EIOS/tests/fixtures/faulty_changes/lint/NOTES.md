# lint overlay

Adds `src/skeleton/lint_violation.py` with an unused import (ruff F401). Only the `lint` gate may fail: the file is formatted, type-clean, and adds one statement, which keeps coverage above 80% `[TARGET]`.
