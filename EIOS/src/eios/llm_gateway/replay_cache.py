"""Replay key and replay store contract (FR-025).

The key is a sha256 over a length-prefixed encoding of the prompt id, prompt version, inputs
and configuration identity, so component boundaries are unambiguous and input order does not
matter. Untrusted inputs contribute their sanitized text and source label.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from eios.common.untrusted_text import UntrustedText
from eios.common.validation import StrictModel


class StoredReplay(StrictModel):
    content: str
    stored_at: datetime


class ReplayStore(Protocol):
    def get(self, key: str) -> StoredReplay | None: ...

    def put(self, key: str, content: str, stored_at: datetime) -> None: ...


def _frame(part: str) -> bytes:
    raw = part.encode("utf-8")
    return len(raw).to_bytes(8, "big") + raw


def _input_text(value: str | UntrustedText) -> str:
    if isinstance(value, UntrustedText):
        return f"untrusted:{value.source}:{value.as_untrusted_str()}"
    return f"trusted:{value}"


def replay_key(
    *,
    prompt_id: str,
    prompt_version: str,
    inputs: Mapping[str, str | UntrustedText],
    config_identity: str,
) -> str:
    """Hex digest identifying a request for caching and replay."""
    digest = hashlib.sha256()
    for part in (prompt_id, prompt_version, config_identity, str(len(inputs))):
        digest.update(_frame(part))
    for name in sorted(inputs):
        digest.update(_frame(name))
        digest.update(_frame(_input_text(inputs[name])))
    return digest.hexdigest()
