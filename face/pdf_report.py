# face/pdf_report.py
"""
Simplified PDF report builder with unified Jinja2 template architecture.
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

try:
    from face.report_order import PDF_PAGE_ORDER
except ImportError:
    PDF_PAGE_ORDER = []

logging.getLogger('weasyprint').setLevel(logging.ERROR)
logging.getLogger('fontTools').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


@dataclass
class MetricItem:
    label: str
    value: str
    metric_key: str = ""
    score: Optional[float] = None
    ideal: Optional[float] = None
    feedback_text: Optional[str] = None
    pct: Optional[float] = None


@dataclass
class AnalysisPage:
    image_bytes: bytes
    metrics: List[MetricItem] = field(default_factory=list)
    title: str = "Facial Analysis"
    theme_color: str = "#8B5CF6"


class PDFReportBuilder:
    def __init__(self, template_dir: str = "face/templates"):
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_file_dir)

        search_paths = [
            template_dir,
            os.path.join(current_file_dir, "templates"),
            os.path.join(root_dir, "templates"),
            current_file_dir,
            root_dir,
        ]

        valid_paths = [path for path in search_paths if os.path.exists(path)]
        self.jinja_env = Environment(loader=FileSystemLoader(valid_paths))

    def _format_metric_page(self, p: AnalysisPage) -> Dict[str, Any]:
        """Format a metric page for Jinja2."""
        clean_title = p.title.replace("—", "").replace("-", "").strip()

        b64 = base64.b64encode(p.image_bytes).decode('utf-8')
        mime = "image/png"
        if p.image_bytes.startswith(b"\xff\xd8"):
            mime = "image/jpeg"

        processed_metrics = []
        for m in p.metrics:
            score = m.score
            pct = max(5.0, min(100.0, (score / 10.0) * 100.0)) if score is not None else 0.0

            ideal_str = None
            if m.ideal is not None:
                ideal_str = f"{m.ideal:.4f}" if isinstance(m.ideal, (int, float)) else str(m.ideal)

            processed_metrics.append({
                'label': m.label,
                'value': m.value,
                'metric_key': m.metric_key,
                'score': f"{score:.2f}" if score is not None else None,
                'pct': pct,
                'ideal': ideal_str,
                'feedback_text': getattr(m, 'feedback_text', None),
            })

        is_eye_overall = clean_title.upper() == "EYE AREA OVERALL IMPRESSION"
        eye_avg_score = "0.00"
        if is_eye_overall:
            scores = [float(m['score']) for m in processed_metrics if m['score'] is not None]
            if scores:
                eye_avg_score = f"{(sum(scores) / len(scores)):.2f}"

        return {
            'is_overview': False,
            'title': clean_title,
            'theme_color': p.theme_color,
            'img_src': f"data:{mime};base64,{b64}",
            'metrics': processed_metrics,
            'is_eye_overall': is_eye_overall,
            'eye_avg_score': eye_avg_score,
        }

    def build(
        self,
        pages: List[AnalysisPage],
        radar_chart_b64: str = "",
        overview_ctx: Optional[Any] = None,
        balance_overview_ctx: Optional[Any] = None,
        nose_overview_ctx: Optional[Any] = None,
        lips_overview_ctx: Optional[Any] = None,
        brows_overview_ctx: Optional[Any] = None,
        dmetrics_overview_ctx: Optional[Any] = None,
        ametrics_overview_ctx: Optional[Any] = None,
        dimorphism_overview_ctx: Optional[Any] = None,
        angularity_overview_ctx: Optional[Any] = None,
        overall_score_ctx: Optional[Any] = None,
        radar_summary_ctx: Optional[Any] = None,
        overall_impression_ctx: Optional[Any] = None,  # NEW
        summary_advice_ctx: Optional[Any] = None,
    ) -> bytes:
        """Build PDF with unified page order and bounded concurrency."""
        unified_pages = []

        overview_map = {
            'overall_score_ctx': overall_score_ctx,
            'radar_summary_ctx': radar_summary_ctx,
            'overall_impression_ctx': overall_impression_ctx, # NEW
            'overview_ctx': overview_ctx,
            'balance_overview_ctx': balance_overview_ctx,
            'nose_overview_ctx': nose_overview_ctx,
            'lips_overview_ctx': lips_overview_ctx,
            'brows_overview_ctx': brows_overview_ctx,
            'dmetrics_overview_ctx': dmetrics_overview_ctx,
            'ametrics_overview_ctx': ametrics_overview_ctx,
            'dimorphism_overview_ctx': dimorphism_overview_ctx,
            'angularity_overview_ctx': angularity_overview_ctx,
            'summary_advice_ctx': summary_advice_ctx,
        }
        metric_pages_map: Dict[str, AnalysisPage] = {}
        unmapped_pages: List[AnalysisPage] = []

        for p in pages:
            key = None
            if p.metrics and len(p.metrics) > 0 and p.metrics[0].metric_key:
                key = p.metrics[0].metric_key

            if key:
                metric_pages_map[key] = p
            else:
                unmapped_pages.append(p)

        processed_metric_keys = set()

        order_list = PDF_PAGE_ORDER if PDF_PAGE_ORDER else list(overview_map.keys()) + list(metric_pages_map.keys())

        for item_key in order_list:
            if item_key in overview_map:
                ctx_obj = overview_map[item_key]
                if ctx_obj is not None:
                    ov_type = item_key.replace('_ctx', '')
                    unified_pages.append({
                        'is_overview': True,
                        'overview_type': ov_type,
                        'ctx': ctx_obj
                    })
            elif item_key in metric_pages_map:
                p = metric_pages_map[item_key]
                unified_pages.append(self._format_metric_page(p))
                processed_metric_keys.add(item_key)
            else:
                logger.debug(f"Order item '{item_key}' not found (skipped).")

        for key, p in metric_pages_map.items():
            if key not in processed_metric_keys:
                logger.warning(f"Metric '{key}' not in report_order.py — appending to end.")
                unified_pages.append(self._format_metric_page(p))

        for p in unmapped_pages:
            logger.warning(f"Page '{p.title}' without metric_key appended to end.")
            unified_pages.append(self._format_metric_page(p))

        total_pages = len(unified_pages) + (1 if radar_chart_b64 else 0)

        template = self.jinja_env.get_template('report.html')
        html_content = template.render(
            pages=unified_pages,
            radar_chart_b64=radar_chart_b64,
            total_pages=total_pages
        )

        return HTML(string=html_content).write_pdf()