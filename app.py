import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from openai import OpenAI

# --- 配置区域 ---
# ⚠️ 注意：在生产环境中，建议将 Key 放入 st.secrets，不要直接写在代码里
DEEPSEEK_API_KEY = "sk-94393b595210452cbe406e7301a0c410"
BASE_URL = "https://api.deepseek.com"

st.set_page_config(page_title="BioMarket Tracker AI", page_icon="🧬", layout="wide")

# --- 映射表 ---
TICKER_MAP = {
    'XBI': 'XBI (S&P Biotech ETF/标普生科)',
    'IBB': 'IBB (Nasdaq Biotech ETF/纳指生科)',
    'MRNA': 'MRNA (Moderna/莫德纳)',
    'PFE': 'PFE (Pfizer/辉瑞)',
    'VRTX': 'VRTX (Vertex/福泰制药)',
    'REGN': 'REGN (Regeneron/再生元)',
    'AMGN': 'AMGN (Amgen/安进)',
    'GILD': 'GILD (Gilead/吉利德)',
    'SPY': 'SPY (S&P 500/标普500基准)',
    'LLY': 'LLY (Eli Lilly/礼来)',
    'NVO': 'NVO (Novo Nordisk/诺和诺德)'
}

# --- 标题区域 ---
st.title("🧬 Biotech Market Intelligence Tracker (AI Enhanced)")
st.subheader("生物医药市场情报追踪器 - AI 增强版")
st.markdown("**Real-time analysis + AI Insights.** *(实时数据分析 + DeepSeek 智能解读)*")

# --- 侧边栏设置 ---
with st.sidebar:
    st.header("⚙️ Settings (设置)")
    
    available_tickers = list(TICKER_MAP.keys())
    if 'SPY' in available_tickers: 
        available_tickers.remove('SPY')
        
    default_selection = ['XBI', 'IBB', 'MRNA', 'PFE', 'VRTX']
    
    tickers = st.multiselect(
        "Select Tickers (选择股票/ETF)", 
        options=available_tickers,
        default=default_selection,
        format_func=lambda x: TICKER_MAP.get(x, x)
    )
    
    time_range = st.selectbox(
        "Time Range (时间范围)", 
        ["3mo", "6mo", "1y", "3y", "5y"], 
        index=2
    )
    
    st.markdown("---")
    st.caption("Data Source: Yahoo Finance")
    st.caption("AI Model: DeepSeek-V3")

# --- 数据获取函数 ---
@st.cache_data
def get_data(user_tickers, period):
    target_tickers = list(set(user_tickers + ['SPY']))
    # yfinance下载数据
    data = yf.download(target_tickers, period=period, auto_adjust=True, threads=False)
    
    # 处理多层索引问题
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

# --- AI 分析函数 ---
def get_deepseek_analysis(metrics_df, period):
    """
    调用 DeepSeek API 分析计算好的指标数据
    """
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)
    
    # 将数据转为 CSV 文本，方便 AI 理解
    data_csv = metrics_df.to_csv(index=False)
    
    system_prompt = """
    你是一位资深的生物医药行业投资分析师。用户会提供一份股票表现数据表（包含回报率、波动率、Beta系数）。
    
    请基于数据，用通俗、专业且带有一点幽默感的口吻，生成一份简报。
    
    请包含以下三个部分（使用Markdown格式）：
    1. 📊 **板块风向标**：根据整体回报率和Beta，判断当前生物医药板块是处于"进攻模式"还是"防御模式"。
    2. 🏆 **红黑榜**：
       - 点评表现最好的"明星股"（高回报）。
       - 警示"高危股"（高波动、低/负回报）。
       - 识别"防御股"（低Beta）。
    3. 💡 **操作建议**：给激进型和稳健型投资者各一句话建议。
    
    注意：
    - 直接分析数据，不要说废话。
    - 重点关注 Beta 值与波动率的关系。
    - 适当使用 Emoji。
    """
    
    user_prompt = f"分析周期: {period}。\n数据如下:\n{data_csv}"

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            temperature=0.6
        )
        return response
    except Exception as e:
        return f"Error: {str(e)}"

