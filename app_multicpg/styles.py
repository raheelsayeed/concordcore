#!/usr/bin/env python3
"""Concord Design System — dark monotone, AI-first with sidebar navigation."""

# Design Tokens
COLORS = {
    # Base
    "bg": "#0A0A0A",
    "surface": "#141414",
    "surface_alt": "#1A1A1A",
    "border": "#262626",
    "border_strong": "#333333",

    # Text
    "text": "#E5E5E5",
    "text_secondary": "#999999",
    "text_muted": "#666666",

    # Accent (monotone — white on black)
    "accent": "#E5E5E5",
    "accent_hover": "#FFFFFF",
    "accent_soft": "#1A1A1A",
    "accent_text": "#0A0A0A",

    # Clinical status (muted for dark bg)
    "success": "#34D399",
    "success_soft": "#064E3B",
    "warning": "#FBBF24",
    "warning_soft": "#451A03",
    "error": "#F87171",
    "error_soft": "#450A0A",
    "info": "#60A5FA",
    "info_soft": "#1E3A5F",

    # Priority
    "priority_critical": "#F87171",
    "priority_high": "#FB923C",
    "priority_moderate": "#60A5FA",
    "priority_low": "#94A3B8",
    "priority_info": "#666666",

    # Evidence
    "evidence_strong": "#34D399",
    "evidence_moderate": "#60A5FA",
    "evidence_weak": "#FBBF24",
    "evidence_harmful": "#F87171",
}

TYPE = {
    "2xs": "0.625rem",   # 10px - micro
    "xs": "0.6875rem",   # 11px - labels
    "sm": "0.8125rem",   # 13px - secondary
    "base": "0.9375rem", # 15px - body
    "lg": "1.0625rem",   # 17px - emphasis
    "xl": "1.25rem",     # 20px - headings
    "2xl": "1.5rem",     # 24px - page title
}

SPACE = {
    "1": "0.25rem",
    "2": "0.5rem",
    "3": "0.75rem",
    "4": "1rem",
    "5": "1.25rem",
    "6": "1.5rem",
    "8": "2rem",
    "10": "2.5rem",
    "12": "3rem",
}


