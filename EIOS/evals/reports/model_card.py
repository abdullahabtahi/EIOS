"""Standardized Model Card Generator & Schema Validator (T056).

Generates schema-valid Model Card metadata and exports comprehensive Model Card documentation
under evals/reports/model_cards/.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema


def get_model_card_schema_path() -> Path:
    cand1 = Path("schemas/evals/model-card.schema.json")
    if cand1.is_file():
        return cand1
    cand2 = Path("FEIOS/schemas/evals/model-card.schema.json")
    if cand2.is_file():
        return cand2
    return Path(__file__).resolve().parents[2] / "schemas" / "evals" / "model-card.schema.json"


def validate_model_card_json(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate Model Card metadata against schemas/evals/model-card.schema.json."""
    schema_path = get_model_card_schema_path()
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    validator = jsonschema.Draft202012Validator(schema)
    errors = [e.message for e in validator.iter_errors(data)]
    return len(errors) == 0, errors


def build_sample_model_card_metadata() -> dict[str, Any]:
    """Build complete, valid Model Card metadata."""
    return {
        "model_id": "client-aml-alert-scorer",
        "model_name": "LightGBM Client AML Alert Scorer",
        "version": "1.2.0",
        "owner_role": "sa-eval-harness",
        "model_type": "gradient_boosted",
        "created_at": datetime.now(UTC).isoformat(),
        "intended_use": "Prioritisation and triage of AML alerts for compliance officer review.",
        "out_of_scope_use": "Autonomous filing of SARs or account closure without human officer approval.",
        "data_splits": {
            "dev_seeds": [42],
            "validation_seeds": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            "sealed_seeds": [901, 902, 903, 904, 905],
        },
        "metrics_vs_baseline": [
            {
                "metric": "PR-AUC",
                "baseline": 0.62,
                "candidate": 0.94,
                "delta": 0.32,
                "target": "Lift >= 30% [TARGET]",
                "target_met": True,
            },
            {
                "metric": "False Positive Rate (FPR)",
                "baseline": 0.28,
                "candidate": 0.06,
                "delta": -0.22,
                "target": "Relative reduction >= 30% [TARGET]",
                "target_met": True,
            },
        ],
        "calibration": {
            "brier_score": 0.038,
            "reliability_slope": 0.98,
        },
        "limitations": [
            "Trained on synthetic typology seeds; requires ongoing batch feedback loop from officer decisions.",
            "Sub-optimal on accounts with less than 24h of transaction history.",
        ],
        "fallback_class": "RuleBasedAMLBaseline",
    }


def export_model_card_markdown(metadata: dict[str, Any]) -> str:
    """Export standardized 6-section Model Card markdown per data-model.md."""
    splits = metadata.get("data_splits", {})
    calib = metadata.get("calibration", {})

    lines: list[str] = [
        f"# Model Card: {metadata.get('model_name')} (Version: {metadata.get('version')})",
        "",
        "## 1. Model Details",
        f"- **Model ID**: `{metadata.get('model_id')}`",
        f"- **Model Type**: `{metadata.get('model_type')}`",
        f"- **Owner Role**: `{metadata.get('owner_role')}`",
        f"- **Created At**: `{metadata.get('created_at')}`",
        "",
        "## 2. Intended Use & Boundaries",
        f"- **Intended Use**: {metadata.get('intended_use')}",
        f"- **Out-of-Scope Use**: {metadata.get('out_of_scope_use')}",
        "",
        "## 3. Training & Validation Data Splits",
        f"- **Dev Seeds**: `{splits.get('dev_seeds')}`",
        f"- **Validation Seeds (>= 10)**: `{splits.get('validation_seeds')}`",
        f"- **Sealed Holdout Seeds (>= 5)**: `{splits.get('sealed_seeds')}`",
        "",
        "## 4. Empirical Evaluation vs Pre-Registered Baselines `[TARGET]`",
        "| Metric | Baseline | Candidate | Delta | Target Commitment | Target Met |",
        "|---|---|---|---|---|---|",
    ]

    for m in metadata.get("metrics_vs_baseline", []):
        tm_str = "YES" if m.get("target_met") else "NO"
        lines.append(
            f"| `{m.get('metric')}` | {m.get('baseline'):.4f} | {m.get('candidate'):.4f} | "
            f"{m.get('delta'):+.4f} | {m.get('target')} | **{tm_str}** |"
        )

    lines.extend(
        [
            "",
            "## 5. Calibration & Reliability",
            f"- **Brier Calibration Score**: `{calib.get('brier_score')}` (near 0 is optimal)",
            f"- **Reliability Slope**: `{calib.get('reliability_slope')}` (1.0 is ideal)",
            "",
            "## 6. Known Limitations & Rollback Procedures",
            "### Limitations",
        ]
    )

    for lim in metadata.get("limitations", []):
        lines.append(f"- {lim}")

    lines.extend(
        [
            "",
            "### Rollback & Fallback Procedure",
            f"If production drift or performance degradation exceeds trigger thresholds, immediately divert alerting traffic to fallback class `{metadata.get('fallback_class')}`.",
        ]
    )

    return "\n".join(lines) + "\n"


def save_model_card(
    metadata: dict[str, Any],
    output_dir: Path | str = "evals/reports/model_cards",
) -> Path:
    """Save Model Card metadata JSON and rendered Markdown to output_dir."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    model_id = metadata["model_id"]
    json_path = out_path / f"{model_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    md_content = export_model_card_markdown(metadata)
    md_path = out_path / f"{model_id}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return md_path
