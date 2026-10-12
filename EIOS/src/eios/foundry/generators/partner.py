"""Partner fraud generator: 3-tier affiliate rings, mirror trading, bot traffic, and bonus abuse (FR-026 to FR-034)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from eios.foundry.contracts import (
    CommissionLedgerRecord,
    ContractValidator,
    Partner360Record,
    ReferralNodeRecord,
)
from eios.foundry.rng import RNGManager
from eios.foundry.storage.eval_truth_store import EvalGroundTruthStore
from eios.foundry.universe import GlobalEntityUniverse


class PartnerDataGenerator:
    """Generates affiliate network structures, commission ledgers, and planted partner fraud typologies."""

    def __init__(
        self,
        universe: GlobalEntityUniverse,
        rng: RNGManager,
        truth_store: Optional[EvalGroundTruthStore] = None,
    ) -> None:
        self.universe = universe
        self.rng = rng
        self.truth_store = truth_store
        self._gen = rng.get_generator("partner_fraud")

        self._validator_360 = ContractValidator(Partner360Record)
        self._validator_tree = ContractValidator(ReferralNodeRecord)
        self._validator_ledger = ContractValidator(CommissionLedgerRecord)

    def generate_partner_360(self) -> List[Dict[str, Any]]:
        """Emits validated partner_360 records."""
        records: List[Dict[str, Any]] = []
        base_dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        tiers: List[Literal["STANDARD", "VIP", "MASTER"]] = ["MASTER", "VIP", "STANDARD"]

        for idx, partner in enumerate(self.universe.partners):
            tier_name = tiers[partner.tier - 1] if 1 <= partner.tier <= 3 else "STANDARD"
            is_bot = 30 <= idx < 42  # 12 bot partners
            joined_dt = base_dt + timedelta(days=idx * 2)

            records.append(
                {
                    "partner_id": partner.partner_id,
                    "person_id": partner.person_id,
                    "referral_code": f"REF-{partner.partner_id}",
                    "parent_partner_id": partner.parent_partner_id,
                    "commission_tier": tier_name,
                    "joined_at": joined_dt.isoformat(),
                    "is_bot_fraud": is_bot,
                }
            )

        self._validator_360.validate_batch(records)
        return records

    def generate_referral_tree(self) -> List[Dict[str, Any]]:
        """Emits validated referral_tree link records across max 3 tiers."""
        records: List[Dict[str, Any]] = []
        link_counter = 0
        base_dt = datetime(2024, 2, 1, tzinfo=timezone.utc)

        # 1. Partner-to-Partner hierarchical links (Tier 1 -> Tier 2 -> Tier 3)
        for partner in self.universe.partners:
            if partner.parent_partner_id:
                link_counter += 1
                records.append(
                    {
                        "link_id": f"LNK-P-{link_counter:07d}",
                        "parent_partner_id": partner.parent_partner_id,
                        "child_partner_id": partner.partner_id,
                        "referred_client_id": None,
                        "tier_depth": partner.tier,
                        "created_at": base_dt.isoformat(),
                    }
                )

        # 2. Partner-to-Client referral links
        for idx, client in enumerate(self.universe.accounts):
            assigned_partner = self.universe.partners[idx % len(self.universe.partners)]
            link_counter += 1
            records.append(
                {
                    "link_id": f"LNK-C-{link_counter:07d}",
                    "parent_partner_id": assigned_partner.partner_id,
                    "child_partner_id": None,
                    "referred_client_id": client.client_id,
                    "tier_depth": min(3, assigned_partner.tier),
                    "created_at": client.created_at,
                }
            )

        self._validator_tree.validate_batch(records)
        return records

    def generate_commission_ledger(self, count: int = 100) -> List[Dict[str, Any]]:
        """Emits validated commission ledger payout records."""
        records: List[Dict[str, Any]] = []
        base_dt = datetime(2025, 2, 1, 0, 0, 0, tzinfo=timezone.utc)

        for idx in range(count):
            partner = self.universe.partners[idx % len(self.universe.partners)]
            client = self.universe.accounts[idx % len(self.universe.accounts)]
            tx_dt = base_dt + timedelta(hours=idx * 2)
            comm_amount = Decimal(f"{(idx % 20 + 1) * 3.50:.2f}")

            records.append(
                {
                    "ledger_id": f"LEDGER-{idx + 1:08d}",
                    "partner_id": partner.partner_id,
                    "client_account_id": client.client_id,
                    "deal_id_ref": f"DEAL-{idx + 1:08d}",
                    "commission_amount": comm_amount,
                    "calculation_tier": partner.tier,
                    "timestamp": tx_dt.isoformat(),
                }
            )

        self._validator_ledger.validate_batch(records)
        return records

    def generate_partner_fraud_suite(self) -> Dict[str, Any]:
        """Generates 3-tier ring, 23 mirror trading pairs, 12 bot partners, and 35% bonus abuse."""
        master_partners = [p.partner_id for p in self.universe.partners[:7]]
        sub_partners = [p.partner_id for p in self.universe.partners[7:30]]  # 23
        clients_184 = [c.client_id for c in self.universe.accounts[:184]]

        ring_truth = {
            "typology": "THREE_TIER_SYNDICATE_RING",
            "master_partner_ids": master_partners,
            "sub_partner_ids": sub_partners,
            "referred_client_ids": clients_184,
            "tier_depth": 3,
        }

        if self.truth_store:
            self.truth_store.write_truth("module_b/partner_ring_7_23_184.json", ring_truth)

        # 23 Mirror trading pairs
        mirror_pairs: List[Dict[str, Any]] = []
        for i in range(23):
            c1 = self.universe.accounts[i * 2].client_id
            c2 = self.universe.accounts[i * 2 + 1].client_id
            mirror_pairs.append(
                {
                    "pair_id": f"PAIR-{i + 1:04d}",
                    "client_a": c1,
                    "client_b": c2,
                    "timing_correlation": 0.92,
                    "net_client_pnl": 0.05,
                    "commission_extracted": 340.50,
                }
            )

        # 12 Bot-traffic partners
        bot_partners: List[Dict[str, Any]] = []
        for i in range(12):
            bp_id = self.universe.partners[30 + i].partner_id
            bot_partners.append(
                {
                    "partner_id": bp_id,
                    "click_to_signup_conversion": 0.96,
                    "traffic_type": "BOT_FARM",
                }
            )

        # 35% Bonus abuse
        bonus_abuse = {
            "typology": "BONUS_ABUSE_SEQUENCE",
            "bonus_abuse_share": 0.35,
            "pattern": "DEPOSIT -> MINIMAL_ACTIVITY -> WITHDRAWAL",
        }

        return {
            "ring_truth": ring_truth,
            "mirror_pairs": mirror_pairs,
            "bot_partners": bot_partners,
            "bonus_abuse": bonus_abuse,
        }
