# face/tta.py
import cv2
import logging
from typing import Tuple, Optional, Any, Dict
from .metrics import get_all_metrics
from .metrics.alignment import frontalize_face

logger = logging.getLogger(__name__)

def analyze_with_tta(img_bgr: Any, face_mesh_model: Any) -> Tuple[Optional[list], Optional[Dict[str, Any]]]:
    h, w = img_bgr.shape[:2]

    rgb_orig = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    res_orig = face_mesh_model.process(rgb_orig)
    if not res_orig.multi_face_landmarks:
        return None, None

    lm_orig = res_orig.multi_face_landmarks[0].landmark
    # Frontalize BEFORE computing any metric, so yaw/pitch/roll from lens
    # distortion / head tilt don't leak into the distances.
    points_orig = frontalize_face(lm_orig, w, h)

    metrics_orig = get_all_metrics(points_orig, w, h)

    img_flipped = cv2.flip(img_bgr, 1)
    rgb_flipped = cv2.cvtColor(img_flipped, cv2.COLOR_BGR2RGB)
    res_flipped = face_mesh_model.process(rgb_flipped)

    if not res_flipped.multi_face_landmarks:
        # NOTE: we still return the RAW mediapipe landmark list (lm_orig),
        # not the frontalized numpy array. Drawing code (icd.py::draw_analysis,
        # photo.py) needs objects with .x/.y/.z in the *original* image's
        # pixel space to paint overlays on the actual photo -- frontalized
        # coordinates are a measurement-only space and would misalign with
        # the source image if drawn directly.
        return list(lm_orig), metrics_orig

    lm_flipped = res_flipped.multi_face_landmarks[0].landmark
    points_flipped = frontalize_face(lm_flipped, w, h)
    metrics_flipped = get_all_metrics(points_flipped, w, h)

    final_metrics = {}

    for block_name in metrics_orig.keys():
        final_metrics[block_name] = {}
        for metric_key, metric_obj in metrics_orig[block_name].items():

            if hasattr(metric_obj, 'value'):
                val_orig = metric_obj.value
                val_flipped = metrics_flipped[block_name][metric_key].value

                if val_orig is not None and val_flipped is not None:
                    avg_value = round((val_orig + val_flipped) / 2.0, 4)

                    metric_obj.value = avg_value

                final_metrics[block_name][metric_key] = metric_obj
            else:
                final_metrics[block_name][metric_key] = metric_obj

    return list(lm_orig), final_metrics
