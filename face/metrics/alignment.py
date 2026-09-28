# face/metrics/alignment.py
"""
3D face frontalization.

Compensates for camera lens distortion / head pose (yaw, pitch, roll) by
estimating global head rotation from a handful of stable landmarks, then
applying the inverse rotation to the *entire* landmark cloud. Downstream
metrics operate on this canonicalized "frontal" point cloud instead of raw,
pose-skewed MediaPipe coordinates, so distances stop drifting when the user
tilts their head or the phone is too close (perspective/lens distortion).
"""

import logging
import math
from typing import Any, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Same calibration constant as confidence/pose.py::_estimate_head_angles —
# MediaPipe's raw pitch estimate carries a constant bias from face curvature,
# so it's subtracted before building the correction matrix.
PITCH_OFFSET_DEG = 5.0

# Anchor point used as the rotation/translation origin (nose bridge, 168).
CENTER_LANDMARK_ID = 168

# Landmark pairs used to estimate global head rotation (same points as pose.py).
YAW_PAIR = (234, 454)    # left cheek  -> right cheek
PITCH_PAIR = (10, 152)   # forehead    -> chin
ROLL_PAIR = (33, 263)    # left eye outer corner -> right eye outer corner


def landmarks_to_numpy(lm: Any, w: int, h: int) -> np.ndarray:
    """
    Convert a MediaPipe FaceMesh landmark list into an [478, 3] numpy array,
    scaling normalized (x, y, z) into pixel-space units.

    x, y -> pixel coordinates (scaled by width / height respectively)
    z    -> depth, scaled by width (MediaPipe's own convention)
    """
    return np.array([[p.x * w, p.y * h, p.z * w] for p in lm], dtype=np.float64)


def _rotation_matrix_x(theta: float) -> np.ndarray:
    c, s = math.cos(theta), math.sin(theta)
    return np.array([
        [1.0, 0.0, 0.0],
        [0.0, c,  -s],
        [0.0, s,   c],
    ])


def _rotation_matrix_y(theta: float) -> np.ndarray:
    c, s = math.cos(theta), math.sin(theta)
    return np.array([
        [c,  0.0, s],
        [0.0, 1.0, 0.0],
        [-s, 0.0, c],
    ])


def _rotation_matrix_z(theta: float) -> np.ndarray:
    c, s = math.cos(theta), math.sin(theta)
    return np.array([
        [c, -s, 0.0],
        [s,  c, 0.0],
        [0.0, 0.0, 1.0],
    ])


def _estimate_head_angles_rad(points: np.ndarray) -> Tuple[float, float, float]:
    """
    Signed head rotation angles in radians, estimated from a *centered*
    landmark cloud.

    Mirrors confidence/pose.py::_estimate_head_angles, but:
      - keeps the sign (we need to know *which way* to rotate back, whereas
        pose.py only needed magnitude for a confidence penalty)
      - reads from the numpy array instead of MediaPipe landmark objects
    """
    p_left_cheek, p_right_cheek = points[YAW_PAIR[0]], points[YAW_PAIR[1]]
    yaw = math.atan2(
        p_right_cheek[2] - p_left_cheek[2],
        p_right_cheek[0] - p_left_cheek[0],
    )

    p_forehead, p_chin = points[PITCH_PAIR[0]], points[PITCH_PAIR[1]]
    pitch = math.atan2(
        p_chin[2] - p_forehead[2],
        p_chin[1] - p_forehead[1],
    )

    p_eye_l, p_eye_r = points[ROLL_PAIR[0]], points[ROLL_PAIR[1]]
    roll = math.atan2(
        p_eye_r[1] - p_eye_l[1],
        p_eye_r[0] - p_eye_l[0],
    )

    return yaw, pitch, roll


def frontalize_face(lm: Any, w: int, h: int) -> np.ndarray:
    """
    Center the face on CENTER_LANDMARK_ID (168) and rotate the whole
    landmark cloud so yaw, pitch and roll are canceled out.
    """
    points = landmarks_to_numpy(lm, w, h)
    center = points[CENTER_LANDMARK_ID].copy()
    centered = points - center

    yaw, pitch, roll = _estimate_head_angles_rad(centered)
    pitch_corrected = pitch - math.radians(PITCH_OFFSET_DEG)

    # SIGN & ORDER CORRECTION:
    # Because atan2 for yaw returns the angle with an opposite sign (due to
    # the Z-axis direction), we apply +yaw rather than -yaw to cancel the
    # rotation. Inverse rotation order: Roll -> Yaw -> Pitch.
    correction = (
        _rotation_matrix_z(-roll)
        @ _rotation_matrix_y(yaw)  # <--- corrected sign for Yaw
        @ _rotation_matrix_x(-pitch_corrected)
    )

    frontalized = centered @ correction.T
    frontalized += center

    logger.debug(
        "Frontalized face: yaw=%.2f° pitch=%.2f° roll=%.2f°",
        math.degrees(yaw), math.degrees(pitch), math.degrees(roll),
    )

    return frontalized