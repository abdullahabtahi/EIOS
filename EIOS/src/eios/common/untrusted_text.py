"""Untrusted external text: data, never instructions (FR-020, RL-6 hook point).

Public API:
- ``wrap_untrusted(text, *, source, max_chars=DEFAULT_MAX_CHARS)``: the only factory.
- ``UntrustedText.as_untrusted_str()``: explicit accessor; the sanitized, escaped text.
- ``UntrustedText.render_block()``: delimited block for prompts, tagged ``trust="untrusted"``.
- ``UntrustedText.source`` / ``.truncated``: provenance label and whether the cap cut the input.
- ``DEFAULT_MAX_CHARS``: default length cap.

There is no implicit ``str`` conversion on purpose: ``str(x)``, f-strings and ``+`` raise
TypeError, so untrusted text cannot slip into a prompt by accident.

Sanitisation order: strip control and format characters (keeping newline and tab, normalising
CRLF), apply the cap to the cleaned text, then escape ``&``, ``<``, ``>`` and code-fence runs.
Capping before escaping means an escape entity is never cut in half. Instruction-like content
is preserved as data; it is neutralised by marking and delimiting, not by being rewritten.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from eios.common.errors import BoundaryValidationError

# [ASSUMPTION] default cap; callers pass max_chars to override. Not derived from any brief.
DEFAULT_MAX_CHARS = 8000

_BLOCK_TAG = "untrusted_data"
_SOURCE_LABEL = re.compile(r"[a-z][a-z0-9_.-]{0,63}")
_FENCE_RUN = re.compile(r"`{3,}|~{3,}")
_KEPT_CONTROLS = frozenset("\n\t")
# Control (Cc), format (Cf: bidi overrides, zero-width) and surrogate (Cs) characters.
_STRIPPED_CATEGORIES = frozenset({"Cc", "Cf", "Cs"})
_ENTITY_BY_FENCE_CHAR = {"`": "&#96;", "~": "&#126;"}
_CONSTRUCTION_GUARD = object()


@dataclass(frozen=True, slots=True)
class UntrustedText:
    """Immutable wrapper; build it with ``wrap_untrusted``, never directly."""

    _text: str = field(repr=False)
    source: str
    truncated: bool
    _guard: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._guard is not _CONSTRUCTION_GUARD:
            raise TypeError("UntrustedText must be built with wrap_untrusted()")

    def as_untrusted_str(self) -> str:
        """Return the sanitized, escaped text. The name is the reminder: this is untrusted."""
        return self._text

    def render_block(self) -> str:
        """Return the text inside a delimited block labelled untrusted, for prompt assembly."""
        return (
            f'<{_BLOCK_TAG} source="{self.source}" trust="untrusted">\n'
            f"{self._text}\n</{_BLOCK_TAG}>"
        )

    def __repr__(self) -> str:
        return (
            f"UntrustedText(source={self.source!r}, chars={len(self._text)}, "
            f"truncated={self.truncated})"
        )

    def __str__(self) -> str:
        raise TypeError("UntrustedText has no implicit str conversion; use as_untrusted_str()")


def _strip_controls(text: str) -> str:
    unified = text.replace("\r\n", "\n")
    return "".join(
        ch
        for ch in unified
        if ch in _KEPT_CONTROLS or unicodedata.category(ch) not in _STRIPPED_CATEGORIES
    )


def _escape_fences(match: re.Match[str]) -> str:
    run = match.group()
    return _ENTITY_BY_FENCE_CHAR[run[0]] * len(run)


def _escape(text: str) -> str:
    entities = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return _FENCE_RUN.sub(_escape_fences, entities)


def wrap_untrusted(text: str, *, source: str, max_chars: int = DEFAULT_MAX_CHARS) -> UntrustedText:
    """Wrap external free text as untrusted data.

    Raises BoundaryValidationError for non-string text, a non-positive cap or an unsafe
    ``source`` label (lowercase token, at most 64 characters). Input values are never echoed.
    """
    if not isinstance(text, str):
        raise BoundaryValidationError("untrusted text must be a string", ("text",))
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise BoundaryValidationError("max_chars must be a positive integer", ("max_chars",))
    if not isinstance(source, str) or _SOURCE_LABEL.fullmatch(source) is None:
        raise BoundaryValidationError(
            "source must be a lowercase token of at most 64 characters", ("source",)
        )
    cleaned = _strip_controls(text)
    return UntrustedText(
        _escape(cleaned[:max_chars]),
        source,
        len(cleaned) > max_chars,
        _CONSTRUCTION_GUARD,
    )
