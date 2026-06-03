import os
from dotenv import load_dotenv
load_dotenv()
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import time
import numpy as np
from typing import Dict, List
import re 

# --- 页面配置 ---
st.set_page_config(
    page_title="BioMarket Tracker",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)
# ========== 恢复 Refresh 保存的状态 ==========
if '_saved_tickers' in st.session_state:
    # ✅ 使用 get() 方法避免 AttributeError
    st.session_state.selected_tickers = st.session_state.get('_saved_tickers', [])
    st.session_state.selected_time_range = st.session_state.get('_saved_time_range', '1y')
    st.session_state.custom_tickers = st.session_state.get('_saved_custom', [])
    st.session_state.preset_tickers = st.session_state.get('_saved_preset', [])
    st.session_state.analysis_started = st.session_state.get('_saved_analysis_started', True)
    st.session_state.is_refreshing = st.session_state.get('_saved_is_refreshing', True)
    
    # 清除临时变量
    for key in ['_saved_tickers', '_saved_time_range', '_saved_custom', 
                '_saved_preset', '_saved_analysis_started', '_saved_is_refreshing']:
        if key in st.session_state:
            del st.session_state[key]
# =============================================

# --- 初始化 Session State（新增）---
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'analysis_context' not in st.session_state:
    st.session_state.analysis_context = None
if 'show_chat' not in st.session_state:
    st.session_state.show_chat = False
if 'last_analysis' not in st.session_state:
    st.session_state.last_analysis = None
if 'is_refreshing' not in st.session_state:  
    st.session_state.is_refreshing = False

# ========== 新增：分析完成标志 ==========
if 'analysis_completed' not in st.session_state:
    st.session_state.analysis_completed = False
if 'analyzed_tickers' not in st.session_state:
    st.session_state.analyzed_tickers = []
# ======================================

