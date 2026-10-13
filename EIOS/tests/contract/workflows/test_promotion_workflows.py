"""T065 (FR-007, FR-008): the promotion workflows' triggers, identities and boundaries."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
# The root .github is the only one GitHub runs; EIOS/.github held stale copies these tests used to read.
WORKFLOWS = REPO.parent / ".github" / "workflows"
STAGE = "promote-stage"
PROD_LIKE = "promote-prod-like"
RELEASE = "release-candidate"
PROMOTION = (STAGE, PROD_LIKE, RELEASE)
ALL_WORKFLOWS = ("pr", *PROMOTION)
PROTECTED_ENVIRONMENT = "prod-like"
STORED_KEY_MARKERS = (
    "secrets.",
    "credentials_json",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "service_account_key",
    "private_key",
)


def _text(name: str) -> str:
    return (WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8")


def _load(name: str) -> dict[Any, Any]:
    document = yaml.safe_load(_text(name))
    assert isinstance(document, dict)
    return document


def _triggers(name: str) -> dict[str, Any]:
    document = _load(name)
    triggers = document["on"] if "on" in document else document[True]  # YAML 1.1 reads `on` as True
    assert isinstance(triggers, dict)
    return {str(key): value for key, value in triggers.items()}


def _jobs(name: str) -> dict[str, dict[str, Any]]:
    jobs = _load(name)["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    steps = job["steps"]
    assert isinstance(steps, list)
    return steps


def _run_commands(name: str) -> list[str]:
    return [
        str(step["run"]) for job in _jobs(name).values() for step in _steps(job) if "run" in step
    ]


def _auth_steps(name: str) -> list[dict[str, Any]]:
    return [
        step
        for job in _jobs(name).values()
        for step in _steps(job)
        if str(step.get("uses", "")).startswith("google-github-actions/auth@")
    ]


# --- triggers (FR-007) --------------------------------------------------------------------


def test_promote_stage_triggers_only_on_push_to_the_main_line() -> None:
    assert _triggers(STAGE) == {"push": {"branches": ["main"]}}


def test_promote_prod_like_is_manual_only() -> None:
    assert set(_triggers(PROD_LIKE)) == {"workflow_dispatch"}


def test_promote_prod_like_is_bound_to_a_protected_environment() -> None:
    jobs = _jobs(PROD_LIKE)
    assert jobs, "the workflow needs at least one job"
    for job in jobs.values():
        environment = job.get("environment")
        name = environment.get("name") if isinstance(environment, dict) else environment
        assert name == PROTECTED_ENVIRONMENT


def test_only_promote_prod_like_uses_the_protected_environment() -> None:
    for name in (RELEASE, "pr"):
        assert all("environment" not in job for job in _jobs(name).values()), name


def test_promote_stage_runs_in_the_unprotected_stage_environment() -> None:
    # The deployer identity is impersonable only under the GitHub environment of the same name
    # (infra/bootstrap/deployers.tf), so a stage job without `environment: stage` cannot
    # authenticate. Stage has no reviewers: it still promotes on every merge to the main line.
    jobs = _jobs(STAGE)
    assert jobs
    for job in jobs.values():
        environment = job.get("environment")
        name = environment.get("name") if isinstance(environment, dict) else environment
        assert name == "stage"


def test_prod_like_approver_comes_from_the_platform_never_from_an_input() -> None:
    dispatch = _triggers(PROD_LIKE)["workflow_dispatch"] or {}  # a bare trigger parses as None
    inputs = dispatch.get("inputs", {})
    assert not any("approver" in str(key).lower() for key in inputs)
    text = _text(PROD_LIKE)
    assert "EIOS_VERIFIED_APPROVER" in text
    assert "/approvals" in text


def test_prod_like_requires_the_rollback_rehearsal_evidence() -> None:
    assert "docs/evidence/sc-009-rollback-rehearsal.md" in _text(PROD_LIKE)


def test_release_candidate_has_its_own_triggers_and_never_runs_on_pull_requests() -> None:
    triggers = set(_triggers(RELEASE))
    assert triggers == {"workflow_dispatch"}
    assert "pull_request" not in triggers


# --- the sealed tier (FR-008) -------------------------------------------------------------


def test_release_candidate_is_the_only_workflow_that_runs_the_sealed_tier() -> None:
    for name in ALL_WORKFLOWS:
        runs_sealed = any(re.search(r"--tier\s+sealed\b", c) for c in _run_commands(name))
        assert runs_sealed is (name == RELEASE), name
        if name != RELEASE:
            assert "sealed" not in _text(name).replace("sealed-seed", ""), name


def test_release_candidate_runs_sealed_under_its_own_workflow_identity_with_an_sbom() -> None:
    commands = "\n".join(_run_commands(RELEASE))
    assert re.search(r"evals\.cli run --tier sealed --workflow release-candidate", commands)
    assert "tools.gates.sbom" in commands
    assert "--sbom-ref" in commands
    assert "tools.gates.promote --workflow release-candidate" in commands


# --- identity: federated, never a stored key ----------------------------------------------


@pytest.mark.parametrize("name", PROMOTION)
def test_promotion_workflows_authenticate_with_federated_identity(name: str) -> None:
    for job in _jobs(name).values():
        assert job["permissions"]["id-token"] == "write"
    auth = _auth_steps(name)
    assert auth, "each promotion workflow authenticates"
    for step in auth:
        with_ = step["with"]
        assert str(with_["workload_identity_provider"]).startswith("${{ vars.")
        assert str(with_["service_account"]).startswith("${{ vars.")


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_no_workflow_holds_a_stored_cloud_key_or_a_secret(name: str) -> None:
    text = _text(name)
    for marker in STORED_KEY_MARKERS:
        assert marker not in text, f"{name}: {marker}"


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_workflow_level_permissions_are_read_only(name: str) -> None:
    permissions = _load(name)["permissions"]
    assert permissions == {"contents": "read"}


def test_the_release_candidate_identity_is_distinct_from_the_promotion_identities() -> None:
    def identities(name: str) -> set[str]:
        return {str(step["with"]["service_account"]) for step in _auth_steps(name)}

    assert identities(RELEASE)
    assert not identities(RELEASE) & (identities(STAGE) | identities(PROD_LIKE))


# --- pull requests never deploy -----------------------------------------------------------


def test_pr_performs_no_deploy_or_apply_or_promotion() -> None:
    forbidden = re.compile(r"\bapply\b|\bdeploy\b|tools\.gates\.promote|--tier\s+validation")
    for command in _run_commands("pr"):
        assert not forbidden.search(command), command
    assert all("environment" not in job for job in _jobs("pr").values())


def test_only_the_promotion_workflows_apply_infrastructure() -> None:
    assert not any("apply" in c for c in _run_commands("pr"))
    assert any("terraform" in c and " apply " in f" {c} " for c in _run_commands(STAGE))


# --- shared hygiene -----------------------------------------------------------------------


PINNED_USES = re.compile(r"uses:\s+[\w./-]+@[0-9a-f]{40}\s+# v\d+(\.\d+)*\s*$")
USES_LINE = re.compile(r"^\s*(-\s+)?uses:")


def _all_workflow_files() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml"))


@pytest.mark.parametrize("path", _all_workflow_files(), ids=lambda p: p.stem)
def test_every_action_is_pinned_to_a_full_commit_sha_with_its_version_comment(path: Path) -> None:
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines() if USES_LINE.match(line)
    ]
    assert lines, path.name
    for line in lines:
        assert PINNED_USES.search(line), f"{path.name}: {line.strip()}"


@pytest.mark.parametrize("name", PROMOTION)
def test_run_steps_never_interpolate_untrusted_expressions(name: str) -> None:
    for command in _run_commands(name):
        for expression in re.findall(r"\$\{\{(.*?)\}\}", command):
            assert expression.strip().startswith(("matrix.", "env.")), (name, expression)


@pytest.mark.parametrize("name", PROMOTION)
def test_every_evals_cli_call_names_the_workflow_it_runs_under(name: str) -> None:
    calls = [c for c in _run_commands(name) if "evals.cli" in c]
    assert calls
    for command in calls:
        assert f"--workflow {name}" in command, command


@pytest.mark.parametrize("name", (STAGE, PROD_LIKE))
def test_promotion_runs_only_non_sealed_tiers(name: str) -> None:
    tiers = {
        tier for command in _run_commands(name) for tier in re.findall(r"--tier\s+(\w+)", command)
    }
    assert "validation" in tiers
    assert "sealed" not in tiers


def test_promote_stage_promotes_after_its_suites_and_installs_frozen() -> None:
    commands = _run_commands(STAGE)
    assert "uv sync --frozen" in commands
    promote_at = next(i for i, c in enumerate(commands) if "tools.gates.promote" in c)
    suites_at = max(i for i, c in enumerate(commands) if "evals.cli" in c)
    assert suites_at < promote_at


# --- preflight and guards -----------------------------------------------------------------


def _step_named(name: str, step_name: str) -> dict[str, Any]:
    matches = [
        step
        for job in _jobs(name).values()
        for step in _steps(job)
        if step.get("name") == step_name
    ]
    assert len(matches) == 1, (name, step_name)
    return matches[0]


@pytest.mark.parametrize("name", (STAGE, RELEASE))
def test_a_missing_cloud_configuration_is_announced_never_a_silent_skip(name: str) -> None:
    for job in _jobs(name).values():
        assert "if" not in job, "a job-level `if` makes an unconfigured pipeline look green"
    preflight = _step_named(name, "preflight")
    assert "::warning" in str(preflight["run"])
    assert "EIOS_CD_ENABLED" in str(preflight["run"]), "strict mode must fail when enabled"
    steps = [s for job in _jobs(name).values() for s in _steps(job)]
    after = steps[steps.index(preflight) + 1 :]
    assert after
    for step in after:
        if step.get("if") == "always()":
            continue
        assert "CD_CONFIGURED" in str(step.get("if", "")), (name, step.get("name"))


def test_prod_like_refuses_a_dispatch_from_any_ref_but_the_main_line() -> None:
    guard = _step_named(PROD_LIKE, "require the main line")
    assert "refs/heads/main" in str(guard["run"])
    steps = [s for job in _jobs(PROD_LIKE).values() for s in _steps(job)]
    assert steps.index(guard) < next(
        i for i, s in enumerate(steps) if "auth@" in str(s.get("uses"))
    )


def test_prod_like_fails_loudly_when_cloud_configuration_is_missing() -> None:
    for job in _jobs(PROD_LIKE).values():
        assert "if" not in job
    assert "preflight" in {str(s.get("name")) for j in _jobs(PROD_LIKE).values() for s in _steps(j)}


def test_release_candidate_tags_must_point_at_the_main_line() -> None:
    guard = _step_named(RELEASE, "require the tagged commit to be on the main line")
    assert "merge-base --is-ancestor" in str(guard["run"])
    checkout = next(
        s for j in _jobs(RELEASE).values() for s in _steps(j) if "checkout@" in str(s.get("uses"))
    )
    assert checkout["with"]["fetch-depth"] == 0


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_checkout_never_persists_credentials(name: str) -> None:
    checkouts = [
        s for j in _jobs(name).values() for s in _steps(j) if "checkout@" in str(s.get("uses"))
    ]
    assert checkouts
    for step in checkouts:
        assert step["with"]["persist-credentials"] is False, name


def test_the_frontend_check_type_checks_and_resolves_peers_strictly() -> None:
    commands = [str(s.get("run", "")) for s in _steps(_jobs("pr")["frontend"])]
    assert "npm ci" in commands, "peer-dependency conflicts must fail the install"
    assert any("tsc --noEmit" in c for c in commands)
    assert not any("legacy-peer-deps" in c for c in commands)


@pytest.mark.parametrize("path", _all_workflow_files(), ids=lambda p: p.stem)
def test_steps_before_checkout_do_not_rely_on_uncreated_job_working_directory(path: Path) -> None:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    for job in document.get("jobs", {}).values():
        job_dir = job.get("defaults", {}).get("run", {}).get("working-directory")
        if not job_dir or job_dir == ".":
            continue
        checkout_seen = False
        for step in job.get("steps", []):
            if "uses" in step and "checkout@" in str(step["uses"]):
                checkout_seen = True
                continue
            if not checkout_seen and "run" in step:
                step_dir = step.get("working-directory")
                assert step_dir == ".", (
                    f"{path.name}: step '{step.get('name')}' runs before checkout with job "
                    f"working-directory '{job_dir}', so it must explicitly set 'working-directory: .'"
                )
