import logging
import cv2
from typing import Any, Dict

from face.metrics.base import SimpleMetric
from face.metrics.geometry import get_3d_distance
from face.metrics.scoring import ScoringConfig

logger = logging.getLogger(__name__)

THEME_COLOR = "#E95870"




LIPS_WIDTH_PAIRS = [
    (61, 291),
]

FACE_EDGE_PAIRS = [
    (234, 454),
]

SCORING_CONFIG = ScoringConfig(
    ideal        = 0.3600,
    tolerance    = 0.0010,
    left_anchor  = (0.0150, 3.25),
    right_anchor = (0.0150, 3.75),
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

    if LIPS_WIDTH_PAIRS:
        _draw_line(annotated, lm, w, h, LIPS_WIDTH_PAIRS[0][0], LIPS_WIDTH_PAIRS[0][1], color_bgr)
        
    if FACE_EDGE_PAIRS:
        _draw_line(annotated, lm, w, h, FACE_EDGE_PAIRS[0][0], FACE_EDGE_PAIRS[0][1], color_bgr)

    _, encoded = cv2.imencode(".jpg", annotated)
    return encoded.tobytes() if encoded is not None else b""

def get_stable_lips_width_metrics(points: Any, w: int, h: int) -> Dict[str, Any]:
    valid_lips = []
    valid_faces = []

    for left_id, right_id in LIPS_WIDTH_PAIRS:
        dist = get_3d_distance(points, left_id, right_id)
        if dist is not None and dist > 0:
            valid_lips.append(dist)

    for left_id, right_id in FACE_EDGE_PAIRS:
        dist = get_3d_distance(points, left_id, right_id)
        if dist is not None and dist > 0:
            valid_faces.append(dist)

    if not valid_lips or not valid_faces:
        return {
            "stable_lips_width": SimpleMetric(name="Lips Width (Average)", value=None),
            "stable_face_width": SimpleMetric(name="Face Width (Average)", value=None),
            "stable_ratio": SimpleMetric(name="Lips to Face Ratio", value=None),
            "point_confidences": []
        }

    avg_lips = sum(valid_lips) / len(valid_lips)
    avg_face = sum(valid_faces) / len(valid_faces)
    avg_ratio = avg_lips / avg_face if avg_face > 0 else 0

    return {
        "stable_lips_width": SimpleMetric(name="Lips Width (Average)", value=round(avg_lips, 2)),
        "stable_face_width": SimpleMetric(name="Face Width (Average)", value=round(avg_face, 2)),
        "stable_ratio": SimpleMetric(name="Lips to Face Ratio", value=round(avg_ratio, 4)),
        "point_confidences": []
    }

FEATURE_CONFIG = {
    "key": "lips_width",
    "title": "Lips to Face Width",
    "label": "Lips / Face Ratio",
    "ratio_key": "stable_ratio",
    "scoring": SCORING_CONFIG,
    "drawer": draw_analysis,
    "theme_color": THEME_COLOR,
}