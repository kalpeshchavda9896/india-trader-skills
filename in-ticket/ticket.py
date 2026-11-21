#!/usr/bin/env python3
"""in-ticket: a plain-words order ticket for YOU to place by hand in Upstox, plus a paper journal.

  ticket.py show                         the ticket for trader/orders.json
  ticket.py show --product CNC           CNC = delivery, MIS = intraday, NRML = F&O carry
  ticket.py log                          record it as a paper trade (open)
  ticket.py close --id 1 --exit 1503.5   close a paper trade at a price
  ticket.py summary                      wins, losses and total paper P&L

This skill NEVER sends an order. It has no broker connection and no keys.
Run /in-risk first. You place and approve every real order yourself.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inmkt as m  # noqa: E402


def load_orders():
    o = m.load_json("orders.json")
    if not o:
        m.die("no trader/orders.json. Run /in-budget with --write first.")
    return o


def show(o, product):
    cfg = m.load_config()
    print("ORDER TICKET (place this by hand in Upstox)")
    print("-" * 48)
    if o["kind"] == "cash":
        prod = product or "MIS"
        print("Instrument : %s (NSE equity)" % o["symbol"])
        print("Side       : BUY")
        print("Quantity   : %d" % o["qty"])
        print("Product    : %s%s" % (prod, "  (intraday: closes by the broker's auto square-off if you forget)" if prod == "MIS" else ""))
        print("Order type : LIMIT at %s (no market orders on a thin stock)" % m.inr(o["entry"]))
        print("Then       : place a STOP-LOSS order, trigger %s. Do it the moment the buy fills." % m.inr(o["stop"]))
        if o.get("target"):
            print("             and a SELL LIMIT at the target %s." % m.inr(o["target"]))
        print("Be flat by : %s IST if this is an intraday plan" % cfg["flat_by"])
    else:
        prod = product or "NRML"
        print("Instrument : %s (use the exact contract: strike, CE/PE, expiry)" % o.get("option", o["underlying"]))
        print("Side       : BUY")
        print("Lots       : %d  (lot size %d, so quantity %d units)" % (o["lots"], o["lot_size"], o["qty"]))
        print("Product    : %s" % prod)
        print("Order type : LIMIT at premium %s" % m.inr(o["entry"]))
        print("Then       : place a STOP-LOSS order at premium %s as soon as the buy fills." % m.inr(o["stop"]))
        if o.get("target"):
            print("             and a SELL LIMIT at %s." % m.inr(o["target"]))
        print("Time rule  : if the premium has not moved in 2-3 sessions, sell. Time decay costs you daily.")
    print("-" * 48)
    print("Max loss if the stop fills: about %s. Cost: about %s." % (m.inr(o.get("max_loss", 0), 0), m.inr(o.get("cost", 0), 0)))
    print("Before you tap BUY: check the live price and lot size in the app, then run /in-risk.")
    print(m.DISCLAIMER)


def journal():
    return m.load_json("journal.json", {"trades": []}) or {"trades": []}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("mode", choices=["show", "log", "close", "summary"])
    ap.add_argument("--product", choices=["MIS", "CNC", "NRML"])
    ap.add_argument("--id", type=int)
    ap.add_argument("--exit", type=float)
    ap.add_argument("--now")
    a = ap.parse_args()
    if a.mode == "show":
        show(load_orders(), a.product)
        return 0
    j = journal()
    cfg = m.load_config()
    if a.mode == "log":
        o = load_orders()
        t = {"id": len(j["trades"]) + 1, "date": m.now_ist(a.now).strftime("%Y-%m-%d"),
             "symbol": o.get("symbol") or o.get("option", o.get("underlying")), "kind": o["kind"],
             "qty": o["qty"], "entry": o["entry"], "stop": o["stop"], "target": o.get("target"),
             "status": "open", "paper": True}
        j["trades"].append(t)
        m.save_json("journal.json", j)
        print("Logged paper trade #%d: %s x%d at %s" % (t["id"], t["symbol"], t["qty"], m.inr(t["entry"])))
        return 0
    if a.mode == "close":
        if a.id is None or a.exit is None:
            m.die("need --id N and --exit PRICE")
        for t in j["trades"]:
            if t["id"] == a.id and t["status"] == "open":
                gross = (a.exit - t["entry"]) * t["qty"]
                c = 2 * cfg["brokerage_per_order_inr"] + cfg["other_charges_pct"] / 100.0 * (t["entry"] + a.exit) * t["qty"]
                t.update(status="closed", exit=a.exit, pnl=round(gross - c, 2), charges=round(c, 2))
                m.save_json("journal.json", j)
                print("Closed #%d at %s: P&L %s after about %s charges" % (a.id, m.inr(a.exit), m.inr(t["pnl"]), m.inr(c)))
                return 0
        m.die("no open trade with id %s" % a.id)
    closed = [t for t in j["trades"] if t["status"] == "closed"]
    if not closed:
        print("No closed paper trades yet. Open: %d" % len([t for t in j["trades"] if t["status"] == "open"]))
        return 0
    wins = [t for t in closed if t["pnl"] > 0]
    tot = sum(t["pnl"] for t in closed)
    print("%d closed paper trades: %d wins, %d losses, total P&L %s" % (len(closed), len(wins), len(closed) - len(wins), m.inr(tot)))
    print("Average win %s, average loss %s" % (
        m.inr(sum(t["pnl"] for t in wins) / len(wins)) if wins else "-",
        m.inr(sum(t["pnl"] for t in closed if t["pnl"] <= 0) / max(1, len(closed) - len(wins)))))
    print("Practise until the result holds over many trades, not a few good days.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
