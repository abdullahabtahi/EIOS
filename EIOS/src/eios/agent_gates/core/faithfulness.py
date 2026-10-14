"""The faithfulness judge: is every figure in an answer backed by a figure a tool returned? (spec 022)

ALGORITHM (research R-2). A deterministic, claim-level check; no model is called.

1. Mask text that is not a claim about the data (`exempt.py`): dates, versions, legal citations, period
   labels, grounded identifiers, structure counts, list markers, and a quoted passage of a regulation that a tool
   result of the turn contains word for word (`quotes.py`). An identifier nothing produced is reported
   as unsupported (`ungrounded_identifier`), so an invented account number cannot hide behind its digits.
2. Extract every remaining figure (`figures.py`): value in base units, unit family, period, the precision it
   states, and the words around it.
3. Flatten every tool result into facts (`facts.py`), each with a unit family and label words.
4. A figure is SUPPORTED only if one fact agrees on all three of
   - value, within the precision the figure states ("about $3.8 million" matches 3,820,000; "$3.9 million"
     does not), capped at 5% of the fact so a coarse figure cannot cover a different number;
   - unit family (a percentage is not a multiplier; hours are not days), and period ("per week" is not
     monthly);
   - label: at least one word near the figure is a word of the fact's field name or alias.
   A figure that matches a fact's value but not its label is `wrong_field`; one whose value is a power of
   ten away from a fact it names is `wrong_scale`; one that restates a relative change is `derived`.
5. Ambiguity fails closed: a bare number matching several facts of different units is `ambiguous`.
6. STRUCTURED MODE: when the record carries bindings (reference answers), each figure is verified by value
   and unit against the fact it is bound to, and any figure without a binding is `unbound` residue.

The verdict for a record is `passed` only if no figure is unsupported. Standard library only; parses under
Python 3.12.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .exempt import find_exempt
from .facts import Fact, flatten_facts
from .figures import Figure, extract_figures
from .quotes import verified_quotes
from .text import DERIVED_WORDS

_COMPATIBLE = {
    "currency": {"currency", "other"},
    "percent": {"percent", "ratio", "other", "count"},
    "bps": {"bps", "other"},
    "multiplier": {"multiplier", "other"},
    "duration": {"duration", "other"},
}
_POWERS = (-6, -3, -2, -1, 1, 2, 3, 6)
_IDENTIFIER = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]*\d{2,}[A-Za-z0-9_-]*\b")


@dataclass(frozen=True)
class FigureVerdict:
    text: str
    start: int
    end: int
    verdict: str  # supported | unsupported | exempt
    reason: str
    matched_fact: str | None = None
    candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class Judgement:
    verdicts: tuple[FigureVerdict, ...]
    counts: Mapping[str, int]
    passed: bool

    def unsupported(self) -> list[FigureVerdict]:
        return [v for v in self.verdicts if v.verdict == "unsupported"]


# ---------------------------------------------------------------------------------------------- matching


def _targets(fig: Figure, fact: Fact) -> list[float]:
    """The fact values a figure may be compared with, after the one allowed rescaling (ratio to percent)."""
    if fig.unit == "percent":
        return [fact.value * 100] if fact.unit == "ratio" else [fact.value]
    return [fact.value]


def _value_matches(fig: Figure, fact: Fact) -> bool:
    for target in _targets(fig, fact):
        tol = min(fig.tolerance, max(0.05 * abs(target), 1e-9)) + 1e-12
        if abs(fig.value - target) <= tol:
            return True
        if fig.directional and abs(abs(fig.value) - abs(target)) <= tol:
            return True
    return False


def _unit_ok(fig: Figure, fact: Fact) -> bool:
    if fig.unit != "none" and fact.unit not in _COMPATIBLE.get(fig.unit, {fact.unit}):
        return False
    return not (
        fig.unit == "duration"
        and fig.duration_unit
        and fact.duration_unit
        and fig.duration_unit != fact.duration_unit
    )


def _overlap(fig: Figure, fact: Fact) -> int:
    return len(set(fig.context) & fact.label_tokens)


def _is_scale_error(fig: Figure, fact: Fact) -> bool:
    for target in {fact.value, *_targets(fig, fact)}:
        if target == 0 or fig.value == 0:
            continue
        ratio = abs(fig.value / target)
        if any(abs(ratio / 10**k - 1) < 0.02 for k in _POWERS):
            return True
    return False


def _verdict(
    fig: Figure, ok: bool, reason: str, fact: Fact | None = None, cands: Sequence[Fact] = ()
) -> FigureVerdict:
    return FigureVerdict(
        text=fig.text,
        start=fig.start,
        end=fig.end,
        verdict="supported" if ok else "unsupported",
        reason=reason,
        matched_fact=fact.path if fact else None,
        candidates=tuple(c.path for c in cands),
    )


def _coverage(fig: Figure, fact: Fact) -> float:
    """How much of a field's name the figure's own clause mentions (1.0 = every word of it)."""
    return _overlap(fig, fact) / max(len(fact.label_tokens), 1)


def _describes_better(fig: Figure, rival: Fact, best: Fact) -> bool:
    """The clause covers more of the rival's name, or equally much but through more of its words."""
    rc, bc = _coverage(fig, rival), _coverage(fig, best)
    return rc > bc or (rc == bc and _overlap(fig, rival) > _overlap(fig, best))


