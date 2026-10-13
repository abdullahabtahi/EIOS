"""Generate the recorded faithfulness corpus (spec 022, T025): faithful and wrong answers across the five
workstations, with the expected outcome known by construction.

Deterministic (seeded). Run `python -m evals.agent.build_corpus`; the output under `evals/recorded/faithfulness/`
is committed so that the suites re-judge stored records (FR-002) and never regenerate them.
"""

import json
import random
from pathlib import Path
from typing import Any

SEED = 2210
OUT = Path(__file__).resolve().parents[1] / "recorded" / "faithfulness"

# Each world: role, entity, the tool result, and claims (field key, words a person would use, kind).
WORLDS: dict[str, dict[str, Any]] = {
    "aml_investigator": {
        "entity": "CR70211",
        "tool": "inspect_aml_entity",
        "result": {
            "entity_id": "CR70211",
            "composite_risk_score": 72,
            "kyc_declared_monthly_income_usd": 1200.0,
            "net_deposit_volume_30d_usd": 36000.0,
            "discrepancy_multiplier": 30.0,
            "syndicate_ring_size": 11,
            "velocity_transfers_count": 9,
            "pending_withdrawal_usd": 18500.0,
        },
        "claims": [
            ("composite_risk_score", "composite risk score", "plain"),
            ("kyc_declared_monthly_income_usd", "declared monthly income", "currency"),
            ("net_deposit_volume_30d_usd", "net deposit volume", "currency"),
            ("discrepancy_multiplier", "discrepancy multiplier", "multiplier"),
            ("syndicate_ring_size", "syndicate ring size", "plain"),
            ("velocity_transfers_count", "velocity", "plain"),
            ("pending_withdrawal_usd", "pending withdrawal", "currency"),
        ],
    },
    "partner_manager": {
        "entity": "PTR-882",
        "tool": "get_partner_signals",
        "result": {
            "partner_id": "PTR-882",
            "churn_hazard_probability": 0.78,
            "realized_volume_30d_usd": 1240000.0,
            "login_decay_pct": -68.0,
            "ftd_decay_pct": -45.0,
            "days_to_intervention_deadline": 14,
            "sub_affiliate_count": 14,
            "historical_drift": {
                "tMinus30d": {"pChurn": 0.22, "valueAtRiskUsd": 272800.0},
                "driftVelocityPct": 254.5,
            },
        },
        "aliases": {"ftd_decay_pct": ["first deposits"]},
        "claims": [
            ("churn_hazard_probability", "churn hazard", "ratio"),
            ("realized_volume_30d_usd", "realized volume", "currency"),
            ("login_decay_pct", "login activity", "pct_negative"),
            ("ftd_decay_pct", "first deposits", "pct_negative"),
            ("days_to_intervention_deadline", "days to the intervention deadline", "plain"),
            ("sub_affiliate_count", "sub affiliate count", "plain"),
        ],
    },
    "executive": {
        "entity": "portfolio",
        "tool": "get_forecast",
        "result": {
            "metric_id": "net_revenue_usd",
            "value": 3820000.0,
            "unit": "USD",
            "forecast": {
                "net_revenue_forecast_usd": 4050000.0,
                "interval_95": [3900000.0, 4200000.0],
            },
            "deltas": {"net_revenue_delta_usd": -1107800.0, "net_revenue_delta_percentage": -29.0},
            "attribution": [
                {"driver": "spread", "share_pct": 62.0},
                {"driver": "volume", "share_pct": 38.0},
            ],
        },
        "claims": [
            ("value", "net revenue", "currency"),
            ("net_revenue_forecast_usd", "net revenue forecast", "currency"),
            ("net_revenue_delta_usd", "net revenue delta", "currency_negative"),
            ("net_revenue_delta_percentage", "net revenue delta", "pct_negative"),
        ],
    },
    "compliance_auditor": {
        "entity": "ledger",
        "tool": "get_ledger_audit_status",
        "result": {
            "entries_count": 1842,
            "head_sequence": 1842,
            "chain_length": 1842,
            "verified": True,
            "last_checkpoint_age_minutes": 7,
        },
        "claims": [
            ("entries_count", "ledger entries", "plain"),
            ("head_sequence", "head sequence", "plain"),
            ("last_checkpoint_age_minutes", "checkpoint age", "minutes"),
        ],
    },
    "data_operations": {
        "entity": "pipeline",
        "tool": "get_data_quality_board",
        "result": {
            "dlq_depth": 3,
            "ingest_p95_ms": 142.0,
            "contract_breaches_24h": 5,
            "freshness_sla_minutes": 15,
            "success_rate_pct": 99.2,
        },
        "claims": [
            ("dlq_depth", "dead letter queue depth", "plain"),
            ("ingest_p95_ms", "ingest p95 latency", "plain"),
            ("contract_breaches_24h", "contract breaches", "plain"),
            ("freshness_sla_minutes", "freshness SLA", "minutes"),
            ("success_rate_pct", "success rate", "pct"),
        ],
    },
}

