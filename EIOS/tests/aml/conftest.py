"""Test fixtures and synthetic data generators for Client Fraud Sentinel / AML tests.

Provides deterministic seeded synthetic data:
- 2,000 alert triage queue with ~50 true positives, noise, and hard negatives (legitimate high-volume traders)
- Planted micro-P&L round-trip structuring lifecycles ($500 deposit -> 10m trade -> withdraw)
- Coordinated mule rings sharing payment/device tokens alongside public Wi-Fi hubs
- Dual-horizon peer cohort profiles (cold start vs mature accounts)
- Mock Cloud KMS ECDSA P-256 key provider
"""

from datetime import datetime, timedelta
import random
from typing import Any
import pandas as pd
import pytest

from eios.aml.models import (
    AMLAlert,
    AMLPriorityTier,
    AMLTriggerType,
    AMLTypology,
)


@pytest.fixture
def base_timestamp() -> datetime:
    return datetime(2026, 10, 1, 10, 0, 0)


@pytest.fixture
def synthetic_alert_queue(base_timestamp: datetime) -> list[AMLAlert]:
    """Generate a realistic queue of 2,000 surveillance alerts per docs/brief/monitoring.md.
    
    Contains:
    - 50 planted true-positive money laundering cases (acute round-trip, mule ring, or KYC burst)
    - 1,850 ambient rule noise alerts (single threshold triggers, false positives)
    - 100 hard negatives (legitimate high-volume retail traders with large routine deposits)
    """
    random.seed(42)
    alerts: list[AMLAlert] = []

    # 1. 50 Planted True Positives
    for i in range(50):
        client_id = f"C-PLANTED-AML-{i:03d}"
        alerts.append(
            AMLAlert(
                alert_id=f"ALT-TP-{i:04d}",
                client_id=client_id,
                trigger_type=AMLTriggerType.ROUND_TRIP_SEQUENCE if i % 2 == 0 else AMLTriggerType.MULE_RING_CLUSTER,
                risk_score=round(random.uniform(0.85, 0.99), 3),
                priority_tier=AMLPriorityTier.CRITICAL,
                typology=AMLTypology.MICRO_PNL_WASH if i % 2 == 0 else AMLTypology.MULE_SYNDICATE,
                amount_usd=round(random.uniform(500.0, 9500.0), 2),
                triggered_at=base_timestamp + timedelta(hours=i),
                is_triage_top50=True,
                attributes={
                    "is_planted_tp": True,
                    "hours_since_kyc": round(random.uniform(2.0, 48.0), 1),
                    "peer_z_score": round(random.uniform(3.5, 6.0), 2),
                    "deposit_withdrawal_ratio": round(random.uniform(0.95, 1.05), 3),
                    "mule_cluster_size": random.randint(8, 20) if i % 2 == 1 else 1,
                    "market_risk_pct": round(random.uniform(0.0001, 0.005), 4),
                },
            )
        )

    # 2. 100 Hard Negatives (Legitimate High-Volume Traders)
    for i in range(100):
        client_id = f"C-HARD-NEG-{i:03d}"
        alerts.append(
            AMLAlert(
                alert_id=f"ALT-HN-{i:04d}",
                client_id=client_id,
                trigger_type=AMLTriggerType.THRESHOLD_RULE,
                risk_score=round(random.uniform(0.40, 0.65), 3),  # naive rule alarms, but lower ML risk
                priority_tier=AMLPriorityTier.MEDIUM,
                typology=AMLTypology.NONE,
                amount_usd=round(random.uniform(15000.0, 50000.0), 2),
                triggered_at=base_timestamp + timedelta(minutes=10 * i),
                is_triage_top50=False,
                attributes={
                    "is_hard_negative": True,
                    "hours_since_kyc": round(random.uniform(300.0, 1000.0), 1),
                    "peer_z_score": round(random.uniform(1.0, 2.2), 2),
                    "deposit_withdrawal_ratio": round(random.uniform(0.2, 0.6), 2),
                    "mule_cluster_size": 1,
                    "market_risk_pct": round(random.uniform(0.08, 0.35), 3),  # genuine risk taken
                },
            )
        )

    # 3. 1,850 Ambient Rule Noise False Positives
    for i in range(1850):
        client_id = f"C-NOISE-{i:04d}"
        alerts.append(
            AMLAlert(
                alert_id=f"ALT-NOISE-{i:04d}",
                client_id=client_id,
                trigger_type=AMLTriggerType.THRESHOLD_RULE,
                risk_score=round(random.uniform(0.10, 0.45), 3),
                priority_tier=AMLPriorityTier.LOW,
                typology=AMLTypology.NONE,
                amount_usd=round(random.uniform(100.0, 12000.0), 2),
                triggered_at=base_timestamp + timedelta(minutes=3 * i),
                is_triage_top50=False,
                attributes={
                    "is_noise": True,
                    "hours_since_kyc": round(random.uniform(100.0, 5000.0), 1),
                    "peer_z_score": round(random.uniform(-1.0, 1.5), 2),
                    "deposit_withdrawal_ratio": round(random.uniform(0.1, 0.8), 2),
                    "mule_cluster_size": 1,
                    "market_risk_pct": round(random.uniform(0.05, 0.25), 3),
                },
            )
        )

    random.shuffle(alerts)
    return alerts


