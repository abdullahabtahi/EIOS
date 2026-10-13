"""End-to-End Integration Test for EIOS Evaluation Harness (F04, T063).

Pipeline verification:
1. Load & manifest synthetic seeds
2. Run naive baselines & compute empirical delta lifts
3. Resample bootstrap confidence intervals
4. Execute all 7 Red-Line blocking gates
5. Emit schema-valid JSON eval report & Markdown summary table
6. Export standardized Model Card metadata and documentation
7. Full runner entrypoint and suite execution coverage
"""

from pathlib import Path

from evals.reports.generator import (
    build_sample_eval_report,
    render_markdown_summary_table,
    validate_report_json,
)
from evals.reports.model_card import (
    build_sample_model_card_metadata,
    export_model_card_markdown,
    save_model_card,
    validate_model_card_json,
)

from eios.evals.models import Tier
from evals.golden.trajectory_eval import (
    main as trajectory_main,
)
from evals.golden.trajectory_eval import (
    run_golden_dialogue_benchmarks,
)
from evals.suites.baselines.runner import main as baselines_main
from evals.suites.baselines.runner import run_all_baselines
from evals.suites.redlines.runner import main as redlines_main
from evals.suites.redlines.runner import run_all_redlines
from evals.suites.redlines.test_rl1_hallucination import main as rl1_main
from evals.suites.redlines.test_rl1_hallucination import test_rl1_suite
from evals.suites.redlines.test_rl2_citation import main as rl2_main
from evals.suites.redlines.test_rl2_citation import test_rl2_suite
from evals.suites.redlines.test_rl3_causal_gate import main as rl3_main
from evals.suites.redlines.test_rl3_causal_gate import test_rl3_suite
from evals.suites.redlines.test_rl4_no_autonomous_write import main as rl4_main
from evals.suites.redlines.test_rl4_no_autonomous_write import test_rl4_suite
from evals.suites.redlines.test_rl5_pii_leakage import main as rl5_main
from evals.suites.redlines.test_rl5_pii_leakage import test_rl5_suite
from evals.suites.redlines.test_rl6_prompt_injection import main as rl6_main
from evals.suites.redlines.test_rl6_prompt_injection import test_rl6_suite
from evals.suites.redlines.test_rl7_action_intent import main as rl7_main
from evals.suites.redlines.test_rl7_action_intent import test_rl7_suite
from evals.suites.splits.runner import generate_seed_manifest, run_seed_splits
from evals.suites.splits.runner import main as splits_main


def test_full_e2e_evaluation_pipeline(tmp_path: Path):
    # Step 1: Multi-seed manifest & splits
    manifest = generate_seed_manifest(Tier.VALIDATION)
    assert len(manifest.seeds) >= 10
    splits_res = run_seed_splits(Tier.VALIDATION)
    assert splits_res["seed_count"] == 10

    # Step 2: Naive baselines & delta benchmarks
    baseline_res = run_all_baselines()
    assert baseline_res["all_benchmarks_computed"] is True
    assert len(baseline_res["comparisons"]) == 4

    # Step 3: Red-Line gates (zero tolerance)
    redline_res = run_all_redlines()
    assert redline_res["all_passed"] is True
    assert redline_res["total_violations"] == 0

    # Step 4: Schema-valid report generation
    report = build_sample_eval_report()
    report_dict = report.model_dump(mode="json")
    valid_report, report_errs = validate_report_json(report_dict)
    assert valid_report is True, f"Report JSON validation failed: {report_errs}"

    md_table = render_markdown_summary_table(report)
    assert "| Suite ID | Tier | Status | Gate Pass % |" in md_table
    assert "[TARGET]" in md_table

    # Step 5: Model card exporter
    mc_metadata = build_sample_model_card_metadata()
    valid_mc, mc_errs = validate_model_card_json(mc_metadata)
    assert valid_mc is True, f"Model Card validation failed: {mc_errs}"

    mc_dir = tmp_path / "model_cards"
    saved_path = save_model_card(mc_metadata, output_dir=mc_dir)
    assert saved_path.is_file()

    mc_markdown = export_model_card_markdown(mc_metadata)
    assert "# Model Card: LightGBM Client AML Alert Scorer" in mc_markdown

    # Step 6: Golden dialogue benchmarks
    dial_res = run_golden_dialogue_benchmarks()
    assert dial_res["target_met"] is True


def test_suite_entrypoint_mains_and_runners():
    # Execute suite direct test functions
    test_rl1_suite()
    test_rl2_suite()
    test_rl3_suite()
    test_rl4_suite()
    test_rl5_suite()
    test_rl6_suite()
    test_rl7_suite()

    # Execute main() runners that write individual JSON reports
    rl1_main()
    rl2_main()
    rl3_main()
    rl4_main()
    rl5_main()
    rl6_main()
    rl7_main()

    # Verify report files were created
    assert Path("evals/reports/rl_hallucination.json").is_file()
    assert Path("evals/reports/rl_citation.json").is_file()
    assert Path("evals/reports/rl_causal_gate.json").is_file()
    assert Path("evals/reports/rl_no_autonomous_write.json").is_file()
    assert Path("evals/reports/rl_pii_leakage.json").is_file()
    assert Path("evals/reports/rl_prompt_injection.json").is_file()
    assert Path("evals/reports/rl_action_intent.json").is_file()

    # Aggregator mains
    redlines_main()
    baselines_main()
    splits_main()
    trajectory_main()

    assert Path("evals/reports/red_line_summary.json").is_file()
    assert Path("evals/reports/baseline_benchmarks.json").is_file()
    assert Path("evals/reports/splits_validation.json").is_file()
    assert Path("evals/reports/dialogue_evals.json").is_file()
