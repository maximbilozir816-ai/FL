# face/report_order.py
from typing import List

# ==============================================================================
# MASTER PDF REPORT PAGE ORDER CONFIGURATION
# ==============================================================================

PDF_PAGE_ORDER: List[str] = [
    # --- 1. INTRODUCTORY & SUMMARY BLOCKS ---
    "overall_score_ctx",       # Main cover page with final Overall Score
    "radar_summary_ctx",       # Radar chart summary & 18 metrics list
    "overall_impression_ctx",  # NEW: Full text aesthetic impression page

    # --- 2. EYE AREA ---
    "overview_ctx",            
    "icd",                     
    "ocd",                     
    "esize",                   

    # --- 3. FACIAL BALANCE ---
    "balance_overview_ctx",    
    "thirds",                  
    "fifths",                  
    "facial_index",            
    
    # --- 4. LIPS & MOUTH ---
    "lips_overview_ctx",       
    "lips_to_nose",            
    "lips_width",              
    "lips_weight",             
    
    # --- 5. NOSE ---
    "nose_overview_ctx",       
    "nose_height",             
    "nose_width",              
    "nose_to_lips",            

    # --- 6. BROWS ---
    "brows_overview_ctx",      
    "eye_eyebrow",             
    "eyebrow_density",         
    "eyebrow_tilt",            
      
    # --- 7. DENTAL & LOWER FACE (DMETRICS) ---
    "dmetrics_overview_ctx",   
    "fwhr",                    
    "jaw_facew",               
    "chin_lowerth",            

    # --- 8. ADVANCED ANALYTICAL OVERVIEWS ---
    "dimorphism_overview_ctx", 
    "summary_advice_ctx",
]