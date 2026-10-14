"""The one catalogue: every capability the assistant can be offered, and the port built over it."""

from eios.ontology.omcp.port import aml_tools
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import ToolSpec
from eios.ontology.omcp.port.service import GovernedToolPort, RefusalLog


def all_specs() -> tuple[ToolSpec, ...]:
    return (*aml_tools.TOOLS,)


def build_port(
    read_models: ReadModels | None = None, refusals: RefusalLog | None = None
) -> GovernedToolPort:
    return GovernedToolPort(
        all_specs(), context=read_models or ReadModels.default(), refusals=refusals
    )
