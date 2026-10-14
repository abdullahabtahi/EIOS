"""Load the acquired corpus into the regulatory index: fetch and verify, upload, import.

Fetching and verifying cost nothing and run first. Uploading and importing are the steps that cost (the data store
parses every page with the layout parser), so the command line only plans them unless it is told to execute. Each
document is imported under its manifest id with its jurisdiction, kind and title as metadata, which is what search
filters and citations read back.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eios.knowledge.corpus import CorpusDocument, acquired

_CURL = shutil.which("curl") or "curl"
MANIFEST_OBJECT = "manifest/import.jsonl"
PDF = "application/pdf"


class CorpusIntegrityError(Exception):
    """A downloaded file is not the one the manifest recorded."""


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(doc: CorpusDocument) -> Path:
    """Download a document if it is not on disk yet, then check its checksum against the manifest."""
    path = doc.raw_path
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(  # noqa: S603  # fixed argv, a manifest URL
            [
                _CURL,
                "-sSL",
                "--fail",
                "--max-time",
                "180",
                "-A",
                "Mozilla/5.0",
                "-o",
                str(path),
                doc.source_url,
            ],
            check=True,
        )
    if doc.sha256 and sha256_of(path) != doc.sha256:
        raise CorpusIntegrityError(f"{doc.id}: the file does not match the manifest checksum")
    return path


def object_name(doc: CorpusDocument) -> str:
    return f"corpus/{doc.id}.pdf"


def import_line(doc: CorpusDocument, bucket: str) -> dict[str, Any]:
    """One JSONL row of the import file: the document id, its metadata and where its file is."""
    return {
        "id": doc.id,
        "structData": {
            "document_id": doc.id,
            "title": doc.title,
            "jurisdiction": doc.jurisdiction,
            "kind": doc.kind,
            "issuer": doc.issuer,
            "version_note": doc.version_note,
        },
        "content": {"mimeType": PDF, "uri": f"gs://{bucket}/{object_name(doc)}"},
    }


def import_file(docs: Iterable[CorpusDocument], bucket: str) -> str:
    return "\n".join(json.dumps(import_line(d, bucket), sort_keys=True) for d in docs) + "\n"


@dataclass(frozen=True)
class Plan:
    documents: tuple[CorpusDocument, ...]
    bucket: str
    data_store: str

    @property
    def pages(self) -> int:
        return sum(d.pages or 0 for d in self.documents)

    def describe(self) -> str:
        rows = "\n".join(
            f"  {d.id:<22} {d.jurisdiction:<5} {d.pages or '?':>4} pages  {d.title}"
            for d in self.documents
        )
        return f"{len(self.documents)} documents, {self.pages} pages, to gs://{self.bucket}/ and data store {self.data_store}\n{rows}"


def plan(bucket: str, data_store: str) -> Plan:
    return Plan(acquired(), bucket, data_store)


def upload(p: Plan) -> None:
    from google.cloud.storage import Client

    bucket = Client().bucket(p.bucket)
    for doc in p.documents:
        bucket.blob(object_name(doc)).upload_from_filename(str(fetch(doc)), content_type=PDF)
    bucket.blob(MANIFEST_OBJECT).upload_from_string(
        import_file(p.documents, p.bucket), content_type="application/jsonl"
    )


def start_import(p: Plan, project: str) -> str:
    """Start the import of the uploaded files. Returns the long-running operation's name; it finishes on the service."""
    from google.cloud import discoveryengine_v1 as de

    client = de.DocumentServiceClient()
    parent = client.branch_path(project, "global", p.data_store, "default_branch")
    request = de.ImportDocumentsRequest(
        parent=parent,
        gcs_source=de.GcsSource(
            input_uris=[f"gs://{p.bucket}/{MANIFEST_OBJECT}"], data_schema="document"
        ),
        reconciliation_mode=de.ImportDocumentsRequest.ReconciliationMode.FULL,
    )
    return str(client.import_documents(request=request).operation.name)
