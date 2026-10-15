"""The EU's list of high-risk third countries with strategic AML/CFT deficiencies, entity-free (docs/data-strategy.md section 6).

[EXTERNAL] Read from the European Commission's page on 2026-10-15; it lists 26 jurisdictions with their entries into
force and offers no data file, so the table is transcribed. The list is set by Delegated Regulation (EU) 2016/1675 as
amended, most recently by 2026/46 (adds the Russian Federation) and 2026/83 (adds Bolivia and the British Virgin
Islands, removes Burkina Faso, Mali, Mozambique, Nigeria, South Africa and Tanzania), both in force on 2026-01-29.
It differs from the FATF lists: the EU follows the FATF with a lag and adds its own entries. A listing triggers
mandatory enhanced due diligence under Article 18a of Directive (EU) 2015/849.
"""

from __future__ import annotations

AS_OF = "2026-01-29"  # the latest amendment in force; the page was read on 2026-10-15
SOURCE = (
    "EU high-risk third countries, Delegated Regulation (EU) 2016/1675 as amended to 2026/83 "
    "(finance.ec.europa.eu, read 2026-10-15)"
)
LIST_NAME = "eu_high_risk"

_CODES = (
    "AF",
    "DZ",
    "AO",
    "BO",
    "VG",
    "CM",
    "CI",
    "KP",
    "CD",
    "HT",
    "IR",
    "KE",
    "LA",
    "LB",
    "MC",
    "MM",
    "NA",
    "NP",
    "RU",
    "SS",
    "SY",
    "TT",
    "VU",
    "VE",
    "VN",
    "YE",
)

EU_ROWS: list[dict[str, str]] = [
    {"iso2": c, "list_name": LIST_NAME, "source": SOURCE, "as_of": AS_OF} for c in _CODES
]
