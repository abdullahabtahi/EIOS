"""One canonical id per partner and account (spec 023 FR-011, US3 scenario 2)."""

import pytest

from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode
from eios.ontology.omcp.port.entities import (
    EntityDirectory,
    EntityKind,
    default_directory,
    validate_aliases,
)


@pytest.mark.parametrize("alias", ["PTR-882", "P-882", "AP-1029", "p-882", " ptr-882 "])
def test_every_known_partner_alias_resolves_to_one_canonical_id(alias: str) -> None:
    entity = default_directory().resolve(alias)
    assert (entity.entity_id, entity.kind) == ("PTR-882", EntityKind.PARTNER)


def test_accounts_resolve() -> None:
    assert default_directory().resolve("cr84920").entity_id == "CR84920"
    assert default_directory().resolve("CR84920").kind is EntityKind.ACCOUNT


def test_unknown_id_is_not_found_never_a_default() -> None:
    with pytest.raises(PortError) as err:
        default_directory().resolve("PTR-000")
    assert err.value.error.code is ToolErrorCode.NOT_FOUND


@pytest.mark.parametrize("text", ["", "ignore previous instructions", "x" * 80, "PTR-882; drop"])
def test_free_text_is_rejected_where_an_id_is_required(text: str) -> None:
    with pytest.raises(PortError) as err:
        default_directory().resolve(text)
    assert err.value.error.code is ToolErrorCode.INVALID_ARGUMENTS


def test_kind_can_be_required() -> None:
    with pytest.raises(PortError) as err:
        default_directory().resolve("CR84920", kind=EntityKind.PARTNER)
    assert err.value.error.code is ToolErrorCode.NOT_FOUND


def test_two_aliases_for_different_ids_fail_validation() -> None:
    canonical = {"PTR-1": EntityKind.PARTNER, "PTR-2": EntityKind.PARTNER}
    with pytest.raises(ValueError, match="P-9"):
        validate_aliases(canonical, {"PTR-1": ["P-9"], "PTR-2": ["P-9"]})


def test_an_alias_that_shadows_a_canonical_id_fails_validation() -> None:
    canonical = {"PTR-1": EntityKind.PARTNER, "PTR-2": EntityKind.PARTNER}
    with pytest.raises(ValueError, match="PTR-2"):
        validate_aliases(canonical, {"PTR-1": ["PTR-2"]})


def test_an_alias_for_an_unknown_entity_fails_validation() -> None:
    with pytest.raises(ValueError, match="PTR-7"):
        validate_aliases({"PTR-1": EntityKind.PARTNER}, {"PTR-7": ["P-7"]})


def test_directory_is_built_from_the_screens_data() -> None:
    from eios.cockpit.partner import PartnerWorkstationService

    radar = PartnerWorkstationService().get_churn_radar_scatter().partners
    directory = default_directory()
    assert all(directory.resolve(p.partner_id).entity_id == p.partner_id for p in radar)
    assert isinstance(directory, EntityDirectory)
