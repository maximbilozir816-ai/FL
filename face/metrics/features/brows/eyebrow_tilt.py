import logging
import cv2
from typing import Any, Dict

from face.metrics.base import SimpleMetric
from face.metrics.scoring import ScoringConfig

logger = logging.getLogger(__name__)

THEME_COLOR = "#FFFFFF"




# Використовуємо точні зовнішні (outer) та внутрішні (inner) кінці брів:
# (70, 55) для лівої брови, (300, 285) для правої брови
BROW_TILT_PAIRS = [
    (70, 55),
    (300, 285),
]

SCORING_CONFIG = ScoringConfig(
    ideal        = 0.0250,
    tolerance    = 0.0005,
    left_anchor  = (0.0250, 2.0),
    right_anchor = (0.0450, 3.0),
    min_score    = 1.0,
)




def _hex_to_bgr(hex_color: str) -> tuple:
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (4, 2, 0))

def draw_analysis(img: Any, lm: Any, w: int, h: int) -> bytes:
    annotated = img.copy()
    color_bgr = _hex_to_bgr(THEME_COLOR)

    for outer_id, inner_id in BROW_TILT_PAIRS:
        try:
            x_in, y_in = int(lm[inner_id].x * w), int(lm[inner_id].y * h)
            x_out, y_out = int(lm[outer_id].x * w), int(lm[outer_id].y * h)
            
            # Щоб біла лінія завжди була горизонтальною основою (знизу кута),
            # беремо найнижчу точку брови по осі Y (де Y більше):
            y_base = max(y_in, y_out)
            
            # Біла горизонтальна базова лінія (підніжжя)
            cv2.line(annotated, (x_in, y_base), (x_out, y_base), (255, 255, 255), 1, cv2.LINE_AA)
            
            # Кольорова лінія реального нахилу брови
            cv2.line(annotated, (x_in, y_in), (x_out, y_out), color_bgr, 2, cv2.LINE_AA)
            
        except (IndexError, AttributeError):
            pass

    _, encoded = cv2.imencode(".jpg", annotated)
    return encoded.tobytes() if encoded is not None else b""

def get_stable_eyebrow_tilt_metrics(points: Any, w: int, h: int) -> Dict[str, Any]:
    valid_tilts = []
    valid_widths = []

    for outer_id, inner_id in BROW_TILT_PAIRS:
        try:
            dx = abs(points[inner_id, 0] - points[outer_id, 0])
            
            # Оскільки в Mediapipe Y=0 зверху, внутрішня точка (нижча) має БІЛЬШИЙ Y,
            # ніж зовнішня (вища). Віднімаємо outer від inner для позитивного результату:
            dy = points[inner_id, 1] - points[outer_id, 1]

            if dx > 0:
                valid_tilts.append(dy)
                valid_widths.append(dx)
        except (IndexError, AttributeError, TypeError):
            pass

    if not valid_tilts or not valid_widths:
        return {
            "stable_tilt": SimpleMetric(name="Eyebrow Tilt (Height)", value=None),
            "stable_width": SimpleMetric(name="Eyebrow Width (Horizontal)", value=None),
            "stable_ratio": SimpleMetric(name="Brow Tilt to Width Ratio", value=None),
            "point_confidences": []
        }

    avg_tilt = sum(valid_tilts) / len(valid_tilts)
    avg_width = sum(valid_widths) / len(valid_widths)
    tilt_ratio = avg_tilt / avg_width if avg_width > 0 else 0

    return {
        "stable_tilt": SimpleMetric(name="Eyebrow Tilt (Height)", value=round(avg_tilt, 2)),
        "stable_width": SimpleMetric(name="Eyebrow Width (Horizontal)", value=round(avg_width, 2)),
        "stable_ratio": SimpleMetric(name="Brow Tilt to Width Ratio", value=round(tilt_ratio, 4)), 
        "point_confidences": []
    }

FEATURE_CONFIG = {
    "key": "eyebrow_tilt",
    "title": "Eyebrow Tilt Proportions",
    "label": "Brow Tilt / Width Ratio",
    "ratio_key": "stable_ratio",
    "scoring": SCORING_CONFIG,
    "drawer": draw_analysis,
    "theme_color": THEME_COLOR,
}