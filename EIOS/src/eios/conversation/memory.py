"""Session memory manager and pronominal reference resolver (F018, T018)."""

from __future__ import annotations

import re
from typing import Any

from eios.conversation.models import EvidenceItem


class SessionMemoryManager:
    """Maintains active entity anchors and resolves pronominal references across conversation turns."""

    def __init__(self, session_id: str = "sess_default", max_tokens: int = 4000) -> None:
        self.session_id = session_id
        self.max_tokens = max_tokens
        self._active_anchor: str | None = None
        self._entity_history: list[str] = []
        self._turn_history: list[dict[str, str]] = []

    def register_turn_entities(
        self,
        turn_index: int,
        query: str,
        extracted_entities: dict[str, str],
    ) -> None:
        """Records entities extracted from an inquiry turn, updating the active anchor."""
        for _key, entity_id in extracted_entities.items():
            if entity_id:
                clean_id = entity_id.strip()
                self._active_anchor = clean_id
                if clean_id not in self._entity_history:
                    self._entity_history.append(clean_id)

        # Regex scan for standard identifiers if not in dictionary
        match = re.search(r"\b([A-Za-z]{1,4}[-_]?\d{3,8})\b", query)
        if match:
            clean_id = match.group(1).upper()
            self._active_anchor = clean_id
            if clean_id not in self._entity_history:
                self._entity_history.append(clean_id)

        self._turn_history.append({"turn": str(turn_index), "query": query})

    def get_active_entity_anchor(self) -> str | None:
        """Returns the most recent active entity anchor in session memory."""
        return self._active_anchor

    def resolve_pronominal_references(self, query: str) -> str:
        """Substitutes ambiguous pronouns with the active entity anchor."""
        if not self._active_anchor:
            return query

        anchor = self._active_anchor
        resolved = query

        # Replace 'his' -> '<ANCHOR>'s'
        resolved = re.sub(r"\bhis\b", f"{anchor}'s", resolved, flags=re.IGNORECASE)
        # Replace 'he' -> '<ANCHOR>'
        resolved = re.sub(r"\bhe\b", anchor, resolved, flags=re.IGNORECASE)
        # Replace 'him' -> '<ANCHOR>'
        resolved = re.sub(r"\bhim\b", anchor, resolved, flags=re.IGNORECASE)

        # Replace 'for them' -> 'for <ANCHOR>'
        resolved = re.sub(r"\bfor\s+them\b", f"for {anchor}", resolved, flags=re.IGNORECASE)
        # Replace 'their' -> '<ANCHOR>'s'
        resolved = re.sub(r"\btheir\b", f"{anchor}'s", resolved, flags=re.IGNORECASE)
        # Replace 'them' -> '<ANCHOR>'
        resolved = re.sub(r"\bthem\b", f"{anchor}", resolved, flags=re.IGNORECASE)
        # Replace 'this entity/partner/account'
        resolved = re.sub(
            r"\bthis\s+(?:account|entity|partner|user|trader)\b",
            anchor,
            resolved,
            flags=re.IGNORECASE,
        )

        return resolved

    def resolve_pronominal_entities(self, query: str, anchors: dict[str, str] | None = None) -> str:
        """Resolves pronominal references using provided anchors."""
        if not anchors:
            return query

        # Find primary entity anchor
        chosen_anchor = None
        for key in ["client", "partner", "account", "user", "entity"]:
            if key in anchors and anchors[key]:
                chosen_anchor = anchors[key]
                break
        if not chosen_anchor:
            for v in anchors.values():
                if v:
                    chosen_anchor = v
                    break

        if not chosen_anchor:
            return query

        prev_anchor = self._active_anchor
        self._active_anchor = chosen_anchor
        try:
            return self.resolve_pronominal_references(query)
        finally:
            self._active_anchor = prev_anchor

    def compact_context(self, messages: list[Any], max_tokens: int | None = None) -> list[Any]:
        """Returns compacted message history preserving system message and recent window within token limits."""
        limit = max_tokens or self.max_tokens
        if not messages:
            return []

        # Check if first message is a SystemMessage
        system_msg = None
        other_messages = messages
        if (
            messages
            and hasattr(messages[0], "content")
            and type(messages[0]).__name__ == "SystemMessage"
        ):
            system_msg = messages[0]
            other_messages = messages[1:]

        system_tokens = (len(str(system_msg.content)) // 4) if system_msg else 0
        available_tokens = max(10, limit - system_tokens)

        # Take from recent to oldest
        retained: list[Any] = []
        current_tokens = 0
        for msg in reversed(other_messages):
            msg_tok = len(str(getattr(msg, "content", ""))) // 4
            if current_tokens + msg_tok <= available_tokens or not retained:
                retained.append(msg)
                current_tokens += msg_tok
            else:
                break

        retained.reverse()
        if system_msg:
            return [system_msg] + retained
        return retained

    def merge_evidence(
        self,
        existing: list[EvidenceItem],
        new_items: list[EvidenceItem],
    ) -> list[EvidenceItem]:
        """Merges evidence collections deduplicating by (tool_name, metric_name)."""
        seen: set[tuple[str, str]] = set()
        result: list[EvidenceItem] = []

        for item in existing:
            key = (item.tool_name, item.metric_name)
            if key not in seen:
                seen.add(key)
                result.append(item)

        for item in new_items:
            key = (item.tool_name, item.metric_name)
            if key not in seen:
                seen.add(key)
                result.append(item)

        return result


ConversationMemoryManager = SessionMemoryManager
