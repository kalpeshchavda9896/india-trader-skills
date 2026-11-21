#!/usr/bin/env python3
"""in-news: recent headlines for Indian stocks, flagged by what tends to move a price.

  news.py check RELIANCE TCS --hours 24
  news.py check --watchlist watchlist.json
  news.py check INFY --offline-dir DIR     (saved RSS files named SYMBOL.xml, for tests)

Sources: Yahoo Finance RSS and Google News RSS (both free, unofficial, can lag).
A headline is a headline, not a signal. Read the story before you act.
"""
import argparse
import email.utils
import json
import os
import sys
import urllib.parse
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inmkt as m  # noqa: E402

FLAGS = [
    ("results", ["results", "q1", "q2", "q3", "q4", "net profit", "quarterly", "earnings", "revenue", "ebitda"]),
    ("orders/deals", ["order win", "bags order", "wins order", "contract", "acquire", "acquisition", "merger", "stake", "bulk deal", "block deal"]),
    ("rating/target", ["upgrade", "downgrade", "target price", "brokerage", "initiates coverage", "buy rating", "sell rating"]),
    ("regulatory", ["sebi", "rbi", "penalty", "probe", "notice", "ban", "fda", "investigation", "fraud"]),
    ("corporate action", ["dividend", "bonus", "split", "buyback", "rights issue", "record date", "ex-date"]),
    ("management", ["resigns", "resignation", "appoints", "ceo", "promoter", "pledge"]),
    ("guidance/outlook", ["guidance", "outlook", "cuts forecast", "raises forecast", "warns"]),
]


def flags_for(title):
    t = title.lower()
    return [name for name, words in FLAGS if any(w in t for w in words)]


def parse_rss(xml_bytes, source):
    out = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return out
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate")
        when = None
        if pub:
            try:
                when = email.utils.parsedate_to_datetime(pub)
            except (TypeError, ValueError):
                when = None
        if title:
            out.append({"title": title, "link": link, "time": when, "source": source})
    return out


def fetch(symbol, offline_dir=None):
    s = m.short_symbol(symbol)
    if offline_dir:
        p = os.path.join(offline_dir, s + ".xml")
        return parse_rss(open(p, "rb").read(), "offline") if os.path.exists(p) else []
    items = []
    yurl = ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=%s.NS&region=IN&lang=en-IN" % s)
    gq = urllib.parse.quote("%s share price when:2d" % s)
    gurl = "https://news.google.com/rss/search?q=%s&hl=en-IN&gl=IN&ceid=IN:en" % gq
    for url, src in ((yurl, "Yahoo Finance"), (gurl, "Google News")):
        try:
            items += parse_rss(m.http_get(url), src)
        except RuntimeError:
            pass
    return items


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("mode", choices=["check"])
    ap.add_argument("symbols", nargs="*")
    ap.add_argument("--watchlist")
    ap.add_argument("--hours", type=float, default=36)
    ap.add_argument("--offline-dir")
    ap.add_argument("--now", help='pin the clock, IST: "2026-11-23 09:00"')
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    syms = [s.upper() for s in a.symbols]
    if a.watchlist:
        p = a.watchlist if os.path.exists(a.watchlist) else os.path.join(m.trader_dir(False), a.watchlist)
        syms += [h["symbol"] for h in json.load(open(p, encoding="utf-8")).get("hits", [])]
    if not syms:
        m.die("give symbols (RELIANCE TCS) or --watchlist FILE")
    now = m.now_ist(a.now)
    cutoff = now - m.dt.timedelta(hours=a.hours)
    result = {}
    for s in syms:
        seen, rows = set(), []
        for it in fetch(s, a.offline_dir):
            key = it["title"].lower()[:70]
            if key in seen:
                continue
            seen.add(key)
            t = it["time"]
            if t is not None and t.tzinfo is not None and t.astimezone(m.IST) < cutoff:
                continue
            it["flags"] = flags_for(it["title"])
            rows.append(it)
        rows.sort(key=lambda r: (not r["flags"], str(r["time"]) ), reverse=False)
        result[s] = rows
        print("== %s: %d headlines in the last %g hours" % (s, len(rows), a.hours))
        for r in rows[:8]:
            when = r["time"].astimezone(m.IST).strftime("%d %b %H:%M") if r["time"] else "?"
            tag = "[%s] " % ", ".join(r["flags"]) if r["flags"] else ""
            print("  %s  %s%s  (%s)" % (when, tag, r["title"], r["source"]))
    if a.json:
        print(json.dumps(result, indent=2, default=str))
    print(m.DISCLAIMER)
    return 0 if any(result.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
