# face/metrics/features/nose/overview.py
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from jinja2 import Template
from face.metrics.scoring import SCORING_REGISTRY, compute_score

@dataclass
class NoseScaleData:
    title: str
    value_text: str
    marker_pos_pct: float
    ideal_text: str = "10.00"

@dataclass
class NoseOverviewContext:
    title: str = "Nose — Overall Impression"
    score_str: str = "0.00"
    summary_text: str = ""
    match_text: str = ""  # НОВЕ ПОЛЕ ДЛЯ ЗОРЯНОГО АРХЕТИПУ
    photo_src: Optional[str] = None
    scales: List[NoseScaleData] = field(default_factory=list)
    theme_color: str = "#F97316"
    study_text: Optional[str] = None

    def render_html(self, page_num_str: str = "01", total_pages: int = 12) -> str:
        html_template = """
        <style>
        @page nose_summary_size { 
            size: 210mm 160mm; 
            margin: 0; 
        }
        .page-nose-overview {
            page: nose_summary_size; 
            width: 210mm; 
            height: 160mm; 
            padding: 16mm;
            background: #040710; 
            position: relative; 
            box-sizing: border-box;
            page-break-after: always; 
            color: #E2E8F0; 
            font-family: Arial, sans-serif;
            -webkit-print-color-adjust: exact; 
            print-color-adjust: exact;
        }

        /* ВІДСТУПИ ШАПКИ ІДЕНТИЧНІ ДО БАЛАНСУ/ОЧЕЙ */
        .header-table { display: table; width: 100%; margin-bottom: 3mm; table-layout: fixed; }
        .header-cell-left { display: table-cell; text-align: left; vertical-align: baseline; width: 40%; }
        .header-cell-center { display: table-cell; text-align: center; vertical-align: baseline; width: 20%; }
        .header-cell-right { display: table-cell; text-align: right; vertical-align: baseline; width: 40%; }
        
        .rule { height: 1px; background: #1E293B; margin-bottom: 5mm; clear: both; }

        /* ВЕРТИКАЛЬНЕ ЦЕНТРУВАННЯ ТЕКСТУ ЗЛІВА (table-cell layout) */
        .nose-cols { 
            display: table; 
            width: 100%; 
            table-layout: fixed;
            margin-top: 2mm;
        }
        
        .nose-col-left { 
            display: table-cell; 
            width: 48%; 
            vertical-align: middle; 
            padding-right: 4%; 
            height: 105mm; 
        }
        
        .nose-col-right { 
            display: table-cell; 
            width: 48%; 
            vertical-align: top; 
            position: relative;
            height: 105mm;
        }

        .nose-overview-text {
            width: 100%; 
            height: auto;
            max-height: 120mm;
            margin: 0; 
            padding: 0; 
            box-sizing: border-box;
        }
        
        /* ШКАЛИ */
        .nose-scale-item { 
            display: block; 
            width: 100%; 
            margin-top: 0 !important; 
            margin-bottom: 16mm !important; 
            padding: 0 !important; 
            position: relative;
            page-break-inside: avoid;
        }
        .nose-scale-head { 
            margin: 0 0 1.5mm 0 !important; 
            padding: 0 !important; 
            display: block; 
            width: 100%; 
            height: 15pt; 
        }
        .nose-scale-title { 
            font-size: 13pt; 
            font-weight: 700; 
            color: #94A3B8 !important; 
            text-transform: uppercase; 
            letter-spacing: 1px; 
            line-height: 1 !important; 
            float: left; 
        }
        
        .nose-scale-track { 
            position: relative; 
            width: 100%; 
            height: 9px; 
            margin-top: 3.5mm; 
            clear: both; 
        }
        .nose-scale-colors { 
            width: 100%; 
            height: 100%; 
            border-radius: 4px; 
            overflow: hidden; 
        }
        .nose-scale-colors span { 
            height: 100%; 
            display: block;
            float: left;
        }
        .nose-scale-marker { 
            position: absolute; 
            width: 4px; 
            height: 18px; 
            background: #FFFFFF; 
            top: -3px; 
            transform: translateX(-50%); 
            box-shadow: 0 0 5px rgba(0,0,0,0.9); 
            border-radius: 3px; 
            z-index: 10; 
        }

        .nose-footer { 
            position: absolute; 
            bottom: 12mm; 
            right: 16mm; 
            font-size: 10pt; 
            color: #64748B; 
        }
        .nose-footer a { 
            color: #3B82F6 !important; 
            text-decoration: none; 
            font-weight: bold; 
        }
        </style>
        
        <div class="page-nose-overview">
            
            <div class="header-table">
                <div class="header-cell-left">
                    <h1 style="font-size: 20pt; font-weight: 700; margin: 0; color: {{ ctx.theme_color }};">
                        {{ ctx.title.split(' — ')[0] if ctx.title and ' — ' in ctx.title else ctx.title }}
                    </h1>
                </div>
                <div class="header-cell-center">
                    <span style="color: #FFFFFF; font-size: 28pt; font-weight: bold; position: relative; top: 5px;">{{ ctx.score_str }}</span>
                </div>
                <div class="header-cell-right">
                    <span class="pgnum" style="color: #FFFFFF; font-size: 10pt; font-weight: bold;">{{ page_num_str }} / {{ "%02d"|format(total_pages) }}</span>
                </div>
            </div>
            
            <div class="rule"></div>
            
            <div class="nose-cols">
                <div class="nose-col-left">
                    <div class="nose-overview-text">
                        {% if ctx.summary_text %}
                            {{ ctx.summary_text | safe }}
                        {% else %}
                            <p style="color: #475569; font-style: italic;">[Biometric evaluation summary text will be generated here by the automated AI clinical structuring module.]</p>
                        {% endif %}
                    </div>
                </div>
                <div class="nose-col-right">
                    {% for scale in ctx.scales %}
                    <div class="nose-scale-item">
                        <div class="nose-scale-head"><span class="nose-scale-title">{{ scale.title }}</span></div>
                        <div class="nose-scale-track">
                            <div class="nose-scale-colors" style="width: 100%; height: 100%;">
                                <span style="width: 19%; background:#EF4444;"></span>
                                <span style="width: 19%; background:#F59E0B;"></span>
                                <span style="width: 24%; background:#10B981;"></span>
                                <span style="width: 19%; background:#F59E0B;"></span>
                                <span style="width: 19%; background:#EF4444;"></span>
                            </div>
                            <div class="nose-scale-marker" style="left: {{ scale.marker_pos_pct }}%;"></div>
                        </div>
                    </div>
                    {% endfor %}
                    
                    {{ ctx.match_text | safe }}
                </div>
            </div>
            <div class="nose-footer">Telegram: <a href="https://t.me/bp_guide_scoringAI_bot" target="_blank">@bp_guide_scoringAI_bot</a></div>
        </div>
        """
        return Template(html_template).render(ctx=self, page_num_str=page_num_str, total_pages=total_pages)

