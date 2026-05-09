import math
from dataclasses import dataclass
from typing import Optional

class LatencyError(ValueError):
    pass

@dataclass
class ProbabilityLatencyResult:
    p_input: float
    p_latency: float
    delta_t_seconds: float
    tau_seconds: float
    lambda_prob: float

@dataclass
class FillLatencyResult:
    p_fill_base: float
    p_fill_adjusted: float
    delta_t_seconds: float
    lambda_fill: float

def adjust_probability_for_latency(p_input, delta_t_seconds, tau_seconds,
                                    lambda_prob=1.0, tau_floor_seconds=60.0):
    if math.isnan(p_input) or math.isinf(p_input):
        raise LatencyError(f"p_input={p_input!r} is NaN or infinite")
    if not (0.0 <= p_input <= 1.0):
        raise LatencyError(f"p_input={p_input} outside [0,1]")
    if delta_t_seconds < 0:
        raise LatencyError(f"delta_t_seconds={delta_t_seconds} cannot be negative")
    effective_tau = max(tau_seconds, tau_floor_seconds)
    decay = math.exp(-lambda_prob * delta_t_seconds / effective_tau)
    p_latency = max(0.0, min(1.0, 0.5 + (p_input - 0.5) * decay))
    return ProbabilityLatencyResult(p_input=p_input, p_latency=p_latency,
                                     delta_t_seconds=delta_t_seconds, tau_seconds=effective_tau,
                                     lambda_prob=lambda_prob)

def adjust_fill_probability_for_latency(p_fill_base, delta_t_seconds, lambda_fill=0.10):
    if math.isnan(p_fill_base) or math.isinf(p_fill_base):
        raise LatencyError(f"p_fill_base={p_fill_base!r} is NaN or infinite")
    if not (0.0 <= p_fill_base <= 1.0):
        raise LatencyError(f"p_fill_base={p_fill_base} outside [0,1]")
    if delta_t_seconds < 0:
        raise LatencyError(f"delta_t_seconds={delta_t_seconds} cannot be negative")
    p_fill_adjusted = max(0.0, min(1.0, p_fill_base * math.exp(-lambda_fill * delta_t_seconds)))
    return FillLatencyResult(p_fill_base=p_fill_base, p_fill_adjusted=p_fill_adjusted,
                              delta_t_seconds=delta_t_seconds, lambda_fill=lambda_fill)