# --- 自定义 CSS 样式（Anthropic Editorial × Pharma Data Terminal）---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;1,400&family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600&display=swap');

    /* =====================================================================
       DESIGN SYSTEM: Anthropic Editorial × Pharma Data Terminal
       Palette: Warm Off-White · Biotech Sage Green · Warm Black
       Typography: Crimson Pro (headings) · Inter (UI) · Mono (numbers)
       ===================================================================== */

    :root {
        --bg:           #f5f4ed;
        --surface:      #faf9f5;
        --surface-2:    #f0eee6;
        --text:         #141413;
        --text-2:       #4d4c48;
        --text-3:       #87867f;
        --border:       #e8e6dc;
        --border-2:     #d1cfc5;
        --accent:       #4a7c59;
        --accent-h:     #5d8f6e;
        --accent-l:     #eaf3de;
        --gold:         #8a7340;
        --gold-l:       #faf0dc;
        --red:          #b53333;
        --red-l:        #fdf0f0;
    }

    /* ---- Streamlit chrome cleanup ---- */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}

    /* ---- Page background ---- */
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"], .main {
        background: var(--bg) !important;
        font-variant-numeric: tabular-nums;
    }
    [data-testid="stAppViewContainer"] > .block-container,
    .block-container {
        padding-top: 1.5rem !important;
    }

    /* =====================================================================
       HEADING OVERRIDES — highest specificity to beat Streamlit's injected
       #667eea / #7c3aed purple defaults
       ===================================================================== */
    h1, h2, h3, h4, h5, h6,
    .main h1, .main h2, .main h3, .main h4,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stVerticalBlock"] h1,
    [data-testid="stVerticalBlock"] h2,
    [data-testid="stVerticalBlock"] h3,
    [data-testid="stVerticalBlock"] h4,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
    .element-container h1, .element-container h2,
    .element-container h3, .element-container h4 {
        font-family: 'Crimson Pro', 'Georgia', 'Times New Roman', serif !important;
        font-weight: 500 !important;
        color: var(--text) !important;
        line-height: 1.15 !important;
        border-bottom-color: var(--border) !important;
    }

    /* =====================================================================
       BUTTON OVERRIDES — target both old [kind] attr and new data-testid
       ===================================================================== */
    [data-testid="baseButton-primary"],
    button[kind="primary"],
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: var(--surface) !important;
        font-family: 'Inter', system-ui, sans-serif !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        transition: background 0.18s ease, border-color 0.18s ease !important;
        box-shadow: none !important;
    }
    [data-testid="baseButton-primary"]:hover,
    button[kind="primary"]:hover,
    .stButton > button[kind="primary"]:hover {
        background: var(--accent-h) !important;
        border-color: var(--accent-h) !important;
    }

    [data-testid="baseButton-secondary"],
    button[kind="secondary"],
    .stButton > button:not([kind="primary"]):not([data-testid="collapsedControl"]),
    .stButton > button[data-testid="baseButton-secondary"] {
        background: var(--surface-2) !important;
        border: 1px solid var(--border-2) !important;
        color: var(--text-2) !important;
        font-family: 'Inter', system-ui, sans-serif !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        transition: background 0.15s ease !important;
        box-shadow: none !important;
    }
    [data-testid="baseButton-secondary"]:hover,
    .stButton > button:not([kind="primary"]):not([data-testid="collapsedControl"]):hover {
        background: var(--border) !important;
        color: var(--text) !important;
        border-color: var(--border-2) !important;
    }

    /* Download button — same as primary */
    [data-testid="stDownloadButton"] button {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: var(--surface) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-family: 'Inter', system-ui, sans-serif !important;
    }
    [data-testid="stDownloadButton"] button:hover {
        background: var(--accent-h) !important;
    }

    /* Preserve Streamlit Material Icons */
    [data-testid="collapsedControl"],
    [data-testid="collapsedControl"] *,
    button[aria-label="Open sidebar"],
    button[aria-label="Open sidebar"] *,
    button[aria-label="Close sidebar"],
    button[aria-label="Close sidebar"] * {
        font-family: "Material Icons", "Material Symbols Outlined", "Material Icons Outlined" !important;
        font-feature-settings: "liga" !important;
        -webkit-font-smoothing: antialiased !important;
    }

    /* =====================================================================
       ALERT / INFO / SUCCESS / WARNING / ERROR OVERRIDES
       Streamlit renders via [data-baseweb="notification"] and .stAlert
       ===================================================================== */
    [data-testid="stAlert"],
    .stAlert,
    [data-baseweb="notification"] {
        border-radius: 10px !important;
        font-family: 'Inter', system-ui, sans-serif !important;
    }
    /* Info — sage green tint */
    [data-testid="stAlert"][data-type="info"],
    .stAlert-info {
        background: #f0f7f3 !important;
        border-color: var(--accent) !important;
        color: #2d5240 !important;
    }
    /* Success — lighter green */
    [data-testid="stAlert"][data-type="success"],
    .stAlert-success {
        background: var(--accent-l) !important;
        border-color: #3d6b4e !important;
        color: #2d5240 !important;
    }
    /* Error — warm red */
    [data-testid="stAlert"][data-type="error"],
    .stAlert-error {
        background: var(--red-l) !important;
        border-color: var(--red) !important;
        color: #7a2323 !important;
    }
    /* Warning — gold */
    [data-testid="stAlert"][data-type="warning"],
    .stAlert-warning {
        background: var(--gold-l) !important;
        border-color: var(--gold) !important;
        color: #5a4a22 !important;
    }
    [data-testid="stAlert"] p, .stAlert p {
        font-family: 'Inter', system-ui, sans-serif !important;
        font-size: 0.88rem !important;
    }

    /* =====================================================================
       SIDEBAR
       ===================================================================== */
    [data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 0.5px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * {
        font-family: 'Inter', system-ui, sans-serif !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        font-family: 'Crimson Pro', 'Georgia', serif !important;
        color: var(--text) !important;
    }
    [data-testid="stSidebar"] .stTabs [data-baseweb="tab-border"] {
        background-color: var(--accent) !important;
    }
    [data-testid="stSidebar"] .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
    }
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] small {
        color: var(--text-3) !important;
        font-size: 0.78rem !important;
    }

    /* =====================================================================
       TABS
       ===================================================================== */
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', system-ui, sans-serif !important;
        color: var(--text-3) !important;
        font-size: 0.85rem !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
        font-weight: 500 !important;
    }
    .stTabs [data-baseweb="tab-border"] {
        background-color: var(--accent) !important;
    }

    /* =====================================================================
       FORM INPUTS
       ===================================================================== */
    .stSelectbox label, .stMultiSelect label,
    .stTextInput label, .stNumberInput label {
        font-family: 'Inter', system-ui, sans-serif !important;
        color: var(--text-3) !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em !important;
        text-transform: uppercase !important;
    }
    [data-baseweb="select"] > div,
    .stTextInput > div > div > input {
        background: var(--surface) !important;
        border-color: var(--border) !important;
        color: var(--text) !important;
        border-radius: 8px !important;
    }
    .stMultiSelect [data-baseweb="tag"] {
        background: var(--accent) !important;
        color: var(--surface) !important;
        border-radius: 4px !important;
    }

    /* =====================================================================
       EXPANDER
       ===================================================================== */
    .stExpander {
        border: 0.5px solid var(--border) !important;
        border-radius: 10px !important;
        background: var(--surface) !important;
    }
    .stExpander > div:first-child {
        font-family: 'Inter', system-ui, sans-serif !important;
        color: var(--text-2) !important;
    }

    /* =====================================================================
       STATUS COMPONENT (AI analysis streaming)
       ===================================================================== */
    [data-testid="stStatus"] {
        background: var(--surface) !important;
        border: 0.5px solid var(--border) !important;
        border-radius: 10px !important;
    }
    [data-testid="stStatus"] .stMarkdown p,
    [data-testid="stStatus"] .stMarkdown li,
    [data-testid="stStatus"] .stMarkdown h1,
    [data-testid="stStatus"] .stMarkdown h2,
    [data-testid="stStatus"] .stMarkdown h3 {
        font-family: 'Crimson Pro', 'Georgia', serif !important;
        font-variant-numeric: tabular-nums !important;
        color: var(--text) !important;
    }
    [data-testid="stStatus"] .stMarkdown p {
        font-size: 1.05rem !important;
        line-height: 1.72 !important;
    }

    /* =====================================================================
       DATAFRAME / TABLE
       ===================================================================== */
    .stDataFrame, .dataframe {
        font-family: 'Inter', system-ui, sans-serif !important;
        font-size: 0.82rem !important;
        font-variant-numeric: tabular-nums !important;
    }

    /* =====================================================================
       GENERAL MARKDOWN
       ===================================================================== */
    .stMarkdown p, .stMarkdown span,
    .stMarkdown li, .stMarkdown label {
        font-family: 'Inter', system-ui, sans-serif !important;
    }
    .stMarkdown p, .stMarkdown li {
        color: var(--text-2) !important;
    }
    code {
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
        background: var(--surface-2) !important;
        padding: 0.1rem 0.3rem !important;
        border-radius: 4px !important;
        font-size: 0.83rem !important;
        color: var(--text-2) !important;
    }
    hr {
        border: none !important;
        border-top: 0.5px solid var(--border) !important;
        margin: 1.8rem 0 !important;
    }

    /* =====================================================================
       SCROLLBAR
       ===================================================================== */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-3); }

    /* =====================================================================
       CUSTOM COMPONENT STYLES
       ===================================================================== */

    /* Brand Header */
    .brand-header {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        padding: 1.2rem 0 0.4rem;
    }
    .brand-title {
        font-family: 'Crimson Pro', 'Georgia', serif !important;
        color: var(--text) !important;
        font-size: 2.5rem !important;
        font-weight: 500 !important;
        letter-spacing: -0.3px !important;
        line-height: 1.1 !important;
        margin: 0 !important;
        text-align: center !important;
    }
    .brand-sub {
        font-family: 'Inter', system-ui, sans-serif !important;
        color: var(--text-3) !important;
        font-size: 0.87rem !important;
        margin: 0.25rem 0 0.5rem !important;
        text-align: center !important;
        letter-spacing: 0.01em !important;
    }
    .brand-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 0.72rem;
        color: var(--accent);
        background: var(--accent-l);
        padding: 2px 10px;
        border-radius: 20px;
        font-family: 'Inter', system-ui, sans-serif;
        font-weight: 600;
        letter-spacing: 0.04em;
        border: 0.5px solid #c0d9c8;
    }

    /* Section Title */
    .section-title {
        font-family: 'Crimson Pro', 'Georgia', serif !important;
        font-size: 1.3rem !important;
        font-weight: 500 !important;
        color: var(--text) !important;
        margin: 2rem 0 0.6rem !important;
        padding-bottom: 0.35rem !important;
        border-bottom: 0.5px solid var(--border) !important;
        line-height: 1.15 !important;
    }

    /* Price Cards */
    .price-card {
        font-family: 'Inter', system-ui, sans-serif;
        background: var(--surface);
        padding: 1rem 1.1rem;
        border-radius: 10px;
        box-shadow: 0 0 0 0.5px var(--border);
        border-left: 3px solid;
        margin: 0.4rem 0;
        transition: box-shadow 0.18s ease;
    }
    .price-card:hover { box-shadow: 0 4px 18px rgba(0,0,0,0.07); }
    .price-card.positive { border-left-color: var(--accent); }
    .price-card.negative { border-left-color: var(--red); }
    .card-ticker {
        font-size: 0.73rem;
        color: var(--text-3);
        font-weight: 500;
        margin-bottom: 0.2rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    .card-price {
        font-size: 1.65rem;
        font-weight: 500;
        margin: 0.2rem 0;
        font-variant-numeric: tabular-nums;
    }
    .card-change {
        font-size: 0.8rem;
        font-weight: 500;
        font-variant-numeric: tabular-nums;
    }

    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 0.18rem 0.65rem;
        border-radius: 5px;
        font-size: 0.77rem;
        font-weight: 500;
        margin: 0.15rem;
        font-family: 'Inter', system-ui, sans-serif;
    }
    .status-bullish {
        background: var(--accent-l);
        color: #2d5240;
        box-shadow: 0 0 0 0.5px #b5d9bd;
    }
    .status-bearish {
        background: var(--red-l);
        color: #7a2323;
        box-shadow: 0 0 0 0.5px #f0b8b8;
    }
    .status-neutral {
        background: var(--gold-l);
        color: #5a4a22;
        box-shadow: 0 0 0 0.5px #e0cc98;
    }

    /* Ticker Tags */
    .ticker-tag {
        display: inline-block;
        background: var(--accent);
        color: var(--surface);
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        margin: 0.1rem;
        font-size: 0.73rem;
        font-weight: 600;
        font-family: 'Inter', system-ui, sans-serif;
        letter-spacing: 0.03em;
    }
    .ticker-tag.custom { background: var(--gold); }

    /* Alert Card */
    .alert-card {
        background: var(--red-l);
        padding: 0.85rem 1rem;
        border-radius: 9px;
        color: #7a2323;
        margin: 0.4rem 0;
        font-weight: 500;
        box-shadow: 0 0 0 0.5px #f0b8b8;
        font-family: 'Inter', system-ui, sans-serif;
        font-size: 0.88rem;
    }

    /* Live dot */
    .live-dot {
        display: inline-block;
        width: 7px; height: 7px;
        background: var(--accent);
        border-radius: 50%;
        animation: pulse 2.2s infinite;
        margin-right: 5px;
        vertical-align: middle;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.25; }
    }

    /* Selection Summary */
    .selection-summary {
        background: var(--surface);
        padding: 1.3rem 1.5rem;
        border-radius: 12px;
        box-shadow: 0 0 0 0.5px var(--border);
        margin: 0.8rem 0;
    }
    .selection-summary h3 {
        font-family: 'Crimson Pro', 'Georgia', serif !important;
        color: var(--text) !important;
        font-weight: 500 !important;
        margin: 0 0 0.8rem !important;
        font-size: 1.2rem !important;
        border-bottom: none !important;
    }
    .selection-summary p {
        font-family: 'Inter', system-ui, sans-serif !important;
        color: var(--text-2) !important;
        font-size: 0.88rem !important;
    }

    /* Chat Interface */
    .chat-container {
        background: var(--surface);
        border-radius: 12px;
        padding: 1.3rem;
        margin: 1.5rem 0;
        box-shadow: 0 0 0 0.5px var(--border);
    }
    .chat-message {
        padding: 0.9rem 1rem;
        border-radius: 8px;
        margin: 0.7rem 0;
        font-family: 'Inter', system-ui, sans-serif;
    }
    .chat-message.user {
        background: var(--surface);
        border-left: 2.5px solid var(--accent);
        box-shadow: 0 0 0 0.5px var(--border);
    }
    .chat-message.assistant {
        background: var(--bg);
        border-left: 2.5px solid var(--gold);
        box-shadow: 0 0 0 0.5px var(--border);
    }
    .chat-message.assistant p {
        font-family: 'Crimson Pro', 'Georgia', serif !important;
        font-size: 1.02rem !important;
        line-height: 1.68 !important;
        color: var(--text) !important;
    }
    .chat-header {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-3);
        margin-bottom: 0.4rem;
        font-family: 'Inter', system-ui, sans-serif;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .chat-divider {
        border-top: 0.5px solid var(--border);
        margin: 1.2rem 0;
    }

    /* News Links */
    .news-link-container { margin: 0 0 4px; }
    .news-link {
        display: flex;
        align-items: center;
        padding: 0.38rem 0.85rem;
        background: var(--surface);
        border-left: 2.5px solid var(--accent);
        border-radius: 0 6px 6px 0;
        text-decoration: none;
        color: var(--text-2);
        transition: all 0.15s ease;
        width: 100%;
        box-sizing: border-box;
        font-family: 'Inter', system-ui, sans-serif;
        font-size: 0.82rem;
        box-shadow: 0 0 0 0.5px var(--border);
    }
    .news-link:hover {
        background: var(--accent-l);
        box-shadow: 0 0 0 0.5px #b5d9bd;
        color: var(--text);
    }
    .official-link { border-left-color: var(--gold); }
    .official-link:hover {
        background: var(--gold-l);
        box-shadow: 0 0 0 0.5px #e0cc98;
    }

    /* Welcome Cards */
    .welcome-card {
        background: var(--surface);
        border: 0.5px solid var(--border);
        border-radius: 12px;
        padding: 1.2rem 1.3rem;
    }
    .welcome-card h4 {
        font-family: 'Crimson Pro', 'Georgia', serif !important;
        font-size: 1.1rem !important;
        font-weight: 500 !important;
        color: var(--text) !important;
        margin: 0 0 0.55rem !important;
        border-bottom: none !important;
    }
    .welcome-card p, .welcome-card li {
        font-family: 'Inter', system-ui, sans-serif !important;
        font-size: 0.82rem !important;
        color: var(--text-3) !important;
        line-height: 1.55 !important;
    }
    .welcome-card-accent { border-top: 2.5px solid var(--accent); }
    .welcome-card-gold   { border-top: 2.5px solid var(--gold); }
    .welcome-card-blue   { border-top: 2.5px solid #5580a0; }

    /* Disclaimer */
    .disclaimer {
        text-align: center;
        font-family: 'Inter', system-ui, sans-serif;
        font-size: 0.76rem;
        color: var(--text-3);
        padding: 1rem;
        background: var(--surface);
        border-radius: 9px;
        box-shadow: 0 0 0 0.5px var(--border);
        margin-top: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 配置 ---
BASE_URL = "https://api.deepseek.com"

# --- 映射表 ---
TICKER_MAP = {
    'XBI': 'XBI (标普生物科技ETF)',
    'IBB': 'IBB (纳斯达克生科ETF)',
    'MRNA': 'MRNA (莫德纳)',
    'PFE': 'PFE (辉瑞制药)',
    'VRTX': 'VRTX (福泰制药)',
    'REGN': 'REGN (再生元制药)',
    'AMGN': 'AMGN (安进公司)',
    'GILD': 'GILD (吉利德科学)',
    'SPY': 'SPY (标普500基准)',
    'LLY': 'LLY (礼来制药)',
    'NVO': 'NVO (诺和诺德)'
}

# ========== 新增：对话处理函数 ==========
def get_ai_response(messages, client):
    """调用 DeepSeek API 获取回答"""
    try:
        response = client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ 获取回答时出错: {str(e)}"

def display_chat_history():
    """显示对话历史"""
    if st.session_state.chat_history:
        st.markdown('<div class="chat-divider"></div>', unsafe_allow_html=True)
        st.markdown("### 💬 Chat History")
        
        for msg in st.session_state.chat_history:
            if msg['role'] == 'user':
                st.markdown(f'''
                <div class="chat-message user">
                    <div class="chat-header">👤 Your Question</div>
                    <div>{msg['content']}</div>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
                <div class="chat-message assistant">
                    <div class="chat-header">🤖 AI Response</div>
                    <div>{msg['content']}</div>
                </div>
                ''', unsafe_allow_html=True)


def handle_user_question(question, selected_tickers, client):
    """处理用户问题"""
    # ========== 防止重复添加相同问题 ==========
    if st.session_state.chat_history and \
       st.session_state.chat_history[-1]['role'] == 'user' and \
       st.session_state.chat_history[-1]['content'] == question:
        return  # 如果最后一条就是这个问题，直接返回
    # 添加用户问题到历史
    st.session_state.chat_history.append({
        "role": "user",
        "content": question
    })
    
    # 准备上下文消息
    messages = [
        {
            "role": "system",
            "content": f"""You are a professional biotech investment analyst.
Currently analyzing: {', '.join(selected_tickers)}
Please answer based on the previous analysis and latest data.
Be professional, objective, and insightful."""
        }
    ]
    
    # 添加分析上下文（如果有）
    if st.session_state.analysis_context:
        messages.append({
            "role": "assistant",
            "content": f"Previous analysis summary: {st.session_state.analysis_context[:1000]}..."
        })
    
    # 添加最近的对话历史（最多5轮）
    recent_history = st.session_state.chat_history[-6:]
    for msg in recent_history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # 获取 AI 回答
    with st.spinner("🤔 AI is thinking..."):
        answer = get_ai_response(messages, client)
    
    # 添加 AI 回答到历史
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": answer
    })


