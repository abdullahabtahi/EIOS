"""T188 (FR-039): every service directory carries valid slo.md, runbook.md and warm_start.md."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from tests.support.repo_builder import build_repo
from tools.repo_checks.runner import main
from tools.repo_checks.service_docs import check_service_docs

SLO = (
    "# SLO\n\n- Indicator: request success ratio\n- Objective: to be set by the owning feature\n"
    "- Owner feature: F00\n- Status: placeholder\n"
)
RUNBOOK = (
    "# Runbook\n\n## Symptoms\n\nHealth probe fails.\n\n## First checks\n\nRead the logs.\n\n"
    "## Escalation\n\nPage the owner.\n\n## Rollback\n\nRedeploy the previous revision.\n"
)
WARM_NO = "# Warm start\n\nHolds in-memory state: no\n"
WARM_YES = (
    "# Warm start\n\nHolds in-memory state: yes\n\nWarm-up behaviour: reload the cache on boot.\n"
)
GOOD: Mapping[str, str] = {"slo.md": SLO, "runbook.md": RUNBOOK, "warm_start.md": WARM_NO}


def _repo(
    tmp_path: Path,
    services: Mapping[str, Mapping[str, str]],
    extra: Mapping[str, str] | None = None,
) -> Path:
    files = {
        f"services/{svc}/{name}": text
        for svc, docs in services.items()
        for name, text in docs.items()
    }
    return build_repo(tmp_path, {**files, **(extra or {})})


def _with(**overrides: str | None) -> dict[str, str]:
    """GOOD docs, replacing (or dropping, for None) a file; ``slo_md`` stands for ``slo.md``."""
    docs = dict(GOOD)
    for key, value in overrides.items():
        name = key.removesuffix("_md") + ".md"
        if value is None:
            docs.pop(name)
        else:
            docs[name] = value
    return docs


def test_valid_service_has_no_findings(tmp_path: Path) -> None:
    assert check_service_docs(_repo(tmp_path, {"svc_a": GOOD})) == ()


def test_no_services_directory_means_nothing_to_check(tmp_path: Path) -> None:
    assert check_service_docs(build_repo(tmp_path, {"a.py": "x = 1\n"})) == ()


def test_underscore_directories_and_loose_files_are_not_services(tmp_path: Path) -> None:
    root = _repo(
        tmp_path,
        {"svc_a": GOOD},
        {
            "services/__init__.py": "",
            "services/__pycache__/x.pyc": "",
            "services/_shared/a.md": "x",
        },
    )
    assert check_service_docs(root) == ()


def test_missing_file_names_service_and_file(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"svc_a": _with(runbook_md=None)})
    (finding,) = check_service_docs(root)
    assert finding.file == "services/svc_a/runbook.md"
    assert "svc_a" in finding.message and "runbook.md" in finding.message
    assert finding.rule_id == "repo.service_docs.missing_file"


def test_empty_file_fails(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"svc_a": _with(warm_start_md="  \n")})
    (finding,) = check_service_docs(root)
    assert finding.file == "services/svc_a/warm_start.md"
    assert finding.rule_id == "repo.service_docs.empty_file"


def test_each_service_is_reported_separately_and_sorted(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"b": _with(slo_md=None), "a": _with(runbook_md=None)})
    files = [f.file for f in check_service_docs(root)]
    assert files == ["services/a/runbook.md", "services/b/slo.md"]


def test_slo_missing_field_names_the_field(tmp_path: Path) -> None:
    slo = SLO.replace("- Owner feature: F00\n", "")
    (finding,) = check_service_docs(_repo(tmp_path, {"svc_a": _with(slo_md=slo)}))
    assert finding.rule_id == "repo.service_docs.slo_field"
    assert "owner feature" in finding.message


def test_slo_field_with_blank_value_fails(tmp_path: Path) -> None:
    slo = SLO.replace("request success ratio", "")
    (finding,) = check_service_docs(_repo(tmp_path, {"svc_a": _with(slo_md=slo)}))
    assert "indicator" in finding.message


def test_slo_fields_accept_bold_markup(tmp_path: Path) -> None:
    slo = (
        "**Indicator:** latency\n**Objective:** to be set by the owning feature\n"
        "**Owner feature:** F00\n**Status:** placeholder\n"
    )
    assert check_service_docs(_repo(tmp_path, {"svc_a": _with(slo_md=slo)})) == ()


def test_slo_status_must_be_known(tmp_path: Path) -> None:
    slo = SLO.replace("placeholder", "whatever")
    (finding,) = check_service_docs(_repo(tmp_path, {"svc_a": _with(slo_md=slo)}))
    assert finding.rule_id == "repo.service_docs.slo_status"


def test_untagged_objective_figure_fails_and_tagged_passes(tmp_path: Path) -> None:
    bad = SLO.replace("to be set by the owning feature", "99.5 percent of requests succeed")
    (finding,) = check_service_docs(_repo(tmp_path / "a", {"svc_a": _with(slo_md=bad)}))
    assert finding.rule_id == "repo.service_docs.slo_untagged_figure"
    good = bad.replace("succeed", "succeed [TARGET]")
    assert check_service_docs(_repo(tmp_path / "b", {"svc_a": _with(slo_md=good)})) == ()


def test_runbook_missing_section_names_it(tmp_path: Path) -> None:
    runbook = RUNBOOK.replace("## Rollback\n\nRedeploy the previous revision.\n", "")
    (finding,) = check_service_docs(_repo(tmp_path, {"svc_a": _with(runbook_md=runbook)}))
    assert finding.rule_id == "repo.service_docs.runbook_section"
    assert "rollback" in finding.message


def test_runbook_section_without_body_fails(tmp_path: Path) -> None:
    runbook = RUNBOOK.replace("Page the owner.\n", "")
    (finding,) = check_service_docs(_repo(tmp_path, {"svc_a": _with(runbook_md=runbook)}))
    assert "escalation" in finding.message


def test_runbook_without_any_section_reports_all_four(tmp_path: Path) -> None:
    findings = check_service_docs(_repo(tmp_path, {"svc_a": _with(runbook_md="just prose\n")}))
    assert len(findings) == 4


def test_warm_start_requires_the_state_statement(tmp_path: Path) -> None:
    (finding,) = check_service_docs(_repo(tmp_path, {"svc_a": _with(warm_start_md="hello\n")}))
    assert finding.rule_id == "repo.service_docs.warm_state"


def test_warm_start_yes_with_behaviour_passes(tmp_path: Path) -> None:
    assert check_service_docs(_repo(tmp_path, {"svc_a": _with(warm_start_md=WARM_YES)})) == ()


def test_warm_start_yes_without_behaviour_fails(tmp_path: Path) -> None:
    warm = "Holds in-memory state: yes\n\nWarm-up behaviour:\n"
    (finding,) = check_service_docs(_repo(tmp_path, {"svc_a": _with(warm_start_md=warm)}))
    assert finding.rule_id == "repo.service_docs.warm_up"


def test_warm_start_yes_accepts_a_heading_section(tmp_path: Path) -> None:
    warm = "Holds in-memory state: yes\n\n## Warm-up behaviour\n\nLoad the model on start.\n"
    assert check_service_docs(_repo(tmp_path, {"svc_a": _with(warm_start_md=warm)})) == ()


def test_cli_subcommand_exit_codes_and_report(tmp_path: Path) -> None:
    ok = _repo(tmp_path / "ok", {"svc_a": GOOD})
    assert main(["service-docs", "--repo-root", str(ok)]) == 0
    bad = _repo(tmp_path / "bad", {"svc_a": _with(runbook_md=None)})
    assert main(["service-docs", "--repo-root", str(bad)]) == 1
    report = json.loads((bad / "evals/reports/service_docs.json").read_text())
    assert report["finding_count"] == 1
    assert main(["service-docs", "--repo-root", str(bad / "nope")]) == 2


def test_no_subcommand_still_runs_the_aggregate(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"svc_a": _with(runbook_md=None)})
    assert main(["--repo-root", str(root)]) == 0
    assert (root / "evals/reports/repo_checks.json").is_file()
