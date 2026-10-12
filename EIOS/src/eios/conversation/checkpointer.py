"""Durable session thread checkpointer supporting SQLite and Firestore (F018, T019)."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Dict, Optional
from eios.conversation.models import sanitize_for_state_storage

_LOG = logging.getLogger("eios.conversation.checkpointer")


class ThreadCheckpointer:
    """Manages thread state persistence across conversational turns."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_checkpoints (
                    thread_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def save_state(self, thread_id: str, state: Dict[str, Any]) -> None:
        """Sanitizes state against NumPy/Firestore serialization traps and saves to store."""
        sanitized = sanitize_for_state_storage(state)
        payload_str = json.dumps(sanitized)

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO conversation_checkpoints (thread_id, state_json)
                VALUES (?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET state_json = excluded.state_json, updated_at = CURRENT_TIMESTAMP
                """,
                (thread_id, payload_str),
            )

    def get_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves and deserializes state for a thread."""
        cur = self._conn.execute(
            "SELECT state_json FROM conversation_checkpoints WHERE thread_id = ?",
            (thread_id,),
        )
        row = cur.fetchone()
        if row:
            return json.loads(row[0])
        return None