TEMPLATES: tuple[str, ...] = (
    "The {phrase} is {fig}.",
    "We see {fig} for the {phrase}.",
    "{Phrase} came to {fig} in this view.",
    "Right now the {phrase} stands at {fig}, per the latest check.",
)


def _find(node: Any, key: str) -> float:
    if isinstance(node, dict):
        if key in node and isinstance(node[key], (int, float)):
            return float(node[key])
        for child in node.values():
            found = _find(child, key)
            if found == found:  # not NaN
                return found
    elif isinstance(node, list):
        for child in node:
            found = _find(child, key)
            if found == found:
                return found
    return float("nan")


def _faithful_forms(value: float, kind: str) -> list[str]:
    v = abs(value)
    if kind == "currency":
        forms = [f"${v:,.0f}"]
        if v >= 1e6:
            forms += [f"${v / 1e6:.2f} million", f"about ${v / 1e6:.1f}M"]
        return forms
    if kind == "currency_negative":
        return [f"-${v:,.0f}", f"a decline of ${v:,.0f}"]
    if kind == "ratio":
        return [f"{value * 100:.0f}%", f"{value:.2f}"]
    if kind == "pct":
        return [f"{value:.1f}%"]
    if kind == "pct_negative":
        return [f"{value:.0f}%", f"{v:.0f}% lower"]
    if kind == "multiplier":
        return [f"{value:.1f}x", f"{value:.0f} times"]
    if kind == "minutes":
        return [f"{value:.0f} minutes"]
    return [f"{value:,.0f}"] if value == int(value) else [f"{value}"]


def _wrong_forms(
    value: float, kind: str, others: list[float], rng: random.Random
) -> list[tuple[str, str]]:
    """Wrong renderings: (text, mutation kind). Values colliding with another real fact are dropped."""
    v = abs(value) * (100 if kind == "ratio" else 1)  # ratios are written as percentages
    candidates: list[tuple[float, str]] = [
        (v * 100, "scale_up"),
        (v / 100, "scale_down"),
        (v * 10, "dropped_decimal"),
        (round(v * rng.choice([1.3, 1.6, 2.4]), 2), "off_value"),
    ]
    out: list[tuple[str, str]] = []
    for wrong, name in candidates:
        if any(abs(wrong - o) <= 0.05 * max(abs(o), 1.0) for o in others + [v]):
            continue
        if kind in {"currency", "currency_negative"}:
            out.append((f"${wrong:,.0f}" if wrong >= 1 else f"${wrong:.2f}", name))
        elif kind == "ratio":
            out.append((f"{wrong:.0f}%", name))
        elif kind in {"pct", "pct_negative"}:
            out.append((f"{wrong:.0f}%", name))
        elif kind == "multiplier":
            out.append((f"{wrong:.1f}x", name))
        elif kind == "minutes":
            out.append((f"{wrong:.0f} minutes", name))
        else:
            out.append((f"{wrong:,.0f}" if wrong >= 1 else f"{wrong:.2f}", name))
    return out


