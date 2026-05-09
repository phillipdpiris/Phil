from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import BotConfig
from .models import BotState


@dataclass(slots=True)
class RemotePositionView:
    side: str | None
    contracts: int


def _extract_remote_position(payload: dict[str, Any], ticker: str) -> RemotePositionView:
    for mp in payload.get("market_positions", []) or []:
        if mp.get("ticker") != ticker:
            continue
        raw_position = int(mp.get("position") or 0)
        if raw_position > 0:
            return RemotePositionView(side="yes", contracts=raw_position)
        if raw_position < 0:
            return RemotePositionView(side="no", contracts=abs(raw_position))
        return RemotePositionView(side=None, contracts=0)
    return RemotePositionView(side=None, contracts=0)


def reconcile_position_state(rest, state: BotState, ticker: str, logger) -> bool:
    cfg: BotConfig = rest.cfg
    if cfg.dry_run or cfg.kalshi_env != "prod":
        return True
    meta = state.metadata.setdefault("reconciliation", {})
    try:
        payload = rest.auth_get("/portfolio/positions", params={"ticker": ticker, "count_filter": "position"})
    except Exception as exc:
        logger.error("Position reconciliation failed; blocking auto-trading: %s", exc)
        meta.update({"status": "error", "error": str(exc)})
        return False
    remote = _extract_remote_position(payload, ticker)
    local = state.position
    meta.update({"remote_ticker": ticker, "remote_side": remote.side, "remote_contracts": remote.contracts,
                 "local_side": getattr(local, "side", None), "local_contracts": getattr(local, "contracts", 0)})
    if local is None and remote.contracts == 0:
        meta["status"] = "ok"
        return True
    if local is None and remote.contracts > 0:
        meta["status"] = "mismatch_remote_only"
        return False
    if local is not None and remote.contracts == 0:
        meta["status"] = "mismatch_local_only"
        return False
    assert local is not None
    if local.side == remote.side and local.contracts == remote.contracts:
        meta["status"] = "ok"
        return True
    meta["status"] = "mismatch_both"
    return False
