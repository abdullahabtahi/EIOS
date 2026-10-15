"""BigQuery tables are generated from the contracts, so the warehouse cannot drift from what ingestion validates."""

from datetime import UTC, datetime

import pytest

from eios.contracts.base import DataProductEnum
from eios.contracts.models import TransactionAMLEvent
from eios.ingestion.validator import PRODUCT_MODEL_REGISTRY
from eios.warm.schema import (
    LINEAGE_COLUMNS,
    dlq_spec,
    table_spec,
    to_bigquery_schema,
)

PRODUCTS = list(PRODUCT_MODEL_REGISTRY)


@pytest.mark.parametrize("product", PRODUCTS)
def test_every_product_has_a_table_whose_layout_names_real_columns(
    product: DataProductEnum,
) -> None:
    spec = table_spec(product)
    names = {f["name"] for f in to_bigquery_schema(spec)}
    assert spec.partition_field in names
    assert set(spec.cluster_fields) <= names
    assert len(names) == len(to_bigquery_schema(spec))  # no duplicate column
    assert len(spec.cluster_fields) <= 4  # BigQuery's limit


@pytest.mark.parametrize("product", PRODUCTS)
def test_every_contract_field_is_a_column_and_every_lineage_column_is_there(
    product: DataProductEnum,
) -> None:
    names = {f["name"] for f in to_bigquery_schema(table_spec(product))}
    assert set(PRODUCT_MODEL_REGISTRY[product].model_fields) <= names
    assert set(LINEAGE_COLUMNS) <= names


def test_types_follow_the_contract() -> None:
    by_name = {
        f["name"]: f for f in to_bigquery_schema(table_spec(DataProductEnum.TRANSACTIONS_AML))
    }
    assert by_name["timestamp"]["type"] == "TIMESTAMP"
    assert by_name["amount"]["type"] == "FLOAT64"
    assert by_name["is_first_deposit"]["type"] == "BOOL"
    assert by_name["txn_type"]["type"] == "STRING"  # a Literal is its string
    assert by_name["txn_id"]["mode"] == "REQUIRED"  # no default, not optional
    assert by_name["payment_agent_id"]["mode"] == "NULLABLE"  # `str | None`
    assert by_name["status"]["mode"] == "NULLABLE"  # has a default, so a row may omit it


def test_dates_are_dates_and_a_table_without_an_event_time_is_partitioned_by_load_time() -> None:
    pnl = {f["name"]: f for f in to_bigquery_schema(table_spec(DataProductEnum.FINANCIAL_PNL))}
    assert pnl["date"]["type"] == "DATE"
    assert table_spec(DataProductEnum.FINANCIAL_PNL).partition_field == "date"
    assert table_spec(DataProductEnum.PARTNER_360).partition_field == "_loaded_at"


def test_a_valid_event_fits_its_table() -> None:
    event = TransactionAMLEvent(
        txn_id="TX-000001",
        client_id="CR84920",
        txn_type="DEPOSIT",
        amount=10.0,
        currency="USD",
        payment_method_id="tok_1",
        timestamp=datetime(2026, 10, 1, tzinfo=UTC),
    )
    names = {f["name"] for f in to_bigquery_schema(table_spec(DataProductEnum.TRANSACTIONS_AML))}
    assert set(event.model_dump()) <= names


def test_quarantined_events_get_their_own_table() -> None:
    spec = dlq_spec()
    cols = {f["name"]: f for f in to_bigquery_schema(spec)}
    assert cols["field_paths"]["mode"] == "REPEATED"
    assert {"dlq_id", "product_name", "breach_type", "payload_sha256", "breach_timestamp"} <= set(
        cols
    )
    assert spec.partition_field == "breach_timestamp"


def test_datasets_group_products_by_bounded_context() -> None:
    datasets = {table_spec(p).dataset for p in PRODUCTS}
    assert datasets == {"warm_aml", "warm_partner", "warm_executive", "warm_ops"}
    assert table_spec(DataProductEnum.TRANSACTIONS_AML).dataset == "warm_aml"
    assert table_spec(DataProductEnum.COMMISSION_LEDGER).dataset == "warm_partner"
