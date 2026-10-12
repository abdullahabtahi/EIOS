"""Unit tests for Traffic & Bot Anomaly Detector (T028 / US5).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US5, FR-009)
- specs/009-partner-fraud/research.md §5
"""

import pytest

from eios.fraud.traffic_anomaly import TrafficAnomalyDetector


def test_traffic_anomaly_detector_flags_bot_funnels(synthetic_clickstream_funnels: list[dict]) -> None:
    detector = TrafficAnomalyDetector(sigma_threshold=3.0)
    signals = detector.evaluate_funnels(synthetic_clickstream_funnels)

    bot_signal = next((s for s in signals if s.partner_id == "P-BOT-TRAFFIC"), None)
    assert bot_signal is not None
    assert bot_signal.anomaly_flag is True
    assert bot_signal.p_value < 0.001
    assert bot_signal.bot_traffic_probability >= 0.90
    assert bot_signal.click_to_signup_rate > 0.80

    normal_signal = next((s for s in signals if s.partner_id == "P-NORMAL-MKT"), None)
    assert normal_signal is not None
    assert normal_signal.anomaly_flag is False
    assert normal_signal.bot_traffic_probability < 0.15


def test_traffic_anomaly_detector_handles_contextual_seminar_campaign() -> None:
    """Offline seminar with genuine organic conversions allows contextual justification."""
    seminar_record = [
        {
            "partner_id": "P-SEMINAR-VIP",
            "click_count": 100,
            "registration_count": 80,
            "ftd_count": 65,
            "is_contextual_campaign": True,
            "campaign_type": "OFFLINE_SEMINAR",
        }
    ]

    detector = TrafficAnomalyDetector(sigma_threshold=3.0)
    signals = detector.evaluate_funnels(seminar_record)

    assert len(signals) == 1
    seminar_signal = signals[0]
    # Even though conversion is high, contextual justification prevents blocking bot flag
    assert seminar_signal.bot_traffic_probability < 0.40
    assert seminar_signal.anomaly_flag is False
