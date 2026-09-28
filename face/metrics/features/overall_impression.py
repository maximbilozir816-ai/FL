# face/metrics/features/overall_impression.py
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from jinja2 import Template

def wrap_impression_html(content: str) -> str:
    raw_text = re.sub(r'<[^>]+>', '', content).strip()
    text_len = len(raw_text)

    p_size = 13.5
    h1_size = 14.5
    bullet_size = 13.5
    quote_size = 14.0  
    
    if text_len > 3400:
        p_size = 9.0
        h1_size = 10.0
        bullet_size = 9.0
        quote_size = 9.5
    elif text_len > 3200:
        p_size = 9.4
        h1_size = 10.4
        bullet_size = 9.4
        quote_size = 10.0
    elif text_len > 2900:
        p_size = 10.0
        h1_size = 11.0
        bullet_size = 10.0
        quote_size = 10.5
    elif text_len > 2700:
        p_size = 10.5
        h1_size = 11.5
        bullet_size = 10.5
        quote_size = 11.0     
    elif text_len > 2400:
        p_size = 11.1
        h1_size = 12.1
        bullet_size = 11.1
        quote_size = 11.6
    elif text_len > 2250:
        p_size = 11.2
        h1_size = 12.2
        bullet_size = 11.2
        quote_size = 11.7
    elif text_len > 2000:
        p_size = 11.8
        h1_size = 12.8
        bullet_size = 11.8
        quote_size = 12.3
    elif text_len > 1900:
        p_size = 12.3
        h1_size = 13.3
        bullet_size = 12.3
        quote_size = 12.8
    elif text_len > 1700:
        p_size = 12.5
        h1_size = 13.5
        bullet_size = 12.5
        quote_size = 13.1
    elif text_len > 1500:
        p_size = 13.0
        h1_size = 14.0
        bullet_size = 13.0
        quote_size = 13.5

    wrap_id = f"imp-box-{uuid.uuid4().hex[:8]}"

    # Scoped strictly by element ID to guarantee 100% CSS isolation
    dynamic_css = f"""
    <style>
    #{wrap_id} p.imp-lead {{ font-size: {h1_size}pt !important; font-weight: 700 !important; color: #FFFFFF !important; margin: 0 0 12px 0 !important; line-height: 1.45 !important; }}
    #{wrap_id} p.imp-text {{ font-size: {p_size}pt !important; font-weight: 400 !important; color: #E2E8F0 !important; margin: 0 0 12px 0 !important; line-height: 1.45 !important; }}
    #{wrap_id} ul {{ margin: 0 0 18px 16px !important; padding: 0 !important; color: #E2E8F0 !important; font-size: {bullet_size}pt !important; line-height: 1.5 !important; }}
    #{wrap_id} ul li {{ margin-bottom: 10px !important; }}
    #{wrap_id} div.imp-quote {{ border-left: 4px solid #FAAF24 !important; padding-left: 14px !important; margin-top: 10px !important; font-style: italic !important; color: #FFFFFF !important; font-size: {quote_size}pt !important; line-height: 1.45 !important; }}
    </style>
    """
    
    content = re.sub(r'style="[^"]*"', '', content)
    
    content = content.replace('<p>', '<p class="imp-text">')
    content = content.replace('<p class="imp-text">', '<p class="imp-lead">', 1)
    content = content.replace('<div>', '<div class="imp-quote">')

    return f'{dynamic_css}<div id="{wrap_id}">{content}</div>'

@dataclass
class OverallImpressionContext:
    summary_text: str

    def render_html(self, page_num_str: str = "03", total_pages: int = 33) -> str:
        wrapped_text = wrap_impression_html(self.summary_text)
        
        html_template = """
        <style>
        @page imp_isolated_page_size { 
            size: 210mm 260mm;
            margin: 0; 
        }
        .imp-page-wrapper {
            page: imp_isolated_page_size; 
            width: 210mm; 
            min-height: 260mm;
            height: auto; 
            padding: 12mm 16mm 10mm 16mm; 
            background: #040710; 
            color: #E2E8F0; 
            font-family: Arial, sans-serif;
            display: block; 
            position: relative; 
            box-sizing: border-box;
        }

        .imp-page-wrapper .imp-header-container { 
            text-align: center; 
            margin-bottom: 6.5mm; 
            width: 100%; 
        }
        .imp-page-wrapper .imp-header { 
            font-size: 24pt; 
            font-weight: 800; 
            letter-spacing: 0.5px; 
            color: #FAAF24; 
            text-transform: uppercase; 
            margin-bottom: 1.5mm; 
            margin-top: 0;
        }
        .imp-page-wrapper .imp-sub-link-wrap {
            font-size: 10pt;
        }
        .imp-page-wrapper .imp-tg-label {
            color: #64748B;
            font-weight: 600;
        }
        .imp-page-wrapper .imp-tg-link {
            color: #4680dd;
            font-weight: bold;
            text-decoration: none;
        }

        .imp-page-wrapper .imp-summary-text {
            width: 100%;
            padding: 0 4mm;
            box-sizing: border-box;
            text-align: justify;
        }
        </style>

        <div class="imp-page-wrapper">
            <div class="imp-header-container">
                <div class="imp-header">AESTHETIC ANALYSIS</div>
                <div class="imp-sub-link-wrap">
                    <span class="imp-tg-label">Telegram: </span><a href="https://t.me/bp_guide_scoringAI_bot" target="_blank" class="imp-tg-link">@bp_guide_scoringAI_bot</a>
                </div>
            </div>

            <div class="imp-summary-text">
                {{ ctx.summary_text }}
            </div>
        </div>
        """
        return Template(html_template).render(ctx={'summary_text': wrapped_text})

def build_overall_impression_page(summary_text: str = "") -> OverallImpressionContext:
    return OverallImpressionContext(summary_text=summary_text)