# face/metrics/features/dimorphism.py
from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from jinja2 import Template

logger = logging.getLogger(__name__)

THEME_COLOR = "#3133d1"  # Основний фіолетовий/індиго колір теми

DIMORPHISM_RULES = {
    # --- КІСТКОВА СТРУКТУРА (60% загальної ваги) ---
    "fwhr": {
        "title": "FWHR",
        "weight": 0.25,
        "val_10": 1.8000,
        "val_1": 1.6250,
        "higher_better": True
    },
    "jaw_facew": {
        "title": "Jaw Robustness",
        "weight": 0.20,
        "val_10": 0.9750,
        "val_1": 0.9400,
        "higher_better": True
    },
    "chin_lowerth": {
        "title": "Chin Height",
        "weight": 0.15,
        "val_10": 0.2150,
        "val_1": 0.1740,
        "higher_better": True
    },
    
    # --- М'ЯКІ ТКАНИНИ ТА БРОВИ (40% загальної ваги) ---
    "eye_eyebrow": {
        "title": "Brow Ridge",
        "weight": 0.15,
        "val_10": 0.3650,
        "val_1": 0.4600,
        "higher_better": False  
    },
    "eyebrow_density": {
        "title": "Brow Thickness",
        "weight": 0.15,
        "val_10": 0.1500,
        "val_1": 0.1150,
        "higher_better": True
    },
    "lips_weight": {
        "title": "Lips Compactness",
        "weight": 0.10,
        "val_10": 0.2600,
        "val_1": 0.4000,
        "higher_better": False  
    },
}


@dataclass
class DimorphismScaleData:
    title: str 
    raw_val_str: str
    score_str: str
    score_num: float
    marker_pos_pct: float
    weight_pct: int


def compute_dimorphism_score(val: float, rule: Dict[str, Any]) -> float:
    v10 = rule["val_10"]
    v1 = rule["val_1"]
    min_score = 1.0
    
    if rule["higher_better"]:
        if val >= v10: return 10.0
        if val <= v1: return min_score
        raw_dev = v10 - val
        max_dev = v10 - v1
    else:
        if val <= v10: return 10.0
        if val >= v1: return min_score
        raw_dev = val - v10
        max_dev = v1 - v10
        
    if max_dev <= 0:
        return min_score

    target_score = min_score + 0.1
    ratio = (target_score - min_score) / (10.0 - min_score)
    k = -math.log(ratio) / (max_dev ** 2)
    raw = min_score + (10.0 - min_score) * math.exp(-k * (raw_dev ** 2))
    
    return round(max(min_score, min(10.0, raw)), 2)


