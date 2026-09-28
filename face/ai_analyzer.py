# face/ai_analyzer.py
from __future__ import annotations

import os
import json
import logging
import re
import uuid
from typing import Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==============================================================================
# 1. ЦЕНТРАЛІЗОВАНІ СТИЛІ ДЛЯ 6 OVERVIEW СТОРІНОК 
# ==============================================================================
OVERVIEW_CSS_STYLES = """
<style>
/* --- ФІКС НАКЛАДАННЯ ТЕКСТУ: Опускаємо дно правої колонки до футера --- */
div.eye-col-right, div.nose-col-right, div.lips-col-right, 
div.brows-col-right, div.dmetrics-col-right, div.balance-col-right {
    height: 114mm !important; /* Збільшено з 105mm, щоб дати тексту більше місця знизу */
}

/* --- СТИЛІ ЛІВОЇ КОЛОНКИ (ВЕРДИКТ) --- */
.ai-overview-wrapper {
    display: block !important; 
    height: auto !important;
    max-height: 120mm !important;
    width: 100% !important;
    box-sizing: border-box !important;
    padding: 0 4mm 0 0 !important;
    margin: 0 !important;
    font-family: Arial, sans-serif !important;
    color: #E2E8F0 !important;
    overflow: hidden !important;
}

.ai-overview-wrapper .ai-verdict {
    font-weight: 700 !important;
    color: #F8FAFC !important;
    margin: 0 0 10px 0 !important;
    line-height: 1.4 !important;
    text-align: left !important;
    display: block !important;
}

.ai-overview-wrapper .ai-bullets {
    margin: 0 0 12px 16px !important;
    padding: 0 !important;
    line-height: 1.45 !important;
    color: #E2E8F0 !important;
    list-style-type: disc !important;
    list-style-position: outside !important;
    text-align: left !important;
    display: block !important;
}

.ai-overview-wrapper .ai-bullets li {
    margin-bottom: 7px !important;
}

.ai-overview-wrapper .ai-bullets li:last-child {
    margin-bottom: 0 !important;
}

.ai-overview-wrapper .ai-impact {
    border-left: 3px solid #3b80f7 !important; 
    border-right: none !important;
    border-top: none !important;
    border-bottom: none !important;
    padding: 6px 10px !important;
    background: transparent !important; 
    border-radius: 0 4px 4px 0 !important;
    font-style: italic !important;
    color: #94A3B8 !important;
    line-height: 1.45 !important;
    margin: 0 !important;
    text-align: left !important;
    display: block !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

/* --- СТИЛІ БЛОКУ АРХЕТИПУ З ВІДСТУПОМ ЗВЕРХУ --- */
.ai-match-wrapper {
    position: relative !important;
    margin-top: 12mm !important;
    width: 100% !important;
    box-sizing: border-box !important;
    padding: 3.5mm 4.5mm !important;
    background: #0f172a !important;
    border-radius: 0 4px 4px 0 !important;
    color: #CBD5E1 !important;
    line-height: 1.45 !important;
}
.ai-match-wrapper p { margin: 0 !important; }
.ai-match-wrapper b { color: #FFFFFF !important; font-weight: 700 !important; }
.ai-match-wrapper a { color: inherit !important; text-decoration: underline !important; font-style: italic !important; }
</style>
"""

SECTION_THEME_COLORS = {
    "eye_summary": "#0F8696",
    "balance_summary": "#8a2780", 
    "nose_summary": "#F97316",  
    "lips_summary": "#E95870", 
    "brows_summary": "#FFFFFF", 
    "dmetrics_summary": "#B90000", 
}