@pytest.fixture
def synthetic_roundtrip_history(base_timestamp: datetime) -> pd.DataFrame:
    """Generate deposit, trading, and withdrawal transactions for round-trip testing."""
    records: list[dict[str, Any]] = []

    # 1. Planted Micro-P&L Laundering Account: C-AML-ROUNDTRIP-01
    # $500 deposit -> trades EURUSD for 10 min with $0.01 profit -> withdraws $499.50 within 24h KYC
    records.append({
        "event_type": "DEPOSIT",
        "txn_id": "TXN-DEP-001",
        "client_id": "C-AML-ROUNDTRIP-01",
        "amount": 500.0,
        "currency": "USD",
        "timestamp": base_timestamp,
        "kyc_approved_at": base_timestamp - timedelta(hours=12),
    })
    records.append({
        "event_type": "TRADE",
        "txn_id": "TRD-001",
        "client_id": "C-AML-ROUNDTRIP-01",
        "symbol": "EURUSD",
        "side": "BUY",
        "volume": 0.1,
        "open_ts": base_timestamp + timedelta(minutes=10),
        "close_ts": base_timestamp + timedelta(minutes=20),
        "profit_loss": 0.01,
    })
    records.append({
        "event_type": "WITHDRAWAL",
        "txn_id": "TXN-WDL-001",
        "client_id": "C-AML-ROUNDTRIP-01",
        "amount": 499.50,
        "currency": "USD",
        "timestamp": base_timestamp + timedelta(hours=2),
        "kyc_approved_at": base_timestamp - timedelta(hours=12),
    })

    # 2. Legitimate Scalper: C-LEGIT-SCALPER-01 (short holding time, but real risk and regular trading)
    records.append({
        "event_type": "DEPOSIT",
        "txn_id": "TXN-DEP-002",
        "client_id": "C-LEGIT-SCALPER-01",
        "amount": 5000.0,
        "currency": "USD",
        "timestamp": base_timestamp - timedelta(days=5),
        "kyc_approved_at": base_timestamp - timedelta(days=60),
    })
    for j in range(15):
        records.append({
            "event_type": "TRADE",
            "txn_id": f"TRD-SCALP-{j}",
            "client_id": "C-LEGIT-SCALPER-01",
            "symbol": "BTCUSD",
            "side": "BUY" if j % 2 == 0 else "SELL",
            "volume": 1.0,
            "open_ts": base_timestamp + timedelta(minutes=30 * j),
            "close_ts": base_timestamp + timedelta(minutes=30 * j + 5),
            "profit_loss": (j % 4 - 1.5) * 85.0,  # fluctuating real P&L
        })
    records.append({
        "event_type": "WITHDRAWAL",
        "txn_id": "TXN-WDL-002",
        "client_id": "C-LEGIT-SCALPER-01",
        "amount": 1200.0,
        "currency": "USD",
        "timestamp": base_timestamp + timedelta(hours=10),
        "kyc_approved_at": base_timestamp - timedelta(days=60),
    })

    return pd.DataFrame(records)


@pytest.fixture
def synthetic_network_edges(base_timestamp: datetime) -> pd.DataFrame:
    """Generate entity network graph edges:
    - Planted Mule Ring: 8 accounts sharing 2 payment methods and 1 device
    - Public Wi-Fi Hub: 150 accounts sharing 1 IP marked as shared context
    """
    edges: list[dict[str, Any]] = []

    # Planted Mule Ring: C-MULE-01 to C-MULE-08
    for i in range(1, 9):
        cid = f"C-MULE-{i:02d}"
        # Shared payment card 1
        edges.append({
            "source_id": cid,
            "target_id": "tok_pay_card_alpha_99",
            "edge_type": "SHARED_PAYMENT",
            "is_shared_context": False,
        })
        # Shared hardware device hash
        edges.append({
            "source_id": cid,
            "target_id": "tok_dev_hw_nexus_42",
            "edge_type": "SHARED_DEVICE",
            "is_shared_context": False,
        })

    # Public Wi-Fi / CGNAT Hub: C-PUBLIC-001 to C-PUBLIC-150
    for i in range(1, 151):
        cid = f"C-PUBLIC-{i:03d}"
        edges.append({
            "source_id": cid,
            "target_id": "tok_ip_airport_cgnat_hub",
            "edge_type": "SHARED_IP",
            "is_shared_context": True,  # High degree hub
        })

    return pd.DataFrame(edges)
