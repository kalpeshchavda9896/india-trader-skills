#!/usr/bin/env python3
"""in-deals: read NSE bulk and block deal files and show who bought and sold what.

  deals.py fetch                       download today's bulk.csv and block.csv to trader/
  deals.py summary --file trader/bulk.csv
  deals.py summary --file bulk.csv --symbol RELIANCE
  deals.py summary --file block.csv --min-crore 25 --client "mutual fund"

This is the India stand-in for the US Congress-trade tracker. Bulk deals (over 0.5% of
a company's shares) and block deals are public the same day. Big buyers can mean
interest, but they also sell, trade for clients, and are often wrong.
If the download fails, save the CSV from nseindia.com (Market Data > Large Deals)
in your browser and pass it with --file.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inmkt as m  # noqa: E402

URLS = {"bulk.csv": "https://nsearchives.nseindia.com/content/equities/bulk.csv",
        "block.csv": "https://nsearchives.nseindia.com/content/equities/block.csv"}


def num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except ValueError:
        return None


def pick(r, *names):
    low = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
    for n in names:
        for k, v in low.items():
            if n in k:
                return v
    return ""


def parse(text):
    rows = []
    for r in m.read_csv_text(text.lstrip("﻿")):
        sym = pick(r, "symbol")
        side = pick(r, "buy/sell", "buy / sell", "buy").upper()
        qty = num(pick(r, "quantity"))
        px = num(pick(r, "price", "wght"))
        if not sym or qty is None or px is None:
            continue
        rows.append({"date": pick(r, "date"), "symbol": sym.upper(), "client": pick(r, "client"),
                     "side": "BUY" if side.startswith("B") else "SELL", "qty": qty, "price": px,
                     "value": qty * px, "remarks": pick(r, "remarks")})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("mode", choices=["fetch", "summary"])
    ap.add_argument("--file")
    ap.add_argument("--symbol")
    ap.add_argument("--client")
    ap.add_argument("--min-crore", type=float, default=0.0)
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    if a.mode == "fetch":
        for name, url in URLS.items():
            try:
                data = m.http_get(url)
                p = os.path.join(m.trader_dir(), name)
                open(p, "wb").write(data)
                print("saved", p)
            except RuntimeError as e:
                print("failed:", e)
        return 0
    if not a.file:
        m.die("give --file bulk.csv (or run: deals.py fetch)")
    rows = parse(open(a.file, encoding="utf-8-sig", errors="replace").read())
    if a.symbol:
        rows = [r for r in rows if r["symbol"] == a.symbol.upper()]
    if a.client:
        rows = [r for r in rows if a.client.lower() in r["client"].lower()]
    rows = [r for r in rows if r["value"] >= a.min_crore * 1e7]
    if not rows:
        print("No deals match.")
        return 1
    buy = sum(r["value"] for r in rows if r["side"] == "BUY")
    sell = sum(r["value"] for r in rows if r["side"] == "SELL")
    print("%d deals. Bought %s crore, sold %s crore." % (len(rows), "%.1f" % (buy / 1e7), "%.1f" % (sell / 1e7)))
    net = {}
    for r in rows:
        net[r["symbol"]] = net.get(r["symbol"], 0) + (r["value"] if r["side"] == "BUY" else -r["value"])
    print("Net by stock (crore, buy minus sell):")
    for s, v in sorted(net.items(), key=lambda kv: -abs(kv[1]))[: a.top]:
        print("  %-12s %+9.1f" % (s, v / 1e7))
    print("Largest deals:")
    for r in sorted(rows, key=lambda r: -r["value"])[: a.top]:
        print("  %-5s %-12s %7.1f cr at %s  %s" % (r["side"], r["symbol"], r["value"] / 1e7, m.inr(r["price"]), r["client"][:40]))
    print("Both sides of a deal are listed; the same trade can show as a buy and a sell.")
    print(m.DISCLAIMER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
