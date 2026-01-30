import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Page Config ---
st.set_page_config(page_title="BioMarket Tracker", page_icon="📈", layout="wide")

# --- Title ---
st.title("📈 Biotech Market Intelligence Tracker")
st.markdown("Real-time analysis of volatility (Beta) and performance vs. S&P 500.")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("⚙️ Settings")
    # 默认一些热门生物医药股 + XBI (指数)
    default_tickers = ['XBI', 'IBB', 'MRNA', 'PFE', 'VRTX', 'REGN', 'AMGN', 'GILD']
    tickers = st.multiselect("Select Tickers", default_tickers, default=default_tickers)
    
    # 时间范围选择
    time_range = st.selectbox("Time Range", ["3mo", "6mo", "1y", "3y", "5y"], index=2)
    
    st.info("ℹ️ **XBI** is the SPDR S&P Biotech ETF (Small/Mid Cap).\n**IBB** is the iShares Biotechnology ETF (Large Cap).")

# --- Data Fetching Function ---
@st.cache_data
def get_data(tickers, period):
    # 加上 SPY (S&P 500) 作为基准
    all_tickers = tickers + ['SPY']
    data = yf.download(all_tickers, period=period)['Adj Close']
    
    # 计算每日收益率
    returns = data.pct_change().dropna()
    return data, returns

# --- Main Logic ---
if len(tickers) > 0:
    with st.spinner('Fetching real-time data from Yahoo Finance...'):
        try:
            prices, returns = get_data(tickers, time_range)
            
            # --- 1. Normalized Performance Chart ---
            st.subheader(f"📊 Price Performance (Normalized, Last {time_range})")
            
            # 归一化：让所有股票从 100 开始跑，方便对比
            normalized_prices = prices / prices.iloc[0] * 100
            
            fig_perf = px.line(normalized_prices, x=normalized_prices.index, y=normalized_prices.columns,
                               labels={'value': 'Rebased Price (100 = Start)', 'variable': 'Ticker'},
                               color_discrete_sequence=px.colors.qualitative.Bold)
            fig_perf.update_layout(hovermode="x unified")
            st.plotly_chart(fig_perf, use_container_width=True)

            # --- 2. Risk vs Return Analysis ---
            st.subheader("⚖️ Risk vs. Return Analysis")
            
            col1, col2 = st.columns([1, 1])
            
            # 计算指标
            total_return = (prices.iloc[-1] / prices.iloc[0] - 1) * 100
            volatility = returns.std() * (252 ** 0.5) * 100 # 年化波动率
            
            # 计算 Beta (相对于 SPY)
            spy_returns = returns['SPY']
            betas = {}
            for t in tickers:
                if t != 'SPY':
                    cov = returns[t].cov(spy_returns)
                    var = spy_returns.var()
                    betas[t] = cov / var
            
            # 整理成 DataFrame
            metrics_df = pd.DataFrame({
                'Ticker': tickers,
                'Total Return (%)': [total_return[t] for t in tickers],
                'Volatility (Risk) (%)': [volatility[t] for t in tickers],
                'Beta (vs SPY)': [betas.get(t, 1.0) for t in tickers] # SPY beta is 1
            })
            
            with col1:
                # 散点图：横轴是风险，纵轴是回报
                fig_scatter = px.scatter(metrics_df, x='Volatility (Risk) (%)', y='Total Return (%)',
                                         text='Ticker', size=[15]*len(metrics_df),
                                         color='Beta (vs SPY)', color_continuous_scale='RdYlGn_r', # 红色代表高Beta(高风险)
                                         title="Risk-Reward Frontier")
                fig_scatter.update_traces(textposition='top center')
                fig_scatter.add_vline(x=volatility['SPY'], line_dash="dash", annotation_text="Market Risk (SPY)")
                fig_scatter.add_hline(y=total_return['SPY'], line_dash="dash", annotation_text="Market Return (SPY)")
                st.plotly_chart(fig_scatter, use_container_width=True)
                
            with col2:
                # 表格展示
                st.markdown("##### Detailed Metrics")
                st.dataframe(metrics_df.style.format("{:.2f}"), use_container_width=True)
                
            # --- 3. Correlation Matrix ---
            st.subheader("🔗 Correlation Matrix")
            corr_matrix = returns[tickers + ['SPY']].corr()
            fig_corr = px.imshow(corr_matrix, text_auto=True, color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
            st.plotly_chart(fig_corr, use_container_width=True)

        except Exception as e:
            st.error(f"Error fetching data: {e}")
else:
    st.warning("Please select at least one ticker from the sidebar.")

