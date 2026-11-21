#!/usr/bin/env python3
"""in-scanner: scan NSE charts for setups and write trader/watchlist.json.

  scan.py universe                      NSE equity list -> trader/universe.txt
  scan.py nifty50                       Nifty 50 members -> trader/universe.txt
  scan.py daily --symbols A,B,C         daily-close setups (run after 15:30 or before 9:15)
  scan.py daily --universe --limit 200
  scan.py orb --symbols A,B             intraday opening-range breakouts (after 9:30 IST)

A scan is a list of charts that match a rule. It is not a list of things to buy.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inmkt as m  # noqa: E402

EQUITY_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
NIFTY50_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
PAUSE = 0.4


def cmd_universe(a, url=EQUITY_URL, only_eq=True):
    if a.file:
        text = open(a.file, encoding="utf-8-sig").read()
    else:
        try:
            text = m.http_get(url).decode("utf-8-sig")
        except RuntimeError as e:
            m.die("%s\nDownload the CSV in your browser and run again with --file PATH." % e)
    rows = m.read_csv_text(text)
    out = []
    for r in rows:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        sym = r.get("symbol")
        name = r.get("name of company") or r.get("company name") or ""
        series = r.get("series") or r.get("series ", "EQ")
        if not sym:
            continue
        if only_eq and series and series != "EQ":
            continue
        out.append("%s|%s" % (sym, name))
    if not out:
        m.die("no symbols found in that file")
    p = os.path.join(m.trader_dir(), "universe.txt")
    open(p, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("Wrote %d symbols to %s" % (len(out), p))


def read_universe():
    p = os.path.join(m.trader_dir(False), "universe.txt")
    if not os.path.exists(p):
        m.die("no trader/universe.txt. Run: scan.py universe  (or pass --symbols)")
    return [ln.split("|")[0] for ln in open(p, encoding="utf-8") if ln.strip()]


def pick_symbols(a):
    if a.symbols:
        return [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    if a.watchlist:
        import json
        p = a.watchlist if os.path.exists(a.watchlist) else os.path.join(m.trader_dir(False), a.watchlist)
        if not os.path.exists(p):
            m.die("no watchlist file at %s" % p)
        return [h["symbol"] for h in json.load(open(p, encoding="utf-8")).get("hits", [])]
    syms = read_universe()
    return syms[: a.limit] if a.limit else syms


def daily_setups(bars, min_price, min_vol):
    """Return (list of setup names, facts) for one stock's daily bars."""
    if len(bars) < 30:
        return [], {}
    closes = [b["c"] for b in bars]
    last = bars[-1]
    prior = bars[-21:-1]
    hi20 = max(b["h"] for b in prior)
    avg_vol = sum(b["v"] for b in bars[-20:]) / 20.0
    ma20 = m.sma(closes, 20)
    r = m.rsi(closes, 14)
    facts = {"close": round(last["c"], 2), "ma20": round(ma20, 2),
             "rsi": round(r, 1) if r is not None else None,
             "high20": round(hi20, 2), "avg_volume": int(avg_vol)}
    if last["c"] < min_price or avg_vol < min_vol:
        return [], facts
    found = []
    if last["c"] > hi20:
        found.append("20-day closing-high breakout" if last["c"] > max(b["c"] for b in prior)
                     else "20-day high breakout")
    if len(closes) > 21 and closes[-2] < m.sma(closes[:-1], 20) <= last["c"]:
        found.append("reclaimed the 20-day average")
    if r is not None and r < 30:
        found.append("oversold (RSI under 30)")
        if last["c"] > bars[-2]["c"] and last["c"] > last["o"]:
            found.append("oversold bounce")
    # bull flag: strong pole, then a tight pause above the 20-day average
    pole = closes[-6] / closes[-16] - 1 if closes[-16] else 0
    flag = bars[-5:]
    rng = (max(b["h"] for b in flag) - min(b["l"] for b in flag)) / last["c"]
    if pole >= 0.10 and rng <= 0.05 and last["c"] > ma20:
        found.append("bull flag")
    return found, facts


