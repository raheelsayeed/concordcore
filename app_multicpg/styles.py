#!/usr/bin/env python3
"""Concord Design System - clinical dashboard for providers."""

# Design Tokens
COLORS = {
    # Base
    "bg": "#F4F5F7",
    "surface": "#FFFFFF",
    "surface_alt": "#F8F9FB",
    "border": "#E2E5EA",
    "border_strong": "#CBD0D8",

    # Text
    "text": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#94A3B8",

    # Accent
    "accent": "#2563EB",
    "accent_hover": "#1D4ED8",
    "accent_soft": "#EFF6FF",
    "accent_text": "#FFFFFF",

    # Clinical status
    "success": "#059669",
    "success_soft": "#ECFDF5",
    "warning": "#D97706",
    "warning_soft": "#FFFBEB",
    "error": "#DC2626",
    "error_soft": "#FEF2F2",
    "info": "#0284C7",
    "info_soft": "#F0F9FF",

    # Priority
    "priority_critical": "#DC2626",
    "priority_high": "#EA580C",
    "priority_moderate": "#2563EB",
    "priority_low": "#64748B",
    "priority_info": "#94A3B8",

    # Evidence
    "evidence_strong": "#059669",
    "evidence_moderate": "#0284C7",
    "evidence_weak": "#D97706",
    "evidence_harmful": "#DC2626",
}

# Typography
TYPE = {
    "xs": "0.6875rem",   # 11px - micro labels
    "sm": "0.8125rem",   # 13px - secondary
    "base": "0.9375rem", # 15px - body
    "lg": "1.0625rem",   # 17px - emphasis
    "xl": "1.25rem",     # 20px - headings
    "2xl": "1.75rem",    # 28px - page titles
    "3xl": "2.25rem",    # 36px - hero
}

# Spacing
SPACE = {
    "1": "0.25rem",   # 4px
    "2": "0.5rem",    # 8px
    "3": "0.75rem",   # 12px
    "4": "1rem",      # 16px
    "5": "1.25rem",   # 20px
    "6": "1.5rem",    # 24px
    "8": "2rem",      # 32px
    "10": "2.5rem",   # 40px
}


