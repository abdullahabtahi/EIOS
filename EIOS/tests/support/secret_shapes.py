"""Secret-shaped strings assembled at call time.

No literal below matches a secret scanner on its own, so the repository itself stays clean
while tests can still plant realistic-looking secrets into throwaway trees.
"""

from __future__ import annotations

_FILLER = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0"


def cloud_access_key() -> str:
    return "AK" + "IA" + _FILLER[:16].upper()


def api_key() -> str:
    return "AI" + "za" + _FILLER[:35]


def vcs_token() -> str:
    return "gh" + "p_" + _FILLER[:36]


def private_key_block() -> str:
    header = "-----BEGIN " + "PRIVATE KEY-----"
    footer = "-----END " + "PRIVATE KEY-----"
    return f"{header}\n{_FILLER}\n{footer}"


def all_shapes() -> dict[str, str]:
    return {
        "cloud_access_key": cloud_access_key(),
        "api_key": api_key(),
        "vcs_token": vcs_token(),
        "private_key_block": private_key_block(),
    }