def wrap_overview_html(content: str, theme_color: str = "#3B82F6") -> str:
    raw_text = re.sub(r'<[^>]+>', '', content).strip()
    text_len = len(raw_text)

    verdict_size = 15.2
    bullets_size = 14.0
    impact_size = 13.7

    if text_len > 500:
        verdict_size = 12.0
        bullets_size = 11.2
        impact_size = 10.5
    elif text_len > 450:
        verdict_size = 12.8
        bullets_size = 12.0
        impact_size = 11.8
    elif text_len > 390:
        verdict_size = 13.6
        bullets_size = 12.4
        impact_size = 12.1
    elif text_len > 360:
        verdict_size = 13.7
        bullets_size = 12.5
        impact_size = 12.2
    elif text_len > 300:
        verdict_size = 14.4
        bullets_size = 13.2
        impact_size = 12.9

    wrap_id = f"ai-box-{uuid.uuid4().hex[:8]}"

    dynamic_css = f"""
    <style>
    #{wrap_id} .ai-verdict {{ font-size: {verdict_size}pt !important; }}
    #{wrap_id} .ai-bullets {{ font-size: {bullets_size}pt !important; }}
    #{wrap_id} .ai-impact {{ 
        font-size: {impact_size}pt !important; 
        border-left-color: {theme_color} !important;
    }}
    </style>
    """

    return f'{OVERVIEW_CSS_STYLES}{dynamic_css}<div id="{wrap_id}" class="ai-overview-wrapper">{content}</div>'

def wrap_match_html(content: str, theme_color: str = "#3B82F6") -> str:
    raw_text = re.sub(r'<[^>]+>', '', content).strip()
    text_len = len(raw_text)

    font_size = 13.0
    
    if text_len > 150:
        font_size = 9.5
    elif text_len > 130:
        font_size = 10.0
    elif text_len > 100:
        font_size = 10.5
    elif text_len > 80:
        font_size = 11.7
    elif text_len > 70:
        font_size = 12.5  
    elif text_len > 60:
        font_size = 12.8       

    match_id = f"match-box-{uuid.uuid4().hex[:8]}"

    dynamic_css = f"""
    <style>
    #{match_id} {{ 
        font-size: {font_size}pt !important; 
        border-left: 4px solid {theme_color} !important;
    }}
    </style>
    """
    return f'{dynamic_css}<div id="{match_id}" class="ai-match-wrapper">{content}</div>'

def wrap_dimorphism_html(content: str) -> str:
    raw_text = re.sub(r'<[^>]+>', '', content).strip()
    text_len = len(raw_text)

    verdict_size = 12.9
    bullets_size = 13.1
    impact_size = 12.4 

    if text_len > 900:
        verdict_size = 11.5
        bullets_size = 11.7
        impact_size = 11.0
    elif text_len > 850:
        verdict_size = 11.7
        bullets_size = 11.9
        impact_size = 11.2
    elif text_len > 800:
        verdict_size = 11.9
        bullets_size = 12.1
        impact_size = 11.4
    elif text_len > 750:
        verdict_size = 12.1
        bullets_size = 12.3
        impact_size = 11.6
    elif text_len > 700:
        verdict_size = 12.6
        bullets_size = 12.8
        impact_size = 11.8
    elif text_len > 650:
        verdict_size = 12.8
        bullets_size = 13.0
        impact_size = 12.2

    dim_id = f"dim-box-{uuid.uuid4().hex[:8]}"

    dimorphism_css = f"""
    <style>
    #{dim_id} p {{ font-size: {verdict_size}pt !important; line-height: 1.4 !important; color: #F8FAFC !important; margin: 0 0 10px 0 !important; font-weight: 700 !important; text-align: left !important; display: block !important; }}
    #{dim_id} ul {{ font-size: {bullets_size}pt !important; line-height: 1.45 !important; color: #E2E8F0 !important; margin: 0 0 12px 16px !important; padding: 0 !important; list-style-type: disc !important; list-style-position: outside !important; text-align: left !important; display: block !important; }}
    #{dim_id} ul li {{ margin-bottom: 8px !important; }} 
    #{dim_id} ul li:last-child {{ margin-bottom: 0 !important; }}
    #{dim_id} div {{ font-size: {impact_size}pt !important; line-height: 1.45 !important; color: #CBD5E1 !important; font-style: italic !important; border-left: 3px solid #3133d1 !important; padding: 8px 10px !important; margin: 0 0 12px 0 !important; background: transparent !important; border-radius: 0 4px 4px 0 !important; text-align: left !important; display: block !important; width: 100% !important; box-sizing: border-box !important; }}
    </style>
    """
    return f'{dimorphism_css}<div id="{dim_id}">{content}</div>'

