"""Tests for the India trader skills. Synthetic data only: no network needed.
Run:  python3 tests/test_all.py   (from the repo root, after ./build.sh)
"""
import datetime as dt
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "_shared"))
import inmkt as m  # noqa: E402

IST = m.IST


def chart(bars, price=None):
    return {"chart": {"result": [{
        "meta": {"regularMarketPrice": price if price is not None else bars[-1]["c"]},
        "timestamp": [int(b["t"].timestamp()) for b in bars],
        "indicators": {"quote": [{
            "open": [b["o"] for b in bars], "high": [b["h"] for b in bars],
            "low": [b["l"] for b in bars], "close": [b["c"] for b in bars],
            "volume": [b.get("v", 100000) for b in bars]}]}}]}}


def bar(day, hh, mm, o, h, l, c, v=100000):
    return {"t": dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=IST), "o": o, "h": h, "l": l, "c": c, "v": v}


def engineered_day(day):
    return [
        bar(day, 9, 15, 99.8, 100.0, 99.5, 99.9),
        bar(day, 9, 20, 99.9, 99.95, 99.6, 99.7),
        bar(day, 9, 25, 99.7, 99.9, 99.4, 99.5),
        bar(day, 9, 30, 99.5, 100.6, 99.4, 99.8),     # wick above the range, close below: NOT a trigger
        bar(day, 9, 35, 99.8, 100.7, 99.7, 100.5, 250000),  # closes above: trigger, bar closes 09:40
        bar(day, 9, 40, 100.5, 100.9, 100.4, 100.6),
    ]


def random_day(day, base, rnd):
    bars, p, t = [], base, dt.datetime(day.year, day.month, day.day, 9, 15, tzinfo=IST)
    for _ in range(75):
        c = p * (1 + rnd.gauss(0, 0.0009))
        bars.append({"t": t, "o": p, "h": max(p, c) * 1.0004, "l": min(p, c) * 0.9996, "c": c, "v": rnd.randint(50000, 150000)})
        p, t = c, t + dt.timedelta(minutes=5)
    return bars


def weekdays_back(end, n):
    out, d = [], end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= dt.timedelta(days=1)
    return sorted(out)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.env = dict(os.environ, TRADER_DIR=os.path.join(self.dir, "trader"))

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, obj):
        p = os.path.join(self.dir, name)
        with open(p, "w") as f:
            json.dump(obj, f)
        return p

    def run_skill(self, skill, script, *args, expect=None):
        r = subprocess.run([sys.executable, os.path.join(ROOT, skill, script)] + list(args),
                           capture_output=True, text=True, env=self.env, cwd=self.dir)
        if expect is not None:
            self.assertEqual(r.returncode, expect, r.stdout + r.stderr)
        return r

    def trader(self, name):
        with open(os.path.join(self.dir, "trader", name)) as f:
            return json.load(f)

    def config(self, **kw):
        os.makedirs(os.path.join(self.dir, "trader"), exist_ok=True)
        with open(os.path.join(self.dir, "trader", "config.json"), "w") as f:
            json.dump(kw, f)


class TestShared(unittest.TestCase):
    def test_inr_grouping(self):
        self.assertEqual(m.inr(123456.5), "₹1,23,456.50")
        self.assertEqual(m.inr(999, 0), "₹999")
        self.assertEqual(m.inr(-1500, 0), "-₹1,500")
        self.assertEqual(m.inr(12345678, 0), "₹1,23,45,678")

    def test_symbols(self):
        self.assertEqual(m.yahoo_symbol("reliance"), "RELIANCE.NS")
        self.assertEqual(m.yahoo_symbol("NIFTY"), "^NSEI")
        self.assertEqual(m.yahoo_symbol("BANKNIFTY"), "^NSEBANK")
        self.assertEqual(m.yahoo_symbol("TCS.NS"), "TCS.NS")
        self.assertEqual(m.short_symbol("TCS.NS"), "TCS")

    def test_parse_chart_drops_missing(self):
        d = dt.date(2026, 11, 23)
        c = chart(engineered_day(d))
        c["chart"]["result"][0]["indicators"]["quote"][0]["close"][2] = None
        self.assertEqual(len(m.parse_chart(c)["bars"]), 5)

    def test_closed_bars(self):
        d = dt.date(2026, 11, 23)
        bars = m.parse_chart(chart(engineered_day(d)))["bars"]
        now = dt.datetime(2026, 11, 23, 9, 36, tzinfo=IST)
        self.assertEqual(len(m.closed_bars(bars, "5m", now)), 4)

    def test_indicators(self):
        self.assertEqual(m.rsi([float(i) for i in range(30)]), 100.0)
        self.assertAlmostEqual(m.sma([1, 2, 3, 4], 2), 3.5)


