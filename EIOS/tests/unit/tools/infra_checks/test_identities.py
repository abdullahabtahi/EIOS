"""T059: Service Identity rules (one per service, explicit roles, truth flag, impersonation)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from tests.support.infra_tree import (
    RC_IMPERSONATOR,
    env_main,
    good_files,
    identity_rows,
    patched,
    render_identities,
    with_file,
)
from tests.support.repo_builder import build_repo
from tools.common.findings import Finding
from tools.infra_checks.hcl import load_infra
from tools.infra_checks.identities import (
    ServiceIdentity,
    check_identities,
    check_identity_wiring,
    load_identities,
)

Row = dict[str, object]
Edit = Callable[[Row], Row]


def _rules(findings: tuple[Finding, ...]) -> set[str]:
    return {f.rule_id for f in findings}


def _rows_check(tmp_path: Path, rows: list[Row]) -> tuple[Finding, ...]:
    root = build_repo(tmp_path, {"infra/identities.yaml": render_identities(rows)})
    return check_identities(root)


def _edit(service: str, environment: str, change: Edit) -> list[Row]:
    return [
        change(row) if row["service"] == service and row["environment"] == environment else row
        for row in identity_rows()
    ]


def _set(**fields: object) -> Edit:
    def apply(row: Row) -> Row:
        return {**row, **fields}

    return apply


def test_valid_rows_have_no_findings(tmp_path: Path) -> None:
    assert _rows_check(tmp_path, identity_rows()) == ()


def test_load_returns_frozen_identities(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"infra/identities.yaml": render_identities(identity_rows())})
    identities = load_identities(root)
    assert len(identities) == 15
    first = identities[0]
    assert isinstance(first, ServiceIdentity)
    with pytest.raises(AttributeError):
        first.service = "other"  # type: ignore[misc]


def test_missing_file_is_a_finding(tmp_path: Path) -> None:
    findings = check_identities(tmp_path)
    assert _rules(findings) == {"infra.identity.file"}
    assert findings[0].file == "infra/identities.yaml"


@pytest.mark.parametrize(
    "text",
    [
        "identities: [",
        "identities: 3\n",
        "other: []\n",
        "identities:\n  - service: pipeline\n",
        "identities:\n  - {service: pipeline, environment: qa, roles: [], "
        "can_read_eval_truth: false, impersonable_by: []}\n",
    ],
)
def test_malformed_file_is_a_finding(tmp_path: Path, text: str) -> None:
    root = build_repo(tmp_path, {"infra/identities.yaml": text})
    assert _rules(check_identities(root)) == {"infra.identity.file"}


def test_a_shared_identity_row_fails(tmp_path: Path) -> None:
    rows = [*identity_rows(), identity_rows()[0]]
    findings = _rows_check(tmp_path, rows)
    assert _rules(findings) == {"infra.identity.duplicate"}


def test_every_service_needs_a_row_in_every_environment(tmp_path: Path) -> None:
    rows = [r for r in identity_rows() if (r["service"], r["environment"]) != ("pipeline", "stage")]
    findings = _rows_check(tmp_path, rows)
    assert _rules(findings) == {"infra.identity.missing"}
    assert "pipeline" in findings[0].message


def test_extra_services_are_allowed(tmp_path: Path) -> None:
    extra = {**identity_rows()[0], "service": "future_service"}
    assert _rows_check(tmp_path, [*identity_rows(), extra]) == ()


def test_empty_role_list_is_rejected(tmp_path: Path) -> None:
    findings = _rows_check(tmp_path, _edit("skeleton_core", "dev", _set(roles=[])))
    assert _rules(findings) == {"infra.identity.roles_empty"}


@pytest.mark.parametrize("role", ["roles/*", "*", "roles/storage.*", "roles/storage.admin*"])
def test_wildcard_roles_are_rejected(tmp_path: Path, role: str) -> None:
    findings = _rows_check(tmp_path, _edit("skeleton_core", "dev", _set(roles=[role])))
    assert _rules(findings) == {"infra.identity.role_wildcard"}


@pytest.mark.parametrize("role", ["roles/editor", "roles/owner", "roles/viewer"])
def test_project_wide_basic_roles_are_rejected(tmp_path: Path, role: str) -> None:
    findings = _rows_check(tmp_path, _edit("skeleton_core", "dev", _set(roles=[role])))
    assert _rules(findings) == {"infra.identity.role_project_wide"}


@pytest.mark.parametrize("role", ["editor", "roles/", "Roles/run.invoker", "run.invoker", ""])
def test_malformed_role_names_are_rejected(tmp_path: Path, role: str) -> None:
    findings = _rows_check(tmp_path, _edit("skeleton_core", "dev", _set(roles=[role])))
    assert _rules(findings) == {"infra.identity.role_invalid"}


def test_custom_role_names_are_accepted(tmp_path: Path) -> None:
    roles = ["roles/run.invoker", "projects/placeholder/roles/evalReader"]
    assert _rows_check(tmp_path, _edit("skeleton_core", "dev", _set(roles=roles))) == ()


@pytest.mark.parametrize("service", ["skeleton_edge", "skeleton_core", "release_candidate"])
def test_only_harness_and_pipeline_may_read_eval_truth(tmp_path: Path, service: str) -> None:
    findings = _rows_check(tmp_path, _edit(service, "dev", _set(can_read_eval_truth=True)))
    assert _rules(findings) == {"infra.identity.truth_flag"}


def test_harness_and_pipeline_may_read_eval_truth(tmp_path: Path) -> None:
    rows = identity_rows()
    assert all(
        r["can_read_eval_truth"] for r in rows if r["service"] in {"eval_harness", "pipeline"}
    )
    assert _rows_check(tmp_path, rows) == ()


def test_runtime_identity_with_broad_storage_role_can_reach_truth(tmp_path: Path) -> None:
    roles = ["roles/storage.objectViewer"]
    findings = _rows_check(tmp_path, _edit("skeleton_core", "dev", _set(roles=roles)))
    assert _rules(findings) == {"infra.identity.truth_reach"}


def test_harness_may_hold_a_broad_storage_role(tmp_path: Path) -> None:
    roles = ["roles/storage.objectViewer"]
    assert _rows_check(tmp_path, _edit("eval_harness", "dev", _set(roles=roles))) == ()


def test_release_candidate_requires_impersonation_attributes(tmp_path: Path) -> None:
    findings = _rows_check(tmp_path, _edit("release_candidate", "stage", _set(impersonable_by=[])))
    assert _rules(findings) == {"infra.identity.impersonation"}


@pytest.mark.parametrize(
    "entry",
    [
        "release-candidate.yml",
        "workflow=*",
        "workflow=",
        "=release-candidate.yml",
        "workflow=pr.yml",
    ],
)
def test_impersonation_must_be_attribute_restricted_to_the_rc_workflow(
    tmp_path: Path, entry: str
) -> None:
    rows = _edit("release_candidate", "dev", _set(impersonable_by=[entry]))
    assert _rules(_rows_check(tmp_path, rows)) == {"infra.identity.impersonation"}


def test_other_identities_need_no_impersonation(tmp_path: Path) -> None:
    rows = _edit("pipeline", "dev", _set(impersonable_by=[]))
    assert _rows_check(tmp_path, rows) == ()
    assert RC_IMPERSONATOR in str(identity_rows())


def _wiring(tmp_path: Path, files: Mapping[str, str]) -> tuple[Finding, ...]:
    return check_identity_wiring(load_infra(build_repo(tmp_path, dict(files))))


def test_valid_terraform_wiring_has_no_findings(tmp_path: Path) -> None:
    assert _wiring(tmp_path, good_files()) == ()


def test_two_services_on_one_identity_module_are_shared(tmp_path: Path) -> None:
    files = patched(
        good_files(),
        "infra/envs/dev/main.tf",
        "service_account_email = module.identity_skeleton_core.email",
        "service_account_email = module.identity_skeleton_edge.email",
    )
    findings = _wiring(tmp_path, files)
    assert _rules(findings) == {"infra.identity.shared"}
    assert findings[0].file == "infra/envs/dev/main.tf"
    assert findings[0].line > 0


def test_two_identity_modules_for_one_service_are_shared(tmp_path: Path) -> None:
    files = patched(
        good_files(),
        "infra/envs/stage/main.tf",
        'service    = "skeleton_core"',
        'service    = "skeleton_edge"',
    )
    assert _rules(_wiring(tmp_path, files)) == {"infra.identity.shared"}


def test_project_wide_editor_grant_in_terraform_is_rejected(tmp_path: Path) -> None:
    extra = (
        'resource "google_project_iam_member" "grant" {\n'
        '  project = var.project_id\n  role    = "roles/editor"\n'
        "  member  = module.identity_skeleton_edge.member\n}\n"
    )
    files = with_file(good_files(), "infra/envs/dev/main.tf", env_main("dev", extra=extra))
    assert _rules(_wiring(tmp_path, files)) == {"infra.identity.role_project_wide"}


def test_wildcard_role_passed_to_the_identity_module_is_rejected(tmp_path: Path) -> None:
    files = patched(
        good_files(), "infra/envs/dev/main.tf", '["roles/logging.logWriter"]', '["roles/*"]'
    )
    assert "infra.identity.role_wildcard" in _rules(_wiring(tmp_path, files))


def test_roles_taken_from_variables_are_not_judged(tmp_path: Path) -> None:
    files = patched(
        good_files(), "infra/envs/dev/main.tf", '["roles/logging.logWriter"]', "var.roles"
    )
    assert _wiring(tmp_path, files) == ()
