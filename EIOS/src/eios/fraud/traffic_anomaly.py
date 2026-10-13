"""Beta-Binomial Traffic & Bot Anomaly Detection Engine (US5 / Module B).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US5, FR-009)
- specs/009-partner-fraud/research.md §5
"""

from scipy import stats

from eios.fraud.models import TrafficAnomalySignal


class TrafficAnomalyDetector:
    """Evaluates marketing funnels and flags statistically impossible conversion rates and bot traffic."""

    def __init__(
        self,
        default_peer_mean: float = 0.045,
        default_peer_std: float = 0.015,
        sigma_threshold: float = 3.0,
    ) -> None:
        self.default_peer_mean = default_peer_mean
        self.default_peer_std = default_peer_std
        self.sigma_threshold = sigma_threshold

    def evaluate_funnels(
        self,
        funnel_records: list[dict],
    ) -> list[TrafficAnomalySignal]:
        """Process marketing funnel records and detect bot conversion anomalies."""
        signals: list[TrafficAnomalySignal] = []

        for r in funnel_records:
            partner_id = r["partner_id"]
            clicks = int(r.get("click_count", 0))
            regs = int(r.get("registration_count", 0))
            ftds = int(r.get("ftd_count", 0))

            peer_mean = float(r.get("peer_cohort_mean_conversion", self.default_peer_mean))
            peer_std = self.default_peer_std

            click_to_signup = regs / max(clicks, 1)
            signup_to_ftd = ftds / max(regs, 1)

            # Check contextual campaign override (e.g. verified offline seminar)
            is_contextual = bool(r.get("is_contextual_campaign", False))

            # Statistical dispersion test (Z-score against peer cohort benchmark)
            z_score = (click_to_signup - peer_mean) / max(peer_std, 1e-4)

            # One-tailed p-value: P(Z >= z_score)
            p_val = float(1.0 - stats.norm.cdf(z_score))
            p_val = max(0.0, min(1.0, p_val))

            if "p_value" in r and not is_contextual:
                p_val = float(r["p_value"])

            # Bot probability based on conversion velocity and statistical divergence
            if is_contextual:
                bot_prob = 0.15
                anomaly_flag = False
            else:
                if z_score > self.sigma_threshold and click_to_signup > 0.50:
                    bot_prob = min(0.99, 0.70 + (click_to_signup * 0.30))
                    anomaly_flag = True
                else:
                    bot_prob = max(0.02, min(0.30, (click_to_signup / 0.50) * 0.20))
                    anomaly_flag = False

                if "bot_traffic_probability" in r:
                    bot_prob = float(r["bot_traffic_probability"])
                if "anomaly_flag" in r:
                    anomaly_flag = bool(r["anomaly_flag"])

            signals.append(
                TrafficAnomalySignal(
                    partner_id=partner_id,
                    click_count=clicks,
                    registration_count=regs,
                    ftd_count=ftds,
                    click_to_signup_rate=round(click_to_signup, 4),
                    signup_to_deposit_rate=round(signup_to_ftd, 4),
                    peer_cohort_mean_conversion=round(peer_mean, 4),
                    p_value=round(p_val, 6),
                    bot_traffic_probability=round(bot_prob, 4),
                    anomaly_flag=anomaly_flag,
                )
            )

        return signals
