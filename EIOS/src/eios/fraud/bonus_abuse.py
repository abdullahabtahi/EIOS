"""Client Quality & Bonus Abuse Scorer (US3 / Module B).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US3, FR-006, FR-007)
- specs/009-partner-fraud/research.md §3
"""

import numpy as np

from eios.fraud.models import BonusAbuseProfile


class BonusAbuseScorer:
    """Calculates client lifecycle velocity, CPA harvesting risk, and Client Quality Index (CQI).

    Formula for Client Quality Index (CQI):
        CQI = 0.40 * retention_score + 0.35 * turnover_score - 0.25 * fast_withdrawal_penalty
    Normalized to [0.0, 1.0].
    Partners with CQI < 0.20 are flagged as HIGH_BONUS_ABUSE_RISK.
    """

    def __init__(
        self,
        fast_withdrawal_threshold_hours: float = 72.0,
        micro_trade_threshold: int = 2,
    ) -> None:
        self.fast_withdrawal_threshold_hours = fast_withdrawal_threshold_hours
        self.micro_trade_threshold = micro_trade_threshold

    def score_partner_portfolio(
        self,
        partner_id: str,
        client_records: list[dict],
    ) -> BonusAbuseProfile:
        """Evaluate all client lifecycles for a given partner and produce a BonusAbuseProfile."""
        partner_clients = [c for c in client_records if c.get("partner_id") == partner_id]
        total_clients = len(partner_clients)

        if total_clients == 0:
            return BonusAbuseProfile(
                partner_id=partner_id,
                total_referred_clients=0,
                fast_withdrawal_count_72h=0,
                micro_trade_only_count=0,
                median_holding_duration_hours=0.0,
                turnover_to_deposit_ratio=0.0,
                cpa_bounty_collected_usd=0.0,
                client_quality_index=1.0,
                abuse_probability=0.0,
                status="NORMAL",
            )

        fast_withdrawals = 0
        micro_trades = 0
        holding_durations: list[float] = []
        turnover_ratios: list[float] = []
        active_30d_count = 0
        total_cpa = 0.0

        for c in partner_clients:
            dep = float(c.get("deposit_usd", 0.0))
            vol = float(c.get("volume_usd", 0.0))
            trades = int(c.get("trade_count", 0))
            hours = float(c.get("deposit_to_withdrawal_hours", 0.0))
            cpa = float(c.get("cpa_collected_usd", 0.0))
            is_active = bool(c.get("active_30d", False))

            total_cpa += cpa

            if 0.0 < hours <= self.fast_withdrawal_threshold_hours:
                fast_withdrawals += 1

            if trades <= self.micro_trade_threshold:
                micro_trades += 1

            if hours > 0.0:
                holding_durations.append(hours)

            t_ratio = vol / max(dep, 1.0)
            turnover_ratios.append(t_ratio)

            if is_active:
                active_30d_count += 1

        fast_withdrawal_rate = fast_withdrawals / total_clients
        active_retention_rate = active_30d_count / total_clients
        mean_turnover = float(np.mean(turnover_ratios)) if turnover_ratios else 0.0
        median_holding = float(np.median(holding_durations)) if holding_durations else 0.0

        # Turnover score normalized: 1.0 if turnover >= 10x deposit, scales smoothly
        turnover_score = min(1.0, mean_turnover / 10.0)

        # Composite Client Quality Index: [0.0, 1.0]
        cqi_raw = (
            (0.45 * active_retention_rate) + (0.35 * turnover_score) - (0.50 * fast_withdrawal_rate)
        )
        # Shift and scale to ensure [0.0, 1.0]
        cqi = max(0.0, min(1.0, cqi_raw + 0.20 * active_retention_rate))
        cqi = round(cqi, 4)

        abuse_prob = round(1.0 - cqi, 4)

        if cqi < 0.20:
            status = "HIGH_BONUS_ABUSE_RISK"
        elif cqi < 0.60:
            status = "MONITORING"
        else:
            status = "NORMAL"

        return BonusAbuseProfile(
            partner_id=partner_id,
            total_referred_clients=total_clients,
            fast_withdrawal_count_72h=fast_withdrawals,
            micro_trade_only_count=micro_trades,
            median_holding_duration_hours=round(median_holding, 2),
            turnover_to_deposit_ratio=round(mean_turnover, 2),
            cpa_bounty_collected_usd=round(total_cpa, 2),
            client_quality_index=cqi,
            abuse_probability=abuse_prob,
            status=status,
        )
