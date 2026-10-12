"""Daily Executive Morning Briefing generator with Metric Auditor Gate compliance (US4, FR-014-FR-019)."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eios.ontology.auditor.gate import MetricAuditorGate
from eios.ontology.metrics.catalog import create_default_registry
from eios.ontology.metrics.engine import MetricEngine, MetricQuery
from eios.synthesis.models import BriefingItem, BriefingObject


class MorningBriefingGenerator:
    """Proactive Morning Briefing synthesizer with tool audit and cached replay fallback."""

    def __init__(
        self,
        metric_engine: MetricEngine | None = None,
        cache_dir: Path | str | None = None,
    ) -> None:
        self.metric_engine = metric_engine
        if cache_dir is not None:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = Path("evals/reports/briefing_cache")
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._simulate_outage: bool = False
        self._latest_cached_briefing: BriefingObject | None = None
        self._auditor = MetricAuditorGate()

    def generate_briefing(self, briefing_date: str = "2026-10-06") -> BriefingObject:
        """Generate executive briefing, returning the structured BriefingObject."""
        briefing, _ = self.generate_briefing_with_tool_evidence(briefing_date=briefing_date)
        return briefing

    def _handle_cached_replay(
        self, briefing_date: str, cache_file: Path
    ) -> tuple[BriefingObject, list[dict[str, Any]]] | None:
        """Load and format cached briefing replay with [REPLAY] provenance."""
        cached = self._latest_cached_briefing
        if cached is None and cache_file.exists():
            with open(cache_file, encoding="utf-8") as f:
                cached = BriefingObject.model_validate_json(f.read())

        if cached is None:
            return None

        replayed_insights = [
            item.model_copy(
                update={
                    "summary": (
                        item.summary if "[REPLAY]" in item.summary else f"[REPLAY] {item.summary}"
                    )
                }
            )
            for item in cached.insights
        ]
        replayed_risks = [
            item.model_copy(
                update={
                    "summary": (
                        item.summary if "[REPLAY]" in item.summary else f"[REPLAY] {item.summary}"
                    )
                }
            )
            for item in cached.risks
        ]
        replayed_opps = [
            item.model_copy(
                update={
                    "summary": (
                        item.summary if "[REPLAY]" in item.summary else f"[REPLAY] {item.summary}"
                    )
                }
            )
            for item in cached.opportunities
        ]

        replayed_briefing = BriefingObject(
            briefing_id=cached.briefing_id,
            briefing_date=cached.briefing_date,
            generated_at=datetime.now(UTC),
            insights=replayed_insights,
            risks=replayed_risks,
            opportunities=replayed_opps,
            is_cached_replay=True,
            provenance_tag="[REPLAY]",
        )
        return replayed_briefing, []

    def generate_briefing_with_tool_evidence(
        self, briefing_date: str = "2026-10-06"
    ) -> tuple[BriefingObject, list[dict[str, Any]]]:
        """Synthesize briefing and return both the BriefingObject and deterministic tool traces."""
        cache_file = self.cache_dir / f"briefing_{briefing_date}.json"

        # Outage handling: return cached replay with [REPLAY] provenance
        if self._simulate_outage:
            replay_res = self._handle_cached_replay(briefing_date, cache_file)
            if replay_res is not None:
                return replay_res

        # Online generation: Query MetricEngine
        tool_outputs: list[dict[str, Any]] = []

        # Ensure metric engine available
        engine = self.metric_engine
        if engine is None:
            from eios.ingestion.hot_state import HotStateEngine

            reg = create_default_registry()
            engine = MetricEngine(hot_state=HotStateEngine(), registry=reg)

        metric_ids = [
            "net_deposit_volume_usd",
            "ftd_count_28d",
            "active_traders_24h",
            "partner_churn_rate",
            "partner_value_at_risk_usd",
            "chargeback_rate_bps",
            "avg_spread_pip",
        ]

        metric_vals: dict[str, float] = {}
        for m_id in metric_ids:
            try:
                res = engine.execute(MetricQuery(metric_id=m_id))
                val = float(res.value)
                unit = res.unit
            except Exception:
                val = 0.0
                unit = "unit"

            metric_vals[m_id] = val
            tool_outputs.append(
                {
                    "tool": "get_metric",
                    "output": {
                        "metric_id": m_id,
                        "value": val,
                        "unit": unit,
                    },
                }
            )

        # Build Insights (>= 3)
        net_dep = metric_vals.get("net_deposit_volume_usd", 0.0)
        ftd_cnt = metric_vals.get("ftd_count_28d", 0.0)
        traders = metric_vals.get("active_traders_24h", 0.0)

        insights = [
            BriefingItem(
                item_id="ITEM-INS-1",
                category="INSIGHT",
                title="Commercial Net Deposit Liquidity",
                summary=(
                    f"Commercial performance reports net deposit volume of {net_dep} USD "
                    "across settled client transaction channels."
                ),
                severity_or_impact="HIGH" if net_dep > 50000 else "MEDIUM",
                metric_citations=["net_deposit_volume_usd"],
                follow_up_prompt="Drill down into net deposits by payment gateway and currency?",
            ),
            BriefingItem(
                item_id="ITEM-INS-2",
                category="INSIGHT",
                title="Client Acquisition Funnel Momentum",
                summary=(
                    f"First-time deposit count reached {ftd_cnt} clients "
                    "in the trailing measurement window."
                ),
                severity_or_impact="MEDIUM",
                metric_citations=["ftd_count_28d"],
                follow_up_prompt="Review cohort retention rates for recent first-time depositors?",
            ),
            BriefingItem(
                item_id="ITEM-INS-3",
                category="INSIGHT",
                title="Trading Platform Activity",
                summary=(
                    f"Platform trading activity recorded {traders} active traders "
                    "executing open positions."
                ),
                severity_or_impact="LOW",
                metric_citations=["active_traders_24h"],
                follow_up_prompt="Analyze active trader turnover by major FX and CFD symbols?",
            ),
        ]

        # Build Risks (>= 2) ranked by P x VaR
        churn_rate = metric_vals.get("partner_churn_rate", 0.0)
        var_usd = metric_vals.get("partner_value_at_risk_usd", 0.0)
        cb_bps = metric_vals.get("chargeback_rate_bps", 0.0)

        partner_risk_score = churn_rate * var_usd

        risks = [
            BriefingItem(
                item_id="ITEM-RSK-1",
                category="RISK",
                title="Affiliate Partner Disengagement Hazard",
                summary=(
                    f"Partner churn hazard is {churn_rate} with total value at risk "
                    f"estimated at {var_usd} USD."
                ),
                severity_or_impact="HIGH" if partner_risk_score > 5000.0 else "MEDIUM",
                metric_citations=["partner_churn_rate", "partner_value_at_risk_usd"],
                follow_up_prompt="View high-risk tier 1 partners with declining referral volumes?",
            ),
            BriefingItem(
                item_id="ITEM-RSK-2",
                category="RISK",
                title="Payment Gateway Chargeback Exposure",
                summary=(
                    f"Transaction compliance tracking logged a chargeback rate of {cb_bps} bps "
                    "on incoming card flows."
                ),
                severity_or_impact="MEDIUM" if cb_bps > 50.0 else "LOW",
                metric_citations=["chargeback_rate_bps"],
                follow_up_prompt="Inspect payment routing rules for processors exceeding threshold?",
            ),
        ]

        # Build Opportunity (>= 1)
        spread = metric_vals.get("avg_spread_pip", 0.0)
        opportunities = [
            BriefingItem(
                item_id="ITEM-OPP-1",
                category="OPPORTUNITY",
                title="Competitive Spread Optimization",
                summary=(
                    f"Benchmark analysis tracks average trading spread at {spread} pips "
                    "relative to competitor quotes."
                ),
                severity_or_impact="MEDIUM",
                metric_citations=["avg_spread_pip"],
                follow_up_prompt="Simulate impact of narrowing EURUSD spread by 0.1 pips?",
            )
        ]

        # Audit narrative against tool traces
        full_narrative = " ".join(item.summary for item in insights + risks + opportunities)
        audit_res = self._auditor.audit(
            narrative_text=full_narrative,
            tool_outputs=tool_outputs,
        )

        # Circuit-breaker fallback if untraceable numbers are detected
        if not audit_res.passed:
            fallback_insights = [
                BriefingItem(
                    item_id=item.item_id,
                    category=item.category,
                    title=item.title,
                    summary=f"Governed metric report for {', '.join(item.metric_citations)}.",
                    severity_or_impact=item.severity_or_impact,
                    metric_citations=item.metric_citations,
                    follow_up_prompt=item.follow_up_prompt,
                )
                for item in insights
            ]
            fallback_risks = [
                BriefingItem(
                    item_id=item.item_id,
                    category=item.category,
                    title=item.title,
                    summary=f"Governed risk report for {', '.join(item.metric_citations)}.",
                    severity_or_impact=item.severity_or_impact,
                    metric_citations=item.metric_citations,
                    follow_up_prompt=item.follow_up_prompt,
                )
                for item in risks
            ]
            fallback_opps = [
                BriefingItem(
                    item_id=item.item_id,
                    category=item.category,
                    title=item.title,
                    summary=f"Governed opportunity report for {', '.join(item.metric_citations)}.",
                    severity_or_impact=item.severity_or_impact,
                    metric_citations=item.metric_citations,
                    follow_up_prompt=item.follow_up_prompt,
                )
                for item in opportunities
            ]
            insights, risks, opportunities = fallback_insights, fallback_risks, fallback_opps

        briefing = BriefingObject(
            briefing_id=f"BRIEF-{briefing_date}",
            briefing_date=briefing_date,
            generated_at=datetime.now(UTC),
            insights=insights,
            risks=risks,
            opportunities=opportunities,
            is_cached_replay=False,
            provenance_tag="[TARGET]",
        )

        # Cache the generated briefing
        self._latest_cached_briefing = briefing
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(briefing.model_dump_json(indent=2))
        except OSError:
            pass

        return briefing, tool_outputs
