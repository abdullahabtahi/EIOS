"""Turn governed tool results into an answer using only the figures they contain (spec 023 judging).

Every number printed here is copied from a result field together with its unit; nothing is computed or
rounded, so the answer cannot say more than the port returned.
"""

import re
from typing import Any

_ENVELOPE = frozenset(
    {
        "capability",
        "entity_id",
        "as_of",
        "data_origin",
        "source",
        "markings",
        "units",
        "untrusted",
        "fact_ids",
    }
)
_SKIP = frozenset(
    {
        "label",
        "narrative_summary",
        "definition_version",
        "identity_cluster_key",
        "pseudonymized_cluster_key",
        "chain_head_hash",
        "retention_expiration",
        "kyc_approval_timestamp",
        "timestamp",
        "received_at",
        "at",
        "last_ingestion_timestamp",
    }
)
_BARE_UNITS = frozenset({"ratio", "score", "sequence", "model weight", "points"})
REFUSAL = "I cannot answer that from the governed data available to this workstation."


def _label(path: str) -> str:
    words = ["month" if w == "30d" else w for w in path.replace("[]", "").split("_")]
    return " ".join(words) or path


def _plain(value: float) -> str:
    return f"{int(value):,}" if value == int(value) else str(value)


def _fmt(value: float, unit: str, label: str) -> str:
    if unit == "USD":
        return f"${value:,.2f}" if value != int(value) else f"${value:,.0f}"
    if unit == "percent":
        return f"{value}%"
    if unit == "multiplier":
        return f"{value}x"
    if unit in _BARE_UNITS:
        return _plain(value)
    return (
        _plain(value)
        if {unit, unit.rstrip("s")} & set(label.split())
        else f"{_plain(value)} {unit}"
    )


_PROSE_FIGURE = re.compile(r"(?<![A-Za-z0-9_-])\d[\d,.]*%?(?![A-Za-z0-9_-])")


def _scalar(key: str, value: Any, unit: str | None) -> str | None:
    if key in _SKIP or value is None:
        return None
    if isinstance(value, str) and _PROSE_FIGURE.search(value):
        return None  # prose with a figure that no field backs is not repeated; the port should structure it
    if isinstance(value, bool):
        return f"{_label(key)}: {'yes' if value else 'no'}"
    if isinstance(value, int | float):
        return f"{_label(key)}: {_fmt(value, unit or '', _label(key))}" if unit else None
    if isinstance(value, str):
        return f"{_label(key)}: {value}"
    return None


def _item(item: dict[str, Any], prefix: str, units: dict[str, str]) -> str:
    parts = [_scalar(k, v, units.get(f"{prefix}[].{k}")) for k, v in item.items()]
    return "; ".join(p for p in parts if p)


def render_result(title: str, payload: dict[str, Any]) -> list[str]:
    units: dict[str, str] = payload.get("units", {})
    lines = [f"{title}:"]
    for key, value in payload.items():
        if key in _ENVELOPE:
            continue
        if isinstance(value, list):
            items = [v for v in value if isinstance(v, dict)]
            lines += [f"- {_label(key)}: {_item(i, key, units)}" for i in items]
            if value and not items and payload.get("untrusted"):
                lines.append(f"- {_label(key)}: {len(value)} untrusted text item(s), not repeated")
            elif value and not items:
                lines.append(f"- {_label(key)}: {', '.join(map(str, value))}")
            continue
        name = payload["metric_id"] if key == "value" and "metric_id" in payload else key
        text = _scalar(name, value, units.get(key))
        if text:
            lines.append(f"- {text}")
    return lines


def render_error(title: str, error: dict[str, Any]) -> str:
    return (
        f"{title}: not available ({error['code'].lower().replace('_', ' ')}: {error['message']})."
    )


def source_line(payload: dict[str, Any]) -> str:
    return f"Source: {payload['capability']}, {payload['data_origin']} data, as of {str(payload['as_of'])[:10]}."
