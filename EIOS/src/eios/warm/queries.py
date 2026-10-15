"""The warm tier's named queries. The model never writes SQL: it calls a capability, which calls one of these.

Each query is portable SQL over the generated tables, with `:name` parameters and four placeholders the store fills in
(`{table}` the table reference, `{TS}` the timestamp type, `{STR}` the string type). Every query filters on the table's
partition column, which BigQuery also enforces (`require_partition_filter`), and a test checks it.
"""

from __future__ import annotations

from dataclasses import dataclass

from eios.contracts.base import DataProductEnum
from eios.warm.schema import table_spec


@dataclass(frozen=True)
class NamedQuery:
    name: str
    product: DataProductEnum
    sql: str
    params: tuple[str, ...]

    @property
    def partition_column(self) -> str:
        return table_spec(self.product).partition_field


# Money that moved or is about to: completed and pending, never failed or cancelled. This is the engine's own definition of
# an account's deposit and withdrawal volume on the world it serves, and the parity eval holds the two to it.
ACCOUNT_DAILY_ACTIVITY = NamedQuery(
    name="account_daily_activity",
    product=DataProductEnum.TRANSACTIONS_AML,
    sql="""
        SELECT CAST(CAST(timestamp AS DATE) AS {STR}) AS day,
               SUM(CASE WHEN txn_type = 'DEPOSIT' THEN amount ELSE 0 END) AS deposits,
               SUM(CASE WHEN txn_type = 'WITHDRAWAL' THEN amount ELSE 0 END) AS withdrawals,
               COUNT(*) AS transactions,
               CAST(MAX(_loaded_at) AS {STR}) AS loaded_at
        FROM {table}
        WHERE timestamp >= CAST(:start AS {TS})
          AND timestamp < CAST(:end AS {TS})
          AND client_id = :client_id
          AND status IN ('COMPLETED', 'PENDING')
        GROUP BY day
        ORDER BY day
    """,
    params=("client_id", "start", "end"),
)

CATALOGUE: dict[str, NamedQuery] = {q.name: q for q in (ACCOUNT_DAILY_ACTIVITY,)}
