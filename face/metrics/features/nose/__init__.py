from typing import Dict, Any

from face.metrics.features.nose.nose_height import get_stable_nose_height_metrics, FEATURE_CONFIG as nose_height_cfg
from face.metrics.features.nose.nose_width import get_stable_nose_width_metrics, FEATURE_CONFIG as nose_width_cfg
from face.metrics.features.nose.nose_to_lips import get_stable_nose_to_lips_metrics, FEATURE_CONFIG as nose_to_lips_cfg

ACTIVE_NOSE_METRICS = [
    nose_height_cfg,
    nose_width_cfg,
    nose_to_lips_cfg,
]

def get_all_nose_metrics(points: Any, w: int, h: int) -> Dict[str, Dict[str, Any]]:
    return {
        "nose_height": get_stable_nose_height_metrics(points, w, h),
        "nose_width": get_stable_nose_width_metrics(points, w, h),
        "nose_to_lips": get_stable_nose_to_lips_metrics(points, w, h),
    }

__all__ = ["ACTIVE_NOSE_METRICS", "get_all_nose_metrics"]