"""Tests for Partner Manager Workstation: Churn Radar, Referral Tree, and Playbooks."""

import pytest
from eios.cockpit.partner import PartnerWorkstationService, PartnerQuadrant
from eios.cockpit.schemas import validate_contract


def test_churn_radar_scatter_contract():
    svc = PartnerWorkstationService()
    scatter = svc.get_churn_radar_scatter()
    
    assert len(scatter.partners) >= 20
    at_risk = next(p for p in scatter.partners if p.partner_id in ["PTR-882", "AP-1029"])
    assert at_risk.quadrant == PartnerQuadrant.HIGH_VALUE_HIGH_RISK
    assert at_risk.days_to_intervention_deadline == 14
    assert at_risk.churn_hazard_probability == 0.78
    assert "Exness" in at_risk.primary_root_cause

    contract_dict = scatter.to_contract_dict()
    assert validate_contract(contract_dict, "churn-radar-scatter") is True


def test_partner_referral_tree_opposite_trading():
    svc = PartnerWorkstationService()
    tree = svc.get_partner_referral_tree("AP-1029")
    
    assert tree["master_partner_id"] == "AP-1029"
    assert len(tree["detected_abusive_rings"]) >= 1
    ring = tree["detected_abusive_rings"][0]
    assert ring["scheme"] == "Opposite Trading on Boom 1000 Index"
    assert ring["unearned_commission_liability_usd"] == 42500.0


def test_retention_playbooks_fast_path_policy():
    svc = PartnerWorkstationService()
    playbooks = svc.get_retention_playbooks("AP-1029")
    
    assert len(playbooks) == 2
    # Deal 1 <= $2,500 -> fast path
    assert playbooks[0].estimated_cost_usd <= 2500.0
    assert playbooks[0].is_fast_path_eligible is True
    assert playbooks[0].requires_four_eyes is False
    
    # Deal 2 > $2,500 -> dual approval
    assert playbooks[1].estimated_cost_usd > 2500.0
    assert playbooks[1].is_fast_path_eligible is False
    assert playbooks[1].requires_four_eyes is True
