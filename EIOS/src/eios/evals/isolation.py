"""IAM and process boundary guards for evaluation ground-truth storage (ADR-015, T009)."""

import json
from pathlib import Path
from typing import Any

AUTHORIZED_EVAL_ROLES = frozenset({"sa-eval-harness", "admin"})


class GroundTruthAccessDeniedError(PermissionError):
    """Raised when an unauthorized agent or service attempts to access eval-truth."""

    pass


def read_ground_truth(
    truth_dir: Path | str,
    filename: str,
    caller_role: str,
) -> dict[str, Any]:
    """Read a ground-truth dataset or manifest under strict role-based boundary control.

    Args:
        truth_dir: Base directory path for ground-truth storage (e.g. eval-truth/).
        filename: Relative path or filename of target ground-truth artifact.
        caller_role: Identity of calling agent or service (e.g. sa-eval-harness).

    Returns:
        Parsed ground-truth dictionary.

    Raises:
        GroundTruthAccessDeniedError: If caller role is not authorized.
        FileNotFoundError: If the requested ground truth file does not exist.
    """
    if caller_role not in AUTHORIZED_EVAL_ROLES:
        raise GroundTruthAccessDeniedError(
            f"Access denied to ground truth file '{filename}' for caller role '{caller_role}'. "
            f"Authorized roles are: {', '.join(sorted(AUTHORIZED_EVAL_ROLES))}."
        )

    base_path = Path(truth_dir)
    target_file = base_path / filename

    if not target_file.is_file():
        raise FileNotFoundError(f"Ground truth file '{filename}' not found in '{base_path}'.")

    with open(target_file, encoding="utf-8") as f:
        return json.load(f)