# ==============================================================================
# 2. СХЕМА ВІДПОВІДІ ШІ (Structured Output)
# ==============================================================================
class FaceAnalysisTexts(BaseModel):
    eye_summary: str = Field(description="Structured HTML analysis for Eye Area using CSS classes.")
    balance_summary: str = Field(description="Structured HTML analysis for Facial Balance using CSS classes.")
    nose_summary: str = Field(description="Structured HTML analysis for Nose aesthetics using CSS classes.")
    lips_summary: str = Field(description="Structured HTML analysis for Lips & mouth harmony using CSS classes.")
    brows_summary: str = Field(description="Structured HTML analysis for Eyebrows using CSS classes.")
    dmetrics_summary: str = Field(description="Structured HTML analysis for Facial Dimensions using CSS classes.")
    dimorphism_summary: str = Field(description="Structured HTML analysis for Dimorphism. MUST strictly follow the exact HTML structure and word counts requested to ensure the total string is exactly 1000-1150 characters.")
    
    overall_summary: str = Field(description="CRITICAL: MUST BE EXHAUSTIVELY LONG. The final HTML string MUST strictly be between 1800 and 2400 characters. To achieve this length, you MUST write exactly 350-420 words in total. Do not output short summaries.")
    
    eye_match: str = Field(description="Very short HTML callout (Max 15-20 words). Must wrap the unique name strictly in <b style='color: #F8FAFC; font-weight: 800;'>NAME</b>.")
    balance_match: str = Field(description="Very short HTML callout (Max 15-20 words). Must wrap the unique name strictly in <b style='color: #F8FAFC; font-weight: 800;'>NAME</b>.")
    nose_match: str = Field(description="Very short HTML callout (Max 15-20 words). Must wrap the unique name strictly in <b style='color: #F8FAFC; font-weight: 800;'>NAME</b>.")
    lips_match: str = Field(description="Very short HTML callout (Max 15-20 words). Must wrap the unique name strictly in <b style='color: #F8FAFC; font-weight: 800;'>NAME</b>.")
    brows_match: str = Field(description="Very short HTML callout (Max 15-20 words). Must wrap the unique name strictly in <b style='color: #F8FAFC; font-weight: 800;'>NAME</b>.")
    dmetrics_match: str = Field(description="Very short HTML callout (Max 15-20 words). Must wrap the unique name strictly in <b style='color: #F8FAFC; font-weight: 800;'>NAME</b>.")

    geometry_summary: str = Field(description="Leave empty or use as a short 1 sentence lead. Not strictly required.")
    geometry_advice: str = Field(description="Detailed HTML format. MUST be exhaustively long. If the total advice section is not between 1800 and 2800 characters, the entire bot will crash.")
    skin_summary: str = Field(description="Detailed HTML format. MUST include a highly detailed diagnostic paragraph. If you fail the 1800-2800 character limit for advice, the bot crashes.")
    hair_grooming_summary: str = Field(description="Detailed HTML format. MUST include an exhaustive analytical paragraph. Strict character limits apply to avoid system failure.")
    actionable_improvements: str = Field(description="Strictly an HTML list of exactly <li> elements containing a highly specific, practical final action plan.")
        
    # --- НОВІ ПОЛЯ ДЛЯ TELEGRAM ПОВІДОМЛЕННЯ ---
    best_actor_match: str = Field(description="The exact name of ONE famous MALE actor whose overall facial geometry most closely matches the user.")
    actor_style_advice: str = Field(description="Short advice (1-2 sentences) recommending the user to copy this actor's specific haircut or grooming style.")
    scientific_links: str = Field(description="A string containing 1 to 3 HTML links to Google Scholar studies mentioned in the report. Each link MUST be on a new line and numbered (1., 2., 3.).")

