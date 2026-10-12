"""Provider adapters. Vendor SDKs may be imported only inside this package (FR-021)."""

from __future__ import annotations

# [SPIKE] F00 registers only the stub. Real providers are added after S-01 closes and ADR-002
# is accepted; config validation rejects any provider label not listed here.
REGISTERED_PROVIDERS: frozenset[str] = frozenset({"stub", "vertex"})
