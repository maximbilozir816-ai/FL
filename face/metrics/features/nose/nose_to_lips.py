import logging
import cv2
from typing import Any, Dict

from face.metrics.base import SimpleMetric
from face.metrics.geometry import get_3d_distance
from face.metrics.scoring import ScoringConfig

logger = logging.getLogger(__name__)

THEME_COLOR = "#F97316"




NOSE_WIDTH_PAIRS = [
    (64, 294),
]

LIPS_WIDTH_PAIRS = [
    (61, 291),
]

SCORING_CONFIG = ScoringConfig(
    ideal        = 0.7700,
    tolerance    = 0.0010,
    left_anchor  = (0.0350, 3.75),
    right_anchor = (0.0350, 3.75),
    min_score    = 1.0,
)




def _hex_to_bgr(hex_color: str) -> tuple:
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (4, 2, 0))

def draw_dashed_line(img, pt1, pt2, color, thickness=1, dash_length=8):
    x1, y1 = pt1
    x2, y2 = pt2
    dist = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
    if dist == 0: return
    dashes = int(dist / dash_length)
    for i in range(dashes):
        if i % 2 == 0:
            start = (int(x1 + (x2 - x1) * i / dashes), int(y1 + (y2 - y1) * i / dashes))
            end = (int(x1 + (x2 - x1) * (i + 1) / dashes), int(y1 + (y2 - y1) * (i + 1) / dashes))
            cv2.line(img, start, end, color, thickness, cv2.LINE_AA)

def _draw_line(img, lm, w, h, p1, p2, color):
    try:
        x1, y1 = int(lm[p1].x * w), int(lm[p1].y * h)
        x2, y2 = int(lm[p2].x * w), int(lm[p2].y * h)
        draw_dashed_line(img, (x1, y1), (x2, y2), color, 2, 8)
    except (IndexError, AttributeError):
        pass

def draw_analysis(img: Any, lm: Any, w: int, h: int) -> bytes:
    annotated = img.copy()
    color_bgr = _hex_to_bgr(THEME_COLOR)

    if NOSE_WIDTH_PAIRS:
        _draw_line(annotated, lm, w, h, NOSE_WIDTH_PAIRS[0][0], NOSE_WIDTH_PAIRS[0][1], color_bgr)
        
    if LIPS_WIDTH_PAIRS:
        _draw_line(annotated, lm, w, h, LIPS_WIDTH_PAIRS[0][0], LIPS_WIDTH_PAIRS[0][1], color_bgr)

    _, encoded = cv2.imencode(".jpg", annotated)
    return encoded.tobytes() if encoded is not None else b""

def get_stable_nose_to_lips_metrics(points: Any, w: int, h: int) -> Dict[str, Any]:
    valid_nose = []
    valid_lips = []

    for left_id, right_id in NOSE_WIDTH_PAIRS:
        dist = get_3d_distance(points, left_id, right_id)
        if dist is not None and dist > 0:
            valid_nose.append(dist)

    for left_id, right_id in LIPS_WIDTH_PAIRS:
        dist = get_3d_distance(points, left_id, right_id)
        if dist is not None and dist > 0:
            valid_lips.append(dist)

    if not valid_nose or not valid_lips:
        return {
            "stable_nose_width": SimpleMetric(name="Nose Width (Average)", value=None),
            "stable_lips_width": SimpleMetric(name="Lips Width (Average)", value=None),
            "stable_ratio": SimpleMetric(name="Nose to Lips Ratio", value=None),
            "point_confidences": []
        }

    avg_nose = sum(valid_nose) / len(valid_nose)
    avg_lips = sum(valid_lips) / len(valid_lips)
    avg_ratio = avg_nose / avg_lips if avg_lips > 0 else 0

    return {
        "stable_nose_width": SimpleMetric(name="Nose Width (Average)", value=round(avg_nose, 2)),
        "stable_lips_width": SimpleMetric(name="Lips Width (Average)", value=round(avg_lips, 2)),
        "stable_ratio": SimpleMetric(name="Nose to Lips Ratio", value=round(avg_ratio, 4)),
        "point_confidences": []
    }

FEATURE_CONFIG = {
    "key": "nose_to_lips",
    "title": "Nose to Lips Ratio",
    "label": "Nose / Lips Width Ratio",
    "ratio_key": "stable_ratio",
    "scoring": SCORING_CONFIG,
    "drawer": draw_analysis,
    "theme_color": THEME_COLOR,
}