def _labelled(
    fig: Figure, hits: list[Fact], facts: Sequence[Fact], others: Sequence[Figure]
) -> FigureVerdict:
    """Value, unit and label agree for at least one fact; check period, then rival readings.

    Ambiguity fails closed: if the clause describes some OTHER field with a different value better than it
    describes the matched one (it says "net revenue" and the match is the net revenue FORECAST), the figure
    is not supported.
    """
    fitting = [f for f in hits if not (fig.period and f.period and fig.period != f.period)]
    if not fitting:
        return _verdict(fig, False, "wrong_unit", cands=hits)
    best = max(fitting, key=lambda f: (_coverage(fig, f), _overlap(fig, f)))
    rivals = [
        f
        for f in facts
        if not _value_matches(fig, f)
        and _unit_ok(fig, f)
        and _describes_better(fig, f, best)
        and not any(
            _value_matches(o, f) for o in others
        )  # another figure already claims this field
    ]
    if rivals:
        return _verdict(fig, False, "ambiguous", cands=[best, *rivals])
    return _verdict(fig, True, "ok", best, fitting)


def _miss(fig: Figure, facts: Sequence[Fact]) -> FigureVerdict:
    """No fact has this value: say what kind of wrong it is."""
    named = [f for f in facts if _overlap(fig, f) > 0]
    if any(_is_scale_error(fig, f) for f in named):
        return _verdict(fig, False, "wrong_scale", cands=named)
    if DERIVED_WORDS.search(fig.sentence):
        return _verdict(fig, False, "derived", cands=named)
    return _verdict(fig, False, "no_matching_value", cands=named)


def _window_supported(fig: Figure, facts: Sequence[Fact]) -> bool:
    """A look-back window ("30 days") that a field name states (`..._30d_...`) is a stated fact."""
    return (
        fig.unit == "duration"
        and fig.duration_unit == "day"
        and any(int(fig.value) in f.windows for f in facts if fig.value == int(fig.value))
    )


def _judge_figure(
    fig: Figure, facts: Sequence[Fact], others: Sequence[Figure] = ()
) -> FigureVerdict:
    if _window_supported(fig, facts):
        return _verdict(fig, True, "window")
    value_hits = [f for f in facts if _value_matches(fig, f)]
    unit_hits = [f for f in value_hits if _unit_ok(fig, f)]
    label_hits = [f for f in unit_hits if _overlap(fig, f) > 0]
    if label_hits:
        return _labelled(fig, label_hits, facts, [o for o in others if o is not fig])
    if value_hits and not unit_hits:
        return _verdict(fig, False, "wrong_unit", cands=value_hits)
    if unit_hits:
        return _verdict(fig, False, "wrong_field", cands=unit_hits)
    return _miss(fig, facts)


# ---------------------------------------------------------------------------------------------- structured


def _fact_for(ref: Mapping[str, Any], facts: Sequence[Fact]) -> Fact | None:
    index, path = int(ref["tool_call_index"]), str(ref["path"])
    for fact in facts:
        if fact.call_index == index and (
            fact.path == f"{index}.{path}" or fact.path.endswith("." + path)
        ):
            return fact
    return None


def _judge_bound(
    figures: Sequence[Figure], facts: Sequence[Fact], bindings: Sequence[Mapping[str, Any]]
) -> list[FigureVerdict]:
    out: list[FigureVerdict] = []
    for fig in figures:
        bound = next(
            (b for b in bindings if fig.start < b["span"][1] and b["span"][0] < fig.end), None
        )
        if bound is None:
            # A look-back window a field name states ("30-day" for `..._30d_...`) is never bound to a value.
            out.append(
                _verdict(fig, True, "window")
                if _window_supported(fig, facts)
                else _verdict(fig, False, "unbound")
            )
            continue
        fact = _fact_for(bound["fact_ref"], facts)
        ok = fact is not None and _value_matches(fig, fact) and _unit_ok(fig, fact)
        out.append(_verdict(fig, ok, "ok" if ok else "binding_mismatch", fact if ok else None))
    return out


# ---------------------------------------------------------------------------------------------- entry point


def _grounded_identifiers(record: Mapping[str, Any]) -> set[str]:
    """Identifier-shaped tokens that the question, context, tool arguments or tool results contain."""
    parts: list[str] = [str(record.get("question", "")), str(record.get("entity_context") or "")]
    for call in record.get("tool_calls", []):
        parts.append(str(call.get("arguments", "")))
        parts.append(str(call.get("result", "")))
    return {m.group(0).lower() for part in parts for m in _IDENTIFIER.finditer(part)}


def judge(
    record: Mapping[str, Any], aliases: Mapping[str, Sequence[str]] | None = None
) -> Judgement:
    """Judge the answer in a Turn Record (its JSON form) against the tool results it received."""
    answer = str(record.get("answer", ""))
    exempt, ungrounded = find_exempt(answer, _grounded_identifiers(record))
    quotes = verified_quotes(answer, record.get("tool_calls", []))
    masked = [(s.start, s.end) for s in exempt + ungrounded] + quotes
    facts = flatten_facts(record.get("tool_calls", []), aliases)
    figures = extract_figures(answer, masked)
    bindings = record.get("bindings")
    judged = (
        _judge_bound(figures, facts, bindings)
        if bindings
        else [_judge_figure(f, facts, figures) for f in figures]
    )
    verdicts = [
        FigureVerdict(s.text, s.start, s.end, "exempt", f"exempt:{s.category}") for s in exempt
    ]
    verdicts += [
        FigureVerdict(answer[a:b].strip(), a, b, "exempt", "exempt:verified_quote")
        for a, b in quotes
    ]
    verdicts += [
        FigureVerdict(s.text, s.start, s.end, "unsupported", "ungrounded_identifier")
        for s in ungrounded
    ]
    verdicts += judged
    verdicts.sort(key=lambda v: v.start)
    counts = Counter(v.verdict for v in verdicts)
    full = {k: counts.get(k, 0) for k in ("supported", "unsupported", "exempt")}
    return Judgement(tuple(verdicts), full, full["unsupported"] == 0)
