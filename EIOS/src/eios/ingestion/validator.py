"""High-throughput Pydantic v2 TypeAdapter validation engine for Layer 1 Data Products."""

from dataclasses import dataclass, field
from typing import Any
from pydantic import TypeAdapter, ValidationError

from eios.contracts.base import DataProductEnum
from eios.contracts.models import (
    BaseDataProductModel,
    Client360Event,
    ClientFunnelEvent,
    TransactionAMLEvent,
    TradingActivityEvent,
    DeviceGraphEdgeEvent,
    Partner360Event,
    ReferralTreeEdgeEvent,
    CommissionLedgerEvent,
    PartnerSignalsEvent,
    PartnerCommsEvent,
    FinancialPnLEvent,
    CompetitorBenchmarkEvent,
    PlatformOperationsEvent,
    ComplianceCaseEvent,
)


@dataclass(frozen=True)
class ValidationErrorDetail:
    """Structured detail of a single field breach."""
    field_path: str
    message: str
    error_type: str


@dataclass
class ValidationResult:
    """Result of contract validation against a governed Data Product."""
    is_valid: bool
    errors: list[ValidationErrorDetail] = field(default_factory=list)
    validated_model: BaseDataProductModel | None = None


# Registry of all 14 Layer 1 Data Products
PRODUCT_MODEL_REGISTRY: dict[DataProductEnum, type[BaseDataProductModel]] = {
    DataProductEnum.CLIENT_360: Client360Event,
    DataProductEnum.CLIENT_FUNNEL: ClientFunnelEvent,
    DataProductEnum.TRANSACTIONS_AML: TransactionAMLEvent,
    DataProductEnum.TRADING_ACTIVITY: TradingActivityEvent,
    DataProductEnum.DEVICE_NETWORK_GRAPH: DeviceGraphEdgeEvent,
    DataProductEnum.PARTNER_360: Partner360Event,
    DataProductEnum.PARTNER_REFERRAL_TREE: ReferralTreeEdgeEvent,
    DataProductEnum.COMMISSION_LEDGER: CommissionLedgerEvent,
    DataProductEnum.PARTNER_ENGAGEMENT_SIGNALS: PartnerSignalsEvent,
    DataProductEnum.PARTNER_COMMS: PartnerCommsEvent,
    DataProductEnum.FINANCIAL_PNL: FinancialPnLEvent,
    DataProductEnum.COMPETITOR_BENCHMARKS: CompetitorBenchmarkEvent,
    DataProductEnum.PLATFORM_OPERATIONS: PlatformOperationsEvent,
    DataProductEnum.COMPLIANCE_CASES: ComplianceCaseEvent,
}


class ContractValidator:
    """Thread-safe contract validation gateway enforcing strict Pydantic v2 schemas."""

    def __init__(self) -> None:
        self._adapters: dict[DataProductEnum, TypeAdapter[Any]] = {
            product: TypeAdapter(model_cls)
            for product, model_cls in PRODUCT_MODEL_REGISTRY.items()
        }

    @property
    def supported_products(self) -> list[DataProductEnum]:
        """Return list of all registered data products."""
        return list(self._adapters.keys())

    def validate(self, product_name: DataProductEnum, payload: dict[str, Any]) -> ValidationResult:
        """Validate an event payload against the target Data Product schema."""
        adapter = self._adapters.get(product_name)
        if adapter is None:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationErrorDetail(
                        field_path="product_name",
                        message=f"Unsupported or unregistered data product: {product_name}",
                        error_type="UNREGISTERED_PRODUCT",
                    )
                ],
            )

        try:
            validated = adapter.validate_python(payload)
            return ValidationResult(is_valid=True, errors=[], validated_model=validated)
        except ValidationError as e:
            errors = [
                ValidationErrorDetail(
                    field_path=".".join(str(loc) for loc in err["loc"]),
                    message=err["msg"],
                    error_type=err["type"],
                )
                for err in e.errors()
            ]
            return ValidationResult(is_valid=False, errors=errors, validated_model=None)
