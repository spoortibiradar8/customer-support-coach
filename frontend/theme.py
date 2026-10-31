"""Centralized theme and pastel glass-card styling for the Support Coach application."""

import streamlit as st


PAGE_THEMES = {
    "Dashboard": {
        "accent": "#C2347A",
        "tint": "#FDE7F1",
        "hover_tint": "#FFF0F6",
        "tab_active_bg": "#FDE7F1",
        "select_bg": "#FFF5F9",
        "border": "#F1E4EE",
        "brand_color": "#C2347A",
        "badge_color": "#A61E63",
    },
    "Sessions": {
        "accent": "#6D5BD0",
        "tint": "#ECE8FB",
        "hover_tint": "#F3F1FD",
        "tab_active_bg": "#ECE8FB",
        "select_bg": "#F5F3FD",
        "border": "#E2DEFA",
        "brand_color": "#6D5BD0",
        "badge_color": "#5844B8",
    },
    "Architecture": {
        "accent": "#0E7A6D",
        "tint": "#DDF5F1",
        "hover_tint": "#EDFAF7",
        "tab_active_bg": "#DDF5F1",
        "select_bg": "#F0FBF9",
        "border": "#CDEFEA",
        "brand_color": "#0E7A6D",
        "badge_color": "#0E7A6D",
    },
    "Milestone 2": {
        "accent": "#4B4D58",
        "tint": "#EEF2F7",
        "hover_tint": "#F7F9FC",
        "tab_active_bg": "#EEF2F7",
        "select_bg": "#F8FAFD",
        "border": "#E3E8F0",
        "brand_color": "#4B4D58",
        "badge_color": "#3D4254",
    },
}


