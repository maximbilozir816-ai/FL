import cv2
import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Any

logger = logging.getLogger(__name__)


@dataclass
class CropConfig:
    target_ratio_x: float = 0.60
    target_ratio_y: float = 0.50
    min_orig_face_width_px: int = 120  
    # pad_color_bgr залишаємо у класі, щоб не зламати інші частини коду, 
    # якщо вони на нього посилаються, але тут він більше не використовується.
    pad_color_bgr: Tuple[int, int, int] = (16, 7, 4)


def smart_face_crop(
    image: np.ndarray, 
    face_mesh: Any, 
    config: CropConfig = CropConfig()
) -> Optional[np.ndarray]:
    h_orig, w_orig = image.shape[:2]

    try:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            logger.warning("Cropper: No face detected on raw image.")
            return None

        lm = results.multi_face_landmarks[0].landmark

        xs = [int(p.x * w_orig) for p in lm]
        ys = [int(p.y * h_orig) for p in lm]

        x_min, x_max = max(0, min(xs)), min(w_orig, max(xs))
        y_min, y_max = max(0, min(ys)), min(h_orig, max(ys))

        face_w = x_max - x_min
        face_h = y_max - y_min

        if face_w < config.min_orig_face_width_px:
            logger.warning(f"Cropper: Face too small ({face_w}px < {config.min_orig_face_width_px}px)")
            return None

        center_x = x_min + face_w // 2
        center_y = y_min + face_h // 2

        # Обчислюємо бажані розміри під пропорцію 70x95
        new_w = int(face_w / config.target_ratio_x)
        new_h = int(new_w * (95 / 70))

        # Обчислюємо ідеальні координати (можуть виходити за межі фото)
        ideal_x1 = center_x - new_w // 2
        ideal_x2 = ideal_x1 + new_w
        ideal_y1 = center_y - int(new_h * config.target_ratio_y)
        ideal_y2 = ideal_y1 + new_h

        # Просто обрізаємо координати до реальних меж оригінального фото.
        # Більше ніяких "padded_img" та штучних фонів.
        crop_x1 = max(0, ideal_x1)
        crop_y1 = max(0, ideal_y1)
        crop_x2 = min(w_orig, ideal_x2)
        crop_y2 = min(h_orig, ideal_y2)

        return image[crop_y1:crop_y2, crop_x1:crop_x2]

    except Exception as e:
        logger.error(f"smart_face_crop failed: {e}", exc_info=True)
        return None