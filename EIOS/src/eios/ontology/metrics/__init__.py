"""Governed Semantic Metric Registry and Vectorized DuckDB Engine."""

from eios.ontology.metrics.catalog import (
    CANONICAL_METRICS,
    create_default_registry,
)
from eios.ontology.metrics.engine import (
    InvalidDimensionFilterError,
    MetricEngine,
    MetricQuery,
    MetricResult,
)
from eios.ontology.metrics.registry import (
    MetricDefinition,
    MetricNotFoundError,
    MetricRegistry,
)

__all__ = [
    "MetricRegistry",
    "MetricDefinition",
    "MetricNotFoundError",
    "MetricEngine",
    "MetricQuery",
    "MetricResult",
    "InvalidDimensionFilterError",
    "CANONICAL_METRICS",
    "create_default_registry",
]
