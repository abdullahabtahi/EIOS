"""Tests for Model Card Exporter and Schema Validation (T054)."""

from evals.reports.model_card import (
    build_sample_model_card_metadata,
    export_model_card_markdown,
    validate_model_card_json,
)


def test_model_card_metadata_validates_against_json_schema():
    metadata = build_sample_model_card_metadata()
    is_valid, errors = validate_model_card_json(metadata)
    assert is_valid is True, f"Model Card validation errors: {errors}"


def test_export_model_card_markdown_structure():
    metadata = build_sample_model_card_metadata()
    md = export_model_card_markdown(metadata)
    assert "# Model Card: LightGBM Client AML Alert Scorer" in md
    assert "## 1. Model Details" in md
    assert "## 2. Intended Use & Boundaries" in md
    assert "## 3. Training & Validation Data Splits" in md
    assert "## 4. Empirical Evaluation vs Pre-Registered Baselines" in md
    assert "## 5. Calibration & Reliability" in md
    assert "## 6. Known Limitations & Rollback Procedures" in md
    assert "Fallback Procedure" in md
