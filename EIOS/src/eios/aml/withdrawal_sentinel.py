"""Real-Time Pre-Withdrawal Sentinel & Action Intent Proposal Emitter (US2 / P1).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4, §6.1
- specs/010-client-aml/spec.md (User Story 2)
- .specify/memory/constitution.md (Principles I, II)

Evaluates withdrawal transactions in real time (< 2.0s p95 latency) and emits
Cloud KMS ECDSA P-256 signed HoldWithdrawal / FreezeAccount proposals in PENDING status.
Never executes mutations autonomously.
"""

import math
import time
import uuid
from datetime import UTC, datetime

from eios.aml.models import (
    WithdrawalDisposition,
    WithdrawalRiskAssessment,
)
from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.intent_hub import ActionIntentHub


def score_withdrawal(
    recent_alert_score: float,
    hours_since_deposit: float,
    market_risk_pct: float,
    hours_since_kyc: float,
) -> float:
    """The composite withdrawal risk score in [0.01, 0.99]. Pure: no intent is proposed and nothing is stored."""
    # Velocity penalty: funds leaving within 12-24h of deposit
    if hours_since_deposit <= 24.0:
        turnaround_risk = math.exp(-hours_since_deposit / 12.0)
    else:
        turnaround_risk = 0.05

    # Micro-risk trading penalty: zero risk taken before withdrawal
    if market_risk_pct <= 0.01:
        wash_risk = 1.0 - (market_risk_pct / 0.01)
    else:
        wash_risk = 0.0

    # KYC Recency factor
    kyc_factor = 1.3 if hours_since_kyc <= 72.0 else 1.0

    raw_score = (0.45 * recent_alert_score + 0.30 * turnaround_risk + 0.25 * wash_risk) * kyc_factor
    return round(min(0.99, max(0.01, raw_score)), 4)


class WithdrawalSentinel:
    """Real-time withdrawal intervention engine."""

    def __init__(
        self,
        hot_state: HotStateEngine | None = None,
        intent_hub: ActionIntentHub | None = None,
        hold_risk_threshold: float = 0.80,
    ) -> None:
        self.hot_state = hot_state
        self.intent_hub = intent_hub or ActionIntentHub()
        self.hold_risk_threshold = hold_risk_threshold

    def evaluate_withdrawal(
        self,
        withdrawal_id: str,
        client_id: str,
        amount_usd: float,
        recent_alert_score: float = 0.20,
        hours_since_deposit: float = 72.0,
        market_risk_pct: float = 0.15,
        hours_since_kyc: float = 500.0,
    ) -> WithdrawalRiskAssessment:
        """Evaluate real-time risk of an inbound withdrawal request."""
        start_time = time.perf_counter()

        risk_score = score_withdrawal(
            recent_alert_score=recent_alert_score,
            hours_since_deposit=hours_since_deposit,
            market_risk_pct=market_risk_pct,
            hours_since_kyc=hours_since_kyc,
        )

        # 2. Decision Formulation & Action Intent Emission
        intent_id: str | None = None
        if risk_score >= self.hold_risk_threshold:
            recommendation = WithdrawalDisposition.PROPOSE_HOLD
            action_type = "HoldWithdrawal"

            # Propose Action Intent via IntentHub (Principle II)
            token = self.intent_hub.propose_action(
                action_type=action_type,
                parameters={
                    "txn_id": withdrawal_id,
                    "reason": f"Acute money laundering indicators (risk={risk_score:.2f}, turnaround={hours_since_deposit:.1f}h)",
                    "amount": amount_usd,
                },
                evidence_refs=[f"txn:{withdrawal_id}", f"client:{client_id}"],
                requester_agent_id="WithdrawalSentinel",
            )
            intent_id = token.intent_id
        else:
            recommendation = WithdrawalDisposition.ALLOW

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        now_dt = datetime.now(UTC)

        assessment = WithdrawalRiskAssessment(
            assessment_id=f"WRA-{uuid.uuid4().hex[:8].upper()}",
            withdrawal_id=withdrawal_id,
            client_id=client_id,
            amount_usd=amount_usd,
            risk_score=risk_score,
            recommendation=recommendation,
            decision_latency_ms=round(latency_ms, 2),
            intent_id=intent_id,
            evaluated_at=now_dt,
        )

        # 3. Persist to Hot State
        if self.hot_state:
            self._persist_assessment(assessment)

        return assessment

    def _persist_assessment(self, assessment: WithdrawalRiskAssessment) -> None:
        """Persist assessment record to DuckDB aml_withdrawal_assessments."""
        if not self.hot_state:
            return
        cursor = self.hot_state.get_cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO aml_withdrawal_assessments (
                assessment_id, withdrawal_id, client_id, amount_usd, risk_score,
                recommendation, decision_latency_ms, intent_id, evaluated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                assessment.assessment_id,
                assessment.withdrawal_id,
                assessment.client_id,
                assessment.amount_usd,
                assessment.risk_score,
                assessment.recommendation.value,
                assessment.decision_latency_ms,
                assessment.intent_id,
                assessment.evaluated_at.strftime("%Y-%m-%d %H:%M:%S"),
            ],
        )
