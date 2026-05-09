from __future__ import annotations

def phase1_weights(context: dict) -> dict:
    continuation_bias = context.get("open_mid_continuation_rate", 0.5) - 0.5
    reversal_bias = context.get("mid_close_reversal_rate", 0.5) - 0.5
    return {
        "momentum": max(0.35, min(0.75, 0.58 + continuation_bias * 0.50 - reversal_bias * 0.15)),
        "meanrev": max(0.10, min(0.40, 0.22 - continuation_bias * 0.35)),
        "mispricing": 0.20, "time": 0.0,
    }

def phase2_weights(context: dict) -> dict:
    return {"momentum": 0.25, "meanrev": 0.15, "mispricing": 0.60, "time": 0.0}

def phase3_weights(context: dict) -> dict:
    return {"momentum": 0.15, "meanrev": 0.10, "mispricing": 0.20, "time": 0.55}

def final_minute_weights(context: dict) -> dict:
    return {"momentum": 0.15, "meanrev": 0.0, "mispricing": 0.25, "time": 0.60}
