"""DuckDB in-process columnar Hot-State Engine for real-time analytical queries (US3)."""

from datetime import datetime, timezone, timedelta
import threading
from typing import Any
import duckdb

from eios.contracts.base import DataProductEnum

TABLE_SCHEMAS: dict[DataProductEnum, str] = {
    DataProductEnum.CLIENT_360: """
        CREATE TABLE IF NOT EXISTS client_360 (
            client_id VARCHAR,
            tax_id VARCHAR,
            full_name VARCHAR,
            email VARCHAR,
            phone VARCHAR,
            dob DATE,
            country VARCHAR,
            kyc_status VARCHAR,
            kyc_approved_at TIMESTAMP,
            partner_id VARCHAR,
            declared_monthly_income DOUBLE,
            lifetime_value DOUBLE,
            segment VARCHAR
        )
    """,
    DataProductEnum.CLIENT_FUNNEL: """
        CREATE TABLE IF NOT EXISTS client_funnel (
            client_id VARCHAR,
            stage VARCHAR,
            entered_at TIMESTAMP,
            source VARCHAR,
            utm_campaign VARCHAR
        )
    """,
    DataProductEnum.TRANSACTIONS_AML: """
        CREATE TABLE IF NOT EXISTS transactions_aml (
            txn_id VARCHAR,
            client_id VARCHAR,
            txn_type VARCHAR,
            amount DOUBLE,
            currency VARCHAR,
            payment_method_id VARCHAR,
            payment_agent_id VARCHAR,
            timestamp TIMESTAMP,
            is_first_deposit BOOLEAN,
            status VARCHAR
        )
    """,
    DataProductEnum.TRADING_ACTIVITY: """
        CREATE TABLE IF NOT EXISTS trading_activity (
            trade_id VARCHAR,
            client_id VARCHAR,
            symbol VARCHAR,
            side VARCHAR,
            volume DOUBLE,
            open_price DOUBLE,
            close_price DOUBLE,
            open_ts TIMESTAMP,
            close_ts TIMESTAMP,
            profit_loss DOUBLE
        )
    """,
    DataProductEnum.DEVICE_NETWORK_GRAPH: """
        CREATE TABLE IF NOT EXISTS device_network_graph (
            edge_id VARCHAR,
            source_id VARCHAR,
            target_id VARCHAR,
            edge_type VARCHAR,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            session_count INT,
            is_shared_context BOOLEAN
        )
    """,
    DataProductEnum.PARTNER_360: """
        CREATE TABLE IF NOT EXISTS partner_360 (
            partner_id VARCHAR,
            tier VARCHAR,
            region VARCHAR,
            tenure_months INT,
            value_at_risk DOUBLE,
            manager_id VARCHAR,
            status VARCHAR
        )
    """,
    DataProductEnum.PARTNER_REFERRAL_TREE: """
        CREATE TABLE IF NOT EXISTS partner_referral_tree (
            parent_id VARCHAR,
            child_id VARCHAR,
            layer INT,
            attributed_master_id VARCHAR,
            since TIMESTAMP
        )
    """,
    DataProductEnum.COMMISSION_LEDGER: """
        CREATE TABLE IF NOT EXISTS commission_ledger (
            entry_id VARCHAR,
            partner_id VARCHAR,
            client_id VARCHAR,
            basis VARCHAR,
            amount DOUBLE,
            currency VARCHAR,
            paid_at TIMESTAMP
        )
    """,
    DataProductEnum.PARTNER_ENGAGEMENT_SIGNALS: """
        CREATE TABLE IF NOT EXISTS partner_engagement_signals (
            partner_id VARCHAR,
            date DATE,
            logins INT,
            referrals INT,
            ftd_count INT,
            conversion_rate DOUBLE,
            clicks INT
        )
    """,
    DataProductEnum.PARTNER_COMMS: """
        CREATE TABLE IF NOT EXISTS partner_comms (
            message_id VARCHAR,
            partner_id VARCHAR,
            channel VARCHAR,
            sentiment VARCHAR,
            text VARCHAR,
            timestamp TIMESTAMP
        )
    """,
    DataProductEnum.FINANCIAL_PNL: """
        CREATE TABLE IF NOT EXISTS financial_pnl (
            date DATE,
            product VARCHAR,
            region VARCHAR,
            revenue DOUBLE,
            cost DOUBLE,
            net_margin DOUBLE,
            ltv_cohort VARCHAR
        )
    """,
    DataProductEnum.COMPETITOR_BENCHMARKS: """
        CREATE TABLE IF NOT EXISTS competitor_benchmarks (
            competitor VARCHAR,
            date DATE,
            region VARCHAR,
            payout_rate DOUBLE,
            spread_pips DOUBLE,
            promo_event VARCHAR
        )
    """,
    DataProductEnum.PLATFORM_OPERATIONS: """
        CREATE TABLE IF NOT EXISTS platform_operations (
            date DATE,
            service VARCHAR,
            latency_p95_ms DOUBLE,
            incidents_count INT,
            escrow_disputes_count INT,
            uptime_percentage DOUBLE
        )
    """,
    DataProductEnum.COMPLIANCE_CASES: """
        CREATE TABLE IF NOT EXISTS compliance_cases (
            case_id VARCHAR,
            client_id VARCHAR,
            status VARCHAR,
            typology VARCHAR,
            analyst_id VARCHAR,
            risk_score DOUBLE,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """,
}

