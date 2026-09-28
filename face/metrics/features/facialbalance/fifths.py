import logging
import cv2
from typing import Any, Dict

from face.metrics.geometry import get_3d_distance
from face.metrics.scoring import ScoringConfig, compute_score

logger = logging.getLogger(__name__)

THEME_COLOR = "#8a2780" 

# ==============================================================================
# ЛОКАЛЬНІ ТОЧКИ ТА КОНФІГУРАЦІЇ ОЦІНЮВАННЯ ДЛЯ П'ЯТИХ ЧАСТИН
# ==============================================================================
FIFTHS_AXIS_X = (234, 454)        
FIFTHS_AXIS_Y = (133, 362)        
FIFTHS_X_POINTS = [234, 33, 133, 362, 263, 454] 
FIFTHS_Y_BOUNDS = (10, 152)       
FIFTHS_SEGMENTS = [
    (234, 33),                    
    (33, 133),                    
    (133, 362),                   
    (362, 263),                   
    (263, 454)                    
]

# Залишаємо лише 3 конфігурації (Outer, Inner, Middle)
FIFTHS_OUTER_SCORING = ScoringConfig(
    ideal        = 22.0,
    tolerance    = 0.1,
    left_anchor  = (1.0, 4.0),
    right_anchor = (1.0, 4.0),
    min_score    = 1.0,
)

FIFTHS_INNER_SCORING = ScoringConfig(
    ideal        = 17.0,
    tolerance    = 0.1,
    left_anchor  = (1.0, 4.0),
    right_anchor = (1.0, 4.0),
    min_score    = 1.0,
)

FIFTHS_MIDDLE_SCORING = ScoringConfig(
    ideal        = 22.0,
    tolerance    = 0.1,
    left_anchor  = (1.0, 4.0),
    right_anchor = (1.0, 4.0),
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
        py_top = int(lm[FIFTHS_Y_BOUNDS[0]].y * h)
        py_bottom = int(lm[FIFTHS_Y_BOUNDS[1]].y * h)

        for pt_id in FIFTHS_X_POINTS:
            px = int(lm[pt_id].x * w)
            draw_dashed_line(annotated, (px, py_top), (px, py_bottom), color_bgr, 2, 8)
            
    except (IndexError, AttributeError):
        pass

    _, encoded = cv2.imencode(".jpg", annotated)
    return encoded.tobytes() if encoded is not None else b""

def get_stable_fifths_metrics(points: Any, w: int, h: int) -> Dict[str, Any]:
    f1 = get_3d_distance(points, FIFTHS_SEGMENTS[0][0], FIFTHS_SEGMENTS[0][1])
    f2 = get_3d_distance(points, FIFTHS_SEGMENTS[1][0], FIFTHS_SEGMENTS[1][1])
    f3 = get_3d_distance(points, FIFTHS_SEGMENTS[2][0], FIFTHS_SEGMENTS[2][1])
    f4 = get_3d_distance(points, FIFTHS_SEGMENTS[3][0], FIFTHS_SEGMENTS[3][1])
    f5 = get_3d_distance(points, FIFTHS_SEGMENTS[4][0], FIFTHS_SEGMENTS[4][1])

    if None in (f1, f2, f3, f4, f5) or any(v == 0 for v in (f1, f2, f3, f4, f5)):
        return {"total": 0}

    return {
        "f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5": f5,
        "total": sum([f1, f2, f3, f4, f5]),
        "point_confidences": []
    }

def build_complex_fifths(m_data: dict, cfg: dict) -> tuple[list, float]:
    total = m_data.get("total", 0)
    if not total: return [], 1.0

    # 1. Рахуємо сирі відсотки для всіх 5 ділянок
    f1_pct = (m_data["f1"] / total) * 100
    f2_pct = (m_data["f2"] / total) * 100
    f3_pct = (m_data["f3"] / total) * 100
    f4_pct = (m_data["f4"] / total) * 100
    f5_pct = (m_data["f5"] / total) * 100

    # 2. Усереднюємо симетричні частини (Ліву та Праву)
    outer_pct = (f1_pct + f5_pct) / 2.0
    inner_pct = (f2_pct + f4_pct) / 2.0
    middle_pct = f3_pct

    # 3. Рахуємо бали через скоринг для 3 об'єднаних зон
    score_outer = compute_score(outer_pct, FIFTHS_OUTER_SCORING)
    score_inner = compute_score(inner_pct, FIFTHS_INNER_SCORING)
    score_middle = compute_score(middle_pct, FIFTHS_MIDDLE_SCORING)

    # 4. Загальна оцінка – середнє значення цих 3 зон
    overall_score = round((score_outer + score_inner + score_middle) / 3.0, 2)

    # 5. Формуємо елементи для виводу в таблицю special_metrics_block.html
    items = [
        {"label": "outer", "value": f"{outer_pct:.1f}%", "ideal": str(int(FIFTHS_OUTER_SCORING.ideal))},
        {"label": "inner", "value": f"{inner_pct:.1f}%", "ideal": str(int(FIFTHS_INNER_SCORING.ideal))},
        {"label": "middle", "value": f"{middle_pct:.1f}%", "ideal": str(int(FIFTHS_MIDDLE_SCORING.ideal))}
    ]

    return items, overall_score

FEATURE_CONFIG = {
    "key": "fifths",
    "title": "Horizontal Fifths Balance",
    "is_complex": True,
    "complex_builder": build_complex_fifths,
    "drawer": draw_analysis,
    "theme_color": THEME_COLOR,
}