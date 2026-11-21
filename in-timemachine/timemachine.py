#!/usr/bin/env python3
"""in-timemachine: replay a trade plan before you risk a rupee.

  timemachine.py run                         plan from trader/plan.json
  timemachine.py run --symbol RELIANCE --entry 1480 --stop 1465 --target 1510
  timemachine.py run --entry-time 10:00 --sims 10000 --offline FILE

Two replays, both from the stock's OWN recent 5-minute bars (about 60 days):
  1. Bootstrap: 10,000 simulated sessions built by reshuffling its real 5-minute moves.
  2. History: every past day the same opening-range breakout fired, replayed bar by bar.
It reports how often the target, the stop or the end-of-day exit came first.
The past is not a promise. A neat result on thin data is not an edge.
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inmkt as m  # noqa: E402


def by_day(bars):
    days = {}
    for b in bars:
        days.setdefault(b["t"].date(), []).append(b)
    return days


def walk(prices_hi_lo_close, entry, stop, target):
    """Return 'target', 'stop' or 'flat', and the exit price. Stop wins a tie inside one bar."""
    last = entry
    for hi, lo, cl in prices_hi_lo_close:
        if lo <= stop:
            return "stop", stop
        if hi >= target:
            return "target", target
        last = cl
    return "flat", last


def history(days, today, plan, or_minutes, flat_by, no_after):
    stop_pct = (plan["entry"] - plan["stop"]) / plan["entry"]
    tgt_pct = (plan["target"] - plan["entry"]) / plan["entry"]
    out = []
    for d, bars in sorted(days.items()):
        if d == today or len(bars) < 20:
            continue
        start = bars[0]["t"]
        end = start + m.dt.timedelta(minutes=or_minutes)
        rng = [b for b in bars if b["t"] < end]
        rest = [b for b in bars if b["t"] >= end]
        if not rng or not rest:
            continue
        hi = max(b["h"] for b in rng)
        for i, b in enumerate(rest):
            if b["c"] > hi and (b["t"] + m.dt.timedelta(minutes=5)).time() <= no_after:
                e = b["c"]
                s, t = e * (1 - stop_pct), e * (1 + tgt_pct)
                fwd = [(x["h"], x["l"], x["c"]) for x in rest[i + 1:] if x["t"].time() < flat_by]
                kind, px = walk(fwd, e, s, t)
                out.append({"date": str(d), "result": kind, "r": (px - e) / (e - s)})
                break
    return out


def bootstrap(rets, steps, entry, stop, target, sims, seed):
    rnd = random.Random(seed)
    res = {"target": 0, "stop": 0, "flat": 0}
    rs = []
    for _ in range(sims):
        p = entry
        kind = "flat"
        for r in rnd.choices(rets, k=steps):
            p *= (1 + r)
            if p <= stop:
                kind, p = "stop", stop
                break
            if p >= target:
                kind, p = "target", target
                break
        res[kind] += 1
        rs.append((p - entry) / (entry - stop))
    return res, sum(rs) / len(rs)


def pct(n, total):
    return "%5.1f%%" % (100.0 * n / total) if total else "  n/a "


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("mode", choices=["run"])
    ap.add_argument("--symbol")
    ap.add_argument("--entry", type=float)
    ap.add_argument("--stop", type=float)
    ap.add_argument("--target", type=float)
    ap.add_argument("--entry-time", default="10:00")
    ap.add_argument("--sims", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--or-minutes", type=int, default=15)
    ap.add_argument("--offline")
    a = ap.parse_args()
    cfg = m.load_config()
    plan = m.load_json("plan.json", {}) or {}
    sym = (a.symbol or plan.get("symbol") or "").upper()
    for k in ("entry", "stop", "target"):
        v = getattr(a, k)
        if v is not None:
            plan[k] = v
    if not sym or not all(plan.get(k) for k in ("entry", "stop", "target")):
        m.die("need a plan (/in-exit plan --write) or --symbol --entry --stop --target")
    if not plan["stop"] < plan["entry"] < plan["target"]:
        m.die("need stop < entry < target (long trades only)")
    try:
        ch = m.get_chart(sym, "60d", "5m", a.offline)
    except (RuntimeError, ValueError) as e:
        m.die(str(e))
    days = by_day(ch["bars"])
    flat_by = m.parse_clock(plan.get("flat_by", cfg["flat_by"]))
    no_after = m.parse_clock(cfg["no_entries_after"])
    # real 5-minute returns inside sessions (no overnight gaps)
    rets = []
    for bars in days.values():
        for x, y in zip(bars, bars[1:]):
            if x["c"] > 0:
                rets.append(y["c"] / x["c"] - 1)
    if len(rets) < 200:
        m.die("only %d bars of history: too little to replay. Try a more liquid stock." % len(rets))
    et = m.parse_clock(a.entry_time)
    steps = max(1, int(((flat_by.hour * 60 + flat_by.minute) - (et.hour * 60 + et.minute)) / 5))
    risk = plan["entry"] - plan["stop"]
    rr = (plan["target"] - plan["entry"]) / risk
    print("%s: entry %s stop %s target %s (reward:risk %.2f), %d days of 5-minute bars"
          % (sym, m.inr(plan["entry"]), m.inr(plan["stop"]), m.inr(plan["target"]), rr, len(days)))
    res, exp = bootstrap(rets, steps, plan["entry"], plan["stop"], plan["target"], a.sims, a.seed)
    print("\n1) %d simulated sessions from %s to %s IST (reshuffled real moves, no trend assumed)" % (a.sims, a.entry_time, plan.get("flat_by", cfg["flat_by"])))
    for k, label in (("target", "target first"), ("stop", "stop first"), ("flat", "neither: sold at the end of day")):
        print("   %-34s %s" % (label, pct(res[k], a.sims)))
    print("   average result: %+.2f R (R = your risk on the trade)" % exp)
    h = history(days, m.now_ist().date(), plan, a.or_minutes, flat_by, no_after)
    print("\n2) %d past days the opening-range breakout fired (same stop and target distance, in %%)" % len(h))
    if h:
        c = {"target": 0, "stop": 0, "flat": 0}
        for x in h:
            c[x["result"]] += 1
        for k, label in (("target", "target first"), ("stop", "stop first"), ("flat", "neither: sold at the end of day")):
            print("   %-34s %s  (%d)" % (label, pct(c[k], len(h)), c[k]))
        print("   average result: %+.2f R" % (sum(x["r"] for x in h) / len(h)))
        if len(h) < 20:
            print("   Only %d days: far too few to trust. Treat it as a hint, not a result." % len(h))
    # a break-even hit rate for this reward:risk
    be = 1.0 / (1.0 + rr)
    print("\nBreak-even: with reward:risk %.2f you must hit the target about %.0f%% of the time before charges." % (rr, be * 100))
    verdict = "above" if res["target"] / a.sims > be else "below"
    print("The bootstrap target rate is %s break-even. Charges (brokerage and taxes) push break-even higher." % verdict)
    print(m.DISCLAIMER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
