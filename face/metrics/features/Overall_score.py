# face/metrics/features/Overall_score.py
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from jinja2 import Template

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. WEIGHTS, SCALES & VISUAL CUSTOMIZATION
# ==============================================================================

PHOTO_BORDER_COLOR = "#808080"  
PHOTO_SHADOW_RGBA = "rgba(248, 177, 42, 0.4)"  

FEATURES_WEIGHTS: Dict[str, float] = {
    "eye_overview": 1.65,
    "balance_overview": 1.65,
    "nose_overview": 1.0,
    "lips_overview": 0.75,
    "brows_overview": 0.7,
    "dmetrics_overview": 1.2,
}

# Final score weights (must sum to 1.0 / 100%)
FINAL_SCORE_WEIGHTS: Dict[str, float] = {
    "features": 0.85,    # 85% -- geometry and proportions
    "dimorphism": 0.15,  # 15% -- sexual dimorphism
}

LEVELS_CONFIG = [
    {
        "min_score": 9.0,
        "level_title": "PSL God",
    },
    {
        "min_score": 8.0,
        "level_title": "Chad",
    },
    {
        "min_score": 7.5,
        "level_title": "Chad-lite",
    },
    {
        "min_score": 7.0,
        "level_title": "HTN+(High Tier Normie+)",
    },
    {
        "min_score": 6.25,
        "level_title": "HTN(High Tier Normie)",
    },
    {
        "min_score": 5.75,
        "level_title": "HTN-(High Tier Normie-)",
    },
    {
        "min_score": 5.0,
        "level_title": "MTN+(Mid Tier Normie+)",
    },
    {
        "min_score": 4.5,
        "level_title": "MTN(Mid Tier Normie)",
    },
    {
        "min_score": 4.0,
        "level_title": "MTN-(Mid Tier Normie-)",
    },
    {
        "min_score": 3.5,
        "level_title": "LTN+(Low Tier Normie+)",
    },
    {
        "min_score": 3.25,
        "level_title": "LTN(Low Tier Normie)",
    },
    {
        "min_score": 3.0,
        "level_title": "LTN-(Low Tier Normie-)",
    },
    {
        "min_score": 0.0,
        "level_title": "Sub 3",
    },
]

PERCENTILE_CURVE_POINTS = [
    (0.0, 100.0),  # Найгірший результат
    (3.0, 98.0),   # LTN- (Нижні 2%)
    (3.25, 95.0),  # LTN
    (3.5, 92.0),   # LTN+
    (4.0, 85.0),   # MTN-
    (4.5, 70.0),   # Початок більшості (MTN) - 75-й перцентиль
    (5.0, 50.0),   # Абсолютна медіана (MTN+) - половина гірше, половина краще
    (5.75, 30.0),  # Кінець середнього класу (HTN-) - Топ 25%
    (6.25, 15.0),  # HTN - Топ 10% (дуже привабливі, але ще не моделі)
    (7.0, 3.5),    # HTN+ - Топ 3.5% (старт модельної зовнішності)
    (7.5, 1.5),    # Chad-lite - Топ 1.5%
    (8.0, 0.5),    # Chad - Топ 0.5% (1 на 200 людей)
    (9.0, 0.05),   # PSL God - Топ 0.05% (1 на 2000 людей)
    (10.0, 0.01)   # Абсолютний ідеал
]
# ==============================================================================

@dataclass
class SubScoreItem:
    label: str
    score: float
    raw_val: Optional[float] = None

    @property
    def score_str(self) -> str:
        return f"{self.score:.2f}"