class TestEntryExit(Base):
    def setUp(self):
        super().setUp()
        self.day = dt.date(2026, 11, 23)
        self.f = self.put("TCS.json", chart(engineered_day(self.day)))

    def test_wick_is_not_a_trigger_and_open_bar_does_not_count(self):
        r = self.run_skill("in-entry", "entry.py", "check", "TCS", "--offline", self.f, "--now", "2026-11-23 09:36", expect=1)
        self.assertIn("WAITING", r.stdout)

    def test_trigger_time_is_bar_close(self):
        r = self.run_skill("in-entry", "entry.py", "check", "TCS", "--offline", self.f, "--now", "2026-11-23 09:41", "--write", expect=0)
        self.assertIn("09:40 IST", r.stdout)
        e = self.trader("entry.json")
        self.assertEqual(e["price"], 100.5)
        self.assertEqual(e["or_high"], 100.0)
        self.assertAlmostEqual(e["or_mid"], 99.7)

    def test_too_early_before_0930(self):
        # a breakout whose bar closes before 09:30 is reported but is not a trigger
        d = self.day
        bars = [bar(d, 9, 15, 99, 100, 98, 99.5), bar(d, 9, 20, 99.5, 100, 99, 99.6), bar(d, 9, 25, 99.6, 100, 99.2, 99.7),
                bar(d, 9, 30, 99.7, 101, 99.7, 100.9)]
        f = self.put("RIL.json", chart(bars))
        r = self.run_skill("in-entry", "entry.py", "check", "RIL", "--offline", f, "--now", "2026-11-23 09:36", "--setup", "level", "--level", "100.5")
        self.assertEqual(r.returncode, 0)  # 09:35 close is after 09:30: valid
        r2 = self.run_skill("in-entry", "entry.py", "check", "RIL", "--offline", f, "--now", "2026-11-23 09:36", "--or-minutes", "5")
        self.assertIn("TRIGGER", r2.stdout)

    def test_watch_replays_to_trigger(self):
        r = self.run_skill("in-entry", "entry.py", "watch", "TCS", "--offline", self.f, "--now", "2026-11-23 09:30", "--until", "09:55", expect=0)
        self.assertIn("TRIGGER", r.stdout)

    def test_exit_plan_or_mid_2r(self):
        self.run_skill("in-entry", "entry.py", "check", "TCS", "--offline", self.f, "--now", "2026-11-23 09:41", "--write", expect=0)
        r = self.run_skill("in-exit", "exit.py", "plan", "--write", expect=0)
        p = self.trader("plan.json")
        self.assertAlmostEqual(p["stop"], 99.7)
        self.assertAlmostEqual(p["risk_per_share"], 0.8)
        self.assertAlmostEqual(p["target"], 102.1)
        self.assertAlmostEqual(p["reward_risk"], 2.0)
        self.assertEqual(p["flat_by"], "15:15")

    def test_exit_rejects_stop_above_entry(self):
        self.run_skill("in-exit", "exit.py", "plan", "--symbol", "TCS", "--entry", "100", "--stop", "price:101", expect=1)

    def test_exit_pct_and_price_target(self):
        r = self.run_skill("in-exit", "exit.py", "plan", "--symbol", "TCS", "--entry", "3200", "--stop", "pct:1", "--target", "price:3264", "--write", expect=0)
        p = self.trader("plan.json")
        self.assertAlmostEqual(p["stop"], 3168.0)
        self.assertAlmostEqual(p["reward_risk"], 2.0)


