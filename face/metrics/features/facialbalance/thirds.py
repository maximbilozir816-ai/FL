import logging
import cv2
from typing import Any, Dict

from face.metrics.geometry import get_3d_distance
from face.metrics.scoring import ScoringConfig, compute_score

logger = logging.getLogger(__name__)

THEME_COLOR = "#8a2780"

THIRDS_AXIS = (10, 152)           
THIRDS_Y_POINTS = [10, 9, 2, 152] 
THIRDS_EDGE_X = (234, 454)        
THIRDS_SEGMENTS = [
    (10, 9),                      
    (9, 2),                       
    (2, 152)                      
]

THIRDS_UPPER_SCORING = ScoringConfig(
    ideal        = 21.0,
    tolerance    = 0.1,
    left_anchor  = (1.0, 4.0),
    right_anchor = (1.0, 4.0),
    min_score    = 1.0,
)

THIRDS_MIDDLE_SCORING = ScoringConfig(
    ideal        = 38.0,
    tolerance    = 0.1,
    left_anchor  = (1.75, 4.0),
    right_anchor = (1.4, 4.0),
    min_score    = 1.0,
)

THIRDS_LOWER_SCORING = ScoringConfig(
    ideal        = 41.0,
    tolerance    = 0.1,
    left_anchor  = (1.75, 4.0),
    right_anchor = (1.4, 4.0),
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
        px_left = int(lm[THIRDS_EDGE_X[0]].x * w)
        px_right = int(lm[THIRDS_EDGE_X[1]].x * w)

        for pt_id in THIRDS_Y_POINTS:
            py = int(lm[pt_id].y * h)
            draw_dashed_line(annotated, (px_left, py), (px_right, py), color_bgr, 2, 8)
            
    except (IndexError, AttributeError):
        pass

    _, encoded = cv2.imencode(".jpg", annotated)
    return encoded.tobytes() if encoded is not None else b""

def get_stable_thirds_metrics(points: Any, w: int, h: int) -> Dict[str, Any]:
    upper = get_3d_distance(points, THIRDS_SEGMENTS[0][0], THIRDS_SEGMENTS[0][1])
    middle = get_3d_distance(points, THIRDS_SEGMENTS[1][0], THIRDS_SEGMENTS[1][1])
    lower = get_3d_distance(points, THIRDS_SEGMENTS[2][0], THIRDS_SEGMENTS[2][1])

    if None in (upper, middle, lower) or upper == 0 or middle == 0 or lower == 0:
        return {"total": 0}

    return {
        "upper_val": upper,
        "middle_val": middle,
        "lower_val": lower,
        "total": upper + middle + lower,
        "point_confidences": []
    }

def build_complex_thirds(m_data: dict, cfg: dict) -> tuple[list, float]:
    total = m_data.get("total", 0)
    if not total: return [], 1.0

    upper_pct = (m_data["upper_val"] / total) * 100
    middle_pct = (m_data["middle_val"] / total) * 100
    lower_pct = (m_data["lower_val"] / total) * 100

    score_up = compute_score(upper_pct, THIRDS_UPPER_SCORING)
    score_mid = compute_score(middle_pct, THIRDS_MIDDLE_SCORING)
    score_low = compute_score(lower_pct, THIRDS_LOWER_SCORING)

    overall_score = round((score_up + score_mid + score_low) / 3.0, 2)

    items = [
        {"label": "upper", "value": f"{upper_pct:.1f}%", "ideal": str(int(THIRDS_UPPER_SCORING.ideal))},
        {"label": "middle", "value": f"{middle_pct:.1f}%", "ideal": str(int(THIRDS_MIDDLE_SCORING.ideal))},
        {"label": "lower", "value": f"{lower_pct:.1f}%", "ideal": str(int(THIRDS_LOWER_SCORING.ideal))}
    ]
    return items, overall_score

FEATURE_CONFIG = {
    "key": "thirds",
    "title": "Vertical Thirds Balance",
    "is_complex": True,
    "complex_builder": build_complex_thirds,
    "drawer": draw_analysis,
    "theme_color": THEME_COLOR,
}