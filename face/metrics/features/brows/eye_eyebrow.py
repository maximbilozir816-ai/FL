import logging
import cv2
from typing import Any, Dict

from face.metrics.base import SimpleMetric
from face.metrics.geometry import get_3d_distance
from face.metrics.scoring import ScoringConfig

logger = logging.getLogger(__name__)

THEME_COLOR = "#FFFFFF"




EYE_BROW_PAIRS = [
    (159, 52),
    (386, 282),
]

EYE_WIDTH_PAIRS = [
    (33, 133),
    (263, 362),
]

SCORING_CONFIG = ScoringConfig(
    ideal        = 0.4100,
    tolerance    = 0.0005,
    left_anchor  = (0.0800, 3.0),
    right_anchor = (0.1000, 1.5),
    min_score    = 1.0,
)




def _hex_to_bgr(hex_color: str) -> tuple:
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (4, 2, 0))

def _draw_line(img, lm, w, h, p1, p2, color):
    try:
        x1, y1 = int(lm[p1].x * w), int(lm[p1].y * h)
        x2, y2 = int(lm[p2].x * w), int(lm[p2].y * h)
        cv2.line(img, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
    except (IndexError, AttributeError):
        pass

def draw_analysis(img: Any, lm: Any, w: int, h: int) -> bytes:
    annotated = img.copy()
    color_bgr = _hex_to_bgr(THEME_COLOR)

    if EYE_BROW_PAIRS:
        _draw_line(annotated, lm, w, h, EYE_BROW_PAIRS[0][0], EYE_BROW_PAIRS[0][1], color_bgr)
        _draw_line(annotated, lm, w, h, EYE_BROW_PAIRS[1][0], EYE_BROW_PAIRS[1][1], color_bgr)

    _, encoded = cv2.imencode(".jpg", annotated)
    return encoded.tobytes() if encoded is not None else b""

def get_stable_eye_eyebrow_metrics(points: Any, w: int, h: int) -> Dict[str, Any]:
    valid_distances = []
    valid_widths = []

    for eye_id, brow_id in EYE_BROW_PAIRS:
        dist = get_3d_distance(points, eye_id, brow_id)
        if dist is not None and dist > 0:
            valid_distances.append(dist)

    for outer_id, inner_id in EYE_WIDTH_PAIRS:
        dist = get_3d_distance(points, outer_id, inner_id)
        if dist is not None and dist > 0:
            valid_widths.append(dist)

    if not valid_distances or not valid_widths:
        return {
            "stable_distance": SimpleMetric(name="Eye to Brow Distance", value=None),
            "stable_width": SimpleMetric(name="Eye Width", value=None),
            "stable_ratio": SimpleMetric(name="Brow / Eye Width Ratio", value=None),
            "point_confidences": []
        }

    avg_dist = sum(valid_distances) / len(valid_distances)
    avg_width = sum(valid_widths) / len(valid_widths)
    avg_ratio = avg_dist / avg_width if avg_width > 0 else 0

    return {
        "stable_distance": SimpleMetric(name="Eye to Brow Distance", value=round(avg_dist, 2)),
        "stable_width": SimpleMetric(name="Eye Width", value=round(avg_width, 2)),
        "stable_ratio": SimpleMetric(name="Brow / Eye Width Ratio", value=round(avg_ratio, 4)),
        "point_confidences": []
    }

FEATURE_CONFIG = {
    "key": "eye_eyebrow",
    "title": "Eye to Eyebrow Distance",
    "label": "Brow / Eye Width Ratio",
    "ratio_key": "stable_ratio",
    "scoring": SCORING_CONFIG,
    "drawer": draw_analysis,
    "theme_color": THEME_COLOR,
}