class TestBudgetRisk(Base):
    def test_cash_size_binds_on_cash(self):
        r = self.run_skill("in-budget", "size.py", "cash", "--symbol", "RELIANCE", "--entry", "1480", "--stop", "1465", "--target", "1510", "--write", expect=0)
        o = self.trader("orders.json")
        self.assertEqual(o["qty"], 6)          # 9,000 usable // 1,480 = 6 (max-loss limit would allow 33)
        self.assertAlmostEqual(o["max_loss"], 90.0)
        self.assertIn("binds", r.stdout)

    def test_cash_size_binds_on_loss(self):
        self.config(capital_inr=100000, max_loss_per_trade_inr=300)
        self.run_skill("in-budget", "size.py", "cash", "--symbol", "ABC", "--entry", "100", "--stop", "98", "--write", expect=0)
        self.assertEqual(self.trader("orders.json")["qty"], 150)   # 300 // 2

    def test_cash_zero_shares(self):
        r = self.run_skill("in-budget", "size.py", "cash", "--symbol", "MRF", "--entry", "130000", "--stop", "129000", expect=1)
        self.assertIn("0 shares", r.stdout)

    def test_option_one_lot_too_big_for_limits(self):
        r = self.run_skill("in-budget", "size.py", "option", "--underlying", "NIFTY", "--premium", "100", "--stop-premium", "70", expect=1)
        self.assertIn("0 lots", r.stdout)
        self.assertIn("1,950", r.stdout)   # 30 x 65

    def test_option_fits_when_limit_allows(self):
        self.config(max_loss_per_trade_inr=2000)
        self.run_skill("in-budget", "size.py", "option", "--underlying", "NIFTY", "--premium", "100", "--stop-premium", "70",
                       "--target-premium", "160", "--contract", "NIFTY 25900 CE", "--expiry", "2026-12-02", "--write", expect=0)
        o = self.trader("orders.json")
        self.assertEqual((o["lots"], o["qty"], o["lot_size"]), (1, 65, 65))
        self.assertAlmostEqual(o["max_loss"], 1950.0)
        self.assertAlmostEqual(o["reward_risk"], 2.0)

    def test_option_delta_estimate(self):
        self.config(max_loss_per_trade_inr=2000)
        r = self.run_skill("in-budget", "size.py", "option", "--underlying", "BANKNIFTY", "--premium", "120",
                           "--delta", "0.5", "--underlying-stop-pts", "40", expect=0)
        self.assertIn("buy 2 lot(s) = 60 units", r.stdout)   # stop 100, loss 20 x 30 = 600; cash 9000 // 3600 = 2; loss 2000 // 600 = 3 -> 2
        self.assertIn("rough guess", r.stdout)

    def test_option_unknown_underlying_needs_lot(self):
        self.run_skill("in-budget", "size.py", "option", "--underlying", "XYZ", "--premium", "10", "--stop-premium", "8", expect=1)

    def test_blocked_symbol(self):
        self.config(blocked=["ABC"])
        self.run_skill("in-budget", "size.py", "cash", "--symbol", "ABC", "--entry", "100", "--stop", "98", expect=1)

    def good_order(self, **kw):
        o = {"kind": "cash", "symbol": "RELIANCE", "side": "buy", "qty": 6, "entry": 1480.0, "stop": 1465.0, "target": 1510.0,
             "cost": 8880.0, "max_loss": 90.0, "reward_risk": 2.0, "date": "2026-11-23"}
        o.update(kw)
        return self.put("orders.json", o)

    def test_risk_pass(self):
        p = self.good_order()
        r = self.run_skill("in-risk", "check.py", "--orders", p, "--now", "2026-11-23 10:30", expect=0)
        self.assertIn("no blocks", r.stdout)

    def test_risk_blocks(self):
        for bad, word in ((dict(stop=None), "stop"), (dict(stop=1500.0), "not below"), (dict(max_loss=900.0), "over your"),
                          (dict(cost=9500.0), "cash buffer"), (dict(date="2026-11-20"), "not today"), (dict(qty=0), "zero")):
            p = self.good_order(**bad)
            r = self.run_skill("in-risk", "check.py", "--orders", p, "--now", "2026-11-23 10:30", expect=2)
            self.assertIn(word, r.stdout, bad)

    def test_risk_warns_on_time_and_rr(self):
        p = self.good_order(reward_risk=1.0)
        r = self.run_skill("in-risk", "check.py", "--orders", p, "--now", "2026-11-23 15:00", expect=0)
        self.assertIn("WARN  reward:risk", r.stdout)
        self.assertIn("after 14:45", r.stdout)

    def test_risk_market_closed_weekend(self):
        p = self.good_order(date="2026-11-21")
        r = self.run_skill("in-risk", "check.py", "--orders", p, "--now", "2026-11-21 11:00", expect=0)
        self.assertIn("NSE is closed", r.stdout)

    def test_risk_option_lot_rounding_and_expiry(self):
        p = self.put("orders.json", {"kind": "option", "underlying": "NIFTY", "option": "NIFTY 25900 CE", "qty": 70, "lot_size": 65,
                                      "entry": 20.0, "stop": 15.0, "cost": 1400.0, "max_loss": 350.0, "reward_risk": 2.0,
                                      "expiry": "2026-11-24", "date": "2026-11-23"})
        r = self.run_skill("in-risk", "check.py", "--orders", p, "--now", "2026-11-23 10:30", expect=2)
        self.assertIn("whole number", r.stdout)
        self.assertIn("1 day(s) to expiry", r.stdout)

    def test_risk_daily_and_trade_limits_from_journal(self):
        os.makedirs(os.path.join(self.dir, "trader"), exist_ok=True)
        j = {"trades": [{"id": 1, "date": "2026-11-23", "status": "closed", "pnl": -950.0},
                        {"id": 2, "date": "2026-11-23", "status": "closed", "pnl": 10.0}]}
        with open(os.path.join(self.dir, "trader", "journal.json"), "w") as f:
            json.dump(j, f)
        p = self.good_order()
        r = self.run_skill("in-risk", "check.py", "--orders", p, "--now", "2026-11-23 10:30", expect=2)
        self.assertIn("already made 2 trades", r.stdout)
        self.assertIn("daily limit", r.stdout)


