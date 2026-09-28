from __future__ import annotations

import logging
import os
from typing import List

import numpy as np
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from mini_analysis.pipeline import MiniMetricPage

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
_jinja_env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR))


def build_mini_pdf_bytes(image_crop_bgr: np.ndarray, pages: List[MiniMetricPage]) -> bytes:
    """Renders the free-preview PDF: N metric pages + 1 fixed promo page."""
    template = _jinja_env.get_template("mini_report.html")
    
    # img_src тепер лежить всередині кожного об'єкта page
    html_content = template.render(pages=pages)
    
    return HTML(string=html_content).write_pdf()