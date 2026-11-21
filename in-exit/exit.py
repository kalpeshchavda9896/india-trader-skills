#!/usr/bin/env python3
"""in-exit: decide how a trade ENDS before it starts. Writes trader/plan.json.

  exit.py plan                                       uses trader/entry.json, stop or-mid, target 2R
  exit.py plan --stop or-low --target 1.5R --write
  exit.py plan --symbol RELIANCE --entry 1480 --stop price:1465 --target price:1510 --write
  exit.py plan --symbol TCS --entry 3200 --stop pct:1 --target 2R
  exit.py plan --stop atr:1.5 --offline FILE         ATR stop from the day's bars

The stop is where the idea has failed. The target is where you take what you came for.
A stop is a plan, not a guarantee: a gap or a fast market can fill past it.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inmkt as m  # noqa: E402


def resolve_stop(spec, entry, ent, atr_val):
    kind, _, val = spec.partition(":")
    if kind == "or-mid":
        if "or_mid" not in ent:
            m.die("or-mid needs an opening range (run /in-entry check --write first)")
        return ent["or_mid"], "opening-range midpoint"
    if kind == "or-low":
        if "or_low" not in ent:
            m.die("or-low needs an opening range (run /in-entry check --write first)")
        return ent["or_low"], "opening-range low"
    if kind == "price":
        return float(val), "your price"
    if kind == "pct":
        return entry * (1 - float(val) / 100.0), "%s%% below entry" % val
    if kind == "atr":
        if atr_val is None:
            m.die("atr stop needs enough bars (use --offline FILE or run during the session)")
        return entry - float(val) * atr_val, "%s x ATR (%.2f)" % (val, atr_val)
    m.die("unknown stop %r. Use or-mid, or-low, price:X, pct:X or atr:K" % spec)


def resolve_target(spec, entry, risk):
    s = spec.lower()
    if s.endswith("r"):
        k = float(s[:-1])
        return entry + k * risk, k
    if s.startswith("price:"):
        t = float(s.split(":", 1)[1])
        return t, (t - entry) / risk
    m.die("unknown target %r. Use 2R, 1.5R or price:X" % spec)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("mode", choices=["plan", "show"])
    ap.add_argument("--symbol")
    ap.add_argument("--entry", type=float)
    ap.add_argument("--stop", default="or-mid")
    ap.add_argument("--target", default="2R")
    ap.add_argument("--flat-by")
    ap.add_argument("--offline")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if a.mode == "show":
        p = m.load_json("plan.json")
        if not p:
            m.die("no trader/plan.json yet")
        for k, v in p.items():
            print("%-14s %s" % (k, v))
        return 0
    cfg = m.load_config()
    ent = m.load_json("entry.json", {}) or {}
    sym = (a.symbol or ent.get("symbol") or "").upper()
    entry = a.entry if a.entry is not None else ent.get("price")
    if not sym or entry is None:
        m.die("need a symbol and an entry: run /in-entry check --write first, or pass --symbol and --entry")
    atr_val = None
    if a.stop.startswith("atr:"):
        ch = m.get_chart(sym, "5d", "5m", a.offline)
        atr_val = m.atr(ch["bars"], 14)
    stop, why = resolve_stop(a.stop, entry, ent, atr_val)
    if stop >= entry:
        m.die("The stop (%s) is not below the entry (%s). This tool plans long trades only." % (m.inr(stop), m.inr(entry)))
    risk = entry - stop
    target, rr = resolve_target(a.target, entry, risk)
    plan = {
        "symbol": sym, "side": "buy", "entry": round(entry, 2), "stop": round(stop, 2),
        "stop_rule": why, "target": round(target, 2), "risk_per_share": round(risk, 2),
        "reward_per_share": round(target - entry, 2), "reward_risk": round(rr, 2),
        "stop_pct": round(risk / entry * 100, 2), "flat_by": a.flat_by or cfg["flat_by"],
        "date": m.now_ist().strftime("%Y-%m-%d"), "setup": ent.get("setup", "manual"),
    }
    print("%s  entry %s  stop %s (%s)  target %s" % (sym, m.inr(entry), m.inr(stop), why, m.inr(target)))
    print("  risk %s a share (%.2f%%), reward %s, reward:risk %.2f, be flat by %s IST"
          % (m.inr(risk), plan["stop_pct"], m.inr(target - entry), rr, plan["flat_by"]))
    if rr < cfg["min_reward_risk"]:
        print("  NOTE: reward:risk is under your minimum of %s. /in-risk will flag it." % cfg["min_reward_risk"])
    if plan["stop_pct"] > 3:
        print("  NOTE: the stop is %.1f%% away. A wide stop means a small position." % plan["stop_pct"])
    if a.write:
        print("  wrote", m.save_json("plan.json", plan))
    print(m.DISCLAIMER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
