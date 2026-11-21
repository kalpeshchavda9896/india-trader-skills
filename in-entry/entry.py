#!/usr/bin/env python3
"""in-entry: find the one bar that confirms a setup. It never buys anything.

  entry.py check RELIANCE                         15-minute opening range, 5-minute bars
  entry.py check NIFTY --setup level --level 25850
  entry.py check TCS --min-volume-x 1.5 --write   also save trader/entry.json
  entry.py watch RELIANCE --until 14:45           one line per closed bar, stops on the trigger

The trigger is the first COMPLETED bar after the opening range that CLOSES above
the level. A wick above the level is not a trigger. Times are IST (NSE 09:15-15:30).
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inmkt as m  # noqa: E402


def evaluate(bars, now, interval, setup, level, or_minutes, min_vol_x, cfg):
    day = now.date()
    sess = m.session_bars(bars, day)
    if not sess:
        return {"status": "no-data", "why": "no bars for %s (market closed or holiday?)" % day}
    ilen = m.dt.timedelta(minutes=m.INTERVAL_MIN[interval])
    start = sess[0]["t"]
    if setup == "orb":
        end = start + m.dt.timedelta(minutes=or_minutes)
        rng = [b for b in sess if b["t"] < end]
        if (now < end) or not rng:
            return {"status": "waiting", "why": "opening range not finished until %s" % m.fmt_time(end)}
        lvl = max(b["h"] for b in rng)
        info = {"or_high": lvl, "or_low": min(b["l"] for b in rng)}
        info["or_mid"] = (info["or_high"] + info["or_low"]) / 2
        pool = [b for b in sess if b["t"] >= end]
        avg_v = sum(b["v"] for b in rng) / len(rng)
    else:
        lvl = level
        info = {}
        pool = sess
        avg_v = sum(b["v"] for b in sess[:3]) / max(1, len(sess[:3]))
    nb = parse_limit(cfg["no_entries_before"])
    na = parse_limit(cfg["no_entries_after"])
    for b in m.closed_bars(pool, interval, now):
        close_t = b["t"] + ilen
        if b["c"] > lvl:
            if min_vol_x and avg_v and b["v"] < min_vol_x * avg_v:
                continue
            res = dict(info, level=lvl, price=b["c"], bar_start=m.fmt_time(b["t"]),
                       time=m.fmt_time(close_t), volume=b["v"])
            if close_t.time() < nb:
                res.update(status="too-early", why="before %s IST: first minutes are noisy" % cfg["no_entries_before"])
            elif close_t.time() > na:
                res.update(status="too-late", why="after %s IST: no new entries" % cfg["no_entries_after"])
            else:
                res["status"] = "triggered"
            return res
    return dict(info, level=lvl, status="waiting",
                why="no completed %s bar has closed above %s yet" % (interval, m.inr(lvl)))


def parse_limit(s):
    return m.parse_clock(s)


def show(sym, res, interval):
    print("%s  setup level %s" % (sym, m.inr(res["level"]) if "level" in res else "-"))
    st = res["status"]
    if st == "triggered":
        print("  TRIGGER: %s bar closed above %s at %s IST, price %s"
              % (interval, m.inr(res["level"]), res["time"], m.inr(res["price"])))
        print("  Next: /in-exit to set the stop and target BEFORE you enter.")
    else:
        print("  %s: %s" % (st.upper(), res.get("why", "")))
        if st in ("too-early", "too-late"):
            print("  (bar %s closed at %s, price %s)" % (res["bar_start"], res["time"], m.inr(res["price"])))


def run_check(a, sym, now):
    cfg = m.load_config()
    ch = m.get_chart(sym, "1d", a.interval, a.offline)
    res = evaluate(ch["bars"], now, a.interval, a.setup, a.level, a.or_minutes, a.min_volume_x, cfg)
    return ch, res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("mode", choices=["check", "watch"])
    ap.add_argument("symbol")
    ap.add_argument("--setup", choices=["orb", "level"], default="orb")
    ap.add_argument("--level", type=float)
    ap.add_argument("--interval", choices=["1m", "5m", "15m"], default="5m")
    ap.add_argument("--or-minutes", type=int, default=15)
    ap.add_argument("--min-volume-x", type=float, default=0.0)
    ap.add_argument("--until", default="14:45")
    ap.add_argument("--now", help='pin the clock, IST: "2026-11-23 10:15"')
    ap.add_argument("--offline")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if a.setup == "level" and a.level is None:
        m.die("--setup level needs --level PRICE")
    sym = a.symbol.upper()
    if a.mode == "check":
        try:
            _, res = run_check(a, sym, m.now_ist(a.now))
        except (RuntimeError, ValueError) as e:
            m.die(str(e))
        show(sym, res, a.interval)
        if res["status"] == "triggered" and a.write:
            out = dict(symbol=sym, setup=a.setup, **res)
            print("  wrote", m.save_json("entry.json", out))
        print(m.DISCLAIMER)
        return 0 if res["status"] == "triggered" else 1
    # watch: poll once a minute (or replay a pinned clock bar by bar)
    until = m.parse_clock(a.until)
    now = m.now_ist(a.now)
    step = m.dt.timedelta(minutes=m.INTERVAL_MIN[a.interval])
    while now.time() <= until:
        try:
            _, res = run_check(a, sym, now)
        except (RuntimeError, ValueError) as e:
            print(m.fmt_time(now), "error:", e)
            res = {"status": "error"}
        print("%s  %s %s" % (m.fmt_time(now), res["status"], res.get("why", "")))
        if res["status"] == "triggered":
            show(sym, res, a.interval)
            if a.write:
                print("  wrote", m.save_json("entry.json", dict(symbol=sym, setup=a.setup, **res)))
            return 0
        if a.now or a.offline:
            now += step
        else:
            time.sleep(60)
            now = m.now_ist()
    print("No trigger before", a.until)
    return 1


if __name__ == "__main__":
    sys.exit(main())
