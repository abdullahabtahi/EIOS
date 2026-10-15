"""Capabilities served from the warm tier (docs/warm-tier.md): history beyond the hot window, through named queries."""

from datetime import timedelta

from pydantic import Field

from eios.common.validation import StrictModel
from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.common import envelope
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode, ToolResult
from eios.ontology.omcp.port.entities import EntityKind
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import Handler, ToolSpec
from eios.warm.store import WarmError, WarmQueryRefused, WarmUnavailable

AML = (Workstation.AML_INVESTIGATOR,)
PRIVATE = (SecurityMarking.PII, SecurityMarking.SENSITIVE_COMPLIANCE)
MAX_HISTORY_DAYS = 90  # [ASSUMPTION] bounds the series the model reads and the bytes a query scans


class HistoryArgs(StrictModel):
    entity_id: str
    days: int = Field(default=30, ge=1, le=MAX_HISTORY_DAYS)


class DayActivity(StrictModel):
    day: str
    deposits_usd: float
    withdrawals_usd: float
    transactions: int


class AccountHistory(ToolResult):
    window_days: int
    active_days: int
    total_deposits_usd: float
    total_withdrawals_usd: float
    total_transactions: int
    busiest_day: str | None
    busiest_day_deposits_usd: float | None
    days: list[DayActivity]


def get_account_history(ctx: ReadModels, _who: Principal, args: HistoryArgs) -> AccountHistory:
    entity_id = ctx.directory.resolve(args.entity_id, EntityKind.ACCOUNT).entity_id
    if ctx.warm is None:
        raise PortError(ToolErrorCode.DATA_UNAVAILABLE, "the warm tier is not configured here")
    now = ctx.clock()
    start = now - timedelta(days=args.days)
    end = now + timedelta(
        days=1
    )  # a day of allowance: the world stamps a few story events just after its as-of
    try:
        result = ctx.warm.run(
            "account_daily_activity",
            {"client_id": entity_id, "start": start.isoformat(), "end": end.isoformat()},
        )
    except WarmUnavailable as exc:
        raise PortError(ToolErrorCode.DATA_UNAVAILABLE, str(exc)) from exc
    except WarmQueryRefused as exc:  # a bug or an over-large window: say so, never guess
        raise PortError(ToolErrorCode.INVALID_ARGUMENTS, str(exc)) from exc
    except WarmError as exc:
        raise PortError(ToolErrorCode.DATA_UNAVAILABLE, str(exc)) from exc
    days = [
        DayActivity(
            day=str(r["day"]),
            deposits_usd=float(r["deposits"]),
            withdrawals_usd=float(r["withdrawals"]),
            transactions=int(r["transactions"]),
        )
        for r in result.rows
    ]
    busiest = max(days, key=lambda d: d.deposits_usd, default=None)
    return AccountHistory(
        **envelope(
            ctx,
            "aml.history",
            entity_id,
            result.source,
            {
                "window_days": "days",
                "active_days": "days",
                "total_deposits_usd": "USD",
                "total_withdrawals_usd": "USD",
                "total_transactions": "count",
                "busiest_day_deposits_usd": "USD",
                "days[].deposits_usd": "USD",
                "days[].withdrawals_usd": "USD",
                "days[].transactions": "count",
            },
            PRIVATE,
            origin=ctx.aml_origin,  # the rows are the AML plane's world, loaded through the pipeline; `source` names the table
        ),
        window_days=args.days,
        active_days=len(days),
        total_deposits_usd=round(sum(d.deposits_usd for d in days), 2),
        total_withdrawals_usd=round(sum(d.withdrawals_usd for d in days), 2),
        total_transactions=sum(d.transactions for d in days),
        busiest_day=busiest.day if busiest and busiest.deposits_usd > 0 else None,
        busiest_day_deposits_usd=busiest.deposits_usd
        if busiest and busiest.deposits_usd > 0
        else None,
        days=days,
    )


_HANDLER: Handler = get_account_history

TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="get_account_history",
        capability="aml.history",
        kind="evidence",
        workstations=AML,
        args_model=HistoryArgs,
        result_model=AccountHistory,
        handler=_HANDLER,
        budget_ms=3000.0,
        markings=PRIVATE,
    ),
)
