"""Synthetic budget wiring on top of the valid synthetic infra tree (T191).

``budget_files()`` returns ``good_files()`` plus ``config/budgets.yaml``, a ``budget_alerts``
module and one ``budget_alerts`` call per environment, all valid. Tests derive faulty trees with
``patched`` / ``with_file``. The amounts are placeholders; nothing here names a real project.
"""

from __future__ import annotations

from collections.abc import Mapping

import yaml

from tests.support.infra_tree import ENVIRONMENTS, good_files

BUDGETS_PATH = "config/budgets.yaml"
MODULE = "infra/modules/budget_alerts"
THRESHOLDS = (50, 80, 100)
AMOUNTS = {"dev": 20, "stage": 50, "prod-like": 100}

BUDGET_LOCALS = """
locals {
  budgets = yamldecode(file("${path.module}/../../../config/budgets.yaml"))
}
"""

DEFAULT_ARGS = {
    "thresholds_percent": "local.budgets.thresholds_percent",
    "amount": "local.budgets.environments[local.environment].amount",
    "currency_code": "local.budgets.currency",
}


def render_budgets(
    *,
    thresholds: object = THRESHOLDS,
    thresholds_tag: str = "[TARGET]",
    amounts: Mapping[str, object] | None = None,
    tags: Mapping[str, object] | None = None,
    currency: object = "USD",
) -> str:
    """A ``config/budgets.yaml`` text; keyword arguments produce faulty variants."""
    chosen = AMOUNTS if amounts is None else amounts
    tag_for = tags or {}
    environments = {
        name: {"amount": amount, "tag": tag_for.get(name, "[ASSUMPTION]")}
        for name, amount in chosen.items()
    }
    return yaml.safe_dump(
        {
            "thresholds_percent": list(thresholds) if isinstance(thresholds, tuple) else thresholds,
            "thresholds_tag": thresholds_tag,
            "currency": currency,
            "environments": environments,
        },
        sort_keys=False,
    )


def module_files(
    *,
    defaults: tuple[str, ...] = (),
    omit_variable: str | None = None,
    channel: bool = True,
    channel_output: bool = True,
) -> dict[str, str]:
    """The ``budget_alerts`` module; variables have no default unless named in ``defaults``."""
    names = (
        "project_id",
        "environment",
        "billing_account",
        "notification_email",
        "thresholds_percent",
        "amount",
        "currency_code",
    )
    variables = ""
    for name in names:
        if name == omit_variable:
            continue
        default = "  default = null\n" if name in defaults else ""
        variables += f'variable "{name}" {{\n  type = any\n{default}}}\n\n'
    main = 'resource "google_billing_budget" "this" {\n  billing_account = var.billing_account\n}\n'
    if channel:
        main += (
            'resource "google_monitoring_notification_channel" "email" {\n'
            '  type         = "email"\n'
            "  display_name = var.environment\n"
            "}\n"
        )
    outputs = 'output "topic_id" {\n  value = "placeholder"\n}\n'
    if channel_output:
        outputs += 'output "notification_channel_id" {\n  value = "placeholder"\n}\n'
    return {
        f"{MODULE}/variables.tf": variables,
        f"{MODULE}/main.tf": main,
        f"{MODULE}/outputs.tf": outputs,
    }


def call_text(overrides: Mapping[str, str] | None = None, *, omit: tuple[str, ...] = ()) -> str:
    """A ``budget_alerts`` module call; ``overrides`` replaces the expression for an argument."""
    args = {**DEFAULT_ARGS, **(overrides or {})}
    lines = [
        '  source             = "../../modules/budget_alerts"',
        "  project_id         = var.project_id",
        "  environment        = local.environment",
        "  billing_account    = var.billing_account",
        "  notification_email = var.notification_email",
    ]
    lines.extend(f"  {key} = {value}" for key, value in args.items() if key not in omit)
    return 'module "budget_alerts" {\n' + "\n".join(lines) + "\n}\n"


def budget_files() -> dict[str, str]:
    """A valid tree with budgets wired into all three environments."""
    files = good_files()
    files[BUDGETS_PATH] = render_budgets()
    files.update(module_files())
    for env in ENVIRONMENTS:
        path = f"infra/envs/{env}/main.tf"
        files[path] = files[path] + BUDGET_LOCALS + call_text()
    return files


def with_call(files: Mapping[str, str], env: str, call: str) -> dict[str, str]:
    """Copy of ``files`` where ``env``'s budget call is replaced by ``call``."""
    path = f"infra/envs/{env}/main.tf"
    text = files[path]
    start = text.index('module "budget_alerts"')
    return {**files, path: text[:start] + call}
