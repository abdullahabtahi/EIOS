"""Typed error hierarchy rooted at EiosError."""

from __future__ import annotations


class EiosError(Exception):
    """Base for every error raised by EIOS code."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BoundaryValidationError(EiosError):
    """Input rejected at a system boundary; carries field paths, never rejected values."""

    def __init__(self, message: str, field_paths: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.field_paths = field_paths


class ConfigError(EiosError):
    """Configuration problem; the message always names the file and the path within it."""

    def __init__(self, file: str, path: str, message: str) -> None:
        super().__init__(f"{file}: {path}: {message}")
        self.file = file
        self.path = path


class ToolError(EiosError):
    """Tool or runtime failure (maps to exit code 2)."""
