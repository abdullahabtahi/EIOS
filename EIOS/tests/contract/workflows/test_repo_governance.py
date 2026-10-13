"""CI hardening: the rulesets, Dependabot and CODEOWNERS files stay in step with the pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from tools.gates.gate_config import load_gates, select_gates

REPO = Path(__file__).resolve().parents[3]
GITHUB = REPO.parent / ".github"
RULESETS = GITHUB / "rulesets"
FRONTEND_CHECK = "frontend-check"
ECOSYSTEMS = {"github-actions", "uv", "npm", "terraform", "docker"}


def _ruleset(name: str) -> dict[str, Any]:
    document = json.loads((RULESETS / f"{name}.json").read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _rule(ruleset: dict[str, Any], rule_type: str) -> dict[str, Any]:
    matches = [r for r in ruleset["rules"] if r["type"] == rule_type]
    assert len(matches) == 1, rule_type
    rule: dict[str, Any] = matches[0]
    return rule


def test_main_ruleset_requires_exactly_the_pr_gates_plus_the_frontend_check() -> None:
    gates = [g.id for g in select_gates(load_gates(REPO / "config" / "gates.yaml"), "pr")]
    checks = _rule(_ruleset("main"), "required_status_checks")["parameters"]
    assert [c["context"] for c in checks["required_status_checks"]] == [*gates, FRONTEND_CHECK]
    assert checks["strict_required_status_checks_policy"] is True


def test_main_ruleset_is_active_has_no_bypass_and_protects_history() -> None:
    ruleset = _ruleset("main")
    assert ruleset["enforcement"] == "active"
    assert ruleset["bypass_actors"] == []
    assert ruleset["conditions"]["ref_name"]["include"] == ["refs/heads/main"]
    for rule_type in ("deletion", "non_fast_forward", "required_linear_history", "pull_request"):
        _rule(ruleset, rule_type)
    pull_request = _rule(ruleset, "pull_request")["parameters"]
    assert pull_request["dismiss_stale_reviews_on_push"] is True
    assert pull_request["required_review_thread_resolution"] is True


def test_release_candidate_tags_are_immutable_and_creatable_only_by_admins() -> None:
    ruleset = _ruleset("rc-tags")
    assert ruleset["target"] == "tag"
    assert ruleset["enforcement"] == "active"
    assert ruleset["conditions"]["ref_name"]["include"] == ["refs/tags/rc-*"]
    for rule_type in ("creation", "update", "deletion", "non_fast_forward"):
        _rule(ruleset, rule_type)
    assert [a["actor_type"] for a in ruleset["bypass_actors"]] == ["RepositoryRole"]


def test_dependabot_covers_every_ecosystem_in_the_repository() -> None:
    document = yaml.safe_load((GITHUB / "dependabot.yml").read_text(encoding="utf-8"))
    assert document["version"] == 2
    assert {u["package-ecosystem"] for u in document["updates"]} == ECOSYSTEMS
    for update in document["updates"]:
        assert update["schedule"]["interval"] == "weekly"
        assert update.get("directory") or update.get("directories")
        assert update["commit-message"]["prefix"] == "chore"


def test_dependabot_directories_exist() -> None:
    document = yaml.safe_load((GITHUB / "dependabot.yml").read_text(encoding="utf-8"))
    for update in document["updates"]:
        for directory in update.get("directories") or [update["directory"]]:
            assert (REPO.parent / directory.lstrip("/")).is_dir(), directory


def test_codeowners_guard_the_pipeline_identity_and_gate_definitions() -> None:
    lines = (GITHUB / "CODEOWNERS").read_text(encoding="utf-8").splitlines()
    owned = {line.split()[0] for line in lines if line.strip() and not line.startswith("#")}
    assert {"/.github/", "/EIOS/infra/", "/EIOS/config/", "/EIOS/tools/gates/"} <= owned


def test_codeql_scans_python_and_typescript_on_pull_requests_and_a_schedule() -> None:
    document = yaml.safe_load((GITHUB / "workflows" / "codeql.yml").read_text(encoding="utf-8"))
    triggers = document["on"] if "on" in document else document[True]
    assert {"pull_request", "push", "schedule"} <= set(triggers)
    job = document["jobs"]["analyze"]
    assert job["permissions"]["security-events"] == "write"
    languages = {entry["language"] for entry in job["strategy"]["matrix"]["include"]}
    assert languages == {"python", "javascript-typescript"}
