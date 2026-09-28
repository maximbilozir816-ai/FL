# face/metrics/features/summary_advice.py
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from jinja2 import Template

logger = logging.getLogger(__name__)


# ==============================================================================
# ДИНАМІЧНИЙ РЕСАЙЗ ТЕКСТУ (ЯК В OVERALL IMPRESSION)
# ==============================================================================
def wrap_advice_html(content: str, accent_color: str = "#F8B12A") -> str:
    if not content:
        return ""
        
    raw_text = re.sub(r'<[^>]+>', '', content).strip()
    text_len = len(raw_text)

    # Базові розміри
    p_size = 11.5
    bullet_size = 11.5
    impact_size = 11.0

    # Адаптація під об'єм тексту
    if text_len > 1200:
        p_size = 10.5; 
        bullet_size = 10.5; 
        impact_size = 10.0
    elif text_len > 900:
        p_size = 10.2; 
        bullet_size = 10.2; 
        impact_size = 9.7
    elif text_len > 800:
        p_size = 10.3; 
        bullet_size = 10.3; 
        impact_size = 9.9
    elif text_len > 700:
        p_size = 10.5; 
        bullet_size = 10.5; 
        impact_size = 10.1
    elif text_len > 600:
        p_size = 10.7; 
        bullet_size = 10.7; 
        impact_size = 10.3
    elif text_len > 500:
        p_size = 11.5; 
        bullet_size = 11.4; 
        impact_size = 11.0

    wrap_id = f"adv-box-{uuid.uuid4().hex[:8]}"

    dynamic_css = f"""
    <style>
    #{wrap_id} p {{ font-size: {p_size}pt !important; margin: 0 0 8px 0 !important; line-height: 1.45 !important; color: #E2E8F0 !important; text-align: justify !important; }}
    #{wrap_id} ul {{ font-size: {bullet_size}pt !important; margin: 0 0 10px 16px !important; padding: 0 !important; color: #E2E8F0 !important; line-height: 1.45 !important; }}
    #{wrap_id} ul li {{ margin-bottom: 6px !important; }}
    #{wrap_id} div.sa-impact {{ 
        font-size: {impact_size}pt !important; 
        border-left: 3px solid {accent_color} !important; 
        padding: 6px 10px !important; 
        margin: 0 0 10px 0 !important; 
        font-style: italic !important; 
        color: #94A3B8 !important; 
        line-height: 1.45 !important; 
        display: block !important;
    }}
    </style>
    """
    return f'{dynamic_css}<div id="{wrap_id}">{content}</div>'


# ==============================================================================
# ДОПОМІЖНА СТРУКТУРА ДЛЯ ОДНІЄЇ ПЛАШКИ ПОРАДИ
# ==============================================================================
@dataclass
class AdviceBoxData:
    icon: str            # емодзі-маркер
    title: str           # заголовок плашки
    body_html: str       # текст поради (вже обгорнутий)