@dataclass
class OverallScoreContext:
    final_score: float
    features_score: float
    dimorphism_score: float
    top_text: str
    level_title: str
    curve_pos_pct: float             
    photo_src: Optional[str] = None
    theme_color: str = "#FAAF24"        
    accent_teal: str = "#00e676"        
    photo_border_color: str = "#808080" 
    photo_shadow_rgba: str = "rgba(248, 177, 42, 0.4)" 
    sub_scores: List[SubScoreItem] = field(default_factory=list)

    @property
    def final_score_str(self) -> str:
        return f"{self.final_score:.2f}"

    def render_html(self, page_num_str: str = "01", total_pages: int = 12) -> str:
        html_template = """
        <style>
        @page overall_page_size { 
            size: 210mm 240mm; 
            margin: 0; 
        }
        
        .overall-page {
            page: overall_page_size;
            width: 210mm; 
            height: 240mm; 
            padding: 10mm 16mm;
            background: #040710; 
            position: relative;
            color: #E2E8F0; 
            font-family: Arial, sans-serif;
            page-break-after: always;
            display: block; 
            text-align: center;
            box-sizing: border-box;
            -webkit-print-color-adjust: exact; 
            print-color-adjust: exact;
        }
        
        .overall-page * { 
            box-sizing: border-box; 
            margin: 0; 
            padding: 0; 
        }
        
        .overall-page .header { 
            text-align: center; 
            margin-bottom: 4mm; 
            width: 100%; 
        }
        .overall-page h1 { 
            font-size: 28pt; 
            font-weight: 800; 
            letter-spacing: 0.5px; 
            color: {{ ctx.theme_color }}; 
            text-transform: uppercase; 
            margin-bottom: 1.5mm; 
            margin-top: 0;
        }
        .overall-page .sub-link-wrap {
            font-size: 10.5pt;
        }
        .overall-page .tg-label {
            color: #64748B;
            font-weight: 600;
        }
        .overall-page .tg-link {
            color: #4680dd;
            font-weight: bold;
            text-decoration: none;
        }

        .overall-page .photo-wrap {
            width: 70mm; 
            height: 95mm;
            margin: 1mm auto 4mm auto;
            border: 1px solid {{ ctx.photo_border_color }};
            background: #0B1121; 
            overflow: hidden;
            text-align: center;
        }
        .overall-page .photo-wrap img { 
            width: 100%; 
            height: 100%; 
            object-fit: cover; 
            display: block; 
            margin: 0; 
            padding: 0; 
        }
        .overall-page .photo-placeholder { color: #475569; font-size: 10pt; text-align: center; padding: 10px; }

        .overall-page .big-score-val { font-family: 'Arial Black', Arial, sans-serif; font-size: 36pt; font-weight: 900; color: #ffffff; line-height: 1.0; text-align: center; width: 100%; }
        .overall-page .big-score-max { font-size: 11.5pt; font-weight: 600; color: #94A3B8; text-align: center; margin-top: 1mm; margin-bottom: 3mm; width: 100%; }

        .overall-page .top-text { font-size: 13pt; font-weight: 700; color: #ffffff; text-align: center; margin-bottom: 3mm; width: 100%; }
        
        .overall-page .pct-highlight {
            color: {{ ctx.accent_teal }}; /* Золотий/помаранчевий (темовий колір). Можеш змінити на свій */
            font-size: 13pt; /* Робимо сам відсоток ще більшим за основний текст */
            font-weight: 900;
        }
        
        .overall-page .curve-container { width: 130mm; height: 35mm; margin: 0 auto 1mm auto; text-align: center; }
        .overall-page .curve-svg { width: 100%; height: 100%; display: block; }
        
        .overall-page .level-title { font-size: 13pt; font-weight: 700; color: {{ ctx.accent_teal }}; font-style: italic; text-align: center; margin-top: 2mm; margin-bottom: 4mm; width: 100%; }

        .overall-page .sub-scores-table {
            display: table;
            width: 150mm; 
            margin: 0 auto; 
            padding: 2.5mm 0; 
            border-top: 1px dashed #1E293B; 
            border-bottom: 1px dashed #1E293B;
            table-layout: fixed;
        }
        .overall-page .sub-item { display: table-cell; text-align: center; width: 50%; vertical-align: middle; }
        .overall-page .sub-label { font-size: 12pt; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 1mm; }
        .overall-page .sub-val { font-size: 22pt; font-weight: 800; color: #FFFFFF; }
        .overall-page .sub-max { font-size: 12pt; font-weight: 600; color: #64748B; }
        </style>
        
        <div class="overall-page">
            <div class="header">
                <h1>Overall Score</h1>
                <div class="sub-link-wrap">
                    <span class="tg-label">Telegram: </span><a href="https://t.me/bp_guide_scoringAI_bot" target="_blank" class="tg-link">@bp_guide_scoringAI_bot</a>
                </div>
            </div>
            
            <div class="photo-wrap">
                {% if ctx.photo_src %}
                    <img src="{{ ctx.photo_src }}" alt="User Face">
                {% else %}
                    <div class="photo-placeholder">No Photo Available</div>
                {% endif %}
            </div>
            
            <div class="big-score-val">{{ ctx.final_score_str }}</div>
            <div class="big-score-max">out of 10</div>
            
            <div class="top-text">{{ ctx.top_text }}</div>
            
            <div class="curve-container">
                <svg class="curve-svg" viewBox="0 0 300 85" preserveAspectRatio="none">
                    <line x1="10" y1="75" x2="290" y2="75" stroke="#1E293B" stroke-width="1.5" />
                    <path d="M 10 75 C 80 75, 110 20, 150 20 C 190 20, 220 75, 290 75 L 290 75 L 10 75 Z" fill="rgba(0, 230, 118, 0.12)" />
                    <path d="M 10 75 C 80 75, 110 20, 150 20 C 190 20, 220 75, 290 75" fill="none" stroke="#475569" stroke-width="2.5" />
                    {% set indicator_x = 10 + (280 * (ctx.curve_pos_pct / 100.0)) %}
                    <line x1="{{ indicator_x }}" y1="10" x2="{{ indicator_x }}" y2="75" stroke="{{ ctx.accent_teal }}" stroke-width="2.5" />
                    <circle cx="{{ indicator_x }}" cy="10" r="4" fill="{{ ctx.accent_teal }}" />
                </svg>
            </div>
            
            <div class="level-title">{{ ctx.level_title }}</div>

            <div class="sub-scores-table">
                {% for item in ctx.sub_scores %}
                <div class="sub-item">
                    <span class="sub-label">{{ item.label }}</span>
                    <div>
                        <span class="sub-val">{{ item.score_str }}</span>
                        <span class="sub-max">/10</span>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        """
        return Template(html_template).render(ctx=self, page_num_str=page_num_str, total_pages=total_pages)


