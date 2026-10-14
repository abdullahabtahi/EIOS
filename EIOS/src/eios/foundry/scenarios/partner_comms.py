"""Partner messages: routine traffic for everyone, plus what a planted driver makes a partner write.

Texts are synthetic and stand in for the communications feed. Downstream they are untrusted text: the port quotes
them as excerpts and never follows them. Rivals are generic aliases; no real firm is named.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from eios.foundry.scenarios.partner_config import Driver, PartnerWorldConfig
from eios.foundry.scenarios.partner_signals import first_day

COMMS_COLUMNS = ("message_id", "partner_id", "channel", "sentiment", "topic", "text", "timestamp")
_RIVAL_FALLBACK = "Competitor Beta"
_CHANNELS = ("EMAIL", "TELEGRAM", "WHATSAPP", "TICKET")
_ROUTINE = (
    (
        "NEUTRAL",
        "creative_request",
        "Could you send the updated landing pages for this month's campaign?",
    ),
    ("POSITIVE", "thanks", "Thanks for the quick help with the tracking link last week."),
    ("NEUTRAL", "report_question", "Where can I download the monthly sub-affiliate report?"),
)
_BY_DRIVER: dict[str, tuple[tuple[str, str, str], ...]] = {
    Driver.CASHIER.value: (
        (
            "NEGATIVE",
            "payout_delay",
            "My clients' withdrawals are still pending after two days. This is hurting my reputation.",
        ),
        (
            "ESCALATED",
            "payout_delay",
            "Third payout ticket this week with no answer. My traders are asking where their money is.",
        ),
        (
            "NEGATIVE",
            "payout_delay",
            "The local payment rail keeps failing on withdrawals; clients are moving their deposits.",
        ),
    ),
    Driver.POACHING.value: (
        (
            "NEGATIVE",
            "rival_offer",
            "{rival} is offering my sub-affiliates a higher revenue share and tighter spreads.",
        ),
        (
            "NEGATIVE",
            "rival_offer",
            "{rival} sent my team a contract with a better rebate per lot. Can you match it?",
        ),
    ),
    Driver.REBATE.value: (
        (
            "ESCALATED",
            "rebate_mismatch",
            "The rebate on last month's statement is lower than our agreement. Please reconcile.",
        ),
        (
            "NEGATIVE",
            "rebate_mismatch",
            "Commission for the synthetic indices volume was cut without notice.",
        ),
    ),
    Driver.SEASONAL.value: (
        (
            "NEUTRAL",
            "holiday_notice",
            "Our desk is on holiday for a week; activity will pick up when we are back.",
        ),
    ),
}
# Hard negatives: a stable partner who complains, or mentions a rival and stays. [ASSUMPTION] shares
_STABLE_NOISE = (
    (
        0.15,
        (
            "NEGATIVE",
            "payout_delay",
            "One withdrawal took longer than usual yesterday; please check it.",
        ),
    ),
    (
        0.08,
        (
            "NEUTRAL",
            "rival_offer",
            "{rival} approached my team last month; we are happy here and staying.",
        ),
    ),
)
_SILENT_SHARE = 0.3  # churners who never write before they leave
_ROUTINE_RATE = 3.0
_PLANTED_COUNT = {
    Driver.CASHIER.value: (2, 4),
    Driver.POACHING.value: (1, 3),
    Driver.REBATE.value: (2, 3),
    Driver.SEASONAL.value: (1, 1),
}


def _at(config: PartnerWorldConfig, day: int, rng: np.random.Generator) -> datetime:
    start = datetime.combine(first_day(config), datetime.min.time(), tzinfo=config.as_of.tzinfo)
    at = start + timedelta(days=day, hours=float(rng.uniform(7.0, 21.0)))
    return min(at, config.as_of - timedelta(minutes=5)).replace(
        tzinfo=None
    )  # naive UTC, as hot state stores it


def partner_messages(
    row: pd.Series, config: PartnerWorldConfig, rng: np.random.Generator
) -> list[dict[str, object]]:
    pid, driver, onset = str(row["partner_id"]), str(row["driver"]), int(row["onset_day"])
    last = config.history_days - 1
    picks: list[tuple[int, tuple[str, str, str]]] = [
        (int(rng.integers(0, last + 1)), _ROUTINE[int(rng.integers(len(_ROUTINE)))])
        for _ in range(int(rng.poisson(_ROUTINE_RATE)))
    ]
    if driver in (Driver.STABLE.value, Driver.GROWING.value):
        picks.extend(
            (int(rng.integers(0, last + 1)), template)
            for share, template in _STABLE_NOISE
            if rng.random() < share
        )
    silent = driver != Driver.SEASONAL.value and rng.random() < _SILENT_SHARE
    if driver in _BY_DRIVER and not silent:
        low, high = _PLANTED_COUNT[driver]
        templates = _BY_DRIVER[driver]
        first = max(onset - 1, 0) if driver == Driver.SEASONAL.value else onset
        for i in range(int(rng.integers(low, high + 1))):
            day = min(first + int(rng.integers(0, max(last - first, 1) + 1)), last)
            picks.append((day, templates[i % len(templates)]))
    picks.sort(key=lambda p: p[0])
    return [
        {
            "message_id": f"MSG-{pid}-{i + 1:02d}",
            "partner_id": pid,
            "channel": _CHANNELS[int(rng.integers(len(_CHANNELS)))],
            "sentiment": sentiment,
            "topic": topic,
            "text": text.format(rival=row["competitor"] or _RIVAL_FALLBACK),
            "timestamp": _at(config, day, rng),
        }
        for i, (day, (sentiment, topic, text)) in enumerate(picks)
    ]
