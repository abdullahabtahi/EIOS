"""Typed results of the geo capabilities (`geo_tools.py`): what the model reads, with a unit for every figure.

Every result lists `map_targets`, the objects it can show on the map. The assembler moves the map only to a target a
tool of the same turn returned, the way it shows only a figure a tool returned (`assistant/map_commands.py`).
"""

from __future__ import annotations

from enum import StrEnum

from eios.common.validation import StrictModel
from eios.ontology.omcp.port.contracts import ToolResult


class MapKind(StrEnum):
    COUNTRY = "country"
    CORRIDOR = "corridor"
    MISMATCH = "mismatch"
    GATEWAY = "gateway"
    ACCOUNT = "account"


class MapTarget(StrictModel):
    kind: MapKind
    target_id: str


class CountryStanding(StrictModel):
    iso2: str
    name: str
    fatf_list: str | None
    eu_high_risk: bool
    basel_score: float | None
    basel_rank: int | None
    basel_band: str | None
    offshore_entities: int | None


STANDING_UNITS = {
    "basel_score": "score",
    "basel_rank": "rank",
    "offshore_entities": "entities",
}


def standing_units(prefix: str) -> dict[str, str]:
    return {f"{prefix}.{path}": unit for path, unit in STANDING_UNITS.items()}


# --- overview and leads ----------------------------------------------------------------------------------


class LensCount(StrictModel):
    lens: str
    flagged: int | None  # None: this lens cannot run here, which is not "nobody flagged"
    assessable: int | None


class ExitLead(StrictModel):
    gateway_id: str
    country: str
    accounts: int
    home_countries: int
    impossible_jumps: int


class CorridorLead(StrictModel):
    corridor_id: str
    origin: str
    destination: str
    tier: str | None
    volume_usd: float
    accounts: int
    events: int


class PairLead(StrictModel):
    pair_id: str
    kyc_country: str
    ip_country: str
    accounts: int
    events: int
    foreign_events: int
    volume_usd: float
    sample_accounts: list[str]


class AccountLead(StrictModel):
    account_id: str
    kyc_country: str
    geo_score: float
    flags: list[str]


def _lead_units(prefix: str) -> dict[str, str]:
    return {
        f"{prefix}exits[].accounts": "accounts",
        f"{prefix}exits[].home_countries": "countries",
        f"{prefix}exits[].impossible_jumps": "jumps",
        f"{prefix}corridors[].volume_usd": "USD",
        f"{prefix}corridors[].accounts": "accounts",
        f"{prefix}corridors[].events": "payments",
        f"{prefix}pairs[].accounts": "accounts",
        f"{prefix}pairs[].events": "payments",
        f"{prefix}pairs[].foreign_events": "payments",
        f"{prefix}pairs[].volume_usd": "USD",
        f"{prefix}accounts[].geo_score": "score",
    }


class GeoOverview(ToolResult):
    clients: int
    lenses: list[LensCount]
    shared_exits: int | None
    hubs_suppressed: int | None
    elevated_corridors: int | None
    top_exits: list[ExitLead]
    top_corridors: list[CorridorLead]
    top_accounts: list[AccountLead]
    map_targets: list[MapTarget]


OVERVIEW_UNITS = {
    "clients": "accounts",
    "lenses[].flagged": "accounts",
    "lenses[].assessable": "accounts",
    "shared_exits": "exits",
    "hubs_suppressed": "gateways",
    "elevated_corridors": "corridors",
    "top_exits[].accounts": "accounts",
    "top_exits[].home_countries": "countries",
    "top_exits[].impossible_jumps": "jumps",
    "top_corridors[].volume_usd": "USD",
    "top_corridors[].accounts": "accounts",
    "top_corridors[].events": "payments",
    "top_accounts[].geo_score": "score",
}


class GeoLeads(ToolResult):
    kind: str
    shown: int
    exits: list[ExitLead] | None = None
    corridors: list[CorridorLead] | None = None
    pairs: list[PairLead] | None = None
    accounts: list[AccountLead] | None = None
    map_targets: list[MapTarget]


LEADS_UNITS = {"shown": "leads", **_lead_units("")}


# --- one exit --------------------------------------------------------------------------------------------


class HomeCount(StrictModel):
    iso2: str
    accounts: int


class ExitRule(StrictModel):
    min_shared_accounts: int
    min_sessions: int
    hub_degree: int


class RingMember(StrictModel):
    account_id: str
    kyc_country: str
    link_kind: str
    via_account_id: str


class ExitRing(StrictModel):
    source: str | None
    seconds: float | None
    graph_users: int | None
    linked_total: int | None
    linked: list[RingMember] | None
    error: str | None


class SharedExitEvidence(ToolResult):
    gateway_id: str
    country: CountryStanding
    hub: bool
    shared_exit: bool
    accounts: int
    sessions: int
    foreign_accounts: int
    flagged_accounts: int
    home_countries: list[HomeCount]
    home_country_count: int
    impossible_jumps: int
    sample_accounts: list[str]
    rule: ExitRule
    hubs_in_country: int
    ring: ExitRing | None
    map_targets: list[MapTarget]


EXIT_UNITS = {
    "accounts": "accounts",
    "sessions": "sessions",
    "foreign_accounts": "accounts",
    "flagged_accounts": "accounts",
    "home_countries[].accounts": "accounts",
    "home_country_count": "countries",
    "impossible_jumps": "jumps",
    "rule.min_shared_accounts": "accounts",
    "rule.min_sessions": "sessions",
    "rule.hub_degree": "accounts",
    "hubs_in_country": "gateways",
    "ring.seconds": "seconds",
    "ring.graph_users": "accounts",
    "ring.linked_total": "accounts",
    **standing_units("country"),
}


# --- one corridor ----------------------------------------------------------------------------------------


class CorridorAccount(StrictModel):
    account_id: str
    volume_usd: float


class CorridorEvidence(ToolResult):
    corridor_id: str
    tier: str | None
    volume_usd: float
    accounts: int
    events: int
    deposits: int
    withdrawals: int
    origin: CountryStanding
    destination: CountryStanding
    top_accounts: list[CorridorAccount]
    map_targets: list[MapTarget]


CORRIDOR_UNITS = {
    "volume_usd": "USD",
    "accounts": "accounts",
    "events": "payments",
    "deposits": "payments",
    "withdrawals": "payments",
    "top_accounts[].volume_usd": "USD",
    **standing_units("origin"),
    **standing_units("destination"),
}


# --- one jurisdiction ------------------------------------------------------------------------------------


class JurisdictionEvidence(ToolResult):
    country_id: str
    standing: CountryStanding
    reference_layer: str
    engine_tier: str | None
    registered_accounts: int
    login_accounts: int | None
    sessions: int | None
    gateways: int | None
    payment_accounts: int
    payment_volume_usd: float
    shared_exits: list[str] | None
    exposed_accounts: int
    corridors: int
    corridor_volume_usd: float
    map_targets: list[MapTarget]


JURISDICTION_UNITS = {
    "registered_accounts": "accounts",
    "login_accounts": "accounts",
    "sessions": "sessions",
    "gateways": "gateways",
    "payment_accounts": "accounts",
    "payment_volume_usd": "USD",
    "exposed_accounts": "accounts",
    "corridors": "corridors",
    "corridor_volume_usd": "USD",
    **standing_units("standing"),
}