def add_chat_interface(selected_tickers, client):
    """添加对话界面"""
    st.markdown("---")
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.markdown("### 💬 继续追问 AI 分析师")
    
    # 快速提问按钮
    st.markdown("**🚀 快速提问：**")
    col1, col2, col3, col4 = st.columns(4)
    
    quick_questions = {
        "📊 详细解释财务指标": "请详细解释这些公司的主要财务指标，包括市盈率、市净率、ROE等的含义和投资意义。",
        "🔬 分析研发管线": "请分析这些公司的研发管线和在研药物情况，哪些最有潜力？",
        "⚠️ 评估投资风险": "这些公司的主要投资风险有哪些？市场、监管、竞争等方面？",
        "📈 预测未来趋势": "基于当前数据，预测这些公司未来6-12个月的发展趋势。"
    }
    
    cols = [col1, col2, col3, col4]
    for idx, (btn_text, question) in enumerate(quick_questions.items()):
        with cols[idx]:
            if st.button(btn_text, key=f"quick_q_{idx}", use_container_width=True):
                handle_user_question(question, selected_tickers, client)
                st.rerun()
    
    # 显示对话历史
    display_chat_history()
    
    # 自定义问题输入
    st.markdown("---")
    st.markdown("**✍️ 或输入你的问题：**")
    user_input = st.chat_input("例如：这些公司中哪个最值得长期持有？")
    
    if user_input:
        handle_user_question(user_input, selected_tickers, client)
        st.rerun()
    
    # 清空对话按钮
    if st.session_state.chat_history:
        col_clear1, col_clear2, col_clear3 = st.columns([1, 1, 1])
        with col_clear2:
            if st.button("🗑️ 清空对话历史", key="clear_chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
# ==========================================
TIME_RANGE_MAP = {
    "3mo": "Last 3 Months",
    "6mo": "Last 6 Months", 
    "1y": "Last 1 Year",
    "3y": "Last 3 Years",
    "5y": "Last 5 Years"
}

# --- Session State 初始化 ---
if 'price_alerts' not in st.session_state:
    st.session_state.price_alerts = []
if 'favorite_tickers' not in st.session_state:
    st.session_state.favorite_tickers = []
if 'ai_report' not in st.session_state:
    st.session_state.ai_report = ""
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

if 'analysis_started' not in st.session_state:
    st.session_state.analysis_started = False
if 'selected_tickers' not in st.session_state:
    st.session_state.selected_tickers = []
if 'selected_time_range' not in st.session_state:
    st.session_state.selected_time_range = '1y'
if 'custom_tickers' not in st.session_state:
    st.session_state.custom_tickers = []
if 'preset_tickers' not in st.session_state:
    st.session_state.preset_tickers = []


# --- 工具函数 ---
@st.cache_data(ttl=3600)
def validate_and_get_name(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if 'symbol' not in info or info.get('regularMarketPrice') is None:
            return False, None
        
        name = info.get('longName') or info.get('shortName') or ticker
        return True, name
    except:
        return False, None

import requests
from typing import List, Dict
import difflib
from pypinyin import lazy_pinyin
from deep_translator import GoogleTranslator


# ========== 核心搜索引擎 ==========
@st.cache_data(ttl=3600)
def smart_search_ticker(query: str) -> List[Dict]:
    """
    多源智能搜索引擎
    支持：中文、英文、拼音、模糊匹配
    """
    results = []
    original_query = query.strip()
    query_lower = original_query.lower()
    
    # ========== 第一步：检测语言并转换 ==========
    search_queries = [original_query]  # 原始查询
    
    # 如果包含中文，尝试翻译
    if any('\u4e00' <= char <= '\u9fff' for char in original_query):
        try:
            # 方法1：Google 翻译
            translated_text = GoogleTranslator(source='zh-CN', target='en').translate(original_query)
            if translated_text:
                search_queries.append(translated_text)
                st.info(f"Automatic Translation：'{original_query}' → '{translated_text}'")
        except:
            pass

        
        # 方法2：拼音转换（作为备用）
        pinyin_query = ''.join(lazy_pinyin(original_query))
        if pinyin_query != original_query:
            search_queries.append(pinyin_query)
    
    # 如果是拼音，尝试常见映射
    elif query_lower.isalpha() and len(query_lower) > 3:
        # 快速映射常见公司（保留少量高频词）
        quick_map = {
            'huirui': 'Pfizer',
            'hengrui': 'Jiangsu Hengrui',
            'sansheng': 'Sunshine Guojian',  # 三生制药
            'sanshengzhiyao': 'Sunshine Guojian',
            'modena': 'Moderna',
            'jilide': 'Gilead',
        }
        if query_lower in quick_map:
            search_queries.append(quick_map[query_lower])
    
    # ========== 第二步：多源搜索 ==========
    for search_term in search_queries:
        # 来源1：Yahoo Finance 主搜索
        yahoo_results = search_yahoo_finance(search_term)
        results.extend(yahoo_results)
        
        # 来源2：直接 Ticker 查询
        direct_result = search_direct_ticker(search_term)
        if direct_result:
            results.append(direct_result)
        
        # 来源3：A股/港股特殊处理
        if any('\u4e00' <= char <= '\u9fff' for char in original_query):
            cn_results = search_chinese_stocks(original_query)
            results.extend(cn_results)
    
    # ========== 第三步：去重与排序 ==========
    # 去重（基于 symbol）
    seen = set()
    unique_results = []
    for r in results:
        if r['symbol'] not in seen:
            seen.add(r['symbol'])
            unique_results.append(r)
    
    # 排序：主要市场优先
    priority_exchanges = ['NASDAQ', 'NYSE', 'SSE', 'SZSE', 'HKEX', 'SHH', 'HKG']
    unique_results.sort(key=lambda x: (
        0 if x['exchange'] in priority_exchanges else 1,
        -len(x['name'])  # 名称越长越详细，优先级越高
    ))
    
    # 过滤多地上市重复（只保留主要市场）
    filtered = []
    seen_names = set()
    for r in unique_results:
        base_name = r['name'].split('(')[0].split('-')[0].strip().lower()
        # 如果是主要市场或者名称未见过，则保留
        if r['exchange'] in priority_exchanges[:5] or base_name not in seen_names:
            filtered.append(r)
            seen_names.add(base_name)
    
    return filtered[:8]  # 最多返回8个结果


# ========== 辅助函数1：Yahoo Finance 搜索 ==========
def search_yahoo_finance(query: str) -> List[Dict]:
    """Yahoo Finance API 搜索"""
    results = []
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {
            'q': query,
            'quotesCount': 10,
            'newsCount': 0,
            'enableFuzzyQuery': True,
            'quotesQueryId': 'tss_match_phrase_query'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            quotes = data.get('quotes', [])
            
            for quote in quotes:
                if quote.get('quoteType') in ['EQUITY', 'ETF']:
                    results.append({
                        'symbol': quote.get('symbol', ''),
                        'name': quote.get('longname') or quote.get('shortname', ''),
                        'exchange': quote.get('exchange', 'N/A'),
                        'type': quote.get('quoteType', 'Stock')
                    })
    except:
        pass
    
    return results


# ========== 辅助函数2：直接 Ticker 查询 ==========
def search_direct_ticker(query: str) -> Dict:
    """尝试直接作为股票代码查询"""
    try:
        ticker = yf.Ticker(query.upper())
        info = ticker.info
        
        if 'symbol' in info and info.get('regularMarketPrice'):
            return {
                'symbol': info['symbol'],
                'name': info.get('longName', info.get('shortName', query)),
                'exchange': info.get('exchange', 'N/A'),
                'type': info.get('quoteType', 'Stock')
            }
    except:
        pass
    
    return None


# ========== 辅助函数3：中文股票特殊搜索 ==========
def search_chinese_stocks(query: str) -> List[Dict]:
    """
    针对A股/港股的特殊搜索
    使用东方财富/新浪财经 API
    """
    results = []
    
    # 方法1：东方财富搜索 API
    try:
        url = "https://searchapi.eastmoney.com/api/suggest/get"
        params = {
            'input': query,
            'type': '14',  # 14=股票
            'token': 'D43BF722C8E33BDC906FB84D85E326E8',
            'count': 5
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('QuotationCodeTable', {}).get('Data'):
                for item in data['QuotationCodeTable']['Data']:
                    code = item.get('Code', '')
                    name = item.get('Name', '')
                    market_code = item.get('MktNum', '')
                    
                    # 转换为 Yahoo Finance 格式
                    if market_code == '1':  # 上海
                        symbol = f"{code}.SS"
                        exchange = 'SSE'
                    elif market_code == '0':  # 深圳
                        symbol = f"{code}.SZ"
                        exchange = 'SZSE'
                    elif market_code == '116':  # 香港
                        symbol = f"{code}.HK"
                        exchange = 'HKEX'
                    else:
                        continue
                    
                    results.append({
                        'symbol': symbol,
                        'name': f"{name} ({code})",
                        'exchange': exchange,
                        'type': 'Stock'
                    })
    except:
        pass
    
    # 方法2：新浪财经搜索（备用）
    if not results:
        try:
            url = "https://suggest3.sinajs.cn/suggest/type=&key=" + query
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                # 解析新浪返回的数据格式
                content = response.text
                if 'var suggestvalue=' in content:
                    data_str = content.split('var suggestvalue="')[1].split('";')[0]
                    items = data_str.split(';')
                    
                    for item in items[:5]:
                        parts = item.split(',')
                        if len(parts) >= 6:
                            code = parts[3]
                            name = parts[4]
                            market = parts[0]
                            
                            if market == 'sh':
                                symbol = f"{code}.SS"
                                exchange = 'SSE'
                            elif market == 'sz':
                                symbol = f"{code}.SZ"
                                exchange = 'SZSE'
                            elif market == 'hk':
                                symbol = f"{code}.HK"
                                exchange = 'HKEX'
                            else:
                                continue
                            
                            results.append({
                                'symbol': symbol,
                                'name': f"{name} ({code})",
                                'exchange': exchange,
                                'type': 'Stock'
                            })
        except:
            pass
    
    return results


def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

def calculate_bollinger_bands(data, period=20, std_dev=2):
    sma = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return sma, upper_band, lower_band

@st.cache_data(ttl=300)
def get_data(user_tickers, period):
    target_tickers = list(set(user_tickers + ['SPY']))
    data = yf.download(target_tickers, period=period, auto_adjust=True, threads=False)
    
    if isinstance(data.columns, pd.MultiIndex):
        try:
            df_close = data['Close']
        except KeyError:
            df_close = data
    else:
        if 'Close' in data.columns:
            df_close = data['Close']
        else:
            df_close = data

    df_close = df_close.apply(pd.to_numeric, errors='coerce').dropna()
    
    if 'SPY' not in df_close.columns:
        return pd.DataFrame(), pd.DataFrame()

    returns = df_close.pct_change().dropna()
    return df_close, returns

# ========== 新增：获取公司信息和新闻 ==========
@st.cache_data(ttl=1800)  # 缓存30分钟
def get_company_info_and_news(ticker):
    """获取公司官网和最新新闻"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 获取官网
        website = info.get('website', '')
        company_name = info.get('longName', info.get('shortName', ticker))
        
        # 获取最新新闻（yfinance 内置）
        news = stock.news[:5] if hasattr(stock, 'news') and stock.news else []
        
        return {
            'name': company_name,
            'website': website,
            'news': news
        }
    except Exception as e:
        return {
            'name': ticker,
            'website': '',
            'news': []
        }

def search_google_news(company_name, ticker):
    """备用：Google News 搜索（如果 yfinance 新闻不足）"""
    try:
        from googlesearch import search
        query = f"{company_name} {ticker} stock news"
        results = []
        
        for url in search(query, num_results=5, lang='en'):
            # 过滤权威财经媒体
            if any(domain in url for domain in ['reuters.com', 'bloomberg.com', 'cnbc.com', 
                                                  'wsj.com', 'ft.com', 'marketwatch.com',
                                                  'seekingalpha.com', 'fool.com']):
                results.append(url)
                if len(results) >= 5:
                    break
        
        return results
    except:
        return []


def get_deepseek_analysis(metrics_df, period):
    api_key = DEEPSEEK_API_KEY
    if not api_key:
        return "Error: DEEPSEEK_API_KEY not found. Please check your .env file."
    
    base_url = "https://api.deepseek.com"

    client = OpenAI(api_key=api_key, base_url=base_url)
    
    data_csv = metrics_df.to_csv(index=False)
    
    # 获取当前日期
    current_date = datetime.now().strftime("%B %d, %Y")

    system_prompt = f"""
    You are a senior biotech equity analyst at a top-tier investment bank.
    Today's Date: {current_date}
    
    Generate a professional investment memo in ENGLISH.
    
    Structure:
    
    ### Sector Overview
    - Current biotech market sentiment (Risk-On vs Risk-Off)
    - Performance vs broader market (SPY)
    
    ### Key Findings
    - Top performers (best risk-adjusted returns)
    - Underperformers (high risk, low return)
    - Beta analysis (market correlation)
    
    ### Investment Strategy
    - Growth opportunity: One actionable idea
    - Risk management: One defensive position
    
    Use professional terminology. Be concise and data-driven.
    """
    
    user_prompt = f"Period: {period}\nData:\n{data_csv}"

    try:
        response = client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            temperature=0.5
        )
        return response
    except Exception as e:
        return f"Error: {str(e)}"

def check_price_alerts(prices):
    triggered_alerts = []
    
    for alert in st.session_state.price_alerts:
        ticker = alert['ticker']
        if ticker in prices.columns:
            current_price = prices[ticker].iloc[-1]
            target_price = alert['price']
            
            if alert['type'] == 'Above' and current_price > target_price:
                triggered_alerts.append({
                    'ticker': ticker,
                    'current': current_price,
                    'target': target_price,
                    'type': 'above'
                })
            elif alert['type'] == 'Below' and current_price < target_price:
                triggered_alerts.append({
                    'ticker': ticker,
                    'current': current_price,
                    'target': target_price,
                    'type': 'below'
                })
    
    return triggered_alerts

def create_pdf_report(metrics_df, ai_analysis, tickers, time_range):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#141413'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Times-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#4a7c59'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Times-Bold'
    )
    
    story.append(Paragraph("BioMarket Intelligence Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # 格式化当前时间
    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    report_info = f"""
    <b>Generated:</b> {current_time_str}<br/>
    <b>Period:</b> {TIME_RANGE_MAP.get(time_range, time_range)}<br/>
    <b>Tickers:</b> {', '.join(tickers)}<br/>
    <b>Analyst:</b> DeepSeek-V4 AI
    """
    story.append(Paragraph(report_info, styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("Performance Metrics", heading_style))
    
    table_data = [['Ticker', 'Name', 'Return(%)', 'Vol(%)', 'Beta']]
    for _, row in metrics_df.iterrows():
        # --- 修复黑框问题：过滤掉中文和非ASCII字符 ---
        raw_name = row['Name']
        # 只保留英文字符、数字和常见标点
        clean_name = re.sub(r'[^\x00-\x7F]+', '', raw_name)
        # 清理可能剩下的空括号，例如 "AMGN ()" -> "AMGN"
        clean_name = clean_name.replace('()', '').strip()
        
        table_data.append([
            row['Ticker Code'],
            clean_name[:30], # 截取过长的名字
            f"{row['Total Return (%)']:.2f}",
            f"{row['Volatility (%)']:.2f}",
            f"{row['Beta']:.2f}"
        ])
    
    table = Table(table_data, colWidths=[0.8*inch, 2.5*inch, 1.2*inch, 1.2*inch, 0.8*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a7c59')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#faf9f5')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#faf9f5')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e8e6dc')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(PageBreak())
    story.append(Paragraph("AI Analysis", heading_style))
    
    analysis_lines = ai_analysis.split('\n')
    for line in analysis_lines:
        if line.strip():
            if line.startswith('###'):
                # --- 修复标题问题：同时去除 ### 和 ** ---
                clean_title = line.replace('###', '').replace('**', '').strip()
                story.append(Paragraph(clean_title, heading_style))
            else:
                # 使用正则修复正文中的粗体：将成对的 **text** 替换为 <b>text</b>
                formatted_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                # 移除剩余的单个 * 号
                formatted_line = formatted_line.replace('*', '')
                try:
                    story.append(Paragraph(formatted_line, styles['Normal']))
                except:
                    story.append(Paragraph(line.replace('*', ''), styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
    
    story.append(Spacer(1, 0.3*inch))
    disclaimer = """
    <b>Disclaimer:</b> AI-generated report for informational purposes only. 
    Not investment advice. Consult a financial advisor before making decisions.
    """
    story.append(Paragraph(disclaimer, styles['Italic']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


# 自定义颜色映射函数（Anthropic 暖色调版本）
def color_return(val):
    """根据回报率返回暖色调颜色"""
    try:
        val = float(val)
        if val > 20:
            return 'background-color: #3d6b4e; color: #faf9f5; font-weight: 500'
        elif val > 10:
            return 'background-color: #5d8f6e; color: #faf9f5'
        elif val > 0:
            return 'background-color: #a8c8a0; color: #2d4d38'
        elif val > -10:
            return 'background-color: #e8d5b0; color: #6b5a2e'
        elif val > -20:
            return 'background-color: #d4a08a; color: #faf9f5'
        else:
            return 'background-color: #b53333; color: #faf9f5; font-weight: 500'
    except:
        return ''

# ==================== 主界面 ====================

# ---- 品牌 Header ----
now = datetime.now()
hour = now.hour
is_market_open = (
    (hour == 21 and now.minute >= 30) or
    (hour >= 22) or
    (hour < 4)
)
market_status   = "Market Open"  if is_market_open else "Market Closed"
market_dot_cls  = "live-dot"     if is_market_open else ""
market_dot_style = (
    "display:inline-block;width:7px;height:7px;border-radius:50%;"
    "background:#4a7c59;animation:pulse 2.2s infinite;margin-right:5px;vertical-align:middle;"
) if is_market_open else (
    "display:inline-block;width:7px;height:7px;border-radius:50%;"
    "background:#87867f;margin-right:5px;vertical-align:middle;"
)
current_time = now.strftime("%I:%M %p")
current_date = now.strftime("%b %d, %Y")

st.markdown(f"""
<div class="brand-header">
    <p class="brand-title">BioMarket Tracker</p>
    <p class="brand-sub">Professional Biotech Market Intelligence Platform</p>
    <span class="brand-badge">⬡ DeepSeek-V4 · Yahoo Finance</span>
</div>
""", unsafe_allow_html=True)

# ---- 控制栏 ----
col_status, col_refresh, col_new = st.columns([2.5, 1, 1], gap="small")

with col_status:
    st.markdown(
        f'<div style="padding:9px 16px;background:#faf9f5;border-radius:9px;'
        f'box-shadow:0 0 0 0.5px #e8e6dc;font-family:Inter,system-ui,sans-serif;'
        f'font-size:0.86rem;color:#4d4c48;display:flex;align-items:center;gap:10px;">'
        f'<span><span style="{market_dot_style}"></span>'
        f'<b style="color:#141413;">{market_status}</b></span>'
        f'<span style="color:#d1cfc5;">|</span>'
        f'<span style="color:#87867f;">Updated <b style="color:#141413;">{current_time}</b></span>'
        f'<span style="color:#d1cfc5;">|</span>'
        f'<span style="color:#87867f;">{current_date}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

with col_refresh:
    if st.button("↺ Refresh", use_container_width=True, key="refresh_btn"):
        st.session_state.analysis_started = True
        st.session_state.is_refreshing = True
        st.session_state._saved_tickers = st.session_state.selected_tickers.copy()
        st.session_state._saved_time_range = st.session_state.selected_time_range
        st.session_state._saved_custom = st.session_state.custom_tickers.copy()
        st.session_state._saved_preset = st.session_state.preset_tickers.copy()
        get_data.clear()
        st.session_state.last_update = datetime.now()
        st.rerun()

with col_new:
    if st.button("+ New Analysis", use_container_width=True):
        st.session_state.analysis_completed = False
        st.session_state.analyzed_tickers = []
        st.session_state.chat_history = []
        st.cache_data.clear()
        st.rerun()

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("### Control Panel")
    
    tab1, tab2, tab3 = st.tabs(["Selection", "Alerts", "Favorites"])   
    with tab1:
        st.markdown("**Smart Search**")
        st.caption("Search by company name or ticker symbol")
        
        # 搜索输入框
        search_query = st.text_input(
            "Search stocks",
            placeholder="e.g., Hengrui, Pfizer, 恒瑞医药, MRNA",
            label_visibility="collapsed",
            key="search_input"
        )
        
        # 搜索结果容器
        if search_query and len(search_query) >= 2:
            with st.spinner('Searching...'):
                search_results = smart_search_ticker(search_query)
                
                if search_results:
                    st.success(f"Found {len(search_results)} results:")
                    
                    # 显示搜索结果（可选择）
                    for result in search_results[:5]:  # 最多显示5个结果
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.caption(f"**{result['symbol']}** - {result['name']}")
                            st.caption(f" {result['exchange']} | {result['type']}")
                        with col2:
                            if st.button("Add", key=f"add_{result['symbol']}", use_container_width=True):
                                # 添加到自定义列表
                                if result['symbol'] not in st.session_state.custom_tickers:
                                    st.session_state.custom_tickers.append(result['symbol'])
                                    TICKER_MAP[result['symbol']] = f"{result['symbol']} ({result['name']})"
                                    st.success(f"Added {result['symbol']}")
                                    st.rerun()
                else:
                    st.warning("No results found. Try different keywords.")

        
        st.markdown("---")
        
        st.markdown("**Popular Biotech**")
        available_tickers = [t for t in TICKER_MAP.keys() if t != 'SPY']
        
        preset_tickers = st.multiselect(
            "Quick select",
            options=available_tickers,
            default=[], 
            format_func=lambda x: TICKER_MAP.get(x, x),
            placeholder="Choose from list...",
            label_visibility="collapsed",
            key="preset_select"
        )
        
        st.session_state.preset_tickers = preset_tickers
        
        if not st.session_state.get('is_refreshing', False):
           all_tickers = list(set(st.session_state.custom_tickers + st.session_state.preset_tickers))
           st.session_state.selected_tickers = all_tickers
        else:
           # 刷新时使用已保存的 tickers
           all_tickers = st.session_state.get('selected_tickers', [])
        
        if all_tickers:
            st.markdown("---")
            st.markdown("**Current Selection**")
            st.info(f"Total: **{len(all_tickers)}** stocks")
            
            if st.session_state.custom_tickers:
                st.caption("Custom:")
                for ticker in st.session_state.custom_tickers:
                    st.markdown(f'<span class="ticker-tag custom">{ticker}</span>', unsafe_allow_html=True)
            
            if st.session_state.preset_tickers:
                st.caption("Preset:")
                for ticker in st.session_state.preset_tickers:
                    st.markdown(f'<span class="ticker-tag">{ticker}</span>', unsafe_allow_html=True)
            
            if st.button("Save to Favorites", use_container_width=True):
                st.session_state.favorite_tickers = all_tickers
                st.success("Saved!")
            
            if st.button("Clear All", use_container_width=True):
                st.session_state.custom_tickers = []
                st.session_state.preset_tickers = []
                st.session_state.selected_tickers = []
                st.rerun()
        
        st.markdown("---")
        
        st.markdown("**Time Period**")
        time_range = st.selectbox(
            "Analysis period",
            ["3mo", "6mo", "1y", "3y", "5y"],
            format_func=lambda x: TIME_RANGE_MAP.get(x, x),
            index=2,
            label_visibility="collapsed"
        )
        st.session_state.selected_time_range = time_range
    
    with tab2:
        st.markdown("**Price Alerts**")
        st.caption("Get notified when price targets are hit")
        
        if st.session_state.selected_tickers:
            alert_ticker = st.selectbox("Stock", st.session_state.selected_tickers, format_func=lambda x: TICKER_MAP.get(x, x))
            
            col1, col2 = st.columns(2)
            with col1:
                alert_price = st.number_input("Target ($)", min_value=0.01, value=100.0, step=1.0)
            with col2:
                alert_type = st.selectbox("Type", ["Above", "Below"])
            
            if st.button("Add Alert", use_container_width=True, type="primary"):
                alert = {
                    'ticker': alert_ticker,
                    'price': alert_price,
                    'type': alert_type,
                    'created': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                st.session_state.price_alerts.append(alert)
                st.success(f"Alert set for {alert_ticker}")
            
            if st.session_state.price_alerts:
                st.markdown("---")
                st.markdown("**Active Alerts**")
                for idx, alert in enumerate(st.session_state.price_alerts):
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.caption(f"{alert['ticker']} {alert['type']} ${alert['price']:.2f}")
                        with col2:
                            if st.button("×", key=f"del_{idx}", use_container_width=True):
                                st.session_state.price_alerts.pop(idx)
                                st.rerun()
        else:
            st.info("Select stocks first")
    
    with tab3:
        st.markdown("**Saved Lists**")
        
        if st.session_state.favorite_tickers:
            st.success(f"{len(st.session_state.favorite_tickers)} stocks saved")
            
            for ticker in st.session_state.favorite_tickers:
                st.caption(f"• {TICKER_MAP.get(ticker, ticker)}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Load Favorites", use_container_width=True):
                    st.session_state.preset_tickers = st.session_state.favorite_tickers
                    st.success("Loaded! Check Selection tab")
                    st.rerun()
            with col2:
                if st.button("Clear", use_container_width=True):
                    st.session_state.favorite_tickers = []
                    st.success("Cleared")
                    st.rerun()
        else:
            st.info("No favorites saved")
    
    st.markdown("---")
    st.caption("Data: Yahoo Finance")
    st.caption("AI: DeepSeek-V4")
    st.caption("Dev: Runze Zhu")


# ==================== 主内容区 ====================
# ========== 优先检查 analysis_started 状态 ==========
should_show_analysis = (
    (st.session_state.get('analysis_started', False) or 
     st.session_state.get('is_refreshing', False)) and  
    len(st.session_state.get('selected_tickers', [])) > 0
)

if should_show_analysis:
    # ========== 显示分析结果 ==========
    tickers = st.session_state.selected_tickers
    time_range = st.session_state.selected_time_range

    with st.spinner('Loading market data...'):
        try:
            prices, returns = get_data(tickers, time_range)
            st.session_state.last_update = datetime.now()
            
            # 重置刷新标志，但保持 analysis_started
            st.session_state.is_refreshing = False
            st.session_state.analysis_started = True # 确保分析状态保持为 True
            
            if not prices.empty:
                triggered = check_price_alerts(prices)
                if triggered:
                    for alert in triggered:
                        type_text = "above" if alert['type'] == 'above' else "below"
                        st.markdown(
                            f'<div class="alert-card"><b>ALERT:</b> {alert["ticker"]} is now ${alert["current"]:.2f} '
                            f'({type_text} target ${alert["target"]:.2f})</div>',
                            unsafe_allow_html=True
                        )
                
                # ========== 增强版：公司情报板块 ==========
                st.markdown('<div class="section-title"> Company Intelligence & Latest News</div>', unsafe_allow_html=True)
                st.caption("Official websites and recent coverage from authoritative sources")

                for ticker in tickers:
                    with st.expander(f" {TICKER_MAP.get(ticker, ticker)}", expanded=False):
                        company_data = get_company_info_and_news(ticker)
        
                        col_left, col_right = st.columns([1, 1])
        
                        # 左侧：官方信息
                        with col_left:
                            st.markdown("####  Official Website")
                            if company_data['website']:
                                st.markdown(
                                    f'<div class="news-link-container">'
                                    f'<a href="{company_data["website"]}" target="_blank" class="news-link official-link">'
                                    f'{company_data["website"]}</a></div>',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.caption("_Not available_")
            
                            st.markdown("####  Market Data")
                            market_links = {
                                "Yahoo Finance": f"https://finance.yahoo.com/quote/{ticker}",
                                "MarketWatch": f"https://www.marketwatch.com/investing/stock/{ticker}"
                            }
                            for name, url in market_links.items():
                                st.markdown(
                                    f'<div class="news-link-container">'
                                    f'<a href="{url}" target="_blank" class="news-link official-link">{name} →</a>'
                                    f'</div>',
                                    unsafe_allow_html=True
                                )
                        # 右侧：新闻源
                        with col_right:
                            st.markdown("####  Latest News & Analysis")
                            news_sources = {
                                "Google News": f"https://news.google.com/search?q={company_data['name']}+{ticker}+stock",
                                "Yahoo Finance News": f"https://finance.yahoo.com/quote/{ticker}/news",
                                "Bloomberg": f"https://www.bloomberg.com/quote/{ticker}:US",
                                "MarketWatch": f"https://www.marketwatch.com/investing/stock/{ticker}",
                                "Seeking Alpha": f"https://seekingalpha.com/symbol/{ticker}/news"
                            }
                            for source, url in news_sources.items():
                                st.markdown(
                                    f'<div class="news-link-container">'
                                    f'<a href="{url}" target="_blank" class="news-link">{source} →</a>'
                                    f'</div>',
                                    unsafe_allow_html=True
                                )

                st.markdown("---")
# ========================================
    
                # ========================================

                st.markdown('<div class="section-title">Real-Time Prices</div>', unsafe_allow_html=True)
                
                cols = st.columns(min(len(tickers), 4))
                for idx, ticker in enumerate(tickers):
                    if ticker in prices.columns:
                        current_price = prices[ticker].iloc[-1]
                        price_change = ((prices[ticker].iloc[-1] / prices[ticker].iloc[0]) - 1) * 100
                        
                        with cols[idx % 4]:
                            change_color = "#4caf50" if price_change >= 0 else "#f44336"
                            arrow = "↑" if price_change >= 0 else "↓"
                            card_class = "positive" if price_change >= 0 else "negative"
                            
                            st.markdown(f"""
                            <div class="price-card {card_class}">
                                <div class="card-ticker">{TICKER_MAP.get(ticker, ticker)}</div>
                                <div class="card-price" style="color: {change_color};">${current_price:.2f}</div>
                                <div class="card-change" style="color: {change_color};">{arrow} {abs(price_change):.2f}%</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                st.markdown('<div class="section-title">Price Performance</div>', unsafe_allow_html=True)
                st.caption(f"Normalized to 100 at start | Period: {TIME_RANGE_MAP.get(time_range, time_range)}")
                
                mapped_columns = {col: TICKER_MAP.get(col, col) for col in prices.columns}
                normalized = prices / prices.iloc[0] * 100
                normalized_plot = normalized.rename(columns=mapped_columns)
                
                fig_perf = px.line(
                    normalized_plot, 
                    x=normalized_plot.index, 
                    y=normalized_plot.columns,
                    labels={'value': 'Indexed Price', 'variable': 'Ticker', 'Date': 'Date'}
                )
                
                spy_full_name = TICKER_MAP['SPY']
                fig_perf.update_traces(
                    patch={"line": {"color": "#8a7340", "width": 2.5, "dash": "dash"}}, 
                    selector={"name": spy_full_name}
                )
                fig_perf.update_traces(
                    patch={"line": {"width": 2.0}}, 
                    selector=lambda t: t.name != spy_full_name
                )
                fig_perf.update_layout(
                    hovermode='x unified',
                    plot_bgcolor='#faf9f5',
                    paper_bgcolor='#faf9f5',
                    font=dict(family="Inter, system-ui, sans-serif", size=11, color='#87867f'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                font=dict(size=10)),
                    height=450,
                    margin=dict(t=30, b=40, l=50, r=20),
                )
                fig_perf.update_xaxes(showgrid=False, showline=False, tickfont=dict(size=10))
                fig_perf.update_yaxes(showgrid=True, gridcolor='#f0eee6', gridwidth=0.5,
                                      zeroline=True, zerolinecolor='#d1cfc5', zerolinewidth=1,
                                      tickfont=dict(size=10))
                
                st.plotly_chart(fig_perf, use_container_width=True)
                
                st.markdown("---")
                
                st.markdown('<div class="section-title">Technical Analysis</div>', unsafe_allow_html=True)
                
                tech_ticker = st.selectbox(
                    "Select ticker for analysis", 
                    tickers, 
                    format_func=lambda x: TICKER_MAP.get(x, x),
                    key="tech_select"
                )
                
                if tech_ticker in prices.columns:
                    ticker_prices = prices[tech_ticker]
                    
                    rsi = calculate_rsi(ticker_prices)
                    macd, signal, histogram = calculate_macd(ticker_prices)
                    sma, upper_bb, lower_bb = calculate_bollinger_bands(ticker_prices)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(go.Scatter(
                            x=rsi.index, y=rsi,
                            name='RSI',
                            line=dict(color='#4a7c59', width=2.2)
                        ))
                        fig_rsi.add_hrect(y0=70, y1=100, fillcolor="#b53333", opacity=0.06, line_width=0)
                        fig_rsi.add_hrect(y0=0, y1=30, fillcolor="#4a7c59", opacity=0.06, line_width=0)
                        fig_rsi.add_hline(y=70, line_dash="dot", line_color="#b53333", line_width=1.2,
                                          annotation_text="Overbought", annotation_font_color="#b53333",
                                          annotation_font_size=10)
                        fig_rsi.add_hline(y=30, line_dash="dot", line_color="#4a7c59", line_width=1.2,
                                          annotation_text="Oversold", annotation_font_color="#4a7c59",
                                          annotation_font_size=10)
                        fig_rsi.update_layout(
                            title=dict(text=f"RSI — {TICKER_MAP.get(tech_ticker, tech_ticker)}",
                                       font=dict(family="Crimson Pro, Georgia, serif", size=15, color="#141413")),
                            yaxis_title="RSI",
                            height=320,
                            hovermode='x',
                            plot_bgcolor='#faf9f5',
                            paper_bgcolor='#faf9f5',
                            font=dict(family="Inter, system-ui, sans-serif", size=11, color='#87867f'),
                            showlegend=False,
                            margin=dict(t=45, b=30, l=45, r=20),
                        )
                        fig_rsi.update_xaxes(showgrid=False, showline=False, tickfont=dict(size=10))
                        fig_rsi.update_yaxes(showgrid=True, gridcolor='#f0eee6', gridwidth=0.5,
                                             zeroline=False, tickfont=dict(size=10))
                        st.plotly_chart(fig_rsi, use_container_width=True)
                        
                        current_rsi = rsi.iloc[-1]
                        if current_rsi > 70:
                            st.markdown(f'<span class="status-badge status-bearish">Overbought (RSI: {current_rsi:.1f})</span>', unsafe_allow_html=True)
                            st.caption("Market may be overheated")
                        elif current_rsi < 30:
                            st.markdown(f'<span class="status-badge status-bullish">Oversold (RSI: {current_rsi:.1f})</span>', unsafe_allow_html=True)
                            st.caption("Potential bounce opportunity")
                        else:
                            st.markdown(f'<span class="status-badge status-neutral">Neutral (RSI: {current_rsi:.1f})</span>', unsafe_allow_html=True)
                            st.caption("Normal trading range")
                    
                    with col2:
                        fig_macd = go.Figure()
                        fig_macd.add_trace(go.Scatter(
                            x=macd.index, y=macd,
                            name='MACD',
                            line=dict(color='#4a7c59', width=1.8)
                        ))
                        fig_macd.add_trace(go.Scatter(
                            x=signal.index, y=signal,
                            name='Signal',
                            line=dict(color='#b53333', width=1.8, dash='dash')
                        ))
                        # histogram: positive green, negative red
                        hist_colors = ['#4a7c59' if v >= 0 else '#b53333' for v in histogram]
                        fig_macd.add_trace(go.Bar(
                            x=histogram.index, y=histogram,
                            name='Histogram',
                            marker_color=hist_colors,
                            opacity=0.45
                        ))
                        fig_macd.update_layout(
                            title=dict(text=f"MACD — {TICKER_MAP.get(tech_ticker, tech_ticker)}",
                                       font=dict(family="Crimson Pro, Georgia, serif", size=15, color="#141413")),
                            yaxis_title="Value",
                            height=320,
                            hovermode='x',
                            plot_bgcolor='#faf9f5',
                            paper_bgcolor='#faf9f5',
                            font=dict(family="Inter, system-ui, sans-serif", size=11, color='#87867f'),
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5,
                                        font=dict(size=10)),
                            margin=dict(t=45, b=40, l=45, r=20),
                        )
                        fig_macd.update_xaxes(showgrid=False, showline=False, tickfont=dict(size=10))
                        fig_macd.update_yaxes(showgrid=True, gridcolor='#f0eee6', gridwidth=0.5,
                                              zeroline=True, zerolinecolor='#d1cfc5', zerolinewidth=1,
                                              tickfont=dict(size=10))
                        st.plotly_chart(fig_macd, use_container_width=True)
                        
                        if macd.iloc[-1] > signal.iloc[-1]:
                            st.markdown('<span class="status-badge status-bullish">Bullish Signal</span>', unsafe_allow_html=True)
                            st.caption("MACD crossed above signal line")
                        else:
                            st.markdown('<span class="status-badge status-bearish">Bearish Signal</span>', unsafe_allow_html=True)
                            st.caption("MACD crossed below signal line")
                    
                    fig_bb = go.Figure()
                    fig_bb.add_trace(go.Scatter(
                        x=upper_bb.index, y=upper_bb,
                        name='Upper Band',
                        line=dict(color='#b53333', width=0.8, dash='dot'),
                        fill=None
                    ))
                    fig_bb.add_trace(go.Scatter(
                        x=lower_bb.index, y=lower_bb,
                        name='Lower Band',
                        line=dict(color='#4a7c59', width=0.8, dash='dot'),
                        fill='tonexty',
                        fillcolor='rgba(74,124,89,0.055)'
                    ))
                    fig_bb.add_trace(go.Scatter(
                        x=sma.index, y=sma,
                        name='SMA(20)',
                        line=dict(color='#8a7340', width=1.4, dash='dash')
                    ))
                    fig_bb.add_trace(go.Scatter(
                        x=ticker_prices.index, y=ticker_prices,
                        name='Price',
                        line=dict(color='#141413', width=2.0)
                    ))
                    fig_bb.update_layout(
                        title=dict(text=f"Bollinger Bands — {TICKER_MAP.get(tech_ticker, tech_ticker)}",
                                   font=dict(family="Crimson Pro, Georgia, serif", size=15, color="#141413")),
                        yaxis_title="Price ($)",
                        height=380,
                        hovermode='x unified',
                        plot_bgcolor='#faf9f5',
                        paper_bgcolor='#faf9f5',
                        font=dict(family="Inter, system-ui, sans-serif", size=11, color='#87867f'),
                        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="center", x=0.5,
                                    font=dict(size=10)),
                        margin=dict(t=45, b=45, l=55, r=20),
                    )
                    fig_bb.update_xaxes(showgrid=False, showline=False, tickfont=dict(size=10))
                    fig_bb.update_yaxes(showgrid=True, gridcolor='#f0eee6', gridwidth=0.5,
                                        zeroline=False, tickfont=dict(size=10),
                                        tickprefix="$")
                    st.plotly_chart(fig_bb, use_container_width=True)
                
                st.markdown("---")
                
                st.markdown('<div class="section-title">Risk-Return Analysis</div>', unsafe_allow_html=True)
                
                summary = []
                spy_ret_series = returns['SPY']
                spy_total_return = (prices['SPY'].iloc[-1] / prices['SPY'].iloc[0] - 1) * 100
                spy_volatility = returns['SPY'].std() * (252**0.5) * 100
                
                for t in tickers:
                    if t in returns.columns:
                        cov = returns[t].cov(spy_ret_series)
                        var = spy_ret_series.var()
                        beta = cov / var if var != 0 else 0
                        
                        tot_ret = (prices[t].iloc[-1] / prices[t].iloc[0] - 1) * 100
                        vol = returns[t].std() * (252**0.5) * 100
                        sharpe = (tot_ret / vol) if vol != 0 else 0
                        
                        summary.append({
                            'Ticker Code': t,
                            'Name': TICKER_MAP.get(t, t),
                            'Total Return (%)': round(tot_ret, 2), 
                            'Volatility (%)': round(vol, 2), 
                            'Beta': round(beta, 2),
                            'Sharpe Ratio': round(sharpe, 2)
                        })
                
                metrics_df = pd.DataFrame(summary)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    metrics_df['Marker Size'] = np.abs(metrics_df['Sharpe Ratio']) * 10 + 5
                    
                    fig_scat = px.scatter(
                        metrics_df, 
                        x='Volatility (%)', 
                        y='Total Return (%)',
                        text='Ticker Code',
                        size='Marker Size',
                        color='Beta', 
                        color_continuous_scale=[[0, '#4a7c59'], [0.5, '#e8d5b0'], [1, '#b53333']],
                        title="Risk-Return Frontier"
                    )
                    
                    fig_scat.update_traces(
                        textposition='top center',
                        textfont=dict(size=11, color='#141413'),
                        marker=dict(line=dict(width=1.5, color='#faf9f5'))
                    )
                    fig_scat.add_vline(
                        x=spy_volatility, 
                        line_dash="dash", 
                        line_color="#8a7340", 
                        annotation_text="Market Risk",
                        annotation_position="top"
                    )
                    fig_scat.add_hline(
                        y=spy_total_return, 
                        line_dash="dash", 
                        line_color="#8a7340", 
                        annotation_text="Market Return",
                        annotation_position="right"
                    )
                    fig_scat.update_layout(
                        height=480,
                        hovermode='closest',
                        plot_bgcolor='#faf9f5',
                        paper_bgcolor='#faf9f5',
                        font=dict(family="Inter, system-ui, sans-serif", size=11, color='#87867f'),
                        showlegend=True,
                        margin=dict(t=40, b=50, l=55, r=20),
                        coloraxis_colorbar=dict(
                            title="Beta",
                            tickfont=dict(size=10),
                            title_font=dict(size=11),
                            len=0.7,
                        )
                    )
                    fig_scat.update_xaxes(showgrid=True, gridcolor='#f0eee6', gridwidth=0.5,
                                          zeroline=False, tickfont=dict(size=10))
                    fig_scat.update_yaxes(showgrid=True, gridcolor='#f0eee6', gridwidth=0.5,
                                          zeroline=True, zerolinecolor='#d1cfc5', zerolinewidth=1,
                                          tickfont=dict(size=10))
                    st.plotly_chart(fig_scat, use_container_width=True)
                
                with col2:
                    st.markdown("**Key Metrics**")
                    display_df = metrics_df[['Name', 'Total Return (%)', 'Volatility (%)', 'Beta', 'Sharpe Ratio']].copy()
                    display_df.columns = ['Name', 'Return(%)', 'Vol(%)', 'Beta', 'Sharpe']
                    display_df = display_df.set_index('Name')
                    
                    styled_df = display_df.style.format("{:.2f}").map(
                        color_return, 
                        subset=['Return(%)']
                    )
                    
                    st.dataframe(
                        styled_df,
                        use_container_width=True,
                        height=400
                    )
                
                st.markdown("---")
                
                st.markdown('<div class="section-title">AI Investment Analysis</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.info("Generate professional investment memo based on current market data")
                
                with col2:
                    generate_btn = st.button("Generate Report", type="primary", use_container_width=True)
                
                if generate_btn:
                    with st.status("AI analyst working...", expanded=True) as status:
                        st.write("Analyzing market data...")
                        st.write("Calculating risk metrics...")
                        st.write("Drafting recommendations...")
                        
                        response_placeholder = st.empty()
                        full_response = ""
                        
                        stream = get_deepseek_analysis(metrics_df, time_range)
                        
                        if isinstance(stream, str):
                            status.update(label="Connection error", state="error")
                            st.error(stream)
                        else:
                            for chunk in stream:
                                if chunk.choices[0].delta.content:
                                    content = chunk.choices[0].delta.content
                                    full_response += content
                                    response_placeholder.markdown(full_response + "▌")
                            
                            response_placeholder.markdown(full_response)
                            st.session_state.ai_report = full_response
                            st.session_state.analysis_completed = True
                            st.session_state.analyzed_tickers = tickers.copy()
                            st.session_state.analysis_context = full_response
                            status.update(label="✅ Analysis completed!", state="complete")
                
                if st.session_state.ai_report:
                    st.markdown("---")
                    
                    st.markdown('<div class="section-title">Export Options</div>', unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.caption("Save your analysis")
                    
                    with col2:
                        if st.button("Generate PDF", type="secondary", use_container_width=True):
                            with st.spinner("Creating PDF..."):
                                pdf_buffer = create_pdf_report(
                                    metrics_df, 
                                    st.session_state.ai_report, 
                                    tickers, 
                                    time_range
                                )
                                
                                st.download_button(
                                    label="Download PDF",
                                    data=pdf_buffer,
                                    file_name=f"BioMarket_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                                st.success("PDF ready!")
                    
                    with col3:
                        csv = metrics_df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="Export CSV",
                            data=csv,
                            file_name=f"metrics_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

        except Exception as e:
            st.error(f"Error: {e}")
            st.warning("Please try refreshing the page")

elif len(st.session_state.selected_tickers) > 0 and not st.session_state.analysis_started:
    # ========== 显示 Start Analysis 按钮 ==========
    st.markdown("---")
    
    custom_list = ', '.join([TICKER_MAP.get(t, t) for t in st.session_state.custom_tickers]) if st.session_state.custom_tickers else "None"
    preset_list = ', '.join([TICKER_MAP.get(t, t) for t in st.session_state.preset_tickers]) if st.session_state.preset_tickers else "None"
    
    st.markdown(f"""
    <div class="selection-summary">
        <h3>Analysis Configuration</h3>
        <p style="margin:0.4rem 0;"><b>Total Selected:</b> {len(st.session_state.selected_tickers)} stocks</p>
        <p style="margin:0.4rem 0;">
            <b>Custom:</b> {custom_list}<br/>
            <b>Preset:</b> {preset_list}
        </p>
        <p style="margin:0.4rem 0;"><b>Time Period:</b> {TIME_RANGE_MAP.get(st.session_state.selected_time_range, st.session_state.selected_time_range)}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Start Analysis", type="primary", use_container_width=True, key="start_analysis"):
            st.session_state.analysis_started = True
            st.rerun()


else:
    st.markdown("---")

    # ---- Welcome 标题 ----
    st.markdown("""
    <div style="text-align:center;padding:1.5rem 0 1rem;">
        <p style="font-family:'Crimson Pro','Georgia',serif;font-size:2rem;font-weight:500;
                  color:#141413;margin:0 0 0.4rem;">Welcome to BioMarket Tracker</p>
        <p style="font-family:'Inter',system-ui,sans-serif;font-size:0.92rem;color:#87867f;margin:0;">
            Select stocks from the sidebar to begin your analysis
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ---- 三列功能卡片 ----
    wc1, wc2, wc3 = st.columns(3, gap="medium")

    with wc1:
        st.markdown("""
        <div class="welcome-card welcome-card-accent">
            <p style="font-size:1.5rem;margin:0 0 0.5rem;">🧬</p>
            <h4>Getting Started</h4>
            <ol style="padding-left:1.1rem;margin:0;color:#87867f;font-size:0.82rem;line-height:1.7;">
                <li>Open the sidebar on the left</li>
                <li>Search by name or ticker symbol</li>
                <li>Or pick from the preset biotech list</li>
                <li>Choose your time period</li>
                <li>Click <b style="color:#4a7c59;">Start Analysis</b></li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    with wc2:
        st.markdown("""
        <div class="welcome-card welcome-card-gold">
            <p style="font-size:1.5rem;margin:0 0 0.5rem;">📊</p>
            <h4>Analytics Suite</h4>
            <ul style="padding-left:1.1rem;margin:0;color:#87867f;font-size:0.82rem;line-height:1.7;">
                <li>Normalized price performance chart</li>
                <li>RSI · MACD · Bollinger Bands</li>
                <li>Risk-Return frontier (Beta, Sharpe)</li>
                <li>Smart price alerts</li>
                <li>Favorites & watchlist management</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with wc3:
        st.markdown("""
        <div class="welcome-card welcome-card-blue">
            <p style="font-size:1.5rem;margin:0 0 0.5rem;">🤖</p>
            <h4>AI Investment Analyst</h4>
            <p style="color:#87867f;font-size:0.82rem;line-height:1.6;margin:0;">
                Powered by <b style="color:#141413;">DeepSeek-V4</b>. After running analysis,
                generate a professional investment memo — sector overview, key findings,
                risk-adjusted rankings — then ask follow-up questions on pipeline, valuation,
                and macro catalysts. Export to PDF.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="disclaimer">
        For educational and research purposes only — not investment advice.
        Consult a qualified financial advisor before making investment decisions.
    </div>
    """, unsafe_allow_html=True)

# ========== AI 对话功能（只在分析完成后显示）==========
# 只有在分析完成后才显示对话界面
if st.session_state.get('analysis_completed', False):
    st.markdown("---")
    st.markdown('<div class="section-title">💬 Continue Discussion with AI Analyst</div>', unsafe_allow_html=True)
    
    try:
        # 获取已分析的股票
        analyzed_tickers = st.session_state.get('analyzed_tickers', [])
        
        if analyzed_tickers and len(analyzed_tickers) > 0:
            # 初始化客户端
            chat_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)
            
            # 快速提问按钮
            st.markdown("**🚀 Quick Questions:**")
            col1, col2, col3, col4 = st.columns(4)

            quick_questions = {
            "📊 Financial Metrics": f"Analyze key financial metrics of {', '.join(analyzed_tickers)} in detail.",
            "🔬 R&D Pipeline": f"Evaluate the R&D pipeline and clinical trials of {', '.join(analyzed_tickers)}.",
            "⚠️ Investment Risks": f"What are the main investment risks for {', '.join(analyzed_tickers)}?",
            "📈 Future Trends": f"Predict market trends for {', '.join(analyzed_tickers)} in next 6-12 months."
            }

            cols = [col1, col2, col3, col4]
            for idx, (btn_text, question) in enumerate(quick_questions.items()):
                with cols[idx]:
                    if st.button(btn_text, key=f"quick_q_{idx}", use_container_width=True):
                        # --- 新增：点击快速提问时，清空之前的历史，只显示当前结果 ---
                        st.session_state.chat_history = [] 
                        with st.spinner("🤖 AI is thinking..."):
                            handle_user_question(question, analyzed_tickers, chat_client)
                        st.rerun()


            
            # 显示对话历史
            if st.session_state.chat_history:
                st.markdown('<div class="chat-divider"></div>', unsafe_allow_html=True)
                st.markdown("### 💬 Chat History")
                
                for msg in st.session_state.chat_history:
                    if msg['role'] == 'user':
                        st.markdown(f'''
                        <div class="chat-message user">
                            <div class="chat-header">👤 Your Question</div>
                            <div>{msg['content']}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    else:
                        st.markdown(f'''
                        <div class="chat-message assistant">
                            <div class="chat-header">🤖 AI Response</div>
                            <div>{msg['content']}</div>
                        </div>
                        ''', unsafe_allow_html=True)
            
            # 自定义问题输入
            st.markdown("---")
            st.markdown("**✍️ Or ask your own question:**")
            user_input = st.chat_input("e.g., Which company has the strongest pipeline?")
            
            if user_input:
                with st.spinner("🤖 AI is thinking..."):
                    handle_user_question(user_input, analyzed_tickers, chat_client)
                st.rerun()
            
            # 清空对话按钮
            if st.session_state.chat_history:
                col_clear1, col_clear2, col_clear3 = st.columns([1, 1, 1])
                with col_clear2:
                    if st.button("🗑️ Clear Chat History", key="clear_chat", use_container_width=True):
                        st.session_state.chat_history = []
                        st.rerun()
                        
    except Exception as e:
        st.error(f"Chat feature error: {str(e)}")
# ====================================================
