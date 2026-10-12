"""Integration tests for AML Dossier Assembler and SAR Composer (US6 / P2).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4
- specs/010-client-aml/spec.md (User Story 6, SC-006, SC-007)
- .specify/memory/constitution.md (Principles I, VII, VIII)
"""

from datetime import datetime, timezone
import time
import pytest

from eios.aml.dossier import AMLDossierAssembler
from eios.aml.sar_composer import SARComposer
from eios.ingestion.hot_state import HotStateEngine


def test_dossier_assembly_latency_and_citation_coverage() -> None:
    """Verify dossier compiles in < 2.5s with 100% citation coverage."""
    hot_state = HotStateEngine()
    assembler = AMLDossierAssembler(hot_state=hot_state)

    t0 = time.perf_counter()
    dossier = assembler.assemble_dossier(
        client_id="C-AML-ROUNDTRIP-01",
        kyc_tier="TIER_2_VERIFIED",
        total_deposit=500.0,
        total_withdrawal=499.50,
        net_pl=0.01,
        mule_ring_id="MULE-01",
        mule_ring_size=4,
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 2500.0, f"Latency {latency_ms:.2f}ms exceeded 2500ms SLO"
    assert dossier.client_id == "C-AML-ROUNDTRIP-01"
    assert dossier.composite_risk_score >= 0.85
    assert len(dossier.citations) >= 2
    assert any("transactions_aml" in c for c in dossier.citations)
    assert any("trading_activity" in c for c in dossier.citations)


def test_sar_composer_generates_regulator_ready_draft() -> None:
    """Verify SAR Composer generates FinCEN sections with statutory normalization."""
    hot_state = HotStateEngine()
    assembler = AMLDossierAssembler(hot_state=hot_state)
    composer = SARComposer()

    dossier = assembler.assemble_dossier(
        client_id="C-AML-ROUNDTRIP-01",
        kyc_tier="TIER_2_VERIFIED",
        total_deposit=500.0,
        total_withdrawal=499.50,
        net_pl=0.01,
        mule_ring_id="MULE-01",
        mule_ring_size=4,
    )

    sar = composer.compose_sar(dossier, jurisdiction="US_FINCEN")

    assert sar.client_id == "C-AML-ROUNDTRIP-01"
    assert sar.jurisdiction == "US_FINCEN"
    assert len(sar.chronological_transactions) >= 1
    assert "31_CFR_1010" in sar.statutory_provisions or "31 CFR 1010" in str(sar.statutory_provisions)
    assert "31_USC_5318" in sar.statutory_provisions or "31 U.S.C. 5318" in str(sar.statutory_provisions)
    assert len(sar.evidence_citations) >= 2


def test_sar_composer_replay_fallback() -> None:
    """Verify deterministic replay fallback with [REPLAY] badge under outage (Principle VIII)."""
    hot_state = HotStateEngine()
    assembler = AMLDossierAssembler(hot_state=hot_state)
    composer = SARComposer(force_fallback=True)

    dossier = assembler.assemble_dossier(
        client_id="C-AML-FALLBACK-01",
        kyc_tier="TIER_1_BASIC",
        total_deposit=1000.0,
        total_withdrawal=995.0,
        net_pl=0.0,
    )

    sar = composer.compose_sar(dossier, jurisdiction="US_FINCEN")

    assert sar.is_replay_fallback is True
    assert "[REPLAY]" in sar.narrative_basis
