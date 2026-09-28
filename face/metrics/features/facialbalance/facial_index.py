import logging
import cv2
from typing import Any, Dict

from face.metrics.geometry import get_3d_distance
from face.metrics.scoring import ScoringConfig, compute_score

logger = logging.getLogger(__name__)

THEME_COLOR = "#8a2780"

# ==============================================================================
# ЛОКАЛЬНІ ТОЧКИ ТА КОНФІГУРАЦІЯ ОЦІНЮВАННЯ
# ==============================================================================
FACIAL_INDEX_HEIGHT_PAIR = (10, 152)
FACIAL_INDEX_WIDTH_PAIR = (234, 454)

SCORING_CONFIG = ScoringConfig(
    ideal        = 122,  
    tolerance    = 0.1,
    left_anchor  = (4, 3.5),
    right_anchor = (4, 4.0),
    min_score    = 1.0,
)
# ==============================================================================

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

def draw_analysis(img: Any, lm: Any, w: int, h: int) -> bytes:
    annotated = img.copy()
    color_bgr = _hex_to_bgr(THEME_COLOR)

    try:
        top = (int(lm[FACIAL_INDEX_HEIGHT_PAIR[0]].x * w), int(lm[FACIAL_INDEX_HEIGHT_PAIR[0]].y * h))
        bottom = (int(lm[FACIAL_INDEX_HEIGHT_PAIR[1]].x * w), int(lm[FACIAL_INDEX_HEIGHT_PAIR[1]].y * h))
        draw_dashed_line(annotated, top, bottom, color_bgr, 2, 8)

        left = (int(lm[FACIAL_INDEX_WIDTH_PAIR[0]].x * w), int(lm[FACIAL_INDEX_WIDTH_PAIR[0]].y * h))
        right = (int(lm[FACIAL_INDEX_WIDTH_PAIR[1]].x * w), int(lm[FACIAL_INDEX_WIDTH_PAIR[1]].y * h))
        draw_dashed_line(annotated, left, right, color_bgr, 2, 8)
            
    except (IndexError, AttributeError):
        pass

    _, encoded = cv2.imencode(".jpg", annotated)
    return encoded.tobytes() if encoded is not None else b""

def get_stable_index_metrics(points: Any, w: int, h: int) -> Dict[str, Any]:
    valid_heights = []
    valid_widths = []

    dist = get_3d_distance(points, FACIAL_INDEX_HEIGHT_PAIR[0], FACIAL_INDEX_HEIGHT_PAIR[1])
    if dist: valid_heights.append(dist)

    dist = get_3d_distance(points, FACIAL_INDEX_WIDTH_PAIR[0], FACIAL_INDEX_WIDTH_PAIR[1])
    if dist: valid_widths.append(dist)

    if not valid_heights or not valid_widths:
        return {"ratio": 0}

    avg_height = sum(valid_heights) / len(valid_heights)
    avg_width = sum(valid_widths) / len(valid_widths)
    avg_ratio = avg_height / avg_width if avg_width > 0 else 0

    return {
        "ratio": avg_ratio,
        "point_confidences": []
    }

def build_complex_index(m_data: dict, cfg: dict) -> tuple[list, float]:
    ratio_raw = m_data.get("ratio", 0)
    if not ratio_raw: return [], 1.0

    ratio_pct = ratio_raw * 100
    overall_score = compute_score(ratio_pct, SCORING_CONFIG)

    items = [
        {
            "label": "H/W",
            "value": f"{ratio_pct:.1f}%",
            "ideal": str(int(SCORING_CONFIG.ideal))
        }
    ]

    return items, overall_score

FEATURE_CONFIG = {
    "key": "facial_index",
    "title": "Facial Index Harmony",
    "is_complex": True,
    "complex_builder": build_complex_index,
    "drawer": draw_analysis,
    "theme_color": THEME_COLOR,
}