#!/usr/bin/env python3
"""in-alerts: ring the terminal bell when a price, a stop, a target or the clock is hit.

  alerts.py add RELIANCE above 1510 --label target
  alerts.py add NIFTY below 25400
  alerts.py from-plan                 adds stop and target alerts from trader/plan.json
  alerts.py list
  alerts.py check                     one look at the prices now
  alerts.py watch --every 60          keeps looking until you press Ctrl-C
  alerts.py clock                     market status, time to the bell and to flat-by

Prices are Yahoo's free, delayed data. For a real stop, place a stop-loss order
at your broker: an alert on your screen does not protect you if you look away.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inmkt as m  # noqa: E402


def load():
    return m.load_json("alerts.json", {"alerts": []}) or {"alerts": []}


def last_price(sym, offline=None):
    ch = m.get_chart(sym, "1d", "1m", offline)
    p = ch["meta"].get("regularMarketPrice")
    if p is None and ch["bars"]:
        p = ch["bars"][-1]["c"]
    if p is None:
        raise RuntimeError("no price for %s" % sym)
    return float(p)


def hit(al, price):
    return price >= al["price"] if al["dir"] == "above" else price <= al["price"]


def check_once(data, offline=None, bell=False):
    fired = 0
    cache = {}
    for al in data["alerts"]:
        if al.get("fired"):
            continue
        try:
            if al["symbol"] not in cache:
                cache[al["symbol"]] = last_price(al["symbol"], offline)
        except (RuntimeError, ValueError) as e:
            print("  %s: %s" % (al["symbol"], e))
            continue
        p = cache[al["symbol"]]
        if hit(al, p):
            al["fired"] = m.now_ist().strftime("%H:%M")
            fired += 1
            print("%sALERT %s went %s %s (now %s) %s" % ("\a" if bell else "", al["symbol"], al["dir"],
                  m.inr(al["price"]), m.inr(p), ("- " + al["label"]) if al.get("label") else ""))
    for s, p in cache.items():
        print("  %-12s %s" % (s, m.inr(p)))
    return fired


def clock(cfg, now):
    t = now.time()
    print("Now: %s IST" % now.strftime("%a %d %b %H:%M"))
    if now.weekday() >= 5:
        print("NSE is closed: weekend. Next session Monday 09:15 IST (unless it is a holiday).")
        return
    def mins(x):
        return (x.hour * 60 + x.minute) - (t.hour * 60 + t.minute)
    if t < m.OPEN_T:
        print("Pre-open. The bell rings in %d minutes (09:15)." % mins(m.OPEN_T))
    elif t <= m.CLOSE_T:
        print("Market open. %d minutes to the close (15:30)." % mins(m.CLOSE_T))
        fb = m.parse_clock(cfg["flat_by"])
        if t < fb:
            print("Be flat in %d minutes (%s) if this is an intraday plan." % (mins(fb), cfg["flat_by"]))
        else:
            print("Past your flat-by time (%s): close intraday positions now." % cfg["flat_by"])
        if t < m.parse_clock(cfg["no_entries_before"]):
            print("No entries before %s." % cfg["no_entries_before"])
        if t > m.parse_clock(cfg["no_entries_after"]):
            print("No new entries after %s." % cfg["no_entries_after"])
    else:
        print("Closed for today (15:30). NSE holidays are not checked here: confirm on nseindia.com.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("mode", choices=["add", "from-plan", "list", "check", "watch", "clear", "clock"])
    ap.add_argument("symbol", nargs="?")
    ap.add_argument("dir", nargs="?", choices=["above", "below"])
    ap.add_argument("price", nargs="?", type=float)
    ap.add_argument("--label", default="")
    ap.add_argument("--every", type=int, default=60)
    ap.add_argument("--offline")
    ap.add_argument("--now")
    a = ap.parse_args()
    cfg = m.load_config()
    if a.mode == "clock":
        clock(cfg, m.now_ist(a.now))
        return 0
    data = load()
    if a.mode == "add":
        if not (a.symbol and a.dir and a.price):
            m.die("usage: alerts.py add SYMBOL above|below PRICE")
        data["alerts"].append({"symbol": a.symbol.upper(), "dir": a.dir, "price": a.price, "label": a.label})
        m.save_json("alerts.json", data)
        print("Added: %s %s %s" % (a.symbol.upper(), a.dir, m.inr(a.price)))
    elif a.mode == "from-plan":
        p = m.load_json("plan.json")
        if not p:
            m.die("no trader/plan.json")
        data["alerts"] += [
            {"symbol": p["symbol"], "dir": "below", "price": p["stop"], "label": "STOP"},
            {"symbol": p["symbol"], "dir": "above", "price": p["target"], "label": "TARGET"}]
        m.save_json("alerts.json", data)
        print("Added stop %s and target %s for %s" % (m.inr(p["stop"]), m.inr(p["target"]), p["symbol"]))
    elif a.mode == "list":
        for i, al in enumerate(data["alerts"], 1):
            print("%d. %s %s %s %s%s" % (i, al["symbol"], al["dir"], m.inr(al["price"]), al.get("label", ""),
                  "  [fired %s]" % al["fired"] if al.get("fired") else ""))
        if not data["alerts"]:
            print("No alerts. Add one: alerts.py add SYMBOL above|below PRICE")
    elif a.mode == "clear":
        m.save_json("alerts.json", {"alerts": []})
        print("Cleared.")
    elif a.mode == "check":
        n = check_once(data, a.offline)
        m.save_json("alerts.json", data)
        print("%d alert(s) fired." % n)
        return 0 if n else 1
    elif a.mode == "watch":
        print("Watching every %ds. Ctrl-C to stop." % a.every)
        try:
            while any(not x.get("fired") for x in data["alerts"]):
                if not (m.OPEN_T <= m.now_ist().time() <= m.CLOSE_T) and not a.offline:
                    print("Market closed. Run again at 09:15 IST.")
                    break
                check_once(data, a.offline, bell=True)
                m.save_json("alerts.json", data)
                if a.offline:
                    break
                time.sleep(a.every)
        except KeyboardInterrupt:
            print("Stopped.")
    print(m.DISCLAIMER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
