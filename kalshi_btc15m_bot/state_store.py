from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import BotState, PositionState


def load_state(path: str | Path) -> BotState:
    path = Path(path)
    if not path.exists():
        return BotState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    position = payload.get("position")
    state = BotState(
        position=PositionState(**position) if position else None,
        metadata=payload.get("metadata", {}),
    )
    return state


def save_state(path: str | Path, state: BotState) -> None:
    path = Path(path)
    payload = {
        "position": asdict(state.position) if state.position else None,
        "metadata": state.metadata,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def clear_position(path: str | Path) -> None:
    state = load_state(path)
    state.position = None
    save_state(path, state)
