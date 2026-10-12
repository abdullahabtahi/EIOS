"""Data models for the EIOS Evaluation Harness (F04)."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Tier(StrEnum):
    DEV = "dev"
    CONTRACT = "contract"
    EVAL_SMOKE = "eval_smoke"
    RED_LINE = "red_line"
    VALIDATION = "validation"
    SEALED = "sealed"


class RedLineID(StrEnum):
    RL_1 = "RL-1"
    RL_2 = "RL-2"
    RL_3 = "RL-3"
    RL_4 = "RL-4"
    RL_5 = "RL-5"
    RL_6 = "RL-6"
    RL_7 = "RL-7"


class MetricConfidenceInterval(BaseModel):
    lower: float = Field(description="2.5th percentile of bootstrap distribution")
    median: float = Field(description="50th percentile of bootstrap distribution")
    upper: float = Field(description="97.5th percentile of bootstrap distribution")
    confidence_level: float = 0.95


class RedLineResult(BaseModel):
    test_id: RedLineID
    name: str
    passed: bool
    total_evaluated: int
    violations_detected: int = 0
    tolerance: int = 0
    violation_samples: list[dict[str, Any]] = Field(default_factory=list)
    execution_time_ms: float = 0.0


class BaselineComparison(BaseModel):
    module: str = Field(description="Target capability (Module A, B, C, Synthesis)")
    metric_name: str = Field(description="Name of evaluated metric (PR-AUC, FPR, Lead Time, MASE)")
    baseline_method: str = Field(description="Name of naive baseline (e.g. Static Rule)")
    candidate_model: str = Field(description="Name of evaluated model (e.g. LightGBM)")
    baseline_value: float = Field(description="Baseline performance score")
    candidate_value: float = Field(description="Candidate model performance score")
    absolute_delta: float = Field(description="Candidate - Baseline")
    relative_lift_pct: float = Field(description="((Candidate - Baseline) / Baseline) * 100")
    pre_registered_target: str = Field(
        description="Target delta commitment from docs/models_and_evals.md"
    )
    target_met: bool = Field(description="True if delta meets or exceeds commitment")
    confidence_interval: MetricConfidenceInterval | None = None


class SeedManifest(BaseModel):
    tier: Tier
    seeds: list[int] = Field(description="List of integer seeds used for generation")
    git_sha: str = Field(description="Git commit SHA of the evaluated codebase")
    dataset_hash: str = Field(description="SHA-256 hash of the evaluation dataset files")
    spec_version: str = Field(default="1.0.0")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExpectedToolCall(BaseModel):
    tool_name: str
    required_arguments: dict[str, Any] = Field(default_factory=dict)
    order_index: int = 0


class GoldenDialogueTurn(BaseModel):
    turn_index: int
    user_query: str
    expected_route: str = Field(
        description="Expected specialist agent ID (e.g. SentinelAML, Synthesis)"
    )
    expected_tool_calls: list[ExpectedToolCall] = Field(default_factory=list)
    forbidden_tool_calls: list[str] = Field(default_factory=list)
    expected_citations: list[str] = Field(default_factory=list)
    refusal_required: bool = False
    expected_substrings: list[str] = Field(default_factory=list)


class GoldenDialogueScenario(BaseModel):
    scenario_id: str
    domain: str
    description: str
    turns: list[GoldenDialogueTurn]


class EvalReport(BaseModel):
    suite_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    git_sha: str
    tier: Tier
    passed: bool
    summary: str
    seed_manifest: SeedManifest
    red_line_results: list[RedLineResult] = Field(default_factory=list)
    baseline_comparisons: list[BaselineComparison] = Field(default_factory=list)
    dialogue_eval_results: list[dict[str, Any]] = Field(default_factory=list)
    latency_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="p50, p95, and max turn latency in milliseconds",
    )
    hardware_and_cost: dict[str, Any] = Field(
        default_factory=dict,
        description="CPU, memory peak, token count, and estimated cost USD",
    )
