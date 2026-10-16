"""Typed results of the two geo capabilities closest to a decision: one account's geography, and a list change."""

from __future__ import annotations

from eios.common.validation import StrictModel
from eios.ontology.omcp.port.contracts import ToolResult
from eios.ontology.omcp.port.geo_models import MapTarget

# --- one account -----------------------------------------------------------------------------------------


class LoginCountry(StrictModel):
    iso2: str
    sessions: int


class AccountGateway(StrictModel):
    gateway_id: str
    country: str
    sessions: int
    accounts: int | None
    hub: bool | None
    shared_exit: bool | None


class JumpExample(StrictModel):
    from_country: str
    to_country: str
    hours: float
    km: int
    at: str


class Jumps(StrictModel):
    count: int
    via_hub: int
    examples: list[JumpExample]


class CrossBorder(StrictModel):
    iso2: str
    direction: str
    events: int
    volume_usd: float
    tier: str | None


class LensFinding(StrictModel):
    lens: str
    flag: bool
    assessable: bool | None  # None: the lens judges every account it sees (the shared exit)


class BenignReading(StrictModel):
    """An innocent explanation the account's own data supports. Read from the evidence, never guessed; carries no
    number, so it adds no figure to check."""

    code: str
    reading: str


class LensRule(StrictModel):
    """The thresholds the lenses apply, so "why was it flagged" is answered from the rule, not from a guess."""

    min_exit_sessions: int
    min_jumps: int
    max_speed_kmh: float
    min_jump_km: float
    login_alpha: float


class Neighbour(StrictModel):
    via: str
    link_id: str
    detail: str | None
    account_id: str
    kyc_country: str


class Neighbourhood(StrictModel):
    source: str | None
    seconds: float | None
    total: int | None
    rows: list[Neighbour] | None
    error: str | None


class GeoAccountEvidence(ToolResult):
    account_id: str
    kyc_country: str
    sessions: int
    login_countries: list[LoginCountry]
    # Counts the reader states ("two countries") come from here, never from the model counting a list (RL-1).
    login_country_count: int
    gateways: list[AccountGateway]
    gateway_count: int
    foreign_logins: int
    exit_gateway_id: str | None
    exit_sessions: int
    jumps: (
        Jumps | None
    )  # None: no country positions here, so travel cannot be judged (not "no jumps")
    payments: list[CrossBorder]
    findings: list[LensFinding]
    # What else could explain the pattern: false-lead control, stated beside the findings (geo rule 18).
    benign_readings: list[BenignReading]
    rule: LensRule
    geo_score: float
    neighbourhood: Neighbourhood
    map_targets: list[MapTarget]


ACCOUNT_UNITS = {
    "sessions": "sessions",
    "login_country_count": "countries",
    "gateway_count": "gateways",
    "login_countries[].sessions": "sessions",
    "gateways[].sessions": "sessions",
    "gateways[].accounts": "accounts",
    "foreign_logins": "sessions",
    "exit_sessions": "sessions",
    "jumps.count": "jumps",
    "jumps.via_hub": "jumps",
    "jumps.examples[].hours": "hours",
    "jumps.examples[].km": "km",
    "payments[].events": "payments",
    "payments[].volume_usd": "USD",
    "rule.min_exit_sessions": "sessions",
    "rule.min_jumps": "jumps",
    "rule.max_speed_kmh": "km/h",
    "rule.min_jump_km": "km",
    "rule.login_alpha": "probability",
    "geo_score": "score",
    "neighbourhood.seconds": "seconds",
    "neighbourhood.total": "accounts",
}


# --- a list change ---------------------------------------------------------------------------------------


class EditionInfo(StrictModel):
    label: str
    in_force: str
    source: str


class CountryChange(StrictModel):
    iso2: str
    name: str
    before: str | None
    after: str | None
    registered_accounts: int
    login_accounts: int | None
    sessions: int | None
    payment_accounts: int
    payment_volume_usd: float
    shared_exits: list[str] | None
    exposed_accounts: int
    linked_accounts: int | None  # None: the graph could not be asked
    session_share_pct: float | None
    payment_share_pct: float | None


class ChangeGroup(StrictModel):
    countries: list[CountryChange]
    exposed_accounts: int
    sessions: int
    payment_volume_usd: float


class GraphNote(StrictModel):
    source: str | None
    seconds: float | None
    error: str | None


class ListChangeImpact(ToolResult):
    list_id: str
    before: EditionInfo
    after: EditionInfo
    added: ChangeGroup
    removed: ChangeGroup
    relisted: ChangeGroup
    graph: GraphNote
    map_targets: list[MapTarget]


def _group_units(group: str) -> dict[str, str]:
    row = f"{group}.countries[]"
    return {
        f"{row}.registered_accounts": "accounts",
        f"{row}.login_accounts": "accounts",
        f"{row}.sessions": "sessions",
        f"{row}.payment_accounts": "accounts",
        f"{row}.payment_volume_usd": "USD",
        f"{row}.exposed_accounts": "accounts",
        f"{row}.linked_accounts": "accounts",
        f"{row}.session_share_pct": "percent",
        f"{row}.payment_share_pct": "percent",
        f"{group}.exposed_accounts": "accounts",
        f"{group}.sessions": "sessions",
        f"{group}.payment_volume_usd": "USD",
    }


LIST_CHANGE_UNITS = {
    **_group_units("added"),
    **_group_units("removed"),
    **_group_units("relisted"),
    "graph.seconds": "seconds",
}