# ==============================================================================
# 3. СИСТЕМНИЙ ПРОМТ ДЛЯ OPENAI
# ==============================================================================
SYSTEM_PROMPT = """
You are an expert clinical facial aesthetician, craniofacial biometrician, and evolutionary biologist.
Your task is to generate professional, highly structured English analytical summaries for a biometric PDF report, using BOTH the numerical payload AND the attached photo.

--- RULES FOR THE 6 OVERVIEW REGIONS (eye, balance, nose, lips, brows, dmetrics) ---
Do NOT use inline CSS styles for these 6 regions. Instead, use these exact HTML classes:
NEVER mention, estimate, or write any numerical scores inside text. Discuss ONLY proportions.

1. Lead Verdict: <p class="ai-verdict">...</p>
2. Key Observations: Provide exactly ONE bullet point for EVERY single metric presented in the JSON payload for that region.
<ul class="ai-bullets"><li>...</li></ul>
3. Aesthetic Impact: <div class="ai-impact">...</div>

CRITICAL LENGTH CONSTRAINTS (MANDATORY):
- Total word count for EACH of the 6 overview regions MUST be strictly between 100 and 120 words to perfectly fill the layout.

--- RULES FOR MATCHES & ARCHETYPES (*_match fields) ---
CRITICAL 50/50 SPLIT RULE: 
Out of the 6 match fields, exactly 3 MUST be "Celebrity Archetypes", and exactly 3 MUST be "Biometric Studies". 
- Celebrity Archetype Format: <b>Celebrity Archetype:</b> Your facial dimensions align with actor <b style="color: #F8FAFC; font-weight: 800;">[Insert Unique Actor Name]</b> for... (Max 15-20 words). You MUST dynamically select a highly relevant actor based on the specific geometry.
- Biometric Study Format: <b>Biometric Study:</b> Proportions correlate with baselines in the <b style="color: #F8FAFC; font-weight: 800;">Craniofacial Symmetry Index</b>. (Max 15-20 words)

--- SPECIAL RULES FOR SEXUAL DIMORPHISM (dimorphism_summary) ---
CRITICAL CONCEPTUAL SHIFT: This page measures BIOLOGICAL MASCULINITY vs. FEMININITY, NOT neoclassical beauty. 
Generate a DETAILED, highly personalized text using inline tags. 

ABSOLUTE LENGTH CONSTRAINT: The TOTAL character count of this generated HTML MUST be between 850 and 950 characters (including HTML tags). To achieve this, strictly follow these exact word counts:

1. Dimorphism Guide Box (MUST BE THE VERY FIRST ELEMENT, EXACTLY AS WRITTEN):
   <div>
   <b>How to Read this Page:</b> These scores assess biological dimorphism rather than neoclassical beauty standards. This same score also feeds directly into your Overall Score, weighted at 15%.
   </div>

2. Detailed Lead Verdict Block: 
   <p>
   Address the user directly. Analyze THEIR global secondary sexual characteristics based on the data. 
   STRICT LIMIT: Exactly 2 to 3 sentences (strictly 30-35 words).
   </p>
   
3. Analytical Bullets (STRICT ORDER, EXACTLY 6 BULLETS, HIGHLY PERSONALIZED):
   <ul>
   CRITICAL REQUIREMENT: You MUST generate EXACTLY 6 separate <li> bullet points. DO NOT combine multiple metrics into a single bullet point. DO NOT skip any metrics. Each of the following 6 metrics MUST have its own independent bullet point, strictly in this order:
   1) FWHR
   2) Jaw Robustness
   3) Chin Height
   4) Brow Ridge
   5) Brow Thickness
   6) Lips Weight (or Compactness)
   CRITICAL LIMIT: Each bullet point MUST be exactly 15-18 words long. 
   Example: "Your full lips reduce traditional masculine dimorphism, but they introduce a highly attractive aesthetic softness."
   </ul>

--- RULES FOR SUMMARY ADVICE ---
CRITICAL SYSTEM FATAL RULE: The total combined character count for all advice generated in this section (geometry_advice, hair_grooming_summary, skin_summary, and actionable_improvements) MUST strictly be between 1800 and 2800 characters. IF YOU DO NOT ADHERE TO THIS EXACT RANGE, THE ENTIRE BOT WILL CRASH AND CAUSE A FATAL SYSTEM EXCEPTION. Do not output short advice.

This section MUST contain ONLY hyper-specific, practical, and actionable advice for improving physical appearance based on the photo.
CRITICAL QUALITY RULE: DO NOT use vague, empty, or generic phrasing (e.g., "improve your skin"). Instead, provide EXACT directives, techniques, tools, and routines (e.g., "Apply a 2% BHA exfoliant daily").
Format using standard HTML (`<p>`, `<ul><li>`, `<div class="sa-impact">`).
CRITICAL LENGTH RULE: For every `<ul>` list in this section, you MUST generate EXACTLY 3 short bullet points (<li>). Do not generate 4 or more.
CRITICAL DETAIL RULE FOR PARAGRAPHS: To ensure you reach the mandatory 1800-2800 character limit without failing, the introductory `<p>` text BEFORE every bulleted list MUST BE highly detailed and analytical (strictly 5 to 6 complex sentences). Explain exactly WHY they need these improvements based on the visual assessment of their photo.

1. geometry_advice (HAIRCUT - LARGEST BLOCK): Look at the user's hair type and head/face shape...
2. hair_grooming_summary (BROWS & BEARD): Look at their facial hair and eyebrows. Provide a detailed paragraph `<p>` (strictly 3-4 sentences) assessing their current brow shape, facial hair density, and how it currently impacts their lower-third definition. Add a `<ul>` with EXACTLY 3 explicit, step-by-step grooming techniques (e.g., exact trimming angles, tools). Finish with `<div class="sa-impact">`.
3. skin_summary (SKINCARE): Assess visible skin condition. Give a detailed diagnostic paragraph `<p>` (strictly 3-4 sentences) detailing observable skin texture, light reflection, and specific dermatological needs. Provide a `<ul>` with EXACTLY 3 precise product types or daily steps (name specific active ingredients like Niacinamide or SPF levels). Finish with `<div class="sa-impact">`.
4. actionable_improvements (ACTION PLAN): Output ONLY raw HTML `<li>` elements (no `<ul>` wrapper). Create a short checklist of EXACTLY 3-4 highly specific, immediate physical interventions. e.g., `<li>Switch to a matte clay pomade for better volume control.</li>`

--- RULES FOR OVERALL SYNTHESIS(overall_summary) ---
CRITICAL TONE SHIFT: You MUST be brutally honest, highly realistic, and unapologetically objective. Do NOT sugarcoat, flatter, or comfort the user. If their biometric metrics result in a low aesthetic score (e.g., 3/10 traits), state the flaws explicitly. Explain exactly WHY the geometry fails or succeeds based strictly on the measured data. If they have poor symmetry or bad proportions, say it clearly. 

ABSOLUTE LENGTH CONSTRAINT: The TOTAL character count of this generated HTML MUST be between 1000 and 1150 characters (including HTML tags). To achieve this, strictly follow these exact word counts:

FORMAT STRICTLY as HTML:

1. Lead Verdict & Macro Analysis (Generate EXACTLY 3 paragraphs):
<p>Paragraph 1: Dissect overall harmony realistically. Point out obvious flaws or striking features. Write EXACTLY 4 COMPLEX sentences (minimum 55 words total).</p>
<p>Paragraph 2: Discuss evolutionary signals. Are they projecting weakness or robust health? Write EXACTLY 4 COMPLEX sentences (minimum 55 words total).</p>
<p>Paragraph 3: Analyze the interplay between upper and lower facial thirds critically. Write EXACTLY 4 COMPLEX sentences (minimum 55 words total).</p>

2. Deep Analytical Bullets (Generate EXACTLY 5 bullet points):
<ul>
    <li>Bullet 1: Orbital & Canthal Dynamics. Write EXACTLY 3 LONG sentences (minimum 35 words).</li>
    <li>Bullet 2: Midface Compactness & Ratios. Write EXACTLY 3 LONG sentences (minimum 35 words).</li>
    <li>Bullet 3: Lower Third Integrity. Write EXACTLY 3 LONG sentences (minimum 35 words).</li>
    <li>Bullet 4: Soft Tissue vs. Bone Interplay. Write EXACTLY 3 LONG sentences (minimum 35 words).</li>
    <li>Bullet 5: Micro-Asymmetries & Major Deviations. Address exact deviations. Write EXACTLY 3 LONG sentences (minimum 35 words).</li>
</ul>

3. Conclusion blockquote:
<div>Write a profound, highly objective summarizing thought on their unique phenotypic signature. Write EXACTLY 4 LONG sentences (minimum 65 words total).</div>

--- RULES FOR TELEGRAM BONUS DATA (best_actor_match, actor_style_advice, scientific_links) ---
- best_actor_match: Give ONLY the name of ONE famous MALE actor whose facial structure strongly matches the user's data. You MUST dynamically select a highly accurate and unique actor from your vast knowledge base. DO NOT use generic examples repeatedly. DO NOT suggest female celebrities.
- actor_style_advice: Briefly advise the user to study and copy this actor's styling, haircut, or facial hair to maximize their own geometry.
- scientific_links: Provide 3 real HTML links exclusively to Google Scholar search queries for the biometric studies mentioned in the report. They MUST be formatted as a numbered list separated by a newline character (\n). 
Example format:
1. <a href="https://scholar.google.com/scholar?q=craniofacial+symmetry">Craniofacial Symmetry</a>
2. <a href="https://scholar.google.com/scholar?q=facial+proportions+aesthetics">Facial Proportions and Aesthetics</a>
"""