class TestTicket(Base):
    def test_ticket_log_close_summary(self):
        self.run_skill("in-budget", "size.py", "cash", "--symbol", "RELIANCE", "--entry", "1480", "--stop", "1465", "--target", "1510", "--write", expect=0)
        r = self.run_skill("in-ticket", "ticket.py", "show", expect=0)
        self.assertIn("BUY", r.stdout)
        self.assertIn("STOP-LOSS", r.stdout)
        self.assertNotIn("api", r.stdout.lower().replace("capital", ""))   # no broker API talk
        self.run_skill("in-ticket", "ticket.py", "log", "--now", "2026-11-23 10:00", expect=0)
        r = self.run_skill("in-ticket", "ticket.py", "close", "--id", "1", "--exit", "1510", expect=0)
        j = self.trader("journal.json")["trades"][0]
        self.assertEqual(j["status"], "closed")
        self.assertAlmostEqual(j["pnl"], 6 * 30 - j["charges"], places=1)
        s = self.run_skill("in-ticket", "ticket.py", "summary", expect=0)
        self.assertIn("1 wins", s.stdout)

    def test_option_ticket(self):
        self.config(max_loss_per_trade_inr=2000)
        self.run_skill("in-budget", "size.py", "option", "--underlying", "NIFTY", "--premium", "100", "--stop-premium", "70",
                       "--contract", "NIFTY 25900 CE", "--write", expect=0)
        r = self.run_skill("in-ticket", "ticket.py", "show", expect=0)
        self.assertIn("NIFTY 25900 CE", r.stdout)
        self.assertIn("65 units", r.stdout)

    def test_no_orders_file(self):
        self.run_skill("in-ticket", "ticket.py", "show", expect=1)


