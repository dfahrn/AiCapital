"""Order sizing against the 5% cap and buying power."""
import types
from unittest.mock import MagicMock
from hedgefund.trading.paper_trader import PaperTrader

def trader(cash=100000, bp=100000, price=107.0, positions=()):
    t = PaperTrader.__new__(PaperTrader)
    t.db=None; t.max_position_size=0.05; t.initial_capital=cash
    t.cash=cash; t.buying_power=bp; t.positions={}
    t.alpaca=MagicMock()
    t.alpaca.get_account.return_value=types.SimpleNamespace(cash=str(cash), buying_power=str(bp))
    t.alpaca.list_positions.return_value=list(positions)
    t.alpaca.submit_order.return_value=types.SimpleNamespace(id="o1", status="accepted")
    t.market_data=MagicMock(); t.market_data.get_current_price.return_value=price
    return t

res=[]
def check(label, cond, detail=""):
    res.append(cond); print(("PASS" if cond else "FAIL"), f"{label:48}", detail)

# The live failure: CVX at 106.97% of portfolio. $5,000 / $107 = 46 shares.
t = trader(price=107.0)
r = t.execute_order({"symbol":"CVX","side":"buy","quantity":1000})
qty = t.alpaca.submit_order.call_args.kwargs["qty"] if t.alpaca.submit_order.called else None
check("oversized order is sized down, not rejected", r["success"] is True, f"submitted qty={qty}")
check("  sized to the 5% cap", qty == 46, f"$5,000/$107 = 46")
check("  and its value fits", qty*107 <= 5000, f"${qty*107:,.2f} <= $5,000")

# A suggestion already within the cap is untouched.
t = trader(price=107.0)
t.execute_order({"symbol":"CVX","side":"buy","quantity":10})
check("in-budget order passes through unchanged", t.alpaca.submit_order.call_args.kwargs["qty"] == 10)

# Buying power below the cap becomes the binding constraint.
t = trader(cash=100000, bp=1000, price=107.0)
t.execute_order({"symbol":"CVX","side":"buy","quantity":1000})
check("buying power binds when lower than cap",
      t.alpaca.submit_order.call_args.kwargs["qty"] == 9, "$1,000/$107 = 9")

# Existing holding eats into the room left.
pos = types.SimpleNamespace(symbol="CVX", qty="40", avg_entry_price="107",
                            current_price="107", market_value="4280",
                            cost_basis="4280", unrealized_pl="0", unrealized_plpc="0")
t = trader(price=107.0, positions=[pos])
t.execute_order({"symbol":"CVX","side":"buy","quantity":100})
# portfolio = 100000 cash + 4280 held = 104280; cap = 5214; minus 4280 held = 934 -> 8 shares
check("existing position reduces remaining room",
      t.alpaca.submit_order.call_args.kwargs["qty"] == 8, "room left $934 -> 8 shares")

# A stock too expensive for any whole share within the cap is rejected.
t = trader(cash=10000, bp=10000, price=900.0)   # cap = $500, share = $900
r = t.execute_order({"symbol":"XPNS","side":"buy","quantity":1})
check("rejects when not even one share fits", r["success"] is False and not t.alpaca.submit_order.called,
      r["message"][:46])

# Sells are not size-capped.
sp = types.SimpleNamespace(symbol="AAPL", qty="500", avg_entry_price="100",
                           current_price="100", market_value="50000",
                           cost_basis="50000", unrealized_pl="0", unrealized_plpc="0")
t = trader(price=100.0, positions=[sp])
r = t.execute_order({"symbol":"AAPL","side":"sell","quantity":500})
check("sell of full position is not capped", r["success"] is True and t.alpaca.submit_order.call_args.kwargs["qty"] == 500)

print(); print(f"{sum(res)}/{len(res)} passed")
