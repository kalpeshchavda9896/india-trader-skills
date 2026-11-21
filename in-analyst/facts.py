#!/usr/bin/env python3
"""in-analyst: read a company's quarterly results and say what changed.

  facts.py template                        print a results file to fill in
  facts.py read results.json               growth, margins and flags for the latest quarter
  facts.py read results.csv

You supply the numbers from the company's results filing (NSE/BSE announcements,
the investor presentation, or your broker app). The tool does the arithmetic and
points at what moved. It does NOT fetch results: no free, stable Indian source exists.
Amounts can be in any one unit (for example Rs crore) as long as you stay consistent.
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inmkt as m  # noqa: E402

TEMPLATE = {
    "symbol": "EXAMPLE",
    "unit": "Rs crore",
    "note": "Oldest quarter first. Use at least 5 quarters so year-on-year works. Replace these EXAMPLE numbers.",
    "quarters": [
        {"period": "Q2 FY25", "revenue": 1000, "ebitda": 200, "pat": 120, "eps": 6.0},
        {"period": "Q3 FY25", "revenue": 1040, "ebitda": 205, "pat": 124, "eps": 6.2},
        {"period": "Q4 FY25", "revenue": 1080, "ebitda": 210, "pat": 128, "eps": 6.4},
        {"period": "Q1 FY26", "revenue": 1100, "ebitda": 215, "pat": 130, "eps": 6.5},
        {"period": "Q2 FY26", "revenue": 1150, "ebitda": 210, "pat": 118, "eps": 5.9},
    ],
}


def load(path):
    if path.lower().endswith(".csv"):
        rows = []
        for r in csv.DictReader(open(path, encoding="utf-8-sig")):
            r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
            q = {"period": r.get("period", "")}
            for k in ("revenue", "ebitda", "pat", "eps"):
                try:
                    q[k] = float(r[k].replace(",", "")) if r.get(k) else None
                except ValueError:
                    q[k] = None
            rows.append(q)
        return {"symbol": os.path.basename(path), "unit": "as given", "quarters": rows}
    return json.load(open(path, encoding="utf-8"))


def chg(new, old):
    if new is None or old in (None, 0):
        return None
    return (new - old) / abs(old) * 100.0


def margin(q, key):
    if q.get(key) is None or not q.get("revenue"):
        return None
    return q[key] / q["revenue"] * 100.0


def fmt(x, suffix="%"):
    return "n/a" if x is None else "%+.1f%s" % (x, suffix)


def analyse(d):
    qs = d["quarters"]
    if len(qs) < 2:
        m.die("need at least 2 quarters (5 for year-on-year)")
    cur, prev = qs[-1], qs[-2]
    yoy = qs[-5] if len(qs) >= 5 else None
    rows = []
    flags = []
    for key, label in (("revenue", "Revenue"), ("ebitda", "EBITDA"), ("pat", "Net profit"), ("eps", "EPS")):
        qoq = chg(cur.get(key), prev.get(key))
        yy = chg(cur.get(key), yoy.get(key)) if yoy else None
        rows.append((label, cur.get(key), qoq, yy))
        if yy is not None and yy <= -20 and key in ("pat", "ebitda"):
            flags.append("%s is down %.0f%% from a year ago" % (label, abs(yy)))
        if yy is not None and yy >= 25 and key in ("pat", "revenue"):
            flags.append("%s is up %.0f%% from a year ago" % (label, yy))
    ebm, ebm_prev = margin(cur, "ebitda"), margin(prev, "ebitda")
    pm, pm_prev = margin(cur, "pat"), margin(prev, "pat")
    ebm_yoy = margin(yoy, "ebitda") if yoy else None
    if ebm is not None and ebm_prev is not None and ebm - ebm_prev <= -1.0:
        flags.append("EBITDA margin fell %.1f points from last quarter" % (ebm_prev - ebm))
    if ebm is not None and ebm_prev is not None and ebm - ebm_prev >= 1.0:
        flags.append("EBITDA margin rose %.1f points from last quarter" % (ebm - ebm_prev))
    if len(qs) >= 6 and all(qs[-i].get("revenue") for i in (1, 2, 5, 6)):
        g_now = chg(qs[-1]["revenue"], qs[-5]["revenue"])
        g_before = chg(qs[-2]["revenue"], qs[-6]["revenue"])
        if g_now is not None and g_before is not None:
            if g_now - g_before >= 3:
                flags.append("year-on-year revenue growth is speeding up (%.0f%% vs %.0f%% last quarter)" % (g_now, g_before))
            elif g_before - g_now >= 3:
                flags.append("year-on-year revenue growth is slowing (%.0f%% vs %.0f%% last quarter)" % (g_now, g_before))
    return cur, rows, (ebm, ebm_prev, ebm_yoy), (pm, pm_prev), flags


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("mode", choices=["template", "read"])
    ap.add_argument("file", nargs="?")
    a = ap.parse_args()
    if a.mode == "template":
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    if not a.file:
        m.die("give a results.json or results.csv")
    d = load(a.file)
    cur, rows, (ebm, ebm_prev, ebm_yoy), (pm, pm_prev), flags = analyse(d)
    print("%s  latest quarter %s  (%s)" % (d.get("symbol", ""), cur.get("period", "?"), d.get("unit", "")))
    print("%-12s %12s %10s %10s" % ("", "this qtr", "vs last Q", "vs year ago"))
    for label, v, qoq, yy in rows:
        print("%-12s %12s %10s %10s" % (label, "n/a" if v is None else "%g" % v, fmt(qoq), fmt(yy)))
    if ebm is not None:
        print("EBITDA margin %.1f%% (last quarter %s%s)" % (ebm, "n/a" if ebm_prev is None else "%.1f%%" % ebm_prev,
              "" if ebm_yoy is None else ", year ago %.1f%%" % ebm_yoy))
    if pm is not None:
        print("Net margin    %.1f%% (last quarter %s)" % (pm, "n/a" if pm_prev is None else "%.1f%%" % pm_prev))
    print("What changed:")
    for f in flags or ["nothing crosses the tool's thresholds (+/-20% profit, +/-1 point margin)"]:
        print("  - " + f)
    print("Numbers say what happened, not what the market expected. A good result can still"
          " fall if the market wanted more. Read the filing's notes: one-off gains and tax changes distort profit.")
    print(m.DISCLAIMER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
