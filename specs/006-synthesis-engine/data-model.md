# Data Model: Executive Synthesis Engine (F05)

**Feature**: `006-synthesis-engine` | **Date**: 2026-10-06  
**Status**: Completed  
**References**: `specs/006-synthesis-engine/spec.md`, `contracts/omcp-tools.json`, `docs/data_products_and_omcp.md`.

---

## 1. Structural Causal Model & Causal DAG Entities

### `CausalEdge`
Represents a directed causal link between two business metrics in the SCM DAG.
```python
class CausalEdge(BaseModel):
    source_metric: str                  # e.g., "competitor_payout_rate"
    target_metric: str                  # e.g., "partner_churn_rate"
    weight: float                       # Point estimate of structural effect
    ci_lower: float                     # Lower bound of 95% confidence interval
    ci_upper: float                     # Upper bound of 95% confidence interval
    confidence: float                   # Statistical confidence in [0.0, 1.0] (must be >= 0.80)
    rationale: str                      # Economic / business rationale
    is_placebo: bool = False            # True for planted anti-circularity verification edges
```

### `RefutationReport`
Represents the empirical refutation results certifying causal validity under the Causal-Evidence Gate (Principle III).
```python
class RefutationReport(BaseModel):
    edge_id: str
    placebo_p_value: float              # Placebo-treatment p-value (MUST be > 0.05 to pass)
    random_cause_delta_pct: float       # Effect shift after adding random confounder (<= 0.20)
    subset_stability_delta_pct: float   # Effect shift across 80% data subsets (<= 0.20)
    ci_excludes_zero: bool              # True if [ci_lower, ci_upper] does not cover 0.0
    gate_verdict: str                   # "PASS" | "FAIL" | "UNVERIFIED"
    failure_reason: str | None = None
```

### `SCMCacheManifest`
Serialized cache manifest of certified SCM DAG edges, weights, and model metadata.
```python
class SCMCacheManifest(BaseModel):
    model_version: str                  # e.g., "v1.2.0-causal"
    generated_at: datetime
    git_sha: str
    dataset_hash: str
    edges: list[CausalEdge]
    refutations: dict[str, RefutationReport]
    active_edge_count: int
    rejected_placebo_count: int
```

---

## 2. Forecasting & Driver Attribution Entities

### `DriverAttribution`
Additive decomposition of forecast variance strictly summing to $100.0\%$.
```python
class DriverAttribution(BaseModel):
    driver_metric: str                  # e.g., "competitor_payout_rate"
    absolute_impact: float              # Impact in metric units
    percentage: float                   # Percentage contribution (0.0 to 100.0)
    direction: str                      # "POSITIVE" | "NEGATIVE"
```

### `ForecastResult`
Time-series forecast with empirical prediction intervals and driver attribution.
```python
class ForecastResult(BaseModel):
    metric_id: str
    horizon_days: int                   # e.g., 28
    historical_points: list[float]
    forecast_points: list[float]
    point_estimate: float               # Aggregate or end-of-period forecast value
    ci_lower: float                     # 95% prediction interval lower bound
    ci_upper: float                     # 95% prediction interval upper bound
    baseline_mase: float                # Out-of-sample MASE vs seasonal-naive (< 1.0 committed)
    driver_attributions: list[DriverAttribution]
    total_attribution_percentage: float # Must strictly equal 100.0
```

---

## 3. Scenario Simulation Entities

### `ScenarioShockSpec`
Exogenous intervention shock parameters applied to the DAG.
```python
class ScenarioShockSpec(BaseModel):
    scenario_name: str
    shocks: dict[str, float]            # e.g., {"competitor_payout_rate": 0.15}
    duration_days: int = 28
    assumptions: list[str] = Field(default_factory=list)
```

### `MitigationOption`
Ranked strategic defensive action responding to simulated scenario impact.
```python
class MitigationOption(BaseModel):
    action_type: str                    # e.g., "AdjustPartnerTier"
    target_cohort: str                  # e.g., "tier_1_emea_partners"
    estimated_cost_usd: float
    estimated_revenue_recovered_usd: float
    roi_ratio: float                    # revenue_recovered / cost
    confidence: float
```

### `ScenarioSimulationResult`
Propagated downstream impacts and mitigation recommendations.
```python
class ScenarioSimulationResult(BaseModel):
    scenario_name: str
    propagated_deltas: dict[str, float]
    confidence_intervals: dict[str, tuple[float, float]]
    mitigation_options: list[MitigationOption]
    assumptions_applied: list[str]
    execution_time_ms: float
```

---

## 4. Morning Briefing Entities

### `BriefingItem`
An individual insight, risk, or opportunity surfaced in the morning briefing.
```python
class BriefingItem(BaseModel):
    item_id: str
    category: str                       # "INSIGHT" | "RISK" | "OPPORTUNITY"
    title: str
    summary: str
    severity_or_impact: str             # "HIGH" | "MEDIUM" | "LOW"
    metric_citations: list[str]         # Cites metric_id, definition_version, as_of
    follow_up_prompt: str               # Suggested conversational drill-down
```

### `BriefingObject`
Complete daily morning executive briefing.
```python
class BriefingObject(BaseModel):
    briefing_id: str                    # e.g., "BRIEF-2026-10-06"
    briefing_date: str                  # ISO date string (YYYY-MM-DD)
    generated_at: datetime
    insights: list[BriefingItem]        # >= 3 insights
    risks: list[BriefingItem]           # >= 2 risks
    opportunities: list[BriefingItem]   # >= 1 opportunity
    is_cached_replay: bool = False      # True if served from fallback cache
    provenance_tag: str = "[TARGET]"
```

---

## 5. Governed Recommendations & AIPW Logging

### `RecommendationCard`
Human-in-the-loop decision recommendation card.
```python
class RecommendationCard(BaseModel):
    recommendation_id: str
    action_type: str                    # e.g., "ReviewSpreadPricing"
    target_entity_id: str               # e.g., "PARTNER-1029"
    impact_estimate_min: float
    impact_estimate_max: float
    impact_unit: str                    # "USD" | "BPS" | "RATIO"
    pros: list[str]
    cons: list[str]
    confidence: float                   # >= 0.80
    evidence_citations: list[str]       # Entity IDs and metric versions
    propensity_score: float             # e(X) in [0.01, 0.99] logged for AIPW
    causal_context: dict[str, float]    # Covariate vector X logged for AIPW
```

### `AIPWPropensityRecord`
Logged decision intent for offline causal flywheel recalibration.
```python
class AIPWPropensityRecord(BaseModel):
    intent_id: str
    action_type: str
    target_entity_id: str
    propensity_score: float             # e(X)
    covariates: dict[str, float]        # X
    action_taken: int                   # 1 if approved, 0 if rejected/unapproved
    observed_outcome: float | None      # Y logged after observation window
    logged_at: datetime
```
