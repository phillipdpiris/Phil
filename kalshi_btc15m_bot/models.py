from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal


Side = Literal["yes", "no"]
Phase = Literal["phase1", "phase2", "phase3", "final_minute"]


@dataclass(slots=True)
class OrderbookLevel:
    price_cents: float
    size: float


@dataclass(slots=True)
class OrderbookState:
    yes_bids: list[OrderbookLevel] = field(default_factory=list)
    no_bids: list[OrderbookLevel] = field(default_factory=list)
    ts_ms: int | None = None


@dataclass(slots=True)
class MarketSnapshot:
    ticker: str
    title: str
    series_ticker: str
    open_time: Any
    close_time: Any
    status: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PositionState:
    ticker: str
    side: Side
    contracts: int
    avg_entry_price_cents: float
    entry_time_iso: str
    tp1_done: bool = False
    tp2_done: bool = False
    phase_at_entry: str = ""
    simulated: bool = True


@dataclass(slots=True)
class SignalState:
    fair_yes_cents: float
    fair_no_cents: float
    momentum_yes: float
    meanrev_yes: float
    mispricing_yes: float
    time_yes: float
    context: dict[str, Any] = field(default_factory=dict)
    features: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EntryDecision:
    side: Side | None
    confidence: float
    fair_value_cents: float
    target_entry_price_cents: float
    edge_cents: float
    tradable: bool
    reason: str
    order_style: str = "resting_limit"
    contracts: int = 0
    fair_yes_cents: float = 0.0
    fair_no_cents: float = 0.0


@dataclass(slots=True)
class ExitDecision:
    action: Literal["hold", "sell_partial", "sell_all"]
    contracts: int
    target_exit_price_cents: float
    reason: str


@dataclass(slots=True)
class TradeRecord:
    market_ticker: str
    side: Side
    contracts: int
    entry_price_cents: float
    exit_price_cents: float | None
    entry_ts: str
    exit_ts: str | None
    pnl_cents: float | None
    exit_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BotState:
    position: PositionState | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
