"""The single finding shape every gate and check tool emits."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Finding:
    """One violation: where it is, which rule fired, and what is wrong."""

    file: str
    line: int
    rule_id: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.file, str) or not self.file:
            raise ValueError("finding.file must be a non-empty string")
        if not isinstance(self.line, int) or isinstance(self.line, bool) or self.line < 0:
            raise ValueError("finding.line must be a non-negative integer")
        if not isinstance(self.rule_id, str) or not self.rule_id:
            raise ValueError("finding.rule_id must be a non-empty string")
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("finding.message must be a non-empty string")

    def to_dict(self) -> dict[str, object]:
        return {
            "file": self.file,
            "line": self.line,
            "rule_id": self.rule_id,
            "message": self.message,
        }
