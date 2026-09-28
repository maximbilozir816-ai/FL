# face/metrics/features/facialbalance/overview.py
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from jinja2 import Template
from face.metrics.scoring import SCORING_REGISTRY, compute_score

@dataclass
class BalanceScaleData:
    title: str
    value_text: str
    marker_pos_pct: float
    ideal_text: str = "10.00"

@dataclass
class BalanceOverviewContext:
    title: str = "Facial Balance — Overall Impression"
    score_str: str = "0.00"
    summary_text: str = ""
    match_text: str = ""  # НОВЕ ПОЛЕ ДЛЯ ЗОРЯНОГО АРХЕТИПУ
    photo_src: Optional[str] = None
    scales: List[BalanceScaleData] = field(default_factory=list)
    theme_color: str = "#8a2780"
    study_text: Optional[str] = None

    def render_html(self, page_num_str: str = "01", total_pages: int = 12) -> str:
        html_template = """
        <style>
        @page balance_summary_size { 
            size: 210mm 160mm; 
            margin: 0; 
        }
        .page-balance-overview {
            page: balance_summary_size; 
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
        
        /* 4. ВІДСТУПИ ШАПКИ ІДЕНТИЧНІ ДО report.html */
        .header-table { display: table; width: 100%; margin-bottom: 3mm; table-layout: fixed; }
        .header-cell-left { display: table-cell; text-align: left; vertical-align: baseline; width: 40%; }
        .header-cell-center { display: table-cell; text-align: center; vertical-align: baseline; width: 20%; }
        .header-cell-right { display: table-cell; text-align: right; vertical-align: baseline; width: 40%; }
        
        .rule { height: 1px; background: #1E293B; margin-bottom: 5mm; clear: both; }

        /* 3. ВЕРТИКАЛЬНЕ ЦЕНТРУВАННЯ ТЕКСТУ ЗЛІВА (table-cell layout) */
        .balance-cols { 
            display: table; 
            width: 100%; 
            table-layout: fixed;
            margin-top: 2mm;
        }
        
        .balance-col-left { 
            display: table-cell; 
            width: 48%; 
            vertical-align: middle; /* Саме це центрує текст, якщо його мало */
            padding-right: 4%; 
            height: 105mm; /* Задана висота для правильного балансу центрування */
        }
        
        .balance-col-right { 
            display: table-cell; 
            width: 48%; 
            vertical-align: top; 
            position: relative;
            height: 105mm;
        }
        
        .balance-overview-text {
            width: 100%; 
            height: auto;
            max-height: 120mm;
            margin: 0; 
            padding: 0; 
            box-sizing: border-box;
        }

        /* 2. ЗБІЛЬШЕНА ВІДСТАНЬ МІЖ ШКАЛАМИ */
        .balance-scale-item { 
            display: block; 
            width: 100%; 
            margin-top: 0 !important; 
            margin-bottom: 16mm !important;
            padding: 0 !important; 
            position: relative; 
            page-break-inside: avoid; 
        }
        .balance-scale-head { 
            margin: 0 0 1.5mm 0 !important; 
            padding: 0 !important; 
            display: block; 
            width: 100%; 
            height: 15pt; 
        }
        
        /* 1. ЗМЕНШЕНО ШРИФТ НАЗВ МЕТРИК */
        .balance-scale-title { 
            font-size: 13pt; /* Було 14.5pt, тепер 12pt */
            font-weight: 700; 
            color: #94A3B8 !important; 
            text-transform: uppercase; 
            letter-spacing: 1px; 
            line-height: 1 !important; 
            float: left; 
        }
        
        .balance-scale-track { 
            position: relative; 
            width: 100%; 
            height: 9px; 
            margin-top: 3.5mm; 
            clear: both; 
        }
        .balance-scale-colors { 
            width: 100%; 
            height: 100%; 
            border-radius: 4px; 
            overflow: hidden; 
        }
        .balance-scale-colors span { 
            height: 100%; 
            display: block;
            float: left;
        }
        .balance-scale-marker { 
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
        
        .balance-footer { 
            position: absolute; 
            bottom: 12mm; 
            right: 16mm; 
            font-size: 10pt; 
            color: #64748B; 
        }
        .balance-footer a { color: #3d81f7; text-decoration: none; font-weight: bold; }
        </style>
        
        <div class="page-balance-overview">
            
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
            
            <div class="balance-cols">
                <div class="balance-col-left">
                    <div class="balance-overview-text">
                        {% if ctx.summary_text %}
                            {{ ctx.summary_text | safe }}
                        {% else %}
                            <p style="color: #475569; font-style: italic;">[Biometric evaluation summary text will be generated here by the automated AI clinical structuring module.]</p>
                        {% endif %}
                    </div>
                </div>
                <div class="balance-col-right">
                    {% for scale in ctx.scales %}
                    <div class="balance-scale-item">
                        <div class="balance-scale-head"><span class="balance-scale-title">{{ scale.title }}</span></div>
                        <div class="balance-scale-track">
                            <div class="balance-scale-colors" style="width: 100%; height: 100%;">
                                <span style="width: 19%; background:#EF4444;"></span>
                                <span style="width: 19%; background:#F59E0B;"></span>
                                <span style="width: 24%; background:#10B981;"></span>
                                <span style="width: 19%; background:#F59E0B;"></span>
                                <span style="width: 19%; background:#EF4444;"></span>
                            </div>
                            <div class="balance-scale-marker" style="left: {{ scale.marker_pos_pct }}%;"></div>
                        </div>
                    </div>
                    {% endfor %}
                    
                    {{ ctx.match_text | safe }}
                </div>
            </div>
            <div class="balance-footer">Telegram: <a href="https://t.me/bp_guide_scoringAI_bot" target="_blank">@bp_guide_scoringAI_bot</a></div>
        </div>
        """
        return Template(html_template).render(ctx=self, page_num_str=page_num_str, total_pages=total_pages)


