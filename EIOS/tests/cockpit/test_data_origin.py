"""Workstation payloads are fixtures today; the contract must say so, never "[LIVE]" (R1)."""

import pytest
from fastapi.testclient import TestClient

from eios.cockpit.server import FIXTURE_DATA_BADGE, app

ROLES = [
    "executive",
    "aml_investigator",
    "partner_manager",
    "compliance_auditor",
    "data_operations",
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("role", ROLES)
def test_workstation_state_declares_its_data_origin(client: TestClient, role: str) -> None:
    body = client.get(f"/api/cockpit/workstations/{role}").json()
    assert body["fallback_state"]["badge_label"] == FIXTURE_DATA_BADGE


def test_fixture_badge_is_not_a_live_claim() -> None:
    assert "LIVE" not in FIXTURE_DATA_BADGE.upper()
    assert "ILLUSTRATIVE" in FIXTURE_DATA_BADGE.upper()


@pytest.mark.parametrize("role", ROLES)
def test_a_fixture_state_is_not_a_cached_fallback(client: TestClient, role: str) -> None:
    """is_active means a replay is being served; fixture data is a different, always-on fact."""
    assert (
        client.get(f"/api/cockpit/workstations/{role}").json()["fallback_state"]["is_active"]
        is False
    )
