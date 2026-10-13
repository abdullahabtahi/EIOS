import re
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool

from eios.conversation.models import SpecialistDomain


class SynthesisSpecialist:
    @property
    def domain(self) -> SpecialistDomain:
        return SpecialistDomain.SYNTHESIS

    @property
    def allowed_tools(self) -> Sequence[BaseTool]:
        # T018: OMCP tools for causal simulation and forecasting
        # Returning mocked tool names as strings or placeholder objects
        # In practice, these would be actual BaseTool instances wrapping OMCP calls.
        return ["run_scenario", "get_forecast"]

    def _detect_counterfactual(self, text: str) -> bool:
        """T017: Detect if the query is a counterfactual / 'What if'."""
        keywords = ["what if", "suppose", "assume", "scenario", "shock"]
        return any(k in text.lower() for k in keywords)

    def _check_extrapolation(self, shock_value: float, std_dev: float = 1.0) -> bool:
        """T019: Check if shock > 3.0 sigma."""
        return abs(shock_value) > (3.0 * std_dev)

    def _extract_shock_value(self, text: str) -> float | None:
        """Extract a numeric shock value from text if it mentions 'sigma'.
        In a full production implementation, this would use a structured Gateway call.
        """
        match = re.search(r"([-+]?\d*\.?\d+)\s*sigma", text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute a reasoning cycle based on the current state."""
        last_msg = state["messages"][-1]
        text = str(last_msg.content)

        content = "Synthesis specialist analysis completed."

        if self._detect_counterfactual(text):
            shock = self._extract_shock_value(text)
            if shock is not None:
                if self._check_extrapolation(shock):
                    content += f" WARNING: The requested shock ({shock}) exceeds 3.0 sigma and may result in unreliable extrapolation."
                else:
                    content += " Executing scenario..."
            else:
                content += " (Counterfactual detected, but no explicit sigma shock value found)."

        return {
            "messages": [AIMessage(content=content)],
            "reflection_cycles": state.get("reflection_cycles", 0) + 1,
            "next_agent": "supervisor",
        }
