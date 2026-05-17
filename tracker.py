from alpaca.trading.client import TradingClient
import pandas as pd
import os
from datetime import datetime

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
last_equity = float(account.last_equity)

daily_pnl = equity - last_equity

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =========================================
# SAVE EQUITY HISTORY
# =========================================

equity_row = pd.DataFrame([{
    "timestamp": timestamp,
    "equity": equity,
    "cash": cash,
    "buying_power": buying_power,
    "daily_pnl": daily_pnl
}])

if os.path.exists("equity_history.csv"):

    old = pd.read_csv("equity_history.csv")

    equity_row = pd.concat(
        [old, equity_row],
        ignore_index=True
    )

equity_row.to_csv(
    "equity_history.csv",
    index=False
)

# =========================================
# POSITIONS TRACKING
# =========================================

positions = client.get_all_positions()

position_rows = []

for p in positions:

    position_rows.append({
        "timestamp": timestamp,
        "symbol": p.symbol,
        "qty": p.qty,
        "market_value": float(p.market_value),
        "unrealized_pl": float(p.unrealized_pl)
    })

positions_df = pd.DataFrame(position_rows)

positions_df.to_csv(
    "positions_snapshot.csv",
    index=False
)

# =========================================
# ORDERS TRACKING
# =========================================

orders = client.get_orders()

order_rows = []

for o in orders[:50]:

    order_rows.append({
        "timestamp": timestamp,
        "symbol": o.symbol,
        "side": str(o.side),
        "qty": o.qty,
        "status": str(o.status)
    })

orders_df = pd.DataFrame(order_rows)

orders_df.to_csv(
    "orders_snapshot.csv",
    index=False
)

# =========================================
# TRADE ANALYTICS
# =========================================

total_positions = len(positions)

exposure = 0

for p in positions:
    exposure += abs(float(p.market_value))

analytics = pd.DataFrame([{
    "timestamp": timestamp,
    "equity": equity,
    "daily_pnl": daily_pnl,
    "open_positions": total_positions,
    "total_exposure": exposure
}])

analytics.to_csv(
    "analytics_snapshot.csv",
    index=False
)

print("Tracking update complete.")
