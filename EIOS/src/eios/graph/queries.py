"""Named graph queries: one definition, two runners.

Each query names its traversals. On BigQuery a traversal is a GQL pattern run through `GRAPH_TABLE` over the property
graph; on the local double it is the equivalent join over the same tables in DuckDB. The SQL around the traversals
(degree, thresholds, grouping) is shared text, so the two runners cannot drift apart silently: the parity check
compares their answers row for row. The model never writes a query; it can only name one of these.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Traversal:
    gql: str  # MATCH ... RETURN ..., inside GRAPH_TABLE
    local: str  # the same rows as a plain join


@dataclass(frozen=True)
class GraphQuery:
    name: str
    params: tuple[str, ...]
    traversals: dict[str, Traversal]
    select: str  # the final SELECT over the traversals' rows; parameters are written @name
    ctes: str = ""  # further CTEs between the traversals and the SELECT


SHARED_EXITS = GraphQuery(
    name="shared_exits",
    params=("hub_degree", "min_shared", "min_sessions"),
    traversals={
        "logins": Traversal(
            gql="""MATCH (a:Account)-[v:LOGGED_IN_VIA]->(g:Gateway)-[:LOCATED_IN]->(c:Country)
    RETURN a.account_id AS account_id, a.kyc_country AS kyc_country, g.gateway_id AS gateway_id,
           c.iso2 AS country, v.sessions AS sessions""",
            local="""SELECT a.account_id, a.kyc_country, g.gateway_id, l.iso2 AS country, v.sessions
    FROM logged_in_via v JOIN account a USING (account_id) JOIN gateway g USING (gateway_id)
    JOIN located_in l USING (gateway_id)""",
        )
    },
    # Degree is counted here from the edges, not read from a stored property: the hub line (RL-4) is applied to what
    # the graph actually holds.
    ctes="""degree AS (SELECT gateway_id, COUNT(DISTINCT account_id) AS accounts FROM logins GROUP BY gateway_id),
abroad AS (
  SELECT l.* FROM logins AS l JOIN degree AS d USING (gateway_id)
  WHERE d.accounts <= @hub_degree AND l.kyc_country != l.country
),
exits AS (SELECT gateway_id FROM abroad GROUP BY gateway_id HAVING COUNT(DISTINCT account_id) >= @min_shared)""",
    select="""SELECT a.gateway_id, a.country, a.account_id, a.kyc_country, a.sessions
FROM abroad AS a JOIN exits USING (gateway_id)
WHERE a.sessions >= @min_sessions
ORDER BY a.gateway_id, a.account_id""",
)

NEIGHBOURHOOD = GraphQuery(
    name="account_neighbourhood",
    params=("account",),
    traversals={
        "by_gateway": Traversal(
            gql="""MATCH (a:Account)-[:LOGGED_IN_VIA]->(g:Gateway)<-[:LOGGED_IN_VIA]-(b:Account)
    WHERE a.account_id = @account AND b.account_id <> a.account_id AND NOT g.hub
    RETURN g.gateway_id AS link, g.country AS detail, b.account_id AS account_id, b.kyc_country AS kyc_country""",
            local="""SELECT g.gateway_id AS link, g.country AS detail, b.account_id, b.kyc_country
    FROM logged_in_via va JOIN gateway g USING (gateway_id) JOIN logged_in_via vb USING (gateway_id)
    JOIN account b ON b.account_id = vb.account_id
    WHERE va.account_id = @account AND vb.account_id <> va.account_id AND NOT g.hub""",
        ),
        "by_identifier": Traversal(
            gql="""MATCH (a:Account)-[:USES]->(i:Identifier)<-[:USES]-(b:Account)
    WHERE a.account_id = @account AND b.account_id <> a.account_id AND NOT i.hub
    RETURN i.identifier_id AS link, i.kind AS detail, b.account_id AS account_id, b.kyc_country AS kyc_country""",
            local="""SELECT i.identifier_id AS link, i.kind AS detail, b.account_id, b.kyc_country
    FROM uses ua JOIN identifier i USING (identifier_id) JOIN uses ub USING (identifier_id)
    JOIN account b ON b.account_id = ub.account_id
    WHERE ua.account_id = @account AND ub.account_id <> ua.account_id AND NOT i.hub""",
        ),
    },
    select="""SELECT 'gateway' AS via, link, detail, account_id, kyc_country FROM by_gateway
