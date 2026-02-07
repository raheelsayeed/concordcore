#!/usr/bin/env python3
"""Minimal monotone styling - compact single column layout."""

COLORS = {
    "background": "#FDF1E5",
    "surface": "#FFFFFF",
    "border": "#E0D5C7",
    "text_primary": "#000000",
    "text_secondary": "#333333",
    "text_muted": "#666666",
    "accent_soft": "rgba(0, 0, 0, 0.04)",
}


def get_custom_css() -> str:
    """Generate custom CSS - compact layout, minimal whitespace."""
    c = COLORS

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap');

    .stApp {{
        background-color: {c['background']};
        font-family: 'Lato', sans-serif;
    }}

    #MainMenu, footer, header {{visibility: hidden;}}

    [data-testid="stSidebar"] {{
        display: none !important;
    }}

    /* Compact centered column */
    .main .block-container {{
        max-width: 800px !important;
        padding: 1.5rem 2rem 3rem 2rem !important;
        margin: 0 auto !important;
    }}

    @media (min-width: 1400px) {{
        .main .block-container {{
            max-width: 900px !important;
        }}
    }}

    /* Typography */
    h1 {{
        font-size: 2.5rem !important;
        font-weight: 900 !important;
        letter-spacing: -0.03em !important;
        color: {c['text_primary']} !important;
        line-height: 1.1 !important;
        margin: 0 0 0.25rem 0 !important;
    }}

    h2 {{
        font-size: 1.75rem !important;
        font-weight: 900 !important;
        letter-spacing: -0.02em !important;
        color: {c['text_primary']} !important;
        line-height: 1.2 !important;
        margin: 0 0 1rem 0 !important;
    }}

    h3 {{
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        color: {c['text_primary']} !important;
        margin: 0 0 0.75rem 0 !important;
    }}

    h4 {{
        font-size: 1.125rem !important;
        font-weight: 700 !important;
        color: {c['text_primary']} !important;
        margin: 0 !important;
    }}

    p, li, span, label {{
        font-size: 1rem !important;
        line-height: 1.7 !important;
        color: {c['text_secondary']} !important;
    }}

    /* Compact buttons */
    .stButton > button {{
        background-color: {c['text_primary']} !important;
        color: {c['background']} !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 700 !important;
        font-size: 0.875rem !important;
    }}

    .stButton > button:hover {{
        opacity: 0.85 !important;
    }}

    .stButton > button[kind="secondary"] {{
        background-color: transparent !important;
        border: 1.5px solid {c['border']} !important;
        color: {c['text_primary']} !important;
    }}

    /* Tabs - compact */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0 !important;
        background: transparent !important;
        border-bottom: 1.5px solid {c['border']} !important;
    }}

    .stTabs [data-baseweb="tab"] {{
        padding: 0.625rem 1rem !important;
        font-size: 0.875rem !important;
        font-weight: 400 !important;
        color: {c['text_muted']} !important;
        border-bottom: 2px solid transparent !important;
        margin-bottom: -1.5px !important;
    }}

    .stTabs [aria-selected="true"] {{
        font-weight: 700 !important;
        color: {c['text_primary']} !important;
        border-bottom: 2px solid {c['text_primary']} !important;
    }}

    /* Form elements */
    .stSelectbox > div > div {{
        background-color: {c['surface']} !important;
        border: 1.5px solid {c['border']} !important;
        border-radius: 6px !important;
        font-size: 0.9375rem !important;
    }}

    .stSelectbox label {{
        font-size: 0.875rem !important;
        color: {c['text_muted']} !important;
    }}

    .stMultiSelect > div > div {{
        background-color: {c['surface']} !important;
        border: 1.5px solid {c['border']} !important;
        border-radius: 6px !important;
    }}

    .streamlit-expanderHeader {{
        font-size: 1rem !important;
        font-weight: 700 !important;
        background: transparent !important;
        border: none !important;
        padding: 0.5rem 0 !important;
    }}

    .stCheckbox label {{
        font-size: 0.9375rem !important;
    }}

    hr {{
        border: none !important;
        border-top: 1.5px solid {c['border']} !important;
        margin: 1.5rem 0 !important;
    }}

    /* Hide metrics - we use custom */
    [data-testid="stMetric"] {{
        display: none !important;
    }}

    /* Reduce column gaps */
    [data-testid="column"] {{
        padding: 0 0.5rem !important;
    }}

    ::-webkit-scrollbar {{
        width: 5px;
    }}
    ::-webkit-scrollbar-thumb {{
        background: {c['border']};
        border-radius: 3px;
    }}
    </style>
    """
