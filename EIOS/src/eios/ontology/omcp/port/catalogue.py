"""The one catalogue: every capability the assistant can be offered, and the port built over it."""

from eios.ontology.omcp.port import (
    aml_tools,
    compliance_tools,
    executive_tools,
    ops_tools,
    partner_tools,
    proposals,
    shared_tools,
)
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import ToolSpec
from eios.ontology.omcp.port.service import GovernedToolPort, RefusalLog


def all_specs() -> tuple[ToolSpec, ...]:
    return (
        *shared_tools.TOOLS,
        *aml_tools.TOOLS,
        *partner_tools.TOOLS,
        *proposals.TOOLS,
        *executive_tools.TOOLS,
        *compliance_tools.TOOLS,
        *ops_tools.TOOLS,
    )


def build_port(
    read_models: ReadModels | None = None, refusals: RefusalLog | None = None
) -> GovernedToolPort:
    models = read_models or ReadModels.default()
    port = GovernedToolPort(all_specs(), context=models, refusals=refusals)
    models.facts.bind(port)  # derived figures resolve their inputs through this same port
    return port