class TestScanner(Base):
    def test_daily_breakout_and_flat(self):
        rnd = random.Random(1)
        days = weekdays_back(dt.date(2026, 11, 20), 70)
        bars, p = [], 100.0
        for i, d in enumerate(days):
            c = p * (1 + rnd.uniform(-0.004, 0.004)) if i < len(days) - 1 else 112.0
            bars.append({"t": dt.datetime(d.year, d.month, d.day, 9, 15, tzinfo=IST), "o": p, "h": max(p, c) * 1.002, "l": min(p, c) * 0.998, "c": c, "v": 600000})
            p = c
        flat = [dict(b, c=100.0 + (i % 3) * 0.1, o=100.0, h=100.4, l=99.6) for i, b in enumerate(bars)]
        os.makedirs(os.path.join(self.dir, "off"))
        for name, bs in (("BRK", bars), ("FLAT", flat)):
            with open(os.path.join(self.dir, "off", name + ".json"), "w") as f:
                json.dump(chart(bs), f)
        r = self.run_skill("in-scanner", "scan.py", "daily", "--symbols", "BRK,FLAT", "--offline", os.path.join(self.dir, "off"), expect=0)
        self.assertIn("BRK", r.stdout)
        self.assertNotIn("FLAT ", r.stdout.replace("failed", ""))
        wl = self.trader("watchlist.json")
        self.assertEqual([h["symbol"] for h in wl["hits"]], ["BRK"])
        self.assertTrue(any("breakout" in s for s in wl["hits"][0]["setups"]))

    def test_orb(self):
        f = self.put("TCS.json", chart(engineered_day(dt.date(2026, 11, 23))))
        r = self.run_skill("in-scanner", "scan.py", "orb", "--symbols", "TCS", "--offline", f, "--now", "2026-11-23 09:45", expect=0)
        self.assertIn("opening-range breakout", r.stdout)
        self.assertEqual(self.trader("watchlist.json")["hits"][0]["trigger_time"], "09:40")

    def test_universe_from_file(self):
        csvp = os.path.join(self.dir, "EQUITY_L.csv")
        open(csvp, "w").write("SYMBOL,NAME OF COMPANY, SERIES,DATE OF LISTING\nRELIANCE,Reliance Industries Limited,EQ,x\nFOO,Foo Ltd,BE,x\nTCS,Tata Consultancy Services Limited,EQ,x\n")
        self.run_skill("in-scanner", "scan.py", "universe", "--file", csvp, expect=0)
        txt = open(os.path.join(self.dir, "trader", "universe.txt")).read().split("\n")
        self.assertIn("RELIANCE|Reliance Industries Limited", txt)
        self.assertNotIn("FOO|Foo Ltd", txt)


class TestTimeMachine(Base):
    def test_run_on_synthetic_history(self):
        rnd = random.Random(7)
        bars, p = [], 1000.0
        for d in weekdays_back(dt.date(2026, 11, 20), 60):
            day = random_day(d, p, rnd)
            bars += day
            p = day[-1]["c"]
        f = self.put("RELIANCE.json", chart(bars))
        r = self.run_skill("in-timemachine", "timemachine.py", "run", "--symbol", "RELIANCE", "--entry", "1000", "--stop", "995",
                           "--target", "1010", "--offline", f, "--sims", "2000", expect=0)
        self.assertIn("target first", r.stdout)
        self.assertIn("Break-even", r.stdout)
        shares = [float(x.split("%")[0].split()[-1]) for x in r.stdout.splitlines() if x.strip().startswith(("target first", "stop first", "neither"))][:3]
        self.assertAlmostEqual(sum(shares), 100.0, delta=0.5)

    def test_rejects_bad_plan_and_thin_data(self):
        f = self.put("X.json", chart(engineered_day(dt.date(2026, 11, 23))))
        self.run_skill("in-timemachine", "timemachine.py", "run", "--symbol", "X", "--entry", "100", "--stop", "101", "--target", "102", "--offline", f, expect=1)
        self.run_skill("in-timemachine", "timemachine.py", "run", "--symbol", "X", "--entry", "100", "--stop", "99", "--target", "102", "--offline", f, expect=1)


