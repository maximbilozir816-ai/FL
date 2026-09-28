# face/metrics/geometry.py
"""
Distance and angle processing helpers.
These operate on an already-frontalized numpy.ndarray (shape [478, 3], pixel-scaled).
"""

import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

def get_3d_distance(points: np.ndarray, p1_id: int, p2_id: int) -> Optional[float]:
    """Planar (X, Y) distance between two landmarks in a frontalized point cloud."""
    try:
        diff = points[p2_id, :2] - points[p1_id, :2]
        return round(float(np.linalg.norm(diff)), 2)
    except (IndexError, TypeError):
        return None

def get_z_difference(points: np.ndarray, p1_id: int, p2_id: int) -> Optional[float]:
    """Absolute depth (z) difference between two landmarks."""
    try:
        return float(abs(points[p2_id, 2] - points[p1_id, 2]))
    except (IndexError, TypeError):
        return None

def get_angle_2d(points: np.ndarray, p1_id: int, vertex_id: int, p2_id: int) -> Optional[float]:
    """Planar (X, Y) angle in degrees between vectors (vertex -> p1) and (vertex -> p2)."""
    try:
        v1 = points[p1_id, :2] - points[vertex_id, :2]
        v2 = points[p2_id, :2] - points[vertex_id, :2]
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return None
        cos_angle = np.dot(v1, v2) / (norm_v1 * norm_v2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        return round(float(np.degrees(np.arccos(cos_angle))), 2)
    except (IndexError, TypeError):
        return None