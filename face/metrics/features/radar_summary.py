# face/metrics/features/radar_summary.py
from __future__ import annotations

import io
import base64
import logging
from dataclasses import dataclass
from typing import Dict, Any, List
import numpy as np
from jinja2 import Template

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from face.metrics.features.Overall_score import FEATURES_WEIGHTS

logger = logging.getLogger(__name__)

BLOCK_DISPLAY_NAMES = {
    "eye_overview": "Eye Area",
    "balance_overview": "Facial Balance",
    "nose_overview": "Nose",
    "lips_overview": "Lips",
    "brows_overview": "Eyebrows",
    "dmetrics_overview": "Facial Dimensions",
    "ametrics_overview": "Angularity / Structure",
}

CATEGORY_COLORS = {
    "Eye Area": "#0F8696",
    "Facial Balance": "#8a2780",
    "Nose": "#F97316",
    "Lips": "#E95870",
    "Eyebrows": "#FFFFFF",
    "Facial Dimensions": "#B90000",
}

def generate_features_radar_chart_b64(scores_dict: dict, weights_dict: dict) -> str:
    categories = list(scores_dict.keys())
    values = list(scores_dict.values())

    if not categories:
        return ""

    labels = []
    colors_list = []
    
    total_weight = sum(weights_dict.values())
    
    for cat in categories:
        cat_weight = weights_dict.get(cat, 0)
        if total_weight > 0:
            pct = int(round((cat_weight / total_weight) * 100))
        else:
            pct = 0
            
        labels.append(f"{cat}\n({pct}%)")
        colors_list.append(CATEGORY_COLORS.get(cat, "#E2E8F0"))

    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    
    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6.8, 6.3), subplot_kw=dict(polar=True))
    
    bg_color = '#040710'
    line_color = '#E95870' 
    grid_color = '#1E293B'
    
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    ax.plot(angles, values, linewidth=2.0, linestyle='solid', color=line_color)
    ax.fill(angles, values, color=line_color, alpha=0.15)

    ax.scatter(angles[:-1], values[:-1], s=25, c=colors_list, edgecolors='none', zorder=10)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=12, weight='bold')

    for label, color in zip(ax.get_xticklabels(), colors_list):
        label.set_color(color)

    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels([], color='#FFFFFF', size=8) 
    
    ax.grid(color=grid_color, linestyle='-', linewidth=1.0, alpha=0.5)
    ax.spines['polar'].set_color(grid_color)
    ax.spines['polar'].set_linewidth(1.0)
    
    ax.tick_params(axis='x', pad=25)
    fig.subplots_adjust(left=0.15, right=0.85, top=0.85, bottom=0.15)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300, transparent=True)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

