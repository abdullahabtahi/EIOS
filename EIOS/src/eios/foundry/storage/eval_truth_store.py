"""Isolated ground-truth store with IAM role-based simulation checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AccessDeniedError(PermissionError):
    """Raised when an unprivileged role attempts to read ground truth."""

    pass


class EvalTruthStore:
    """Manages deposition and retrieval of evaluation ground truth datasets."""

    ALLOWED_ROLES = {"eval-harness", "ci-pipeline", "admin"}
    DENIED_ROLES = {"reasoning-mesh", "cockpit-api", "analyst", "agent"}

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write_truth(self, filename: str, data: dict[str, Any]) -> Path:
        """Writes ground truth to isolated storage."""
        if not filename.endswith(".json"):
            filename = f"{filename}.json"
        target_path = self.base_dir / filename
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(data, indent=2, sort_keys=True))
        return target_path

    def read_truth(self, filename: str, role: str) -> dict[str, Any]:
        """Reads ground truth enforcing role-based access denial."""
        if role in self.DENIED_ROLES or role not in self.ALLOWED_ROLES:
            raise AccessDeniedError(f"Access to eval-truth denied for role: {role}")

        if not filename.endswith(".json"):
            filename = f"{filename}.json"
        target_path = self.base_dir / filename
        if not target_path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {target_path}")

        return json.loads(target_path.read_text())


EvalGroundTruthStore = EvalTruthStore
