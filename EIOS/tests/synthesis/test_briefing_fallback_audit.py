"""Tests for Morning Briefing Auditor Gate compliance and cached replay fallback (T024, US4)."""

from eios.ontology.auditor.gate import MetricAuditorGate
from eios.ontology.metrics.catalog import create_default_registry
from eios.ontology.metrics.engine import MetricEngine
from eios.synthesis.briefing import MorningBriefingGenerator


def test_briefing_narrative_passes_metric_auditor_gate(seeded_hot_state):
    """Verify that synthesized briefing text contains 0 ungrounded/hallucinated numbers."""
    registry = create_default_registry()
    metric_engine = MetricEngine(hot_state=seeded_hot_state, registry=registry)
    generator = MorningBriefingGenerator(metric_engine=metric_engine)

    briefing, tool_outputs = generator.generate_briefing_with_tool_evidence(
        briefing_date="2026-10-06"
    )

    auditor = MetricAuditorGate()
    # Audit narrative of all items against tool_outputs
    full_narrative = " ".join(
        item.summary for item in briefing.insights + briefing.risks + briefing.opportunities
    )
    audit_res = auditor.audit(response_text=full_narrative, tool_outputs=tool_outputs)

    assert audit_res.passed is True
    assert len(audit_res.untraceable_numbers) == 0


def test_briefing_cached_replay_fallback_on_failure(seeded_hot_state, tmp_path):
    """Verify that provider outage returns cached briefing marked with [REPLAY] badge."""
    registry = create_default_registry()
    metric_engine = MetricEngine(hot_state=seeded_hot_state, registry=registry)
    cache_dir = tmp_path / "briefing_cache"
    generator = MorningBriefingGenerator(metric_engine=metric_engine, cache_dir=cache_dir)

    # 1. Successful generation seeds cache
    b1 = generator.generate_briefing(briefing_date="2026-10-06")
    assert b1.is_cached_replay is False

    # 2. Simulate upstream failure by corrupting engine execution
    generator._simulate_outage = True
    b2 = generator.generate_briefing(briefing_date="2026-10-06")

    assert b2.is_cached_replay is True
    assert b2.briefing_id == b1.briefing_id
    assert any("[REPLAY]" in item.summary for item in b2.insights)
