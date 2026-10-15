"""FATF jurisdiction lists as of the 19 June 2026 plenary, entity-free and hand-curated (docs/data-strategy.md section 6).

[EXTERNAL, secondary] The FATF's own pages refuse scripted access, so this table was read from a secondary summary that
names the June 2026 changes (added Iraq and Bosnia and Herzegovina, removed Algeria and Namibia); a second summary listed
a different, older-looking grey list and was set aside. Verify against the FATF statement before formal use.
"""

from __future__ import annotations

AS_OF = "2026-06-19"
SOURCE = "FATF plenary statement, June 2026 (secondary summary; verify against fatf-gafi.org)"

_CALL_FOR_ACTION = ("IR", "KP", "MM")
_INCREASED_MONITORING = (
    "AO",
    "BO",
    "BA",
    "BG",
    "CM",
    "CI",
    "CD",
    "HT",
    "IQ",
    "KE",
    "KW",
    "LA",
    "LB",
    "MC",
    "NP",
    "PG",
    "SS",
    "SY",
    "VE",
    "VN",
    "VG",
    "YE",
)


def _rows(codes: tuple[str, ...], list_name: str) -> list[dict[str, str]]:
    return [{"iso2": c, "list_name": list_name, "source": SOURCE, "as_of": AS_OF} for c in codes]


FATF_ROWS: list[dict[str, str]] = _rows(_CALL_FOR_ACTION, "call_for_action") + _rows(
    _INCREASED_MONITORING, "increased_monitoring"
)
