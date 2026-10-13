"""Foundry Command Line Interface (CLI) and end-to-end multi-generator pipeline orchestrator."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from eios.foundry.generators.aml import AMLDataGenerator
from eios.foundry.generators.causal_truth import CausalTruthGenerator
from eios.foundry.generators.churn import ChurnDataGenerator
from eios.foundry.generators.client import ClientDataGenerator
from eios.foundry.generators.competitive import CompetitiveDataGenerator
from eios.foundry.generators.financial import FinancialDataGenerator
from eios.foundry.generators.operational import OperationalDataGenerator
from eios.foundry.generators.partner import PartnerDataGenerator
from eios.foundry.manifest import (
    FoundryManifest,
    compute_dataset_merkle_hash,
    validate_manifest_dict,
)
from eios.foundry.noise.prompt_injections import PromptInjectionGenerator
from eios.foundry.rng import RNGManager
from eios.foundry.storage.eval_truth_store import EvalTruthStore
from eios.foundry.storage.lineage import write_dataset_lineage
from eios.foundry.storage.parquet_writer import write_deterministic_parquet
from eios.foundry.universe import GlobalEntityUniverse


def run_pipeline(
    seed: int,
    tier: str,
    output_dir: Path | str,
    scale: float = 1.0,
) -> FoundryManifest:
    """Executes the complete Layer 0 Foundry generation pipeline across all 14 data products."""
    if tier == "sealed" and os.environ.get("CI_RELEASE_CANDIDATE") != "true":
        raise PermissionError(
            "Sealed seed generation is strictly restricted to CI release candidates "
            "(CI_RELEASE_CANDIDATE=true)."
        )

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = target_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    eval_dir = target_dir / "eval_truth"
    eval_dir.mkdir(parents=True, exist_ok=True)

    rng = RNGManager(seed=seed)
    eval_store = EvalTruthStore(eval_dir)
    run_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"foundry.run.{seed}.{tier}"))

    # Compute baseline counts scaled by scale parameter
    client_count = max(200, int(500 * scale))
    partner_count = max(70, int(100 * scale))

    universe = GlobalEntityUniverse(rng=rng, client_count=client_count, partner_count=partner_count)

    # 1. gen_client (client_360, client_funnel, device_network_graph)
    client_gen = ClientDataGenerator(universe=universe, rng=rng)
    r_c360 = client_gen.generate_client_360()
    r_funnel = client_gen.generate_client_funnel()
    r_device = client_gen.generate_device_network()

    _write_product(
        raw_dir / "client_360",
        "client_360",
        r_c360,
        "client_id",
        "Client360Record",
        run_uuid,
        universe,
    )
    _write_product(
        raw_dir / "client_funnel",
        "client_funnel",
        r_funnel,
        "event_id",
        "FunnelEventRecord",
        run_uuid,
        universe,
    )
    _write_product(
        raw_dir / "device_network",
        "device_network_graph",
        r_device,
        "edge_id",
        "DeviceNetworkEdge",
        run_uuid,
        universe,
    )

    # 2. gen_aml (transactions_aml, trading_activity, compliance_cases)
    aml_gen = AMLDataGenerator(universe=universe, rng=rng, truth_store=eval_store)
    tx_count = max(100, int(300 * scale))
    trades_count = max(100, int(300 * scale))
    cases_count = max(50, int(100 * scale))

    r_tx = aml_gen.generate_transactions(count=tx_count)
    r_trades = aml_gen.generate_trades(count=trades_count)
    r_cases = aml_gen.generate_compliance_cases(count=cases_count)
    syndicate_data = aml_gen.inject_syndicate_ring_and_round_trip()

    _write_product(
        raw_dir / "transactions_aml",
        "transactions_aml",
        r_tx,
        "transaction_id",
        "TransactionAMLRecord",
        run_uuid,
        universe,
    )
    _write_product(
        raw_dir / "trading_activity",
        "trading_activity",
        r_trades,
        "deal_id",
        "TradeExecutionRecord",
        run_uuid,
        universe,
    )
    _write_product(
        raw_dir / "compliance_cases",
        "compliance_cases",
        r_cases,
        "case_id",
        "ComplianceCaseRecord",
        run_uuid,
        universe,
    )

    # 3. gen_partner (partner_360, partner_referral_tree, commission_ledger)
    partner_gen = PartnerDataGenerator(universe=universe, rng=rng, truth_store=eval_store)
    r_p360 = partner_gen.generate_partner_360()
    r_tree = partner_gen.generate_referral_tree()
    r_ledger = partner_gen.generate_commission_ledger(count=max(100, int(200 * scale)))
    partner_fraud_data = partner_gen.generate_partner_fraud_suite()

    _write_product(
        raw_dir / "partner_360",
        "partner_360",
        r_p360,
        "partner_id",
        "Partner360Record",
        run_uuid,
        universe,
    )
    _write_product(
        raw_dir / "partner_referral_tree",
        "partner_referral_tree",
        r_tree,
        "link_id",
        "ReferralNodeRecord",
        run_uuid,
        universe,
    )
    _write_product(
        raw_dir / "commission_ledger",
        "commission_ledger",
        r_ledger,
        "ledger_id",
        "CommissionLedgerRecord",
        run_uuid,
        universe,
    )

    # 4. gen_partner_churn (partner_engagement_signals, partner_comms)
    churn_gen = ChurnDataGenerator(universe=universe, rng=rng)
    r_signals = churn_gen.generate_weekly_signals(weeks=8)
    seasonal_dips = churn_gen.get_seasonal_dip_partners()
    cohort_shock = churn_gen.get_regional_cohort_shock()

    inj_gen = PromptInjectionGenerator(universe=universe, rng=rng)
    r_comms = inj_gen.generate_comms_with_injections(count=max(50, int(100 * scale)))

    _write_product(
        raw_dir / "partner_engagement",
        "partner_engagement_signals",
        r_signals,
        "signal_id",
        "WeeklySignalRecord",
        run_uuid,
        universe,
    )
    _write_product(
        raw_dir / "partner_comms",
        "partner_comms",
        r_comms,
        "ticket_id",
        "PartnerCommsRecord",
        run_uuid,
        universe,
    )

    # 5. gen_financial (financial_pnl)
    fin_gen = FinancialDataGenerator(universe=universe, rng=rng)
    r_fin = fin_gen.generate_daily_pnl(days=30)
    _write_product(
        raw_dir / "financial_pnl",
        "financial_pnl",
        r_fin,
        "date",
        "DailyPnLRecord",
        run_uuid,
        universe,
    )

    # 6. gen_competitive (competitor_benchmarks)
    comp_gen = CompetitiveDataGenerator(rng=rng)
    r_comp = comp_gen.generate_events(count=max(30, int(40 * scale)))
    _write_product(
        raw_dir / "competitor_benchmarks",
        "competitor_benchmarks",
        r_comp,
        "event_id",
        "CompetitorEventRecord",
        run_uuid,
        universe,
    )

    # 7. gen_operational (platform_operations)
    ops_gen = OperationalDataGenerator(rng=rng)
    r_ops = ops_gen.generate_metrics(hours=48)
    _write_product(
        raw_dir / "platform_operations",
        "platform_operations",
        r_ops,
        "timestamp",
        "OperationalMetricRecord",
        run_uuid,
        universe,
    )

    # 8. gen_causal_truth (synthesis ground truth)
    causal_gen = CausalTruthGenerator(rng=rng, truth_store=eval_store)
    dag_data = causal_gen.generate_causal_dag()
    driver_data = causal_gen.generate_forecast_driver_attribution()

    # 9. Unified eval-ground-truth.json adhering to eval-ground-truth.schema.json
    unified_truth = _build_unified_ground_truth(
        run_uuid=run_uuid,
        tier=tier,
        universe=universe,
        syndicate_data=syndicate_data,
        partner_fraud_data=partner_fraud_data,
        seasonal_dips=seasonal_dips,
        cohort_shock=cohort_shock,
        dag_data=dag_data,
        driver_data=driver_data,
    )
    eval_store.write_truth("eval-ground-truth.json", unified_truth)

    # 10. Merkle hash across all raw datasets
    dataset_hash = compute_dataset_merkle_hash(raw_dir)

    manifest_data = {
        "manifest_id": run_uuid,
        "manifest_version": "1.0.0",
        "seed": seed,
        "seed_tier": tier,
        "git_sha": "a" * 40,
        "spec_hash": "b" * 64,
        "generator_versions": {
            "gen_client": "1.0.0",
            "gen_aml": "1.0.0",
            "gen_partner": "1.0.0",
            "gen_financial": "1.0.0",
            "gen_competitive": "1.0.0",
            "gen_operational": "1.0.0",
            "gen_causal_truth": "1.0.0",
        },
        "dataset_hash": dataset_hash,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    manifest = validate_manifest_dict(manifest_data)
    (target_dir / "manifest.yaml").write_text(json.dumps(manifest.model_dump(), indent=2))
    return manifest


def _write_product(
    product_dir: Path,
    product_name: str,
    records: list[dict[str, Any]],
    sort_key: str,
    schema_model: str,
    manifest_id: str,
    universe: GlobalEntityUniverse,
) -> None:
    """Helper writing a deterministic Parquet partition and its accompanying MMDP _lineage.json."""
    product_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = product_dir / f"{product_name}.parquet"
    write_deterministic_parquet(records, parquet_path, sort_key=sort_key)
    write_dataset_lineage(
        dataset_dir=product_dir,
        dataset_id=product_name,
        schema_model=schema_model,
        upstream_inputs=[f"foundry.universe.{universe.rng.master_seed}"],
        record_count=len(records),
        manifest_id_ref=manifest_id,
        metadata={
            "product_name": product_name,
            "partition_file": parquet_path.name,
        },
    )


def _build_unified_ground_truth(
    run_uuid: str,
    tier: str,
    universe: GlobalEntityUniverse,
    syndicate_data: dict[str, Any],
    partner_fraud_data: dict[str, Any],
    seasonal_dips: list[dict[str, Any]],
    cohort_shock: dict[str, Any],
    dag_data: dict[str, Any],
    driver_data: dict[str, Any],
) -> dict[str, Any]:
    """Constructs unified ground truth conforming strictly to eval-ground-truth.schema.json."""
    return {
        "manifest_id_ref": run_uuid,
        "seed_tier": tier,
        "module_a": {
            "syndicates": [
                {
                    "syndicate_id": "SYN-47-RING",
                    "member_count": 47,
                    "client_ids": syndicate_data["client_uuids"],
                    "shared_devices": syndicate_data["device_hashes"],
                    "shared_ips": syndicate_data["ip_addresses"],
                }
            ],
            "round_trip_tx_ids": syndicate_data["round_trip_transaction_ids"],
            "benign_hub_ips": ["100.64.0.1"],
        },
        "module_b": {
            "partner_rings": [
                {
                    "ring_id": "RING-7-23-184",
                    "master_partners": partner_fraud_data["ring_truth"]["master_partner_ids"],
                    "sub_affiliates": partner_fraud_data["ring_truth"]["sub_partner_ids"],
                    "recycled_clients": partner_fraud_data["ring_truth"]["referred_client_ids"],
                }
            ],
            "mirror_trading_pairs": [
                {
                    "client_a": p["client_a"],
                    "client_b": p["client_b"],
                    "symbol": "EURUSD",
                    "timing_correlation": p["timing_correlation"],
                }
                for p in partner_fraud_data["mirror_pairs"]
            ],
            "traffic_fraud_partner_ids": [
                bp["partner_id"] for bp in partner_fraud_data["bot_partners"]
            ],
            "hard_negatives": {
                "legitimate_hedgers": [c.client_id for c in universe.accounts[184:224]],
                "ib_portfolios": [p.partner_id for p in universe.partners[42:54]],
                "high_volume_referrers": [p.partner_id for p in universe.partners[54:69]],
            },
        },
        "module_c": {
            "seasonal_dip_partner_ids": [d["partner_id"] for d in seasonal_dips],
            "cohort_events": [
                {
                    "cohort_id": "COHORT-LATAM-01",
                    "region": cohort_shock["region"],
                    "partner_ids": cohort_shock["affected_partners"],
                    "trigger_date": "2025-04-01",
                }
            ],
        },
        "synthesis": {
            "causal_dag": {
                "edges": [
                    {
                        "from_node": e["source"],
                        "to_node": e["target"],
                        "true_effect": float(e["true_structural_coefficient"]),
                        "is_placebo": bool(e["is_placebo"]),
                        "refuter_p_value_expected": float(
                            e.get("placebo_refuter_expected_p_value", 0.45)
                        ),
                    }
                    for e in dag_data["edges"]
                ]
            },
            "forecast_driver_split": {
                "miss_id": "MISS-Q3-LTV",
                "drivers": {k: float(v) for k, v in driver_data["forecast_miss_drivers"].items()},
                "sum_percentage": 100.0,
            },
        },
    }


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EIOS Layer 0 Synthetic Foundry CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_p = subparsers.add_parser("generate", help="Run synthetic generation")
    gen_p.add_argument("--tier", choices=["dev", "validation", "sealed"], default="dev")
    gen_p.add_argument("--seed", type=int, default=42)
    gen_p.add_argument("--output-dir", type=str, default="data/output")
    gen_p.add_argument("--scale", type=float, default=1.0)

    hash_p = subparsers.add_parser("verify-hash", help="Verify Merkle hash")
    hash_p.add_argument("--dataset-dir", type=str, required=True)

    parsed = parser.parse_args(args)

    if parsed.command == "generate":
        manifest = run_pipeline(
            seed=parsed.seed,
            tier=parsed.tier,
            output_dir=parsed.output_dir,
            scale=parsed.scale,
        )
        print(f"Generation complete. Dataset Hash: {manifest.dataset_hash}")
        return 0

    if parsed.command == "verify-hash":
        h = compute_dataset_merkle_hash(parsed.dataset_dir)
        print(f"Dataset Hash: {h}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
