import math
from dataclasses import dataclass

PHASE1_SHRINKAGE_FACTOR = 0.70

class ProbabilityError(ValueError):
    pass

@dataclass
class ShrinkageResult:
    p_raw: float
    p_shrunk: float
    shrinkage_factor: float

def apply_shrinkage(p_raw: float, shrinkage_factor: float = PHASE1_SHRINKAGE_FACTOR) -> ShrinkageResult:
    if p_raw is None:
        raise ProbabilityError("p_raw is None")
    if math.isnan(p_raw) or math.isinf(p_raw):
        raise ProbabilityError(f"p_raw={p_raw!r} is NaN or infinite")
    if not (0.0 <= p_raw <= 1.0):
        raise ProbabilityError(f"p_raw={p_raw} is outside valid range [0.0, 1.0]")
    p_shrunk = 0.5 + (p_raw - 0.5) * shrinkage_factor
    return ShrinkageResult(p_raw=p_raw, p_shrunk=p_shrunk, shrinkage_factor=shrinkage_factor)
