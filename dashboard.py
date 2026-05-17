import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Trading Dashboard",
    layout="wide"
)

# =========================================
# CUSTOM CSS
# =========================================

st.markdown("""
<style>

.stApp {
    background-color: #020617;
    color: white;
}

.metric-card {
    background: #071225;
    padding: 20px;
    border-radius: 18px;
    border: 1px solid #1e293b;
}

.big-font {
    font-size: 40px !important;
    font-weight: 700;
    color: #4ade80;
}

.small-font {
    font-size: 14px;
    color: #94a3b8;
}

</style>
""", unsafe_allow_html=True)

# =========================================
# SIDEBAR
# =========================================

st.sidebar.title("📈 Trading Dashboard")

st.sidebar.success("System Online")

st.sidebar.markdown("---")

st.sidebar.write("🏠 Overview")
st.sidebar.write("📦 Positions")
st.sidebar.write("📄 Orders")
st.sidebar.write("📊 Analytics")
st.sidebar.write("⚙ Settings")

# =========================================
# TITLE
# =========================================

st.markdown(
    "<div class='big-font'>📈 Advanced Trading Dashboard</div>",
    unsafe_allow_html=True
)

st.write("")

# =========================================
# FAKE DATA
# =========================================

equity_data = pd.DataFrame({
    "Equity": [
        2000,
        2010,
        2025,
        2040,
        2055,
        2075,
        2090
    ]
})

# =========================================
# METRICS
# =========================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="metric-card">
        <div class="small-font">Equity</div>
        <h2>$2,090</h2>
        <div style="color:#4ade80;">+4.5%</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card">
        <div class="small-font">Cash</div>
        <h2>$1,240</h2>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card">
        <div class="small-font">Buying Power</div>
        <h2>$4,180</h2>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="metric-card">
        <div class="small-font">Daily PnL</div>
        <h2 style="color:#4ade80;">+$55</h2>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# =========================================
# EQUITY CURVE
# =========================================

st.subheader("📈 Equity Curve")

fig = px.line(
    equity_data,
    y="Equity"
)

fig.update_traces(
    line_color="#4ade80",
    line_width=4
)

fig.update_layout(
    paper_bgcolor="#020617",
    plot_bgcolor="#020617",
    font_color="white",
    height=500
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =========================================
# POSITIONS
# =========================================

st.subheader("📦 Open Positions")

positions = pd.DataFrame({
    "Symbol": ["NVDA", "SPY"],
    "Shares": [2, 5],
    "PnL": ["+$45", "-$12"]
})

st.dataframe(
    positions,
    use_container_width=True
)

# =========================================
# ORDERS
# =========================================

st.subheader("📄 Recent Orders")

orders = pd.DataFrame({
    "Symbol": ["AAPL", "TSLA", "AMD"],
    "Side": ["BUY", "SELL", "BUY"],
    "Qty": [1, 2, 3]
})

st.dataframe(
    orders,
    use_container_width=True
)

# =========================================
# FOOTER
# =========================================

st.success("Dashboard Running Successfully")
