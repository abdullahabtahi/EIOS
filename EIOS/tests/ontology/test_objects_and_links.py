from eios.ontology.config import SecurityMarking
from eios.ontology.core.links import OntologyLinkGraph
from eios.ontology.core.objects import (
    Alert,
    Case,
    ClientAccount,
    Competitor,
    Decision,
    Device,
    IPAddress,
    MacroEvent,
    Partner,
    PaymentMethod,
    Product,
    Region,
    SubAffiliate,
)


def test_13_canonical_object_types():
    # 1. ClientAccount
    c = ClientAccount(
        client_id="C-1001",
        kyc_status="APPROVED",
        segment="VIP",
        lifetime_value_usd=15000.0,
        markings=[SecurityMarking.PII],
    )
    assert c.primary_key == "C-1001"
    assert c.has_marking(SecurityMarking.PII)

    # 2. Device
    d = Device(device_id="DEV-1", device_fingerprint="fp_abc123", is_shared_context=False)
    assert d.primary_key == "DEV-1"

    # 3. IPAddress
    ip = IPAddress(
        ip_id="IP-1", ip_address="192.168.1.1", country_code="CYP", is_shared_context=True
    )
    assert ip.primary_key == "IP-1"
    assert ip.is_shared_context

    # 4. PaymentMethod
    pm = PaymentMethod(
        payment_method_id="PM-1", method_type="CREDIT_CARD", markings=[SecurityMarking.PII]
    )
    assert pm.primary_key == "PM-1"

    # 5. Partner
    p = Partner(
        partner_id="P-101",
        tier="TIER_1",
        region_id="LATAM",
        markings=[SecurityMarking.PARTNER_COMMERCIAL],
    )
    assert p.primary_key == "P-101"

    # 6. SubAffiliate
    sub = SubAffiliate(sub_affiliate_id="SUB-1", parent_partner_id="P-101", attribution_layer=2)
    assert sub.primary_key == "SUB-1"

    # 7. Competitor
    comp = Competitor(competitor_id="COMP-1", name="AlphaBroker", payout_rate_estimate=0.45)
    assert comp.primary_key == "COMP-1"

    # 8. Product
    prod = Product(product_id="PROD-MT5", name="Deriv MT5", category="CFD")
    assert prod.primary_key == "PROD-MT5"

    # 9. Region
    reg = Region(region_id="LATAM", name="Latin America", regulatory_tier="TIER_2")
    assert reg.primary_key == "LATAM"

    # 10. Case
    case = Case(
        case_id="CASE-1",
        target_id="C-1001",
        typology="MIRROR_TRADING",
        markings=[SecurityMarking.SENSITIVE_COMPLIANCE],
    )
    assert case.primary_key == "CASE-1"

    # 11. Alert
    alert = Alert(
        alert_id="ALT-1",
        case_id="CASE-1",
        rule_name="OPPOSITE_TRADE",
        confidence_score=0.92,
        markings=[SecurityMarking.SENSITIVE_COMPLIANCE],
    )
    assert alert.primary_key == "ALT-1"

    # 12. Decision
    dec = Decision(
        decision_id="DEC-1", action_intent_id="INT-99", outcome="APPROVED", approver_id="MLRO-1"
    )
    assert dec.primary_key == "DEC-1"

    # 13. MacroEvent
    me = MacroEvent(event_id="EVT-1", event_type="REGULATORY_SHIFT", shock_intensity=0.75)
    assert me.primary_key == "EVT-1"


def test_ontology_link_graph_bidirectional_traversal():
    graph = OntologyLinkGraph()
    graph.add_link(
        link_type="USES_DEVICE",
        source_id="C-1001",
        target_id="DEV-1",
        cardinality="MANY_TO_MANY",
        metadata={"session_count": 5},
    )
    graph.add_link(
        link_type="USES_DEVICE",
        source_id="C-1002",
        target_id="DEV-1",
        cardinality="MANY_TO_MANY",
        metadata={"session_count": 10},
    )

    devices = graph.get_target_links("C-1001", link_type="USES_DEVICE")
    assert len(devices) == 1
    assert devices[0].target_id == "DEV-1"

    clients = graph.get_source_links("DEV-1", link_type="USES_DEVICE")
    assert len(clients) == 2
    assert {c.source_id for c in clients} == {"C-1001", "C-1002"}
