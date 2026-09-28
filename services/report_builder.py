# services/report_builder.py
"""
Turns raw TTA metrics into: the AI payload, the per-metric PDF pages, the
six overview contexts, the overall-score page, and finally the rendered
PDF bytes. This is the split-out second half of the old monolithic
`photo.py` (steps 5-7).
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from config import settings
from face.ai_analyzer import _build_fallback_dict, generate_face_summaries
from face.metrics.features import ACTIVE_METRICS as METRICS_CONFIG
from face.metrics.features.Dmetrics.overview import build_dmetrics_overview
from face.metrics.features.Overall_score import build_overall_score_page
from face.metrics.features.brows.overview import build_brows_overview
from face.metrics.features.dimorphism import build_dimorphism_overview
from face.metrics.features.eye_area.overview import build_eye_area_overview
from face.metrics.features.facialbalance.overview import build_facial_balance_overview
from face.metrics.features.lips.overview import build_lips_overview
from face.metrics.features.nose.overview import build_nose_overview
from face.metrics.features.overall_impression import build_overall_impression_page
from face.metrics.features.radar_summary import build_radar_summary_page
from face.metrics.features.summary_advice import build_summary_advice_page
from face.metrics.scoring import compute_score
from face.pdf_report import AnalysisPage, MetricItem, PDFReportBuilder
from face.utils import get_pdf_executor

logger = logging.getLogger(__name__)


@dataclass
class MetricsBundle:
    report_pages: List[AnalysisPage] = field(default_factory=list)
    ai_payload: Dict[str, Any] = field(default_factory=dict)
    overview_measurements: Dict[str, float] = field(default_factory=dict)
    balance_scores: Dict[str, float] = field(default_factory=dict)
    individual_metrics_list: List[Dict[str, Any]] = field(default_factory=list)
    log_metrics: List[str] = field(default_factory=list)
    overview_photo_src: Optional[str] = None
    image_b64: str = ""


def build_metrics_bundle(metrics: dict, img_crop: np.ndarray, lm_crop: Any, w_c: int, h_c: int) -> MetricsBundle:
    """Walks ACTIVE_METRICS, builds per-metric PDF pages, and assembles the
    structured payload later sent to the AI model."""
    bundle = MetricsBundle(
        ai_payload={
            "eye_area": {}, "facial_balance": {}, "nose": {}, "lips": {},
            "brows": {}, "facial_dimensions": {}, "dimorphism": {},
        }
    )

    for cfg in METRICS_CONFIG:
        key = cfg["key"]
        m_data = metrics.get(key, {})

        if cfg.get("is_complex"):
            _handle_complex_metric(cfg, m_data, img_crop, lm_crop, w_c, h_c, bundle)
        else:
            _handle_simple_metric(cfg, m_data, img_crop, lm_crop, w_c, h_c, bundle)

    _, buffer = cv2.imencode(".jpg", img_crop)
    bundle.overview_photo_src = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode()}"
    bundle.image_b64 = base64.b64encode(buffer).decode("utf-8")

    return bundle


def _handle_complex_metric(cfg: dict, m_data: dict, img_crop, lm_crop: Any, w_c: int, h_c: int, bundle: MetricsBundle) -> None:
    key = cfg["key"]
    if not m_data or m_data.get("total") == 0:
        return

    items_data, overall_score = cfg["complex_builder"](m_data, cfg)
    overall_score = float(overall_score)

    if key in ["thirds", "fifths", "facial_index"]:
        bundle.balance_scores[key] = overall_score
        bundle.ai_payload["facial_balance"][cfg["title"]] = {
            "user_score": round(overall_score, 2),
            "ideal_score": 10.0,
            "components": [f"{it['label']}: {it['value']} (ideal: {it['ideal']})" for it in items_data],
        }

    current_feedback = None
    feedback_func = cfg.get("feedback_func")
    if callable(feedback_func):
        current_feedback = feedback_func(m_data)

    metric_items = [
        MetricItem(
            label=item["label"],
            value=item["value"],
            ideal=item["ideal"],
            metric_key=key,
            score=overall_score,
            pct=int(overall_score * 10),
            feedback_text=current_feedback if i == 0 else None,
        )
        for i, item in enumerate(items_data)
    ]

    bundle.log_metrics.append(f"{key.upper()} Score: {overall_score:.2f}")
    bundle.individual_metrics_list.append({
        "name": cfg["title"].split("(")[0].strip(),
        "score": overall_score,
        "color": cfg.get("theme_color", "#3B82F6"),
    })

    img_bytes = cfg["drawer"](img_crop, lm_crop, w_c, h_c)
    bundle.report_pages.append(AnalysisPage(
        title=cfg["title"],
        image_bytes=img_bytes,
        theme_color=cfg.get("theme_color", "#3B82F6"),
        metrics=metric_items,
    ))


def _handle_simple_metric(cfg: dict, m_data: dict, img_crop, lm_crop: Any, w_c: int, h_c: int, bundle: MetricsBundle) -> None:
    key = cfg["key"]

    ratio_val = None
    if m_data and m_data.get(cfg["ratio_key"]):
        metric_obj = m_data.get(cfg["ratio_key"])
        if hasattr(metric_obj, "value"):
            ratio_val = metric_obj.value
        elif isinstance(metric_obj, (int, float)):
            ratio_val = metric_obj
        else:
            ratio_val = getattr(metric_obj, "value", None)

    if ratio_val is not None:
        bundle.overview_measurements[key] = float(ratio_val)

    scoring_cfg = cfg.get("scoring", {})
    ideal_val = scoring_cfg.get("ideal") if isinstance(scoring_cfg, dict) else getattr(scoring_cfg, "ideal", None)
    ideal_str = f"{ideal_val:.4f}" if ideal_val is not None else None

    if ratio_val is None:
        score, str_ratio, score_fmt, ideal_str = 1.0, "N/A", "1.00", None
    else:
        score = compute_score(ratio_val, cfg["scoring"])
        str_ratio = f"{ratio_val:.4f}"
        score_fmt = f"{score:.2f}"

    if key in ["thirds", "fifths", "facial_index"]:
        bundle.balance_scores[key] = float(score)

    val_to_record = float(ratio_val) if ratio_val is not None else 0.0
    ideal_to_record = float(ideal_val) if ideal_val is not None else 0.0
    metric_summary = {
        "user_value": round(val_to_record, 4),
        "ideal_canon": round(ideal_to_record, 4),
        "metric_score_out_of_10": round(float(score), 2),
    }

    section_map = {
        "eye_area": ["icd", "ocd", "esize"],
        "nose": ["nose_height", "nose_to_lips", "nose_width"],
        "lips": ["lips_to_nose", "lips_width", "lips_weight"],
        "brows": ["custom_eyebrow_density", "eyebrow_density", "eyebrow_tilt", "eye_eyebrow"],
        "facial_dimensions": ["fwhr", "jaw_facew", "chin_lowerth"],
    }
    for section, keys in section_map.items():
        if key in keys:
            bundle.ai_payload[section][cfg["title"]] = metric_summary

    if key in ["fwhr", "jaw_facew", "chin_lowerth", "eye_eyebrow", "eyebrow_density", "lips_weight"]:
        bundle.ai_payload["dimorphism"][cfg["title"]] = metric_summary

    current_feedback = None
    if ratio_val is not None:
        feedback_func = cfg.get("feedback_func")
        if callable(feedback_func):
            current_feedback = feedback_func(float(ratio_val))

    bundle.log_metrics.append(f"{key.upper()} Ratio: {str_ratio} (Score: {score_fmt}/10)")
    bundle.individual_metrics_list.append({
        "name": cfg["title"].split("(")[0].strip(),
        "score": float(score),
        "color": cfg.get("theme_color", "#3B82F6"),
    })

    img_bytes = cfg["drawer"](img_crop, lm_crop, w_c, h_c)
    bundle.report_pages.append(AnalysisPage(
        title=cfg["title"],
        image_bytes=img_bytes,
        theme_color=cfg.get("theme_color", "#3B82F6"),
        metrics=[MetricItem(
            label=cfg["label"], value=str_ratio, metric_key=key,
            feedback_text=current_feedback, score=float(score),
            pct=int(score * 10), ideal=ideal_str,
        )],
    ))


async def request_ai_summaries(bundle: MetricsBundle, telegram_id: int) -> Dict[str, Any]:
    if not settings.ai_analysis_enabled:
        logger.info(f"[INFO] User {telegram_id}: AI analysis disabled, using fallback texts.")
        return _build_fallback_dict()

    ai_texts = await generate_face_summaries(metrics_payload=bundle.ai_payload, image_b64=bundle.image_b64)
    logger.info(f"[INFO] User {telegram_id}: AI generation complete.")
    return ai_texts


def build_overview_contexts(
    bundle: MetricsBundle, 
    ai_texts: Dict[str, Any],
    force_f: Optional[float] = None,
    force_d: Optional[float] = None
) -> Dict[str, Any]:
    
    photo_src = bundle.overview_photo_src

    overview_ctx = build_eye_area_overview(
        measurements=bundle.overview_measurements,
        summary_text=ai_texts.get("eye_summary", ""), match_text=ai_texts.get("eye_match", ""),
        photo_src=photo_src,
    )
    balance_overview_ctx = build_facial_balance_overview(
        scores=bundle.balance_scores,
        summary_text=ai_texts.get("balance_summary", ""), match_text=ai_texts.get("balance_match", ""),
        photo_src=photo_src,
    )
    nose_overview_ctx = build_nose_overview(
        measurements=bundle.overview_measurements,
        summary_text=ai_texts.get("nose_summary", ""), match_text=ai_texts.get("nose_match", ""),
        photo_src=photo_src,
    )
    lips_overview_ctx = build_lips_overview(
        measurements=bundle.overview_measurements,
        summary_text=ai_texts.get("lips_summary", ""), match_text=ai_texts.get("lips_match", ""),
        photo_src=photo_src,
    )
    brows_overview_ctx = build_brows_overview(
        measurements=bundle.overview_measurements,
        summary_text=ai_texts.get("brows_summary", ""), match_text=ai_texts.get("brows_match", ""),
        photo_src=photo_src,
    )
    dmetrics_overview_ctx = build_dmetrics_overview(
        measurements=bundle.overview_measurements,
        summary_text=ai_texts.get("dmetrics_summary", ""), match_text=ai_texts.get("dmetrics_match", ""),
        photo_src=photo_src,
    )
    dimorphism_overview_ctx = build_dimorphism_overview(
        measurements=bundle.overview_measurements, summary_text=ai_texts.get("dimorphism_summary", "")
    )

    def _score_safe(obj: Any, attr: str = "score_str") -> float:
        try:
            val = getattr(obj, attr, "0.0")
            return float(val) if val else 0.0
        except (ValueError, TypeError, AttributeError):
            return 0.0

    overview_scores_map = {
        "eye_overview": _score_safe(overview_ctx),
        "balance_overview": _score_safe(balance_overview_ctx),
        "nose_overview": _score_safe(nose_overview_ctx),
        "lips_overview": _score_safe(lips_overview_ctx),
        "brows_overview": _score_safe(brows_overview_ctx),
        "dmetrics_overview": _score_safe(dmetrics_overview_ctx),
    }

    raw_dim = _score_safe(dimorphism_overview_ctx, "dimorphism_score")
    if raw_dim == 0.0:
        raw_dim = _score_safe(dimorphism_overview_ctx, "score_str")

    overall_score_ctx = build_overall_score_page(
        overview_scores=overview_scores_map,
        dimorphism_score=raw_dim if raw_dim > 0 else 7.0,
        photo_src=photo_src, ai_summary_text="", theme_color="#3B82F6",
        force_f_score=force_f,  # <--- ДОДАНО
        force_d_score=force_d   # <--- ДОДАНО
    )

    radar_summary_ctx = build_radar_summary_page(
        overview_contexts={
            "eye_overview": overview_ctx, "balance_overview": balance_overview_ctx,
            "nose_overview": nose_overview_ctx, "lips_overview": lips_overview_ctx,
            "brows_overview": brows_overview_ctx, "dmetrics_overview": dmetrics_overview_ctx,
        },
        individual_metrics=bundle.individual_metrics_list,
    )

    overall_impression_ctx = build_overall_impression_page(summary_text=ai_texts.get("overall_summary", ""))

    visual_profile = {
        "geometry_summary": ai_texts.get("geometry_summary", ""),
        "geometry_advice": ai_texts.get("geometry_advice", ""),
        "skin_summary": ai_texts.get("skin_summary", ""),
        "hair_grooming_summary": ai_texts.get("hair_grooming_summary", ""),
        "actionable_improvements": ai_texts.get("actionable_improvements", ""),
    }
    summary_advice_ctx = build_summary_advice_page(
        visual_profile=visual_profile, photo_src=photo_src,
        theme_color="#8B5CF6", accent_color="#F8B12A",
    )

    return {
        "overview_ctx": overview_ctx,
        "balance_overview_ctx": balance_overview_ctx,
        "nose_overview_ctx": nose_overview_ctx,
        "lips_overview_ctx": lips_overview_ctx,
        "brows_overview_ctx": brows_overview_ctx,
        "dmetrics_overview_ctx": dmetrics_overview_ctx,
        "dimorphism_overview_ctx": dimorphism_overview_ctx,
        "overall_score_ctx": overall_score_ctx,
        "radar_summary_ctx": radar_summary_ctx,
        "overall_impression_ctx": overall_impression_ctx,
        "summary_advice_ctx": summary_advice_ctx,
    }


async def build_pdf_bytes(bundle: MetricsBundle, contexts: Dict[str, Any], telegram_id: int) -> bytes:
    pdf_builder = PDFReportBuilder()
    pdf_executor = get_pdf_executor()

    pdf_bytes = await pdf_executor.render_pdf_async(
        pdf_builder.build,
        pages=bundle.report_pages,
        radar_chart_b64=None,
        **contexts,
    )

    logger.info(f"[INFO] User {telegram_id}: PDF generated ({len(bundle.report_pages)} metric pages).")
    return pdf_bytes