@dataclass
class DimorphismOverviewContext:
    title: str = "Dimorphism"
    score_str: str = "0.00"
    score_num: float = 0.0
    summary_text: str = ""
    scales: List[DimorphismScaleData] = field(default_factory=list)
    theme_color: str = THEME_COLOR

    def render_html(self, page_num_str: str = "01", total_pages: int = 12) -> str:
        html_template = """
        <style>
        @page dimorphism_size { 
            size: 210mm 240mm; 
            margin: 0; 
        }
        .page-dimorphism-overview {
            page: dimorphism_size; 
            width: 210mm; 
            height: 240mm; 
            padding: 16mm;
            background: #040710; 
            position: relative; 
            box-sizing: border-box;
            page-break-after: always; 
            color: #E2E8F0; 
            font-family: Arial, sans-serif;
            display: block;
            -webkit-print-color-adjust: exact; 
            print-color-adjust: exact;
        }
        .dimorphism-header-table {
            display: table;
            width: 100%;
            margin-bottom: 4mm;
        }
        .dimorphism-header-left {
            display: table-cell;
            text-align: left;
            vertical-align: middle;
            width: 33%;
        }
        .dimorphism-header-center {
            display: table-cell;
            text-align: center;
            vertical-align: middle;
            width: 33%;
        }
        .dimorphism-header-right {
            display: table-cell;
            text-align: right;
            vertical-align: middle;
            width: 33%;
        }
        .dimorphism-cols { 
            display: table;
            width: 100%; 
            margin-top: 4mm; 
            table-layout: fixed;
        }
        .dimorphism-col-left { 
            display: table-cell;
            width: 47%; 
            vertical-align: top; 
        }
        .dimorphism-col-spacer {
            display: table-cell;
            width: 6%;
        }
        .dimorphism-col-right { 
            display: table-cell;
            width: 47%; 
            vertical-align: top; 
        }
        
        .dimorphism-overview-text {
            width: 100%; 
            box-sizing: border-box;
            color: #E2E8F0 !important; 
            font-size: 12pt !important; 
            line-height: 1.6; 
            text-align: left;
        }    
        .dimorphism-overview-text p, .dimorphism-overview-text ul, .dimorphism-overview-text div { 
            color: #E2E8F0 !important; 
        }
        .dimorphism-overview-text a { 
            color: {{ ctx.theme_color }} !important; 
            text-decoration: underline !important; 
        }

        .dimorphism-scale-item { 
            display: block !important; 
            width: 100% !important; 
            margin-top: 0 !important;
            margin-bottom: 15mm !important; 
            padding: 0 !important;
            position: relative;
            page-break-inside: avoid;
        }
        .dimorphism-scale-head { 
            display: table;
            width: 100% !important;
            margin: 0 0 1.5mm 0 !important; 
        }
        .dimorphism-scale-title { 
            display: table-cell;
            text-align: left;
            vertical-align: baseline;
            font-size: 16.5pt; 
            font-weight: 700; 
            color: #E2E8F0 !important; 
            text-transform: uppercase; 
            letter-spacing: 0.5px; 
        }
        .dimorphism-scale-score {
            display: table-cell;
            text-align: right;
            vertical-align: baseline;
            font-size: 19pt;
            font-weight: 700;
            color: {{ ctx.theme_color }} !important;
        }
        
        .dimorphism-scale-meta {
            font-size: 10.5pt;
            color: #64748B !important;
            margin-bottom: 2mm;
            display: block;
        }

        .dimorphism-scale-track { 
            position: relative !important; 
            width: 100% !important; 
            height: 8px !important; 
            background: #1E293B !important;
            border-radius: 4px; 
            overflow: visible; 
            margin-top: 2mm;
        }
        .dimorphism-scale-fill { 
            height: 100% !important; 
            background: {{ ctx.theme_color }} !important;
            border-radius: 4px; 
        }
        .dimorphism-scale-marker {
            position: absolute !important; 
            width: 14px !important; 
            height: 14px !important; 
            background: #FFFFFF !important;
            top: -3px !important; 
            transform: translateX(-50%); 
            box-shadow: 0 0 6px rgba(0,0,0,0.8); 
            border-radius: 50%; 
            z-index: 10;
            border: 2px solid {{ ctx.theme_color }} !important;
        }

        .dimorphism-footer { 
            position: absolute; 
            bottom: 12mm; 
            right: 16mm; 
            font-size: 10pt; 
            color: #64748B; 
            text-align: right; 
        }
        .dimorphism-footer a { 
            color: #3d81f7; 
            text-decoration: none; 
            font-weight: bold; 
        }
        </style>
        
        <div class="page-dimorphism-overview">
            
            <div class="dimorphism-header-table">
                <div class="dimorphism-header-left">
                    <h1 style="font-size: 20pt; font-weight: 700; margin: 0; padding-top: 1.2mm; color: {{ ctx.theme_color }};">
                        {{ ctx.title }}
                    </h1>
                </div>
                <div class="dimorphism-header-center">
                    <span style="color: #FFFFFF; font-size: 30pt; font-weight: bold;">{{ ctx.score_str }}</span>
                    <span style="color: #64748B; font-size: 14pt; font-weight: bold; margin-left: 2px;">/10</span>
                </div>
                <div class="dimorphism-header-right">
                    <span class="pgnum" style="color: #FFFFFF; font-size: 10pt; font-weight: bold;">{{ page_num_str }} / {{ "%02d"|format(total_pages) }}</span>
                </div>
            </div>
            
            <div style="height: 1px; background: #1E293B; margin-bottom: 4mm;"></div>
            
            <div class="dimorphism-cols">
                <div class="dimorphism-col-left">
                    <div class="dimorphism-overview-text">
                        {% if ctx.summary_text %}
                            {{ ctx.summary_text | safe }}
                        {% else %}
                            <p style="color: #475569; font-style: italic;">[Biometric evaluation summary text will be generated here by the automated AI clinical structuring module.]</p>
                        {% endif %}
                    </div>
                </div>
                
                <div class="dimorphism-col-spacer"></div>
                
                <div class="dimorphism-col-right">
                    {% for scale in ctx.scales %}
                    <div class="dimorphism-scale-item">
                        <div class="dimorphism-scale-head">
                            <div class="dimorphism-scale-title">{{ scale.title }}</div>
                            <div class="dimorphism-scale-score">{{ scale.score_str }}<span style="color: #64748B; font-size: 12pt; font-weight: 700;">/10</span></div>
                        </div>
                        <span class="dimorphism-scale-meta">Raw Ratio: {{ scale.raw_val_str }} (Weight: {{ scale.weight_pct }}%)</span>
                        <div class="dimorphism-scale-track">
                            <div class="dimorphism-scale-fill" style="width: {{ scale.marker_pos_pct }}%;"></div>
                            <div class="dimorphism-scale-marker" style="left: {{ scale.marker_pos_pct }}%;"></div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <div class="dimorphism-footer">Telegram: <a href="https://t.me/bp_guide_scoringAI_bot" target="_blank">@bp_guide_scoringAI_bot</a></div>
        </div>
        """
        return Template(html_template).render(ctx=self, page_num_str=page_num_str, total_pages=total_pages)


def build_dimorphism_overview(measurements: Dict[str, float], summary_text: str = "") -> DimorphismOverviewContext:
    scales = []
    total_weighted_score = 0.0
    total_active_weight = 0.0
    
    for key, rule in DIMORPHISM_RULES.items():
        if key in measurements:
            val = measurements[key]
            score = compute_dimorphism_score(val, rule)
            weight = rule["weight"]
            
            total_weighted_score += score * weight
            total_active_weight += weight
            
            marker_pct = max(5.0, min(100.0, (score / 10.0) * 100.0))
            
            scales.append(DimorphismScaleData(
                title=rule["title"].upper(),
                raw_val_str=f"{val:.4f}",
                score_str=f"{score:.2f}",
                score_num=score,
                marker_pos_pct=marker_pct,
                weight_pct=int(weight * 100)
            ))
            
    final_score = (total_weighted_score / total_active_weight) if total_active_weight > 0 else 0.0
    
    return DimorphismOverviewContext(
        title="Dimorphism",
        score_str=f"{final_score:.2f}",
        score_num=round(final_score, 2),
        summary_text=summary_text,
        scales=scales,
        theme_color=THEME_COLOR
    )