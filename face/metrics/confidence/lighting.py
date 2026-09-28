# face/metrics/confidence/lighting.py
import logging
import cv2
import numpy as np
from typing import Any, List, Tuple

logger = logging.getLogger(__name__)

# Thresholds are tuned to protect MediaPipe Face Mesh from tracking failures
# (when landmarks drift off the face due to loss of contrast in frame).

# 1. Overexposure: skin/contour detail is lost.
OVEREXPOSURE_MEAN_THRESHOLD = 235.0   # mean face brightness above which detail 'burns out'
OVEREXPOSURE_CLIPPED_RATIO = 0.15     # ratio of fully 'white' pixels (>=250) considered critical

# 2. Deep shadows: MediaPipe loses contrast on facial features.
SHADOW_MEAN_THRESHOLD = 60.0          # mean face brightness below which it's considered 'too dark'

# 3. Harsh side lighting: sharp brightness asymmetry between left/right face halves.
SIDE_DIFF_THRESHOLD = 28.0


def _face_bbox(lm: Any, w: int, h: int):
    x_coords = [int(p.x * w) for p in lm]
    y_coords = [int(p.y * h) for p in lm]
    x_min, x_max = max(0, min(x_coords)), min(w, max(x_coords))
    y_min, y_max = max(0, min(y_coords)), min(h, max(y_coords))
    return x_min, x_max, y_min, y_max


def analyze_lighting(image: np.ndarray, lm: Any, w: int, h: int) -> Tuple[bool, List[str]]:
    """
    Strict binary Pass/Fail lighting check, tuned to protect MediaPipe Face Mesh
    from tracking failures caused by overexposure, deep shadows, or harsh side light.

    Returns:
        (is_valid, reasons) — reasons is a list of clear, user-facing English messages.
    """
    reasons: List[str] = []

    if image is None:
        return True, reasons

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        x_min, x_max, y_min, y_max = _face_bbox(lm, w, h)
        if x_max <= x_min or y_max <= y_min:
            return True, reasons

        face_region = gray[y_min:y_max, x_min:x_max]
        if face_region.size == 0:
            return True, reasons

        mean_brightness = float(np.mean(face_region))
        clipped_ratio = float(np.mean(face_region >= 250))

        # 1. Strong overexposure
        if mean_brightness > OVEREXPOSURE_MEAN_THRESHOLD or clipped_ratio > OVEREXPOSURE_CLIPPED_RATIO:
            reasons.append("Lighting is too bright and washes out facial detail. Move away from direct light or a bright window.")

        # 2. Deep shadows
        if mean_brightness < SHADOW_MEAN_THRESHOLD:
            reasons.append("Lighting is too dark. Move to a brighter, evenly lit area.")

        # 3. Harsh side lighting
        mid_x = x_min + (x_max - x_min) // 2
        left_half = gray[y_min:y_max, x_min:mid_x]
        right_half = gray[y_min:y_max, mid_x:x_max]

        if left_half.size > 0 and right_half.size > 0:
            mean_l = float(np.mean(left_half))
            mean_r = float(np.mean(right_half))
            diff = abs(mean_l - mean_r)

            if diff > SIDE_DIFF_THRESHOLD:
                reasons.append("Lighting is too harsh on one side. Stand facing a window or light source directly.")

        is_valid = len(reasons) == 0
        return is_valid, reasons

    except Exception as e:
        logger.error(f"Error checking lighting: {e}")
        return True, reasons