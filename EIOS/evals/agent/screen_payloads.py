"""Workstation payloads for the agent-versus-screen check (spec 022 FR-026), read from the contract the cockpit serves.

A reference looks like `partner:PTR-882`. The partner radar and the AML dossier are typed services today; executive
payloads are added as that workstation service becomes typed (spec 023).
"""

from typing import Any

from eios.cockpit.partner import PartnerWorkstationService
from eios.dataplane.plane import read_models


def load_payload(reference: str) -> dict[str, Any]:
    kind, _, entity = reference.partition(":")
    if kind == "aml":
        return read_models().aml.get_entity_dossier(entity).to_contract_dict()
    if kind != "partner":
        raise KeyError(f"no workstation payload source for '{reference}'")
    for partner in (
        PartnerWorkstationService().get_churn_radar_scatter().to_contract_dict()["partners"]
    ):
        if partner["partner_id"] == entity:
            return dict(partner)
    raise KeyError(f"'{entity}' is not on the partner radar")
