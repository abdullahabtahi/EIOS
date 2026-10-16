"""Geo capabilities for the geospatial workstation: the geo engine, BigQuery Graph and the published lists as evidence.

Each handler reads the geo read model (`dataplane/geo_readmodel.py`) through the deterministic evidence functions the
cockpit routes also use, so the map and an answer show the same numbers. Arguments are ids in the map's own formats
(`GW-NG-X00`, `ID>MM`, `NG`, `CR11568`); a wrong shape is refused with the field named, so the model can correct it.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from eios.common.validation import StrictModel
from eios.dataplane.aml_geo import GeoSnapshot
from eios.dataplane.geo_evidence import (
    LEAD_KINDS,
    corridor,
    jurisdiction,
    leads,
    overview,
    shared_exit,
)
from eios.dataplane.geo_lists import list_change
from eios.dataplane.geo_readmodel import GeoReadModel
from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.common import envelope
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode
from eios.ontology.omcp.port.geo_account import account_evidence
from eios.ontology.omcp.port.geo_case_models import (
    ACCOUNT_UNITS,
    LIST_CHANGE_UNITS,
    GeoAccountEvidence,
    ListChangeImpact,
)
from eios.ontology.omcp.port.geo_models import (
    CORRIDOR_UNITS,
    EXIT_UNITS,
    JURISDICTION_UNITS,
    LEADS_UNITS,
    OVERVIEW_UNITS,
    CorridorEvidence,
    GeoLeads,
    GeoOverview,
    JurisdictionEvidence,
    MapKind,
    MapTarget,
    SharedExitEvidence,
)
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import Handler, ToolSpec
from eios.reference.editions import ListId, editions

GEO = (Workstation.GEOSPATIAL,)
PRIVATE = (SecurityMarking.PII, SecurityMarking.SENSITIVE_COMPLIANCE)
_SVC = "dataplane.geo_evidence"
MAX_TARGETS = (
    12  # [ASSUMPTION] objects one result offers the map; enough for a ring's first members
)


class LeadKind(StrEnum):
    SHARED_EXIT = "shared_exit"
    CORRIDOR = "corridor"
    LOGIN_COUNTRY = "login_country"
    ACCOUNT = "account"


class _Upper(StrictModel):
    @field_validator("*", mode="before")
    @classmethod
    def _upper(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value


class NoArgs(StrictModel):
    pass


class LeadsArgs(StrictModel):
    kind: LeadKind
    limit: int = Field(default=10, ge=1, le=20)


class ExitArgs(_Upper):
    gateway_id: str = Field(pattern=r"^GW-[A-Z]{2}-[A-Z][0-9]{2}$")


class CorridorArgs(_Upper):
    corridor_id: str = Field(pattern=r"^[A-Z]{2}>[A-Z]{2}$")


class GeoAccountArgs(_Upper):
    entity_id: str = Field(pattern=r"^CR[0-9]{3,8}$")


class CountryArgs(_Upper):
    country_id: str = Field(pattern=r"^[A-Z]{2}$")


class ListChangeArgs(StrictModel):
    list_id: ListId


def _geo(ctx: ReadModels) -> tuple[GeoReadModel, GeoSnapshot]:
    geo = ctx.geo
    snap = geo.snapshot() if geo is not None else None
    if geo is None or snap is None:
        raise PortError(ToolErrorCode.DATA_UNAVAILABLE, "the geo plane is not built here")
    return geo, snap


def _envelope(
    ctx: ReadModels,
    geo: GeoReadModel,
    snap: GeoSnapshot,
    capability: str,
    entity_id: str | None,
    units: dict[str, str],
) -> dict[str, Any]:
    """The common envelope, stamped with the world's own as-of rather than the wall clock."""
    as_of: datetime = snap.world.config.as_of
    return {
        **envelope(ctx, capability, entity_id, _SVC, units, PRIVATE, origin=geo.origin),
        "as_of": as_of,
    }


def target(kind: MapKind, target_id: str) -> MapTarget:
    return MapTarget(kind=kind, target_id=target_id)


def _targets(*groups: list[MapTarget]) -> list[MapTarget]:
    seen: dict[tuple[str, str], MapTarget] = {}
    for group in groups:
        for t in group:
            seen.setdefault((t.kind.value, t.target_id), t)
    return list(seen.values())[:MAX_TARGETS]


