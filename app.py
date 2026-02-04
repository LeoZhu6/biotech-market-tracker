import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from openai import OpenAI

# --- 配置区域 ---
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
        
    
    tickers = st.multiselect(
        "Select Tickers (选择股票/ETF)", 
        options=available_tickers,
        default=[], 
        format_func=lambda x: TICKER_MAP.get(x, x),
        placeholder="Choose stocks to analyze... (请选择股票)" 
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
    Calls DeepSeek API to analyze metrics, strictly in English.
    """
    try:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
    except:
        return "Error: API Key not found. Please configure secrets.toml."

    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    
    # Data context
    data_csv = metrics_df.to_csv(index=False)
    
    system_prompt = """
    You are a top-tier Wall Street Biotech Equity Research Analyst. 
    You are presenting to a portfolio manager.
    
    The user will provide a dataset of stock performance metrics (Total Return, Volatility, Beta).
    
    Your task is to generate a **concise, professional investment memo** in ENGLISH.
    
    Please structure your response in Markdown:
    
    ### 1. 🧭 Sector Sentiment & Market Pulse
    - Analyze the overall mood. Is the biotech sector currently "Risk-On" (High Beta/High Return) or "Risk-Off"?
    - How does it compare to the broader market (SPY)?
    
    ### 2. 🎯 Alpha Drivers & Risk Factors
    - Identify the **"Top Picks"**: Stocks with the best risk-adjusted returns.
    - Flag the **"Underperformers"**: High volatility with negative returns (Capital destruction).
    - Comment on **Beta exposure**: Which stocks are highly correlated to the market vs. idiosyncratic movers.
    
    ### 3. ♟️ Strategic Recommendations
    - **For Aggressive Growth**: One actionable idea.
    - **For Capital Preservation**: One actionable idea.
    
    **Style Guidelines:**
    - Use professional financial terminology (e.g., "Alpha generation", "Drawdown", "High-beta play", "Defensive rotation").
    - Be direct and insightful. Avoid generic fluff.
    - Do NOT include disclaimers.
    """
    
    user_prompt = f"Time Horizon: {period}.\nData Set:\n{data_csv}"

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            temperature=0.5 # 稍微降低温度，让回答更严谨
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

                # --- 4. AI 智能分析模块 ---
                st.divider()
                st.subheader("🤖 AI Equity Research Analyst")
                
                st.info("Generate a professional investment memo based on the current metrics.")
                
                # 按钮文案改为纯英文
                if st.button("✨ Generate Investment Memo", type="primary"):
                    
                    # 状态栏文案改为纯英文
                    with st.status("🤖 AI Analyst is analyzing market data...", expanded=True) as status:
                        st.write("1. Cranking the numbers (Beta, Volatility)...")
                        st.write("2. Comparing against S&P 500 benchmark...")
                        st.write("3. Drafting research note...")
                        
                        response_placeholder = st.empty()
                        full_response = ""
                        
                        stream = get_deepseek_analysis(metrics_df, time_range)
                        
                        if isinstance(stream, str):
                            status.update(label="❌ Connection Error", state="error")
                            st.error(stream)
                        else:
                            for chunk in stream:
                                if chunk.choices[0].delta.content:
                                    content = chunk.choices[0].delta.content
                                    full_response += content
                                    response_placeholder.markdown(full_response + "▌")
                            
                            response_placeholder.markdown(full_response)
                            status.update(label="✅ Research Note Ready", state="complete")


        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.warning("Please refresh the page. (请刷新页面)")
else:
    # 当用户没选股票时，显示一个漂亮的欢迎页
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.info("👈 **Start Here (从左侧开始)**")
        st.markdown("""
        **How to use:**
        1. Go to the **Sidebar** on the left.
        2. Select **Tickers** (e.g., XBI, MRNA).
        3. Choose a **Time Range**.
        4. The AI Analyst will stand by.
        """)
    
    with col2:
        st.success("✨ **Features (功能亮点)**")
        st.markdown("""
        *   **📈 Real-time Alpha**: Compare stocks vs. S&P 500.
            *(实时超额收益分析)*
        *   **⚖️ Risk Quadrant**: Visualize Risk vs. Reward.
            *(风险-回报象限图)*
        *   **🤖 AI Insights**: DeepSeek-V3 generates instant reports.
            *(DeepSeek 智能生成投资研报)*
        """)



