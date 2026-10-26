import ast
from pathlib import Path

import yaml

from tools.common.findings import Finding
from tools.infra_checks.hcl import InfraTree, resolve

BUDGETS_PATH = "config/budgets.yaml"
MODULE = "budget_alerts"
THRESHOLDS = (50, 80, 100)


def check_budgets(root: Path, tree: InfraTree) -> tuple[Finding, ...]:  # noqa: C901, PLR0912, PLR0915
    findings: list[Finding] = []

    config_file = root / BUDGETS_PATH
    if not config_file.is_file():
        findings.append(Finding(BUDGETS_PATH, 0, "infra.budget.config", "missing config"))
        return tuple(findings)

    try:
        with config_file.open() as f:
            data = yaml.safe_load(f)
    except Exception:
        data = None

    if not isinstance(data, dict):
        findings.append(Finding(BUDGETS_PATH, 0, "infra.budget.config", "invalid config"))
        return tuple(findings)

    thresholds = data.get("thresholds_percent")
    if not isinstance(thresholds, list) or not all(isinstance(t, (int, float)) for t in thresholds):
        findings.append(
            Finding(BUDGETS_PATH, 0, "infra.budget.thresholds", "thresholds must be numbers")
        )
    else:
        if any(t <= 0 for t in thresholds):
            findings.append(Finding(BUDGETS_PATH, 0, "infra.budget.thresholds", "must be positive"))
        elif thresholds != sorted(thresholds):
            findings.append(
                Finding(BUDGETS_PATH, 0, "infra.budget.thresholds", "must be ascending")
            )
        elif len(set(thresholds)) != len(thresholds):
            findings.append(
                Finding(BUDGETS_PATH, 0, "infra.budget.thresholds", "must be strictly ascending")
            )
        elif not all(t in thresholds for t in THRESHOLDS):
            findings.append(
                Finding(BUDGETS_PATH, 0, "infra.budget.thresholds", "must contain 50, 80, 100")
            )

    if data.get("thresholds_tag") != "[TARGET]":
        findings.append(
            Finding(BUDGETS_PATH, 0, "infra.budget.threshold_tag", "tag must be [TARGET]")
        )

    curr = data.get("currency")
    if not isinstance(curr, str) or len(curr) != 3 or not curr.isupper():
        findings.append(
            Finding(BUDGETS_PATH, 0, "infra.budget.currency", "currency must be 3 upper letters")
        )

    env_dict = data.get("environments", {})
    for env_name in ["dev", "stage", "prod-like"]:
        env_data = env_dict.get(env_name, {})
        amt = env_data.get("amount")
        if amt is None or isinstance(amt, bool) or not isinstance(amt, (int, float)) or amt <= 0:
            findings.append(
                Finding(
                    BUDGETS_PATH, 0, "infra.budget.amount", f"{env_name} amount must be positive"
                )
            )
        tag = env_data.get("tag")
        if (
            not isinstance(tag, str)
            or not tag.startswith("[")
            or not tag.endswith("]")
            or tag == "[]"
            or tag == "[GUESS]"
            or tag == "ASSUMPTION"
        ):
            findings.append(
                Finding(BUDGETS_PATH, 0, "infra.budget.amount_tag", f"{env_name} tag invalid")
            )

    mod = tree.modules.get(MODULE)
    if not mod:
        findings.append(Finding(str(root), 0, "infra.budget.module_missing", "module missing"))
    else:
        for var in ["thresholds_percent", "amount", "currency_code"]:
            found = False
            for v in mod.of_kind("variable"):
                if v.name == var:
                    found = True
                    if "default" in v.body:
                        findings.append(
                            Finding(v.file, v.line, "infra.budget.module_default", f"{var} default")
                        )
            if not found:
                findings.append(
                    Finding(mod.directory, 0, "infra.budget.module_variable", f"{var} missing")
                )

        if not mod.resources("google_monitoring_notification_channel"):
            findings.append(Finding(mod.directory, 0, "infra.budget.channel", "no channel"))

        out_found = False
        for o in mod.of_kind("output"):
            if "channel_id" in o.name:
                out_found = True
        if not out_found:
            findings.append(
                Finding(mod.directory, 0, "infra.budget.channel_output", "no channel output")
            )

    for env_name, env_unit in tree.envs.items():
        calls = env_unit.module_calls(MODULE)
        if not calls:
            findings.append(
                Finding(
                    env_unit.directory + "/main.tf",
                    0,
                    "infra.budget.env_call",
                    f"{env_name} misses call",
                )
            )
            continue
        call = calls[0]

        thresh_raw = call.get("thresholds_percent")
        is_literal = False
        thresh_val = None
        if isinstance(thresh_raw, list):
            is_literal = True
            thresh_val = thresh_raw
        elif isinstance(thresh_raw, str) and thresh_raw.strip().startswith("["):
            is_literal = True
            try:
                # Use ast.literal_eval instead of eval to prevent arbitrary code execution
                thresh_val = ast.literal_eval(thresh_raw)
            except Exception:
                thresh_val = []
        elif isinstance(thresh_raw, str) and ("other.yaml" in thresh_raw or "slice(" in thresh_raw):
            findings.append(
                Finding(
                    call.file,
                    call.line,
                    "infra.budget.env_threshold",
                    f"{env_name} does not read budgets.yaml",
                )
            )
            continue
        elif isinstance(thresh_raw, str) and (
            "yamldecode" in thresh_raw or "local.budgets.thresholds_percent" in thresh_raw
        ):
            is_valid = False
            if "yamldecode" in thresh_raw and "budgets.yaml" in thresh_raw:
                is_valid = True
            else:
                for loc in env_unit.of_kind("locals"):
                    b_val = loc.get("budgets")
                    if isinstance(b_val, str) and "yamldecode" in b_val and "budgets.yaml" in b_val:
                        is_valid = True
            if not is_valid:
                findings.append(
                    Finding(
                        call.file,
                        call.line,
                        "infra.budget.env_threshold",
                        f"{env_name} does not read budgets.yaml",
                    )
                )
                continue
            thresh_val = thresholds
        else:
            thresh_val = resolve(env_unit, thresh_raw)

        if (
            thresh_val is None
            or not isinstance(thresh_val, list)
            or set(thresh_val) != set(thresholds if isinstance(thresholds, list) else [])
        ):
            findings.append(
                Finding(
                    call.file,
                    call.line,
                    "infra.budget.env_threshold",
                    f"{env_name} misses threshold 100",
                )
            )
        elif is_literal:
            findings.append(
                Finding(call.file, call.line, "infra.budget.literal", "literal threshold_percent")
            )

        amt_raw = call.get("amount")
        if isinstance(amt_raw, (int, float)) or (
            isinstance(amt_raw, str) and (amt_raw.isdigit() or amt_raw.startswith('"'))
        ):
            findings.append(
                Finding(call.file, call.line, "infra.budget.literal", f"{env_name} literal amount")
            )
        elif (
            isinstance(amt_raw, str)
            and "environments[" in amt_raw
            and "local.environment" not in amt_raw
            and f'"{env_name}"' not in amt_raw
        ):
            findings.append(
                Finding(call.file, call.line, "infra.budget.amount_env", f"{env_name} amount_env")
            )

    for unit in tree.units.values():
        for b in unit.resources("google_billing_budget"):
            rules = b.get("threshold_rules")
            if rules:
                if not isinstance(rules, list):
                    rules = [rules]
                for r in rules:
                    if (
                        isinstance(r, dict)
                        and "threshold_percent" in r
                        and isinstance(r["threshold_percent"], (int, float))
                    ):
                        findings.append(
                            Finding(b.file, b.line, "infra.budget.literal", "literal in infra")
                        )

    return tuple(findings)
