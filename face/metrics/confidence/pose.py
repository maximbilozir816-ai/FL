# face/metrics/confidence/pose.py
import logging
import math
from typing import Any, List, Tuple

logger = logging.getLogger(__name__)

# User instruction: "Hold the phone with both hands, extend your arms forward,
# use the front camera with x2 zoom".
# At this distance (~40-55 cm) the face occupies a SMALLER share of the frame than a
# typical close-up selfie, so the ratio thresholds are adapted to this instruction.
MIN_FACE_RATIO = 0.28
MAX_FACE_RATIO = 0.55

# MediaPipe Face Mesh is very sensitive to head tilt -- thresholds in degrees
# are kept strict to guarantee stable tracking of the 468 landmarks.
MAX_YAW_DEG = 8.0
MAX_PITCH_DEG = 8.0
MAX_ROLL_DEG = 6.0

# Lens-distortion threshold (Outer Canthal / Face Width) under x2 zoom + extended arms.
# At this distance 'fisheye' distortion appears far less often than at 15-20 cm,
# so the threshold is narrowed relative to the old close-up-selfie logic.
LENS_DISTORTION_RATIO = 0.68


def check_lens_distortion(lm: Any, w: int, h: int) -> Tuple[bool, str]:
    """
    Checks whether the photo was taken too close to the camera (fisheye/lens
    distortion), adapted for the "extended arms + front camera x2 zoom" instruction.

    Returns:
        (is_distorted, reason) — reason is a ready-to-show English message.
    """
    dx_eyes = (lm[263].x - lm[33].x) * w
    dy_eyes = (lm[263].y - lm[33].y) * h
    eyes_width = math.sqrt(dx_eyes**2 + dy_eyes**2)

    dx_face = (lm[454].x - lm[234].x) * w
    dy_face = (lm[454].y - lm[234].y) * h
    face_width = math.sqrt(dx_face**2 + dy_face**2)

    if face_width == 0:
        return False, ""

    ratio = eyes_width / face_width

    if ratio > LENS_DISTORTION_RATIO:
        return True, "Lens distortion detected. Make sure your arms are fully extended and x2 zoom is active."

    return False, ""


def _estimate_head_angles(lm: Any, w: int, h: int) -> Tuple[float, float, float]:
    """Calculates SIGNED global head rotation angles (Yaw, Pitch, Roll) in degrees."""
    try:
        dx_yaw = (lm[454].x - lm[234].x) * w
        dz_yaw = (lm[454].z - lm[234].z) * w
        yaw = math.degrees(math.atan2(dz_yaw, dx_yaw))

        dy_pitch = (lm[152].y - lm[10].y) * h
        dz_pitch = (lm[152].z - lm[10].z) * w
        pitch = math.degrees(math.atan2(dz_pitch, dy_pitch)) - 5.0

        dx_roll = (lm[263].x - lm[33].x) * w
        dy_roll = (lm[263].y - lm[33].y) * h
        roll = math.degrees(math.atan2(dy_roll, dx_roll))

        return yaw, pitch, roll
    except Exception as e:
        logger.error(f"Failed to calculate head angles: {e}")
        return 0.0, 0.0, 0.0


def analyze_pose(lm: Any, w: int, h: int, face_width_px: float) -> Tuple[bool, List[str]]:
    """
    Strict binary Pass/Fail pose check, tuned for MediaPipe Face Mesh stability
    under the "hold with two hands, arms extended, front camera x2 zoom" instruction.

    Returns:
        (is_valid, reasons) — reasons is a list of clear, user-facing English messages.
    """
    reasons: List[str] = []

    current_face_ratio = face_width_px / w

    if current_face_ratio < MIN_FACE_RATIO:
        reasons.append("Face is too small in the frame. Bring the phone slightly closer while keeping your arms extended.")
    elif current_face_ratio > MAX_FACE_RATIO:
        reasons.append("Face is too close to the camera. Extend your arms a bit further or check the x2 zoom.")

    yaw, pitch, roll = _estimate_head_angles(lm, w, h)

    if abs(yaw) > MAX_YAW_DEG:
        reasons.append("Face is turned slightly to the side. Look straight into the camera.")

    if abs(pitch) > MAX_PITCH_DEG:
        if pitch > 0:
            reasons.append("Your chin is tucked in too much. Lift your head slightly.")
        else:
            reasons.append("Camera is not at eye level. Please hold the phone exactly at eye level.")

    if abs(roll) > MAX_ROLL_DEG:
        reasons.append("Head is tilted. Keep your head perfectly straight.")

    is_valid = len(reasons) == 0
    return is_valid, reasons