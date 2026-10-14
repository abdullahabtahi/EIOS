"""Baseline and release reports (spec 022 FR-018, FR-027): measured values only, failures with evidence.

A report is built from per-case results and is comparable with an earlier one. A value that was not measured
is None in the data and "not measured" in the text; nothing is estimated or defaulted.
"""

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


def _p95(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def latency_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """p95 over every turn that ran, one value per turn, a timeout counted at the time it took.

    The report's own p95 is per judged case (first repeat, completed turns only), so a turn that hit the deadline
    drops out of it. This one cannot hide a timeout. A turn that never started (a capability gap) is not a turn.
    """
    ran = [r for r in records if r.get("outcome") == "completed" or _timed_out(r)]
    return {
        "p95_ms": _p95([float(r["latency_ms"]) for r in ran]),
        "turns": len(ran),
        "timed_out": sum(1 for r in ran if _timed_out(r)),
    }


def _timed_out(record: Mapping[str, Any]) -> bool:
    return record.get("outcome") == "inconclusive" and str(
        record.get("inconclusive_reason") or ""
    ).startswith("deadline")


def _share(results: Sequence[Mapping[str, Any]], key: str, value: str) -> float | None:
    seen = [r for r in results if r.get(key) is not None]
    return sum(1 for r in seen if r[key] == value) / len(seen) if seen else None


def _rate(results: Sequence[Mapping[str, Any]]) -> float | None:
    total = sum(int(r.get("figures_total") or 0) for r in results)
    return sum(int(r.get("figures_supported") or 0) for r in results) / total if total else None


def build_report(
    runtime: str, results: Sequence[Mapping[str, Any]], meta: Mapping[str, Any]
) -> dict[str, Any]:
    counts = Counter(str(r["verdict"]) for r in results)
    counts = Counter(
        {"pass": counts["pass"], "fail": counts["fail"], "inconclusive": counts["inconclusive"]}
    )
    by_ws: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for r in results:
        by_ws[str(r.get("workstation", "unknown"))].append(r)
    costs = [float(r["cost_usd"]) for r in results if r.get("cost_usd") is not None]
    return {
        "runtime": runtime,
        "meta": dict(meta),
        "counts": dict(counts),
        "gate": {"proven": counts["fail"] == 0 and counts["inconclusive"] == 0 and bool(results)},
        "faithfulness_rate": _rate(results),
        "p95_latency_ms": _p95(
            [float(r["latency_ms"]) for r in results if r.get("latency_ms") is not None]
        ),
        "cost_usd_per_turn": (sum(costs) / len(costs)) if costs else None,
        "share_fixture": _share(results, "data_origin", "fixture"),
        "share_request_body_identity": _share(results, "identity_source", "request_body"),
        "by_workstation": {
            ws: {
                "counts": dict(Counter(str(r["verdict"]) for r in rs)),
                "faithfulness_rate": _rate(rs),
            }
            for ws, rs in sorted(by_ws.items())
        },
        "failures": [
            {"case_id": r["case_id"], "suite": r.get("suite"), "evidence": r.get("evidence", "")}
            for r in results
            if r["verdict"] == "fail"
        ],
        "inconclusive": [
            {"case_id": r["case_id"], "suite": r.get("suite"), "evidence": r.get("evidence", "")}
            for r in results
            if r["verdict"] == "inconclusive"
        ],
        "cases": {f"{r.get('suite')}:{r['case_id']}": str(r["verdict"]) for r in results},
    }


def compare_reports(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, list[str]]:
    """Cases that improved, regressed or stayed the same between two reports."""
    a, b = before["cases"], after["cases"]
    common = sorted(set(a) & set(b))
    return {
        "improved": [c.split(":", 1)[-1] for c in common if a[c] != "pass" and b[c] == "pass"],
        "regressed": [c.split(":", 1)[-1] for c in common if a[c] == "pass" and b[c] != "pass"],
        "unchanged": [c.split(":", 1)[-1] for c in common if a[c] == b[c]],
    }


def _fmt(value: float | None, pattern: str) -> str:
    return "not measured" if value is None else pattern.format(value)


def _latency_all_turns_line(report: Mapping[str, Any]) -> list[str]:
    summary = report.get("latency_all_turns")
    if not summary:
        return []
    return [
        f"- p95 over every turn, timeouts counted: {_fmt(summary['p95_ms'], '{:.0f} ms')} "
        f"({summary['turns']} turns, {summary['timed_out']} timed out)"
    ]


def render_markdown(report: Mapping[str, Any]) -> str:
    c = report["counts"]
    lines = [
        f"# Agent baseline: {report['runtime']}",
        "",
        f"Cases: {c['pass']} pass, {c['fail']} fail, {c['inconclusive']} inconclusive. "
        f"Gate proven: {'yes' if report['gate']['proven'] else 'no'}.",
        "",
        f"- Faithfulness (share of figures supported): {_fmt(report['faithfulness_rate'], '{:.1%}')}",
        f"- p95 turn latency: {_fmt(report['p95_latency_ms'], '{:.0f} ms')}",
        *_latency_all_turns_line(report),
        f"- Cost per turn: {_fmt(report['cost_usd_per_turn'], '${:.4f}')}",
        f"- Turns on fixture data: {_fmt(report['share_fixture'], '{:.0%}')}",
        f"- Turns with identity taken from the request body: {_fmt(report['share_request_body_identity'], '{:.0%}')}",
        "",
        "| Workstation | Pass | Fail | Inconclusive | Faithfulness |",
        "|---|---|---|---|---|",
    ]
    for ws, row in report["by_workstation"].items():
        k = row["counts"]
        lines.append(
            f"| {ws} | {k.get('pass', 0)} | {k.get('fail', 0)} | {k.get('inconclusive', 0)} | "
            f"{_fmt(row['faithfulness_rate'], '{:.0%}')} |"
        )
    for title, key in (
        ("Failures", "failures"),
        ("Inconclusive (never counted as a pass)", "inconclusive"),
    ):
        if report[key]:
            lines += ["", f"## {title}", ""]
            lines += [f"- `{r['suite']}:{r['case_id']}`: {r['evidence']}" for r in report[key]]
    return "\n".join(lines) + "\n"
