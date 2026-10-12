"""Tests for Report Generator and Schema Validation (T053)."""

from evals.reports.generator import (
    build_sample_eval_report,
    render_markdown_summary_table,
    validate_report_json,
)


def test_eval_report_validates_against_json_schema():
    report = build_sample_eval_report()
    data = report.model_dump(mode="json")
    is_valid, errors = validate_report_json(data)
    assert is_valid is True, f"Report JSON validation errors: {errors}"


def test_markdown_summary_table_formatting():
    report = build_sample_eval_report()
    md = render_markdown_summary_table(report)
    assert "| Suite ID | Tier | Status | Gate Pass % |" in md
    assert "[TARGET]" in md or "[BRIEF]" in md
    assert "Red-Line Gates" in md
    assert "Naive Baselines" in md