# --- 主程序逻辑 ---
if len(tickers) > 0:
    with st.spinner('Fetching real-time data... (正在获取实时数据...)'):
        try:
            prices, returns = get_data(tickers, time_range)
            
            if not prices.empty:
                # 1. 价格走势图
                mapped_columns = {col: TICKER_MAP.get(col, col) for col in prices.columns}
                
                st.divider()
                st.subheader(f"📈 Price Performance (股价表现 - 归一化)")
                
                normalized = prices / prices.iloc[0] * 100
                normalized_plot = normalized.rename(columns=mapped_columns)
                
                fig_perf = px.line(normalized_plot, x=normalized_plot.index, y=normalized_plot.columns,
                                   labels={'value': 'Rebased Price (相对价格, 起点=100)', 'variable': 'Asset', 'Date': 'Date'})
                
                spy_full_name = TICKER_MAP['SPY']
                fig_perf.update_traces(patch={"line": {"color": "#FF8C00", "width": 4}}, selector={"name": spy_full_name})
                fig_perf.update_traces(patch={"line": {"width": 2}}, selector=lambda t: t.name != spy_full_name)

                st.plotly_chart(fig_perf, use_container_width=True)

                # 2. 计算指标 (Metrics)
                st.divider()
                st.subheader("⚖️ Risk vs. Return Analysis (风险 vs 回报分析)")
                
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
                        
                        summary.append({
                            'Ticker Code': t,
                            'Name': TICKER_MAP.get(t, t),
                            'Total Return (%)': round(tot_ret, 2), 
                            'Volatility (%)': round(vol, 2), 
                            'Beta': round(beta, 2)
                        })
                
                metrics_df = pd.DataFrame(summary)
                
                # 3. 散点图与表格
                col1, col2 = st.columns([2, 1])
                with col1:
                    fig_scat = px.scatter(metrics_df, 
                                          x='Volatility (%)', 
                                          y='Total Return (%)',
                                          text='Ticker Code', # 用代码显示更简洁
                                          size=[20]*len(metrics_df),
                                          color='Beta', 
                                          color_continuous_scale='RdYlGn_r',
                                          title="Risk-Reward Frontier (风险-回报边界)")
                    
                    fig_scat.update_traces(textposition='top center')
                    fig_scat.add_vline(x=spy_volatility, line_dash="dash", line_color="gray", annotation_text="Market Risk")
                    fig_scat.add_hline(y=spy_total_return, line_dash="dash", line_color="gray", annotation_text="Market Return")
                    st.plotly_chart(fig_scat, use_container_width=True)
                
                with col2:
                    st.markdown("##### Detailed Metrics (详细数据)")
                    display_df = metrics_df[['Name', 'Total Return (%)', 'Volatility (%)', 'Beta']].set_index('Name')
                    st.dataframe(display_df.style.format("{:.2f}"), use_container_width=True)

                # --- 4. AI 智能分析模块 (新增核心功能) ---
                st.divider()
                st.subheader("🤖 DeepSeek AI Analyst (智能研报)")
                
                st.info("点击下方按钮，让 AI 基于上述数据为您生成一份实时投资分析报告。")
                
                if st.button("✨ Generate AI Analysis (生成深度解读)", type="primary"):
                    with st.status("🤖 AI Analyst is thinking... (AI 正在分析数据...)", expanded=True) as status:
                        st.write("1. Reading market data... (读取市场数据)")
                        st.write("2. Calculating risk metrics... (计算风险指标)")
                        st.write("3. Generating insights... (生成观点)")
                        
                        # 创建占位符用于流式输出
                        response_placeholder = st.empty()
                        full_response = ""
                        
                        # 调用 API
                        stream = get_deepseek_analysis(metrics_df, time_range)
                        
                        if isinstance(stream, str):
                            status.update(label="❌ Error", state="error")
                            st.error(stream)
                        else:
                            # 流式渲染
                            for chunk in stream:
                                if chunk.choices[0].delta.content:
                                    content = chunk.choices[0].delta.content
                                    full_response += content
                                    response_placeholder.markdown(full_response + "▌")
                            
                            response_placeholder.markdown(full_response)
                            status.update(label="✅ Analysis Complete (分析完成)", state="complete")

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.warning("Please refresh the page. (请刷新页面)")
else:
    st.info("👈 Please select tickers from the sidebar to begin. (请在左侧选择股票代码)")
