"""Measure how early the churn radar sees planted churn: `PYTHONPATH=src:. python -m evals.partner.lead_time`.

Builds the seeded partner world, scores it at the cut and at 14 and 30 days before it, and prints the radar's ranking
quality and alert volume at each lead. Offline and free. Writes `evals/reports/partner_lead_time.json`.
"""

import json
from dataclasses import asdict
from pathlib import Path

from eios.dataplane.partner_engine import run_partner_engine
from eios.dataplane.partner_lead_time import LeadTimeRow, lead_time_report
from eios.foundry.scenarios.partner_config import PartnerWorldConfig
from eios.foundry.scenarios.partner_world import build_partner_world

REPORT = Path(__file__).resolve().parent.parent / "reports" / "partner_lead_time.json"


def render(rows: tuple[LeadTimeRow, ...]) -> str:
    head = f"{'lead':>5} {'AUC':>6} {'P@k':>6} {'alerts':>7} {'alert P':>8} {'alert R':>8}"
    lines = [head]
    for r in rows:
        precision = "n/a" if r.alert_precision is None else f"{r.alert_precision:.2f}"
        lines.append(
            f"{r.lead_days:>4}d {r.auc:>6.3f} {r.precision_at_k:>6.2f} {r.alerts:>7} {precision:>8} {r.alert_recall:>8.2f}"
        )
    return "\n".join(lines)


def main() -> int:
    rows = lead_time_report(run_partner_engine(build_partner_world(PartnerWorldConfig())))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps([asdict(r) for r in rows], indent=2))
    print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
