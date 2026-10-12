"""Single-pass prompt rendering with trusted and untrusted slots.

Template slots are ``{{name}}`` (trusted text the caller controls) and ``{{untrusted:name}}``
(external text, which must arrive wrapped by ``untrusted_text`` and renders as a delimited
block labelled untrusted). Substitution happens once, so input text can never introduce a slot.
Errors name slots only and never echo input values.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from eios.common.errors import BoundaryValidationError
from eios.common.untrusted_text import UntrustedText

_SLOT = re.compile(r"\{\{(untrusted:)?([a-z_][a-z0-9_]{0,63})\}\}")
_SAFE_NAME = re.compile(r"[a-z_][a-z0-9_]{0,63}")


def _fail(message: str, names: list[str]) -> BoundaryValidationError:
    paths = tuple(f"inputs.{n if _SAFE_NAME.fullmatch(n) else '<redacted>'}" for n in names)
    return BoundaryValidationError(message, paths)


def template_slots(template: str) -> dict[str, bool]:
    """Map each slot name to whether it is untrusted. A name cannot be both kinds."""
    slots: dict[str, bool] = {}
    for match in _SLOT.finditer(template):
        untrusted = match.group(1) is not None
        name = match.group(2)
        if slots.setdefault(name, untrusted) != untrusted:
            raise _fail("template uses a slot as both trusted and untrusted", [name])
    return slots


def _value_problems(
    slots: Mapping[str, bool], inputs: Mapping[str, str | UntrustedText]
) -> tuple[list[str], list[str]]:
    missing = [n for n in slots if n not in inputs]
    wrong = [
        n
        for n, untrusted in slots.items()
        if n in inputs
        and not (isinstance(inputs[n], UntrustedText) if untrusted else isinstance(inputs[n], str))
    ]
    return missing, wrong


def render_prompt(template: str, inputs: Mapping[str, str | UntrustedText]) -> str:
    """Fill ``template`` from ``inputs`` or raise BoundaryValidationError."""
    slots = template_slots(template)
    missing, wrong = _value_problems(slots, inputs)
    extra = [n for n in inputs if n not in slots]
    if missing or wrong or extra:
        raise _fail(
            "inputs do not match the prompt template "
            f"(missing={len(missing)}, wrong_kind={len(wrong)}, unexpected={len(extra)})",
            [*missing, *wrong, *extra],
        )

    def substitute(match: re.Match[str]) -> str:
        value = inputs[match.group(2)]
        return value.render_block() if isinstance(value, UntrustedText) else value

    return _SLOT.sub(substitute, template)