class TestAlerts(Base):
    def test_add_check_fire(self):
        d = dt.date(2026, 11, 23)
        f = self.put("RELIANCE.json", chart(engineered_day(d), price=1511.0))
        self.run_skill("in-alerts", "alerts.py", "add", "RELIANCE", "above", "1510", "--label", "target", expect=0)
        self.run_skill("in-alerts", "alerts.py", "add", "RELIANCE", "below", "1450", "--label", "STOP", expect=0)
        r = self.run_skill("in-alerts", "alerts.py", "check", "--offline", f, expect=0)
        self.assertIn("ALERT RELIANCE went above", r.stdout)
        self.assertNotIn("went below", r.stdout)
        r = self.run_skill("in-alerts", "alerts.py", "list", expect=0)
        self.assertIn("[fired", r.stdout)

    def test_from_plan(self):
        self.run_skill("in-exit", "exit.py", "plan", "--symbol", "TCS", "--entry", "3200", "--stop", "price:3170", "--target", "2R", "--write", expect=0)
        self.run_skill("in-alerts", "alerts.py", "from-plan", expect=0)
        a = self.trader("alerts.json")["alerts"]
        self.assertEqual({x["label"] for x in a}, {"STOP", "TARGET"})

    def test_clock(self):
        r = self.run_skill("in-alerts", "alerts.py", "clock", "--now", "2026-11-23 15:00", expect=0)
        self.assertIn("Market open", r.stdout)
        self.assertIn("minutes to the close", r.stdout)
        r = self.run_skill("in-alerts", "alerts.py", "clock", "--now", "2026-11-21 11:00", expect=0)
        self.assertIn("weekend", r.stdout)
        r = self.run_skill("in-alerts", "alerts.py", "clock", "--now", "2026-11-23 15:20", expect=0)
        self.assertIn("Past your flat-by", r.stdout)


