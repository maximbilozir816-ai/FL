from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any, Dict, List

# Імпортуємо справжню функцію оцінювання та функцію малювання сітки
from face.metrics.scoring import compute_score
from face.utils.mesh_drawer import generate_mesh_photo_b64

logger = logging.getLogger(__name__)

try:
    from face.metrics.features.eye_area import icd as _icd_mod
    from face.metrics.features.eye_area import ocd as _ocd_mod
    from face.metrics.features.nose import nose_height as _nose_height_mod
    from face.metrics.features.nose import nose_width as _nose_width_mod

    _FEATURE_MODULES = [_icd_mod, _ocd_mod, _nose_height_mod, _nose_width_mod]
except ImportError as e:  
    logger.error(f"[ERROR] mini_analysis.pipeline: could not import feature modules ({e}).")
    _FEATURE_MODULES = []


@dataclass
class MiniMetricPage:
    title: str
    theme_color: str
    label: str
    value_str: str
    ideal_str: str
    score: float       # Справжній бал
    img_src: str       # Унікальне фото з лініями (base64)


def build_mini_metric_pages(processed) -> List[MiniMetricPage]:
    """`processed` is a `services.photo_processor.ProcessedPhoto` instance."""
    pages: List[MiniMetricPage] = []

    for module in _FEATURE_MODULES:
        cfg: Dict[str, Any] = module.FEATURE_CONFIG
        block = processed.metrics.get(cfg["key"]) if isinstance(processed.metrics, dict) else None
        ratio_metric = block.get(cfg["ratio_key"]) if block else None

        if ratio_metric is None or getattr(ratio_metric, "value", None) is None:
            logger.warning(f"[WARN] Mini-analysis: metric block '{cfg['key']}' missing, skipping.")
            continue

        value = float(ratio_metric.value)
        ideal = float(cfg["scoring"].ideal)

        # 1. Рахуємо точний бал
        actual_score = compute_score(value, cfg["scoring"])

        # 2. Малюємо лінії на фото (викликаємо drawer з конфігу метрики)
        drawer_func = cfg.get("drawer")
        img_b64 = ""
        if drawer_func:
            # Створюємо копію фото, щоб не малювати всі метрики на одному зображенні
            img_with_mesh = processed.image_crop_bgr.copy()

            # Додаємо напівпрозору сітку (змінює img_with_mesh in-place)
            generate_mesh_photo_b64(
                img_numpy=img_with_mesh,
                landmarks=processed.landmarks,
                width=processed.width_crop,
                height=processed.height_crop,
                alpha_opacity=0.9  # Прозорість сітки (зменшіть, якщо хочете ще прозорішу)
            )

            # Передаємо фото з уже накладеною сіткою у функцію малювання ліній
            img_bytes = drawer_func(
                img_with_mesh, 
                processed.landmarks, 
                processed.width_crop, 
                processed.height_crop
            )
            if img_bytes:
                encoded = base64.b64encode(img_bytes).decode("utf-8")
                img_b64 = f"data:image/jpeg;base64,{encoded}"

        pages.append(
            MiniMetricPage(
                title=cfg["title"],
                theme_color=cfg["theme_color"],
                label=cfg["label"],
                value_str=f"{value:.4f}",
                ideal_str=f"{ideal:.4f}",
                score=actual_score,
                img_src=img_b64,
            )
        )

    return pages