UNION ALL
SELECT 'identifier' AS via, link, detail, account_id, kyc_country FROM by_identifier
ORDER BY via, link, account_id""",
)

# A one-hop identifier link from an account of a starting set: who is linked, through what, and from which account.
_LINK_LOCAL = """SELECT {country}ua.account_id AS source_account, i.identifier_id AS link, i.kind, ub.account_id, b.kyc_country
    FROM {start} AS s JOIN uses ua ON ua.account_id = s.account_id
    JOIN identifier i ON i.identifier_id = ua.identifier_id
    JOIN uses ub ON ub.identifier_id = ua.identifier_id
    JOIN account b ON b.account_id = ub.account_id
    WHERE NOT i.hub AND ub.account_id <> ua.account_id"""

EXIT_RING = GraphQuery(
    name="exit_ring",
    params=("gateway",),
    traversals={
        "users": Traversal(
            gql="""MATCH (g:Gateway)<-[v:LOGGED_IN_VIA]-(a:Account)
    WHERE g.gateway_id = @gateway AND NOT g.hub
    RETURN a.account_id AS account_id, a.kyc_country AS kyc_country, v.sessions AS sessions""",
            local="""SELECT a.account_id, a.kyc_country, v.sessions
    FROM logged_in_via v JOIN gateway g USING (gateway_id) JOIN account a USING (account_id)
    WHERE v.gateway_id = @gateway AND NOT g.hub""",
        ),
        "shared": Traversal(
            gql="""MATCH (g:Gateway)<-[:LOGGED_IN_VIA]-(a:Account)-[:USES]->(i:Identifier)<-[:USES]-(b:Account)
    WHERE g.gateway_id = @gateway AND NOT g.hub AND NOT i.hub AND b.account_id <> a.account_id
    RETURN a.account_id AS source_account, i.identifier_id AS link, i.kind AS kind,
           b.account_id AS account_id, b.kyc_country AS kyc_country""",
            local=_LINK_LOCAL.format(
                country="",
                start="""(SELECT v.account_id FROM logged_in_via v JOIN gateway g USING (gateway_id)
    WHERE v.gateway_id = @gateway AND NOT g.hub)""",
            ),
        ),
    },
    # One row per linked account, naming its first link by identifier id, so the row points at a link that exists.
    ctes="""ranked AS (
  SELECT s.*, ROW_NUMBER() OVER (PARTITION BY s.account_id ORDER BY s.link, s.source_account) AS rn
  FROM shared AS s
  WHERE s.account_id NOT IN (SELECT account_id FROM users)
)""",
    # A linked account has no session through this exit (it is not one of its users), so its sessions are zero.
    select="""SELECT 'exit' AS via, account_id, kyc_country, sessions, @gateway AS link, 'gateway' AS kind,
       account_id AS source_account
