import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- Configuration & Mapping (配置与映射) ---
st.set_page_config(page_title="BioMarket Tracker", page_icon="📈", layout="wide")

# 股票代码的中英对照字典
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

# --- Title (标题) ---
st.title("📈 Biotech Market Intelligence Tracker")
st.subheader("生物医药市场情报追踪器")
st.markdown("**Real-time analysis of volatility (Beta) and performance vs. S&P 500.**")
st.markdown("*(实时分析生物医药股的波动率与大盘表现对比)*")

# --- Sidebar (侧边栏) ---
with st.sidebar:
    st.header("⚙️ Settings (设置)")
    
    # 定义可选列表（只包含字典里的 Key）
    available_tickers = list(TICKER_MAP.keys())
    # 移除 SPY，因为它是基准，不需要用户选，默认会在后台跑
    if 'SPY' in available_tickers: 
        available_tickers.remove('SPY')
        
    default_selection = ['XBI', 'IBB', 'MRNA', 'PFE', 'VRTX']
    
    # 使用 format_func 让选项显示中文，但返回的还是代码
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

# --- Data Function (数据抓取) ---
@st.cache_data
def get_data(user_tickers, period):
    # 1. 自动加上 SPY 作为基准
    target_tickers = list(set(user_tickers + ['SPY']))
    
    # 2. 下载数据
    data = yf.download(target_tickers, period=period, auto_adjust=True, threads=False)
    
    # 3. 提取收盘价 (兼容性处理)
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

    # 4. 清洗
    df_close = df_close.apply(pd.to_numeric, errors='coerce').dropna()
    
    # 5. 检查 SPY 是否存在
    if 'SPY' not in df_close.columns:
        return pd.DataFrame(), pd.DataFrame()

    # 6. 重命名列名为中文友好格式 (用于后续画图)
    # 但我们要保留原始代码用于计算，所以这里先不改列名，画图时再映射
    
    # 7. 计算收益率
    returns = df_close.pct_change().dropna()
    return df_close, returns

# --- Main Logic (主逻辑) ---
if len(tickers) > 0:
    with st.spinner('Fetching real-time data... (正在获取实时数据...)'):
        try:
            prices, returns = get_data(tickers, time_range)
            
            if not prices.empty:
                # 准备映射后的名字列表
                mapped_columns = {col: TICKER_MAP.get(col, col) for col in prices.columns}
                
                # ==========================================
                # SECTION 1: Price Performance
                # ==========================================
                st.divider()
                st.subheader(f"📊 Price Performance (股价表现 - 归一化)")
                
                with st.expander("ℹ️ Guide: How to interpret this chart (指南：如何解读此图)"):
                    st.markdown("""
                    * **Normalization (归一化)**: All prices are rebased to **100** at the start date. This allows for direct comparison between high-priced and low-priced stocks.
                      (所有股价在起始日都被设为 100，以便直接对比高价股和低价股的涨跌幅度。)
                    * **Benchmark (基准)**: The orange line **SPY** represents the Market (S&P 500).
                      (橙色线 SPY 代表大盘基准。)
                    """)

                # 归一化处理
                normalized = prices / prices.iloc[0] * 100
                # 重命名列用于展示
                normalized_plot = normalized.rename(columns=mapped_columns)
                
                fig_perf = px.line(normalized_plot, x=normalized_plot.index, y=normalized_plot.columns,
                                   labels={
                                       'value': 'Rebased Price (相对价格, 起点=100)', 
                                       'variable': 'Asset (资产)',
                                       'Date': 'Date (日期)'
                                   })
                st.plotly_chart(fig_perf, use_container_width=True)

                # ==========================================
                # SECTION 2: Risk vs Return
                # ==========================================
                st.divider()
                st.subheader("⚖️ Risk vs. Return Analysis (风险 vs 回报分析)")
                
                with st.expander("ℹ️ Guide: Key Indicators (指南：关键指标解释)"):
                    st.markdown("""
                    * **Total Return (总回报率)**: Percentage gain/loss over the selected period.
                      (选定周期内的涨跌幅百分比。)
                    * **Volatility (波动率)**: Represents the risk. Higher volatility means larger price swings.
                      (代表风险。波动率越高，价格起伏越剧烈。)
                    * **Beta (贝塔系数)**: Measure of correlation with the market.
                      (衡量与大盘的相关性。)
                        * **Beta > 1**: Aggressive (High Risk). (激进/高风险)
                        * **Beta < 1**: Defensive (Low Risk). (防御/低风险)
                    """)

                summary = []
                spy_ret_series = returns['SPY']
                
                # 单独计算 SPY 的指标用于画基准线
                spy_total_return = (prices['SPY'].iloc[-1] / prices['SPY'].iloc[0] - 1) * 100
                spy_volatility = returns['SPY'].std() * (252**0.5) * 100
                
                for t in tickers:
                    if t in returns.columns:
                        # Beta Calculation
                        cov = returns[t].cov(spy_ret_series)
                        var = spy_ret_series.var()
                        beta = cov / var if var != 0 else 0
                        
                        # Metrics
                        tot_ret = (prices[t].iloc[-1] / prices[t].iloc[0] - 1) * 100
                        vol = returns[t].std() * (252**0.5) * 100
                        
                        summary.append({
                            'Ticker Code': t,
                            'Name': TICKER_MAP.get(t, t), # 使用中文名
                            'Total Return (%)': tot_ret, 
                            'Volatility (%)': vol, 
                            'Beta': beta
                        })
                
                metrics_df = pd.DataFrame(summary)
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    # 散点图
                    fig_scat = px.scatter(metrics_df, 
                                          x='Volatility (%)', 
                                          y='Total Return (%)',
                                          text='Name', # 显示中文名
                                          size=[20]*len(metrics_df),
                                          color='Beta', 
                                          color_continuous_scale='RdYlGn_r',
                                          title="Risk-Reward Frontier (风险-回报边界)")
                    
                    fig_scat.update_traces(textposition='top center')
                    
                    # 修复 Bug：直接使用计算好的 SPY 变量，不再查表
                    fig_scat.add_vline(x=spy_volatility, line_dash="dash", line_color="gray", annotation_text="Market Risk (SPY)")
                    fig_scat.add_hline(y=spy_total_return, line_dash="dash", line_color="gray", annotation_text="Market Return (SPY)")
                    
                    st.plotly_chart(fig_scat, use_container_width=True)
                
                with col2:
                    st.markdown("##### Detailed Metrics (详细数据)")
                    # 展示表格，把 Name 设为索引
                    display_df = metrics_df[['Name', 'Total Return (%)', 'Volatility (%)', 'Beta']].set_index('Name')
                    st.dataframe(display_df.style.format("{:.2f}"), use_container_width=True)

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.warning("Please refresh the page. (请刷新页面)")
else:
    st.info("👈 Please select tickers from the sidebar to begin. (请在左侧选择股票代码)")
