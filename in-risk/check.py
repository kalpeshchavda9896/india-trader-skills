#!/usr/bin/env python3
"""in-risk: check a proposed trade against your limits. PASS, WARN or BLOCK.

  check.py                       checks trader/orders.json (from /in-budget --write)
  check.py --orders FILE
  check.py --now "2026-11-23 10:30"

Reads trader/config.json for the limits and trader/journal.json (from /in-ticket)
for today's trades and losses. It cannot place or cancel anything.
Exit code: 0 = PASS or WARN only, 2 = at least one BLOCK.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inmkt as m  # noqa: E402


def check(o, cfg, journal, now):
    res = []  # (level, name, text)

    def add(level, name, text):
        res.append((level, name, text))

    day = now.strftime("%Y-%m-%d")
    if o.get("date") and o["date"] != day:
        add("BLOCK", "stale", "this order is from %s, not today (%s). Make a new one." % (o["date"], day))
    kind = o.get("kind")
    if kind not in ("cash", "option"):
        add("BLOCK", "format", "orders.json needs kind cash or option")
        return res
    sym = (o.get("symbol") or o.get("underlying") or "").upper()
    if sym in [b.upper() for b in cfg["blocked"]]:
        add("BLOCK", "blocked", "%s is on your blocked list" % sym)
    if kind == "option" and not cfg["allow_options"]:
        add("BLOCK", "options", "allow_options is false in your config")
    if not o.get("qty") or o["qty"] <= 0:
        add("BLOCK", "size", "quantity is zero")
    if kind == "option" and o.get("qty") and o.get("lot_size") and o["qty"] % o["lot_size"]:
        add("BLOCK", "lot", "quantity %d is not a whole number of %d-unit lots" % (o["qty"], o["lot_size"]))
    if cfg["require_stop"] and not o.get("stop"):
        add("BLOCK", "stop", "no stop-loss on the plan")
    entry, stop, target = o.get("entry"), o.get("stop"), o.get("target")
    if entry and stop and stop >= entry:
        add("BLOCK", "stop", "stop %s is not below entry %s" % (stop, entry))
    cost = o.get("cost") or (o.get("qty", 0) * (entry or 0))
    cap = cfg["capital_inr"]
    if cost > cap * (1 - cfg["cash_buffer_pct"] / 100.0) + 1e-6:
        add("BLOCK", "cash", "cost %s leaves less than the %g%% cash buffer" % (m.inr(cost, 0), cfg["cash_buffer_pct"]))
    if kind == "cash" and cost > cap * cfg["max_position_pct"] / 100.0 + 1e-6:
        add("BLOCK", "position", "bigger than %g%% of capital" % cfg["max_position_pct"])
    loss = o.get("max_loss") or ((entry - stop) * o.get("qty", 0) if entry and stop else 0)
    if loss > cfg["max_loss_per_trade_inr"] + 1e-6:
        add("BLOCK", "loss", "if the stop fills you lose %s, over your %s limit" % (m.inr(loss, 0), m.inr(cfg["max_loss_per_trade_inr"], 0)))
    rr = o.get("reward_risk") or ((target - entry) / (entry - stop) if entry and stop and target and entry > stop else None)
    if rr is None:
        add("WARN", "target", "no target, so reward:risk is unknown")
    elif rr < cfg["min_reward_risk"]:
        add("WARN", "reward:risk", "%.2f is under your minimum of %g" % (rr, cfg["min_reward_risk"]))
    today = [t for t in journal.get("trades", []) if t.get("date") == day]
    if len(today) >= cfg["max_trades_per_day"]:
        add("BLOCK", "trades", "you already made %d trades today (limit %d)" % (len(today), cfg["max_trades_per_day"]))
    lost = -sum(t.get("pnl", 0) for t in today if t.get("status") == "closed" and t.get("pnl", 0) < 0)
    if lost + loss > cfg["max_daily_loss_inr"] + 1e-6:
        add("BLOCK", "daily loss", "today's losses %s plus this stop %s would pass your %s daily limit"
            % (m.inr(lost, 0), m.inr(loss, 0), m.inr(cfg["max_daily_loss_inr"], 0)))
    t = now.time()
    if t < m.parse_clock(cfg["no_entries_before"]):
        add("WARN", "time", "before %s IST: the opening minutes are noisy" % cfg["no_entries_before"])
    if t > m.parse_clock(cfg["no_entries_after"]):
        add("WARN", "time", "after %s IST: no new entries by your rules" % cfg["no_entries_after"])
    if not (m.OPEN_T <= t <= m.CLOSE_T) or now.weekday() >= 5:
        add("WARN", "market", "NSE is closed now (09:15-15:30 IST, Mon-Fri, minus holidays)")
    if kind == "option" and o.get("expiry"):
        try:
            d = (m.dt.date.fromisoformat(o["expiry"]) - now.date()).days
            if d < cfg["min_days_to_expiry"]:
                add("WARN", "expiry", "only %d day(s) to expiry (your minimum is %d): time decay is fast" % (d, cfg["min_days_to_expiry"]))
        except ValueError:
            add("WARN", "expiry", "could not read the expiry date")
    if kind == "option":
        add("WARN", "options", "an option can lose its whole premium; a stop may fill past your price")
    if cfg.get("paper", True):
        add("PASS", "paper", "paper mode is on: practise first, nothing real is at risk")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--orders")
    ap.add_argument("--now")
    a = ap.parse_args()
    import json
    path = a.orders or os.path.join(m.trader_dir(False), "orders.json")
    if not os.path.exists(path):
        m.die("no orders.json. Run /in-budget with --write first.")
    o = json.load(open(path, encoding="utf-8"))
    res = check(o, m.load_config(), m.load_json("journal.json", {}) or {}, m.now_ist(a.now))
    blocks = [r for r in res if r[0] == "BLOCK"]
    for level, name, text in res:
        print("%-5s %-12s %s" % (level, name, text))
    print("RESULT:", "BLOCK - do not take this trade as planned" if blocks else
          "no blocks%s" % (" (read the warnings)" if any(r[0] == "WARN" for r in res) else ""))
    print(m.DISCLAIMER)
    return 2 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
