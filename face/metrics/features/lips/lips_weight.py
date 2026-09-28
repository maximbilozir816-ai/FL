import logging
import cv2
from typing import Any, Dict

from face.metrics.base import SimpleMetric
from face.metrics.geometry import get_3d_distance
from face.metrics.scoring import ScoringConfig

logger = logging.getLogger(__name__)

THEME_COLOR = "#E95870"

# Використовуємо окремо верхню і нижню губу від лінії змикання (для точності)
UPPER_LIP_PAIRS = [(0, 13)]
LOWER_LIP_PAIRS = [(14, 17)]

LIPS_WIDTH_PAIRS = [
    (61, 291),
]

SCORING_CONFIG = ScoringConfig(
    ideal        = 0.3250,
    tolerance    = 0.0200,
    left_anchor  = (0.0400, 2.5),
    right_anchor = (0.0450, 3.0),
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

    for top_id, bottom_id in UPPER_LIP_PAIRS + LOWER_LIP_PAIRS:
        _draw_line(annotated, lm, w, h, top_id, bottom_id, color_bgr)
        
    for left_id, right_id in LIPS_WIDTH_PAIRS:
        _draw_line(annotated, lm, w, h, left_id, right_id, color_bgr)

    _, encoded = cv2.imencode(".jpg", annotated)
    return encoded.tobytes() if encoded is not None else b""

def get_stable_lips_weight_metrics(points: Any, w: int, h: int) -> Dict[str, Any]:
    valid_heights = []
    valid_widths = []

    for top_id, bottom_id in UPPER_LIP_PAIRS + LOWER_LIP_PAIRS:
        dist = get_3d_distance(points, top_id, bottom_id)
        if dist is not None and dist > 0:
            valid_heights.append(dist)

    for left_id, right_id in LIPS_WIDTH_PAIRS:
        dist = get_3d_distance(points, left_id, right_id)
        if dist is not None and dist > 0:
            valid_widths.append(dist)

    if not valid_heights or not valid_widths:
        return {
            "stable_lips_height": SimpleMetric(name="Lips Height (Average)", value=None),
            "stable_lips_width": SimpleMetric(name="Lips Width (Average)", value=None),
            "stable_ratio": SimpleMetric(name="Lips Weight Ratio", value=None),
            "point_confidences": []
        }

    # Сумуємо висоту верхньої та нижньої губи
    total_height = sum(valid_heights)
    avg_width = sum(valid_widths) / len(valid_widths)
    avg_ratio = total_height / avg_width if avg_width > 0 else 0

    # Фільтрація міміки: якщо рот сильно розтягнутий в усмішці, коефіцієнт ширини зростає, 
    # тому ми вводимо поправочний множник, щоб уникнути хибно низьких оцінок
    interpupillary_dist = get_3d_distance(points, 468, 473) # 468 та 473 - зіниці у MediaPipe
    if interpupillary_dist and interpupillary_dist > 0:
        mouth_to_eyes_ratio = avg_width / interpupillary_dist
        if mouth_to_eyes_ratio > 0.85: # Ознака широкої усмішки
            avg_ratio *= 1.15

    return {
        "stable_lips_height": SimpleMetric(name="Lips Height (Average)", value=round(total_height, 2)),
        "stable_lips_width": SimpleMetric(name="Lips Width (Average)", value=round(avg_width, 2)),
        "stable_ratio": SimpleMetric(name="Lips Weight Ratio", value=round(avg_ratio, 4)),
        "point_confidences": []
    }

FEATURE_CONFIG = {
    "key": "lips_weight",
    "title": "Lips Fullness",
    "label": "Height / Width Ratio",
    "ratio_key": "stable_ratio",
    "scoring": SCORING_CONFIG,
    "drawer": draw_analysis,
    "theme_color": THEME_COLOR,
}