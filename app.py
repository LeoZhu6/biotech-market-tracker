import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

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

# --- Data Function (修复版) ---
@st.cache_data
def get_data(user_tickers, period):
    # 1. 确保 SPY 在列表里
    target_tickers = list(set(user_tickers + ['SPY']))
    
    # 2. 下载数据
    # auto_adjust=True 会让 'Close' 变成复权收盘价，不再需要 'Adj Close'
    data = yf.download(target_tickers, period=period, auto_adjust=True, threads=False)
    
    # 3. 提取收盘价 (处理多层索引问题)
    # 如果数据有多层列 (比如 Price, Ticker)，我们只取 'Close'
    if isinstance(data.columns, pd.MultiIndex):
        try:
            # 尝试直接获取 Close 层级
            df_close = data['Close']
        except KeyError:
            # 备用方案：如果结构不同，尝试直接用 data
            df_close = data
    else:
        # 如果只有一层索引
        if 'Close' in data.columns:
            df_close = data['Close']
        else:
            df_close = data

    # 4. 再次清洗：确保所有列都是数字，且 SPY 存在
    df_close = df_close.apply(pd.to_numeric, errors='coerce').dropna()
    
    if 'SPY' not in df_close.columns:
        st.error("⚠️ Failed to fetch SPY data. Please refresh or check connection.")
        return pd.DataFrame(), pd.DataFrame()

    # 5. 计算收益率
    returns = df_close.pct_change().dropna()
    return df_close, returns

# --- Main Logic ---
if len(tickers) > 0:
    with st.spinner('Fetching data...'):
        try:
            prices, returns = get_data(tickers, time_range)
            
            if not prices.empty:
                # --- Chart 1: Performance ---
                st.subheader(f"📊 Price Performance (Normalized)")
                normalized = prices / prices.iloc[0] * 100
                fig_perf = px.line(normalized, x=normalized.index, y=normalized.columns,
                                   labels={'value': 'Rebased Price (100 = Start)', 'variable': 'Ticker'})
                st.plotly_chart(fig_perf, use_container_width=True)

                # --- Chart 2: Risk/Reward ---
                st.subheader("⚖️ Risk vs. Return Analysis")
                
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
                        
                        summary.append({'Ticker': t, 'Return (%)': tot_ret, 'Volatility (%)': vol, 'Beta': beta})
                
                metrics_df = pd.DataFrame(summary)
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    fig_scat = px.scatter(metrics_df, x='Volatility (%)', y='Return (%)',
                                          text='Ticker', size=[20]*len(metrics_df),
                                          color='Beta', color_continuous_scale='RdYlGn_r',
                                          title="Risk-Reward Frontier")
                    fig_scat.update_traces(textposition='top center')
                    st.plotly_chart(fig_scat, use_container_width=True)
                
                with col2:
                    st.dataframe(metrics_df.set_index('Ticker').style.format("{:.2f}"), use_container_width=True)

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.code(str(e)) # 打印详细报错以便调试
else:
    st.info("Select tickers to begin.")
