import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- Page Config (页面设置) ---
st.set_page_config(page_title="BioMarket Tracker", page_icon="📈", layout="wide")

# --- Title (标题) ---
st.title("📈 Biotech Market Intelligence Tracker")
st.subheader("生物医药市场情报追踪器")
st.markdown("**Real-time analysis of volatility (Beta) and performance vs. S&P 500.**")
st.markdown("*(实时分析生物医药股的波动率与大盘表现对比)*")

# --- Sidebar (侧边栏) ---
with st.sidebar:
    st.header("⚙️ Settings (设置)")
    
    default_tickers = ['XBI', 'IBB', 'MRNA', 'PFE', 'VRTX', 'REGN', 'AMGN', 'GILD']
    tickers = st.multiselect(
        "Select Tickers (选择股票/ETF)", 
        default_tickers, 
        default=default_tickers
    )
    
    time_range = st.selectbox(
        "Time Range (时间范围)", 
        ["3mo", "6mo", "1y", "3y", "5y"], 
        index=2
    )
    
    st.markdown("---")
    st.info("""
    **Ticker Guide (代码指南):**
    * **XBI**: SPDR Biotech ETF (中小盘生物科技指数)
    * **IBB**: iShares Biotech ETF (大盘生物科技指数)
    * **SPY**: S&P 500 (标普500/大盘基准)
    """)

# --- Data Function (数据抓取 - V3稳健版) ---
@st.cache_data
def get_data(user_tickers, period):
    # 1. 确保 SPY 在列表里
    target_tickers = list(set(user_tickers + ['SPY']))
    
    # 2. 下载数据
    data = yf.download(target_tickers, period=period, auto_adjust=True, threads=False)
    
    # 3. 提取收盘价
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
    
    if 'SPY' not in df_close.columns:
        return pd.DataFrame(), pd.DataFrame()

    # 5. 计算收益率
    returns = df_close.pct_change().dropna()
    return df_close, returns

# --- Main Logic (主逻辑) ---
if len(tickers) > 0:
    with st.spinner('Fetching data... (正在获取数据...)'):
        try:
            prices, returns = get_data(tickers, time_range)
            
            if not prices.empty:
                # ==========================================
                # SECTION 1: Price Performance (股价表现)
                # ==========================================
                st.divider()
                st.subheader(f"📊 Price Performance (股价表现 - 归一化)")
                
                # 教学说明栏
                with st.expander("ℹ️ How to read this chart? (如何读懂这张图？)"):
                    st.markdown("""
                    * **Normalization (归一化)**: All prices are rebased to **100** at the start date. 
                      (所有股价在起始日都被设为 100，相当于假设你在那天每只股票都投了 100 块钱。)
                    * **Above 100 (大于100)**: Profit (赚钱了).
                    * **Below 100 (小于100)**: Loss (亏钱了).
                    * **Compare with SPY**: If a line is above the orange SPY line, it is **"Outperforming" (跑赢大盘)**.
                    """)

                normalized = prices / prices.iloc[0] * 100
                fig_perf = px.line(normalized, x=normalized.index, y=normalized.columns,
                                   labels={
                                       'value': 'Rebased Price (相对价格, 起点=100)', 
                                       'variable': 'Ticker (代码)',
                                       'Date': 'Date (日期)'
                                   })
                st.plotly_chart(fig_perf, use_container_width=True)

                # ==========================================
                # SECTION 2: Risk vs Return (风险回报分析)
                # ==========================================
                st.divider()
                st.subheader("⚖️ Risk vs. Return Analysis (风险 vs 回报分析)")
                
                # 教学说明栏
                with st.expander("ℹ️ Key Metrics Explanation (关键指标解释) - 面试必看"):
                    st.markdown("""
                    * **Total Return (总回报率)**: How much percentage the stock gained/lost in the selected period.
                    * **Volatility (波动率)**: A measure of risk. Higher volatility means the price swings wildly (High Risk). 
                      (衡量风险的指标。波动率越高，股价上下跳动越剧烈，风险越大。)
                    * **Beta (贝塔系数)**: 
                        * **Beta = 1**: Moves exactly with the market (SPY). (和大盘同频)
                        * **Beta > 1**: More volatile than the market (Aggressive). (比大盘更激进，大盘涨1%，它可能涨1.5%)
                        * **Beta < 1**: Less volatile (Defensive). (比大盘稳健)
                    """)

                summary = []
                spy_ret = returns['SPY']
                
                for t in tickers:
                    if t in returns.columns:
                        # Beta Calculation
                        cov = returns[t].cov(spy_ret)
                        var = spy_ret.var()
                        beta = cov / var if var != 0 else 0
                        
                        # Metrics
                        tot_ret = (prices[t].iloc[-1] / prices[t].iloc[0] - 1) * 100
                        vol = returns[t].std() * (252**0.5) * 100
                        
                        summary.append({
                            'Ticker': t, 
                            'Total Return (总回报率 %)': tot_ret, 
                            'Volatility (波动率/风险 %)': vol, 
                            'Beta (贝塔系数)': beta
                        })
                
                metrics_df = pd.DataFrame(summary)
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    # 散点图
                    fig_scat = px.scatter(metrics_df, 
                                          x='Volatility (波动率/风险 %)', 
                                          y='Total Return (总回报率 %)',
                                          text='Ticker', 
                                          size=[20]*len(metrics_df),
                                          color='Beta (贝塔系数)', 
                                          color_continuous_scale='RdYlGn_r',
                                          title="Risk-Reward Frontier (风险-回报边界)")
                    fig_scat.update_traces(textposition='top center')
                    # 加两条基准线
                    fig_scat.add_vline(x=metrics_df[metrics_df['Ticker']=='SPY']['Volatility (波动率/风险 %)'].values[0], line_dash="dash", annotation_text="Market Risk")
                    fig_scat.add_hline(y=metrics_df[metrics_df['Ticker']=='SPY']['Total Return (总回报率 %)'].values[0], line_dash="dash", annotation_text="Market Return")
                    
                    st.plotly_chart(fig_scat, use_container_width=True)
                
                with col2:
                    # 表格
                    st.markdown("##### Detailed Metrics (详细数据)")
                    # 格式化表格显示
                    display_df = metrics_df.set_index('Ticker')
                    st.dataframe(display_df.style.format("{:.2f}"), use_container_width=True)

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.warning("Please refresh the page. (请刷新页面)")
else:
    st.info("👈 Please select tickers from the sidebar to begin. (请在左侧选择股票代码)")
