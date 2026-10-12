"""Tests for Daily Morning Briefing generation and schema validation (T023, US4)."""

import json
from pathlib import Path

import jsonschema

from eios.ontology.metrics.catalog import create_default_registry
from eios.ontology.metrics.engine import MetricEngine
from eios.synthesis.briefing import MorningBriefingGenerator


def test_morning_briefing_generation_and_schema_validation(seeded_hot_state):
    """Verify morning briefing generates >=3 insights, >=2 risks, >=1 opportunity and matches schema."""
    registry = create_default_registry()
    metric_engine = MetricEngine(hot_state=seeded_hot_state, registry=registry)

    generator = MorningBriefingGenerator(metric_engine=metric_engine)
    briefing = generator.generate_briefing(briefing_date="2026-10-06")

    assert briefing.briefing_id == "BRIEF-2026-10-06"
    assert len(briefing.insights) >= 3
    assert len(briefing.risks) >= 2
    assert len(briefing.opportunities) >= 1
    assert briefing.is_cached_replay is False

    # Check each item structure
    for item in briefing.insights + briefing.risks + briefing.opportunities:
        assert item.item_id.startswith("ITEM-")
        assert len(item.metric_citations) >= 1
        assert len(item.follow_up_prompt) > 0

    # Validate against JSON schema contract
    schema_path = (
        Path(__file__).parents[2] / "schemas" / "synthesis" / "synthesis-briefing.schema.json"
    )
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    briefing_dict = briefing.model_dump(mode="json")
    jsonschema.validate(instance=briefing_dict, schema=schema)