def build_balance_scale_data(key: str, score: float, title: str) -> BalanceScaleData:
    """Вираховує позицію білого маркеру на основі балів (0..10)."""
    direction = -1 if key == "thirds" else (1 if key == "fifths" else -1)
    deviation = (10.0 - score) * 5.5
    marker_pos = 50.0 + (direction * deviation)
    marker_pos_pct = max(2.0, min(98.0, marker_pos))
    
    return BalanceScaleData(
        title=title.upper(), 
        value_text=f"{score:.2f}", 
        marker_pos_pct=marker_pos_pct, 
        ideal_text="10.00"
    )


def build_facial_balance_overview(scores: Dict[str, float], summary_text: str = "", match_text: str = "", photo_src: Optional[str] = None) -> BalanceOverviewContext:
    """Головна функція створення контексту оглядової сторінки балансу."""
    scales = []
    targets = [
        ("thirds", "VERTICAL THIRDS BALANCE"), 
        ("fifths", "HORIZONTAL FIFTHS BALANCE"), 
        ("facial_index", "FACIAL INDEX HARMONY")
    ]
    
    total_score = 0.0
    valid_metrics = 0
    
    for key, title in targets:
        if key in scores:
            score_val = float(scores[key])
            scales.append(build_balance_scale_data(key, score_val, title))
            total_score += score_val
            valid_metrics += 1
            
    avg_score_str = f"{(total_score / valid_metrics):.2f}" if valid_metrics > 0 else "0.00"
    
    return BalanceOverviewContext(
        title="Facial Balance — Overall Impression", 
        score_str=avg_score_str,
        summary_text=summary_text, 
        match_text=match_text,  # ← ПЕРЕДАЄМО ЗОРЯНИЙ МАТЧ У КОНТЕКСТ
        photo_src=photo_src, 
        scales=scales, 
        theme_color="#8a2780"
    )