def orb_setup(bars, now, or_minutes):
    """Opening range = first `or_minutes` of the session (09:15 start)."""
    day = now.date()
    sess = [b for b in m.session_bars(bars, day)]
    if not sess:
        return None
    start = sess[0]["t"]
    end = start + m.dt.timedelta(minutes=or_minutes)
    rng = [b for b in sess if b["t"] < end]
    after = m.closed_bars([b for b in sess if b["t"] >= end], "5m", now)
    if not rng or not after:
        return None
    hi = max(b["h"] for b in rng)
    lo = min(b["l"] for b in rng)
    for b in after:
        if b["c"] > hi:
            return {"setup": "opening-range breakout", "or_high": hi, "or_low": lo,
                    "trigger_time": m.fmt_time(b["t"] + m.dt.timedelta(minutes=5)),
                    "trigger_close": b["c"], "last": after[-1]["c"]}
    return None


def cmd_scan(a):
    syms = pick_symbols(a)
    now = m.now_ist(a.now)
    hits, failed = [], []
    for i, s in enumerate(syms):
        try:
            if a.mode == "daily":
                ch = m.get_chart(s, "6mo", "1d", a.offline)
                found, facts = daily_setups(ch["bars"], a.min_price, a.min_volume)
                if found:
                    hits.append(dict(symbol=s, setups=found, **facts))
            else:
                ch = m.get_chart(s, "1d", "5m", a.offline)
                r = orb_setup(ch["bars"], now, a.or_minutes)
                if r:
                    hits.append(dict(symbol=s, setups=[r.pop("setup")], **r))
        except (RuntimeError, ValueError, KeyError) as e:
            failed.append("%s: %s" % (s, e))
        if not a.offline and i + 1 < len(syms):
            time.sleep(a.pause)
    out = {"mode": a.mode, "as_of": now.strftime("%Y-%m-%d %H:%M IST"),
           "scanned": len(syms) - len(failed), "failed": len(failed), "hits": hits}
    if not a.no_write:
        m.save_json("watchlist.json", out)
    print("%s scan, %s: %d scanned, %d failed, %d hits" %
          (a.mode, out["as_of"], out["scanned"], out["failed"], len(hits)))
    for h in hits[: a.show]:
        extra = ("close %s" % m.inr(h["close"])) if "close" in h else \
            ("broke %s at %s" % (m.inr(h["or_high"]), h["trigger_time"]))
        print("  %-12s %s  (%s)" % (h["symbol"], "; ".join(h["setups"]), extra))
    for f in failed[:5]:
        print("  failed", f)
    if a.json:
        import json
        print(json.dumps(out, indent=2))
    print(m.DISCLAIMER)
    return 0 if hits else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("mode", choices=["universe", "nifty50", "daily", "orb"])
    ap.add_argument("--symbols")
    ap.add_argument("--watchlist")
    ap.add_argument("--universe", action="store_true", help="use trader/universe.txt")
    ap.add_argument("--file", help="a downloaded NSE CSV (for universe / nifty50)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-price", type=float, default=50.0)
    ap.add_argument("--min-volume", type=float, default=200000.0)
    ap.add_argument("--or-minutes", type=int, default=15)
    ap.add_argument("--now", help='pin the clock, IST: "2026-11-23 10:15"')
    ap.add_argument("--offline", help="saved Yahoo chart JSON file or folder of SYMBOL.json")
    ap.add_argument("--pause", type=float, default=PAUSE)
    ap.add_argument("--show", type=int, default=25)
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.mode == "universe":
        return cmd_universe(a)
    if a.mode == "nifty50":
        return cmd_universe(a, NIFTY50_URL, only_eq=False)
    if not (a.symbols or a.watchlist or a.universe):
        m.die("give --symbols A,B,C, --watchlist FILE or --universe")
    return cmd_scan(a)


if __name__ == "__main__":
    sys.exit(main())