def get_geo_overview(ctx: ReadModels, _who: Principal, _args: NoArgs) -> GeoOverview:
    geo, snap = _geo(ctx)
    o = overview(snap)
    return GeoOverview.model_validate(
        {
            **_envelope(ctx, geo, snap, "geo.overview", None, OVERVIEW_UNITS),
            **{k: v for k, v in o.items() if k not in {"as_of", "source"}},
            "lens_count": len(o["lenses"]),
            "map_targets": _targets(
                [target(MapKind.GATEWAY, e["gateway_id"]) for e in o["top_exits"]],
                [target(MapKind.CORRIDOR, c["corridor_id"]) for c in o["top_corridors"]],
                [target(MapKind.ACCOUNT, a["account_id"]) for a in o["top_accounts"]],
                [target(MapKind.COUNTRY, h["iso2"]) for h in o["login_hotspots"]],
            ),
        }
    )


_LEAD_FIELD = {
    LeadKind.SHARED_EXIT: ("exits", MapKind.GATEWAY, "gateway_id"),
    LeadKind.CORRIDOR: ("corridors", MapKind.CORRIDOR, "corridor_id"),
    LeadKind.LOGIN_COUNTRY: ("pairs", MapKind.MISMATCH, "pair_id"),
    LeadKind.ACCOUNT: ("accounts", MapKind.ACCOUNT, "account_id"),
}
LEAD_VOCABULARY = frozenset(
    LEAD_KINDS
)  # the evidence module's kinds; a test holds `LeadKind` to them


def list_geo_leads(ctx: ReadModels, _who: Principal, args: LeadsArgs) -> GeoLeads:
    geo, snap = _geo(ctx)
    rows = leads(snap, args.kind.value, args.limit)
    field, kind, key = _LEAD_FIELD[args.kind]
    return GeoLeads.model_validate(
        {
            **_envelope(ctx, geo, snap, "geo.leads", args.kind.value, LEADS_UNITS),
            "kind": args.kind.value,
            "shown": len(rows),
            field: rows,
            "map_targets": _targets([target(kind, r[key]) for r in rows]),
        }
    )


def _ring_view(ring: dict[str, Any] | None) -> dict[str, Any] | None:
    """The ring as the result names it: a member's linking account is an id field, so it is never read as a figure."""
    if ring is None:
        return None
    members = ring.get("linked")
    return {
        **{k: ring.get(k) for k in ("source", "seconds", "graph_users", "linked_total", "error")},
        "linked": None
        if members is None
        else [
            {
                "account_id": m["account_id"],
                "kyc_country": m["kyc_country"],
                "link_kind": m["link_kind"],
                "via_account_id": m["via_account"],
            }
            for m in members
        ],
    }


def get_shared_exit(ctx: ReadModels, _who: Principal, args: ExitArgs) -> SharedExitEvidence:
    geo, snap = _geo(ctx)
    countries, _ = geo.reference()
    e = shared_exit(snap, geo.graph(), countries, args.gateway_id)
    if e is None:
        raise PortError(ToolErrorCode.NOT_FOUND, f"no gateway {args.gateway_id} in this book")
    linked = (e["ring"] or {}).get("linked") or []
    return SharedExitEvidence.model_validate(
        {
            **_envelope(ctx, geo, snap, "geo.exit", args.gateway_id, EXIT_UNITS),
            **{k: v for k, v in e.items() if k not in {"as_of", "source", "ring"}},
            "home_country_count": len(e["home_countries"]),
            "ring": _ring_view(e["ring"]),
            "map_targets": _targets(
                [
                    target(MapKind.GATEWAY, args.gateway_id),
                    target(MapKind.COUNTRY, e["country"]["iso2"]),
                ],
                [target(MapKind.ACCOUNT, a) for a in e["sample_accounts"]],
                [target(MapKind.ACCOUNT, m["account_id"]) for m in linked],
            ),
        }
    )


def get_corridor(ctx: ReadModels, _who: Principal, args: CorridorArgs) -> CorridorEvidence:
    geo, snap = _geo(ctx)
    origin, destination = args.corridor_id.split(">")
    countries, _ = geo.reference()
    c = corridor(snap, countries, origin, destination)
    if c is None:
        raise PortError(
            ToolErrorCode.NOT_FOUND, f"no money moves on {args.corridor_id} in this book"
        )
    return CorridorEvidence.model_validate(
        {
            **_envelope(ctx, geo, snap, "geo.corridor", args.corridor_id, CORRIDOR_UNITS),
            **{k: v for k, v in c.items() if k not in {"as_of", "source"}},
            "map_targets": _targets(
                [target(MapKind.CORRIDOR, args.corridor_id)],
                [target(MapKind.COUNTRY, origin), target(MapKind.COUNTRY, destination)],
                [target(MapKind.ACCOUNT, a["account_id"]) for a in c["top_accounts"]],
            ),
        }
    )


