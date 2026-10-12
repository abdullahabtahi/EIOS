"""Deliberate Layer 1 contract breach and schema violation injector (SC-007, FR-010)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional
from eios.foundry.rng import RNGManager


class BreachInjector:
    """Injects deliberate schema breaches and corruptions for Layer 1 ingestion stress-testing."""

    def __init__(self, rng: RNGManager) -> None:
        self.rng = rng
        self._gen = rng.get_generator("breach_injector")

    def inject_transaction_breaches(
        self,
        records: List[Dict[str, Any]],
        breach_type: str = "NEGATIVE_AMOUNT",
    ) -> List[Dict[str, Any]]:
        """Mutates transaction records to deliberately violate Layer 1 Pydantic contracts."""
        mutated: List[Dict[str, Any]] = []
        for r in records:
            item = dict(r)
            if breach_type == "NEGATIVE_AMOUNT":
                item["amount"] = Decimal("-500.00")
            elif breach_type == "INVALID_DIRECTION":
                item["direction"] = "UNKNOWN_DIRECTION"
            elif breach_type == "ZERO_AMOUNT":
                item["amount"] = Decimal("0.00")
            mutated.append(item)
        return mutated

    def inject_client_breaches(
        self,
        records: List[Dict[str, Any]],
        breach_type: str = "INVALID_STATUS",
    ) -> List[Dict[str, Any]]:
        """Mutates client records to deliberately violate Layer 1 Pydantic contracts."""
        mutated: List[Dict[str, Any]] = []
        for r in records:
            item = dict(r)
            if breach_type == "INVALID_STATUS":
                item["status"] = "CORRUPTED_STATUS"
            elif breach_type == "INVALID_KYC_TIER":
                item["kyc_tier"] = "TIER_99_SUPER"
            elif breach_type == "MISSING_REQUIRED_FIELD":
                item.pop("client_id", None)
            mutated.append(item)
        return mutated
