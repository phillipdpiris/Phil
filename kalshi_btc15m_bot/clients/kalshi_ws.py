from __future__ import annotations
import json, time
from dataclasses import dataclass
from typing import Any, Iterator
from websocket import WebSocket, create_connection
from ..config import BotConfig
from .kalshi_rest import build_auth_headers

@dataclass(slots=True)
class KalshiWebSocketClient:
    cfg: BotConfig
    ws: WebSocket

    @classmethod
    def connect(cls, cfg: BotConfig) -> "KalshiWebSocketClient":
        headers = build_auth_headers(cfg, "GET", "/trade-api/ws/v2")
        header_lines = [f"{k}: {v}" for k, v in headers.items() if k != "Content-Type"]
        ws = create_connection(cfg.ws_url, header=header_lines, timeout=15)
        return cls(cfg=cfg, ws=ws)

    def send_json(self, payload: dict[str, Any]) -> None:
        self.ws.send(json.dumps(payload))

    def recv_json(self) -> dict[str, Any]:
        return json.loads(self.ws.recv())

    def subscribe_orderbook(self, market_ticker: str) -> int:
        request_id = int(time.time() * 1000)
        self.send_json({"id": request_id, "cmd": "subscribe",
                        "params": {"channels": ["orderbook_delta"], "market_tickers": [market_ticker]}})
        while True:
            msg = self.recv_json()
            if msg.get("type") == "error" and msg.get("id") == request_id:
                raise RuntimeError(f"WS subscribe error: {msg}")
            if msg.get("type") == "subscribed" and msg.get("id") == request_id:
                sid = msg.get("msg", {}).get("sid")
                if not isinstance(sid, int):
                    raise RuntimeError(f"WS subscribed without valid sid: {msg}")
                return sid

    def get_snapshot(self, sid: int, market_ticker: str) -> int:
        request_id = int(time.time() * 1000)
        self.send_json({"id": request_id, "cmd": "update_subscription",
                        "params": {"sids": [sid], "market_tickers": [market_ticker], "action": "get_snapshot"}})
        return request_id

    def iter_messages(self) -> Iterator[dict[str, Any]]:
        while True:
            yield self.recv_json()

    def close(self) -> None:
        self.ws.close()
