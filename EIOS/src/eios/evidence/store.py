"""Where sealed bundles live: write-once, and checked against their own hash every time they are read.

Firestore when `EIOS_PERSISTENCE=firestore` (collection `eios_evidence_bundles`), process memory only in dev and test;
any other environment refuses to start without Firestore (the same rule as the approval state). A bundle is created
once and never updated: sealing the same content twice gives the same id and stores nothing new.
"""

from __future__ import annotations

import functools
import logging
import re
from typing import Any

from eios.evidence.bundle import intact
from eios.ontology.actions.record_store import RecordStore, default_record_store

_LOG = logging.getLogger("eios.evidence.store")
BUNDLE_ID = re.compile(r"^[0-9a-f]{64}$")


class Tampered(RuntimeError):
    """A stored bundle no longer hashes to its id."""


class EvidenceStore:
    def __init__(self, records: RecordStore) -> None:
        self._records = records

    def put(self, bundle: dict[str, Any]) -> str:
        if not intact(bundle):
            raise ValueError("a bundle is stored only as sealed")
        bundle_id = str(bundle["bundle_id"])
        self._records.create(
            bundle_id, bundle
        )  # create-if-absent: the same content is the same bundle
        return bundle_id

    def get(self, bundle_id: str) -> dict[str, Any] | None:
        if not BUNDLE_ID.fullmatch(bundle_id):
            return None
        bundle = self._records.get(bundle_id)
        if bundle is None:
            return None
        if not intact(bundle):
            _LOG.error("evidence bundle %s no longer matches its hash", bundle_id)
            raise Tampered(f"evidence bundle {bundle_id} no longer matches its hash")
        return bundle


@functools.cache
def evidence_store() -> EvidenceStore:
    return EvidenceStore(default_record_store("evidence_bundles"))
