import logging
import cv2
from typing import Any, Dict

from face.metrics.base import SimpleMetric
from face.metrics.geometry import get_3d_distance
from face.metrics.scoring import ScoringConfig

logger = logging.getLogger(__name__)

THEME_COLOR = "#0F8696"  

# ==============================================================================
# ЛОКАЛЬНІ ТОЧКИ ТА КОНФІГУРАЦІЯ ОЦІНЮВАННЯ
# ==============================================================================
EYE_INNER_PAIRS = [
    (133, 362),
]

FACE_EDGE_PAIRS = [
    (234, 454),
]

SCORING_CONFIG = ScoringConfig(
    ideal        = 0.2700,
    tolerance    = 0.0001,
    left_anchor  = (0.0200, 3.25),
    right_anchor = (0.0200, 3.0),
    min_score    = 1.0,
)
# ==============================================================================

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

    if EYE_INNER_PAIRS:
        _draw_line(annotated, lm, w, h, EYE_INNER_PAIRS[0][0], EYE_INNER_PAIRS[0][1], color_bgr)
        
    if FACE_EDGE_PAIRS:
        _draw_line(annotated, lm, w, h, FACE_EDGE_PAIRS[0][0], FACE_EDGE_PAIRS[0][1], color_bgr)

    _, encoded = cv2.imencode(".jpg", annotated)
    return encoded.tobytes() if encoded is not None else b""

def get_stable_icd_metrics(points: Any, w: int, h: int) -> Dict[str, Any]:
    valid_icds = []
    valid_faces = []

    for left_id, right_id in EYE_INNER_PAIRS:
        dist = get_3d_distance(points, left_id, right_id)
        if dist is not None and dist > 0:
            valid_icds.append(dist)

    for left_id, right_id in FACE_EDGE_PAIRS:
        dist = get_3d_distance(points, left_id, right_id)
        if dist is not None and dist > 0:
            valid_faces.append(dist)

    if not valid_icds or not valid_faces:
        return {
            "stable_icd": SimpleMetric(name="ICD (Average)", value=None),
            "stable_face": SimpleMetric(name="Face Width (Average)", value=None),
            "stable_ratio": SimpleMetric(name="Eye Ratio (Average)", value=None),
            "point_confidences": []
        }

    avg_icd = sum(valid_icds) / len(valid_icds)
    avg_face = sum(valid_faces) / len(valid_faces)
    avg_ratio = avg_icd / avg_face if avg_face > 0 else 0

    return {
        "stable_icd": SimpleMetric(name="ICD (Average)", value=avg_icd),
        "stable_face": SimpleMetric(name="Face Width (Average)", value=avg_face),
        "stable_ratio": SimpleMetric(name="Eye Ratio (Average)", value=avg_ratio),
        "point_confidences": []
    }

FEATURE_CONFIG = {
    "key": "icd",
    "title": "Interocular Canthal Distance",
    "label": "ICD / Face Ratio",
    "ratio_key": "stable_ratio",
    "scoring": SCORING_CONFIG,
    "drawer": draw_analysis,
    "theme_color": THEME_COLOR,
}