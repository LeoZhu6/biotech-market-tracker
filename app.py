import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(page_title="BioMarket Tracker", page_icon="📈", layout="wide")

st.title("📈 Biotech Market Intelligence Tracker")
st.markdown("Real-time analysis of volatility (Beta) and performance vs. S&P 500.")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")
    default_tickers = ['XBI', 'IBB', 'MRNA', 'PFE', 'VRTX', 'REGN', 'AMGN', 'GILD']
    tickers = st.multiselect("Select Tickers", default_tickers, default=default_tickers)
    time_range = st.selectbox("Time Range", ["3mo", "6mo", "1y", "3y", "5y"], index=2)
    st.info("ℹ️ If you are in China, this app requires a VPN (Global Mode) to run locally, or deploy to Streamlit Cloud.")

# --- Robust Data Function ---
@st.cache_data
def get_data(user_tickers, period):
    # 1. 确保 SPY 在列表里
    target_tickers = list(set(user_tickers + ['SPY']))
    
    # 2. 下载数据 (使用 auto_adjust=True 简化数据结构)
    # threads=False 有时候能解决网络请求过快被拒的问题
    raw_data = yf.download(target_tickers, period=period, auto_adjust=True, threads=False)
    
    # 3. 数据清洗 (处理 yfinance 新版本的 MultiIndex 问题)
    # 如果下载了多个股票，yfinance 通常返回 ('Close', 'AAPL') 这种格式
    # 我们只取 'Close' 列
    if isinstance(raw_data.columns, pd.MultiIndex):
        try:
            # 尝试提取 Close 列
            df_close = raw_data['Close']
        except KeyError:
            # 如果没有 Close 列，可能直接就是价格数据（视版本而定）
            df_close = raw_data
    else:
        # 如果只有一列或者结构简单
        df_close = raw_data

    # 4. 再次检查 SPY 是否真的下载成功了
    if 'SPY' not in df_close.columns:
        # 如果下载失败，手动抛出异常，触发外层的 except
        raise ValueError("Failed to download market data (SPY). Check your internet connection.")

    # 5. 计算收益率
    returns = df_close.pct_change().dropna()
    return df_close, returns

# --- Main Logic ---
if len(tickers) > 0:
    with st.spinner('Fetching real-time data... (If local, ensure VPN is ON)'):
        try:
            prices, returns = get_data(tickers, time_range)
            
            # --- Chart 1: Performance ---
            st.subheader(f"📊 Price Performance (Normalized, Last {time_range})")
            # 归一化
            normalized = prices / prices.iloc[0] * 100
            fig_perf = px.line(normalized, x=normalized.index, y=normalized.columns,
                               labels={'value': 'Rebased Price (100 = Start)', 'variable': 'Ticker'})
            st.plotly_chart(fig_perf, use_container_width=True)

            # --- Chart 2: Risk/Reward ---
            st.subheader("⚖️ Risk vs. Return Analysis")
            
            # 准备数据
            summary = []
            spy_ret = returns['SPY']
            
            for t in tickers:
                if t in returns.columns:
                    # 计算 Beta
                    cov = returns[t].cov(spy_ret)
                    var = spy_ret.var()
                    beta = cov / var
                    
                    # 计算回报和波动
                    tot_ret = (prices[t].iloc[-1] / prices[t].iloc[0] - 1) * 100
                    vol = returns[t].std() * (252**0.5) * 100
                    
                    summary.append({
                        'Ticker': t,
                        'Return (%)': tot_ret,
                        'Volatility (%)': vol,
                        'Beta': beta
                    })
            
            metrics_df = pd.DataFrame(summary)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                if not metrics_df.empty:
                    fig_scat = px.scatter(metrics_df, x='Volatility (%)', y='Return (%)',
                                          text='Ticker', size=[20]*len(metrics_df),
                                          color='Beta', color_continuous_scale='RdYlGn_r',
                                          title="Risk-Reward Frontier (vs SPY)")
                    fig_scat.update_traces(textposition='top center')
                    st.plotly_chart(fig_scat, use_container_width=True)
            
            with col2:
                st.dataframe(metrics_df.set_index('Ticker').style.format("{:.2f}"), use_container_width=True)

        except Exception as e:
            st.error(f"⚠️ Data Error: {e}")
            st.warning("Hint: If you are in China, Yahoo Finance is blocked. Please deploy to Streamlit Cloud or use a Global VPN.")
else:
    st.info("Select tickers to begin.")