def apply_theme(page_title: str = "Dashboard") -> None:
    """Inject centralized CSS styling for the application based on the active page."""
    theme = PAGE_THEMES.get(page_title, PAGE_THEMES["Dashboard"])
    accent = theme["accent"]
    tint = theme["tint"]
    hover_tint = theme["hover_tint"]
    tab_active_bg = theme["tab_active_bg"]
    select_bg = theme["select_bg"]
    border = theme["border"]
    brand_color = theme["brand_color"]
    badge_color = theme.get("badge_color", accent)

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ── Base Font & Reset: Inter with system sans fallback ── */
    html, body, [class*="css"], [data-testid="stMarkdownContainer"] p, .stMarkdown {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        font-size: 14px !important;
        color: #2B2433 !important;
    }}

    /* ── Field labels: 13px / 500 weight ── */
    label, [data-testid="stWidgetLabel"] p {{
        font-size: 13px !important;
        font-weight: 500 !important;
        color: #2B2433 !important;
        margin-bottom: 2px !important;
    }}

    /* ── Transparent header bar — keep it visible so sidebar toggle is reachable ── */
    header[data-testid="stHeader"] {{
        background: transparent !important;
        border-bottom: none !important;
        box-shadow: none !important;
        height: 2.5rem !important;
        z-index: 999 !important;
    }}
    [data-testid="stToolbar"] {{
        background: transparent !important;
        display: flex !important;
        visibility: visible !important;
    }}
    [data-testid="stAppDeployButton"],
    [data-testid="stToolbarActions"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stMainMenu"],
    [data-testid="stMainMenuButton"],
    #MainMenu,
    footer {{
        display: none !important;
        visibility: hidden !important;
    }}

    /* ── Sidebar collapse / expand toggle button: always visible and clearly clickable ── */
    [data-testid="stExpandSidebarButton"],
    [data-testid="stBaseButton-headerNoPadding"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    button[aria-label="Expand sidebar"],
    button[aria-label="Collapse sidebar"],
    button[kind="headerNoPadding"] {{
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        z-index: 99999 !important;
        color: #2B2433 !important;
        border-radius: 8px !important;
        transition: all 0.15s ease !important;
    }}
    [data-testid="stExpandSidebarButton"] {{
        background: rgba(255, 255, 255, 0.95) !important;
        border: 1px solid #E6D8E2 !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08) !important;
        padding: 4px !important;
        color: {accent} !important;
    }}
    [data-testid="stExpandSidebarButton"]:hover {{
        background: {hover_tint} !important;
        border-color: {accent} !important;
    }}

    /* ── App background gradient ── */
    .stApp {{
        background: linear-gradient(135deg, #FFF9FC 0%, {tint} 100%) !important;
        background-attachment: fixed !important;
    }}

    /* ── Main block container: comfortable top padding clearing header ── */
    .block-container {{
        padding-top: 2.2rem !important;
        padding-bottom: 0.4rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 1440px !important;
    }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background: rgba(255, 255, 255, 0.90) !important;
        backdrop-filter: blur(14px) !important;
        border-right: 1px solid {border} !important;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        padding-top: 1rem !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
    }}

    .sb-brand {{
        font-size: 1.15rem;
        font-weight: 700;
        color: {brand_color};
        letter-spacing: -0.02em;
        margin-bottom: 0.1rem;
        display: flex;
        align-items: center;
        gap: 7px;
    }}
    .sb-tagline {{
        font-size: 0.72rem;
        color: #6B6475;
        margin-bottom: 0.8rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid {border};
    }}
    .sb-section-label {{
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #8C8496;
        margin-top: 0.6rem;
        margin-bottom: 8px !important;
    }}

    /* ── Sidebar nav items: 8px gap ── */
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{
        border-radius: 9px !important;
        padding: 0.35rem 0.65rem !important;
        font-size: 0.86rem !important;
        font-weight: 500 !important;
        color: #2B2433 !important;
        transition: all 0.15s ease !important;
        margin-bottom: 8px !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {{
        background-color: {hover_tint} !important;
        color: {accent} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] {{
        background: {tint} !important;
        color: {accent} !important;
        font-weight: 700 !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    }}

    .sb-session-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 3px 5px;
        border-radius: 6px;
        font-size: 0.76rem;
        color: #3A3344;
        margin-bottom: 4px;
    }}
    .sb-session-row:hover {{ background: {hover_tint}; }}
    .sb-mode-badge {{
        font-size: 0.64rem;
        font-weight: 600;
        padding: 1px 6px;
        border-radius: 4px;
        background: {tint};
        color: {badge_color};
        white-space: nowrap;
    }}

    /* ── Header Row: 24px/600 ── */
    .app-header-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        height: 36px;
    }}
    .m2-flow-shell {{
        margin: 0.5rem 0 1.25rem;
        padding: 0.25rem 0;
    }}
    .m2-phone-card {{
        max-width: 980px;
        margin: 0 auto;
        border-radius: 26px;
        background: rgba(247, 247, 245, 0.95);
        border: 1px solid #E5E1E8;
        padding: 0.65rem 0.9rem 1rem;
        box-shadow: 0 10px 30px rgba(25, 20, 30, 0.06);
    }}
    .m2-statusbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.9rem;
        font-weight: 600;
        color: #1E1B2F;
        padding: 0.1rem 0.1rem 0.4rem;
    }}
    .m2-icons {{
        display: flex;
        align-items: center;
        gap: 0.55rem;
        font-size: 0.9rem;
        opacity: 0.8;
    }}
    .m2-header-row {{
        display: flex;
        align-items: center;
        gap: 0.9rem;
        margin: 0.8rem 0 0.75rem;
        padding-left: 0.15rem;
    }}
    .m2-close {{
        font-size: 2.2rem;
        line-height: 1;
        color: #1E1B2F;
        font-weight: 300;
    }}
    .m2-title {{
        font-size: clamp(1.1rem, 2vw, 2rem);
        font-weight: 500;
        color: #1E1B2F;
        letter-spacing: -0.03em;
    }}
    .m2-call-panel {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, #4B4D58 0%, #2F3340 100%);
        border-radius: 18px;
        padding: 0.7rem 0.8rem;
        min-height: 92px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
    }}
    .m2-call-left {{
        flex: 0 0 auto;
        width: 56px;
        display: flex;
        justify-content: center;
        align-items: center;
    }}
    .m2-icon-box {{
        width: 42px;
        height: 42px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid rgba(255,255,255,0.25);
        color: rgba(255,255,255,0.9);
        background: rgba(255,255,255,0.05);
        font-size: 1.3rem;
    }}
    .m2-call-center {{
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        min-width: 0;
    }}
    .m2-bubble-header {{
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.5rem;
    }}
    .m2-avatar {{
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        color: #FFFFFF;
        font-size: 1.05rem;
    }}
    .m2-avatar-rose {{ background: linear-gradient(135deg, #d1447c, #b62f6a); }}
    .m2-avatar-blue {{ background: linear-gradient(135deg, #3d80d5, #2d5bc7); }}
    .m2-call-labels {{
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.6rem;
        color: #F4F5F7;
        font-size: 0.95rem;
        overflow: hidden;
    }}
    .m2-label-left {{ opacity: 0.95; }}
    .m2-label-right {{ opacity: 0.92; }}
    .m2-badge {{
        min-width: 28px;
        height: 28px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: rgba(255,255,255,0.9);
        color: #2A2F3A;
        font-weight: 700;
        font-size: 0.8rem;
    }}
    .m2-call-note {{
        margin: 0.6rem 0 1rem;
        text-align: left;
        font-size: 0.9rem;
        color: #5C5867;
        padding-left: 0.3rem;
    }}
    .m2-message-block {{
        display: flex;
        align-items: flex-start;
        gap: 0.8rem;
        margin-bottom: 1rem;
    }}
    .m2-avatar-bubble {{
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: linear-gradient(135deg, #d8467e, #af2d65);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1rem;
        flex-shrink: 0;
        margin-top: 0.2rem;
    }}
    .m2-bubble-text {{
        flex: 1;
        background: rgba(255,255,255,0.7);
        border: 1px solid rgba(120,110,130,0.18);
        border-radius: 18px;
        padding: 0.9rem 1rem;
        font-size: clamp(1rem, 1.8vw, 1.35rem);
        line-height: 1.4;
        color: #23202F;
        box-shadow: 0 2px 10px rgba(40, 30, 48, 0.03);
    }}
    .m2-step-list {{
        display: flex;
        flex-direction: column;
        gap: 0.42rem;
    }}
    .m2-message-user {{
        justify-content: flex-end;
    }}
    .m2-message-user .m2-bubble-text {{
        max-width: 70%;
        background: transparent;
        border: none;
        box-shadow: none;
        padding: 0.2rem 0;
        font-size: 0.9rem;
        color: #5F586B;
    }}
    .m2-now {{
        margin-left: 0.5rem;
        color: #7A7287;
    }}
    .m2-message-timestamp {{
        text-align: center;
        color: #6A6476;
        font-size: 0.9rem;
        margin: 0.2rem 0 0.8rem;
    }}
    .m2-input-row {{
        display: flex;
        align-items: center;
        gap: 0.7rem;
        background: rgba(219, 220, 224, 0.8);
        border: 1px solid rgba(126, 126, 135, 0.15);
        border-radius: 18px;
        padding: 0.7rem 0.85rem;
        margin-top: 0.35rem;
    }}
    .m2-input-box {{
        flex: 1;
        font-size: 1.1rem;
        color: #6C6B73;
        min-height: 22px;
        display: flex;
        align-items: center;
    }}
    .m2-send-btn {{
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background: rgba(255,255,255,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #32313A;
        font-size: 1.1rem;
        font-weight: 700;
    }}
    .milestone-shell {{
        position: relative;
        margin: 0.5rem 0 1.15rem;
        padding: 0.8rem 1rem 0.25rem;
        border-radius: 16px;
        border: 1px solid #E7E2EA;
        background: rgba(255,255,255,0.78);
        box-shadow: 0 6px 24px rgba(40,26,52,0.05);
        overflow: hidden;
    }}
    .milestone-header {{
        font-size: clamp(1.15rem, 2vw, 2rem) !important;
        font-weight: 700 !important;
        line-height: 1.2;
        color: #1F1B2C !important;
        margin-bottom: 0.8rem;
        letter-spacing: -0.02em;
    }}
    .milestone-list {{
        display: flex;
        flex-direction: column;
        gap: 0.55rem;
    }}
    .milestone-row {{
        display: flex;
        align-items: flex-start;
        gap: 0.65rem;
        width: 100%;
        min-width: 0;
        padding: 0.2rem 0;
    }}
    .milestone-index {{
        flex-shrink: 0;
        font-size: clamp(0.95rem, 1.6vw, 1.25rem);
        font-weight: 500;
        color: #2B2433;
        line-height: 1.6;
    }}
    .milestone-copy {{
        flex: 1;
        min-width: 0;
        font-size: clamp(0.95rem, 1.5vw, 1.15rem);
        line-height: 1.45;
        font-weight: 400;
        color: #2B2433;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }}
    .highlight-row {{
        position: relative;
        padding-left: 0.15rem;
    }}
    .milestone-arrow {{
        flex-shrink: 0;
        width: 2.1rem;
        height: 2.1rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        background: rgba(103, 92, 119, 0.12);
        color: #2B2433;
        font-size: 1.5rem;
        font-weight: 600;
        line-height: 1;
        margin-top: 0.12rem;
    }}
    .milestone-arrow.left {{
        margin-right: 0.1rem;
    }}
    .milestone-arrow.right {{
        margin-left: 0.1rem;
    }}
    .app-title {{
        font-size: 24px !important;
        font-weight: 600 !important;
        color: #2B2433 !important;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }}
    .status-pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }}
    .status-pill.ready {{
        background: #DDF5F1;
        color: #0E7A6D;
        border: 1px solid #B8EADF;
    }}
    .status-pill.warn {{
        background: #FFE9DC;
        color: #9C3E08;
        border: 1px solid #FFD3BA;
    }}

    /* ── Stat Cards: 76px height, 12px padding, 24px/600 number, 11px uppercase label ── */
    .stat-card-row {{
        display: flex;
        gap: 12px;
        margin-bottom: 12px;
    }}
    .stat-card {{
        flex: 1;
        border-radius: 14px;
        padding: 12px !important;
        height: 76px !important;
        box-sizing: border-box !important;
        border: 1px solid rgba(255,255,255,0.6);
        box-shadow: 0 4px 20px rgba(80,50,90,0.05);
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    .stat-val {{
        font-size: 24px !important;
        font-weight: 600 !important;
        color: #2B2433 !important;
        line-height: 1 !important;
    }}
    .stat-val-text {{
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #2B2433 !important;
        line-height: 1 !important;
    }}
    .stat-val-accuracy {{
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #2B2433 !important;
        line-height: 1 !important;
        white-space: nowrap !important;
    }}
    .stat-lbl {{
        font-size: 11px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: #6B6475 !important;
        margin-top: 4px !important;
    }}

    /* ── Card Containers: 14px radius, 16px padding, 1px #F1E4EE, shadow ── */
    [data-testid="stVerticalBlockBorderWrapper"],
    .glass-card {{
        background: rgba(255, 255, 255, 0.85) !important;
        border: 1px solid #F1E4EE !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 20px rgba(80,50,90,0.06) !important;
        backdrop-filter: blur(10px) !important;
        padding: 16px !important;
    }}

    .card-title-16 {{
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #2B2433 !important;
        margin-bottom: 8px !important;
    }}

    /* ── Tabs ── */
    [data-testid="stTabs"] [data-baseweb="tab-list"],
    [data-testid="stTabs"] [role="tablist"] {{
        gap: 3px !important;
        border-bottom: 2px solid {border} !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab"],
    [data-testid="stTab"] {{
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 0.28rem 0.65rem !important;
        border-radius: 7px 7px 0 0 !important;
        color: #6B6475 !important;
        background: transparent !important;
        border-bottom: 2px solid transparent !important;
        margin-bottom: -2px !important;
    }}
    [data-testid="stTabs"] [aria-selected="true"][data-baseweb="tab"],
    [data-testid="stTab"][aria-selected="true"] {{
        background: {tab_active_bg} !important;
        color: {accent} !important;
        font-weight: 600 !important;
        border-bottom: 2px solid {accent} !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab"]:hover,
    [data-testid="stTab"]:hover {{
        background: {hover_tint} !important;
        color: {accent} !important;
    }}

    /* ── Expanders ── */
    [data-testid="stExpander"] {{
        border: 1px solid {border} !important;
        border-radius: 10px !important;
        background: #FFFFFF !important;
        margin-top: 0.25rem !important;
    }}
    [data-testid="stExpander"] summary:hover {{
        background: {hover_tint} !important;
        border-radius: 10px !important;
    }}

    /* ── Selectbox ── */
    [data-testid="stSelectbox"] > div > div {{
        border: 1px solid #E6D8E2 !important;
        border-radius: 9px !important;
        background: {select_bg} !important;
        font-size: 13px !important;
    }}
    [data-testid="stSelectbox"] > div > div:focus-within {{
        border-color: {accent} !important;
        box-shadow: 0 0 0 2px {tint} !important;
    }}

    /* ── Segmented Control / Radio ── */
    [data-testid="stSegmentedControl"] [data-baseweb="button-group"] {{
        border-radius: 9px !important;
        overflow: hidden !important;
    }}
    [data-testid="stSegmentedControl"] button[aria-checked="true"],
    button[data-variant="segmented_control"][aria-checked="true"],
    button[data-variant="segmented_control"][aria-selected="true"],
    button[data-variant="segmented_control"][data-selected="true"] {{
        background-color: {accent} !important;
        color: #FFFFFF !important;
    }}
    button[data-variant="segmented_control"][aria-checked="true"] *,
    button[data-variant="segmented_control"][aria-selected="true"] *,
    button[data-variant="segmented_control"][data-selected="true"] * {{
        color: #FFFFFF !important;
    }}

    /* ── Table & DataFrame ── */
    [data-testid="stTable"] th,
    [data-testid="stDataFrame"] th,
    .dvn-scroller thead th {{
        background: {tab_active_bg} !important;
        color: {accent} !important;
        font-weight: 600 !important;
        font-size: 12px !important;
    }}
    [data-testid="stTable"],
    [data-testid="stDataFrame"] {{
        border-radius: 10px !important;
        overflow: hidden !important;
        font-size: 13px !important;
    }}

    /* ── Buttons ── */
    .stButton > button[kind="primary"],
    button[kind="primary"] {{
        background-color: {accent} !important;
        border: none !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 9px !important;
        padding: 0.38rem 0.9rem !important;
        font-size: 13px !important;
        box-shadow: 0 2px 7px rgba(0,0,0,0.08) !important;
        transition: opacity 0.15s, transform 0.1s !important;
    }}
    .stButton > button[kind="primary"] *,
    button[kind="primary"] * {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }}
    .stButton > button[kind="primary"]:hover,
    button[kind="primary"]:hover {{
        opacity: 0.9 !important;
        transform: translateY(-1px) !important;
    }}
    .stButton > button[kind="primary"]:disabled,
    button[kind="primary"]:disabled {{
        opacity: 0.45 !important;
        cursor: not-allowed !important;
        transform: none !important;
    }}
    .stButton > button:not([kind="primary"]) {{
        background-color: #FFFFFF !important;
        border: 1px solid #E6D8E2 !important;
        color: #2B2433 !important;
        font-weight: 500 !important;
        border-radius: 9px !important;
        font-size: 13px !important;
    }}
    .stButton > button:not([kind="primary"]):hover {{
        border-color: {accent} !important;
        color: {accent} !important;
        background-color: {tint} !important;
    }}

    /* ── Inputs & Textareas ── */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {{
        border: 1px solid #E6D8E2 !important;
        border-radius: 9px !important;
        background: #FFFFFF !important;
        color: #2B2433 !important;
        font-size: 13px !important;
    }}
    [data-testid="stTextArea"] textarea {{
        min-height: 96px !important;
        height: 96px !important;
    }}
    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {{
        border-color: {accent} !important;
        box-shadow: 0 0 0 2px {tint} !important;
    }}

    /* ── Two-card heights & inner scroll control ── */
    [data-testid="column"]:nth-child(1) [data-testid="stVerticalBlockBorderWrapper"] > div {{
        overflow-y: auto !important;
    }}
    [data-testid="column"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="column"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"] > div {{
        overflow-y: hidden !important;
    }}

    /* ── Compact File Uploader ── */
    [data-testid="stFileUploader"] {{
        padding: 0 !important;
    }}
    [data-testid="stFileUploaderDropzone"] {{
        padding: 0.6rem !important;
        min-height: 80px !important;
    }}

    /* ── Disabled button helper text: 12px grey ── */
    .btn-disabled-note {{
        font-size: 12px !important;
        color: #8C8496 !important;
        text-align: center;
        margin-top: 4px;
    }}

    /* ── Character counter (only when close to limit) ── */
    .counter-warning {{
        font-size: 11px;
        color: #B5541B;
        text-align: right;
        margin-top: -2px;
    }}

    /* ── Search Results Compact Rows ── */
    .search-result-row {{
        border-left: 3px solid {accent};
        background: rgba(255,255,255,0.7);
        border-radius: 0 8px 8px 0;
        padding: 5px 8px;
        margin-bottom: 5px;
    }}
    .score-bar-bg {{
        background: #EAE8EE;
        border-radius: 3px;
        height: 4px;
        width: 100%;
        margin: 3px 0;
    }}
    .score-bar-fill {{
        background: {accent};
        border-radius: 3px;
        height: 4px;
    }}

    /* ── Footer: 12px muted line ── */
    .app-footer {{
        font-size: 12px !important;
        color: #8C8496 !important;
        margin-top: 12px;
        margin-bottom: 6px;
    }}

    /* ── Spacing reductions ── */
    [data-testid="stVerticalBlock"] {{
        gap: 0.35rem !important;
    }}
    .main > [data-testid="stVerticalBlock"] {{
        gap: 0.5rem !important;
    }}
    [data-testid="column"] {{
        padding-left: 0.35rem !important;
        padding-right: 0.35rem !important;
    }}
    @media (max-width: 760px) {{
        .milestone-shell {{
            padding: 0.75rem 0.7rem 0.2rem;
        }}
        .milestone-row {{
            gap: 0.45rem;
        }}
        .milestone-arrow {{
            width: 1.7rem;
            height: 1.7rem;
            font-size: 1.2rem;
        }}
        .m2-phone-card {{
            padding: 0.55rem 0.7rem 0.8rem;
        }}
        .m2-call-panel {{
            min-height: 86px;
        }}
        .m2-input-row {{
            padding: 0.6rem 0.7rem;
        }}
    }}
    @media (max-width: 560px) {{
        .milestone-row {{
            flex-wrap: wrap;
            gap: 0.35rem;
        }}
        .milestone-arrow {{
            display: none;
        }}
        .milestone-index {{
            width: 1.5rem;
        }}
        .m2-call-panel {{
            padding: 0.55rem 0.55rem;
        }}
        .m2-header-row {{
            gap: 0.55rem;
        }}
        .m2-close {{
            font-size: 1.8rem;
        }}
        .m2-title {{
            font-size: 1.2rem;
        }}
        .m2-message-block {{
            gap: 0.55rem;
        }}
        .m2-bubble-text {{
            padding: 0.8rem 0.8rem;
        }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
