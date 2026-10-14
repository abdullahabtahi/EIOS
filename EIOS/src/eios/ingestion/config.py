"""Configuration settings for EIOS Layer 1 Ingestion Spine & Contract Gateway."""

import os

from pydantic import BaseModel, Field


class IngestionConfig(BaseModel):
    """Configuration parameters for Pub/Sub, DuckDB, DLQ, and HTTP endpoints."""

    # Ingestion transport
    pubsub_project_id: str = Field(
        default_factory=lambda: os.getenv("EIOS_PUBSUB_PROJECT_ID", "deriv-eios-dev")
    )
    pubsub_topic_id: str = Field(
        default_factory=lambda: os.getenv("EIOS_PUBSUB_TOPIC_ID", "eios.l1.events.v1")
    )
    pubsub_subscription_id: str = Field(
        default_factory=lambda: os.getenv("EIOS_PUBSUB_SUBSCRIPTION_ID", "eios-l1-events-sub")
    )
    dlq_topic_id: str = Field(
        default_factory=lambda: os.getenv("EIOS_DLQ_TOPIC_ID", "eios.l1.dlq.v1")
    )

    # In-memory hot state & warm start
    duckdb_database_path: str = Field(
        default_factory=lambda: os.getenv("EIOS_DUCKDB_PATH", ":memory:eios_hot_state")
    )
    parquet_lakehouse_root: str = Field(
        # The directory holding `raw/` (foundry baseline) and `lakehouse/` (exported batches).
        default_factory=lambda: os.getenv("EIOS_LAKEHOUSE_ROOT", "data")
    )
    rehydration_timeout_seconds: float = Field(default=3.0)

    @property
    def warm_start_data_path(self) -> str:
        """Alias for backward compatibility."""
        return self.parquet_lakehouse_root

    # Micro-batching and flow control
    flow_control_max_messages: int = Field(default=1000)
    flow_control_max_bytes: int = Field(default=10 * 1024 * 1024)  # 10 MB
    microbatch_max_size: int = Field(default=250)
    microbatch_max_delay_ms: int = Field(default=500)

    # Security & Token Vault
    # Resolved (and enforced outside dev/test) by `vault.resolve_master_salt`; supplied from Secret Manager.
    hmac_salt: str | None = Field(default_factory=lambda: os.getenv("EIOS_HMAC_SALT"))
    vault_key_version: str = Field(default="v1")

    # Service endpoints
    server_host: str = Field(default="0.0.0.0")  # noqa: S104
    server_port: int = Field(default=8080)

    # Freshness SLA thresholds in seconds
    freshness_sla_seconds: dict[str, float] = Field(
        default={
            "client_360": 300.0,
            "client_funnel": 900.0,
            "transactions_aml": 30.0,
            "trading_activity": 30.0,
            "device_network_graph": 60.0,
            "partner_360": 900.0,
            "partner_referral_tree": 900.0,
            "commission_ledger": 900.0,
            "partner_engagement_signals": 3600.0,
            "partner_comms": 900.0,
            "financial_pnl": 3600.0,
            "competitor_benchmarks": 86400.0,
            "platform_operations": 300.0,
            "compliance_cases": 60.0,
        }
    )


# Global default configuration instance
_default_config: IngestionConfig | None = None


def get_ingestion_config() -> IngestionConfig:
    """Retrieve or initialize the process-global IngestionConfig."""
    global _default_config
    if _default_config is None:
        _default_config = IngestionConfig()
    return _default_config
