from collections.abc import Sequence
from typing import Any, Protocol

from langchain_core.tools import BaseTool

from eios.conversation.models import BlackboardState, SpecialistDomain


class BaseSpecialistAgent(Protocol):
    """
    Protocol for domain specialist agents within the LangGraph topology.
    """

    @property
    def domain(self) -> SpecialistDomain:
        """Return the specialist domain string."""
        ...

    @property
    def allowed_tools(self) -> Sequence[BaseTool]:
        """Return the list of permitted OMCP tools for this agent."""
        ...

    def invoke(self, state: BlackboardState) -> dict[str, Any]:
        """
        Execute a reasoning cycle based on the current blackboard state.
        Returns state updates to be applied to the LangGraph Shared State.
        """
        ...
