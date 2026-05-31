# dashboard.py

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from alpaca.trading.client import TradingClient

# =========================================
# PAGE CONFIG
# =========================================

st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📈",
    layout="wide",
)

# =========================================
# AUTO REFRESH + STYLE
# =========================================

st.markdown("""
<meta http-equiv="refresh" content="60">
<style>
.stApp {
    background-color: #020617;
    color: white;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}
.metric-card {
    background: linear-gradient(135deg, #071225 0%, #0f172a 100%);
    padding: 18px;
    border-radius: 18px;
    border: 1px solid #1e293b;
    min-height: 112px;
}
.metric-label {
    font-size: 13px;
    color: #94a3b8;
    margin-bottom: 6px;
}
.metric-value {
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 4px;
}
.metric-sub {
    font-size: 13px;
    color: #cbd5e1;
}
.good { color: #4ade80; }
.bad { color: #f87171; }
.warn { color: #facc15; }
.neutral { color: #cbd5e1; }
.status-box {
    background: #071225;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================================
# FILES THE DASHBOARD WILL LOOK FOR
# =========================================

DATA_FILES = {
    "equity": ["equity_history.csv", "data/equity_history.csv"],
    "trades": ["trade_history.csv", "trades.csv", "data/trade_history.csv"],
    "positions": ["positions_snapshot.csv", "positions.csv", "data/positions_snapshot.csv"],
    "orders": ["orders_snapshot.csv", "orders.csv", "data/orders_snapshot.csv"],
    "analytics": ["analytics_snapshot.csv", "analytics.csv", "data/analytics_snapshot.csv"],
    "decisions": ["decision_log.csv", "bot_decisions.csv", "ranked_candidates.csv", "data/decision_log.csv"],
}


# =========================================
# HELPERS
# =========================================

def get_secret(name, default=None):
    """
    Reads from Streamlit secrets first, then environment variables.
    This lets it work on Streamlit Cloud and locally.
    """
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, default)


@st.cache_data(ttl=45)
def load_csv(kind):
    for file_name in DATA_FILES.get(kind, []):
        if Path(file_name).exists():
            try:
                return pd.read_csv(file_name), file_name
            except Exception as exc:
                return pd.DataFrame(), f"{file_name} error: {exc}"
    return pd.DataFrame(), None


def clean(df):
    if df.empty:
        return df
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    return out


def to_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(str(value).replace("$", "").replace(",", "").replace("%", ""))
    except Exception:
        return default


def money(value):
    return f"${to_float(value):,.2f}"


def color_class(value):
    return "good" if to_float(value) >= 0 else "bad"


def metric_card(label, value, sub="", color="neutral"):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {color}">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def find_col(df, names):
    if df.empty:
        return None

    cols = {str(c).lower(): c for c in df.columns}

    for name in names:
        if name.lower() in cols:
            return cols[name.lower()]

    for c in df.columns:
        c_low = str(c).lower()
        if any(name.lower() in c_low for name in names):
            return c

    return None


def equity_info(df, live_equity):
    df = clean(df)
    time_col = find_col(df, ["timestamp", "time", "date", "datetime"])
    equity_col = find_col(df, ["equity", "account_equity", "portfolio_value"])

    if df.empty or equity_col is None:
        return df, time_col, equity_col, live_equity, live_equity, live_equity, 0.0, 0.0, 0.0

    if time_col:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.dropna(subset=[time_col]).sort_values(time_col)

    df[equity_col] = df[equity_col].apply(to_float)

    current = to_float(df[equity_col].iloc[-1], live_equity)
    start = to_float(df[equity_col].iloc[0], current)
    peak = max(float(df[equity_col].max()), current)
    drawdown = ((peak - current) / peak * 100) if peak else 0.0
    five_run_pnl = current - to_float(df[equity_col].iloc[max(0, len(df) - 5)], current)
    twenty_one_run_pnl = current - to_float(df[equity_col].iloc[max(0, len(df) - 21)], current)

    return df, time_col, equity_col, start, current, peak, drawdown, five_run_pnl, twenty_one_run_pnl


def trade_info(df):
    if df.empty:
        return 0, 0, 0, 0.0, 0.0, 0.0

    df = clean(df)
    pnl_col = find_col(df, ["pnl", "profit", "realized_pnl", "pl"])

    if pnl_col is None:
        return len(df), 0, 0, 0.0, 0.0, 0.0

    pnl = df[pnl_col].apply(to_float)
    wins = int((pnl > 0).sum())
    losses = int((pnl < 0).sum())
    gross_profit = pnl[pnl > 0].sum()
    gross_loss = abs(pnl[pnl < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss else 0.0
    win_rate = wins / max(wins + losses, 1) * 100

    return len(df), wins, losses, win_rate, profit_factor, pnl.sum()


def connect_alpaca():
    api_key = get_secret("ALPACA_API_KEY") or get_secret("PAPER_ALPACA_API_KEY")
    secret_key = get_secret("ALPACA_SECRET_KEY") or get_secret("PAPER_ALPACA_SECRET_KEY")
    paper = str(get_secret("ALPACA_PAPER", "false")).lower() in ["1", "true", "yes", "paper"]

    if not api_key or not secret_key:
        return None, None, [], [], "Missing Alpaca keys", paper

    try:
        client = TradingClient(api_key, secret_key, paper=paper)
        account = client.get_account()

        try:
            clock = client.get_clock()
        except Exception:
            clock = None

        try:
            positions = client.get_all_positions()
        except Exception:
            positions = []

        try:
            orders = client.get_orders()
        except Exception:
            orders = []

        return account, clock, positions, orders, None, paper

    except Exception as exc:
        return None, None, [], [], str(exc), paper


def positions_df_from_api(positions):
    rows = []

    for p in positions:
        rows.append({
            "symbol": getattr(p, "symbol", ""),
            "qty": getattr(p, "qty", ""),
            "entry_price": getattr(p, "avg_entry_price", ""),
            "current_price": getattr(p, "current_price", ""),
            "market_value": getattr(p, "market_value", ""),
            "unrealized_pnl": getattr(p, "unrealized_pl", ""),
            "unrealized_pnl_pct": to_float(getattr(p, "unrealized_plpc", 0)) * 100,
        })

    return pd.DataFrame(rows)


def orders_df_from_api(orders):
    rows = []

    for o in orders:
        rows.append({
            "symbol": getattr(o, "symbol", ""),
            "side": str(getattr(o, "side", "")).replace("OrderSide.", ""),
            "type": str(getattr(o, "type", "")).replace("OrderType.", ""),
            "status": str(getattr(o, "status", "")).replace("OrderStatus.", ""),
            "qty": getattr(o, "qty", ""),
            "limit_price": getattr(o, "limit_price", ""),
            "stop_price": getattr(o, "stop_price", ""),
            "submitted_at": getattr(o, "submitted_at", ""),
        })

    return pd.DataFrame(rows)


def risk_flags(account, clock, positions_df, orders_df, drawdown):
    flags = []

    if account is None:
        flags.append(("bad", "Alpaca connection failed or keys are missing."))

    if clock is not None and not getattr(clock, "is_open", False):
        flags.append(("warn", "Market is closed right now."))

    if drawdown >= 3:
        flags.append(("bad", f"Drawdown is {drawdown:.2f}%. Review risk."))
    elif drawdown >= 1.5:
        flags.append(("warn", f"Drawdown is {drawdown:.2f}%. Watch risk."))

    if not positions_df.empty and orders_df.empty:
        flags.append(("warn", "Open positions found, but no open orders were detected."))

    pnl_pct_col = find_col(positions_df, ["unrealized_pnl_pct", "unrealized_plpc", "pnl_pct"])
    if pnl_pct_col:
        worst_position = positions_df[pnl_pct_col].apply(to_float).min()
        if worst_position <= -2:
            flags.append(("bad", f"One open position is down {worst_position:.2f}%. Check risk."))

    if not flags:
        flags.append(("good", "No major dashboard warnings detected."))

    return flags


def show_flags(flags):
    for level, text in flags:
        emoji = "✅" if level == "good" else "⚠️" if level == "warn" else "🚨"
        css = "good" if level == "good" else "warn" if level == "warn" else "bad"
        st.markdown(
            f"<div class='status-box'><span class='{css}'>{emoji} {text}</span></div>",
            unsafe_allow_html=True
        )


# =========================================
# LOAD LIVE + CSV DATA
# =========================================

account, clock, api_positions, api_orders, api_error, paper = connect_alpaca()

if account:
    equity = to_float(account.equity)
    cash = to_float(account.cash)
    buying_power = to_float(account.buying_power)
    last_equity = to_float(account.last_equity, equity)
    daily_pnl = equity - last_equity
    daily_pct = daily_pnl / last_equity * 100 if last_equity else 0.0
else:
    equity = cash = buying_power = last_equity = daily_pnl = daily_pct = 0.0

equity_raw, equity_file = load_csv("equity")
trades_raw, trades_file = load_csv("trades")
positions_raw, positions_file = load_csv("positions")
orders_raw, orders_file = load_csv("orders")
analytics_raw, analytics_file = load_csv("analytics")
decisions_raw, decisions_file = load_csv("decisions")

positions_live = positions_df_from_api(api_positions)
orders_live = orders_df_from_api(api_orders)

positions_df = positions_live if not positions_live.empty else positions_raw
orders_df = orders_live if not orders_live.empty else orders_raw

(
    equity_df,
    time_col,
    equity_col,
    start_equity,
    current_equity,
    peak_equity,
    drawdown,
    five_run_pnl,
    twenty_one_run_pnl,
) = equity_info(equity_raw, equity)

(
    total_trades,
    wins,
    losses,
    win_rate,
    profit_factor,
    total_realized,
) = trade_info(trades_raw)

flags = risk_flags(account, clock, positions_df, orders_df, drawdown)

market_status = "Open" if clock is not None and getattr(clock, "is_open", False) else "Closed"
mode = "Paper" if paper else "Live"
updated = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

# =========================================
# SIDEBAR
# =========================================

st.sidebar.title("📈 Trading Dashboard")

if api_error:
    st.sidebar.error("Needs Attention")
else:
    st.sidebar.success("System Online")

st.sidebar.markdown("---")
st.sidebar.write(f"Mode: **{mode}**")
st.sidebar.write(f"Market: **{market_status}**")
st.sidebar.write(f"Updated: **{updated}**")
st.sidebar.markdown("---")

st.sidebar.caption("Files detected")
st.sidebar.write(f"Equity: `{equity_file or 'missing'}`")
st.sidebar.write(f"Trades: `{trades_file or 'missing'}`")
st.sidebar.write(f"Positions: `{'Live Alpaca API' if not positions_live.empty else positions_file or 'missing'}`")
st.sidebar.write(f"Orders: `{'Live Alpaca API' if not orders_live.empty else orders_file or 'missing'}`")
st.sidebar.write(f"Decisions: `{decisions_file or 'missing'}`")

# =========================================
# TITLE + TOP METRICS
# =========================================

st.title("📈 Advanced Trading Dashboard")
st.caption("Tracks account value, positions, orders, trade history, bot decisions, and risk warnings.")

if api_error:
    st.error(f"Alpaca connection problem: {api_error}")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    metric_card("Equity", money(equity), f"Today {daily_pct:.2f}%", color_class(daily_pnl))

with c2:
    metric_card("Cash", money(cash), "Available cash")

with c3:
    metric_card("Buying Power", money(buying_power), "Alpaca reported")

with c4:
    metric_card("Today P/L", money(daily_pnl), f"Last equity {money(last_equity)}", color_class(daily_pnl))

with c5:
    dd_color = "bad" if drawdown > 2 else "warn" if drawdown > 1 else "good"
    metric_card("Drawdown", f"{drawdown:.2f}%", f"Peak {money(peak_equity)}", dd_color)

# =========================================
# TABS
# =========================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Overview",
    "📦 Positions / Orders",
    "📊 Trades",
    "🧠 Bot Decisions",
    "⚙️ Health",
])

# =========================================
# OVERVIEW
# =========================================

with tab1:
    left, right = st.columns([2, 1])

    with left:
        st.subheader("📈 Equity Curve")

        if not equity_df.empty and time_col and equity_col:
            fig = px.line(equity_df, x=time_col, y=equity_col, markers=True)
            fig.update_traces(line_width=4)
            fig.update_layout(
                paper_bgcolor="#020617",
                plot_bgcolor="#020617",
                font_color="white",
                height=450,
                margin=dict(l=10, r=10, t=30, b=10),
                yaxis_title="Equity",
                xaxis_title="Time",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No equity_history.csv found yet.")

    with right:
        st.subheader("🚦 Bot Health")
        st.markdown(f"""
        <div class='status-box'>
            <b>Mode:</b> {mode}<br>
            <b>Market:</b> {market_status}<br>
            <b>Refresh:</b> {updated}<br>
        </div>
        """, unsafe_allow_html=True)
        show_flags(flags)

    st.subheader("📌 Performance Snapshot")

    p1, p2, p3, p4 = st.columns(4)

    with p1:
        metric_card("5-Run P/L", money(five_run_pnl), "Last 5 equity points", color_class(five_run_pnl))

    with p2:
        metric_card("21-Run P/L", money(twenty_one_run_pnl), "Last 21 equity points", color_class(twenty_one_run_pnl))

    with p3:
        metric_card("Total Trades", str(total_trades), f"Wins {wins} / Losses {losses}")

    with p4:
        metric_card(
            "Win Rate",
            f"{win_rate:.1f}%",
            f"Profit factor {profit_factor:.2f}",
            "good" if win_rate >= 50 else "warn"
        )

# =========================================
# POSITIONS / ORDERS
# =========================================

with tab2:
    st.subheader("📦 Open Positions")

    if positions_df.empty:
        st.info("No positions detected.")
    else:
        st.dataframe(clean(positions_df), use_container_width=True, hide_index=True)

    st.subheader("📄 Orders")

    if orders_df.empty:
        st.info("No orders detected.")
    else:
        st.dataframe(clean(orders_df), use_container_width=True, hide_index=True)

# =========================================
# TRADES
# =========================================

with tab3:
    st.subheader("🏆 Trade Stats")

    s1, s2, s3, s4, s5 = st.columns(5)

    s1.metric("Total Trades", total_trades)
    s2.metric("Wins", wins)
    s3.metric("Losses", losses)
    s4.metric("Win Rate", f"{win_rate:.1f}%")
    s5.metric("Realized P/L", money(total_realized))

    st.subheader("📒 Trade Journal")

    if trades_raw.empty:
        st.info("No trade history file found yet.")
    else:
        st.dataframe(clean(trades_raw), use_container_width=True, hide_index=True)

    st.subheader("📉 Drawdown Chart")

    if not equity_df.empty and time_col and equity_col:
        dd = equity_df[[time_col, equity_col]].copy()
        dd["peak"] = dd[equity_col].cummax()
        dd["drawdown_pct"] = ((dd[equity_col] - dd["peak"]) / dd["peak"]) * 100

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=dd[time_col],
                y=dd["drawdown_pct"],
                mode="lines+markers",
                name="Drawdown %",
            )
        )
        fig.update_layout(
            paper_bgcolor="#020617",
            plot_bgcolor="#020617",
            font_color="white",
            height=350,
            margin=dict(l=10, r=10, t=30, b=10),
            yaxis_title="Drawdown %",
            xaxis_title="Time",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Drawdown chart needs equity_history.csv.")

# =========================================
# BOT DECISIONS
# =========================================

with tab4:
    st.subheader("🧠 Why Did The Bot Trade?")

    if decisions_raw.empty:
        st.warning("No decision log found yet. Add bot_decisions.csv or decision_log.csv from your bot.")
        st.code(
            "timestamp,symbol,decision,score,strength,volatility,extension,reason",
            language="text",
        )
    else:
        st.dataframe(clean(decisions_raw), use_container_width=True, hide_index=True)

    st.subheader("🚨 Warning Detector")
    show_flags(flags)

# =========================================
# HEALTH / FILE CHECK
# =========================================

with tab5:
    st.subheader("⚙️ Dashboard Inputs")

    input_rows = [
        {"Data Type": "Equity History", "File Used": equity_file or "Missing", "Rows": len(equity_raw)},
        {"Data Type": "Trade History", "File Used": trades_file or "Missing", "Rows": len(trades_raw)},
        {
            "Data Type": "Positions",
            "File Used": "Live Alpaca API" if not positions_live.empty else positions_file or "Missing",
            "Rows": len(positions_df),
        },
        {
            "Data Type": "Orders",
            "File Used": "Live Alpaca API" if not orders_live.empty else orders_file or "Missing",
            "Rows": len(orders_df),
        },
        {"Data Type": "Analytics", "File Used": analytics_file or "Missing", "Rows": len(analytics_raw)},
        {"Data Type": "Decision Log", "File Used": decisions_file or "Missing", "Rows": len(decisions_raw)},
    ]

    st.dataframe(pd.DataFrame(input_rows), use_container_width=True, hide_index=True)

    st.subheader("Recommended CSV Columns")
    st.code("""equity_history.csv: timestamp,equity,cash,buying_power
trade_history.csv: timestamp,symbol,side,qty,entry_price,exit_price,pnl,pnl_pct,reason
positions_snapshot.csv: timestamp,symbol,qty,entry_price,current_price,market_value,unrealized_pnl,unrealized_pnl_pct
orders_snapshot.csv: timestamp,symbol,side,type,status,qty,limit_price,stop_price
bot_decisions.csv: timestamp,symbol,decision,score,strength,volatility,extension,reason
""", language="text")

st.success("Dashboard Running Successfully")
