"""Load the graph tables into BigQuery (`warm_graph`) and create the property graph over them.

Load jobs, WRITE_TRUNCATE per table, so a reload is idempotent. A `_meta` row records which world the tables came from,
which the store checks before answering. The dataset lives with the warm tier (us-central1).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from eios.graph.store import META_TABLE
from eios.graph.tables import GRAPH_DATASET, GraphTables, property_graph_ddl

WARM_LOCATION = "us-central1"


def load_graph(
    tables: GraphTables, project: str, client: Any | None = None, dataset: str = GRAPH_DATASET
) -> dict[str, Any]:
    from google.cloud import bigquery

    bq = client or bigquery.Client(project=project)
    ds = bigquery.Dataset(f"{project}.{dataset}")
    ds.location = WARM_LOCATION
    ds.description = "The AML world as a property graph (accounts, countries, gateways, identifiers). Synthetic rows."
    bq.create_dataset(ds, exists_ok=True)
    started = time.perf_counter()
    rows: dict[str, int] = {}
    write = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    for name, frame in tables.frames.items():
        bq.load_table_from_dataframe(
            frame, f"{project}.{dataset}.{name}", job_config=write
        ).result()
        rows[name] = len(frame)
    meta = pd.DataFrame(
        [{"fingerprint": tables.fingerprint, "loaded_at": datetime.now(UTC), "tables": len(rows)}]
    )
    bq.load_table_from_dataframe(
        meta, f"{project}.{dataset}.{META_TABLE}", job_config=write
    ).result()
    bq.query(property_graph_ddl(project, dataset)).result()
    return {
        "rows": rows,
        "seconds": round(time.perf_counter() - started, 1),
        "fingerprint": tables.fingerprint,
    }