def get_custom_css() -> str:
    c = COLORS
    t = TYPE
    s = SPACE

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ===== Base ===== */
    html {{ font-size: 16px; }}

    .stApp {{
        background: {c['bg']};
        font-family: 'Inter', -apple-system, system-ui, sans-serif;
        color: {c['text']};
        -webkit-font-smoothing: antialiased;
    }}

    #MainMenu, footer {{
        display: none !important;
    }}

    header[data-testid="stHeader"] {{
        background: transparent !important;
        border: none !important;
    }}

    header[data-testid="stHeader"] button {{
        color: {c['text_muted']} !important;
    }}

    [data-testid="stBaseButton-header"] {{
        display: none !important;
    }}

    .main .block-container {{
        max-width: 960px !important;
        padding: {s['8']} {s['6']} !important;
        margin: 0 auto !important;
    }}

    /* ===== Sidebar ===== */
    section[data-testid="stSidebar"] {{
        background: {c['bg']} !important;
        border-right: 1px solid {c['border']} !important;
    }}

    section[data-testid="stSidebar"] > div:first-child {{
        padding-top: {s['8']} !important;
    }}

    /* Sidebar brand */
    .sidebar-brand {{
        font-size: 1rem;
        font-weight: 700;
        color: {c['text']};
        letter-spacing: -0.04em;
        margin-bottom: {s['6']};
        padding: 0 {s['3']};
    }}

    /* Sidebar section labels */
    .sidebar-section-label {{
        font-size: {t['2xs']};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: {c['text_muted']};
        margin: 0 0 {s['2']} 0;
        padding: 0 {s['3']};
    }}

    /* Sidebar patient buttons */
    [data-testid="stSidebar"] .stButton > button {{
        background: transparent !important;
        color: {c['text_secondary']} !important;
        border: none !important;
        text-align: left !important;
        padding: {s['2']} {s['3']} !important;
        border-radius: 6px !important;
        font-weight: 400 !important;
        font-size: {t['sm']} !important;
        transition: background 0.15s ease !important;
    }}

    [data-testid="stSidebar"] .stButton > button:hover {{
        background: {c['surface']} !important;
        color: {c['text']} !important;
    }}

    [data-testid="stSidebar"] .stButton > button:not([kind="secondary"]) {{
        background: {c['surface']} !important;
        color: {c['text']} !important;
        font-weight: 600 !important;
    }}

    /* Sidebar patient context */
    .sidebar-divider {{
        height: 1px;
        background: {c['border']};
        margin: {s['5']} {s['3']};
    }}

    .sidebar-demo {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        margin: 0;
        padding: 0 {s['3']};
    }}

    .sidebar-conditions {{
        font-size: {t['xs']};
        color: {c['text_muted']};
        margin: {s['1']} 0 0 0;
        padding: 0 {s['3']};
    }}

    .sidebar-meds {{
        font-size: {t['xs']};
        color: {c['text_muted']};
        margin: {s['1']} 0 0 0;
        padding: 0 {s['3']};
    }}

    /* Sidebar metrics */
    .sidebar-metric-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 3px {s['3']};
        font-size: {t['sm']};
    }}

    .sidebar-metric-label {{
        color: {c['text_muted']};
    }}

    .sidebar-metric-value {{
        font-weight: 600;
        color: {c['text']};
    }}

    .sidebar-metric-value.high {{ color: {c['error']}; }}
    .sidebar-metric-value.low {{ color: {c['warning']}; }}
    .sidebar-metric-value.normal {{ color: {c['success']}; }}

    /* ===== Brand (welcome page) ===== */
    .brand {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {c['text']};
        letter-spacing: -0.04em;
        margin-bottom: {s['2']};
    }}

    .page-desc {{
        font-size: {t['base']};
        color: {c['text_muted']};
        margin: 0;
        line-height: 1.5;
    }}

    /* ===== Page headings ===== */
    .page-patient-name {{
        font-size: {t['2xl']};
        font-weight: 700;
        color: {c['text']};
        letter-spacing: -0.02em;
        margin: 0 0 {s['1']} 0;
    }}

    .page-patient-desc {{
        font-size: {t['sm']};
        color: {c['text_muted']};
        margin: 0 0 {s['6']} 0;
    }}

    .results-summary {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        margin: 0 0 {s['6']} 0;
    }}

    /* ===== Section heading ===== */
    .section-heading {{
        font-size: {t['xs']};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: {c['text_muted']};
        margin: 0 0 {s['4']} 0;
        display: flex;
        align-items: center;
        gap: {s['2']};
    }}

    .section-count {{
        font-weight: 400;
        color: {c['border_strong']};
    }}

    /* ===== CPG cards (screening page) ===== */
    .cpg-card {{
        padding: {s['4']} {s['5']};
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-bottom: {s['2']};
    }}

    .cpg-card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: {s['1']};
    }}

    .cpg-card-name {{
        font-size: {t['base']};
        font-weight: 600;
        color: {c['text']};
    }}

    .cpg-card-category {{
        font-size: {t['2xs']};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: {c['text_muted']};
    }}

    .cpg-card-desc {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        margin: 0;
        line-height: 1.5;
    }}

    .cpg-na-row {{
        padding: {s['1']} 0;
        font-size: {t['sm']};
        color: {c['text_muted']};
        border-bottom: 1px solid {c['surface_alt']};
    }}

    .cpg-na-row:last-child {{
        border-bottom: none;
    }}

    /* ===== Alert row ===== */
    .alert-row {{
        display: flex;
        align-items: center;
        gap: {s['3']};
        padding: {s['3']} {s['4']};
        background: {c['warning_soft']};
        border: 1px solid #332200;
        border-radius: 8px;
        font-size: {t['sm']};
        color: {c['warning']};
        margin-bottom: {s['6']};
    }}

    .alert-icon {{
        flex-shrink: 0;
    }}

    /* ===== Recommendation cards ===== */
    .rec-card {{
        border-left: 3px solid {c['border_strong']};
        padding: {s['4']} {s['5']};
        margin-bottom: {s['2']};
        background: {c['surface']};
        border-radius: 0 8px 8px 0;
    }}

    .rec-card.priority-critical {{ border-left-color: {c['priority_critical']}; }}
    .rec-card.priority-high {{ border-left-color: {c['priority_high']}; }}
    .rec-card.priority-moderate {{ border-left-color: {c['priority_moderate']}; }}
    .rec-card.priority-low {{ border-left-color: {c['border_strong']}; }}
    .rec-card.priority-info {{ border-left-color: {c['border']}; }}

    .rec-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: {s['1']};
    }}

    .rec-priority {{
        font-size: {t['2xs']};
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: {c['text_muted']};
    }}

    .rec-priority.critical {{ color: {c['priority_critical']}; }}
    .rec-priority.high {{ color: {c['priority_high']}; }}
    .rec-priority.moderate {{ color: {c['priority_moderate']}; }}

    .rec-grade {{
        font-size: {t['2xs']};
        font-weight: 600;
        color: {c['text_muted']};
        letter-spacing: 0.04em;
    }}

    .rec-title {{
        font-size: {t['base']};
        font-weight: 600;
        color: {c['text']};
        margin: 0 0 {s['1']} 0;
        line-height: 1.4;
    }}

    .rec-narrative {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        line-height: 1.6;
        margin: 0 0 {s['2']} 0;
    }}

    .rec-source {{
        font-size: {t['xs']};
        color: {c['border_strong']};
    }}

    .empty-text {{
        font-size: {t['sm']};
        color: {c['text_muted']};
        padding: {s['4']} 0;
    }}

    /* ===== Detail rows (expander content) ===== */
    .detail-row {{
        display: flex;
        align-items: center;
        gap: {s['2']};
        padding: {s['2']} 0;
        border-bottom: 1px solid {c['surface_alt']};
        font-size: {t['sm']};
    }}

    .detail-row:last-child {{
        border-bottom: none;
    }}

    .detail-label {{
        flex: 1;
        color: {c['text_secondary']};
    }}

    .detail-value {{
        font-weight: 600;
        color: {c['text']};
        text-align: right;
    }}

    .detail-value.high {{ color: {c['error']}; }}
    .detail-value.low {{ color: {c['warning']}; }}
    .detail-value.normal {{ color: {c['success']}; }}
    .detail-value.v-true {{ color: {c['success']}; }}
    .detail-value.v-false {{ color: {c['text_muted']}; }}
    .detail-value.v-number {{ color: {c['text']}; }}
    .detail-value.v-missing {{ color: {c['border_strong']}; }}

    .detail-dot {{
        width: 6px;
        height: 6px;
        border-radius: 50%;
        flex-shrink: 0;
    }}

    .detail-dot.true {{ background: {c['success']}; }}
    .detail-dot.false {{ background: {c['border_strong']}; }}
    .detail-dot.error {{ background: {c['error']}; }}

    .detail-group {{
        font-size: {t['2xs']};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: {c['border_strong']};
        margin: {s['4']} 0 {s['1']} 0;
        padding: 0;
    }}

    .detail-cpg-title {{
        font-size: {t['xs']};
        font-weight: 600;
        color: {c['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin: {s['5']} 0 {s['2']} 0;
        padding-bottom: {s['2']};
        border-bottom: 1px solid {c['border']};
    }}

    .detail-cpg-title:first-child {{
        margin-top: 0;
    }}

    /* ===== Conflict items ===== */
    .conflict-item {{
        display: flex;
        align-items: center;
        gap: {s['2']};
        margin-top: {s['3']};
    }}

    .conflict-item:first-child {{
        margin-top: 0;
    }}

    .conflict-severity-tag {{
        font-size: {t['2xs']};
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 2px 6px;
        border-radius: 3px;
    }}

    .conflict-severity-tag.critical {{ color: {c['error']}; background: {c['error_soft']}; }}
    .conflict-severity-tag.high {{ color: {c['priority_high']}; background: #431407; }}
    .conflict-severity-tag.medium {{ color: {c['warning']}; background: {c['warning_soft']}; }}
    .conflict-severity-tag.low {{ color: {c['info']}; background: {c['info_soft']}; }}

    .conflict-type {{
        font-size: {t['xs']};
        color: {c['text_muted']};
    }}

    .conflict-desc {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        line-height: 1.5;
        margin: {s['1']} 0 {s['1']} 0;
    }}

    .conflict-cpgs {{
        font-size: {t['xs']};
        color: {c['border_strong']};
        margin: 0 0 {s['3']} 0;
    }}

    .conflict-resolution {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        padding: {s['3']} {s['4']};
        background: {c['surface_alt']};
        border-radius: 6px;
        margin: 0 0 {s['3']} 0;
        line-height: 1.5;
    }}

    /* ===== Streamlit Overrides (dark) ===== */

    /* Selectbox & Multiselect */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {{
        background: {c['surface']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 8px !important;
        color: {c['text']} !important;
        font-size: {t['sm']} !important;
    }}

    .stSelectbox > div > div:focus-within,
    .stMultiSelect > div > div:focus-within {{
        border-color: {c['border_strong']} !important;
        box-shadow: none !important;
    }}

    .stSelectbox [data-baseweb="select"] span,
    .stSelectbox [data-baseweb="select"] input {{
        color: {c['text']} !important;
    }}

    .stMultiSelect [data-baseweb="tag"] {{
        background: {c['border_strong']} !important;
        border-radius: 4px !important;
        margin: 2px !important;
    }}

    .stMultiSelect [data-baseweb="tag"] span {{
        color: {c['text']} !important;
        font-size: {t['xs']} !important;
    }}

    [data-baseweb="popover"] {{
        background: {c['surface']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 8px !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
    }}

    [data-baseweb="menu"] {{
        background: {c['surface']} !important;
    }}

    [data-baseweb="menu"] li {{
        font-size: {t['sm']} !important;
        color: {c['text']} !important;
    }}

    [data-baseweb="menu"] li:hover {{
        background: {c['surface_alt']} !important;
    }}

    /* Buttons (main content) */
    .main .stButton > button {{
        background: {c['text']} !important;
        color: {c['bg']} !important;
        border: none !important;
        border-radius: 8px !important;
        padding: {s['3']} {s['5']} !important;
        font-size: {t['sm']} !important;
        font-weight: 600 !important;
        transition: opacity 0.15s ease !important;
    }}

    .main .stButton > button:hover {{
        background: {c['accent_hover']} !important;
        opacity: 0.9;
    }}

    .main .stButton > button:disabled {{
        opacity: 0.2 !important;
    }}

    .main .stButton > button[kind="secondary"] {{
        background: transparent !important;
        border: 1px solid {c['border_strong']} !important;
        color: {c['text_secondary']} !important;
        padding: 6px {s['3']} !important;
        font-size: {t['xs']} !important;
    }}

    .main .stButton > button[kind="secondary"]:hover {{
        border-color: {c['text_muted']} !important;
        color: {c['text']} !important;
        background: transparent !important;
    }}

    /* Expanders */
    [data-testid="stExpander"] {{
        border: 1px solid {c['border']} !important;
        border-radius: 8px !important;
        overflow: hidden;
        margin-bottom: {s['2']} !important;
    }}

    .streamlit-expanderHeader {{
        background: {c['surface']} !important;
        color: {c['text_secondary']} !important;
        font-size: {t['sm']} !important;
        font-weight: 600 !important;
        padding: {s['3']} {s['4']} !important;
        border: none !important;
    }}

    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
        background: {c['bg']} !important;
        border-top: 1px solid {c['border']} !important;
        padding: {s['4']} !important;
    }}

    /* Alerts */
    [data-testid="stAlert"] {{
        background: {c['error_soft']} !important;
        border: 1px solid #330000 !important;
        color: {c['error']} !important;
    }}

    /* Spinner */
    .stSpinner > div {{
        border-color: {c['text']} transparent transparent transparent !important;
    }}

    /* Reset spacing */
    .stMarkdown {{
        min-height: 0 !important;
    }}

    div[data-testid="stVerticalBlock"] > div {{
        margin: 0 !important;
    }}

    [data-testid="column"] {{
        padding: 0 {s['2']} !important;
    }}

    /* ===== Responsive ===== */
    @media (max-width: 768px) {{
        .main .block-container {{
            max-width: 100% !important;
            padding: {s['4']} {s['4']} !important;
        }}
        .page-patient-name {{
            font-size: {t['xl']};
        }}
    }}
    </style>
    """