@dataclass
class RadarSummaryContext:
    radar_chart_b64: str
    top_3: List[Dict[str, Any]]
    bottom_3: List[Dict[str, Any]]
    all_metrics: List[Dict[str, Any]]

    def render_html(self, page_num_str: str = "02", total_pages: int = 33) -> str:
        html_template = """
        <style>
        @page rs_isolated_page_size { 
            size: 210mm 270mm;
            margin: 0; 
        }
        .rs-page-wrapper {
            page: rs_isolated_page_size; 
            width: 210mm; 
            height: 270mm;
            padding: 10mm 16mm; 
            background: #040710; 
            color: #E2E8F0; 
            font-family: Arial, sans-serif;
            display: block; 
            box-sizing: border-box;
            page-break-after: always;
            -webkit-print-color-adjust: exact; 
            print-color-adjust: exact;
            overflow: hidden;
        }
        
        .rs-page-wrapper * { 
            box-sizing: border-box; 
        }
        
        .rs-header { 
            text-align: center; 
            margin-bottom: 3mm; 
            width: 100%; 
            display: block;
        }
        .rs-h1 { 
            font-size: 24pt; 
            font-weight: 800; 
            letter-spacing: 0.5px; 
            color: #FAAF24; 
            text-transform: uppercase; 
            margin-bottom: 1.5mm; 
            margin-top: 0;
            display: block;
        }
        .rs-sub-link-wrap {
            font-size: 10pt;
            display: block;
        }
        .rs-tg-label {
            color: #64748B;
            font-weight: 600;
        }
        .rs-tg-link {
            color: #4680dd;
            font-weight: bold;
            text-decoration: none;
        }

        .rs-chart-area { 
            width: 100%; 
            text-align: center;
            margin-bottom: 6mm; 
            display: block;
        }
        .rs-chart-area img { 
            max-height: 115mm; 
            width: auto; 
            object-fit: contain; 
            margin: 0 auto;
            display: block;
        }
        
        /* Таблиця замість Grid */
        .rs-top-bottom-table {
            display: table;
            width: 100%;
            table-layout: fixed;
            margin-bottom: 5mm; 
        }
        .rs-tb-col {
            display: table-cell;
            width: 48%;
            vertical-align: top;
        }
        .rs-tb-spacer {
            display: table-cell;
            width: 4%;
        }
        
        .rs-list-header {
            font-size: 12pt;
            font-weight: 800;
            margin-bottom: 3mm;
        }
        .rs-list-header.green { color: #10B981; }
        .rs-list-header.red { color: #EF4444; }

        .rs-tb-item {
            display: table;
            width: 100%;
            table-layout: fixed;
            margin-bottom: 2mm;
            font-size: 10pt;
            color: #94A3B8;
        }
        .rs-tb-dot-cell {
            display: table-cell;
            width: 18px;
            vertical-align: middle;
        }
        .rs-tb-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        .rs-tb-name-cell {
            display: table-cell;
            vertical-align: middle;
            text-align: left;
        }
        .rs-tb-val-cell {
            display: table-cell;
            vertical-align: middle;
            text-align: right;
            color: #E2E8F0;
            font-size: 10.5pt;
            font-weight: 600;
            width: 40px;
        }

        .rs-metrics-breakdown {
            width: 100%;
            display: block;
        }

        .rs-metrics-breakdown h3 {
            font-size: 14pt;
            color: #FFFFFF;
            margin-bottom: 4mm; 
            margin-top: 0; 
            display: block;
        }

        .rs-metrics-table {
            display: table;
            width: 100%;
            table-layout: fixed;
        }

        .rs-metrics-col {
            display: table-cell;
            width: 48%;
            vertical-align: top;
        }
        .rs-metrics-divider {
            display: table-cell;
            width: 4%;
            vertical-align: top;
            /* Можна додати border-left якщо потрібна лінія */
        }

        .rs-m-row {
            display: table;
            width: 100%;
            table-layout: fixed;
            margin-bottom: 2.5mm;
        }

        .rs-m-name {
            display: table-cell;
            width: 50%;
            font-size: 9.5pt;
            color: #cbd5e1;
            font-style: italic;
            text-align: left;
            vertical-align: middle;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .rs-m-right-side {
            display: table-cell;
            width: 50%;
            text-align: right;
            vertical-align: middle;
        }

        .rs-m-bar-bg {
            display: inline-block;
            width: 14mm; 
            height: 8px;
            background: #1E293B;
            margin-right: 2mm;
            border-radius: 2px;
            vertical-align: middle;
        }
        
        .rs-m-bar-fill {
            height: 100%;
            border-radius: 2px;
        }

        .rs-m-score {
            display: inline-block;
            width: 25px;
            text-align: right;
            font-size: 9.5pt;
            font-weight: 700;
            vertical-align: middle;
        }
        </style>

        <div class="rs-page-wrapper">
            <div class="rs-header">
                <div class="rs-h1">PROPORTIONAL HARMONY</div>
                <div class="rs-sub-link-wrap">
                    <span class="rs-tg-label">Telegram: </span><a href="https://t.me/bp_guide_scoringAI_bot" target="_blank" class="rs-tg-link">@bp_guide_scoringAI_bot</a>
                </div>
                <div style="font-size: 8.5pt; color: #64748B; font-style: italic; margin-top: 3mm; padding: 0 10mm; line-height: 1.3;">
                    * Percentages indicate the aesthetic weight of each category. Core structural foundations (like Facial Dimensions) impact the final score significantly more than easily adjustable soft features (like Eyebrows).
                </div>
            </div>

            <div class="rs-chart-area">
                {% if ctx.radar_chart_b64 %}
                    <img src="data:image/png;base64,{{ ctx.radar_chart_b64 }}" alt="Global Features Radar Chart">
                {% endif %}
            </div>
            
            <div class="rs-top-bottom-table">
                <div class="rs-tb-col">
                    <div class="rs-list-header green">Top-3 Strengths</div>
                    {% for m in ctx.top_3 %}
                    <div class="rs-tb-item">
                        <div class="rs-tb-dot-cell"><div class="rs-tb-dot" style="background-color: {{ m.color }};"></div></div>
                        <div class="rs-tb-name-cell">{{ m.name }}</div>
                        <div class="rs-tb-val-cell" style="color: {{ m.color }};">{{ m.score | round(2) }}</div>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="rs-tb-spacer"></div>
                
                <div class="rs-tb-col">
                    <div class="rs-list-header red">Top-3 Potential Areas</div>
                    {% for m in ctx.bottom_3 %}
                    <div class="rs-tb-item">
                        <div class="rs-tb-dot-cell"><div class="rs-tb-dot" style="background-color: {{ m.color }};"></div></div>
                        <div class="rs-tb-name-cell">{{ m.name }}</div>
                        <div class="rs-tb-val-cell" style="color: {{ m.color }};">{{ m.score | round(2) }}</div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <div class="rs-metrics-breakdown">
                <h3>Metrics Contribution</h3>
                
                <div class="rs-metrics-table">
                    <div class="rs-metrics-col">
                        {% for m in ctx.all_metrics[:9] %}
                        <div class="rs-m-row">
                            <div class="rs-m-name">{{ m.name }}</div>
                            <div class="rs-m-right-side">
                                <div class="rs-m-bar-bg">
                                    <div class="rs-m-bar-fill" style="width: {{ m.score * 10 }}%; background-color: {{ m.color }};"></div>
                                </div>
                                <div class="rs-m-score" style="color: {{ m.color }};">{{ '%0.2f' % m.score|float }}</div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    
                    <div class="rs-metrics-divider"></div>
                    
                    <div class="rs-metrics-col">
                        {% for m in ctx.all_metrics[9:] %}
                        <div class="rs-m-row">
                            <div class="rs-m-name">{{ m.name }}</div>
                            <div class="rs-m-right-side">
                                <div class="rs-m-bar-bg">
                                    <div class="rs-m-bar-fill" style="width: {{ m.score * 10 }}%; background-color: {{ m.color }};"></div>
                                </div>
                                <div class="rs-m-score" style="color: {{ m.color }};">{{ '%0.2f' % m.score|float }}</div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                
            </div>
        </div>
        """
        return Template(html_template).render(ctx=self)

