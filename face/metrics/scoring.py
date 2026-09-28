# face/metrics/scoring.py
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any

def _solve_k(anchor: Tuple[float, float], tolerance: float, min_score: float) -> float:
    anchor_dev, anchor_score = anchor
    net = anchor_dev - tolerance

    if net <= 0:
        raise ValueError(
            f"Anchor deviation ({anchor_dev}) must exceed tolerance ({tolerance}). "
            f"Net deviation = {net}"
        )
    ratio = (anchor_score - min_score) / (10.0 - min_score)
    if not (0.0 < ratio < 1.0):
        raise ValueError(
            f"anchor_score ({anchor_score}) must be strictly between "
            f"min_score ({min_score}) and 10.0 so that ln(ratio) is defined."
        )
    return -math.log(ratio) / (net ** 2)

@dataclass
class ScoringConfig:
    ideal:        float
    tolerance:    float
    left_anchor:  Tuple[float, float]
    right_anchor: Tuple[float, float]
    min_score:    float = 3.0

    _k_left:  float = field(init=False, repr=False)
    _k_right: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._k_left  = _solve_k(self.left_anchor,  self.tolerance, self.min_score)
        self._k_right = _solve_k(self.right_anchor, self.tolerance, self.min_score)

def compute_score(value: float, config: ScoringConfig) -> float:
    raw_dev = value - config.ideal
    net_dev = abs(raw_dev) - config.tolerance

    if net_dev <= 0.0:
        return 10.0

    k   = config._k_left if raw_dev < 0 else config._k_right
    raw = config.min_score + (10.0 - config.min_score) * math.exp(-k * net_dev ** 2)
    return round(max(config.min_score, min(10.0, raw)), 2)

def score_label(score: float) -> str:
    return f"Score: {score:.2f}/10"

# --- ДОДАНО ТУТ ---
# Глобальний реєстр конфігурацій оцінювання для всіх метрик
SCORING_REGISTRY: Dict[str, ScoringConfig] = {}