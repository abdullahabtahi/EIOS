"""Vectorized DuckDB aggregation query compiler and executor (ADR-003, US1)."""

import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.metrics.registry import MetricRegistry


class InvalidDimensionFilterError(Exception):
    """Raised when a query attempts to filter on an unwhitelisted dimension."""

    pass


class MetricQuery(BaseModel):
    """Query envelope requesting evaluation of a governed metric."""

    metric_id: str
    grain: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    period: str | None = None  # e.g. last_24h, last_7d, last_28d, last_30d
    version: str | None = None
    as_of: datetime | None = None


class MetricResult(BaseModel):
    """Result envelope containing scalar value, definition version, and telemetry."""

    metric_id: str
    value: float
    unit: str
    grain: str | None = None
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    period: str | None = None
    definition_version: str
    as_of: datetime
    source_product: str
    execution_duration_ms: float


class MetricEngine:
    """Vectorized query engine executing governed metric queries against DuckDB hot state."""

    def __init__(self, hot_state: HotStateEngine, registry: MetricRegistry) -> None:
        self.hot_state = hot_state
        self.registry = registry

    def execute(self, query: MetricQuery) -> MetricResult:
        """Execute a metric query deterministically against DuckDB hot state."""
        t0 = time.perf_counter()
        metric_def = self.registry.get(query.metric_id, version=query.version)

        # Dimension filter whitelisting to prevent SQL injection and schema drift
        for filter_key in query.filters.keys():
            if filter_key not in metric_def.dimension_filters:
                raise InvalidDimensionFilterError(
                    f"Dimension '{filter_key}' is not allowed for metric '{metric_def.metric_id}'. "
                    f"Whitelisted dimensions: {metric_def.dimension_filters}"
                )

        table_name = metric_def.source_products[0]
        where_clauses: list[str] = []
        parameters: list[Any] = []

        # Dimensional filters (parameterized)
        for col, val in query.filters.items():
            where_clauses.append(f"{col} = ?")
            parameters.append(val)

        # Period filtering
        if query.period:
            period_mapping = {
                "last_24h": "INTERVAL 24 HOUR",
                "last_7d": "INTERVAL 7 DAY",
                "last_28d": "INTERVAL 28 DAY",
                "last_30d": "INTERVAL 30 DAY",
                "last_90d": "INTERVAL 90 DAY",
            }
            interval_str = period_mapping.get(query.period)
            if interval_str:
                # Use standard timestamp column based on product
                ts_col = (
                    "timestamp"
                    if table_name in ["transactions_aml", "partner_comms"]
                    else (
                        "open_ts"
                        if table_name == "trading_activity"
                        else (
                            "date"
                            if table_name in ["financial_pnl", "partner_engagement_signals"]
                            else None
                        )
                    )
                )
                if ts_col:
                    where_clauses.append(f"{ts_col} >= NOW() - {interval_str}")

        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"SELECT {metric_def.formula} AS metric_val FROM {table_name}{where_sql}"  # noqa: S608

        cursor = self.hot_state.get_cursor()
        try:
            res = cursor.execute(sql, parameters).fetchone()
            val = float(res[0]) if res and res[0] is not None else 0.0
        finally:
            cursor.close()

        duration_ms = (time.perf_counter() - t0) * 1000.0

        return MetricResult(
            metric_id=metric_def.metric_id,
            value=val,
            unit=metric_def.unit,
            grain=query.grain or (metric_def.grain[0] if metric_def.grain else None),
            filters_applied=query.filters,
            period=query.period,
            definition_version=metric_def.semantic_version,
            as_of=query.as_of or datetime.now(UTC),
            source_product=table_name,
            execution_duration_ms=duration_ms,
        )
