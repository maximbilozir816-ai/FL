import logging
import cv2
from typing import Any, Dict
from face.metrics.base import SimpleMetric
from face.metrics.geometry import get_3d_distance
from face.metrics.scoring import ScoringConfig

logger = logging.getLogger(__name__)
THEME_COLOR = "#B90000"

FACE_WIDTH_PAIRS = [(234, 454)]
MID_FACE_HEIGHT_PAIRS = [(9, 0)]

SCORING_CONFIG = ScoringConfig(
    ideal=1.7300,
    tolerance=0.0050,
    left_anchor=(0.1000, 2.0),
    right_anchor=(0.1200, 2.0),
    min_score=1.0,
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
    if FACE_WIDTH_PAIRS:
        _draw_line(annotated, lm, w, h, FACE_WIDTH_PAIRS[0][0], FACE_WIDTH_PAIRS[0][1], color_bgr)
    if MID_FACE_HEIGHT_PAIRS:
        _draw_line(annotated, lm, w, h, MID_FACE_HEIGHT_PAIRS[0][0], MID_FACE_HEIGHT_PAIRS[0][1], color_bgr)
    _, encoded = cv2.imencode(".jpg", annotated)
    return encoded.tobytes() if encoded is not None else b""

def get_stable_fwhr_metrics(points: Any, w: int, h: int) -> Dict[str, Any]:
    valid_width = []
    valid_height = []
    for left_id, right_id in FACE_WIDTH_PAIRS:
        dist = get_3d_distance(points, left_id, right_id)
        if dist is not None and dist > 0:
            valid_width.append(dist)
    for top_id, bottom_id in MID_FACE_HEIGHT_PAIRS:
        dist = get_3d_distance(points, top_id, bottom_id)
        if dist is not None and dist > 0:
            valid_height.append(dist)
    if not valid_width or not valid_height:
        return {
            "stable_face_width": SimpleMetric(name="Face Width", value=None),
            "stable_mid_height": SimpleMetric(name="Mid Face Height", value=None),
            "stable_ratio": SimpleMetric(name="FWHR", value=None),
            "point_confidences": []
        }
    avg_w = sum(valid_width) / len(valid_width)
    avg_h = sum(valid_height) / len(valid_height)
    avg_ratio = avg_w / avg_h if avg_h > 0 else 0
    return {
        "stable_face_width": SimpleMetric(name="Face Width", value=round(avg_w, 2)),
        "stable_mid_height": SimpleMetric(name="Mid Face Height", value=round(avg_h, 2)),
        "stable_ratio": SimpleMetric(name="FWHR", value=round(avg_ratio, 4)),
        "point_confidences": []
    }

FEATURE_CONFIG = {
    "key": "fwhr",
    "title": "Facial Width to Height Ratio",
    "label": "FWHR Ratio",
    "ratio_key": "stable_ratio",
    "scoring": SCORING_CONFIG,
    "drawer": draw_analysis,
    "theme_color": THEME_COLOR,
}