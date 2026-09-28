from typing import Optional
from dataclasses import dataclass


@dataclass
class SimpleMetric:
    name: str
    value: Optional[float]
    unit: str = "px"
    confidence: float = 1.0


@dataclass
class PointConfidence:
    point_id: int
    confidence: int
