"""Governed Semantic Metric Registry catalog and definition schemas (ADR-003, US1)."""

from pydantic import BaseModel, Field


class MetricNotFoundError(Exception):
    """Raised when a requested metric ID or version is not found in the registry."""

    pass


class MetricDefinition(BaseModel):
    """Declarative, versioned specification of a governed business metric."""

    metric_id: str
    name: str
    description: str = ""
    formula: str
    source_products: list[str]
    grain: list[str]
    dimension_filters: list[str] = Field(default_factory=list)
    owner_role: str
    unit: str
    semantic_version: str = "1.0.0"
    freshness_sla: str = "PT15M"
    domain: str = "general"
    is_active: bool = True


class MetricRegistry:
    """In-memory thread-safe registry of governed enterprise metrics."""

    def __init__(self) -> None:
        # Key: (metric_id, version) -> MetricDefinition
        self._definitions: dict[tuple[str, str], MetricDefinition] = {}
        # Key: metric_id -> latest version string
        self._latest_versions: dict[str, str] = {}

    def register(self, definition: MetricDefinition) -> None:
        """Register a versioned metric definition."""
        key = (definition.metric_id, definition.semantic_version)
        self._definitions[key] = definition
        # Update latest active version pointer
        self._latest_versions[definition.metric_id] = definition.semantic_version

    def get(self, metric_id: str, version: str | None = None) -> MetricDefinition:
        """Retrieve a metric definition by ID and optional semantic version."""
        if metric_id not in self._latest_versions:
            raise MetricNotFoundError(
                f"Metric '{metric_id}' is not registered in the Metric Registry."
            )

        target_version = version or self._latest_versions[metric_id]
        key = (metric_id, target_version)
        if key not in self._definitions:
            raise MetricNotFoundError(
                f"Metric '{metric_id}' with version '{target_version}' is not registered."
            )
        return self._definitions[key]

    def list_metrics(self, domain: str | None = None) -> list[MetricDefinition]:
        """List active metric definitions, optionally filtered by domain."""
        active_metrics = [
            self._definitions[(mid, ver)]
            for mid, ver in self._latest_versions.items()
            if self._definitions[(mid, ver)].is_active
        ]
        if domain:
            active_metrics = [m for m in active_metrics if m.domain == domain]
        return active_metrics
