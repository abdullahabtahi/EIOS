"""The corpus manifest: which documents were acquired, where they came from and how they are described to the index.

`data/corpus/regulatory/manifest.yaml` is the record of provenance; the PDFs themselves are git-ignored and are
re-fetched from `source_url`, with the sha256 checked, by `tools.ingest_regulations`.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field

from eios.common.validation import StrictModel

CORPUS_ROOT = Path(__file__).resolve().parents[3] / "data" / "corpus" / "regulatory"
MANIFEST = CORPUS_ROOT / "manifest.yaml"
ACQUIRED = "acquired"


class CorpusDocument(StrictModel):
    id: str
    title: str
    issuer: str
    jurisdiction: str
    kind: str
    source_url: str
    version_note: str
    pages: int | None = Field(default=None, ge=1)
    sha256: str | None = None
    text_layer: bool = True
    licence_state: str
    status: str
    serves: tuple[str, ...] = ()

    @property
    def raw_path(self) -> Path:
        return CORPUS_ROOT / "raw" / f"{self.id}.pdf"


def load_manifest(path: Path = MANIFEST) -> tuple[CorpusDocument, ...]:
    """Every document the manifest lists, acquired or not."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    keep = CorpusDocument.model_fields.keys()
    return tuple(
        CorpusDocument(**{k: v for k, v in d.items() if k in keep}) for d in raw["documents"]
    )


def acquired(path: Path = MANIFEST) -> tuple[CorpusDocument, ...]:
    return tuple(d for d in load_manifest(path) if d.status == ACQUIRED)
