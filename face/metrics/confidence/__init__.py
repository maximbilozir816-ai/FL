# face/metrics/confidence/__init__.py
from typing import Any, Dict, List
import numpy as np

from .pose import analyze_pose
from .lighting import analyze_lighting


def analyze_total_confidence(lm: Any, w: int, h: int, face_width_px: float, image: np.ndarray = None) -> Dict[str, Any]:
    """
    Runs the pose and lighting Pass/Fail checks and aggregates them into a single
    binary gate result.

    Returns:
        {
            "is_valid": bool,   # True only if BOTH pose and lighting passed
            "reasons": List[str],  # combined list of user-facing rejection reasons
        }
    """
    pose_valid, pose_reasons = analyze_pose(lm, w, h, face_width_px)
    light_valid, light_reasons = analyze_lighting(image, lm, w, h)

    reasons: List[str] = [*pose_reasons, *light_reasons]
    is_valid = pose_valid and light_valid

    return {
        "is_valid": is_valid,
        "reasons": reasons,
    }