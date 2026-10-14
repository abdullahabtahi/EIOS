"""Row builders and frame assembly for the AML world (spec 031 FR-001).

Rows are plain dicts built by pure functions; frames are assembled once, sorted, and given stable ids so the same
config always produces the same bytes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

TXN_COLUMNS = (
    "txn_id",
    "client_id",
    "transaction_type",
    "amount",
    "currency",
    "asset",
    "payment_token",
    "timestamp",
    "kyc_approved_at",
    "status",
    "reference",
)
TRADE_COLUMNS = (
    "trade_id",
    "client_id",
    "symbol",
    "side",
    "volume_lots",
    "profit_loss",
    "open_ts",
    "close_ts",
    "timestamp",
    "amount",
)
EDGE_COLUMNS = ("source_id", "target_id", "edge_type", "is_shared_context")
PAYMENT, DEVICE, IP_ADDRESS = "PAYMENT_TOKEN", "DEVICE_FINGERPRINT", "IP_ADDRESS"
DEPOSIT, WITHDRAWAL = "DEPOSIT", "WITHDRAWAL"
COMPLETED, PENDING = "COMPLETED", "PENDING"
SYMBOLS = ("EURUSD", "GBPUSD", "XAUUSD", "BTCUSD", "Volatility 75 Index", "Volatility 100 Index")
_PIP_NOTIONAL = 100.0


def txn_row(  # noqa: PLR0913
    client_id: str,
    kind: str,
    amount: float,
    at: datetime | pd.Timestamp,
    *,
    kyc: pd.Timestamp,
    asset: str = "CARD",
    payment_token: str = "",
    status: str = COMPLETED,
    reference: str = "",
) -> dict[str, Any]:
    return {
        "client_id": client_id,
        "transaction_type": kind,
        "amount": round(float(amount), 2),
        "currency": "USD",
        "asset": asset,
        "payment_token": payment_token,
        "timestamp": pd.Timestamp(at),
        "kyc_approved_at": kyc,
        "status": status,
        "reference": reference,
    }


def trade_row(
    client_id: str,
    open_ts: datetime | pd.Timestamp,
    seconds: float,
    pnl: float,
    symbol: str,
    lots: float,
) -> dict[str, Any]:
    opened = pd.Timestamp(open_ts)
    return {
        "client_id": client_id,
        "symbol": symbol,
        "side": "BUY" if pnl >= 0 else "SELL",
        "volume_lots": round(float(lots), 2),
        "profit_loss": round(float(pnl), 4),
        "open_ts": opened,
        "close_ts": opened + timedelta(seconds=float(seconds)),
        "timestamp": opened,
        "amount": round(float(lots) * _PIP_NOTIONAL, 2),
    }


def edge_row(
    client_id: str, token_id: str, edge_type: str, *, shared_context: bool = False
) -> dict[str, Any]:
    return {
        "source_id": client_id,
        "target_id": token_id,
        "edge_type": edge_type,
        "is_shared_context": shared_context,
    }


def transactions_frame(rows: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows), columns=[c for c in TXN_COLUMNS if c != "txn_id"])
    frame = frame.sort_values(["timestamp", "client_id", "transaction_type"], kind="stable")
    frame = frame.reset_index(drop=True)
    frame.insert(0, "txn_id", [f"TX-{i + 1:07d}" for i in range(len(frame))])
    return frame.loc[:, list(TXN_COLUMNS)]


def trades_frame(rows: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows), columns=[c for c in TRADE_COLUMNS if c != "trade_id"])
    frame = frame.sort_values(["open_ts", "client_id"], kind="stable").reset_index(drop=True)
    frame.insert(0, "trade_id", [f"TR-{i + 1:07d}" for i in range(len(frame))])
    return frame.loc[:, list(TRADE_COLUMNS)]


def edges_frame(rows: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows), columns=list(EDGE_COLUMNS))
    return (
        frame.drop_duplicates()
        .sort_values(["target_id", "source_id"], kind="stable")
        .reset_index(drop=True)
    )
