"""Resolve brief citations and spike ids against the repository."""

from __future__ import annotations

import re
from pathlib import Path

from tools.label_check.rules import LabelRules
from tools.records.index import parse_spike_index
from tools.records.spike import parse_spike

_SPIKE_ID = re.compile(r"\bS-\d+\b")
_SPIKE_FORM = re.compile(r"S-[0-9]{2}")
_SECTION = re.compile(r"§\s?\d|\bsection\s+\d|#[\w-]+", re.IGNORECASE)


class Citations:
    """Cached lookups; ``spike_states`` records the state of every spike id seen."""

    def __init__(self, repo_root: Path, rules: LabelRules) -> None:
        self._root = repo_root
        self._rules = rules
        self._brief = re.compile(re.escape(rules.brief_root) + r"/([\w.-]+)")
        self._index: frozenset[str] | None = None
        self.spike_states: dict[str, str] = {}

    def has_brief_citation(self, text: str) -> bool:
        return self._brief.search(text) is not None

    def brief_problem(self, text: str) -> str | None:
        """None when ``text`` cites an existing brief file with a section reference."""
        match = self._brief.search(text)
        if match is None:
            return f"tag without a citation to {self._rules.brief_root}/<file> and a section"
        name = match.group(1).rstrip(".-")
        if not (self._root / self._rules.brief_root / name).is_file():
            return f"cited brief file {self._rules.brief_root}/{name} does not exist"
        if _SECTION.search(text) is None:
            return f"citation to {self._rules.brief_root}/{name} has no section reference"
        return None

    def spike_problems(self, text: str) -> list[str]:
        ids = list(dict.fromkeys(_SPIKE_ID.findall(text)))
        if not ids:
            return ["tag has no spike id (expected S-NN)"]
        problems = []
        for spike_id in ids:
            if _SPIKE_FORM.fullmatch(spike_id) is None:
                problems.append(f"malformed spike id {spike_id}; expected S-NN")
                continue
            state = self._state(spike_id)
            if state is None:
                problems.append(f"no spike record or index row for {spike_id}")
            else:
                self.spike_states[spike_id] = state
        return problems

    def _state(self, spike_id: str) -> str | None:
        directory = self._root / self._rules.spike_dir
        for path in sorted(directory.glob(f"{spike_id}*.md")):
            record = parse_spike(
                path.read_text(encoding="utf-8"), path.relative_to(self._root).as_posix()
            )
            closed = isinstance(record.state, str) and "closed" in record.state.lower()
            return "closed" if closed else "open"
        return "open" if spike_id in self._index_ids() else None

    def _index_ids(self) -> frozenset[str]:
        if self._index is None:
            path = self._root / self._rules.spike_index
            rows = (
                parse_spike_index(path.read_text(encoding="utf-8"), str(path))
                if path.is_file()
                else ()
            )
            self._index = frozenset(row.spike_id for row in rows)
        return self._index