# ==============================================================================
# КОНТЕКСТ ТА ШАБЛОН ФІНАЛЬНОЇ СТОРІНКИ
# ==============================================================================
@dataclass
class SummaryAdviceContext:
    geometry_advice: str = ""
    hair_grooming_summary: str = ""
    skin_summary: str = ""
    actionable_improvements: str = ""
    photo_src: Optional[str] = None
    theme_color: str = "#FAAF24"
    accent_color: str = "#F8B12A"

    def _build_advice_boxes(self) -> List[AdviceBoxData]:
        boxes: List[AdviceBoxData] = []

        if self.geometry_advice:
            boxes.append(AdviceBoxData(
                icon="&#x2702;",  # Код контурних ножиць ✂
                title="Haircut & Styling",
                body_html=wrap_advice_html(self.geometry_advice, self.accent_color),
            ))

        if self.hair_grooming_summary:
            boxes.append(AdviceBoxData(
                icon="&#x2338;",  # Або &#x2704; / &#x293A; для брів/бороди
                title="Brows & Facial Hair",
                body_html=wrap_advice_html(self.hair_grooming_summary, self.accent_color),
            ))

        if self.skin_summary:
            boxes.append(AdviceBoxData(
                icon="&#x2697;",  # Контурна баночка/догляд ⚗ / &#x25C7;
                title="Skincare & Texture Regimen",
                body_html=wrap_advice_html(self.skin_summary, self.accent_color),
            ))

        return boxes

    def render_html(self, page_num_str: str = "28", total_pages: int = 28) -> str:
        advice_boxes = self._build_advice_boxes()

        html_template = """
        <style>
        @page sa_isolated_page_size { 
            size: 210mm 340mm;
            margin: 0; 
        }
        .sa-page-wrapper {
            page: sa_isolated_page_size; 
            width: 210mm; 
            height: 297mm; 
            padding: 12mm 18mm 18mm 18mm;
            background: #040710; 
            color: #E2E8F0; 
            font-family: Arial, sans-serif;
            display: block;
            position: relative; 
            box-sizing: border-box;
            page-break-after: always;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }

        .sa-header {
            margin-bottom: 6mm;
            text-align: left;
            display: block;
        }
        .sa-title {
            font-size: 20pt;
            font-weight: 800;
            color: #FAAF24;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 0 0 2mm 0;
        }
        .sa-subtitle {
            font-size: 12pt;
            color: #94A3B8;
            margin: 0;
            font-weight: 500;
        }

        .sa-grid {
            display: block; 
            margin-bottom: 6mm;
            width: 100%;
        }
        .sa-box {
            background: transparent;
            border: none;
            padding: 0;
            box-sizing: border-box;
            margin-bottom: 7mm; 
            display: block;
        }
        .sa-box:last-child {
            margin-bottom: 0;
        }
        
        .sa-box-head {
            display: table;
            width: 100%;
            margin-bottom: 2mm;
        }
        .sa-box-icon {
            display: table-cell;
            width: 35px;
            font-size: 16pt;
            vertical-align: middle;
            font-family: 'Segoe UI Symbol', Arial, sans-serif;
        }
        .sa-box-title {
            display: table-cell;
            font-size: 15pt;
            font-weight: 800;
            color: #F8FAFC;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            vertical-align: middle;
        }
        .sa-box-body {
            display: block;
        }

        .sa-improvements-card {
            background: rgba(253, 174, 30, 0.1);
            border: 1px solid #F8B12A;
            border-radius: 8px;
            padding: 5mm 6mm;
            margin-bottom: 0;
            box-sizing: border-box;
            margin-top: 8mm;
            display: block;
        }
        .sa-improvements-title {
            font-size: 14pt;
            font-weight: 800;
            color: #F8B12A;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 3mm;
            display: block;
        }
        .sa-improvements-list {
            margin: 0;
            padding-left: 5mm;
            font-size: 11.25pt;
            line-height: 1.5;
            color: #E2E8F0;
        }
        .sa-improvements-list li {
            margin-bottom: 2mm;
        }
        .sa-improvements-list li:last-child {
            margin-bottom: 0;
        }
        .sa-tg-wrap {
            text-align: left;
            margin-top: 5mm;
            font-size: 10.5pt;
            display: block;
        }
        .sa-tg-label {
            color: #64748B;
            font-weight: 600;
        }
        .sa-tg-link {
            color: #4680dd;
            font-weight: bold;
            text-decoration: none;
        }
        </style>

        <div class="sa-page-wrapper">
            <div class="sa-header">
                <div class="sa-title">Style & Grooming Advisory</div>
                <div class="sa-subtitle">Personalized structural & visual recommendations</div>
            </div>

            <div class="sa-grid">
                {% for box in advice_boxes %}
                <div class="sa-box">
                    <div class="sa-box-head">
                        <div class="sa-box-icon">{{ box.icon }}</div>
                        <div class="sa-box-title">{{ box.title }}</div>
                    </div>
                    <div class="sa-box-body">
                        {{ box.body_html | safe }}
                    </div>
                </div>
                {% endfor %}
            </div>

            {% if ctx.actionable_improvements %}
            <div class="sa-improvements-card">
                <div class="sa-improvements-title">Recommended Action Plan</div>
                <ul class="sa-improvements-list">
                    {{ ctx.actionable_improvements | safe }}
                </ul>
            </div>
            {% endif %}
            
            <div class="sa-tg-wrap">
                <span class="sa-tg-label">Telegram: </span><a href="https://t.me/bp_guide_scoringAI_bot" target="_blank" class="sa-tg-link">@bp_guide_scoringAI_bot</a>
            </div>

        </div>
        """
        return Template(html_template).render(
            ctx=self,
            advice_boxes=advice_boxes,
        )


# ==============================================================================
# ГОЛОВНА ФУНКЦІЯ-БІЛДЕР
# ==============================================================================
def build_summary_advice_page(
    visual_profile: Dict[str, Any],
    theme_color: str = "#8B5CF6",
    accent_color: str = "#F8B12A",
    photo_src: Optional[str] = None,
) -> SummaryAdviceContext:
    logger.info("🎨 Building final Style & Grooming Advisory page.")

    return SummaryAdviceContext(
        geometry_advice=visual_profile.get("geometry_advice", ""),
        hair_grooming_summary=visual_profile.get("hair_grooming_summary", ""),
        skin_summary=visual_profile.get("skin_summary", ""),
        actionable_improvements=visual_profile.get("actionable_improvements", ""),
        photo_src=photo_src,
        theme_color=theme_color,
        accent_color=accent_color,
    )