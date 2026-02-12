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

# --- 自定义 CSS 样式 ---
st.markdown("""
<style>
    :root {
        --primary-color: #1e88e5;
        --secondary-color: #43a047;
        --accent-color: #ff6f00;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .main-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.3rem;
        letter-spacing: -0.5px;
    }
    
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    .price-card {
        background: white;
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    
    .price-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }
    
    .price-card.positive {
        border-left-color: #4caf50;
    }
    
    .price-card.negative {
        border-left-color: #f44336;
    }
    
    .card-ticker {
        font-size: 0.85rem;
        color: #666;
        font-weight: 600;
        margin-bottom: 0.3rem;
    }
    
    .card-price {
        font-size: 1.8rem;
        font-weight: bold;
        margin: 0.3rem 0;
    }
    
    .card-change {
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    
    .status-bullish {
        background: #e8f5e9;
        color: #2e7d32;
        border: 1px solid #4caf50;
    }
    
    .status-bearish {
        background: #ffebee;
        color: #c62828;
        border: 1px solid #f44336;
    }
    
    .status-neutral {
        background: #fff3e0;
        color: #e65100;
        border: 1px solid #ff9800;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .live-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #4caf50;
        border-radius: 50%;
        animation: pulse 2s infinite;
        margin-right: 6px;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    
    .alert-card {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
        padding: 1rem 1.2rem;
        border-radius: 8px;
        color: white;
        margin: 0.5rem 0;
        font-weight: 500;
    }
    
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 1px solid #e0e0e0;
    }
    
    .dataframe {
        font-size: 0.9rem;
    }
    
    .section-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #333;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #667eea;
    }
    
    .analyze-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 2rem;
        border-radius: 10px;
        font-size: 1.1rem;
        font-weight: 700;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .analyze-button:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    .selection-summary {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #667eea;
        margin: 1rem 0;
    }
    
    .ticker-tag {
        display: inline-block;
        background: #667eea;
        color: white;
        padding: 0.3rem 0.6rem;
        border-radius: 6px;
        margin: 0.2rem;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .ticker-tag.custom {
        background: #43a047;
    }
    /* ========== 新增：对话界面样式 ========== */
    .chat-container {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 2rem 0;
        border: 2px solid #e0e0e0;
    }
    
    .chat-message {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.8rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .chat-message.user {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-left: 3px solid #667eea;
    }
    
    .chat-message.assistant {
        background: white;
        border-left: 3px solid #43a047;
    }
    
    .chat-header {
        font-weight: 700;
        color: #667eea;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
    }
    
    .quick-question-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        border: none;
        font-size: 0.9rem;
        font-weight: 600;
        margin: 0.3rem;
    }
    
    .chat-divider {
        border-top: 2px dashed #e0e0e0;
        margin: 1.5rem 0;
    }
    /* ========================================= */
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
            model="deepseek-reasoner",
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
    "3mo": "近3个月",
    "6mo": "近6个月", 
    "1y": "近1年",
    "3y": "近3年",
    "5y": "近5年"
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

def get_deepseek_analysis(metrics_df, period):
    api_key = DEEPSEEK_API_KEY
    if not api_key:
        return "Error: DEEPSEEK_API_KEY not found. Please check your .env file."
    
    base_url = "https://api.deepseek.com"

    client = OpenAI(api_key=api_key, base_url=base_url)
    
    data_csv = metrics_df.to_csv(index=False)
    
    system_prompt = """
    You are a senior biotech equity analyst at a top-tier investment bank.
    
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
            model="deepseek-reasoner",
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
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#43a047'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    story.append(Paragraph("BioMarket Intelligence Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    report_info = f"""
    <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
    <b>Period:</b> {TIME_RANGE_MAP.get(time_range, time_range)}<br/>
    <b>Tickers:</b> {', '.join(tickers)}<br/>
    <b>Analyst:</b> DeepSeek-V3 AI
    """
    story.append(Paragraph(report_info, styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("Performance Metrics", heading_style))
    
    table_data = [['Ticker', 'Name', 'Return(%)', 'Vol(%)', 'Beta']]
    for _, row in metrics_df.iterrows():
        table_data.append([
            row['Ticker Code'],
            row['Name'][:30],
            f"{row['Total Return (%)']:.2f}",
            f"{row['Volatility (%)']:.2f}",
            f"{row['Beta']:.2f}"
        ])
    
    table = Table(table_data, colWidths=[0.8*inch, 2.5*inch, 1.2*inch, 1.2*inch, 0.8*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
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
                story.append(Paragraph(line.replace('###', '').strip(), heading_style))
            else:
                story.append(Paragraph(line.replace('**', '<b>').replace('**', '</b>').replace('*', ''), styles['Normal']))
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

# 自定义颜色映射函数（不依赖 matplotlib）
def color_return(val):
    """根据回报率返回颜色"""
    try:
        val = float(val)
        if val > 20:
            return 'background-color: #4caf50; color: white; font-weight: bold'
        elif val > 10:
            return 'background-color: #8bc34a; color: white'
        elif val > 0:
            return 'background-color: #cddc39; color: black'
        elif val > -10:
            return 'background-color: #ffeb3b; color: black'
        elif val > -20:
            return 'background-color: #ff9800; color: white'
        else:
            return 'background-color: #f44336; color: white; font-weight: bold'
    except:
        return ''

# ==================== 主界面 ====================

# 标题
st.markdown('<h1 class="main-title">BioMarket Tracker</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Professional Biotech Market Intelligence Platform | Powered by DeepSeek-V3</p>', unsafe_allow_html=True)

# ========== 英文版时间显示 ==========
col_time1, col_time2, col_time3 = st.columns([2, 1.5, 1.5], gap="small")

with col_time1:
    # 获取当前时间
    now = datetime.now()
    hour = now.hour
    
    # 判断市场状态（美股时间：21:30-04:00 北京时间）
    if (hour == 21 and now.minute >= 30) or (hour >= 22 and hour <= 23) or (hour >= 0 and hour < 4):
        market_text = "Market Open"
    else:
        market_text = "Market Closed"
    
    # 英文时间格式
    current_time = now.strftime("%I:%M %p")  # 03:16 PM
    current_date = now.strftime("%b %d, %Y")  # Feb 12, 2026
    
    # 显示
    st.markdown(
        f'<div style="padding: 10px; background: #f8f9fa; border-radius: 8px; font-size: 0.95rem;">'
        f'{market_text}</b> | '
        f' Last Update: <b>{current_time}</b> | '
        f' {current_date}'
        f'</div>',
        unsafe_allow_html=True
    )

with col_time2:
    if st.button("Refresh", use_container_width=True, key="refresh_btn"):
        # ✅ 强制保存所有关键状态（在 rerun 之前）
        st.session_state.analysis_started = True
        st.session_state.is_refreshing = True
        
        # ✅ 保存当前选择（防止侧边栏重置）
        st.session_state._saved_tickers = st.session_state.selected_tickers.copy()
        st.session_state._saved_time_range = st.session_state.selected_time_range
        st.session_state._saved_custom = st.session_state.custom_tickers.copy()
        st.session_state._saved_preset = st.session_state.preset_tickers.copy()
        
        # 清除数据缓存
        get_data.clear()
        st.session_state.last_update = datetime.now()
        st.rerun()

with col_time3:
    if st.button(" New Analysis", use_container_width=True):
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
        st.markdown("**Custom Search**")
        st.caption("Enter ticker symbols (comma-separated)")
        
        custom_input = st.text_input(
            "Ticker codes",
            placeholder="e.g., BNTX, CRSP, BEAM",
            label_visibility="collapsed",
            key="custom_input"
        )
        
        custom_tickers = []
        invalid_tickers = []
        
        if custom_input:
            raw_tickers = [t.strip().upper() for t in custom_input.split(',') if t.strip()]
            
            with st.spinner('Validating...'):
                for ticker in raw_tickers:
                    is_valid, full_name = validate_and_get_name(ticker)
                    if is_valid:
                        custom_tickers.append(ticker)
                        if ticker not in TICKER_MAP:
                            TICKER_MAP[ticker] = f"{ticker} ({full_name})"
                    else:
                        invalid_tickers.append(ticker)
            
            if custom_tickers:
                st.success(f"Valid: {', '.join(custom_tickers)}")
            if invalid_tickers:
                st.error(f"Invalid: {', '.join(invalid_tickers)}")
        
        st.session_state.custom_tickers = custom_tickers
        
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
    st.caption("AI: DeepSeek-V3")
    st.caption("Dev: Runze Zhu")


# ==================== 主内容区 ====================
# ========== 优先检查 analysis_started 状态 ==========
should_show_analysis = (
    (st.session_state.get('analysis_started', False) or 
     st.session_state.get('is_refreshing', False)) and  
    len(st.session_state.get('selected_tickers', [])) > 0
)

# 临时调试（找到问题后删除）
if st.session_state.get('selected_tickers'):
    with st.sidebar.expander("🔍 Debug", expanded=False):
        st.json({
            "analysis_started": st.session_state.get('analysis_started', False),
            "is_refreshing": st.session_state.get('is_refreshing', False),
            "should_show": should_show_analysis,
            "tickers_count": len(st.session_state.get('selected_tickers', []))
        })

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
                    patch={"line": {"color": "#FF6F00", "width": 3, "dash": "dash"}}, 
                    selector={"name": spy_full_name}
                )
                fig_perf.update_traces(
                    patch={"line": {"width": 2.5}}, 
                    selector=lambda t: t.name != spy_full_name
                )
                fig_perf.update_layout(
                    hovermode='x unified',
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(size=11),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    height=450
                )
                
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
                            line=dict(color='#9c27b0', width=2.5)
                        ))
                        fig_rsi.add_hrect(y0=70, y1=100, fillcolor="red", opacity=0.08, line_width=0)
                        fig_rsi.add_hrect(y0=0, y1=30, fillcolor="green", opacity=0.08, line_width=0)
                        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
                        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
                        fig_rsi.update_layout(
                            title=f"RSI - {TICKER_MAP.get(tech_ticker, tech_ticker)}",
                            yaxis_title="RSI",
                            height=320,
                            hovermode='x',
                            plot_bgcolor='white',
                            showlegend=False
                        )
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
                            line=dict(color='#2196f3', width=2)
                        ))
                        fig_macd.add_trace(go.Scatter(
                            x=signal.index, y=signal, 
                            name='Signal', 
                            line=dict(color='#ff5722', width=2)
                        ))
                        fig_macd.add_trace(go.Bar(
                            x=histogram.index, y=histogram, 
                            name='Histogram', 
                            marker_color='rgba(120,120,120,0.4)'
                        ))
                        fig_macd.update_layout(
                            title=f"MACD - {TICKER_MAP.get(tech_ticker, tech_ticker)}",
                            yaxis_title="Value",
                            height=320,
                            hovermode='x',
                            plot_bgcolor='white',
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
                        )
                        st.plotly_chart(fig_macd, use_container_width=True)
                        
                        if macd.iloc[-1] > signal.iloc[-1]:
                            st.markdown('<span class="status-badge status-bullish">Bullish Signal</span>', unsafe_allow_html=True)
                            st.caption("MACD crossed above signal line")
                        else:
                            st.markdown('<span class="status-badge status-bearish">Bearish Signal</span>', unsafe_allow_html=True)
                            st.caption("MACD crossed below signal line")
                    
                    fig_bb = go.Figure()
                    fig_bb.add_trace(go.Scatter(
                        x=ticker_prices.index, y=ticker_prices, 
                        name='Price', 
                        line=dict(color='#000000', width=2.5)
                    ))
                    fig_bb.add_trace(go.Scatter(
                        x=sma.index, y=sma, 
                        name='SMA(20)', 
                        line=dict(color='#2196f3', width=1.5, dash='dash')
                    ))
                    fig_bb.add_trace(go.Scatter(
                        x=upper_bb.index, y=upper_bb, 
                        name='Upper Band', 
                        line=dict(color='#f44336', width=1, dash='dot'),
                        fill=None
                    ))
                    fig_bb.add_trace(go.Scatter(
                        x=lower_bb.index, y=lower_bb, 
                        name='Lower Band', 
                        line=dict(color='#4caf50', width=1, dash='dot'),
                        fill='tonexty',
                        fillcolor='rgba(120,120,120,0.08)'
                    ))
                    fig_bb.update_layout(
                        title=f"Bollinger Bands - {TICKER_MAP.get(tech_ticker, tech_ticker)}",
                        yaxis_title="Price ($)",
                        height=380,
                        hovermode='x unified',
                        plot_bgcolor='white',
                        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5)
                    )
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
                        color_continuous_scale='RdYlGn_r',
                        title="Risk-Return Frontier"
                    )
                    
                    fig_scat.update_traces(
                        textposition='top center',
                        textfont=dict(size=11, color='black'),
                        marker=dict(line=dict(width=1.5, color='white'))
                    )
                    fig_scat.add_vline(
                        x=spy_volatility, 
                        line_dash="dash", 
                        line_color="#FF6F00", 
                        annotation_text="Market Risk",
                        annotation_position="top"
                    )
                    fig_scat.add_hline(
                        y=spy_total_return, 
                        line_dash="dash", 
                        line_color="#FF6F00", 
                        annotation_text="Market Return",
                        annotation_position="right"
                    )
                    fig_scat.update_layout(
                        height=480,
                        hovermode='closest',
                        plot_bgcolor='white',
                        showlegend=True
                    )
                    st.plotly_chart(fig_scat, use_container_width=True)
                
                with col2:
                    st.markdown("**Key Metrics**")
                    display_df = metrics_df[['Name', 'Total Return (%)', 'Volatility (%)', 'Beta', 'Sharpe Ratio']].copy()
                    display_df.columns = ['Name', 'Return(%)', 'Vol(%)', 'Beta', 'Sharpe']
                    display_df = display_df.set_index('Name')
                    
                    styled_df = display_df.style.format("{:.2f}").applymap(
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
        <h3 style="margin: 0 0 1rem 0; color: #667eea;">Analysis Configuration</h3>
        <p style="margin: 0.5rem 0;"><b>Total Selected:</b> {len(st.session_state.selected_tickers)} stocks</p>
        <p style="margin: 0.5rem 0; font-size: 0.9rem; color: #666;">
            <b>Custom:</b> {custom_list}<br/>
            <b>Preset:</b> {preset_list}
        </p>
        <p style="margin: 0.5rem 0;"><b>Time Period:</b> {TIME_RANGE_MAP.get(st.session_state.selected_time_range, st.session_state.selected_time_range)}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Start Analysis", type="primary", use_container_width=True, key="start_analysis"):
            st.session_state.analysis_started = True
            st.rerun()


else:
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 0;">
            <h2 style="color: #667eea; font-weight: 700;">Welcome to BioMarket Tracker</h2>
            <p style="font-size: 1rem; color: #666; margin: 1.5rem 0;">
                Professional biotech equity analysis platform
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("""
        **Getting Started**
        
        1. Open the sidebar on the left
        2. Enter custom tickers OR select from preset list (or both!)
        3. Choose your analysis time period
        4. Click "Start Analysis" button
        5. View comprehensive market insights
        """)
        
        st.success("""
        **Key Features**
        
        - Combine custom search with preset stocks
        - Global stock search with real-time validation
        - Technical indicators (RSI, MACD, Bollinger Bands)
        - Smart price alerts and notifications
        - Risk-return analysis (Beta, Volatility, Sharpe)
        - AI-powered investment reports
        - Professional PDF export
        - Favorites management
        """)
        
        st.markdown("""
        <div style="text-align: center; margin-top: 2.5rem; padding: 1.5rem; 
                    background: #f8f9fa; border-radius: 10px; border-left: 4px solid #667eea;">
            <p style="color: #666; font-size: 0.9rem; margin: 0;">
                Disclaimer: For educational purposes only. Not investment advice.
            </p>
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
                    if st.button(btn_text, key=f"quick_q_{idx}", 
            use_container_width=True):
                        with st.spinner("🤖 AI is thinking..."):
                            handle_user_question(question, analyzed_tickers, 
            chat_client)
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
