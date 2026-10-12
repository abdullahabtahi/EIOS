"""Hot-state table-to-ontology object hydrator (US2)."""

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.config import SecurityMarking
from eios.ontology.core.objects import Case, ClientAccount, Partner


class OntologyHydrator:
    """Rehydrates strongly-typed Ontology objects directly from DuckDB hot-state tables."""

    def __init__(self, hot_state: HotStateEngine) -> None:
        self.hot_state = hot_state

    def hydrate_client(self, client_id: str) -> ClientAccount:
        """Hydrate ClientAccount instance from client_360 table."""
        cursor = self.hot_state.get_cursor()
        try:
            row = cursor.execute(
                """
                SELECT client_id, kyc_status, segment, lifetime_value, partner_id
                FROM client_360
                WHERE client_id = ?
                """,
                [client_id],
            ).fetchone()
        finally:
            cursor.close()

        if not row:
            raise KeyError(f"ClientAccount '{client_id}' not found in hot state.")

        return ClientAccount(
            client_id=row[0],
            kyc_status=row[1] or "PENDING",
            segment=row[2] or "STANDARD",
            lifetime_value_usd=float(row[3] or 0.0),
            partner_id=row[4],
            markings=[SecurityMarking.PII],
        )

    def hydrate_partner(self, partner_id: str) -> Partner:
        """Hydrate Partner instance from partner_360 table."""
        cursor = self.hot_state.get_cursor()
        try:
            row = cursor.execute(
                """
                SELECT partner_id, tier, region, tenure_months, value_at_risk, manager_id
                FROM partner_360
                WHERE partner_id = ?
                """,
                [partner_id],
            ).fetchone()
        finally:
            cursor.close()

        if not row:
            raise KeyError(f"Partner '{partner_id}' not found in hot state.")

        return Partner(
            partner_id=row[0],
            tier=row[1] or "TIER_2",
            region_id=row[2],
            tenure_days=(row[3] or 0) * 30,
            value_at_risk_usd=float(row[4] or 0.0),
            manager_id=row[5],
            markings=[SecurityMarking.PARTNER_COMMERCIAL],
        )

    def hydrate_case(self, case_id: str) -> Case:
        """Hydrate Case instance from compliance_cases table."""
        cursor = self.hot_state.get_cursor()
        try:
            row = cursor.execute(
                """
                SELECT case_id, client_id, status, typology,
                       analyst_id, risk_score, created_at, updated_at
                FROM compliance_cases
                WHERE case_id = ?
                """,
                [case_id],
            ).fetchone()
        finally:
            cursor.close()

        if not row:
            raise KeyError(f"Case '{case_id}' not found in hot state.")

        return Case(
            case_id=row[0],
            target_id=row[1] or "",
            status=row[2] or "OPEN",
            typology=row[3] or "UNKNOWN",
            assigned_analyst=row[4] or "UNASSIGNED",
            risk_score=float(row[5] or 0.0),
            created_at=row[6],
            updated_at=row[7],
            markings=[SecurityMarking.SENSITIVE_COMPLIANCE],
        )