def get_custom_css() -> str:
    c = COLORS
    t = TYPE
    s = SPACE

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Base */
    html {{ font-size: 16px; }}

    .stApp {{
        background: {c['bg']};
        font-family: 'Inter', -apple-system, system-ui, sans-serif;
        color: {c['text']};
        -webkit-font-smoothing: antialiased;
    }}

    #MainMenu, footer, header, [data-testid="stSidebar"] {{
        display: none !important;
    }}

    .main .block-container {{
        max-width: 1320px !important;
        padding: {s['2']} {s['6']} {s['8']} {s['6']} !important;
        margin: 0 auto !important;
    }}

    /* ===== Top Nav ===== */
    .top-nav {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: {s['3']} 0;
        margin-bottom: {s['5']};
        border-bottom: 1px solid {c['border']};
    }}

    .top-nav-brand {{
        font-size: {t['lg']};
        font-weight: 700;
        color: {c['text']};
        letter-spacing: -0.02em;
    }}

    .top-nav-brand span {{
        color: {c['accent']};
    }}

    .top-nav-meta {{
        font-size: {t['xs']};
        color: {c['text_muted']};
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        letter-spacing: 0.04em;
    }}

    /* ===== Patient Banner ===== */
    .patient-banner {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: {s['5']};
        margin-bottom: {s['5']};
        display: flex;
        align-items: center;
        gap: {s['5']};
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}

    .patient-avatar {{
        width: 48px;
        height: 48px;
        border-radius: 12px;
        background: {c['accent_soft']};
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        font-weight: 700;
        color: {c['accent']};
        flex-shrink: 0;
    }}

    .patient-info {{
        flex: 1;
        min-width: 0;
    }}

    .patient-name {{
        font-size: {t['xl']};
        font-weight: 700;
        color: {c['text']};
        margin: 0;
        letter-spacing: -0.01em;
    }}

    .patient-demo {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        margin: 2px 0 0 0;
    }}

    .patient-conditions {{
        display: flex;
        align-items: center;
        gap: {s['2']};
        flex-wrap: wrap;
    }}

    .condition-chip {{
        font-size: {t['xs']};
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 600;
        background: {c['warning_soft']};
        color: {c['warning']};
        border: 1px solid rgba(217, 119, 6, 0.15);
    }}

    .condition-chip.med {{
        background: {c['info_soft']};
        color: {c['info']};
        border-color: rgba(2, 132, 199, 0.15);
    }}

    .condition-chip.ok {{
        background: {c['success_soft']};
        color: {c['success']};
        border-color: rgba(5, 150, 105, 0.15);
    }}

    .risk-badge {{
        font-size: {t['xs']};
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    .risk-badge.risk-high {{
        background: {c['error_soft']};
        color: {c['error']};
        border: 1px solid rgba(220, 38, 38, 0.15);
    }}

    .risk-badge.risk-moderate {{
        background: {c['warning_soft']};
        color: {c['warning']};
        border: 1px solid rgba(217, 119, 6, 0.15);
    }}

    .risk-badge.risk-low {{
        background: {c['success_soft']};
        color: {c['success']};
        border: 1px solid rgba(5, 150, 105, 0.15);
    }}

    /* ===== Stats Row ===== */
    .stats-row {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: {s['3']};
        margin-bottom: {s['5']};
    }}

    .stat-card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        padding: {s['4']};
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}

    .stat-card-value {{
        font-size: {t['2xl']};
        font-weight: 700;
        color: {c['text']};
        line-height: 1;
        margin-bottom: 4px;
    }}

    .stat-card-value.accent {{
        color: {c['accent']};
    }}

    .stat-card-value.success {{
        color: {c['success']};
    }}

    .stat-card-value.warning {{
        color: {c['warning']};
    }}

    .stat-card-value.error {{
        color: {c['error']};
    }}

    .stat-card-label {{
        font-size: {t['xs']};
        color: {c['text_muted']};
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}

    /* ===== Section Headers ===== */
    .section-header {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        margin-bottom: {s['4']};
        padding-bottom: {s['2']};
        border-bottom: 1px solid {c['border']};
    }}

    .section-title {{
        font-size: {t['lg']};
        font-weight: 700;
        color: {c['text']};
        margin: 0;
        letter-spacing: -0.01em;
    }}

    .section-count {{
        font-size: {t['xs']};
        color: {c['text_muted']};
        font-weight: 500;
        font-family: 'JetBrains Mono', monospace;
    }}

    /* ===== Recommendation Cards ===== */
    .rec-card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-left: 4px solid {c['border']};
        border-radius: 10px;
        padding: {s['4']};
        margin-bottom: {s['3']};
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: box-shadow 0.15s ease;
    }}

    .rec-card:hover {{
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }}

    .rec-card.priority-critical {{ border-left-color: {c['priority_critical']}; }}
    .rec-card.priority-high {{ border-left-color: {c['priority_high']}; }}
    .rec-card.priority-moderate {{ border-left-color: {c['priority_moderate']}; }}
    .rec-card.priority-low {{ border-left-color: {c['priority_low']}; }}
    .rec-card.priority-info {{ border-left-color: {c['priority_info']}; }}

    .rec-card-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: {s['2']};
        margin-bottom: 6px;
    }}

    .rec-card-meta {{
        display: flex;
        align-items: center;
        gap: {s['2']};
    }}

    .rec-priority-tag {{
        font-size: {t['xs']};
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 2px 8px;
        border-radius: 4px;
    }}

    .rec-priority-tag.critical {{
        color: {c['priority_critical']};
        background: {c['error_soft']};
    }}

    .rec-priority-tag.high {{
        color: {c['priority_high']};
        background: #FFF7ED;
    }}

    .rec-priority-tag.moderate {{
        color: {c['priority_moderate']};
        background: {c['accent_soft']};
    }}

    .rec-priority-tag.low {{
        color: {c['priority_low']};
        background: {c['surface_alt']};
    }}

    .rec-priority-tag.info {{
        color: {c['priority_info']};
        background: {c['surface_alt']};
    }}

    .rec-evidence {{
        font-size: {t['xs']};
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        background: {c['text']};
        color: {c['surface']};
    }}

    .rec-category-tag {{
        font-size: {t['xs']};
        color: {c['text_muted']};
        font-weight: 500;
    }}

    .rec-card-title {{
        font-size: {t['base']};
        font-weight: 600;
        color: {c['text']};
        margin: 0 0 4px 0;
        line-height: 1.4;
    }}

    .rec-card-narrative {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        line-height: 1.6;
        margin: 0 0 8px 0;
    }}

    .rec-card-source {{
        font-size: {t['xs']};
        color: {c['text_muted']};
    }}

    .rec-card-conflict {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: {t['xs']};
        color: {c['warning']};
        font-weight: 600;
        margin-left: {s['2']};
    }}

    /* ===== Health Data Panel ===== */
    .health-panel {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: {s['3']};
        transition: box-shadow 0.15s ease;
    }}

    .health-panel:hover {{
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}

    .health-panel-header {{
        padding: 8px {s['4']};
        background: {c['surface_alt']};
        border-bottom: 1px solid {c['border']};
        font-size: {t['xs']};
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: {c['text_secondary']};
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    .health-panel-header .panel-icon {{
        width: 4px;
        height: 14px;
        border-radius: 2px;
        flex-shrink: 0;
    }}

    .health-panel-header .panel-icon.vitals {{ background: {c['error']}; }}
    .health-panel-header .panel-icon.lipids {{ background: {c['priority_high']}; }}
    .health-panel-header .panel-icon.metabolic {{ background: {c['warning']}; }}
    .health-panel-header .panel-icon.demo {{ background: {c['accent']}; }}
    .health-panel-header .panel-icon.conditions {{ background: {c['priority_critical']}; }}
    .health-panel-header .panel-icon.meds {{ background: {c['info']}; }}
    .health-panel-header .panel-icon.smoking {{ background: {c['text_muted']}; }}

    .health-panel-body {{
        padding: 0;
    }}

    .health-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 9px {s['4']};
        border-bottom: 1px solid {c['border']};
        font-size: {t['sm']};
    }}

    .health-row:nth-child(even) {{
        background: {c['surface_alt']};
    }}

    .health-row:last-child {{
        border-bottom: none;
    }}

    .health-row-label {{
        color: {c['text_secondary']};
        font-weight: 500;
    }}

    .health-row-value {{
        font-weight: 600;
        color: {c['text']};
        font-family: 'JetBrains Mono', monospace;
        font-size: {t['xs']};
    }}

    .health-row-value.high {{
        color: {c['error']};
    }}

    .health-row-value.low {{
        color: {c['warning']};
    }}

    .health-row-value.normal {{
        color: {c['success']};
    }}

    /* ===== Key Findings ===== */
    .findings-panel {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}

    .finding-row {{
        display: flex;
        align-items: center;
        gap: {s['3']};
        padding: 10px {s['4']};
        border-bottom: 1px solid {c['border']};
        font-size: {t['sm']};
    }}

    .finding-row:nth-child(even) {{
        background: {c['surface_alt']};
    }}

    .finding-row:last-child {{
        border-bottom: none;
    }}

    .finding-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }}

    .finding-dot.critical {{ background: {c['priority_critical']}; }}
    .finding-dot.high {{ background: {c['priority_high']}; }}
    .finding-dot.moderate {{ background: {c['priority_moderate']}; }}
    .finding-dot.low {{ background: {c['priority_low']}; }}

    .finding-label {{
        flex: 1;
        font-weight: 600;
        color: {c['text']};
    }}

    .finding-value {{
        font-family: 'JetBrains Mono', monospace;
        font-size: {t['xs']};
        color: {c['text_secondary']};
        font-weight: 500;
    }}

    /* ===== Assessment Summary ===== */
    .assess-summary {{
        display: flex;
        gap: {s['4']};
        margin-bottom: {s['4']};
        flex-wrap: wrap;
    }}

    .assess-summary-item {{
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: {t['sm']};
        color: {c['text_secondary']};
    }}

    .assess-summary-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }}

    .assess-summary-dot.positive {{ background: {c['success']}; }}
    .assess-summary-dot.negative {{ background: {c['border_strong']}; }}
    .assess-summary-dot.unavailable {{ background: {c['text_muted']}; }}
    .assess-summary-dot.error {{ background: {c['error']}; }}

    /* ===== Assessment Table ===== */
    .assess-table {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}

    .assess-table-header {{
        display: grid;
        grid-template-columns: 8px 1fr 100px;
        gap: {s['3']};
        padding: 8px {s['4']};
        background: {c['surface_alt']};
        border-bottom: 1px solid {c['border']};
        font-size: {t['xs']};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: {c['text_muted']};
        align-items: center;
    }}

    .assess-row {{
        display: grid;
        grid-template-columns: 8px 1fr 100px;
        gap: {s['3']};
        padding: 8px {s['4']};
        border-bottom: 1px solid {c['border']};
        align-items: center;
        font-size: {t['sm']};
    }}

    .assess-row:nth-child(even) {{
        background: {c['surface_alt']};
    }}

    .assess-row:last-child {{
        border-bottom: none;
    }}

    .assess-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }}

    .assess-dot.true {{ background: {c['success']}; }}
    .assess-dot.false {{ background: {c['border_strong']}; }}
    .assess-dot.error {{ background: {c['error']}; }}

    .assess-name {{
        font-weight: 500;
        color: {c['text']};
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}

    .assess-val {{
        font-family: 'JetBrains Mono', monospace;
        font-size: {t['xs']};
        font-weight: 600;
        text-align: right;
    }}

    .assess-val.v-true {{
        color: {c['success']};
    }}

    .assess-val.v-false {{
        color: {c['text_muted']};
    }}

    .assess-val.v-number {{
        color: {c['text']};
    }}

    .assess-val.v-missing {{
        color: {c['border_strong']};
    }}

    .assess-cpg-divider {{
        padding: 6px {s['4']};
        background: {c['surface_alt']};
        border-bottom: 1px solid {c['border']};
        font-size: {t['xs']};
        font-weight: 600;
        color: {c['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    /* ===== Guideline Cards ===== */
    .gl-card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        padding: {s['4']};
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}

    .gl-card.eligible {{
        border-color: {c['success']};
    }}

    .gl-card-top {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 8px;
    }}

    .gl-card-category {{
        font-size: {t['xs']};
        font-weight: 600;
        color: {c['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}

    .gl-status {{
        font-size: {t['xs']};
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
    }}

    .gl-status.eligible {{
        color: {c['success']};
        background: {c['success_soft']};
    }}

    .gl-status.not-eligible {{
        color: {c['text_muted']};
        background: {c['surface_alt']};
    }}

    .gl-card-title {{
        font-size: {t['base']};
        font-weight: 600;
        color: {c['text']};
        margin: 0 0 4px 0;
        line-height: 1.4;
    }}

    .gl-card-desc {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        line-height: 1.5;
        margin: 0 0 {s['3']} 0;
    }}

    .gl-card-stats {{
        display: flex;
        gap: {s['4']};
    }}

    .gl-card-stat {{
        display: flex;
        flex-direction: column;
    }}

    .gl-card-stat-value {{
        font-size: {t['lg']};
        font-weight: 700;
        color: {c['text']};
        line-height: 1;
    }}

    .gl-card-stat-label {{
        font-size: {t['xs']};
        color: {c['text_muted']};
    }}

    /* ===== Conflict Alert ===== */
    .conflict-banner {{
        background: {c['warning_soft']};
        border: 1px solid rgba(217, 119, 6, 0.25);
        border-radius: 10px;
        padding: {s['4']};
        margin-bottom: {s['5']};
        display: flex;
        align-items: flex-start;
        gap: {s['3']};
    }}

    .conflict-banner-icon {{
        font-size: 1.25rem;
        line-height: 1;
        flex-shrink: 0;
    }}

    .conflict-banner-text {{
        flex: 1;
    }}

    .conflict-banner-title {{
        font-size: {t['base']};
        font-weight: 600;
        color: #92400E;
        margin: 0 0 2px 0;
    }}

    .conflict-banner-desc {{
        font-size: {t['sm']};
        color: #B45309;
        margin: 0;
    }}

    .conflict-card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-left: 4px solid {c['warning']};
        border-radius: 8px;
        padding: {s['4']};
        margin-bottom: {s['3']};
    }}

    .conflict-severity {{
        font-size: {t['xs']};
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 2px 8px;
        border-radius: 4px;
    }}

    .conflict-severity.critical {{
        color: {c['error']};
        background: {c['error_soft']};
    }}

    .conflict-severity.high {{
        color: {c['priority_high']};
        background: #FFF7ED;
    }}

    .conflict-severity.medium {{
        color: {c['warning']};
        background: {c['warning_soft']};
    }}

    .conflict-severity.low {{
        color: {c['info']};
        background: {c['info_soft']};
    }}

    /* ===== Setup Page ===== */
    .setup-header {{
        margin-bottom: {s['6']};
    }}

    .setup-title {{
        font-size: {t['2xl']};
        font-weight: 700;
        color: {c['text']};
        margin: 0 0 {s['2']} 0;
        letter-spacing: -0.02em;
    }}

    .setup-subtitle {{
        font-size: {t['base']};
        color: {c['text_secondary']};
        margin: 0;
        max-width: 600px;
    }}

    .patient-select-card {{
        background: {c['surface']};
        border: 1.5px solid {c['border']};
        border-radius: 10px;
        padding: {s['4']};
        cursor: pointer;
        transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.1s ease;
        height: 140px;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }}

    .patient-select-card:hover {{
        border-color: {c['border_strong']};
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }}

    .patient-select-card.selected {{
        border-color: {c['accent']};
        box-shadow: 0 0 0 1.5px {c['accent']};
        background: {c['accent_soft']};
    }}

    .patient-card-name {{
        font-size: {t['base']};
        font-weight: 600;
        color: {c['text']};
        margin: 0 0 2px 0;
    }}

    .patient-card-meta {{
        font-size: {t['sm']};
        color: {c['text_muted']};
        margin: 0 0 {s['2']} 0;
    }}

    .patient-card-desc {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        margin: 0;
        line-height: 1.5;
    }}

    .patient-card-data {{
        display: flex;
        gap: {s['4']};
        margin-top: auto;
        padding-top: {s['3']};
        border-top: 1px solid {c['border']};
        flex-wrap: wrap;
    }}

    .patient-card-datum {{
        display: flex;
        flex-direction: column;
    }}

    .patient-card-datum-label {{
        font-size: {t['xs']};
        color: {c['text_muted']};
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    .patient-card-datum-value {{
        font-size: {t['xs']};
        font-weight: 600;
        color: {c['text']};
        font-family: 'JetBrains Mono', monospace;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 90px;
    }}

    /* ===== Grid Layouts ===== */
    .grid-2 {{
        display: grid;
        gap: {s['4']};
        grid-template-columns: repeat(2, 1fr);
    }}

    .grid-3 {{
        display: grid;
        gap: {s['4']};
        grid-template-columns: repeat(3, 1fr);
    }}

    /* ===== Misc ===== */
    .label {{
        font-size: {t['xs']};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: {c['text_muted']};
        margin-bottom: {s['2']};
    }}

    .empty-state {{
        text-align: center;
        padding: {s['4']};
        color: {c['text_muted']};
        font-size: {t['sm']};
        background: {c['surface']};
        border: 1px dashed {c['border']};
        border-radius: 10px;
    }}

    .empty-state.positive {{
        background: {c['success_soft']};
        border-color: rgba(5, 150, 105, 0.2);
        color: {c['success']};
    }}

    .eval-footer {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        padding: {s['4']} {s['5']};
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: {s['4']};
        margin-top: {s['4']};
    }}

    .eval-footer-text {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        font-weight: 500;
    }}

    .eval-footer-text strong {{
        color: {c['text']};
        font-weight: 700;
    }}

    .divider {{
        height: 1px;
        background: {c['border']};
        margin: {s['5']} 0;
    }}

    .back-link {{
        font-size: {t['sm']};
        color: {c['text_secondary']};
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }}

    .back-link:hover {{
        color: {c['text']};
    }}

    /* ===== Streamlit Overrides ===== */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {{
        background: {c['surface']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 8px !important;
        font-size: {t['sm']} !important;
        min-height: 2.5rem !important;
    }}

    .stSelectbox > div > div:focus-within,
    .stMultiSelect > div > div:focus-within {{
        border-color: {c['accent']} !important;
        box-shadow: 0 0 0 1px {c['accent']} !important;
    }}

    .stMultiSelect [data-baseweb="tag"] {{
        background: {c['accent']} !important;
        border-radius: 6px !important;
        margin: 2px !important;
    }}

    .stMultiSelect [data-baseweb="tag"] span {{
        color: {c['accent_text']} !important;
        font-size: {t['xs']} !important;
        font-weight: 500 !important;
    }}

    [data-baseweb="popover"] {{
        background: {c['surface']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 8px !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.12) !important;
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

    /* Buttons */
    .stButton > button {{
        background: {c['accent']} !important;
        color: {c['accent_text']} !important;
        border: none !important;
        border-radius: 8px !important;
        padding: {s['3']} {s['5']} !important;
        font-size: {t['sm']} !important;
        font-weight: 600 !important;
        transition: background 0.15s ease, box-shadow 0.15s ease !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;
    }}

    .stButton > button:hover {{
        background: {c['accent_hover']} !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
    }}

    .stButton > button:disabled {{
        opacity: 0.5 !important;
    }}

    .stButton > button[kind="secondary"] {{
        background: {c['surface']} !important;
        border: 1px solid {c['border']} !important;
        color: {c['text_secondary']} !important;
        padding: 6px {s['3']} !important;
        font-size: {t['xs']} !important;
        box-shadow: none !important;
    }}

    .stButton > button[kind="secondary"]:hover {{
        border-color: {c['border_strong']} !important;
        background: {c['surface_alt']} !important;
        box-shadow: none !important;
    }}

    /* Expander */
    [data-testid="stExpander"] {{
        border: 1px solid {c['border']} !important;
        border-radius: 10px !important;
        overflow: hidden;
    }}

    .streamlit-expanderHeader {{
        font-size: {t['sm']} !important;
        font-weight: 600 !important;
        background: {c['surface']} !important;
        padding: {s['3']} {s['4']} !important;
        border: none !important;
    }}

    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
        background: {c['surface']} !important;
        border-top: 1px solid {c['border']} !important;
        padding: {s['4']} !important;
        border: none !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0 !important;
        background: {c['surface_alt']};
        border-radius: 8px;
        padding: 3px;
        border: 1px solid {c['border']};
    }}

    .stTabs [data-baseweb="tab"] {{
        font-size: {t['sm']} !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        border-radius: 6px !important;
        color: {c['text_secondary']} !important;
        background: transparent !important;
        border-bottom: none !important;
    }}

    .stTabs [aria-selected="true"] {{
        background: {c['surface']} !important;
        color: {c['text']} !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06) !important;
    }}

    .stTabs [data-baseweb="tab-highlight"] {{
        display: none !important;
    }}

    .stTabs [data-baseweb="tab-border"] {{
        display: none !important;
    }}

    /* Hide spacing */
    .stMarkdown {{
        min-height: 0 !important;
    }}

    div[data-testid="stVerticalBlock"] > div {{
        margin: 0 !important;
    }}

    [data-testid="column"] {{
        padding: 0 {s['2']} !important;
    }}

    /* Spinner */
    .stSpinner > div {{
        border-color: {c['accent']} transparent transparent transparent !important;
    }}

    @media (max-width: 900px) {{
        .stats-row {{
            grid-template-columns: repeat(2, 1fr);
        }}
        .grid-3, .grid-2 {{
            grid-template-columns: 1fr;
        }}
        .patient-banner {{
            flex-direction: column;
            align-items: flex-start;
        }}
    }}
    </style>
    """