def _get_level_info(score: float) -> dict:
    for item in LEVELS_CONFIG:
        if score >= item["min_score"]:
            return item
    return LEVELS_CONFIG[-1]


def calculate_top_percentile(score: float) -> float:
    # Використовуємо наш новий масив замість локального
    points = PERCENTILE_CURVE_POINTS

    # Знаходимо проміжок, у який потрапляє бал
    for i in range(len(points) - 1):
        score1, pct1 = points[i]
        score2, pct2 = points[i+1]
        
        if score1 <= score <= score2:
            # Математична пропорція (лінійна інтерполяція)
            fraction = (score - score1) / (score2 - score1)
            dynamic_pct = pct1 + fraction * (pct2 - pct1)
            
            # Розумне округлення:
            # Якщо результат входить у топ 1% (екстремальна рідкість), залишаємо 2 знаки (напр. 0.05)
            # Якщо звичайний відсоток, округлюємо до 1 знака (напр. 13.3)
            if dynamic_pct < 1.0:
                return round(dynamic_pct, 2)
            return round(dynamic_pct, 1)
            
    return 0.01


def calculate_features_score(overview_scores: Dict[str, float]) -> float:
    total_weighted_score = 0.0
    total_weight = 0.0

    for key, weight in FEATURES_WEIGHTS.items():
        if key in overview_scores and overview_scores[key] is not None:
            total_weighted_score += float(overview_scores[key]) * weight
            total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(total_weighted_score / total_weight, 2)


def build_overall_score_page(
    overview_scores: Dict[str, float],
    dimorphism_score: float,
    photo_src: Optional[str] = None,
    ai_summary_text: str = "",  
    theme_color: str = "#FAAF24",
    force_f_score: Optional[float] = None,
    force_d_score: Optional[float] = None,
    raw_dimorphism: Optional[float] = None,  # <-- ДОДАНО ЩОБ ВИПРАВИТИ ПОМИЛКУ
    **kwargs  # <-- ГАРАНТУЄ, ЩО БІЛЬШЕ ТАКИХ ПОМИЛОК НЕ БУДЕ
) -> OverallScoreContext:
    """
    `dimorphism_score` must be the exact same final score shown on the Dimorphism
    page (DimorphismOverviewContext.score_num from build_dimorphism_overview).
    There is no separate conversion anymore -- the same number is used here,
    blended 85/15 with the features score.
    """
    # Якщо адмін передав свої оцінки - використовуємо їх
    if force_f_score is not None:
        features_score = max(1.0, min(10.0, round(float(force_f_score), 2)))
        logger.info(f"Using forced features_score: {features_score}")
    else:
        features_score = calculate_features_score(overview_scores)

    if force_d_score is not None:
        dimorphism_score = max(1.0, min(10.0, round(float(force_d_score), 2)))
        logger.info(f"Using forced dimorphism_score: {dimorphism_score}")
    else:
        dimorphism_score = max(1.0, min(10.0, round(float(dimorphism_score), 2)))

    w_feat = FINAL_SCORE_WEIGHTS.get("features", 0.85)
    w_dim = FINAL_SCORE_WEIGHTS.get("dimorphism", 0.15)

    final_score = (features_score * w_feat) + (dimorphism_score * w_dim)
    final_score = max(1.0, min(10.0, round(final_score, 2)))

    # Отримуємо назву рівня
    level_info = _get_level_info(final_score)
    
    # Вираховуємо динамічний відсоток та формуємо текст
    top_percentile = calculate_top_percentile(final_score)
    if final_score < 3.0:
        dynamic_top_text = "Facial geometry requires angle correction"
    else:
        dynamic_top_text = f"You are in the top <span class='pct-highlight'>{top_percentile}%</span> of people by facial geometry!"

    # Залишаємо позицію для SVG-графіка (зеленої шкали) без змін
    curve_pos_pct = round(max(5.0, min(95.0, (final_score / 10.0) * 100.0)), 1)

    sub_scores = [
        SubScoreItem(label="Features 85%", score=features_score),
        SubScoreItem(label="Dimorphism 15%", score=dimorphism_score),
    ]

    logger.info(f"🏆 Overall Score Page generated: {final_score} (Curve Pct: {curve_pos_pct}%)")

    return OverallScoreContext(
        final_score=final_score,
        features_score=features_score,
        dimorphism_score=dimorphism_score,
        top_text=dynamic_top_text,
        level_title=level_info["level_title"],
        curve_pos_pct=curve_pos_pct,
        photo_src=photo_src,
        theme_color="#FAAF24",  
        photo_border_color=PHOTO_BORDER_COLOR, 
        photo_shadow_rgba=PHOTO_SHADOW_RGBA,   
        sub_scores=sub_scores
    )