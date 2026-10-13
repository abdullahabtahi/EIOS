"""Tests for Compliance & Audit Explorer: Monotonic Ledger, Hash Chain Verifier, and WORM Proofs."""

from eios.cockpit.compliance import ComplianceExplorerService


def test_monotonic_ledger_timeline():
    svc = ComplianceExplorerService()
    entries = svc.get_ledger_timeline(start_seq=1, limit=10)

    assert len(entries) >= 3
    # Check strict sequence monotonicity: 1, 2, 3...
    seqs = [e["ledger_seq"] for e in entries]
    assert seqs == list(range(1, len(entries) + 1))

    # Check cryptographic link continuity: e[i].prev_hash == e[i-1].current_hash
    for i in range(1, len(entries)):
        assert entries[i]["prev_hash"] == entries[i - 1]["current_hash"]


def test_verify_hash_chain_interactive_latency_and_integrity():
    svc = ComplianceExplorerService()
    res = svc.verify_hash_chain_interactive()

    assert res["total_entries_verified"] >= 1000
    assert res["is_chain_unbroken"] is True
    assert res["integrity_score_pct"] == 100.0
    assert len(res["corrupted_indices"]) == 0
    # Latency must be < 1000ms
    assert res["verification_latency_ms"] < 1000.0


def test_worm_compliance_proofs():
    svc = ComplianceExplorerService()
    proofs = svc.get_worm_compliance_proofs()

    assert len(proofs) >= 1
    p = proofs[0]
    assert p["compliance_lock_mode"] == "COMPLIANCE"
    assert p["is_immutable"] is True
    assert "gs://" in p["storage_uri"]


def test_four_eyes_approval_log():
    svc = ComplianceExplorerService()
    logs = svc.get_four_eyes_approval_log()

    assert len(logs) >= 1
    log = logs[0]
    assert log["severity"] == "HIGH"
    assert log["first_approver"]["officer_id"] != log["second_approver"]["officer_id"]
    assert log["first_approver"]["role"] == "AML_INVESTIGATOR"
    assert log["second_approver"]["role"] == "COMPLIANCE_HEAD"
    assert log["status"] == "EXECUTED"
