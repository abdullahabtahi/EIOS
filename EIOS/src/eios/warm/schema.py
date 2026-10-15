"""BigQuery tables for the warm tier, generated from the data-product contracts (docs/warm-tier.md).

A column is exactly a contract field, typed from the pydantic annotation, so the warehouse cannot drift from what
ingestion validates. Each row also carries lineage columns (`_batch_id`, `_loaded_at`, `_source`, `_tenant_id`) taken
from the exporter's manifest. Pure and offline: nothing here calls BigQuery.
"""

from __future__ import annotations

import types
import typing
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal, get_args, get_origin

from eios.contracts.base import DataProductEnum
from eios.ingestion.validator import PRODUCT_MODEL_REGISTRY

LOAD_TIME = "_loaded_at"
LINEAGE_COLUMNS = ("_batch_id", LOAD_TIME, "_source", "_tenant_id")
_LINEAGE_FIELDS: tuple[dict[str, str], ...] = (
    {"name": "_batch_id", "type": "STRING", "mode": "REQUIRED"},
    {"name": LOAD_TIME, "type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "_source", "type": "STRING", "mode": "REQUIRED"},
    {"name": "_tenant_id", "type": "STRING", "mode": "NULLABLE"},
)

# [ASSUMPTION] bounded contexts as datasets (docs/data-strategy.md section 4); one per context, never one per product.
CONTEXT_DATASET: dict[DataProductEnum, str] = {
    DataProductEnum.CLIENT_360: "warm_aml",
    DataProductEnum.CLIENT_FUNNEL: "warm_aml",
    DataProductEnum.TRANSACTIONS_AML: "warm_aml",
    DataProductEnum.DEVICE_NETWORK_GRAPH: "warm_aml",
    DataProductEnum.COMPLIANCE_CASES: "warm_aml",
    DataProductEnum.TRADING_ACTIVITY: "warm_partner",
    DataProductEnum.PARTNER_360: "warm_partner",
    DataProductEnum.PARTNER_REFERRAL_TREE: "warm_partner",
    DataProductEnum.COMMISSION_LEDGER: "warm_partner",
    DataProductEnum.PARTNER_ENGAGEMENT_SIGNALS: "warm_partner",
    DataProductEnum.PARTNER_COMMS: "warm_partner",
    DataProductEnum.FINANCIAL_PNL: "warm_executive",
    DataProductEnum.COMPETITOR_BENCHMARKS: "warm_executive",
    DataProductEnum.PLATFORM_OPERATIONS: "warm_ops",
}
DLQ_DATASET = "warm_dlq"

# product -> (partition column, clustering columns). The partition column is the event's own time where the contract
# has one, else the load time. Clustering follows the grain and the filters the named queries use (BigQuery allows 4).
_LAYOUT: dict[DataProductEnum, tuple[str, tuple[str, ...]]] = {
    DataProductEnum.CLIENT_360: (LOAD_TIME, ("client_id",)),
    DataProductEnum.CLIENT_FUNNEL: ("entered_at", ("client_id",)),
    DataProductEnum.TRANSACTIONS_AML: ("timestamp", ("client_id", "txn_type")),
    DataProductEnum.TRADING_ACTIVITY: ("open_ts", ("client_id",)),
    DataProductEnum.DEVICE_NETWORK_GRAPH: ("last_seen", ("source_id", "target_id")),
    DataProductEnum.PARTNER_360: (LOAD_TIME, ("partner_id",)),
    DataProductEnum.PARTNER_REFERRAL_TREE: ("since", ("parent_id", "child_id")),
    DataProductEnum.COMMISSION_LEDGER: ("paid_at", ("partner_id", "client_id")),
    DataProductEnum.PARTNER_ENGAGEMENT_SIGNALS: ("date", ("partner_id",)),
    DataProductEnum.PARTNER_COMMS: ("timestamp", ("partner_id",)),
    DataProductEnum.FINANCIAL_PNL: ("date", ()),
    DataProductEnum.COMPETITOR_BENCHMARKS: ("date", ()),
    DataProductEnum.PLATFORM_OPERATIONS: ("date", ()),
    DataProductEnum.COMPLIANCE_CASES: ("created_at", ("client_id", "case_id")),
}


@dataclass(frozen=True)
class TableSpec:
    dataset: str
    table: str
    fields: tuple[dict[str, str], ...]
    partition_field: str
    cluster_fields: tuple[str, ...]


def _scalar(annotation: Any) -> str:
    if get_origin(annotation) is Literal:
        return "STRING"
    if annotation is bool:
        return "BOOL"
    if annotation is int:
        return "INT64"
    if annotation is float:
        return "FLOAT64"
    if annotation is datetime:  # before `date`: a datetime is also a date
        return "TIMESTAMP"
    if annotation is date:
        return "DATE"
    if annotation is str:
        return "STRING"
    raise TypeError(f"no BigQuery type for contract annotation {annotation!r}")


def _split_optional(annotation: Any) -> tuple[Any, bool]:
    if get_origin(annotation) in (typing.Union, types.UnionType):
        members = [a for a in get_args(annotation) if a is not type(None)]
        if len(members) == 1:
            return members[0], True
    return annotation, False


def _contract_fields(product: DataProductEnum) -> tuple[dict[str, str], ...]:
    out = []
    for name, info in PRODUCT_MODEL_REGISTRY[product].model_fields.items():
        annotation, optional = _split_optional(info.annotation)
        mode = "NULLABLE" if optional or not info.is_required() else "REQUIRED"
        out.append({"name": name, "type": _scalar(annotation), "mode": mode})
    return tuple(out)


def table_spec(product: DataProductEnum) -> TableSpec:
    partition, cluster = _LAYOUT[product]
    return TableSpec(
        dataset=CONTEXT_DATASET[product],
        table=product.value,
        fields=(*_contract_fields(product), *_LINEAGE_FIELDS),
        partition_field=partition,
        cluster_fields=cluster,
    )


def dlq_spec() -> TableSpec:
    """Contract breaches, quarantined with the reason and a hash of the raw payload (the payload itself stays out)."""
    fields = (
        {"name": "dlq_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "event_id", "type": "STRING", "mode": "NULLABLE"},
        {"name": "product_name", "type": "STRING", "mode": "REQUIRED"},
        {"name": "breach_type", "type": "STRING", "mode": "REQUIRED"},
        {"name": "field_paths", "type": "STRING", "mode": "REPEATED"},
        {"name": "error_messages", "type": "STRING", "mode": "REPEATED"},
        {"name": "payload_sha256", "type": "STRING", "mode": "REQUIRED"},
        {"name": "breach_timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
        *_LINEAGE_FIELDS,
    )
    return TableSpec(
        DLQ_DATASET, "quarantined", fields, "breach_timestamp", ("product_name", "breach_type")
    )


def to_bigquery_schema(spec: TableSpec) -> list[dict[str, str]]:
    """The schema in BigQuery's JSON form (what `bq` and Terraform accept)."""
    return [dict(f) for f in spec.fields]


def all_specs() -> list[TableSpec]:
    return [*(table_spec(p) for p in PRODUCT_MODEL_REGISTRY), dlq_spec()]