FROM users
UNION ALL
SELECT 'identifier' AS via, account_id, kyc_country, 0 AS sessions, link, kind, source_account
FROM ranked WHERE rn = 1
ORDER BY via, account_id""",
)

# Accounts the countries touch directly (registered there, paying through its instruments, logging in from it), and
# the accounts one identifier away from them. Several countries in one job: a list change names up to a dozen.
_HELD_LOCAL = """SELECT iso2 AS country, account_id FROM registered_in WHERE list_contains(@countries, iso2)
    UNION ALL SELECT iso2 AS country, account_id FROM paid_via WHERE list_contains(@countries, iso2)"""
_LOGGED_LOCAL = """SELECT l.iso2 AS country, v.account_id FROM logged_in_via v JOIN located_in l USING (gateway_id)
    WHERE list_contains(@countries, l.iso2)"""

COUNTRY_LINKS = GraphQuery(
    name="country_links",
    params=("countries",),
    traversals={
        "held": Traversal(
            gql="""MATCH (c:Country)<-[:REGISTERED_IN|PAID_VIA]-(a:Account)
    WHERE c.iso2 IN UNNEST(@countries)
    RETURN c.iso2 AS country, a.account_id AS account_id""",
            local=_HELD_LOCAL,
        ),
        "logged": Traversal(
            gql="""MATCH (c:Country)<-[:LOCATED_IN]-(g:Gateway)<-[:LOGGED_IN_VIA]-(a:Account)
    WHERE c.iso2 IN UNNEST(@countries)
    RETURN c.iso2 AS country, a.account_id AS account_id""",
            local=_LOGGED_LOCAL,
        ),
        "held_links": Traversal(
            gql="""MATCH (c:Country)<-[:REGISTERED_IN|PAID_VIA]-(a:Account)-[:USES]->(i:Identifier)<-[:USES]-(b:Account)
    WHERE c.iso2 IN UNNEST(@countries) AND NOT i.hub AND b.account_id <> a.account_id
    RETURN c.iso2 AS country, a.account_id AS source_account, i.identifier_id AS link, i.kind AS kind,
           b.account_id AS account_id, b.kyc_country AS kyc_country""",
            local=_LINK_LOCAL.format(country="s.country, ", start=f"({_HELD_LOCAL})"),
        ),
        "logged_links": Traversal(
            gql="""MATCH (c:Country)<-[:LOCATED_IN]-(g:Gateway)<-[:LOGGED_IN_VIA]-(a:Account)-[:USES]->(i:Identifier)<-[:USES]-(b:Account)
    WHERE c.iso2 IN UNNEST(@countries) AND NOT i.hub AND b.account_id <> a.account_id
    RETURN c.iso2 AS country, a.account_id AS source_account, i.identifier_id AS link, i.kind AS kind,
           b.account_id AS account_id, b.kyc_country AS kyc_country""",
            local=_LINK_LOCAL.format(country="s.country, ", start=f"({_LOGGED_LOCAL})"),
        ),
    },
    ctes="""direct AS (
  SELECT DISTINCT country, account_id FROM (SELECT * FROM held UNION ALL SELECT * FROM logged) AS d
),
ranked AS (
  SELECT s.*, ROW_NUMBER() OVER (PARTITION BY s.country, s.account_id ORDER BY s.link, s.source_account) AS rn
  FROM (SELECT * FROM held_links UNION ALL SELECT * FROM logged_links) AS s
  LEFT JOIN direct AS d ON d.country = s.country AND d.account_id = s.account_id
  WHERE d.account_id IS NULL
)""",
    select="""SELECT country, account_id, kyc_country, link, kind, source_account FROM ranked WHERE rn = 1
ORDER BY country, account_id""",
)

CATALOGUE: dict[str, GraphQuery] = {
    q.name: q for q in (SHARED_EXITS, NEIGHBOURHOOD, EXIT_RING, COUNTRY_LINKS)
}


def compose(query: GraphQuery, *, graph: str | None) -> str:
    """The full SQL: with `graph` the traversals run as GQL through GRAPH_TABLE, without it as local joins."""
    parts = [
        # Fixed catalogue text and a graph name built from a validated project id; parameters stay bound (@name).
        f"{name} AS (\n  "  # noqa: S608
        + (f"SELECT * FROM GRAPH_TABLE(\n  {graph}\n  {t.gql}\n)" if graph else t.local)  # noqa: S608
        + "\n)"
        for name, t in query.traversals.items()
    ]
    if query.ctes:
        parts.append(query.ctes)
    return "WITH " + ",\n".join(parts) + "\n" + query.select