class TestAnalystDealsNews(Base):
    def test_analyst(self):
        t = self.run_skill("in-analyst", "facts.py", "template", expect=0).stdout
        p = os.path.join(self.dir, "r.json")
        open(p, "w").write(t)
        r = self.run_skill("in-analyst", "facts.py", "read", p, expect=0)
        self.assertIn("Q2 FY26", r.stdout)
        self.assertIn("+15.0%", r.stdout)      # revenue 1150 vs 1000 a year ago
        self.assertIn("-1.7%", r.stdout)       # PAT 118 vs 120 a year ago
        self.assertIn("EBITDA margin fell", r.stdout)

    def test_analyst_csv(self):
        p = os.path.join(self.dir, "r.csv")
        open(p, "w").write("period,revenue,ebitda,pat,eps\nA,100,20,10,1\nB,100,20,10,1\nC,100,20,10,1\nD,100,20,10,1\nE,150,30,5,0.5\n")
        r = self.run_skill("in-analyst", "facts.py", "read", p, expect=0)
        self.assertIn("down 50% from a year ago", r.stdout)
        self.assertIn("up 50% from a year ago", r.stdout)

    def test_deals(self):
        p = os.path.join(self.dir, "bulk.csv")
        open(p, "w").write(
            "Date,Symbol,Security Name,Client Name,Buy/Sell,Quantity Traded,Trade Price / Wght. Avg. Price,Remarks\n"
            '21-NOV-2026,ABC,ABC Ltd,Big Fund,BUY,"5,00,000" ,100.00,-\n'.replace("5,00,000", "500000") +
            "21-NOV-2026,ABC,ABC Ltd,Other Fund,SELL,100000,101.00,-\n"
            "21-NOV-2026,XYZ,XYZ Ltd,Small Co,SELL,1000,50,-\n")
        r = self.run_skill("in-deals", "deals.py", "summary", "--file", p, expect=0)
        self.assertIn("3 deals", r.stdout)
        self.assertIn("+", r.stdout)
        r = self.run_skill("in-deals", "deals.py", "summary", "--file", p, "--symbol", "ABC", "--min-crore", "1", expect=0)
        self.assertIn("2 deals", r.stdout)
        self.run_skill("in-deals", "deals.py", "summary", "--file", p, "--symbol", "NOPE", expect=1)

    def test_news_offline(self):
        xml = ('<?xml version="1.0"?><rss><channel>'
               '<item><title>TCS Q2 net profit rises 8%</title><link>http://x/1</link><pubDate>Mon, 23 Nov 2026 03:00:00 GMT</pubDate></item>'
               '<item><title>TCS Q2 net profit rises 8%</title><link>http://x/2</link><pubDate>Mon, 23 Nov 2026 03:05:00 GMT</pubDate></item>'
               '<item><title>SEBI notice to a TCS vendor</title><link>http://x/3</link><pubDate>Mon, 23 Nov 2026 02:00:00 GMT</pubDate></item>'
               '<item><title>Old story from last year</title><link>http://x/4</link><pubDate>Mon, 03 Nov 2025 02:00:00 GMT</pubDate></item>'
               '</channel></rss>')
        os.makedirs(os.path.join(self.dir, "rss"))
        open(os.path.join(self.dir, "rss", "TCS.xml"), "w").write(xml)
        r = self.run_skill("in-news", "news.py", "check", "TCS", "--offline-dir", os.path.join(self.dir, "rss"), "--now", "2026-11-23 10:00", "--hours", "24", expect=0)
        self.assertIn("2 headlines", r.stdout)       # duplicate dropped, old story filtered
        self.assertIn("results", r.stdout)
        self.assertIn("regulatory", r.stdout)
        self.assertNotIn("Old story", r.stdout)


class TestRepo(unittest.TestCase):
    def test_every_skill_is_complete(self):
        names = sorted(d for d in os.listdir(ROOT) if d.startswith("in-"))
        self.assertEqual(len(names), 11)
        shared = open(os.path.join(ROOT, "_shared", "inmkt.py")).read()
        for n in names:
            md = open(os.path.join(ROOT, n, "SKILL.md")).read()
            self.assertTrue(md.startswith("---\nname: %s\n" % n), n)
            self.assertIn("description:", md)
            self.assertIn("CLAUDE_SKILL_DIR", md, n)
            self.assertEqual(open(os.path.join(ROOT, n, "inmkt.py")).read(), shared, "%s has a stale inmkt.py: run ./build.sh" % n)
            py = [f for f in os.listdir(os.path.join(ROOT, n)) if f.endswith(".py") and f != "inmkt.py"]
            self.assertEqual(len(py), 1, n)
            self.assertIn(py[0], md, n)

    def test_nothing_can_place_an_order(self):
        # no skill may talk to a broker or send orders
        for d in os.listdir(ROOT):
            if not d.startswith("in-"):
                continue
            for f in os.listdir(os.path.join(ROOT, d)):
                if f.endswith(".py"):
                    src = open(os.path.join(ROOT, d, f)).read().lower()
                    for bad in ("api.upstox", "placeorder", "place_order", "access_token", "api_key", "apikey", "password"):
                        self.assertNotIn(bad, src, "%s/%s mentions %s" % (d, f, bad))


if __name__ == "__main__":
    unittest.main(verbosity=1)