def _record(
    role: str,
    world: dict[str, Any],
    case: str,
    answer: str,
    expected: bool,
    how: str,
    calls: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "record_id": f"{case}.0",
        "case_id": case,
        "repeat": 0,
        "runtime": "copilot",
        "session_id": "corpus",
        "turn_index": 1,
        "operator_id": "tok_op_corpus",
        "identity_source": "request_body",
        "role": role,
        "entity_context": {"entity_id": world["entity"]},
        "question": f"Tell me about {world['entity']}",
        "tool_calls": calls,
        "rounds": 1,
        "answer": answer,
        "is_replay_fallback": False,
        "data_origin": "fixture",
        "latency_ms": 1.0,
        "outcome": "completed",
        "eval": {"expected_supported": expected, "kind": how, "aliases": world.get("aliases", {})},
    }


def _calls(world: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": world["tool"],
            "arguments": {"entity_id": world["entity"]},
            "result": world["result"],
        }
    ]


def _sentences(role: str, world: dict[str, Any], rng: random.Random) -> list[dict[str, Any]]:
    claims = world["claims"]
    values = {key: _find(world["result"], key) for key, _, _ in claims}
    records: list[dict[str, Any]] = []
    n = 0

    def add(
        answer: str, expected: bool, how: str, calls: list[dict[str, Any]] | None = None
    ) -> None:
        nonlocal n
        n += 1
        records.append(
            _record(role, world, f"{role}_{n:03d}", answer, expected, how, calls or _calls(world))
        )

    for key, phrase, kind in claims:
        value = values[key]
        others = [x for k, x in values.items() if k != key]
        for form in _faithful_forms(value, kind):
            for template in rng.sample(TEMPLATES, 2):
                add(
                    template.format(phrase=phrase, Phrase=phrase.capitalize(), fig=form),
                    True,
                    "faithful",
                )
        for form, name in _wrong_forms(value, kind, others, rng):
            template = rng.choice(TEMPLATES)
            add(
                template.format(phrase=phrase, Phrase=phrase.capitalize(), fig=form),
                False,
                f"mutant:{name}",
            )
    # field swap: a real value attached to another claim's words
    pairs = [
        (a, b)
        for a in claims
        for b in claims
        if a[0] != b[0] and abs(values[a[0]] - values[b[0]]) > 1e-9
    ]
    for (_, phrase, kind), (key_b, _, kind_b) in rng.sample(pairs, k=min(3, len(pairs))):
        if kind == kind_b or kind in {"plain"} and kind_b in {"plain"}:
            form = _faithful_forms(values[key_b], kind_b)[0]
            add(f"The {phrase} is {form}.", False, "mutant:field_swap")
    # two faithful figures; one faithful and one wrong
    for (k1, p1, t1), (k2, p2, t2) in zip(claims, claims[1:], strict=False):
        f1, f2 = _faithful_forms(values[k1], t1)[0], _faithful_forms(values[k2], t2)[0]
        add(f"The {p1} is {f1} and the {p2} is {f2}.", True, "faithful:compound")
        bad = _wrong_forms(values[k2], t2, [values[k1]], rng)
        if bad:
            add(f"The {p1} is {f1} and the {p2} is {bad[0][0]}.", False, "mutant:compound")
    # no figures, a refusal, and a tool failure
    add(
        f"I looked at {world['entity']} and nothing needs your attention beyond what the dossier shows.",
        True,
        "no_figures",
    )
    add("The data for that is unavailable right now, so I will not give a figure.", True, "refusal")
    failed = [
        {
            "name": world["tool"],
            "arguments": {"entity_id": world["entity"]},
            "result": None,
            "error": "DATA_UNAVAILABLE",
        }
    ]
    first = claims[0]
    add(
        f"The {first[1]} is {_faithful_forms(values[first[0]], first[2])[0]}.",
        False,
        "mutant:figure_after_tool_failure",
        failed,
    )
    return records


def build(seed: int = SEED) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(seed)  # noqa: S311 - seeded so the corpus is reproducible
    return {role: _sentences(role, world, rng) for role, world in WORLDS.items()}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for role, records in build().items():
        (OUT / f"{role}.json").write_text(json.dumps(records, indent=1) + "\n", encoding="utf-8")
        total += len(records)
    print(f"wrote {total} records for {len(WORLDS)} workstations to {OUT}")


if __name__ == "__main__":
    main()
