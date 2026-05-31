# dashboard.py

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from alpaca.trading.client import TradingClient

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📈",
    layout="wide",
)

# =========================================================
# STYLE
# =========================================================

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

.info-box {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# CSV FILES
# =========================================================

DATA_FILES = {
    "equity": ["equity_history.csv", "data/equity_history.csv"],
    "trades": ["trade_history.csv", "trades.csv", "data/trade_history.csv"],
    "positions": ["positions_snapshot.csv", "positions.csv", "data/positions_snapshot.csv"],
    "orders": ["orders_snapshot.csv", "orders.csv", "data/orders_snapshot.csv"],
    "analytics": ["analytics_snapshot.csv", "analytics.csv", "data/analytics_snapshot.csv"],
}

# =========================================================
# HELPERS
# =========================================================

def get_secret(name, default=None):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass

    return os.getenv(name, default)


@st.cache_data(ttl=45)
def load_csv(kind):
    for file_name in DATA_FILES.get(kind, []):
        path = Path(file_name)

        if path.exists():
            try:
                return pd.read_csv(path), file_name
            except Exception as exc:
                return pd.DataFrame(), f"{file_name} error: {exc}"

    return pd.DataFrame(), None


def clean_columns(df):
    if df.empty:
        return df

    out = df.copy()
    out.columns = [
        str(c).strip().lower().replace(" ", "_")
        for c in out.columns
    ]
    return out


def to_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default

        return float(
            str(value)
            .replace("$", "")
            .replace(",", "")
            .replace("%", "")
            .replace("+", "")
        )

    except Exception:
        return default


def money(value):
    return f"${to_float(value):,.2f}"


def percent(value):
    return f"{to_float(value):.2f}%"


def good_bad_class(value):
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

    lower_map = {
        str(c).lower(): c
        for c in df.columns
    }

    for name in names:
        if name.lower() in lower_map:
            return lower_map[name.lower()]

    for c in df.columns:
        c_low = str(c).lower()
        if any(name.lower() in c_low for name in names):
            return c

    return None


# =========================================================
# ALPACA
# =========================================================

def connect_alpaca():
    api_key = get_secret("ALPACA_API_KEY") or get_secret("PAPER_ALPACA_API_KEY")
    secret_key = get_secret("ALPACA_SECRET_KEY") or get_secret("PAPER_ALPACA_SECRET_KEY")

    paper = str(
        get_secret("ALPACA_PAPER", "false")
    ).lower() in ["1", "true", "yes", "paper"]

    if not api_key or not secret_key:
        return None, None, [], [], "Missing Alpaca API keys", paper

    try:
        client = TradingClient(
            api_key,
            secret_key,
            paper=paper,
        )

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


def positions_to_df(positions):
    rows = []

    for p in positions:
        rows.append({
            "symbol": getattr(p, "symbol", ""),
            "qty": getattr(p, "qty", ""),
            "entry_price": getattr(p, "avg_entry_price", ""),
            "current_price": getattr(p, "current_price", ""),
            "market_value": getattr(p, "market_value", ""),
            "unrealized_pnl": getattr(p, "unrealized_pl", ""),
            "unrealized_pnl_pct": to_float(
                getattr(p, "unrealized_plpc", 0)
            ) * 100,
        })

    return pd.DataFrame(rows)


def orders_to_df(orders):
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


# =========================================================
# EQUITY ANALYTICS
# =========================================================

def parse_equity_history(df, live_equity):
    df = clean_columns(df)

    time_col = find_col(df, ["timestamp", "time", "date", "datetime"])
    equity_col = find_col(df, ["equity", "account_equity", "portfolio_value"])

    if df.empty or equity_col is None:
        return df, time_col, equity_col, {
            "start": live_equity,
            "current": live_equity,
            "peak": live_equity,
            "drawdown": 0.0,
            "five_run_pnl": 0.0,
            "twenty_one_run_pnl": 0.0,
        }

    if time_col:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.dropna(subset=[time_col]).sort_values(time_col)

    df[equity_col] = df[equity_col].apply(to_float)

    current = live_equity if live_equity > 0 else to_float(df[equity_col].iloc[-1])
    start = to_float(df[equity_col].iloc[0], current)
    peak = max(float(df[equity_col].max()), current)

    drawdown = ((peak - current) / peak * 100) if peak else 0.0

    five_index = max(0, len(df) - 5)
    twenty_one_index = max(0, len(df) - 21)

    five_run_pnl = current - to_float(df[equity_col].iloc[five_index], current)
    twenty_one_run_pnl = current - to_float(df[equity_col].iloc[twenty_one_index], current)

    return df, time_col, equity_col, {
        "start": start,
        "current": current,
        "peak": peak,
        "drawdown": drawdown,
        "five_run_pnl": five_run_pnl,
        "twenty_one_run_pnl": twenty_one_run_pnl,
    }


# =========================================================
# TRADE ANALYTICS
# =========================================================

def parse_trade_history(df):
    """
    Dashboard-only logic.

    If trade_history.csv has a real pnl column, calculate wins/losses.
    If it does not, do NOT fake win rate.
    """
    if df.empty:
        return clean_columns(df), {
            "total_rows": 0,
            "has_pnl": False,
            "wins": None,
            "losses": None,
            "win_rate": None,
            "profit_factor": None,
            "realized_pnl": None,
            "buy_count": 0,
            "sell_count": 0,
        }

    df = clean_columns(df)

    side_col = find_col(df, ["side", "order_side", "type"])
    pnl_col = find_col(df, ["pnl", "profit", "realized_pnl", "pl", "p/l"])

    buy_count = 0
    sell_count = 0

    if side_col:
        sides = df[side_col].astype(str).str.lower()
        buy_count = int(sides.str.contains("buy").sum())
        sell_count = int(sides.str.contains("sell").sum())

    if pnl_col is None:
        return df, {
            "total_rows": len(df),
            "has_pnl": False,
            "wins": None,
            "losses": None,
            "win_rate": None,
            "profit_factor": None,
            "realized_pnl": None,
            "buy_count": buy_count,
            "sell_count": sell_count,
        }

    pnl = df[pnl_col].apply(to_float)

    wins = int((pnl > 0).sum())
    losses = int((pnl < 0).sum())

    gross_profit = pnl[pnl > 0].sum()
    gross_loss = abs(pnl[pnl < 0].sum())

    win_rate = wins / max(wins + losses, 1) * 100
    profit_factor = gross_profit / gross_loss if gross_loss else None
    realized_pnl = pnl.sum()

    return df, {
        "total_rows": len(df),
        "has_pnl": True,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "realized_pnl": realized_pnl,
        "buy_count": buy_count,
        "sell_count": sell_count,
    }


# =========================================================
# RISK WARNINGS
# =========================================================

def risk_flags(account, clock, positions_df, orders_df, drawdown):
    flags = []

    if account is None:
        flags.append(("bad", "Alpaca connection failed or API keys are missing."))

    if clock is not None and not getattr(clock, "is_open", False):
        flags.append(("warn", "Market is closed right now."))

    if drawdown >= 3:
        flags.append(("bad", f"Drawdown is {drawdown:.2f}%. Review risk."))
    elif drawdown >= 1.5:
        flags.append(("warn", f"Drawdown is {drawdown:.2f}%. Watch risk."))
    else:
        flags.append(("good", f"Drawdown is controlled at {drawdown:.2f}%."))

    if not positions_df.empty and orders_df.empty:
        flags.append(("warn", "Open positions found, but no open orders were detected."))

    if not positions_df.empty:
        pnl_pct_col = find_col(
            positions_df,
            ["unrealized_pnl_pct", "unrealized_plpc", "pnl_pct"]
        )

        if pnl_pct_col:
            worst = positions_df[pnl_pct_col].apply(to_float).min()

            if worst <= -2:
                flags.append(("bad", f"One open position is down {worst:.2f}%. Check risk."))

    return flags


def show_flags(flags):
    for level, text in flags:
        emoji = "✅" if level == "good" else "⚠️" if level == "warn" else "🚨"
        css = "good" if level == "good" else "warn" if level == "warn" else "bad"

        st.markdown(
            f"<div class='status-box'><span class='{css}'>{emoji} {text}</span></div>",
            unsafe_allow_html=True,
        )


# =========================================================
# LOAD DATA
# =========================================================

account, clock, api_positions, api_orders, api_error, paper = connect_alpaca()

if account:
    equity = to_float(account.equity)
    cash = to_float(account.cash)
    buying_power = to_float(account.buying_power)
    last_equity = to_float(account.last_equity, equity)
    daily_pnl = equity - last_equity
    daily_pct = daily_pnl / last_equity * 100 if last_equity else 0.0
else:
    equity = 0.0
    cash = 0.0
    buying_power = 0.0
    last_equity = 0.0
    daily_pnl = 0.0
    daily_pct = 0.0

equity_raw, equity_file = load_csv("equity")
trades_raw, trades_file = load_csv("trades")
positions_raw, positions_file = load_csv("positions")
orders_raw, orders_file = load_csv("orders")
analytics_raw, analytics_file = load_csv("analytics")

positions_live = positions_to_df(api_positions)
orders_live = orders_to_df(api_orders)

positions_df = positions_live if not positions_live.empty else positions_raw
orders_df = orders_live if not orders_live.empty else orders_raw

equity_df, time_col, equity_col, equity_stats = parse_equity_history(
    equity_raw,
    equity,
)

trades_df, trade_stats = parse_trade_history(trades_raw)

market_status = "Open" if clock is not None and getattr(clock, "is_open", False) else "Closed"
mode = "Paper" if paper else "Live"
updated = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

flags = risk_flags(
    account,
    clock,
    clean_columns(positions_df),
    clean_columns(orders_df),
    equity_stats["drawdown"],
)

# =========================================================
# SIDEBAR
# =========================================================

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
st.sidebar.write("Decisions: `dashboard-only mode`")

# =========================================================
# TITLE
# =========================================================

st.title("📈 Advanced Trading Dashboard")
st.caption("Dashboard-only version. No bot code changes required.")

if api_error:
    st.error(f"Alpaca connection problem: {api_error}")

# =========================================================
# TOP METRICS
# =========================================================

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    metric_card(
        "Equity",
        money(equity),
        f"Today {daily_pct:.2f}%",
        good_bad_class(daily_pnl),
    )

with c2:
    metric_card(
        "Cash",
        money(cash),
        "Available cash",
    )

with c3:
    metric_card(
        "Buying Power",
        money(buying_power),
        "Alpaca reported",
    )

with c4:
    metric_card(
        "Today P/L",
        money(daily_pnl),
        f"Last equity {money(last_equity)}",
        good_bad_class(daily_pnl),
    )

with c5:
    dd = equity_stats["drawdown"]

    if dd > 2:
        dd_color = "bad"
    elif dd > 1:
        dd_color = "warn"
    else:
        dd_color = "good"

    metric_card(
        "Drawdown",
        f"{dd:.2f}%",
        f"Peak {money(equity_stats['peak'])}",
        dd_color,
    )

# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Overview",
    "📦 Positions / Orders",
    "📊 Trades",
    "🧠 Dashboard Notes",
    "⚙️ Health",
])

