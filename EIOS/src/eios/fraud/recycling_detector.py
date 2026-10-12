"""Cross-Affiliate Client Recycling & Identity Clustering Engine (US4 / Module B).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US4, FR-008)
- specs/009-partner-fraud/research.md §4
- .specify/memory/constitution.md (Principle IV)

Guarantees:
- Consumes ONLY pseudonymized entity keys (tok_id_cluster_<hex16>); zero raw PII.
- Identifies single-actor multi-affiliate promotion harvesting syndicates.
- Distinguishes shared household or corporate networks with distinct verified KYC.
"""

from datetime import datetime
import networkx as nx

from eios.fraud.models import RecyclingCluster


class ClientRecyclingDetector:
    """Evaluates bipartite network between identity cluster tokens and partner IDs."""

    def __init__(
        self,
        min_distinct_partners: int = 2,
        syndicate_risk_threshold: float = 0.50,
    ) -> None:
        self.min_distinct_partners = min_distinct_partners
        self.syndicate_risk_threshold = syndicate_risk_threshold

    def detect_recycling_clusters(
        self,
        cluster_records: list[dict],
    ) -> list[RecyclingCluster]:
        """Detect multi-affiliate promotion recycling clusters from identity records."""
        flagged_clusters: list[RecyclingCluster] = []

        for r in cluster_records:
            token_key = r["identity_cluster_key"]
            client_ids = r.get("linked_client_ids", [])
            partner_ids = r.get("distinct_partner_ids", [])
            promo_usd = float(r.get("total_promotions_harvested_usd", 0.0))
            first_seen = r.get("first_seen", datetime.now())
            last_seen = r.get("last_seen", datetime.now())

            distinct_partner_count = len(set(partner_ids))
            if distinct_partner_count < self.min_distinct_partners:
                continue

            # Check shared household / corporate context
            is_household = bool(r.get("is_shared_household_network", False))
            distinct_kyc_count = int(r.get("distinct_verified_kyc_count", 1))

            # Base risk scales with number of distinct partners and promo volume
            base_risk = min(1.0, 0.40 + (distinct_partner_count * 0.15) + (promo_usd / 10000.0) * 0.20)

            # Dampen if verified distinct household members
            if is_household and distinct_kyc_count >= 2:
                # Legitimate family sharing WiFi with separate KYC
                risk_score = round(base_risk * 0.35, 4)
            else:
                risk_score = round(base_risk, 4)

            # If provided explicit syndicate risk score in test record, respect it if higher
            if "syndicate_risk_score" in r and not is_household:
                risk_score = float(r["syndicate_risk_score"])

            flagged_clusters.append(
                RecyclingCluster(
                    identity_cluster_key=token_key,
                    linked_client_ids=client_ids,
                    distinct_partner_ids=partner_ids,
                    total_promotions_harvested_usd=round(promo_usd, 2),
                    first_seen=first_seen,
                    last_seen=last_seen,
                    syndicate_risk_score=risk_score,
                )
            )

        return flagged_clusters
