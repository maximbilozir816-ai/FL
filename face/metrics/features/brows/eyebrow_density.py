import logging
import cv2
import numpy as np
from typing import Any, Dict

from face.metrics.base import SimpleMetric
from face.metrics.geometry import get_3d_distance
from face.metrics.scoring import ScoringConfig

logger = logging.getLogger(__name__)

THEME_COLOR = "#FFFFFF"

BROW_THICKNESS_PAIRS = [
    (105, 52),
    (334, 282),
]

BROW_WIDTH_PAIRS = [
    (70, 107),
    (300, 336),
]

# Область для кропу брів (ліва і права)
LEFT_BROW_CONTOUR = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
RIGHT_BROW_CONTOUR = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]

SCORING_CONFIG = ScoringConfig(
    ideal        = 0.1400,
    tolerance    = 0.0005,
    left_anchor  = (0.0100, 3.5),
    right_anchor = (0.0100, 3.5),
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

    for top_id, bottom_id in BROW_THICKNESS_PAIRS:
        _draw_line(annotated, lm, w, h, top_id, bottom_id, color_bgr)

    for outer_id, inner_id in BROW_WIDTH_PAIRS:
        _draw_line(annotated, lm, w, h, outer_id, inner_id, color_bgr)

    _, encoded = cv2.imencode(".jpg", annotated)
    return encoded.tobytes() if encoded is not None else b""

def _calculate_pixel_density(img: np.ndarray, points: np.ndarray, contour_ids: list, w: int, h: int) -> float:
    try:
        polygon = np.array([(int(points[idx, 0]), int(points[idx, 1])) for idx in contour_ids], dtype=np.int32)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [polygon], 255)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        masked_gray = cv2.bitwise_and(gray, gray, mask=mask)
        
        # Використовуємо Otsu Thresholding для пошуку темного волосся брів
        x, y, bw, bh = cv2.boundingRect(polygon)
        roi_gray = masked_gray[y:y+bh, x:x+bw]
        roi_mask = mask[y:y+bh, x:x+bw]
        
        valid_pixels = roi_gray[roi_mask == 255]
        if len(valid_pixels) == 0:
            return 0.0
            
        _, thresh = cv2.threshold(valid_pixels, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        dark_pixels = np.count_nonzero(thresh)
        total_pixels = len(valid_pixels)
        
        return float(dark_pixels) / float(total_pixels) if total_pixels > 0 else 0.0
    except Exception as e:
        logger.error(f"Error calculating brow density: {e}")
        return 0.0

def get_stable_eyebrow_density_metrics(points: Any, w: int, h: int, img: np.ndarray = None) -> Dict[str, Any]:
    valid_thickness = []
    valid_widths = []

    for top_id, bottom_id in BROW_THICKNESS_PAIRS:
        dist = get_3d_distance(points, top_id, bottom_id)
        if dist is not None and dist > 0:
            valid_thickness.append(dist)

    for outer_id, inner_id in BROW_WIDTH_PAIRS:
        dist = get_3d_distance(points, outer_id, inner_id)
        if dist is not None and dist > 0:
            valid_widths.append(dist)

    if not valid_thickness or not valid_widths:
        return {
            "stable_thickness": SimpleMetric(name="Brow Thickness", value=None),
            "stable_width": SimpleMetric(name="Brow Width", value=None),
            "stable_ratio": SimpleMetric(name="Thickness to Width Ratio", value=None),
            "point_confidences": []
        }

    avg_thickness = sum(valid_thickness) / len(valid_thickness)
    avg_width = sum(valid_widths) / len(valid_widths)
    
    # Якщо зображення передано, рахуємо справжню піксельну густоту
    if img is not None and isinstance(img, np.ndarray):
        left_density = _calculate_pixel_density(img, points, LEFT_BROW_CONTOUR, w, h)
        right_density = _calculate_pixel_density(img, points, RIGHT_BROW_CONTOUR, w, h)
        avg_ratio = (left_density + right_density) / 2.0
    else:
        # Резервний варіант (геометричний)
        avg_ratio = avg_thickness / avg_width if avg_width > 0 else 0

    return {
        "stable_thickness": SimpleMetric(name="Brow Thickness", value=round(avg_thickness, 2)),
        "stable_width": SimpleMetric(name="Brow Width", value=round(avg_width, 2)),
        "stable_ratio": SimpleMetric(name="Thickness to Width Ratio", value=round(avg_ratio, 4)),
        "point_confidences": []
    }

FEATURE_CONFIG = {
    "key": "eyebrow_density",
    "title": "Eyebrow Thickness",
    "label": "Thickness / Width Ratio",
    "ratio_key": "stable_ratio",
    "scoring": SCORING_CONFIG,
    "drawer": draw_analysis,
    "theme_color": THEME_COLOR,
}