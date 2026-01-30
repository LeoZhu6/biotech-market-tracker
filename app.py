import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="BioMarket Tracker", page_icon="📈", layout="wide")

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

st.title("📈 Biotech Market Intelligence Tracker")
st.subheader("生物医药市场情报追踪器")
st.markdown("**Real-time analysis of volatility (Beta) and performance vs. S&P 500.**")
st.markdown("*(实时分析生物医药股的波动率与大盘表现对比)*")

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

@st.cache_data
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

if len(tickers) > 0:
    with st.spinner('Fetching real-time data... (正在获取实时数据...)'):
        try:
            prices, returns = get_data(tickers, time_range)
            
            if not prices.empty:
                mapped_columns = {col: TICKER_MAP.get(col, col) for col in prices.columns}
                
                st.divider()
                st.subheader(f"📊 Price Performance (股价表现 - 归一化)")
                
                with st.expander("ℹ️ Guide: How to interpret this chart (指南：如何解读此图)"):
                    st.markdown("""
                    **1. Normalization Logic (归一化逻辑)**
                    * All assets start at **100**. This allows us to compare "apples to oranges" (e.g., a $30 stock vs. a $300 stock).
                    * (所有资产起点设为100，实现了不同价位股票的可比性。)

                    **2. Relative Strength (相对强弱)**
                    * **Above SPY (Orange Line)**: The stock is generating "Alpha" (Excess Return). It is beating the market.
                    * **Below SPY**: The stock is underperforming the broader market.
                    * (位于橙色SPY线上方代表跑赢大盘，产生超额收益；下方则代表跑输大盘。)
                    
                    **3. Trend Analysis (趋势分析)**
                    * Look for divergence. If the Biotech sector (XBI) drops while the Market (SPY) rises, it indicates a sector-specific rotation or risk-off sentiment.
                    * (观察背离现象。如果生物医药板块下跌而大盘上涨，通常暗示资金正在轮动或避险。)
                    """)

                normalized = prices / prices.iloc[0] * 100
                normalized_plot = normalized.rename(columns=mapped_columns)
                
                fig_perf = px.line(normalized_plot, x=normalized_plot.index, y=normalized_plot.columns,
                                   labels={
                                       'value': 'Rebased Price (相对价格, 起点=100)', 
                                       'variable': 'Asset (资产)',
                                       'Date': 'Date (日期)'
                                   })
                
                spy_full_name = TICKER_MAP['SPY']
                
                fig_perf.update_traces(
                    patch={"line": {"color": "#FF8C00", "width": 4}}, 
                    selector={"name": spy_full_name}
                )
                
                fig_perf.update_traces(
                    patch={"line": {"width": 2}}, 
                    selector=lambda t: t.name != spy_full_name
                )

                st.plotly_chart(fig_perf, use_container_width=True)

                st.divider()
                st.subheader("⚖️ Risk vs. Return Analysis (风险 vs 回报分析)")
                
                with st.expander("ℹ️ Guide: Investment Quadrants (指南：投资象限分析)"):
                    st.markdown("""
                    **The 4 Quadrants of Risk/Reward (风险回报的四个象限):**
                    
                    * **Top-Left (High Return, Low Volatility)**: 🌟 **The Stars**. Ideally where you want to be. High efficiency.
                      (左上：明星股。高回报低风险，最理想的投资标的。)
                    
                    * **Top-Right (High Return, High Volatility)**: 🚀 **Aggressive Growth**. Typical for clinical-stage biotech. High reward comes with high risk.
                      (右上：激进增长。典型的临床阶段生物科技股，高风险伴随高回报。)
                    
                    * **Bottom-Left (Low Return, Low Volatility)**: 🛡️ **Defensive/Slow**. Safe but stagnant money.
                      (左下：防御/缓慢。资金安全但增长停滞。)
                    
                    * **Bottom-Right (Low Return, High Volatility)**: ⚠️ **The Danger Zone**. Taking high risk for poor returns. Avoid these.
                      (右下：危险区。承担了高风险却只有低回报，应尽量避免。)
                    
                    **Key Metrics (关键指标):**
                    * **Beta > 1**: Aggressive/Volatile (激进).
                    * **Beta < 1**: Defensive/Stable (稳健).
                    """)

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
                            'Total Return (%)': tot_ret, 
                            'Volatility (%)': vol, 
                            'Beta': beta
                        })
                
                metrics_df = pd.DataFrame(summary)
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    fig_scat = px.scatter(metrics_df, 
                                          x='Volatility (%)', 
                                          y='Total Return (%)',
                                          text='Name', 
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

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.warning("Please refresh the page. (请刷新页面)")
else:
    st.info("👈 Please select tickers from the sidebar to begin. (请在左侧选择股票代码)")
