from typing import Dict, Any

from face.metrics.features.brows.eye_eyebrow import get_stable_eye_eyebrow_metrics, FEATURE_CONFIG as eye_eyebrow_cfg
from face.metrics.features.brows.eyebrow_density import get_stable_eyebrow_density_metrics, FEATURE_CONFIG as eyebrow_density_cfg
from face.metrics.features.brows.eyebrow_tilt import get_stable_eyebrow_tilt_metrics, FEATURE_CONFIG as eyebrow_tilt_cfg

ACTIVE_BROWS_METRICS = [
    eye_eyebrow_cfg,
    eyebrow_density_cfg,
    eyebrow_tilt_cfg,
]

def get_all_brows_metrics(points: Any, w: int, h: int) -> Dict[str, Dict[str, Any]]:
    return {
        "eye_eyebrow": get_stable_eye_eyebrow_metrics(points, w, h),
        "eyebrow_density": get_stable_eyebrow_density_metrics(points, w, h),
        "eyebrow_tilt": get_stable_eyebrow_tilt_metrics(points, w, h),
    }

__all__ = ["ACTIVE_BROWS_METRICS", "get_all_brows_metrics"]