# =========================================================
# OVERVIEW
# =========================================================

with tab1:
    left, right = st.columns([2, 1])

    with left:
        st.subheader("📈 Equity Curve")

        if not equity_df.empty and time_col and equity_col:
            fig = px.line(
                equity_df,
                x=time_col,
                y=equity_col,
                markers=True,
            )

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
            st.warning("No usable equity_history.csv found yet.")

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
        metric_card(
            "5-Run P/L",
            money(equity_stats["five_run_pnl"]),
            "Based on equity_history.csv",
            good_bad_class(equity_stats["five_run_pnl"]),
        )

    with p2:
        metric_card(
            "21-Run P/L",
            money(equity_stats["twenty_one_run_pnl"]),
            "Based on equity_history.csv",
            good_bad_class(equity_stats["twenty_one_run_pnl"]),
        )

    with p3:
        metric_card(
            "Trade Rows",
            str(trade_stats["total_rows"]),
            f"Buys {trade_stats['buy_count']} / Sells {trade_stats['sell_count']}",
        )

    with p4:
        if trade_stats["has_pnl"]:
            metric_card(
                "Win Rate",
                f"{trade_stats['win_rate']:.1f}%",
                f"Profit factor {trade_stats['profit_factor'] or 0:.2f}",
                "good" if trade_stats["win_rate"] >= 50 else "warn",
            )
        else:
            metric_card(
                "Win Rate",
                "N/A",
                "trade_history.csv has no P/L column",
                "warn",
            )

