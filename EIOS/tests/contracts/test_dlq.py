"""Tests for Dead-Letter Queue (DLQ) dispatcher and Circuit Breaker."""

from datetime import datetime, timezone
import json
import jsonschema
from pathlib import Path
import pytest

from eios.contracts.base import DataProductEnum, TenantEnum
from eios.ingestion.dlq import DLQDispatcher, ContractBreachRecord, BreachType
from eios.ingestion.circuit_breaker import IngestionCircuitBreaker, ProductHealthStatus


@pytest.fixture
def dlq_schema() -> dict:
    schema_path = Path(__file__).parents[2] / "schemas" / "dlq-envelope.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_dlq_record_conforms_to_json_schema(dlq_schema: dict):
    record = ContractBreachRecord(
        dlq_id="550e8400-e29b-41d4-a716-446655440000",
        event_id="evt_invalid_001",
        product_name=DataProductEnum.TRANSACTIONS_AML,
        breach_timestamp=datetime.now(timezone.utc),
        breach_type=BreachType.VALUE_RANGE_VIOLATION,
        field_paths=["amount"],
        error_messages=["Input should be greater than 0"],
        raw_payload_bytes="eyJhbW91bnQiOiAtNTB9",  # base64 for '{"amount": -50}'
        source_topic="eios.l1.transactions_aml.v1",
        ingestion_metadata={"tenant_id": "DERIV_MFSA"},
    )
    payload_dict = record.to_dict()
    # Validate against JSON schema
    jsonschema.validate(instance=payload_dict, schema=dlq_schema)
    assert payload_dict["product_name"] == "transactions_aml"
    assert payload_dict["breach_type"] == "VALUE_RANGE_VIOLATION"


def test_dlq_dispatcher_buffers_and_logs(caplog):
    dispatcher = DLQDispatcher()
    record = dispatcher.create_breach_record(
        product_name=DataProductEnum.TRANSACTIONS_AML,
        raw_payload={"amount": -10},
        errors=[{"loc": ("amount",), "msg": "Input should be greater than 0"}],
        breach_type=BreachType.VALUE_RANGE_VIOLATION,
        source_topic="eios.l1.transactions_aml.v1",
        event_id="evt_001",
    )
    assert record is not None
    assert dispatcher.get_pending_count() == 1
    # Check that dispatch emits structured log
    flushed = dispatcher.flush()
    assert len(flushed) == 1
    assert dispatcher.get_pending_count() == 0


def test_circuit_breaker_toggles_degraded_on_high_breach_rate():
    cb = IngestionCircuitBreaker(breach_rate_threshold=0.0005)  # 0.05%
    product = DataProductEnum.TRANSACTIONS_AML
    
    # Initial status is HEALTHY
    assert cb.get_status(product) == ProductHealthStatus.HEALTHY
    
    # Record 10,000 valid events
    for _ in range(10000):
        cb.record_success(product)
        
    # Record 10 breaches (10 / 10010 = ~0.099% > 0.05%)
    for _ in range(10):
        cb.record_breach(product)
        
    # Status should now be DEGRADED
    assert cb.get_status(product) == ProductHealthStatus.DEGRADED
    metrics = cb.get_metrics(product)
    assert metrics.breach_rate > 0.0005