def build_nose_scale_data(metric_key: str, user_value: float, title: str) -> NoseScaleData:
    cfg = SCORING_REGISTRY.get(metric_key)
    ideal = cfg.ideal if cfg else 0.0
    if ideal > 0:
        ratio = user_value / ideal
        if ratio < 0.8: 
            marker_pos = 10.0
        elif ratio > 1.2: 
            marker_pos = 90.0
        else: 
            marker_pos = 50.0 + (ratio - 1.0) * 200.0
    else:
        marker_pos = 50.0
    marker_pos_pct = max(2.0, min(98.0, marker_pos))
    return NoseScaleData(
        title=title.upper(), 
        value_text=f"{user_value:.4f}", 
        marker_pos_pct=marker_pos_pct, 
        ideal_text=f"{ideal:.4f}" if ideal > 0 else "N/A"
    )

def build_nose_overview(measurements: Dict[str, float], summary_text: str = "", match_text: str = "", photo_src: Optional[str] = None) -> NoseOverviewContext:
    scales = []
    targets = [
        ("nose_height", "NOSE / FACE HEIGHT RATIO"), 
        ("nose_to_lips", "NOSE / LIPS WIDTH RATIO"), 
        ("nose_width", "NOSE / FACE WIDTH RATIO")
    ]
    total_score = 0.0
    valid_metrics = 0
    for key, title in targets:
        if key in measurements:
            val = measurements[key]
            scales.append(build_nose_scale_data(key, val, title))
            cfg = SCORING_REGISTRY.get(key)
            if cfg:
                try:
                    score = compute_score(val, cfg)
                    total_score += score
                    valid_metrics += 1
                except (ValueError, TypeError):
                    pass
    avg_score_str = f"{(total_score / valid_metrics):.2f}" if valid_metrics > 0 else "0.00"
    return NoseOverviewContext(
        title="Nose — Overall Impression", 
        score_str=avg_score_str, 
        photo_src=photo_src, 
        summary_text=summary_text, 
        match_text=match_text,  # ← ПЕРЕДАЄМО ЗОРЯНИЙ МАТЧ У КОНТЕКСТ
        scales=scales, 
        theme_color="#F97316"
    )