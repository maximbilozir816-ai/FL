#face/metrics/features/__init__.py

from typing import Dict, Any

from face.metrics.features.eye_area.icd import get_stable_icd_metrics, FEATURE_CONFIG as icd_cfg
from face.metrics.features.eye_area.ocd import get_stable_ocd_metrics, FEATURE_CONFIG as ocd_cfg
from face.metrics.features.eye_area.esize import get_stable_esize_metrics, FEATURE_CONFIG as esize_cfg

from face.metrics.features.facialbalance.thirds import get_stable_thirds_metrics, FEATURE_CONFIG as thirds_cfg
from face.metrics.features.facialbalance.fifths import get_stable_fifths_metrics, FEATURE_CONFIG as fifths_cfg
from face.metrics.features.facialbalance.facial_index import get_stable_index_metrics, FEATURE_CONFIG as index_cfg

from face.metrics.features.lips.lips_to_nose import get_stable_lips_to_nose_metrics, FEATURE_CONFIG as lips_to_nose_cfg
from face.metrics.features.lips.lips_width import get_stable_lips_width_metrics, FEATURE_CONFIG as lips_width_cfg
from face.metrics.features.lips.lips_weight import get_stable_lips_weight_metrics, FEATURE_CONFIG as lips_weight_cfg

from face.metrics.features.nose.nose_height import get_stable_nose_height_metrics, FEATURE_CONFIG as nose_height_cfg
from face.metrics.features.nose.nose_width import get_stable_nose_width_metrics, FEATURE_CONFIG as nose_width_cfg
from face.metrics.features.nose.nose_to_lips import get_stable_nose_to_lips_metrics, FEATURE_CONFIG as nose_to_lips_cfg

from face.metrics.features.brows.eye_eyebrow import get_stable_eye_eyebrow_metrics, FEATURE_CONFIG as eye_eyebrow_cfg
from face.metrics.features.brows.eyebrow_density import get_stable_eyebrow_density_metrics, FEATURE_CONFIG as eyebrow_density_cfg
from face.metrics.features.brows.eyebrow_tilt import get_stable_eyebrow_tilt_metrics, FEATURE_CONFIG as eyebrow_tilt_cfg

from face.metrics.features.Dmetrics.fwhr import get_stable_fwhr_metrics, FEATURE_CONFIG as fwhr_cfg
from face.metrics.features.Dmetrics.jaw_facew import get_stable_jaw_facew_metrics, FEATURE_CONFIG as jaw_facew_cfg
from face.metrics.features.Dmetrics.chin_lowerth import get_stable_chin_lowerth_metrics, FEATURE_CONFIG as chin_lowerth_cfg

from face.metrics.scoring import SCORING_REGISTRY, ScoringConfig

ACTIVE_METRICS = [
    icd_cfg,
    ocd_cfg,
    esize_cfg,
    thirds_cfg,
    fifths_cfg,
    index_cfg,
    lips_to_nose_cfg,
    lips_width_cfg,
    lips_weight_cfg,
    nose_height_cfg,
    nose_width_cfg,
    nose_to_lips_cfg,
    eye_eyebrow_cfg,
    eyebrow_density_cfg,
    eyebrow_tilt_cfg,
    fwhr_cfg,
    jaw_facew_cfg,
    chin_lowerth_cfg,
]

for cfg in ACTIVE_METRICS:
    if isinstance(cfg, dict) and "key" in cfg and "scoring" in cfg:
        sc = cfg["scoring"]
        if isinstance(sc, dict):
            valid_keys = {'ideal', 'tolerance', 'left_anchor', 'right_anchor', 'min_score'}
            sc = ScoringConfig(**{k: v for k, v in sc.items() if k in valid_keys})
        SCORING_REGISTRY[cfg["key"]] = sc

def get_all_metrics(points: Any, w: int, h: int) -> Dict[str, Dict[str, Any]]:
    return {
        "icd": get_stable_icd_metrics(points, w, h),
        "ocd": get_stable_ocd_metrics(points, w, h),
        "esize": get_stable_esize_metrics(points, w, h),
        "thirds": get_stable_thirds_metrics(points, w, h),
        "fifths": get_stable_fifths_metrics(points, w, h),
        "facial_index": get_stable_index_metrics(points, w, h),
        "lips_to_nose": get_stable_lips_to_nose_metrics(points, w, h),
        "lips_width": get_stable_lips_width_metrics(points, w, h),
        "lips_weight": get_stable_lips_weight_metrics(points, w, h),
        "nose_height": get_stable_nose_height_metrics(points, w, h),
        "nose_width": get_stable_nose_width_metrics(points, w, h),
        "nose_to_lips": get_stable_nose_to_lips_metrics(points, w, h),
        "eye_eyebrow": get_stable_eye_eyebrow_metrics(points, w, h),
        "eyebrow_density": get_stable_eyebrow_density_metrics(points, w, h),
        "eyebrow_tilt": get_stable_eyebrow_tilt_metrics(points, w, h),
        "fwhr": get_stable_fwhr_metrics(points, w, h),
        "jaw_facew": get_stable_jaw_facew_metrics(points, w, h),
        "chin_lowerth": get_stable_chin_lowerth_metrics(points, w, h),
    }

__all__ = ["ACTIVE_METRICS", "get_all_metrics"]