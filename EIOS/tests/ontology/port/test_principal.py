"""Identity and scope come from the server, never from what the caller says (spec 023 FR-006, FR-007)."""

import pytest

from eios.agent_gates.records import Role
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode
from eios.ontology.omcp.port.principal import (
    DEV_UID,
    Principal,
    Workstation,
    entitled_workstations,
    principal_for,
)


def test_workstations_match_the_agent_gate_roles() -> None:
    assert {w.value for w in Workstation} == {r.value for r in Role}


def test_uid_comes_from_the_verified_operator() -> None:
    principal = principal_for("firebase-uid-1", "partner_manager")
    assert principal == Principal(uid="firebase-uid-1", workstation=Workstation.PARTNER_MANAGER)


def test_one_rule_every_verified_operator_may_use_every_workstation() -> None:
    assert entitled_workstations("firebase-uid-1") == frozenset(Workstation)
    for workstation in Workstation:
        assert principal_for("firebase-uid-1", workstation.value).workstation is workstation


def test_dev_without_a_token_gets_the_dev_principal() -> None:
    assert principal_for(None, "executive").uid == DEV_UID


@pytest.mark.parametrize("claimed", ["admin", "compliance_head", "", "AML_INVESTIGATOR ", "../x"])
def test_an_unknown_workstation_is_refused(claimed: str) -> None:
    with pytest.raises(PortError) as err:
        principal_for("uid", claimed)
    assert err.value.error.code is ToolErrorCode.INVALID_ARGUMENTS


def test_the_principal_cannot_be_changed_after_it_is_built() -> None:
    principal = principal_for("uid", "executive")
    with pytest.raises(ValueError):
        principal.workstation = Workstation.AML_INVESTIGATOR  # type: ignore[misc]
