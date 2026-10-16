import hashlib
import json
from pathlib import Path

import pytest

from eios.knowledge import ingest
from eios.knowledge.corpus import CorpusDocument, acquired, load_manifest


def doc(**kw: object) -> CorpusDocument:
    base = dict(
        id="MT-X",
        title="A title",
        issuer="Regulator",
        jurisdiction="MT",
        kind="legislation",
        source_url="https://example.invalid/x.pdf",
        version_note="v1",
        pages=10,
        sha256="0" * 64,
        licence_state="accepted_for_prototype",
        status="acquired",
    )
    return CorpusDocument(**{**base, **kw})  # type: ignore[arg-type]


def test_every_import_row_names_the_document_its_metadata_and_its_file() -> None:
    row = ingest.import_line(doc(), "bucket-1")
    assert row["id"] == "MT-X"
    assert row["structData"]["jurisdiction"] == "MT" and row["structData"]["document_id"] == "MT-X"
    assert row["content"] == {"mimeType": "application/pdf", "uri": "gs://bucket-1/corpus/MT-X.pdf"}
    lines = ingest.import_file([doc(), doc(id="LB-Y")], "bucket-1").strip().splitlines()
    assert [json.loads(line)["id"] for line in lines] == ["MT-X", "LB-Y"]


def test_a_file_that_does_not_match_the_manifest_checksum_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "MT-X.pdf"
    path.write_bytes(b"not the recorded file")
    monkeypatch.setattr(CorpusDocument, "raw_path", property(lambda self: path))
    with pytest.raises(ingest.CorpusIntegrityError):
        ingest.fetch(doc())
    path.write_bytes(b"recorded")
    assert ingest.fetch(doc(sha256=hashlib.sha256(b"recorded").hexdigest())) == path


def test_the_plan_counts_pages_and_names_the_target() -> None:
    p = ingest.Plan((doc(pages=3), doc(id="B", pages=4)), "bkt", "store")
    assert p.pages == 7
    assert "2 documents, 7 pages" in p.describe() and "gs://bkt/" in p.describe()


def test_the_real_manifest_loads_and_lists_the_acquired_documents_with_no_unverified_licence() -> (
    None
):
    every = load_manifest()
    assert {d.id for d in acquired()} >= {
        "MT-FIAU-IP1",
        "MT-PMLFTR",
        "LB-KRI-2025",
        "US-FINCEN-NARR-2003",
    }
    assert all(d.licence_state != "unverified" for d in every)
    assert all(d.jurisdiction in {"MT", "LB", "US", "INTL"} for d in every)


def test_ingest_regulations_main_plan_and_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    from tools import ingest_regulations

    dummy_plan = ingest.Plan((doc(pages=1),), "bkt", "store")
    monkeypatch.setattr(ingest, "plan", lambda b, d: dummy_plan)
    monkeypatch.setattr(ingest, "fetch", lambda d: Path("/tmp/dummy"))
    monkeypatch.setattr(ingest, "upload", lambda p: None)

    # Dry-run without execute returns 0
    assert (
        ingest_regulations.main(
            ["--project", "p", "--data-store", "ds", "--bucket", "b"]
        )
        == 0
    )

    # Execute with successful operation returns 0
    monkeypatch.setattr(ingest, "start_import", lambda p, prj: "operations/12345")
    assert (
        ingest_regulations.main(
            ["--project", "p", "--data-store", "ds", "--bucket", "b", "--execute"]
        )
        == 0
    )

    # Execute with empty operation returns 1
    monkeypatch.setattr(ingest, "start_import", lambda p, prj: "")
    assert (
        ingest_regulations.main(
            ["--project", "p", "--data-store", "ds", "--bucket", "b", "--execute"]
        )
        == 1
    )
