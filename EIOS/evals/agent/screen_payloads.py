"""Workstation payloads for the agent-versus-screen check (spec 022 FR-026), read from the contract the cockpit serves.

A reference looks like `partner:PTR-882`. Only the partner radar exists as a typed service today; AML and
executive payloads are added as their workstation services become typed (spec 023).
"""

from typing import Any

from eios.cockpit.partner import PartnerWorkstationService


def load_payload(reference: str) -> dict[str, Any]:
    kind, _, entity = reference.partition(":")
    if kind != "partner":
        raise KeyError(f"no workstation payload source for '{reference}'")
    for partner in (
        PartnerWorkstationService().get_churn_radar_scatter().to_contract_dict()["partners"]
    ):
        if partner["partner_id"] == entity:
            return dict(partner)
    raise KeyError(f"'{entity}' is not on the partner radar")
