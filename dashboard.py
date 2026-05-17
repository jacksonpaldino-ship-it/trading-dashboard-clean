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

# =========================================
# ACCOUNT INFO
# =========================================

account = client.get_account()

equity = float(account.equity)
cash = float(account.cash)
buying_power = float(account.buying_power)

daily_pnl = equity - float(account.last_equity)
daily_pct = (daily_pnl / float(account.last_equity)) * 100

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

st.sidebar.markdown("---")

st.sidebar.write(f"Updated:")
st.sidebar.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

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
        <div style="color:#4ade80;">{daily_pct:.2f}%</div>
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
    pnl_color = "#4ade80" if daily_pnl >= 0 else "#ef4444"

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
    equity_history = pd.read_csv("equity_history.csv")

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

except:
    st.warning("No equity history yet.")

# =========================================
# POSITIONS
# =========================================

st.subheader("📦 Open Positions")

try:
    positions = client.get_all_positions()

    if len(positions) > 0:

        pos_data = []

        for p in positions:
            pos_data.append({
                "Symbol": p.symbol,
                "Qty": p.qty,
                "Market Value": f"${float(p.market_value):,.2f}",
                "Unrealized PnL": f"${float(p.unrealized_pl):,.2f}"
            })

        positions_df = pd.DataFrame(pos_data)

        st.dataframe(
            positions_df,
            use_container_width=True
        )

    else:
        st.info("No open positions.")

except Exception as e:
    st.error(str(e))

# =========================================
# RECENT ORDERS
# =========================================

st.subheader("📄 Recent Orders")

try:
    orders = client.get_orders()

    order_data = []

    for o in orders[:10]:

        order_data.append({
            "Symbol": o.symbol,
            "Side": o.side,
            "Qty": o.qty,
            "Status": o.status
        })

    orders_df = pd.DataFrame(order_data)

    st.dataframe(
        orders_df,
        use_container_width=True
    )

except Exception as e:
    st.error(str(e))

# =========================================
# FOOTER
# =========================================

st.success("Dashboard Running Successfully")
