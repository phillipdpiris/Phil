from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonlLogger:
    def __init__(self, path: str | Path = "bot_events.jsonl") -> None:
        self.path = Path(path)

    def _write(self, event_type: str, payload: dict[str, Any]) -> None:
        record = {"event_type": event_type, **payload}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def log_market_snapshot(self, payload: dict[str, Any]) -> None:
        self._write("market_snapshot", payload)

    def log_signal_snapshot(self, payload: dict[str, Any]) -> None:
        self._write("signal_snapshot", payload)

    def log_order_submission(self, payload: dict[str, Any]) -> None:
        self._write("order_submission", payload)

    def log_fill(self, payload: dict[str, Any]) -> None:
        self._write("fill", payload)

    def log_exit(self, payload: dict[str, Any]) -> None:
        self._write("exit", payload)

    def log_trade_summary(self, payload: dict[str, Any]) -> None:
        self._write("trade_summary", payload)