def _extract_score_from_ctx(ctx: Any) -> float:
    if ctx is None: return 0.0
    if hasattr(ctx, 'final_score'): return float(ctx.final_score)
    if hasattr(ctx, 'score'): return float(ctx.score)
    if hasattr(ctx, 'score_str'):
        try: return float(ctx.score_str)
        except ValueError: return 0.0
    return 0.0

def build_radar_summary_page(overview_contexts: Dict[str, Any], individual_metrics: List[Dict[str, Any]]) -> RadarSummaryContext:
    temp_scores = {}
    temp_weights = {}
    for key, weight in FEATURES_WEIGHTS.items():
        display_name = BLOCK_DISPLAY_NAMES.get(key, key.replace("_overview", "").title())
        ctx_obj = overview_contexts.get(key)
        temp_scores[display_name] = _extract_score_from_ctx(ctx_obj)
        temp_weights[display_name] = weight

    custom_order = ["Nose", "Facial Balance", "Eye Area", "Lips", "Facial Dimensions", "Eyebrows"]
    scores_dict = {cat: temp_scores[cat] for cat in custom_order if cat in temp_scores}
    weights_dict = {cat: temp_weights[cat] for cat in custom_order if cat in temp_weights}

    radar_b64 = generate_features_radar_chart_b64(scores_dict, weights_dict)
    
    sorted_metrics = sorted(individual_metrics, key=lambda x: x['score'], reverse=True)
    top_3 = sorted_metrics[:3]
    bottom_3 = sorted_metrics[-3:][::-1] 

    return RadarSummaryContext(
        radar_chart_b64=radar_b64,
        top_3=top_3,
        bottom_3=bottom_3,
        all_metrics=individual_metrics 
    )