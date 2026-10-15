"""Country codes: ISO 3166 through pycountry, plus the offshore-leaks shorthand pycountry cannot know."""

from __future__ import annotations

import pycountry

# ICIJ's own jurisdiction codes and spellings that are not ISO 3166 alpha-2 or alpha-3. US states collapse to US.
_ICIJ_OVERRIDES: dict[str, str] = {
    "BAH": "BS",
    "BVI": "VG",
    "PMA": "PA",
    "SEY": "SC",
    "SAM": "WS",
    "NIUE": "NU",
    "COOK": "CK",
    "COK": "CK",
    "ANG": "AI",
    "NEV": "US",
    "USDE": "US",
    "WYO": "US",
    "CAYMN": "KY",
    "LABUA": "MY",
    "MAURI": "MU",
    "MALAY": "MY",
    "JSY": "JE",
    "GGY": "GG",
    "IOM": "IM",
    "BERMU": "BM",
    "LIBER": "LR",
    "MARSH": "MH",
    "VANU": "VU",
    "STLU": "LC",
    "DUBAI": "AE",
    "RAK": "AE",
    "THAIL": "TH",
    "BRUN": "BN",
    "NETH": "NL",
    "IRELD": "IE",
    "CHINA": "CN",
    "UK": "GB",
}
_UNDETERMINED = {"XXX", "XX", ""}


def to_iso2(code: str | None) -> str | None:
    """An ISO alpha-2 for an ICIJ or ISO code, or None when it is undetermined or unknown. Never guessed."""
    if code is None:
        return None
    key = code.strip().upper()
    if key in _UNDETERMINED:
        return None
    if key in _ICIJ_OVERRIDES:
        return _ICIJ_OVERRIDES[key]
    if len(key) == 2:
        return key if pycountry.countries.get(alpha_2=key) else None
    if len(key) == 3:
        country = pycountry.countries.get(alpha_3=key)
        return country.alpha_2 if country else None
    return None
