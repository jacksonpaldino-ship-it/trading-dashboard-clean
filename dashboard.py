# dashboard.py

import streamlit as st
import pandas as pd
import plotly.express as px
from alpaca.trading.client import TradingClient
import os
from datetime import datetime

# =========================================
# PAGE CONFIG
# =========================================

st.set_page_config(
    page_title="Trading Dashboard",
    layout="wide"
)

# =========================================
# AUTO REFRESH
# =========================================

st.markdown("""
<meta http-equiv="refresh" content="60">
""", unsafe_allow_html=True)

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
    font-size: 42px !important;
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
# ALPACA CONNECTION
# =========================================

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

client = TradingClient(
    API_KEY,
    SECRET_KEY,
    paper=False
)

account = client.get_account()

equity = float(account.equity)
cash = float(account.cash)
buying_power = float(account.buying_power)

daily_pnl = equity - float(account.last_equity)

daily_pct = (
    daily_pnl
    / float(account.last_equity)
) * 100

# =========================================
# SIDEBAR
# =========================================

st.sidebar.title(
    "📈 Trading Dashboard"
)

st.sidebar.success(
    "System Online"
)

st.sidebar.markdown("---")

st.sidebar.write("🏠 Overview")
st.sidebar.write("📦 Positions")
st.sidebar.write("📄 Orders")
st.sidebar.write("📊 Analytics")
st.sidebar.write("⚙ Settings")

st.sidebar.markdown("---")

st.sidebar.write("Updated:")

st.sidebar.write(
    datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)

# =========================================
# TITLE
# =========================================

st.markdown(
    "<div class='big-font'>📈 Advanced Trading Dashboard</div>",
    unsafe_allow_html=True
)

st.write("")

# =========================================
# METRICS
# =========================================

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.markdown(f"""
    <div class="metric-card">
        <div class="small-font">Equity</div>
        <h2>${equity:,.2f}</h2>
        <div style="color:#4ade80;">
        {daily_pct:.2f}%
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:

    st.markdown(f"""
    <div class="metric-card">
        <div class="small-font">Cash</div>
        <h2>${cash:,.2f}</h2>
    </div>
    """, unsafe_allow_html=True)

with col3:

    st.markdown(f"""
    <div class="metric-card">
        <div class="small-font">Buying Power</div>
        <h2>${buying_power:,.2f}</h2>
    </div>
    """, unsafe_allow_html=True)

with col4:

    pnl_color = (
        "#4ade80"
        if daily_pnl >= 0
        else "#ef4444"
    )

    st.markdown(f"""
    <div class="metric-card">
        <div class="small-font">Daily PnL</div>
        <h2 style="color:{pnl_color};">
        ${daily_pnl:,.2f}
        </h2>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# =========================================
# EQUITY CURVE
# =========================================

st.subheader("📈 Equity Curve")

try:

    equity_history = pd.read_csv(
        "equity_history.csv"
    )

    fig = px.line(
        equity_history,
        x="timestamp",
        y="equity"
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

except Exception as e:

    st.warning(
        "No equity history yet."
    )

    st.write(e)
st.subheader("🏆 Win Rate Analytics")

try:

    trade_df = pd.read_csv(
        "trade_history.csv"
    )

    total_trades = len(trade_df)

    buy_count = len(
        trade_df[
            trade_df["side"] == "OrderSide.BUY"
        ]
    )

    sell_count = len(
        trade_df[
            trade_df["side"] == "OrderSide.SELL"
        ]
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Total Trades",
            total_trades
        )

    with c2:

        st.metric(
            "Buy Orders",
            buy_count
        )

    with c3:

        st.metric(
            "Sell Orders",
            sell_count
        )

except Exception as e:

    st.warning(
        "No trade history yet"
    )
# =========================================
# PERFORMANCE ANALYTICS
# =========================================

st.subheader(
    "📊 Performance Analytics"
)

try:

    analytics_df = pd.read_csv(
        "analytics_snapshot.csv"
    )

    latest = analytics_df.iloc[-1]

    exposure = float(
        latest["total_exposure"]
    )

    open_positions = int(
        latest["open_positions"]
    )

    peak_equity = equity_history[
        "equity"
    ].max()

    current_equity = equity_history[
        "equity"
    ].iloc[-1]

    drawdown = (
        (
            peak_equity
            - current_equity
        )
        / peak_equity
    ) * 100

    a1, a2, a3 = st.columns(3)

    with a1:

        st.metric(
            "Open Positions",
            open_positions
        )

    with a2:

        st.metric(
            "Total Exposure",
            f"${exposure:,.2f}"
        )

    with a3:

        st.metric(
            "Drawdown",
            f"{drawdown:.2f}%"
        )

except Exception as e:

    st.warning(
        "Analytics unavailable"
    )

    st.write(e)

# =========================================
# POSITIONS SNAPSHOT
# =========================================

st.subheader(
    "📦 Positions Snapshot"
)

try:

    positions_df = pd.read_csv(
        "positions_snapshot.csv"
    )

    st.dataframe(
        positions_df,
        use_container_width=True
    )

except:

    st.info(
        "No positions snapshot yet."
    )

# =========================================
# ORDERS SNAPSHOT
# =========================================

st.subheader(
    "📄 Orders Snapshot"
)

try:

    orders_df = pd.read_csv(
        "orders_snapshot.csv"
    )

    st.dataframe(
        orders_df,
        use_container_width=True
    )

except:

    st.info(
        "No orders snapshot yet."
    )

# =========================================
# FOOTER
# =========================================

st.success(
    "Dashboard Running Successfully"
)
