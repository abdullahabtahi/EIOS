"""The shelf is served on its own, always fresh, so a workstation's panels can be cached without caching the shelf."""

from collections import Counter
from typing import Any

import pytest
from fastapi.testclient import TestClient

from eios.cockpit import server

ROLES = [
    "executive",
    "aml_investigator",
    "partner_manager",
    "compliance_auditor",
    "data_operations",
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(server.app)


def test_the_shelf_endpoint_returns_the_shelf_and_is_never_cacheable(client: TestClient) -> None:
    res = client.get("/api/cockpit/shelf")
    assert res.status_code == 200
    shelf = res.json()["governed_action_shelf"]
    assert shelf["staged_count"] == len(shelf["actions"])
    assert res.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("role", ROLES)
def test_shelf_false_leaves_the_shelf_out_and_the_rest_unchanged(
    client: TestClient, role: str
) -> None:
    full = client.get(f"/api/cockpit/workstations/{role}").json()
    lean = client.get(f"/api/cockpit/workstations/{role}?shelf=false").json()
    assert "governed_action_shelf" in full
    assert (
        "governed_action_shelf" not in lean
    )  # absent, never an empty shelf that reads as "nothing staged"
    assert set(lean) == set(full) - {"governed_action_shelf"}
    assert [i["id"] for i in lean["triage_queue"]["items"]] == [
        i["id"] for i in full["triage_queue"]["items"]
    ]
    assert lean["active_dossier"]["headline"] == full["active_dossier"]["headline"]
    assert lean["kinetic_canvas"]["canvas_type"] == full["kinetic_canvas"]["canvas_type"]


def test_shelf_false_does_not_list_the_intents_for_a_non_compliance_role(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    counts: Counter[str] = Counter()
    original: Any = server.action_shelf.list_cards_with_tokens

    def counted() -> Any:
        counts["listings"] += 1
        return original()

    monkeypatch.setattr(server.action_shelf, "list_cards_with_tokens", counted)
    client.get("/api/cockpit/workstations/executive?shelf=false")
    assert counts["listings"] == 0
    client.get("/api/cockpit/workstations/executive")
    assert counts["listings"] == 1
