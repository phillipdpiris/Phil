from __future__ import annotations
from ..clients.kalshi_rest import KalshiRestClient

def get_queue_position(rest: KalshiRestClient, order_id: str) -> int:
    payload = rest.auth_get(f"/portfolio/orders/{order_id}/queue_position")
    return int(payload.get("queue_position", 0))

def get_all_queue_positions(rest: KalshiRestClient) -> dict:
    return rest.auth_get("/portfolio/orders/queue_positions")

def should_reprice(queue_position: int, remaining_seconds: int) -> bool:
    if remaining_seconds <= 30 and queue_position > 0:
        return True
    if remaining_seconds <= 90 and queue_position > 10:
        return True
    return False
