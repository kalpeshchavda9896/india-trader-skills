#!/usr/bin/env python3
"""inmkt.py - shared helpers for the India trader skills. Standard library only.

Every skill folder carries an identical copy of this file (build.sh copies it),
so a skill works on its own once it sits in ~/.claude/skills/.

Nothing here can place an order. Prices come from Yahoo Finance's free,
unofficial chart endpoint (delayed, can be wrong or missing). Check any price
in your broker app before you act on it.
"""
import csv
import datetime as dt
import gzip
import io
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
OPEN_T = dt.time(9, 15)
CLOSE_T = dt.time(15, 30)
UA = "Mozilla/5.0 (compatible; india-trader-skills/1.0)"
INTERVAL_MIN = {"1m": 1, "2m": 2, "5m": 5, "15m": 15, "30m": 30, "60m": 60}

# Index names -> Yahoo symbols. NIFTY, BANKNIFTY and SENSEX are the common ones;
# the other two are best effort, so check them in your own app.
INDEX_MAP = {
    "NIFTY": "^NSEI", "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK",
    "NIFTYBANK": "^NSEBANK", "SENSEX": "^BSESN",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS", "MIDCPNIFTY": "NIFTY_MID_SELECT.NS",
}

# Edit these in trader/config.json. They are examples, not advice.
# lot_sizes were Nifty 65, Bank Nifty 30, Sensex 20 as of Nov 2026. NSE revises
# lot sizes, so confirm each one in your broker app before you size a trade.
DEFAULTS = {
    "capital_inr": 10000,
    "cash_buffer_pct": 10,
    "max_loss_per_trade_inr": 500,
    "max_daily_loss_inr": 1000,
    "max_trades_per_day": 2,
    "max_position_pct": 100,
    "min_reward_risk": 1.5,
    "require_stop": True,
    "no_entries_before": "09:30",
    "no_entries_after": "14:45",
    "flat_by": "15:15",
    "brokerage_per_order_inr": 20,
    "other_charges_pct": 0.05,
    "min_days_to_expiry": 2,
    "allow_options": True,
    "blocked": [],
    "paper": True,
    "lot_sizes": {"NIFTY": 65, "BANKNIFTY": 30, "FINNIFTY": 60,
                  "MIDCPNIFTY": 120, "SENSEX": 20},
}


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def parse_clock(s):
    h, m = str(s).split(":")[:2]
    return dt.time(int(h), int(m))


def now_ist(pin=None):
    """Current time in India. pin='YYYY-MM-DD HH:MM' (IST) replays a day."""
    if pin:
        return dt.datetime.strptime(pin, "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    return dt.datetime.now(IST)


def yahoo_symbol(s):
    s = s.strip().upper()
    if s in INDEX_MAP:
        return INDEX_MAP[s]
    if s.startswith("^") or "." in s:
        return s
    return s + ".NS"


def short_symbol(s):
    s = s.strip().upper()
    return s[:-3] if s.endswith(".NS") else s.lstrip("^")


def inr(x, dec=2):
    """Rupees with Indian digit grouping: 1,23,456.00"""
    neg = x < 0
    s = "%.*f" % (dec, abs(x))
    ip, _, fp = s.partition(".")
    if len(ip) > 3:
        head, tail = ip[:-3], ip[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        ip = ",".join(parts + [tail])
    return ("-" if neg else "") + "₹" + ip + ("." + fp if dec else "")


# ---------------------------------------------------------------- network
def http_get(url, timeout=20, retries=2, headers=None, pause=0.4):
    h = {"User-Agent": UA, "Accept": "*/*"}
    h.update(headers or {})
    last = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = "HTTP %d" % e.code
            if e.code in (400, 403, 404):
                break
        except (urllib.error.URLError, OSError) as e:
            last = str(e)
        time.sleep(pause * (i + 1))
    raise RuntimeError("could not fetch %s (%s)" % (url, last))


def chart_url(symbol, rng, interval):
    return ("https://query1.finance.yahoo.com/v8/finance/chart/%s"
            "?range=%s&interval=%s&includePrePost=false"
            % (urllib.parse.quote(yahoo_symbol(symbol)), rng, interval))


def parse_chart(obj):
    """Yahoo chart JSON -> {'meta': {...}, 'bars': [ {t,o,h,l,c,v} ]}.
    t is a timezone-aware datetime in IST and is the bar's START time.
    Bars with a missing price are dropped."""
    try:
        res = obj["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
    except (KeyError, IndexError, TypeError):
        raise ValueError("no chart data in response")
    bars = []
    for i, t in enumerate(res.get("timestamp") or []):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        bars.append({"t": dt.datetime.fromtimestamp(t, IST), "o": float(o),
                     "h": float(h), "l": float(l), "c": float(c),
                     "v": float(q["volume"][i] or 0)})
    return {"meta": res.get("meta") or {}, "bars": bars}


def load_chart_file(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def get_chart(symbol, rng="1d", interval="5m", offline=None):
    """Fetch (or read from --offline FILE or a folder of <SYMBOL>.json)."""
    if offline:
        path = offline
        if os.path.isdir(path):
            base = short_symbol(symbol)
            for ext in (".json", ".json.gz"):
                cand = os.path.join(path, base + ext)
                if os.path.exists(cand):
                    path = cand
                    break
            else:
                raise RuntimeError("no offline file for %s in %s" % (symbol, offline))
        return parse_chart(load_chart_file(path))
    raw = http_get(chart_url(symbol, rng, interval))
    return parse_chart(json.loads(raw.decode("utf-8")))


def closed_bars(bars, interval, now):
    """Only bars that have finished by `now` count (a bar is closed once its
    start plus its length has passed)."""
    n = dt.timedelta(minutes=INTERVAL_MIN.get(interval, 5))
    return [b for b in bars if b["t"] + n <= now]


def session_bars(bars, day):
    return [b for b in bars if b["t"].date() == day]


# ------------------------------------------------------------- indicators
def sma(vals, n):
    return sum(vals[-n:]) / n if len(vals) >= n else None


def rsi(closes, n=14):
    if len(closes) <= n:
        return None
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / n, losses / n
    for i in range(n + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)


def atr(bars, n=14):
    if len(bars) < n + 1:
        return None
    trs = []
    for i in range(1, len(bars)):
        p = bars[i - 1]["c"]
        b = bars[i]
        trs.append(max(b["h"] - b["l"], abs(b["h"] - p), abs(b["l"] - p)))
    a = sum(trs[:n]) / n
    for tr in trs[n:]:
        a = (a * (n - 1) + tr) / n
    return a


# ------------------------------------------------------- files and config
def trader_dir(create=True):
    d = os.environ.get("TRADER_DIR") or os.path.join(os.getcwd(), "trader")
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def load_json(name, default=None):
    p = os.path.join(trader_dir(False), name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(name, obj):
    p = os.path.join(trader_dir(), name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)
    return p


def load_config():
    cfg = json.loads(json.dumps(DEFAULTS))
    user = load_json("config.json", {}) or {}
    for k, v in user.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    return cfg


def read_csv_text(text):
    return list(csv.DictReader(io.StringIO(text)))


def fmt_time(t):
    return t.astimezone(IST).strftime("%H:%M")


DISCLAIMER = ("Most people who trade lose money. This is a calculation and a "
              "plan, not advice or a prediction. It cannot place an order.")
