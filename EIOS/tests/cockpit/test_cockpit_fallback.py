"""Tests for Cockpit Deterministic Fallback and Replay Badging."""

import pytest
from eios.cockpit.fallback import FallbackEngine, ServiceHealthState


def test_fallback_caches_live_execution():
    engine = FallbackEngine()
    
    def live_call():
        return {"briefing_id": "brf_001", "headline": "Live briefing content"}

    result = engine.execute_with_fallback("morning_briefing", live_call)
    assert result["briefing_id"] == "brf_001"
    assert engine.health_state == ServiceHealthState.HEALTHY_LIVE
    assert engine.failover_count == 0


def test_fallback_activates_on_outage():
    engine = FallbackEngine()
    
    # Prime with a warm snapshot
    engine.register_snapshot("morning_briefing", {"briefing_id": "brf_001", "headline": "Verified cached briefing"})
    
    def failing_call():
        raise TimeoutError("Vertex AI gateway 504 Gateway Timeout")

    result = engine.execute_with_fallback("morning_briefing", failing_call)
    
    assert result["is_cached_fallback"] is True
    assert "fallback_badge" in result
    badge = result["fallback_badge"]
    assert badge["badge_label"] == "[REPLAY]"
    assert badge["badge_color"] == "#b45309"
    assert "unavailable" in badge["message"]
    assert engine.health_state == ServiceHealthState.DEGRADED_REPLAY
    assert engine.failover_count == 1


def test_fallback_unregistered_view_raises():
    engine = FallbackEngine()
    
    def failing_call():
        raise ConnectionResetError("Connection lost")

    with pytest.raises(KeyError, match="No cached snapshot"):
        engine.execute_with_fallback("unknown_view", failing_call)
