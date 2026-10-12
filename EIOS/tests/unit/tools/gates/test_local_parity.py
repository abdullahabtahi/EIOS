"""T029 (FR-003, FR-004): the pipeline and `make check` run the same gates in the same order."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from tools.gates.gate_config import load_gates, select_gates
from tools.gates.local import local_gate_ids

REPO = Path(__file__).resolve().parents[4]
WORKFLOW = REPO / ".github" / "workflows" / "pr.yml"
RUN_GATE = re.compile(r"^uv run python -m tools\.gates\.run_gate \$\{\{ matrix\.gate \}\}$")


def _workflow() -> dict[Any, Any]:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _steps() -> list[dict[str, Any]]:
    """Steps of the `gate` job only; the per-environment plan job has its own tests below."""
    steps = _gate_job()["steps"]
    assert isinstance(steps, list)
    return steps


def _gate_job() -> dict[str, Any]:
    jobs = _workflow()["jobs"]
    assert "gate" in jobs, "one matrix job named by gate id gives one status check per gate"
    job = jobs["gate"]
    assert isinstance(job, dict)
    return job


def _plan_job() -> dict[str, Any]:
    job = _workflow()["jobs"]["plan"]
    assert isinstance(job, dict)
    return job


def _workflow_gate_ids() -> list[str]:
    matrix = _gate_job()["strategy"]["matrix"]["gate"]
    assert isinstance(matrix, list)
    return [str(gate) for gate in matrix]


def _config_pr_ids() -> list[str]:
    return [g.id for g in select_gates(load_gates(REPO / "config" / "gates.yaml"), "pr")]


def test_workflow_gate_ids_equal_the_pr_stage_ids_in_config_order() -> None:
    assert _workflow_gate_ids() == _config_pr_ids()


def test_the_local_entry_point_runs_the_same_ordered_list() -> None:
    assert list(local_gate_ids()) == _config_pr_ids()


def test_the_pr_stage_is_not_empty() -> None:
    assert len(_config_pr_ids()) >= 9


def test_the_makefile_check_target_calls_the_local_entry_point() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "uv run python -m tools.gates.local" in makefile


def test_workflow_permissions_are_read_only_and_there_are_no_cloud_credentials() -> None:
    document = _workflow()
    assert document["permissions"] == {"contents": "read"}
    assert "permissions" not in _gate_job(), "gate jobs inherit read-only contents"
    assert "id-token" not in yaml.safe_dump(_gate_job())
    assert "secrets." not in WORKFLOW.read_text(encoding="utf-8")


def test_workflow_installs_with_a_frozen_lockfile_and_uploads_reports_always() -> None:
    steps = _steps()
    assert any(s.get("run") == "uv sync --frozen" for s in steps)
    uploads = [s for s in steps if str(s.get("uses", "")).startswith("actions/upload-artifact")]
    assert len(uploads) == 1
    assert uploads[0]["with"]["path"] == "evals/reports/"
    assert "matrix.gate" in uploads[0]["with"]["name"]
    assert "always()" in str(uploads[0]["if"])


def test_actions_use_major_version_tags_with_the_pin_spike_comment() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    uses = [ln for ln in text.splitlines() if "uses:" in ln]
    assert len(uses) >= 5
    for line in uses:
        assert re.search(r"@v\d+\b", line), line
        assert "[SPIKE] pin to commit SHA when CI first runs" in line


def test_each_gate_is_its_own_required_status_check() -> None:
    job = _gate_job()
    assert job["name"] == "${{ matrix.gate }}"
    assert job["strategy"]["fail-fast"] is False
    runs = [str(s["run"]) for s in _steps() if "run_gate" in str(s.get("run", ""))]
    assert len(runs) == 1
    assert RUN_GATE.fullmatch(runs[0].strip())


def test_the_iac_toolchain_is_installed_and_tflint_is_required_in_ci() -> None:
    uses = [str(s.get("uses", "")) for s in _steps()]
    assert any(u.startswith("hashicorp/setup-terraform") for u in uses)
    assert any(u.startswith("terraform-linters/setup-tflint") for u in uses)
    assert "EIOS_REQUIRE_TFLINT" in WORKFLOW.read_text(encoding="utf-8")


# --- plan-only job per environment (T093) --------------------------------------------------

ENVIRONMENTS = ["dev", "stage", "prod-like"]


def _plan_commands() -> list[str]:
    return [str(s["run"]) for s in _plan_job()["steps"] if "run" in s]


def test_there_is_one_plan_job_instance_per_environment() -> None:
    job = _plan_job()
    assert job["strategy"]["matrix"]["environment"] == ENVIRONMENTS
    assert job["strategy"]["fail-fast"] is False
    assert job["name"] == "plan-${{ matrix.environment }}"


def test_the_plan_job_plans_but_never_applies() -> None:
    commands = _plan_commands()
    plans = [c for c in commands if "terraform" in c and " plan " in f" {c} "]
    assert len(plans) == 1
    assert "infra/envs/${{ matrix.environment }}" in plans[0]
    assert "-lock=false" in plans[0], "the read-only identity cannot take the state lock"
    assert not any(re.search(r"\b(apply|destroy|import)\b", c) for c in commands)
    assert "terraform apply" not in WORKFLOW.read_text(encoding="utf-8")


def test_the_plan_job_uses_a_read_only_federated_identity() -> None:
    job = _plan_job()
    assert job["permissions"] == {"contents": "read", "id-token": "write"}
    auth = [s for s in job["steps"] if str(s.get("uses", "")).startswith("google-github-actions/")]
    assert len(auth) == 1
    with_ = auth[0]["with"]
    assert str(with_["workload_identity_provider"]).startswith("${{ vars.")
    assert "PLAN" in str(with_["service_account"]), "a plan identity, not a deploy identity"
    assert "secrets." not in yaml.safe_dump(job)


def test_the_plan_job_skips_pull_requests_from_forks() -> None:
    assert "github.event.pull_request.head.repo.full_name" in str(_plan_job()["if"])