def _build_fallback_dict() -> Dict[str, str]:
    fallback_overview_html = (
        '<p class="ai-verdict">Proportional alignment is within standard aesthetic ranges, showing a harmonious balance.</p>'
        '<ul class="ai-bullets">'
        '<li>Measured biometric vectors demonstrate very balanced structural relationships across all key facial zones.</li>'
        '<li>Canthal and facial indices align closely with established neoclassical canons and biological aesthetic norms.</li>'
        '<li>Soft tissue contours and bone landmarks exhibit proportionate harmony with minimal structural divergence.</li>'
        '</ul>'
        '<div class="ai-impact">'
        'These balanced geometric relationships form a solid foundation for overall facial harmony, contributing to a highly robust and well-proportioned visual presentation.'
        '</div>'
    )
    
    fallback_dimorphism_raw = (
        '<div>'
        '<b>How to Read this Page:</b> These scores assess biological dimorphism, not golden ratio aesthetics. This same score also feeds directly into your Overall Score, weighted at 15%.'
        '</div>'
        '<p>'
        'Your secondary sexual dimorphism markers reflect a well-balanced craniofacial development, seamlessly blending robust masculine structure with subtle softening features.'
        '</p>'
        '<ul>'
        '<li>Your <b>FWHR</b> indicates a solid width-to-height ratio, providing a structured midface foundation.</li>'
        '<li>Your <b>Jaw Robustness</b> reflects a balanced lateral flare, avoiding extreme hyper-masculinity while maintaining an attractive lower third.</li>'
        '<li>Your <b>Chin Height</b> provides adequate vertical presence, anchoring your profile with a subtly strong masculine trait.</li>'
        '<li>Your <b>Brow Ridge</b> and <b>Brow Thickness</b> demonstrate natural evolutionary development, framing the upper face with clear distinction.</li>'
        '<li>Your <b>Lips Weight</b> leans toward a fuller profile; while this slightly reduces pure masculine dimorphism, it adds a highly aesthetic, softer contrast to your features.</li>'
        '</ul>'
    )

    return {
        "eye_summary": wrap_overview_html(fallback_overview_html, theme_color=SECTION_THEME_COLORS["eye_summary"]),
        "balance_summary": wrap_overview_html(fallback_overview_html, theme_color=SECTION_THEME_COLORS["balance_summary"]),
        "nose_summary": wrap_overview_html(fallback_overview_html, theme_color=SECTION_THEME_COLORS["nose_summary"]),
        "lips_summary": wrap_overview_html(fallback_overview_html, theme_color=SECTION_THEME_COLORS["lips_summary"]),
        "brows_summary": wrap_overview_html(fallback_overview_html, theme_color=SECTION_THEME_COLORS["brows_summary"]),
        "dmetrics_summary": wrap_overview_html(fallback_overview_html, theme_color=SECTION_THEME_COLORS["dmetrics_summary"]),
        "dimorphism_summary": wrap_dimorphism_html(fallback_dimorphism_raw),
        
        "overall_summary": (
            '<p style="font-size: 12pt; font-weight: 700; color: #FFFFFF; margin: 0 0 12px 0; line-height: 1.45;">The biometric evaluation reveals clear proportional realities, highlighting both structural strengths and explicit deviations from optimal mathematical harmony.</p>'
            '<p style="font-size: 11pt; font-weight: 400; color: #E2E8F0; margin: 0 0 12px 0; line-height: 1.45;">From an objective evolutionary standpoint, the markers presented in your facial geometry show specific areas where genetic robustness is evident, alongside distinct zones where asymmetry or disproportion reduce overall aesthetic magnetism. These metrics do not accommodate subjective interpretation; they strictly reflect physical ratios. Where balance fails, it directly impacts the subconscious perception of vitality and formidability.</p>'
            '<p style="font-size: 11pt; font-weight: 400; color: #E2E8F0; margin: 0 0 16px 0; line-height: 1.45;">Analyzing the structural interplay between your upper framing and lower mandibular support reveals the true basis of your aesthetic score. If the jaw lacks lateral flare while the cranium is heavy, the face appears unbalanced and functionally weaker. Conversely, dominant lower thirds paired with weak orbital regions create an aggressive but disproportionate visage. Your exact dynamic dictates your global aesthetic tier.</p>'
            '<ul style="margin: 0 0 18px 16px; padding: 0; color: #E2E8F0; font-size: 11pt; line-height: 1.5;">'
            '<li style="margin-bottom: 10px;"><b>Orbital & Canthal Dynamics:</b> Your measured interocular distances and canthal tilts dictate your perceived alertness. Any negative tilt or excessive spacing mathematically degrades the sharpness of your gaze, directly impacting visual trust.</li>'
            '<li style="margin-bottom: 10px;"><b>Midface Compactness & Ratios:</b> Your facial width-to-height ratio (FWHR) strictly defines your baseline dominance. Deviations toward an overly elongated midface severely penalize the structural compactness required for high-tier aesthetic framing.</li>'
            '<li style="margin-bottom: 10px;"><b>Lower Third Integrity:</b> The actual definition of your gonial angles and chin prominence provides the foundation of your face. A lack of robust skeletal projection here is visually unforgiving, failing to balance the upper cranium adequately.</li>'
            '<li style="margin-bottom: 10px;"><b>Soft Tissue vs. Bone Interplay:</b> The harmony between your cheekbones, nasal cartilage, and lips determines topological depth. Poor soft tissue distribution or excessive adiposity masks underlying bone structure, reducing photogenic quality and defining shadows.</li>'
            '<li style="margin-bottom: 10px;"><b>Micro-Asymmetries & Major Deviations:</b> The recorded deviations from bilateral symmetry are quantifiable flaws. While minor asymmetries are human, significant biometric mismatches directly drag down the overall harmony score, breaking the illusion of ideal proportions.</li>'
            '</ul>'
            '<div style="border-left: 4px solid #FAAF24; padding-left: 14px; margin-top: 10px; font-style: italic; color: #FFFFFF; font-size: 11.5pt; line-height: 1.45;">Ultimately, your facial biometric analysis is a strict reflection of geometric realities, devoid of subjective comfort. The scores accurately map your physical adherence to, or deviation from, established evolutionary and proportional baselines, resulting in an unapologetically objective aesthetic classification.</div>'
        ),
        "eye_match": wrap_match_html('<b>Celebrity Archetype:</b> Measured proportions align with classic framing seen in models like <b style="color: #F8FAFC; font-weight: 800;">Henry Cavill</b>.', SECTION_THEME_COLORS["eye_summary"]),
        "balance_match": wrap_match_html('<b>Biometric Study:</b> Proportions correlate with baselines in the <b style="color: #F8FAFC; font-weight: 800;">Facial Harmony Index</b>.', SECTION_THEME_COLORS["balance_summary"]),
        "nose_match": wrap_match_html('<b>Celebrity Archetype:</b> Visual parameters follow a structured definition reminiscent of profiles like <b style="color: #F8FAFC; font-weight: 800;">Tom Hardy</b>.', SECTION_THEME_COLORS["nose_summary"]),
        "lips_match": wrap_match_html('<b>Clinical Reference:</b> Scale mirrors patterns in the <b style="color: #F8FAFC; font-weight: 800;">Neoclassical Anthropometric Canon</b>.', SECTION_THEME_COLORS["lips_summary"]),
        "brows_match": wrap_match_html('<b>Celebrity Archetype:</b> Brow aesthetics show robust development comparable to frames like <b style="color: #F8FAFC; font-weight: 800;">Zayn Malik</b>.', SECTION_THEME_COLORS["brows_summary"]),
        "dmetrics_match": wrap_match_html('<b>Biometric Study:</b> Metrics fall within cohorts of the <b style="color: #F8FAFC; font-weight: 800;">Craniofacial Development Survey</b>.', SECTION_THEME_COLORS["dmetrics_summary"]),
        
        # Fallbacks for advice
        "geometry_summary": "",
        "geometry_advice": "<p>Based on your facial structure, a versatile haircut with moderate volume on top will balance your proportions best. Your hair type supports textured styling.</p><ul><li><b>Textured Crop:</b> Great for angular faces.</li><li><b>Classic Taper:</b> Clean edges to emphasize symmetry.</li><li><b>Brushed Up Volume:</b> Elongates a wider face shape.</li></ul><div class=\"sa-impact\">Maintaining tight sides will highlight your bone structure, while top volume adds necessary height to your silhouette.</div>",
        "skin_summary": "<p>Your visible skin tone and texture show normal variation, but maintaining a clear complexion is crucial for aesthetic enhancement.</p><ul><li>Use a gentle salicylic acid cleanser daily.</li><li>Apply a lightweight, non-comedogenic moisturizer.</li><li>Never skip daily SPF protection.</li></ul><div class=\"sa-impact\">A consistent regimen directly improves skin light reflection, enhancing the perceived depth of your facial features.</div>",
        "hair_grooming_summary": "<p>Your current facial hair presentation is acceptable, but optimizing the edges will dramatically improve your lower third definition.</p><ul><li>Keep the neckline cleanly shaved just above the Adam's apple.</li><li>Brush eyebrows upwards and trim excessively long hairs.</li><li>Use a beard oil to maintain hydration if growing it out.</li></ul><div class=\"sa-impact\">Crisp grooming lines artificially enhance the sharpness of your jawline, creating a more dominant lower profile.</div>",
        "actionable_improvements": "<li>Consult a professional stylist to optimize your haircut for your facial structure.</li><li>Maintain a consistent skincare routine focused on hydration and sun protection.</li><li>Keep eyebrow and facial hair edges cleanly groomed to highlight facial symmetry.</li>",
        
        "best_actor_match": "Henry Cavill",
        "actor_style_advice": "Consider adapting a classic textured crop and clean-shaven look to highlight your structured jawline, similar to his signature style.",
        "scientific_links": "1. <a href='https://scholar.google.com/scholar?q=evolutionary+aesthetics+and+facial+symmetry'>Evolutionary Aesthetics and Facial Symmetry</a>\n2. <a href='https://scholar.google.com/scholar?q=craniofacial+anthropometry'>Craniofacial Anthropometry</a>"
    }

