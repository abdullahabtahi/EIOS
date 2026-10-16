"""The one catalogue: every capability the assistant can be offered, and the port built over it."""

from dataclasses import replace

from eios.ontology.omcp.port import (
    aml_tools,
    compliance_tools,
    executive_tools,
    geo_tools,
    knowledge_tools,
    ops_tools,
    partner_tools,
    proposals,
    shared_tools,
    warm_tools,
)
from eios.ontology.omcp.port.descriptions import DESCRIPTIONS
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import ToolSpec
from eios.ontology.omcp.port.service import GovernedToolPort, RefusalLog


def all_specs() -> tuple[ToolSpec, ...]:
    declared = (
        *shared_tools.TOOLS,
        *aml_tools.TOOLS,
        *partner_tools.TOOLS,
        *proposals.TOOLS,
        *executive_tools.TOOLS,
        *compliance_tools.TOOLS,
        *knowledge_tools.TOOLS,
        *ops_tools.TOOLS,
        *warm_tools.TOOLS,
        *geo_tools.TOOLS,
    )
    return tuple(
        replace(s, description=DESCRIPTIONS.get(s.capability, s.description)) for s in declared
    )


def build_port(
    read_models: ReadModels | None = None, refusals: RefusalLog | None = None
) -> GovernedToolPort:
    models = read_models or ReadModels.default()
    port = GovernedToolPort(all_specs(), context=models, refusals=refusals)
    models.facts.bind(port)  # derived figures resolve their inputs through this same port
    return port
