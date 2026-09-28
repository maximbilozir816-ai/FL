# services/photo_processor.py
"""
Owns everything that happens to raw photo bytes before we have clean,
frontalized landmarks + biometric metrics ready for reporting:
  decode -> validate -> detect face -> quality gate -> crop -> TTA metrics.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Optional

import cv2
import mediapipe as mp
import numpy as np

from config import settings
from face.cropper import CropConfig, smart_face_crop
from face.metrics.confidence import analyze_total_confidence
from face.metrics.confidence.pose import check_lens_distortion
from face.tta import analyze_with_tta
from texts import en

logger = logging.getLogger(__name__)

mp_face_mesh = mp.solutions.face_mesh

MIN_DIMENSION = 100
MAX_DIMENSION = 2560
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
MIN_ASPECT_RATIO = 0.4
MAX_ASPECT_RATIO = 2.0


class PhotoRejected(Exception):
    """
    Carries a ready-to-show, English, HTML-formatted message explaining why
    the photo could not be processed.
    """
    def __init__(self, message: str, is_quality_gate: bool = False):
        super().__init__(message)
        self.message = message
        self.is_quality_gate = is_quality_gate


@dataclass
class ProcessedPhoto:
    image_crop_bgr: np.ndarray
    landmarks: Any
    metrics: dict
    width_crop: int
    height_crop: int


def decode_image(raw_bytes: bytes, file_size: Optional[int]) -> np.ndarray:
    if file_size and file_size > MAX_FILE_SIZE_BYTES:
        raise PhotoRejected(en.PHOTO_TOO_LARGE)

    img = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise PhotoRejected(en.CANNOT_READ_PHOTO)

    h, w = img.shape[:2]

    if min(h, w) < MIN_DIMENSION:
        raise PhotoRejected(en.LOW_RESOLUTION.format(min_dim=MIN_DIMENSION))

    if h == 0 or w == 0 or not (MIN_ASPECT_RATIO <= (w / h) <= MAX_ASPECT_RATIO):
        raise PhotoRejected(en.BAD_ASPECT_RATIO)

    if max(h, w) > MAX_DIMENSION:
        scale = MAX_DIMENSION / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    return img


def _run_quality_gate(orig_lm: Any, w_orig: int, h_orig: int, img_orig: np.ndarray) -> None:
    is_distorted, dist_reason = check_lens_distortion(orig_lm, w_orig, h_orig)

    dx_f = (orig_lm[454].x - orig_lm[234].x) * w_orig
    dy_f = (orig_lm[454].y - orig_lm[234].y) * h_orig
    orig_face_width_px = math.sqrt(dx_f ** 2 + dy_f ** 2)

    conf_res = analyze_total_confidence(
        lm=orig_lm, w=w_orig, h=h_orig, face_width_px=orig_face_width_px, image=img_orig
    )

    reasons = list(conf_res["reasons"])
    if is_distorted and dist_reason:
        reasons.insert(0, dist_reason)

    is_valid = conf_res["is_valid"] and not is_distorted
    if not is_valid:
        # Передаємо ТІЛЬКИ список причин, без заголовка і підказки (це зробить photo.py)
        reasons_str = "\n".join(f"\u2022 {r}" for r in reasons) if reasons else "\u2022 Quality check failed"
        raise PhotoRejected(reasons_str, is_quality_gate=True)


def process_photo(img_orig: np.ndarray, telegram_id: int, skip_quality_check: bool = False) -> ProcessedPhoto:
    h_orig, w_orig = img_orig.shape[:2]

    with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
        rgb_orig = cv2.cvtColor(img_orig, cv2.COLOR_BGR2RGB)
        raw_results = face_mesh.process(rgb_orig)

        if not raw_results.multi_face_landmarks:
            raise PhotoRejected(en.NO_FACE_DETECTED)

        orig_lm = raw_results.multi_face_landmarks[0].landmark

        if settings.quality_gate_enabled and not skip_quality_check:
            _run_quality_gate(orig_lm, w_orig, h_orig, img_orig)
        else:
            reason = "user skipped" if skip_quality_check else "disabled in settings"
            logger.info(f"[INFO] User {telegram_id}: quality gate checks bypassed ({reason}).")

        img_crop = smart_face_crop(
            img_orig, face_mesh, CropConfig(target_ratio_x=0.60, target_ratio_y=0.50)
        )
        if img_crop is None:
            raise PhotoRejected(en.CROP_FAILED)

        h_c, w_c = img_crop.shape[:2]
        lm_crop, metrics = analyze_with_tta(img_crop, face_mesh)

    if not lm_crop or not metrics:
        raise PhotoRejected(en.TTA_FAILED)

    logger.info(f"[INFO] User {telegram_id} passed face extraction.")

    return ProcessedPhoto(
        image_crop_bgr=img_crop,
        landmarks=lm_crop,
        metrics=metrics,
        width_crop=w_c,
        height_crop=h_c,
    )