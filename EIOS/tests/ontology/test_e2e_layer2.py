"""End-to-End Layer 2 Integration Test (T047).

Executes full enterprise lifecycle:
1. Ingest event into hot state
2. Query governed metric via OMCP tool surface
3. Traverse graph with hub suppression
4. Evaluate deterministic server-side function
5. Propose non-autonomous Action Intent (ECDSA P-256 signed)
6. Verify agent synthetic narrative through Metric Auditor Gate (Red-Line RL-1)
"""

from datetime import UTC, datetime

from eios.contracts.base import DataProductEnum
from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.auditor.gate import MetricAuditorGate
from eios.ontology.omcp.server import OMCPServer


def test_full_layer2_lifecycle(seeded_hot_state: HotStateEngine):
    # 1. Ingest new transactions into hot-state
    seeded_hot_state.insert_event(
        DataProductEnum.TRANSACTIONS_AML,
        {
            "txn_id": "TXN-E2E-1",
            "client_id": "C-1001",
            "txn_type": "deposit",
            "amount": 50000.0,
            "currency": "USD",
            "payment_method_id": "PM-1",
            "payment_agent_id": None,
            "timestamp": datetime.now(UTC),
            "is_first_deposit": False,
            "status": "SETTLED",
        },
    )

    # 2. Instantiate OMCPServer
    server = OMCPServer(hot_state=seeded_hot_state)

    # 3. Query governed metric
    metric_res = server.call_tool(
        "get_metric",
        {"metric_id": "net_deposit_volume_usd", "filters": {"currency": "USD"}},
        caller_role="AMLInvestigator",
    )
    metric_val = metric_res["value"]
    assert metric_val > 0.0

    # 4. Traverse graph with hub suppression
    graph_res = server.call_tool(
        "traverse_graph",
        {"seed_ids": ["C-1001"], "hops": 2, "suppress_hubs": True},
        caller_role="AMLInvestigator",
    )
    assert len(graph_res["nodes"]) > 0
    assert "DEV-HUB" in graph_res["hub_flags"]

    # 5. Evaluate deterministic partner signals
    partner_signals = server.call_tool(
        "get_partner_signals",
        {"partner_id": "P-101"},
        caller_role="PartnerManager",
    )
    hazard_score = partner_signals["churn_hazard_score"]
    assert hazard_score >= 0.0

    # 6. Propose non-autonomous action intent
    action_res = server.call_tool(
        "propose_action",
        {
            "action_type": "HoldWithdrawal",
            "parameters": {"txn_id": "TXN-E2E-1", "reason": "UNUSUAL_VOLUME"},
            "evidence_refs": ["EVID-E2E-99"],
        },
        caller_role="AMLInvestigator",
    )
    intent_id = action_res["intent_id"]
    assert action_res["status"] == "PENDING"
    assert action_res["signature"] is not None

    # Check status
    status_res = server.call_tool(
        "get_intent_status",
        {"intent_id": intent_id},
        caller_role="AMLInvestigator",
    )
    assert status_res["status"] == "PENDING"

    # 7. Construct session execution traces
    session_tool_traces = [
        {
            "tool_name": "get_metric",
            "inputs": {"metric_id": "net_deposit_volume_usd"},
            "output": {"value": metric_val, "unit": "USD"},
        },
        {
            "tool_name": "get_partner_signals",
            "inputs": {"partner_id": "P-101"},
            "output": {"churn_hazard_score": hazard_score},
        },
    ]

    # 8. Verify compliant agent narrative through Metric Auditor Gate
    auditor = MetricAuditorGate()
    compliant_text = (
        f"Partner P-101 exhibits a churn hazard score of {hazard_score:.2f}. "
        f"The net deposit volume stands at ${metric_val:,.2f}."
    )
    audit_rec = auditor.verify_response(compliant_text, session_tool_traces)
    assert audit_rec.is_compliant is True
    assert len(audit_rec.unanchored_tokens) == 0

    # 9. Verify adversarial/hallucinated narrative is blocked
    hallucinated_text = "Net deposit volume reached $999,999.00 while partner churn hazard is 0.99."
    adversarial_rec = auditor.verify_response(hallucinated_text, session_tool_traces)
    assert adversarial_rec.is_compliant is False
    assert len(adversarial_rec.unanchored_tokens) > 0