CHURN_RADAR_SCHEMAS = {
    "churn_radar_scores": """
        CREATE TABLE IF NOT EXISTS churn_radar_scores (
            partner_id VARCHAR PRIMARY KEY,
            as_of_date DATE NOT NULL,
            hazard_probability_30d DOUBLE NOT NULL,
            priority_score DOUBLE NOT NULL,
            risk_tier VARCHAR NOT NULL,
            intervention_window VARCHAR NOT NULL,
            change_point_flag BOOLEAN NOT NULL,
            top_driver_family VARCHAR NOT NULL,
            top_driver_metric VARCHAR NOT NULL,
            top_driver_delta DOUBLE NOT NULL,
            narrative_summary VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "churn_cohort_alerts": """
        CREATE TABLE IF NOT EXISTS churn_cohort_alerts (
            alert_id VARCHAR PRIMARY KEY,
            region_id VARCHAR NOT NULL,
            partner_count INTEGER NOT NULL,
            aggregate_value_at_risk DOUBLE NOT NULL,
            p_value DOUBLE NOT NULL,
            common_driver VARCHAR NOT NULL,
            recommended_playbook VARCHAR NOT NULL,
            detected_at TIMESTAMP NOT NULL,
            status VARCHAR DEFAULT 'ACTIVE'
        )
    """,
    "decision_outcomes_ledger": """
        CREATE TABLE IF NOT EXISTS decision_outcomes_ledger (
            outcome_id VARCHAR PRIMARY KEY,
            intent_id VARCHAR NOT NULL,
            partner_id VARCHAR NOT NULL,
            playbook_id VARCHAR NOT NULL,
            treatment_assigned INTEGER NOT NULL,
            propensity_score DOUBLE NOT NULL,
            observed_retained_revenue_60d DOUBLE NOT NULL,
            actual_churn_60d BOOLEAN NOT NULL,
            recorded_at TIMESTAMP NOT NULL,
            manager_override_flag BOOLEAN DEFAULT FALSE,
            override_reason VARCHAR,
            unobserved_signal_proxy DOUBLE DEFAULT 0.0
        )
    """,
}

PARTNER_FRAUD_SCHEMAS = {
    "partner_fraud_scores": """
        CREATE TABLE IF NOT EXISTS partner_fraud_scores (
            partner_id VARCHAR PRIMARY KEY,
            master_partner_id VARCHAR,
            tier_level INTEGER NOT NULL,
            primary_typology VARCHAR NOT NULL,
            fraud_risk_score DOUBLE NOT NULL,
            client_quality_index DOUBLE NOT NULL,
            opposite_trading_pair_count INTEGER NOT NULL,
            bonus_abuse_probability DOUBLE NOT NULL,
            bot_traffic_probability DOUBLE NOT NULL,
            total_exposure_usd DOUBLE NOT NULL,
            computed_at TIMESTAMP NOT NULL
        )
    """,
    "partner_opposite_trading_pairs": """
        CREATE TABLE IF NOT EXISTS partner_opposite_trading_pairs (
            pair_id VARCHAR PRIMARY KEY,
            partner_a VARCHAR NOT NULL,
            account_a VARCHAR NOT NULL,
            partner_b VARCHAR NOT NULL,
            account_b VARCHAR NOT NULL,
            symbol VARCHAR NOT NULL,
            co_occurrence_count INTEGER NOT NULL,
            timing_correlation_pct DOUBLE NOT NULL,
            directional_type VARCHAR NOT NULL,
            combined_net_pl_usd DOUBLE NOT NULL,
            total_commission_usd DOUBLE NOT NULL,
            collusion_confidence DOUBLE NOT NULL,
            detected_at TIMESTAMP NOT NULL
        )
    """,
    "partner_fraud_cases": """
        CREATE TABLE IF NOT EXISTS partner_fraud_cases (
            case_id VARCHAR PRIMARY KEY,
            partner_id VARCHAR NOT NULL,
            master_partner_id VARCHAR,
            primary_typology VARCHAR NOT NULL,
            fraud_risk_score DOUBLE NOT NULL,
            total_exposure_usd DOUBLE NOT NULL,
            confidence_level VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'OPEN',
            created_at TIMESTAMP NOT NULL
        )
    """,
}

CLIENT_AML_SCHEMAS = {
    "aml_alert_scores": """
        CREATE TABLE IF NOT EXISTS aml_alert_scores (
            alert_id VARCHAR PRIMARY KEY,
            client_id VARCHAR NOT NULL,
            trigger_type VARCHAR NOT NULL,
            risk_score DOUBLE NOT NULL,
            priority_tier VARCHAR NOT NULL,
            typology VARCHAR NOT NULL,
            amount_usd DOUBLE NOT NULL,
            is_triage_top50 BOOLEAN NOT NULL DEFAULT FALSE,
            triggered_at TIMESTAMP NOT NULL
        )
    """,
    "aml_roundtrip_events": """
        CREATE TABLE IF NOT EXISTS aml_roundtrip_events (
            event_id VARCHAR PRIMARY KEY,
            client_id VARCHAR NOT NULL,
            deposit_txn_id VARCHAR NOT NULL,
            withdrawal_txn_id VARCHAR NOT NULL,
            deposit_amount_usd DOUBLE NOT NULL,
            withdrawal_amount_usd DOUBLE NOT NULL,
            trade_count INTEGER NOT NULL,
            net_pl_usd DOUBLE NOT NULL,
            market_risk_pct DOUBLE NOT NULL,
            holding_duration_seconds DOUBLE NOT NULL,
            hours_since_kyc DOUBLE NOT NULL,
            typology_risk_score DOUBLE NOT NULL,
            detected_at TIMESTAMP NOT NULL
        )
    """,
    "aml_mule_rings": """
        CREATE TABLE IF NOT EXISTS aml_mule_rings (
            cluster_id VARCHAR NOT NULL,
            client_id VARCHAR NOT NULL,
            cluster_size INTEGER NOT NULL,
            shared_payment_count INTEGER NOT NULL,
            shared_device_count INTEGER NOT NULL,
            total_volume_usd DOUBLE NOT NULL,
            is_syndicate BOOLEAN NOT NULL,
            explanation VARCHAR NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            PRIMARY KEY (cluster_id, client_id)
        )
    """,
    "aml_withdrawal_assessments": """
        CREATE TABLE IF NOT EXISTS aml_withdrawal_assessments (
            assessment_id VARCHAR PRIMARY KEY,
            withdrawal_id VARCHAR NOT NULL,
            client_id VARCHAR NOT NULL,
            amount_usd DOUBLE NOT NULL,
            risk_score DOUBLE NOT NULL,
            recommendation VARCHAR NOT NULL,
            decision_latency_ms DOUBLE NOT NULL,
            intent_id VARCHAR,
            evaluated_at TIMESTAMP NOT NULL
        )
    """,
    "aml_case_dossiers": """
        CREATE TABLE IF NOT EXISTS aml_case_dossiers (
            case_id VARCHAR PRIMARY KEY,
            client_id VARCHAR NOT NULL,
            composite_risk_score DOUBLE NOT NULL,
            priority_tier VARCHAR NOT NULL,
            recommended_action VARCHAR NOT NULL,
            total_deposit_usd DOUBLE NOT NULL,
            total_withdrawal_usd DOUBLE NOT NULL,
            roundtrip_count INTEGER NOT NULL,
            mule_ring_id VARCHAR,
            narrative_summary VARCHAR NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """,
}

GOVERNANCE_LEDGER_SCHEMAS = {
    "atomic_sequence_ledger": """
        CREATE TABLE IF NOT EXISTS atomic_sequence_ledger (
            ledger_seq BIGINT PRIMARY KEY,
            prev_hash VARCHAR(64) NOT NULL,
            current_hash VARCHAR(64) NOT NULL,
            event_type VARCHAR NOT NULL,
            entity_id VARCHAR NOT NULL,
            payload_digest VARCHAR(64) NOT NULL,
            payload JSON NOT NULL,
            recorded_at TIMESTAMP NOT NULL,
            worm_checkpoint_seq BIGINT
        )
    """,
    "governed_action_intents": """
        CREATE TABLE IF NOT EXISTS governed_action_intents (
            intent_id VARCHAR PRIMARY KEY,
            action_type VARCHAR NOT NULL,
            parameters JSON NOT NULL,
            evidence_refs JSON NOT NULL,
            severity VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            nonce VARCHAR NOT NULL UNIQUE,
            issued_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            requester_agent_id VARCHAR NOT NULL,
            kms_key_id VARCHAR NOT NULL,
            signature VARCHAR NOT NULL,
            approvals JSON NOT NULL,
            propensity_score DOUBLE,
            causal_context JSON,
            requires_dual_approval BOOLEAN NOT NULL,
            policy_tags JSON,
            ledger_seq BIGINT,
            execution_receipt_id VARCHAR
        )
    """,
    "simulated_writeback_ledger": """
        CREATE TABLE IF NOT EXISTS simulated_writeback_ledger (
            receipt_id VARCHAR PRIMARY KEY,
            intent_id VARCHAR NOT NULL,
            idempotency_key VARCHAR NOT NULL UNIQUE,
            external_transaction_id VARCHAR NOT NULL,
            action_type VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            simulated_latency_ms DOUBLE NOT NULL,
            executed_at TIMESTAMP NOT NULL,
            side_effects JSON NOT NULL,
            compensation_intent_id VARCHAR
        )
    """,
    "worm_anchor_checkpoints": """
        CREATE TABLE IF NOT EXISTS worm_anchor_checkpoints (
            checkpoint_seq BIGINT PRIMARY KEY,
            chain_head_seq BIGINT NOT NULL,
            chain_head_hash VARCHAR(64) NOT NULL,
            locked_at TIMESTAMP NOT NULL,
            retention_until TIMESTAMP NOT NULL,
            compliance_mode BOOLEAN NOT NULL DEFAULT TRUE,
            lock_signature VARCHAR NOT NULL
        )
    """,
}

TABLE_TIMESTAMP_COLUMNS: dict[str, str] = {
    "trading_activity": "open_ts",
    "transactions_aml": "timestamp",
    "clickstream": "event_time",
    "client_funnel": "entered_at",
    "partner_engagement_signals": "date",
    "partner_comms": "timestamp",
    "commission_ledger": "paid_at",
    "financial_pnl": "date",
    "partner_churn_scores": "computed_at",
    "churn_early_warnings": "detected_at",
    "churn_cohort_alerts": "detected_at",
    "decision_outcomes_ledger": "recorded_at",
    "partner_fraud_scores": "computed_at",
    "partner_opposite_trading_pairs": "detected_at",
    "partner_fraud_cases": "created_at",
    "aml_alert_scores": "triggered_at",
    "aml_roundtrip_events": "detected_at",
    "aml_mule_rings": "updated_at",
    "aml_withdrawal_assessments": "evaluated_at",
    "aml_case_dossiers": "created_at",
    "atomic_sequence_ledger": "recorded_at",
    "governed_action_intents": "issued_at",
    "simulated_writeback_ledger": "executed_at",
    "worm_anchor_checkpoints": "locked_at",
}


class HotStateEngine:
    """Thread-safe manager for the in-memory DuckDB hot state instance."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn = duckdb.connect(database=db_path)
        self._local = threading.local()
        self._init_schemas()

    def _get_local_cursor(self) -> duckdb.DuckDBPyConnection:
        if not hasattr(self._local, "cursor"):
            self._local.cursor = self._conn.cursor()
        return self._local.cursor

    def _init_schemas(self) -> None:
        """Create tables for all data products, churn radar state, partner fraud, client AML, and governance ledger."""
        cursor = self._get_local_cursor()
        for schema_sql in TABLE_SCHEMAS.values():
            cursor.execute(schema_sql)
        for schema_sql in CHURN_RADAR_SCHEMAS.values():
            cursor.execute(schema_sql)
        for schema_sql in PARTNER_FRAUD_SCHEMAS.values():
            cursor.execute(schema_sql)
        for schema_sql in CLIENT_AML_SCHEMAS.values():
            cursor.execute(schema_sql)
        for schema_sql in GOVERNANCE_LEDGER_SCHEMAS.values():
            cursor.execute(schema_sql)
        # Extend decision_outcomes_ledger with multi-horizon columns if missing
        try:
            cursor.execute("ALTER TABLE decision_outcomes_ledger ADD COLUMN IF NOT EXISTS observed_retained_revenue_30d DOUBLE")
            cursor.execute("ALTER TABLE decision_outcomes_ledger ADD COLUMN IF NOT EXISTS clawback_recovered_usd_90d DOUBLE")
            cursor.execute("ALTER TABLE decision_outcomes_ledger ADD COLUMN IF NOT EXISTS reconciled_at TIMESTAMP")
            cursor.execute("ALTER TABLE decision_outcomes_ledger ADD COLUMN IF NOT EXISTS causal_features JSON")
        except Exception:
            pass


    def get_cursor(self) -> duckdb.DuckDBPyConnection:
        """Provide a new cursor connection sharing the same database state."""
        return self._conn.cursor()

    def list_tables(self) -> list[str]:
        """List all tables registered in the hot state database."""
        res = self._get_local_cursor().execute("SHOW TABLES").fetchall()
        return [row[0] for row in res]

    def insert_event(self, product: DataProductEnum, payload: dict[str, Any]) -> None:
        """Insert a single dictionary event into the appropriate table."""
        table_name = product.value if isinstance(product, DataProductEnum) else str(product)
        columns = list(payload.keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        values = list(payload.values())

        query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
        self._get_local_cursor().execute(query, values)

    def evict_older_than(self, product: DataProductEnum, timestamp_col: str, hours: int = 24) -> int:
        """Sliding-window eviction: remove records older than cutoff hours."""
        table_name = product.value if isinstance(product, DataProductEnum) else str(product)
        cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        cursor = self._get_local_cursor()
        # Count rows to be deleted
        pre_count = cursor.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        cursor.execute(
            f"DELETE FROM {table_name} WHERE {timestamp_col} < ?",
            [cutoff_dt],
        )
        post_count = cursor.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        return pre_count - post_count

    def prune_hot_state(
        self,
        max_age_days: int = 30,
        as_of_ts: datetime | None = None,
    ) -> dict[str, int]:
        """Prunes time-series tables older than max_age_days to enforce hot-state scale ceiling."""
        if as_of_ts is None:
            as_of_ts = datetime.now(timezone.utc)
        elif as_of_ts.tzinfo is None:
            as_of_ts = as_of_ts.replace(tzinfo=timezone.utc)

        cutoff_dt = as_of_ts - timedelta(days=max_age_days)
        cursor = self._get_local_cursor()
        existing_tables = set(self.list_tables())
        pruned_stats: dict[str, int] = {}

        for table_name, ts_col in TABLE_TIMESTAMP_COLUMNS.items():
            if table_name not in existing_tables:
                continue
            try:
                pre_count = cursor.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
                if ts_col == "date":
                    cutoff_val = cutoff_dt.date()
                else:
                    cutoff_val = cutoff_dt
                cursor.execute(f"DELETE FROM {table_name} WHERE {ts_col} < ?", [cutoff_val])
                post_count = cursor.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
                pruned_stats[table_name] = pre_count - post_count
            except Exception:
                pruned_stats[table_name] = 0

        return pruned_stats

    def get_storage_metrics(self) -> dict[str, Any]:
        """Return table-level row counts and capacity statistics for hot state memory monitoring."""
        cursor = self._get_local_cursor()
        tables = self.list_tables()
        metrics: dict[str, int] = {}
        total_rows = 0
        for tbl in tables:
            try:
                count = cursor.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
                metrics[tbl] = count
                total_rows += count
            except Exception:
                metrics[tbl] = 0
        return {
            "db_path": self.db_path,
            "total_tables": len(tables),
            "total_rows": total_rows,
            "table_counts": metrics,
        }

    def close(self) -> None:
        """Close connection."""
        self._conn.close()
