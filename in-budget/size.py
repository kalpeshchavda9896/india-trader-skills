#!/usr/bin/env python3
"""in-budget: turn a plan into an exact quantity, inside limits you set once.

  size.py cash [--write]                    sizes trader/plan.json (from /in-exit)
  size.py cash --symbol RELIANCE --entry 1480 --stop 1465 --target 1510 --write
  size.py option --underlying NIFTY --premium 100 --stop-premium 70 --target-premium 160 --write
  size.py option --underlying NIFTY --premium 100 --delta 0.5 --underlying-stop-pts 60
  size.py config                            show the limits in force

The stop decides the size: the further away the stop, the fewer shares or lots.
Sizing to a maximum loss keeps each loss small. It does not make a trade win.
Edit limits in trader/config.json (see config.example.json).
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inmkt as m  # noqa: E402


def charges(cfg, buy_value, sell_value):
    """Rough round trip: 2 x flat brokerage + a % of turnover. Edit both in config."""
    return 2 * cfg["brokerage_per_order_inr"] + cfg["other_charges_pct"] / 100.0 * (buy_value + sell_value)


def size_cash(cfg, symbol, entry, stop, target):
    risk = entry - stop
    if risk <= 0:
        m.die("The stop must be below the entry (this tool sizes long trades only).")
    usable = cfg["capital_inr"] * (1 - cfg["cash_buffer_pct"] / 100.0)
    limits = {
        "max loss per trade (%s)" % m.inr(cfg["max_loss_per_trade_inr"], 0): int(cfg["max_loss_per_trade_inr"] // risk),
        "cash after the %g%% buffer (%s)" % (cfg["cash_buffer_pct"], m.inr(usable, 0)): int(usable // entry),
        "max position %g%% of capital" % cfg["max_position_pct"]: int(cfg["capital_inr"] * cfg["max_position_pct"] / 100.0 // entry),
    }
    binding = min(limits, key=limits.get)
    qty = max(0, limits[binding])
    out = {"kind": "cash", "symbol": symbol, "side": "buy", "qty": qty, "entry": round(entry, 2),
           "stop": round(stop, 2), "target": round(target, 2) if target else None}
    print("%s: entry %s, stop %s, risk %s a share" % (symbol, m.inr(entry), m.inr(stop), m.inr(risk)))
    for k, v in limits.items():
        print("  limit by %-42s %d shares%s" % (k, v, "   <- binds" if k == binding else ""))
    if qty == 0:
        print("RESULT: 0 shares. One share already breaks a limit (%s)." % binding)
        return out, 1
    cost = qty * entry
    loss = qty * risk
    c = charges(cfg, cost, qty * stop)
    out.update(cost=round(cost, 2), max_loss=round(loss, 2), est_charges=round(c, 2),
               max_loss_with_charges=round(loss + c, 2), capital=cfg["capital_inr"])
    print("RESULT: buy %d shares = %s (%.0f%% of capital)" % (qty, m.inr(cost), cost / cfg["capital_inr"] * 100))
    print("  if the stop fills at %s you lose about %s (+ about %s charges)" % (m.inr(stop), m.inr(loss), m.inr(c)))
    if target:
        gain = qty * (target - entry)
        cg = charges(cfg, cost, qty * target)
        out.update(max_gain=round(gain, 2), reward_risk=round((target - entry) / risk, 2))
        print("  if the target fills at %s you make about %s, about %s after charges"
              % (m.inr(target), m.inr(gain), m.inr(gain - cg)))
        if gain - cg <= 0:
            print("  WARNING: charges eat the whole gain. This trade is too small to be worth it.")
    return out, 0


def size_option(cfg, a):
    u = a.underlying.upper()
    lot = a.lot or cfg["lot_sizes"].get(u)
    if not lot:
        m.die("no lot size for %s. Pass --lot N (check your broker app; NSE revises lots)." % u)
    p = a.premium
    if a.stop_premium is not None:
        sp = a.stop_premium
    elif a.delta and a.underlying_stop_pts:
        sp = p - a.delta * a.underlying_stop_pts
        print("Estimated stop premium %s = premium - delta %.2f x %g points (a rough guess: delta changes)"
              % (m.inr(sp), a.delta, a.underlying_stop_pts))
    else:
        m.die("give --stop-premium, or --delta and --underlying-stop-pts")
    per_unit = p - sp
    if per_unit <= 0:
        m.die("The stop premium must be below the premium you pay.")
    per_lot_loss = per_unit * lot
    per_lot_cost = p * lot
    usable = cfg["capital_inr"] * (1 - cfg["cash_buffer_pct"] / 100.0)
    by_loss = int(cfg["max_loss_per_trade_inr"] // per_lot_loss)
    by_cash = int(usable // per_lot_cost)
    lots = max(0, min(by_loss, by_cash))
    out = {"kind": "option", "underlying": u, "option": a.contract or u, "side": "buy", "lots": lots,
           "lot_size": lot, "qty": lots * lot, "entry": p, "stop": round(sp, 2),
           "target": a.target_premium, "expiry": a.expiry, "capital": cfg["capital_inr"]}
    print("%s option, lot size %d: premium %s, stop premium %s" % (u, lot, m.inr(p), m.inr(sp)))
    print("  one lot costs %s and loses %s if the stop fills" % (m.inr(per_lot_cost), m.inr(per_lot_loss)))
    print("  lots by max loss (%s): %d   lots by cash after buffer (%s): %d"
          % (m.inr(cfg["max_loss_per_trade_inr"], 0), by_loss, m.inr(usable, 0), by_cash))
    if lots == 0:
        need_loss = per_lot_loss
        need_cash = per_lot_cost / (1 - cfg["cash_buffer_pct"] / 100.0)
        print("RESULT: 0 lots. One lot does not fit your limits.")
        if by_loss == 0:
            print("  One lot risks %s, but your limit is %s. The stop is too wide for this account." % (m.inr(need_loss, 0), m.inr(cfg["max_loss_per_trade_inr"], 0)))
        if by_cash == 0:
            print("  One lot needs about %s of capital; you have %s." % (m.inr(need_cash, 0), m.inr(cfg["capital_inr"], 0)))
        print("  Raising the limit is not the fix. Consider a cash-segment ETF or paper trading.")
        return out, 1
    cost = lots * per_lot_cost
    loss = lots * per_lot_loss
    c = 2 * cfg["brokerage_per_order_inr"] + cfg["other_charges_pct"] / 100.0 * (cost + lots * lot * sp)
    out.update(cost=round(cost, 2), max_loss=round(loss, 2), est_charges=round(c, 2),
               max_loss_with_charges=round(loss + c, 2))
    print("RESULT: buy %d lot(s) = %d units, cost %s (%.0f%% of capital)" % (lots, lots * lot, m.inr(cost), cost / cfg["capital_inr"] * 100))
    print("  if the stop fills you lose about %s (+ about %s charges)" % (m.inr(loss), m.inr(c)))
    if a.target_premium:
        gain = (a.target_premium - p) * lots * lot
        out.update(max_gain=round(gain, 2), reward_risk=round((a.target_premium - p) / per_unit, 2))
        print("  at the target premium %s you make about %s (reward:risk %.2f)"
              % (m.inr(a.target_premium), m.inr(gain), out["reward_risk"]))
    print("  Option buyers also lose value to time every day. If the premium has not moved in "
          "2-3 sessions, the plan says sell.")
    print("  The max loss is the whole premium if the option expires worthless, "
          "and a gap can skip a stop.")
    return out, 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("mode", choices=["cash", "option", "config"])
    ap.add_argument("--symbol")
    ap.add_argument("--entry", type=float)
    ap.add_argument("--stop", type=float)
    ap.add_argument("--target", type=float)
    ap.add_argument("--underlying", default="NIFTY")
    ap.add_argument("--contract", help="e.g. 'NIFTY 25900 CE' (for the ticket)")
    ap.add_argument("--expiry", help="YYYY-MM-DD")
    ap.add_argument("--premium", type=float)
    ap.add_argument("--stop-premium", type=float)
    ap.add_argument("--target-premium", type=float)
    ap.add_argument("--delta", type=float)
    ap.add_argument("--underlying-stop-pts", type=float)
    ap.add_argument("--lot", type=int)
    ap.add_argument("--write", action="store_true", help="write trader/orders.json")
    a = ap.parse_args()
    cfg = m.load_config()
    if a.mode == "config":
        for k, v in cfg.items():
            print("%-24s %s" % (k, v))
        return 0
    if a.mode == "cash":
        plan = m.load_json("plan.json", {}) or {}
        sym = (a.symbol or plan.get("symbol") or "").upper()
        entry = a.entry if a.entry is not None else plan.get("entry")
        stop = a.stop if a.stop is not None else plan.get("stop")
        target = a.target if a.target is not None else plan.get("target")
        if not sym or entry is None or stop is None:
            m.die("need a plan (/in-exit plan --write) or --symbol --entry --stop")
        if sym in [b.upper() for b in cfg["blocked"]]:
            m.die("%s is on your blocked list." % sym)
        out, code = size_cash(cfg, sym, entry, stop, target)
    else:
        if not cfg["allow_options"]:
            m.die("allow_options is false in trader/config.json")
        if a.premium is None:
            m.die("give --premium (what one unit of the option costs)")
        out, code = size_option(cfg, a)
    if a.write and code == 0:
        out["date"] = m.now_ist().strftime("%Y-%m-%d")
        print("wrote", m.save_json("orders.json", out))
    print(m.DISCLAIMER)
    return code


if __name__ == "__main__":
    sys.exit(main())
