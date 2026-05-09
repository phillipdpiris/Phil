from __future__ import annotations
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

def load_saved_orderbook_stream(path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

@dataclass(slots=True)
class ReplayPosition:
    side: str
    contracts: int
    avg_entry_price_cents: float

@dataclass(slots=True)
class ReplayPnL:
    realized_pnl_cents: float = 0.0
    trades: int = 0
    def as_dict(self):
        avg = self.realized_pnl_cents / self.trades if self.trades > 0 else 0.0
        return {"realized_pnl_cents": self.realized_pnl_cents, "trades": float(self.trades), "avg_pnl_per_trade_cents": avg}

def _price_from_payload(payload):
    return float(payload.get("yes_price") or payload.get("no_price") or 0.0)

def replay_market(session_data, strategy_params=None):
    if strategy_params is None: strategy_params = {}
    positions = {}
    per_market_pnl = defaultdict(ReplayPnL)
    for event in session_data:
        etype = event.get("event_type")
        ticker = event.get("ticker")
        if not ticker: continue
        if etype == "order_submission" and not event.get("skipped"):
            if event.get("mode") != "entry": continue
            payload = event.get("payload") or {}
            side = payload.get("side")
            if side not in {"yes","no"}: continue
            price_cents = _price_from_payload(payload)
            contracts = int(payload.get("count") or 0)
            if contracts <= 0 or price_cents <= 0.0: continue
            pos = positions.get(ticker)
            if pos is None:
                positions[ticker] = ReplayPosition(side=side, contracts=contracts, avg_entry_price_cents=price_cents)
            else:
                if pos.side != side: continue
                total = pos.contracts + contracts
                if total <= 0: continue
                pos.avg_entry_price_cents = (pos.avg_entry_price_cents*pos.contracts + price_cents*contracts)/total
                pos.contracts = total
        elif etype == "exit" and not event.get("skipped"):
            payload = event.get("payload") or {}
            price_cents = _price_from_payload(payload)
            contracts = int(payload.get("count") or 0)
            if contracts <= 0 or price_cents <= 0.0: continue
            pos = positions.get(ticker)
            if pos is None or pos.contracts <= 0: continue
            sell = min(contracts, pos.contracts)
            per_market_pnl[ticker].realized_pnl_cents += (price_cents - pos.avg_entry_price_cents) * sell
            per_market_pnl[ticker].trades += 1
            pos.contracts -= sell
    totals = ReplayPnL()
    market_summaries = {}
    for t, pnl in per_market_pnl.items():
        totals.realized_pnl_cents += pnl.realized_pnl_cents
        totals.trades += pnl.trades
        market_summaries[t] = pnl.as_dict()
    return {"events": len(session_data), "markets": market_summaries, "totals": totals.as_dict(),
            "open_positions": {t: {"side":p.side,"contracts":p.contracts,"avg_entry_price_cents":p.avg_entry_price_cents}
                               for t,p in positions.items() if p.contracts>0},
            "strategy_params": strategy_params, "status": "ok"}

def compare_exit_variants(session_data):
    return {"events": len(session_data), "variants": {"recorded": replay_market(session_data, {"variant":"recorded"})},
            "status": "baseline_only"}
