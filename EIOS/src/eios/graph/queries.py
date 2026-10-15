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

CATALOGUE: dict[str, GraphQuery] = {q.name: q for q in (SHARED_EXITS, NEIGHBOURHOOD)}


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
