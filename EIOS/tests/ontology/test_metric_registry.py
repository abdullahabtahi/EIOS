"""Test Governed Metric Registry definitions, versioning, and catalog (T010)."""

import pytest

from eios.ontology.metrics.registry import MetricDefinition, MetricNotFoundError, MetricRegistry


def test_metric_registration_and_retrieval():
    registry = MetricRegistry()
    metric_def = MetricDefinition(
        metric_id="test_deposit_sum",
        name="Test Deposit Sum",
        description="Sum of deposits in USD",
        formula="SUM(amount)",
        source_products=["transactions_aml"],
        grain=["region"],
        dimension_filters=["region", "currency"],
        owner_role="financial_analyst",
        unit="USD",
        semantic_version="1.0.0",
        freshness_sla="PT30S",
    )
    registry.register(metric_def)

    retrieved = registry.get("test_deposit_sum")
    assert retrieved.metric_id == "test_deposit_sum"
    assert retrieved.unit == "USD"
    assert retrieved.semantic_version == "1.0.0"


def test_metric_not_found_raises_typed_error():
    registry = MetricRegistry()
    with pytest.raises(MetricNotFoundError) as exc_info:
        registry.get("non_existent_kpi")
    assert "non_existent_kpi" in str(exc_info.value)


def test_metric_definition_versioning():
    registry = MetricRegistry()
    v1 = MetricDefinition(
        metric_id="churn_rate",
        name="Churn Rate",
        formula="COUNT(churned) / COUNT(total)",
        source_products=["partner_360"],
        grain=["tier"],
        dimension_filters=["tier", "region"],
        owner_role="head_of_partnerships",
        unit="ratio",
        semantic_version="1.0.0",
    )
    v2 = MetricDefinition(
        metric_id="churn_rate",
        name="Churn Rate 28d",
        formula="COUNT(churned_28d) / COUNT(total)",
        source_products=["partner_360"],
        grain=["tier"],
        dimension_filters=["tier", "region"],
        owner_role="head_of_partnerships",
        unit="ratio",
        semantic_version="2.0.0",
    )
    registry.register(v1)
    registry.register(v2)

    # Active default is latest version
    assert registry.get("churn_rate").semantic_version == "2.0.0"
    # Specific historical version retrieval
    assert registry.get("churn_rate", version="1.0.0").semantic_version == "1.0.0"


def test_list_metrics_by_domain():
    registry = MetricRegistry()
    m1 = MetricDefinition(
        metric_id="p1",
        name="Partner Count",
        formula="count()",
        source_products=["partner_360"],
        grain=["tier"],
        dimension_filters=[],
        owner_role="head_of_partnerships",
        unit="count",
        domain="partner",
    )
    m2 = MetricDefinition(
        metric_id="f1",
        name="Net Deposit",
        formula="sum()",
        source_products=["transactions_aml"],
        grain=["region"],
        dimension_filters=[],
        owner_role="cfo",
        unit="USD",
        domain="financial",
    )
    registry.register(m1)
    registry.register(m2)

    partner_metrics = registry.list_metrics(domain="partner")
    assert len(partner_metrics) == 1
    assert partner_metrics[0].metric_id == "p1"
