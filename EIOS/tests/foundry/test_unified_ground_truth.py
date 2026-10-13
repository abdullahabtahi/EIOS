"""Tests for unified eval-ground-truth.json schema validation (T066, FR-008, SC-005)."""

import json
from pathlib import Path

import jsonschema

from eios.foundry.cli import run_pipeline


def test_unified_ground_truth_matches_json_schema(tmp_path: Path):
    """Verifies that run_pipeline emits eval-ground-truth.json valid against JSON schema."""
    output_dir = tmp_path / "run_eval_truth"
    manifest = run_pipeline(seed=42, tier="dev", output_dir=output_dir, scale=0.5)

    truth_file = output_dir / "eval_truth" / "eval-ground-truth.json"
    assert truth_file.exists(), f"Missing unified ground truth file: {truth_file}"

    with open(truth_file, encoding="utf-8") as f:
        truth_data = json.load(f)

    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "eval-ground-truth.schema.json"
    assert schema_path.exists(), f"Schema file not found at {schema_path}"

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    # Validate against JSON schema
    jsonschema.validate(instance=truth_data, schema=schema)

    # Check key anchors
    assert truth_data["seed_tier"] == "dev"
    assert len(truth_data["module_a"]["syndicates"][0]["client_ids"]) == 47
    assert len(truth_data["module_b"]["partner_rings"][0]["master_partners"]) == 7
    assert len(truth_data["module_b"]["mirror_trading_pairs"]) == 23
    assert truth_data["synthesis"]["forecast_driver_split"]["sum_percentage"] == 100.0
