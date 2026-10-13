"""Budget alert rules (FR-038, acceptance scenario 3): ``--rules budget`` over config and Terraform."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from tests.support.budget_tree import (
    BUDGETS_PATH,
    budget_files,
    call_text,
    module_files,
    render_budgets,
    with_call,
)
from tests.support.infra_tree import ENVIRONMENTS, good_files, with_file
from tests.support.repo_builder import build_repo
from tools.common.findings import Finding
from tools.infra_checks.runner import main, run_checks
from tools.infra_checks.runner import run_rules as _run_rules

DEV_MAIN = "infra/envs/dev/main.tf"
STAGE_MAIN = "infra/envs/stage/main.tf"


def run_budget(tmp_path: Path, files: Mapping[str, str]) -> tuple[Finding, ...]:
    return _run_rules(build_repo(tmp_path, files), "budget")


def rules_of(findings: tuple[Finding, ...]) -> set[str]:
    return {f.rule_id for f in findings}


def _call(files: Mapping[str, str], env: str, overrides: Mapping[str, str]) -> dict[str, str]:
    return with_call(files, env, call_text(overrides))


# --- the valid tree --------------------------------------------------------------------------


def test_a_fully_wired_tree_has_no_budget_findings(tmp_path: Path) -> None:
    assert run_budget(tmp_path, budget_files()) == ()


def test_a_tree_with_neither_budgets_nor_environments_has_nothing_to_judge(tmp_path: Path) -> None:
    assert run_budget(tmp_path, {"infra/main.tf": 'output "m" { value = 1 }\n'}) == ()


def test_the_default_run_does_not_include_the_budget_rules(tmp_path: Path) -> None:
    root = build_repo(tmp_path, good_files())  # environments exist, config/budgets.yaml does not
    assert run_checks(root) == ()
    assert "infra.budget.config" in rules_of(_run_rules(root, "budget"))


# --- config/budgets.yaml ---------------------------------------------------------------------


def test_the_thresholds_must_include_50_80_and_100(tmp_path: Path) -> None:
    files = with_file(budget_files(), BUDGETS_PATH, render_budgets(thresholds=(50, 80)))
    found = run_budget(tmp_path, files)
    assert "infra.budget.thresholds" in rules_of(found)
    assert any("100" in f.message for f in found)


def test_the_thresholds_must_be_ascending(tmp_path: Path) -> None:
    files = with_file(budget_files(), BUDGETS_PATH, render_budgets(thresholds=(80, 50, 100)))
    assert "infra.budget.thresholds" in rules_of(run_budget(tmp_path, files))


@pytest.mark.parametrize("bad", [(50, 80, 100, 100), (0, 50, 80, 100), (-5, 50, 80, 100)])
def test_the_thresholds_must_be_strictly_ascending_positive_percentages(
    tmp_path: Path, bad: tuple[int, ...]
) -> None:
    files = with_file(budget_files(), BUDGETS_PATH, render_budgets(thresholds=bad))
    assert "infra.budget.thresholds" in rules_of(run_budget(tmp_path, files))


def test_the_thresholds_must_be_numbers(tmp_path: Path) -> None:
    files = with_file(budget_files(), BUDGETS_PATH, render_budgets(thresholds="50,80,100"))
    assert "infra.budget.thresholds" in rules_of(run_budget(tmp_path, files))


def test_the_thresholds_must_carry_the_target_tag(tmp_path: Path) -> None:
    files = with_file(budget_files(), BUDGETS_PATH, render_budgets(thresholds_tag="[BRIEF]"))
    assert "infra.budget.threshold_tag" in rules_of(run_budget(tmp_path, files))


def test_each_environment_needs_an_amount_with_a_provenance_tag(tmp_path: Path) -> None:
    amounts = {"dev": 20, "stage": 50}
    files = with_file(budget_files(), BUDGETS_PATH, render_budgets(amounts=amounts))
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.amount"]
    assert found
    assert any("prod-like" in f.message for f in found)


@pytest.mark.parametrize("tag", ["", "[GUESS]", "ASSUMPTION", None])
def test_an_amount_without_a_valid_tag_is_a_finding_naming_the_environment(
    tmp_path: Path, tag: object
) -> None:
    files = with_file(budget_files(), BUDGETS_PATH, render_budgets(tags={"stage": tag}))
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.amount_tag"]
    assert found
    assert "stage" in found[0].message


@pytest.mark.parametrize("amount", [0, -1, "20", None, True])
def test_an_amount_must_be_a_positive_number(tmp_path: Path, amount: object) -> None:
    files = with_file(
        budget_files(),
        BUDGETS_PATH,
        render_budgets(amounts={"dev": amount, "stage": 50, "prod-like": 100}),
    )
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.amount"]
    assert found
    assert "dev" in found[0].message


@pytest.mark.parametrize("currency", ["", "usd", 5, None])
def test_the_currency_must_be_a_three_letter_code(tmp_path: Path, currency: object) -> None:
    files = with_file(budget_files(), BUDGETS_PATH, render_budgets(currency=currency))
    assert "infra.budget.currency" in rules_of(run_budget(tmp_path, files))


def test_a_missing_budgets_file_is_a_finding_once_environments_exist(tmp_path: Path) -> None:
    files = {k: v for k, v in budget_files().items() if k != BUDGETS_PATH}
    assert "infra.budget.config" in rules_of(run_budget(tmp_path, files))


@pytest.mark.parametrize("text", ["- a\n- b\n", "thresholds_percent: [50\n", "", "just text\n"])
def test_an_unusable_budgets_file_is_a_finding_not_a_crash(tmp_path: Path, text: str) -> None:
    found = run_budget(tmp_path, with_file(budget_files(), BUDGETS_PATH, text))
    assert "infra.budget.config" in rules_of(found)


# --- the module ------------------------------------------------------------------------------


@pytest.mark.parametrize("variable", ["thresholds_percent", "amount", "currency_code"])
def test_the_module_has_no_default_for_thresholds_amount_or_currency(
    tmp_path: Path, variable: str
) -> None:
    files = {**budget_files(), **module_files(defaults=(variable,))}
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.module_default"]
    assert found
    assert variable in found[0].message


@pytest.mark.parametrize("variable", ["thresholds_percent", "amount", "currency_code"])
def test_the_module_must_declare_the_required_variables(tmp_path: Path, variable: str) -> None:
    files = {**budget_files(), **module_files(omit_variable=variable)}
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.module_variable"]
    assert found
    assert variable in found[0].message


def test_the_module_must_declare_a_notification_channel(tmp_path: Path) -> None:
    files = {**budget_files(), **module_files(channel=False)}
    assert "infra.budget.channel" in rules_of(run_budget(tmp_path, files))


def test_the_module_must_output_the_channel_identifier(tmp_path: Path) -> None:
    files = {**budget_files(), **module_files(channel_output=False)}
    assert "infra.budget.channel_output" in rules_of(run_budget(tmp_path, files))


def test_the_module_must_exist_once_environments_exist(tmp_path: Path) -> None:
    files = {k: v for k, v in budget_files().items() if "modules/budget_alerts" not in k}
    assert "infra.budget.module_missing" in rules_of(run_budget(tmp_path, files))


# --- environment composition -----------------------------------------------------------------


def test_an_environment_that_does_not_call_the_module_is_named(tmp_path: Path) -> None:
    files = budget_files()
    files[STAGE_MAIN] = files[STAGE_MAIN].split('module "budget_alerts"')[0]
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.env_call"]
    assert [f.file for f in found] == [STAGE_MAIN]
    assert "stage" in found[0].message


def test_removing_a_threshold_from_one_environment_fails_naming_it(tmp_path: Path) -> None:
    files = _call(budget_files(), "stage", {"thresholds_percent": "[50, 80]"})
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.env_threshold"]
    assert len(found) == 1
    assert found[0].file == STAGE_MAIN
    assert "stage" in found[0].message
    assert "100" in found[0].message


def test_a_literal_threshold_list_is_a_literal_finding_even_when_it_is_complete(
    tmp_path: Path,
) -> None:
    files = _call(budget_files(), "dev", {"thresholds_percent": "[50, 80, 100]"})
    found = run_budget(tmp_path, files)
    assert "infra.budget.literal" in rules_of(found)
    assert "infra.budget.env_threshold" not in rules_of(found)


def test_the_environment_must_pass_thresholds_at_all(tmp_path: Path) -> None:
    files = with_call(budget_files(), "dev", call_text(omit=("thresholds_percent",)))
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.env_threshold"]
    assert found
    assert "dev" in found[0].message


def test_an_expression_that_hides_a_threshold_cannot_be_proven(tmp_path: Path) -> None:
    expression = "slice(local.budgets.thresholds_percent, 0, 2)"
    files = _call(budget_files(), "dev", {"thresholds_percent": expression})
    assert "infra.budget.env_threshold" in rules_of(run_budget(tmp_path, files))


def test_a_literal_amount_is_a_finding(tmp_path: Path) -> None:
    files = _call(budget_files(), "dev", {"amount": "25"})
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.literal"]
    assert found
    assert "dev" in found[0].message


def test_an_amount_read_for_another_environment_is_a_finding(tmp_path: Path) -> None:
    other = 'local.budgets.environments["prod-like"].amount'
    files = _call(budget_files(), "dev", {"amount": other})
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.amount_env"]
    assert found
    assert "dev" in found[0].message


def test_the_amount_may_be_indexed_by_the_environments_own_literal_name(tmp_path: Path) -> None:
    own = 'local.budgets.environments["dev"].amount'
    assert run_budget(tmp_path, _call(budget_files(), "dev", {"amount": own})) == ()


def test_the_inline_yamldecode_form_is_accepted(tmp_path: Path) -> None:
    inline = 'yamldecode(file("${path.module}/../../../config/budgets.yaml")).thresholds_percent'
    assert run_budget(tmp_path, _call(budget_files(), "dev", {"thresholds_percent": inline})) == ()


def test_a_local_that_does_not_read_the_budgets_file_is_not_trusted(tmp_path: Path) -> None:
    files = budget_files()
    files[DEV_MAIN] = files[DEV_MAIN].replace("config/budgets.yaml", "config/other.yaml")
    assert "infra.budget.env_threshold" in rules_of(run_budget(tmp_path, files))


def test_a_literal_threshold_percent_anywhere_under_infra_is_a_finding(tmp_path: Path) -> None:
    extra = (
        'resource "google_billing_budget" "extra" {\n'
        "  threshold_rules {\n    threshold_percent = 0.5\n  }\n}\n"
    )
    files = with_file(budget_files(), "infra/envs/dev/extra.tf", extra)
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.literal"]
    assert [f.file for f in found] == ["infra/envs/dev/extra.tf"]


@pytest.mark.parametrize("env", ENVIRONMENTS)
def test_every_environment_is_checked(tmp_path: Path, env: str) -> None:
    files = _call(budget_files(), env, {"thresholds_percent": "[50]"})
    found = [f for f in run_budget(tmp_path, files) if f.rule_id == "infra.budget.env_threshold"]
    assert [f.file for f in found] == [f"infra/envs/{env}/main.tf"]


# --- command line ----------------------------------------------------------------------------


def test_rules_budget_exits_0_and_writes_its_own_report(tmp_path: Path) -> None:
    root = build_repo(tmp_path, budget_files())
    assert main(["--repo-root", str(root), "--rules", "budget"]) == 0
    report = json.loads((root / "evals/reports/infra_checks_budget.json").read_text())
    assert report["tool"] == "infra_checks_budget"
    assert report["finding_count"] == 0
    assert not (root / "evals/reports/infra_checks.json").exists()


def test_rules_budget_exits_1_on_a_missing_threshold(tmp_path: Path) -> None:
    files = _call(budget_files(), "prod-like", {"thresholds_percent": "[50, 100]"})
    root = build_repo(tmp_path, files)
    assert main(["--repo-root", str(root), "--rules", "budget"]) == 1


def test_the_default_run_ignores_budget_faults_and_keeps_its_own_report(tmp_path: Path) -> None:
    files = _call(budget_files(), "prod-like", {"thresholds_percent": "[50]"})
    root = build_repo(tmp_path, files)
    assert main(["--repo-root", str(root)]) == 0
    assert (root / "evals/reports/infra_checks.json").is_file()


def test_rules_all_runs_core_and_budget_together(tmp_path: Path) -> None:
    files = _call(budget_files(), "prod-like", {"thresholds_percent": "[50]"})
    root = build_repo(tmp_path, files)
    assert main(["--repo-root", str(root), "--rules", "all"]) == 1
    assert (
        main(["--repo-root", str(build_repo(tmp_path / "ok", budget_files())), "--rules", "all"])
        == 0
    )


def test_an_unknown_rule_set_exits_2(tmp_path: Path) -> None:
    root = build_repo(tmp_path, budget_files())
    assert main(["--repo-root", str(root), "--rules", "nonsense"]) == 2


def test_rules_without_a_value_exits_2(tmp_path: Path) -> None:
    root = build_repo(tmp_path, budget_files())
    assert main(["--repo-root", str(root), "--rules"]) == 2


def test_the_real_repository_budget_rules_are_clean() -> None:
    repo = Path(__file__).resolve().parents[4]
    assert _run_rules(repo, "budget") == ()
