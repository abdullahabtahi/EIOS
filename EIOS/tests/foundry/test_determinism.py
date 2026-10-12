"""Tests for end-to-end byte-for-byte run determinism across all 14 data products (SC-001, FR-002)."""

from pathlib import Path
from eios.foundry.cli import run_pipeline

EXPECTED_PRODUCTS = [
    "client_360/client_360.parquet",
    "client_funnel/client_funnel.parquet",
    "device_network/device_network_graph.parquet",
    "transactions_aml/transactions_aml.parquet",
    "trading_activity/trading_activity.parquet",
    "compliance_cases/compliance_cases.parquet",
    "partner_360/partner_360.parquet",
    "partner_referral_tree/partner_referral_tree.parquet",
    "commission_ledger/commission_ledger.parquet",
    "partner_engagement/partner_engagement_signals.parquet",
    "partner_comms/partner_comms.parquet",
    "financial_pnl/financial_pnl.parquet",
    "competitor_benchmarks/competitor_benchmarks.parquet",
    "platform_operations/platform_operations.parquet",
]


def test_end_to_end_determinism_across_all_14_data_products(tmp_path: Path) -> None:
    """Verifies that two independent runs with identical seed produce byte-identical files across all 14 products."""
    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"

    manifest_a = run_pipeline(seed=42, tier="dev", output_dir=dir_a, scale=0.5)
    manifest_b = run_pipeline(seed=42, tier="dev", output_dir=dir_b, scale=0.5)

    # 1. Merkle root hash must match exactly
    assert manifest_a.dataset_hash == manifest_b.dataset_hash

    # 2. Check all 14 data products exist and are byte-for-byte identical
    for rel_path in EXPECTED_PRODUCTS:
        file_a = dir_a / "raw" / rel_path
        file_b = dir_b / "raw" / rel_path

        assert file_a.exists(), f"Missing product partition in run A: {rel_path}"
        assert file_b.exists(), f"Missing product partition in run B: {rel_path}"

        bytes_a = file_a.read_bytes()
        bytes_b = file_b.read_bytes()
        assert bytes_a == bytes_b, f"Non-deterministic byte mismatch detected in {rel_path}"
