"""Graph tables of the AML world, derived straight from the world's frames (never from an engine's output).

Nodes: accounts, countries, login gateways and shared identifiers (devices, payment tokens, IP addresses). Edges: an
account is registered in a country, logs in through gateways, pays through countries' instruments and uses identifiers;
a gateway is located in a country. Because the tables come from the frames and not from the geo engine, a graph query
that agrees with the engine is an independent check of it. Country level only (P-2); synthetic accounts.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from eios.dataplane.aml_geo_sessions import HUB_DEGREE
from eios.foundry.scenarios.aml_world import AmlWorld

GRAPH_DATASET = "warm_graph"
GRAPH_NAME = "aml_geo"
NODE_TABLES = ("account", "country", "gateway", "identifier")
EDGE_TABLES = ("registered_in", "logged_in_via", "located_in", "paid_via", "uses")
_MONEY_STATUSES = ("COMPLETED", "PENDING")


@dataclass(frozen=True)
class GraphTables:
    fingerprint: (
        str  # the world these tables were built from; a store refuses tables from another world
    )
    frames: Mapping[str, pd.DataFrame]


def _sessions(world: AmlWorld) -> pd.DataFrame:
    if world.geo_sessions is None:
        raise ValueError("this world carries no login sessions")
    return world.geo_sessions


def _logins(sessions: pd.DataFrame) -> pd.DataFrame:
    by = sessions.groupby(["client_id", "gateway_id"])
    # BigQuery keeps microseconds; the world's session times carry nanoseconds
    return (
        pd.DataFrame(
            {
                "sessions": by.size(),
                "first_ts": by["ts"].min().dt.floor("us"),
                "last_ts": by["ts"].max().dt.floor("us"),
            }
        )
        .reset_index()
        .rename(columns={"client_id": "account_id"})
    )


def _gateways(sessions: pd.DataFrame) -> pd.DataFrame:
    by = sessions.groupby("gateway_id")
    table = pd.DataFrame(
        {"country": by["ip_country"].first(), "accounts": by["client_id"].nunique()}
    ).reset_index()
    table["hub"] = table["accounts"] > HUB_DEGREE  # RL-4
    return table


def _payments(world: AmlWorld) -> pd.DataFrame:
    """Cross-border money per account and instrument country, split by direction."""
    if world.geo_flows is None:
        raise ValueError("this world carries no geo flows")
    txn = world.transactions[["txn_id", "transaction_type", "amount", "status"]]
    home = world.clients.set_index("client_id")["country"]
    df = world.geo_flows.merge(txn, on="txn_id")
    df = df[
        df["status"].isin(_MONEY_STATUSES) & (df["instrument_country"] != df["client_id"].map(home))
    ]
    df = df.assign(
        direction=df["transaction_type"].map({"DEPOSIT": "in", "WITHDRAWAL": "out"}).fillna("other")
    )
    by = df.groupby(["client_id", "instrument_country", "direction"])
    return (
        pd.DataFrame({"events": by.size(), "volume_usd": by["amount"].sum().round(2)})
        .reset_index()
        .rename(columns={"client_id": "account_id", "instrument_country": "iso2"})
    )


def _identifiers(world: AmlWorld) -> tuple[pd.DataFrame, pd.DataFrame]:
    edges = world.edges
    uses = edges.rename(
        columns={"source_id": "account_id", "target_id": "identifier_id", "edge_type": "kind"}
    )[["account_id", "identifier_id", "kind"]].drop_duplicates(["account_id", "identifier_id"])
    by = edges.groupby("target_id")
    nodes = (
        pd.DataFrame(
            {
                "kind": by["edge_type"].first(),
                "shared_context": by["is_shared_context"].any(),
                "accounts": by["source_id"].nunique(),
            }
        )
        .reset_index()
        .rename(columns={"target_id": "identifier_id"})
    )
    nodes["hub"] = (
        nodes["accounts"] > HUB_DEGREE
    )  # RL-4: carrier-grade NAT addresses collapse out of rings
    return nodes, uses


def build_tables(
    world: AmlWorld, tiers: Mapping[str, str], names: Mapping[str, str] | None = None
) -> GraphTables:
    sessions = _sessions(world)
    logins = _logins(sessions)
    gateways = _gateways(sessions)
    payments = _payments(world)
    identifiers, uses = _identifiers(world)
    account = world.clients[["client_id", "country"]].rename(
        columns={"client_id": "account_id", "country": "kyc_country"}
    )
    codes = sorted(set(account["kyc_country"]) | set(gateways["country"]) | set(payments["iso2"]))
    country = pd.DataFrame(
        {
            "iso2": codes,
            "name": [(names or {}).get(c, c) for c in codes],
            "tier": [tiers.get(c) for c in codes],  # null when unrated: never "low" by default
        }
    )
    frames = {
        "account": account.reset_index(drop=True),
        "country": country,
        "gateway": gateways,
        "identifier": identifiers,
        "registered_in": account.rename(columns={"kyc_country": "iso2"}).reset_index(drop=True),
        "logged_in_via": logins,
        "located_in": gateways[["gateway_id", "country"]].rename(columns={"country": "iso2"}),
        "paid_via": payments,
        "uses": uses.reset_index(drop=True),
    }
    return GraphTables(fingerprint=world.config.fingerprint(), frames=frames)


def property_graph_ddl(project: str, dataset: str = GRAPH_DATASET) -> str:
    """CREATE PROPERTY GRAPH over the tables: every column is a property (the default)."""

    def t(name: str) -> str:
        return f"`{project}.{dataset}.{name}`"

    return f"""CREATE OR REPLACE PROPERTY GRAPH `{project}.{dataset}.{GRAPH_NAME}`
NODE TABLES (
  {t("account")} AS Account KEY (account_id) LABEL Account,
  {t("country")} AS Country KEY (iso2) LABEL Country,
  {t("gateway")} AS Gateway KEY (gateway_id) LABEL Gateway,
  {t("identifier")} AS Identifier KEY (identifier_id) LABEL Identifier
)
EDGE TABLES (
  {t("registered_in")} AS RegisteredIn KEY (account_id)
    SOURCE KEY (account_id) REFERENCES Account (account_id)
    DESTINATION KEY (iso2) REFERENCES Country (iso2) LABEL REGISTERED_IN,
  {t("logged_in_via")} AS LoggedInVia KEY (account_id, gateway_id)
    SOURCE KEY (account_id) REFERENCES Account (account_id)
    DESTINATION KEY (gateway_id) REFERENCES Gateway (gateway_id) LABEL LOGGED_IN_VIA,
  {t("located_in")} AS LocatedIn KEY (gateway_id)
    SOURCE KEY (gateway_id) REFERENCES Gateway (gateway_id)
    DESTINATION KEY (iso2) REFERENCES Country (iso2) LABEL LOCATED_IN,
  {t("paid_via")} AS PaidVia KEY (account_id, iso2, direction)
    SOURCE KEY (account_id) REFERENCES Account (account_id)
    DESTINATION KEY (iso2) REFERENCES Country (iso2) LABEL PAID_VIA,
  {t("uses")} AS Uses KEY (account_id, identifier_id)
    SOURCE KEY (account_id) REFERENCES Account (account_id)
    DESTINATION KEY (identifier_id) REFERENCES Identifier (identifier_id) LABEL USES
)"""