# =========================================================
# POSITIONS / ORDERS
# =========================================================

with tab2:
    st.subheader("📦 Open Positions")

    positions_clean = clean_columns(positions_df)

    if positions_clean.empty:
        st.info("No open positions detected.")
    else:
        st.dataframe(
            positions_clean,
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("📄 Orders")

    orders_clean = clean_columns(orders_df)

    if orders_clean.empty:
        st.info("No open orders detected.")
    else:
        st.dataframe(
            orders_clean,
            use_container_width=True,
            hide_index=True,
        )

# =========================================================
# TRADES
# =========================================================

with tab3:
    st.subheader("🏆 Trade Stats")

    t1, t2, t3, t4, t5 = st.columns(5)

    t1.metric("Trade Rows", trade_stats["total_rows"])
    t2.metric("Buy Rows", trade_stats["buy_count"])
    t3.metric("Sell Rows", trade_stats["sell_count"])

    if trade_stats["has_pnl"]:
        t4.metric("Win Rate", f"{trade_stats['win_rate']:.1f}%")
        t5.metric("Realized P/L", money(trade_stats["realized_pnl"]))
    else:
        t4.metric("Win Rate", "N/A")
        t5.metric("Realized P/L", "N/A")

    if not trade_stats["has_pnl"]:
        st.warning(
            "Your trade_history.csv does not have a real P/L column, so the dashboard should NOT show fake wins/losses."
        )

    st.subheader("📒 Trade History")

    if trades_df.empty:
        st.info("No trade_history.csv found yet.")
    else:
        st.dataframe(
            trades_df,
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("📉 Drawdown Chart")

    if not equity_df.empty and time_col and equity_col:
        dd_df = equity_df[[time_col, equity_col]].copy()
        dd_df["peak"] = dd_df[equity_col].cummax()
        dd_df["drawdown_pct"] = ((dd_df[equity_col] - dd_df["peak"]) / dd_df["peak"]) * 100

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=dd_df[time_col],
                y=dd_df["drawdown_pct"],
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

# =========================================================
# DASHBOARD NOTES
# =========================================================

with tab4:
    st.subheader("🧠 Dashboard Notes")

    st.markdown("""
    <div class="info-box">
        <b>This is dashboard-only mode.</b><br><br>
        You said you do not want to change the actual trading bot, so this dashboard will not expect
        <code>bot_decisions.csv</code>. That means it can show account data, equity, positions, orders,
        trade rows, and drawdown — but it cannot know the exact reason the bot bought or skipped a symbol.
    </div>
    """, unsafe_allow_html=True)

    st.subheader("What the dashboard can know without changing the bot")

    st.write("- Current Alpaca equity")
    st.write("- Current cash")
    st.write("- Buying power")
    st.write("- Open positions")
    st.write("- Open orders")
    st.write("- Equity curve, if equity_history.csv exists")
    st.write("- Trade rows, if trade_history.csv exists")
    st.write("- Win rate only if trade_history.csv has a real P/L column")

    st.subheader("What it cannot know without bot logging")

    st.write("- Why AMD was skipped")
    st.write("- Why META was bought")
    st.write("- Which symbols failed filters")
    st.write("- Whether a stock was skipped because it was too extended")
    st.write("- Whether a stock was skipped because of exposure limits")

# =========================================================
# HEALTH
# =========================================================

with tab5:
    st.subheader("⚙️ Dashboard Inputs")

    input_rows = [
        {
            "Data Type": "Equity History",
            "File Used": equity_file or "Missing",
            "Rows": len(equity_raw),
        },
        {
            "Data Type": "Trade History",
            "File Used": trades_file or "Missing",
            "Rows": len(trades_raw),
        },
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
        {
            "Data Type": "Analytics",
            "File Used": analytics_file or "Missing",
            "Rows": len(analytics_raw),
        },
    ]

    st.dataframe(
        pd.DataFrame(input_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Recommended Files")

    st.code("""equity_history.csv: timestamp,equity,cash,buying_power
trade_history.csv: timestamp,symbol,side,qty,price,amount,pnl
positions_snapshot.csv: timestamp,symbol,qty,entry_price,current_price,market_value,unrealized_pnl,unrealized_pnl_pct
orders_snapshot.csv: timestamp,symbol,side,type,status,qty,limit_price,stop_price
""", language="text")

st.success("Dashboard Running Successfully")
