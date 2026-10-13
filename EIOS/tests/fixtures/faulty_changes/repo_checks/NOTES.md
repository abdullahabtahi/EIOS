# repo_checks overlay

Adds `src/eios/mutable_model.py` with a dataclass that is not `frozen=True` (`repo.frozen_model`). Only the `repo_checks` gate may fail: the check scans only `src/eios`; the file is ruff-clean and formatted, so the other gates stay green.