def get_geo_account(ctx: ReadModels, _who: Principal, args: GeoAccountArgs) -> GeoAccountEvidence:
    geo, snap = _geo(ctx)
    found = account_evidence(snap, geo.graph(), args.entity_id)
    if found is None:
        raise PortError(ToolErrorCode.NOT_FOUND, f"no account {args.entity_id} in this book")
    return GeoAccountEvidence.model_validate(
        {**_envelope(ctx, geo, snap, "geo.account", args.entity_id, ACCOUNT_UNITS), **found}
    )


def get_jurisdiction(ctx: ReadModels, _who: Principal, args: CountryArgs) -> JurisdictionEvidence:
    geo, snap = _geo(ctx)
    countries, layer = geo.reference()
    j = jurisdiction(snap, countries, args.country_id)
    return JurisdictionEvidence.model_validate(
        {
            **_envelope(ctx, geo, snap, "geo.jurisdiction", args.country_id, JURISDICTION_UNITS),
            **{k: v for k, v in j.items() if k not in {"as_of", "source"}},
            "reference_layer": layer,
            "map_targets": _targets(
                [target(MapKind.COUNTRY, args.country_id)],
                [target(MapKind.GATEWAY, g) for g in j["shared_exits"] or []],
            ),
        }
    )


def _with_shares(group: dict[str, Any]) -> dict[str, Any]:
    """A group's countries with each one's share of the group's sessions and payments (None: nothing to share)."""
    sessions, payments = group["session_shares"] or {}, group["payment_shares"] or {}
    return {
        "countries": [
            {
                **row,
                "session_share_pct": sessions.get(row["iso2"]),
                "payment_share_pct": payments.get(row["iso2"]),
            }
            for row in group["countries"]
        ],
        **{k: group[k] for k in ("exposed_accounts", "sessions", "payment_volume_usd")},
    }


def get_list_change_impact(
    ctx: ReadModels, _who: Principal, args: ListChangeArgs
) -> ListChangeImpact:
    geo, snap = _geo(ctx)
    out = list_change(snap, geo.graph(), editions(args.list_id))
    groups = {name: _with_shares(out[name]) for name in ("added", "removed", "relisted")}
    rows = [row for g in groups.values() for row in g["countries"]]
    return ListChangeImpact.model_validate(
        {
            **_envelope(ctx, geo, snap, "geo.list_change", args.list_id.value, LIST_CHANGE_UNITS),
            **{k: out[k] for k in ("list_id", "before", "after", "graph")},
            **groups,
            "map_targets": _targets(
                [target(MapKind.COUNTRY, r["iso2"]) for r in rows],
                [target(MapKind.GATEWAY, g) for r in rows for g in r["shared_exits"] or []],
            ),
        }
    )


def _spec(
    name: str, capability: str, args: type[StrictModel], out: type[Any], fn: Handler, budget: float
) -> ToolSpec:
    return ToolSpec(
        name=name,
        capability=capability,
        kind="evidence",
        workstations=GEO,
        args_model=args,
        result_model=out,
        handler=fn,
        budget_ms=budget,
        markings=PRIVATE,
    )


# Budgets [ASSUMPTION]: an in-memory read is well under the port's default; a BigQuery Graph job takes about two
# seconds warm and nine cold [MEASURED, docs/geospatial-milestones.md N1], so the three that query the graph get more.
TOOLS: tuple[ToolSpec, ...] = (
    _spec("get_geo_overview", "geo.overview", NoArgs, GeoOverview, get_geo_overview, 300.0),
    _spec("list_geo_leads", "geo.leads", LeadsArgs, GeoLeads, list_geo_leads, 300.0),
    _spec("get_shared_exit", "geo.exit", ExitArgs, SharedExitEvidence, get_shared_exit, 3000.0),
    _spec("get_corridor", "geo.corridor", CorridorArgs, CorridorEvidence, get_corridor, 300.0),
    _spec(
        "get_geo_account",
        "geo.account",
        GeoAccountArgs,
        GeoAccountEvidence,
        get_geo_account,
        3000.0,
    ),
    _spec(
        "get_jurisdiction",
        "geo.jurisdiction",
        CountryArgs,
        JurisdictionEvidence,
        get_jurisdiction,
        300.0,
    ),
    _spec(
        "get_list_change_impact",
        "geo.list_change",
        ListChangeArgs,
        ListChangeImpact,
        get_list_change_impact,
        3000.0,
    ),
)
