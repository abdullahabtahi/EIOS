"""Unified Single Client View (SCV) Coordinator enforcing ADR-008 Hub Suppression (US4)."""

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from eios.ingestion.entity_resolution.deterministic import (
    ClientProfileRecord,
    DeterministicResolver,
)
from eios.ingestion.entity_resolution.hub_suppression import HubSuppressionFilter
from eios.ingestion.entity_resolution.probabilistic import ProbabilisticLinker


@dataclass
class CanonicalClientEntity:
    """Canonical client representation linking fragmented trading accounts."""

    canonical_id: str
    tax_id: str | None
    email_hash: str | None
    phone_hash: str | None
    linked_accounts: list[str] = field(default_factory=list)
    devices: list[str] = field(default_factory=list)
    ips: list[str] = field(default_factory=list)
    is_shared_context: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SCVCoordinator:
    """Coordinates deterministic matching, probabilistic linking, and hub suppression."""

    def __init__(self, hub_degree_threshold: int = 5) -> None:
        self.deterministic_resolver = DeterministicResolver()
        self.probabilistic_linker = ProbabilisticLinker(threshold=0.85)
        self.hub_filter = HubSuppressionFilter(degree_threshold=hub_degree_threshold)
        self._canonical_entities: dict[str, CanonicalClientEntity] = {}
        self._entity_profiles: dict[str, dict[str, Any]] = {}
        self._account_to_canonical: dict[str, str] = {}
        self._lock = threading.Lock()

    def resolve_record(  # noqa: C901, PLR0912
        self,
        record: ClientProfileRecord,
        profile_metadata: dict[str, Any] | None = None,
    ) -> str:
        """Resolve an incoming profile record to its canonical entity with hub suppression."""
        with self._lock:
            # Check if account_id already mapped
            if record.account_id in self._account_to_canonical:
                return self._account_to_canonical[record.account_id]

            # Register device/IP associations for hub detection
            is_shared = False
            effective_tax = record.tax_id or record.account_id

            if record.device_id:
                self.hub_filter.register_association("device_id", record.device_id, effective_tax)
                if self.hub_filter.is_shared_context("device_id", record.device_id):
                    is_shared = True

            if record.ip_address:
                self.hub_filter.register_association("ip_address", record.ip_address, effective_tax)
                if self.hub_filter.is_shared_context("ip_address", record.ip_address):
                    is_shared = True

            # Build profile dict for current record
            curr_profile: dict[str, Any] = {
                "full_name": record.full_name or "",
                # Hub Suppression: if device is shared across >= 5 users, suppress device link!
                "device_id": None if is_shared else record.device_id,
            }
            if profile_metadata:
                curr_profile.update(profile_metadata)

            has_deterministic_keys = bool(record.tax_id or record.email_hash or record.phone_hash)
            canonical_id: str | None = None

            # Stage 1: Deterministic Exact Key Resolution (tax, email, phone)
            if has_deterministic_keys:
                canonical_id = self.deterministic_resolver.resolve(record)

            # Stage 2: Probabilistic Fellegi-Sunter Record Linkage (when deterministic key is absent or fresh)
            if not canonical_id or canonical_id not in self._canonical_entities:
                for cand_id, cand_profile in self._entity_profiles.items():
                    score, is_match = self.probabilistic_linker.evaluate_pair(
                        curr_profile, cand_profile
                    )
                    if is_match:
                        canonical_id = cand_id
                        break

            if not canonical_id:
                canonical_id = f"scv_{uuid4().hex[:12]}"

            self._account_to_canonical[record.account_id] = canonical_id

            if canonical_id not in self._canonical_entities:
                self._canonical_entities[canonical_id] = CanonicalClientEntity(
                    canonical_id=canonical_id,
                    tax_id=record.tax_id,
                    email_hash=record.email_hash,
                    phone_hash=record.phone_hash,
                    linked_accounts=[record.account_id],
                    devices=[record.device_id] if record.device_id else [],
                    ips=[record.ip_address] if record.ip_address else [],
                    is_shared_context=is_shared,
                )
                self._entity_profiles[canonical_id] = curr_profile
            else:
                entity = self._canonical_entities[canonical_id]
                if record.account_id not in entity.linked_accounts:
                    entity.linked_accounts.append(record.account_id)
                if record.device_id and record.device_id not in entity.devices:
                    entity.devices.append(record.device_id)
                if record.ip_address and record.ip_address not in entity.ips:
                    entity.ips.append(record.ip_address)
                if is_shared:
                    entity.is_shared_context = True

            return canonical_id

    def get_entity(self, canonical_id: str) -> CanonicalClientEntity | None:
        """Lookup canonical entity by ID."""
        with self._lock:
            return self._canonical_entities.get(canonical_id)
