"""Palantir Foundry-Grade Branch-per-Scenario Copy-on-Write Sandbox Engine (F019 Phase 8, T025)."""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class BranchMetadata(BaseModel):
    branch_id: str
    parent_branch_id: str
    scenario_name: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = True
    shock_parameters: dict[str, float] = Field(default_factory=dict)


class ScenarioSandboxEngine:
    """Isolates What-If parametric simulations onto copy-on-write ontology branches.

    Guarantees the canonical live operational graph is never directly mutated by hypothetical queries.
    """

    def __init__(self, canonical_state: dict[str, Any] | None = None) -> None:
        self.canonical_state: dict[str, Any] = canonical_state or {
            "partner_commissions": {"AP-1029": 45.0, "AP-2041": 35.0, "AP-3088": 50.0},
            "broker_spread_bps": {"EURUSD": 1.2, "XAUUSD": 2.5, "BTCUSD": 12.0},
            "active_clients": 12500,
            "aggregate_var_30d_usd": 1041600.0,
        }
        self._branches: dict[str, BranchMetadata] = {
            "main": BranchMetadata(
                branch_id="main",
                parent_branch_id="",
                scenario_name="Canonical Production Graph",
                created_by="SYSTEM",
            )
        }
        # Copy-on-write delta overlays per branch: branch_id -> {key: value}
        self._branch_overlays: dict[str, dict[str, Any]] = {"main": {}}

    def fork_branch(
        self,
        scenario_name: str,
        parent_branch_id: str = "main",
        operator_id: str = "OFFICER_CHENG",
        shock_parameters: dict[str, float] | None = None,
    ) -> BranchMetadata:
        """Forks a new copy-on-write ontology branch without copying full underlying memory."""
        if parent_branch_id not in self._branches:
            raise KeyError(f"Parent branch '{parent_branch_id}' does not exist")

        branch_id = f"br_{scenario_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
        meta = BranchMetadata(
            branch_id=branch_id,
            parent_branch_id=parent_branch_id,
            scenario_name=scenario_name,
            created_by=operator_id,
            shock_parameters=shock_parameters or {},
        )
        self._branches[branch_id] = meta
        self._branch_overlays[branch_id] = copy.deepcopy(self._branch_overlays[parent_branch_id])

        # Apply initial shock parameters to branch overlay
        if shock_parameters:
            for k, v in shock_parameters.items():
                self.mutate_state(branch_id, k, v)

        return meta

    def mutate_state(self, branch_id: str, key: str, value: Any) -> None:
        """Applies mutation to the isolated branch overlay only (never mutates canonical state)."""
        if branch_id == "main":
            raise PermissionError(
                "Direct mutation of canonical 'main' branch is forbidden (Principle II)"
            )
        if branch_id not in self._branch_overlays:
            raise KeyError(f"Branch '{branch_id}' not found")
        self._branch_overlays[branch_id][key] = value

    def read_state(self, branch_id: str, key: str) -> Any:
        """Resolves state by checking branch overlay first, then falling back to canonical state."""
        if branch_id not in self._branches:
            raise KeyError(f"Branch '{branch_id}' not found")

        # 1. Check branch overlay
        if key in self._branch_overlays[branch_id]:
            return self._branch_overlays[branch_id][key]

        # 2. Fallback to canonical state
        return self.canonical_state.get(key)

    def compute_branch_diff(self, branch_id: str) -> dict[str, Any]:
        """Calculates delta between sandbox branch and canonical base."""
        if branch_id not in self._branch_overlays:
            raise KeyError(f"Branch '{branch_id}' not found")

        overlay = self._branch_overlays[branch_id]
        diff: dict[str, Any] = {}
        for k, v in overlay.items():
            base_val = self.canonical_state.get(k)
            diff[k] = {
                "base_value": base_val,
                "sandbox_value": v,
                "delta": round(v - base_val, 4)
                if isinstance(v, (int, float)) and isinstance(base_val, (int, float))
                else "MODIFIED",
            }
        return diff

    def discard_branch(self, branch_id: str) -> None:
        """Tears down an isolated scenario branch."""
        if branch_id == "main":
            raise ValueError("Cannot discard canonical 'main' branch")
        self._branches.pop(branch_id, None)
        self._branch_overlays.pop(branch_id, None)