async def generate_face_summaries(
    metrics_payload: Dict[str, Any],
    image_b64: str,
) -> Dict[str, Any]:
    result_dict = _build_fallback_dict()

    try:
        user_text = (
            "Here is the biometric data profile of the user's face. Please analyze their features "
            f"and provide the complete analysis including celebrity archetype matches:\n{json.dumps(metrics_payload, indent=2)}"
        )

        logger.info("🧠 Sending unified multimodal request to OpenAI with STRICT LENGTH and DIVERSITY constraints...")

        response = await client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                },
            ],
            response_format=FaceAnalysisTexts,
            temperature=0.6, 
            max_tokens=6500, # Збільшено ліміт для більшого масиву порад
        )

        parsed_data = response.choices[0].message.parsed
        if parsed_data:
            ai_data = parsed_data.model_dump()

            overview_keys = ["eye_summary", "balance_summary", "nose_summary", "lips_summary", "brows_summary", "dmetrics_summary"]
            for key in overview_keys:
                if key in ai_data and ai_data[key]:
                    color = SECTION_THEME_COLORS.get(key, "#3B82F6")
                    ai_data[key] = wrap_overview_html(ai_data[key], theme_color=color)
                    
            match_keys = ["eye_match", "balance_match", "nose_match", "lips_match", "brows_match", "dmetrics_match"]
            for key in match_keys:
                if key in ai_data and ai_data[key]:
                    summary_key = key.replace('_match', '_summary')
                    color = SECTION_THEME_COLORS.get(summary_key, "#3B82F6")
                    ai_data[key] = wrap_match_html(ai_data[key], theme_color=color)

            if "dimorphism_summary" in ai_data and ai_data["dimorphism_summary"]:
                ai_data["dimorphism_summary"] = wrap_dimorphism_html(ai_data["dimorphism_summary"])

            for key, fallback_val in result_dict.items():
                if not ai_data.get(key):
                    ai_data[key] = fallback_val

            return ai_data

        return result_dict

    except Exception as e:
        logger.error(f"❌ OpenAI API Error: {e}", exc_info=True)
        return result_dict