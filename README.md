# India Trader Skills for Claude Code (NSE)

Eleven skills that help you plan trades in the Indian market, step by step: find stocks,
check news, time the entry, set the stop-loss and target, work out how many shares or
lots to buy, check your risk, and practise on paper.

- Works with NSE stocks, the Nifty 50 index, Bank Nifty, Sensex and Nifty option lots.
- Uses Indian time (09:15 to 15:30 IST) and rupees.
- Free. Plain Python, nothing to pip install.
- **It cannot place an order.** It has no broker connection and asks for no passwords or keys.
  You place every real order yourself in Upstox (or any broker).

> **Read this first.** Most people who trade lose money. SEBI studies found that around nine
> in ten individual F&O traders lost money in recent years. These skills do arithmetic and
> keep you disciplined. They do not predict the market and they are not financial advice.
> Practise on paper before you use real money, and only trade money you can afford to lose.

---

## Contents

1. [What you need](#1-what-you-need)
2. [Setup (one time)](#2-setup-one-time)
3. [Set your limits (one time)](#3-set-your-limits-one-time)
4. [How to use it: a trading day, step by step](#4-how-to-use-it-a-trading-day-step-by-step)
5. [How to scan the market](#5-how-to-scan-the-market)
6. [The 11 skills at a glance](#6-the-11-skills-at-a-glance)
7. [Options: how lots and stop-loss work here](#7-options-how-lots-and-stop-loss-work-here)
8. [Paper trading](#8-paper-trading)
9. [Troubleshooting](#9-troubleshooting)
10. [What was tested, and what was not](#10-what-was-tested-and-what-was-not)
11. [Uninstall and update](#11-uninstall-and-update)

---

## 1. What you need

- A Mac or Linux computer (Windows: see the note in step 2).
- **Claude Code**, the coding version of Claude. Use it from the Claude desktop app (the `</>`
  button) or from Terminal by typing `claude`.
- **Python 3.8 or newer.** Check with `python3 --version` in Terminal.
- An internet connection when you scan. Prices come from Yahoo Finance's free feed, which is
  **delayed** and can have gaps. Always check the live price in your broker app before you act.

## 2. Setup (one time)

**Step 1. Unzip.** Double-click `india-trader.zip` (for example in Downloads). You get a folder
called `india-trader`.

**Step 2. Install.** Open Terminal and run:

```bash
cd ~/Downloads/india-trader
./install.sh
```

If it says "permission denied", run `chmod +x install.sh build.sh` first, then try again.
This copies the 11 skill folders (`in-alerts`, `in-analyst`, `in-budget`, `in-deals`,
`in-entry`, `in-exit`, `in-news`, `in-risk`, `in-scanner`, `in-ticket`, `in-timemachine`)
into `~/.claude/skills/`.

*Windows:* `install.sh` does not run there. Do it by hand: copy `_shared\inmkt.py` into every `in-*` folder
(the zip already includes a copy in each, so you can skip this), then copy the 11 `in-*` folders into
`C:\Users\<you>\.claude\skills\`. Use `python` where this guide says `python3`.

**Step 3. Check the install.**

```bash
ls ~/.claude/skills
```

You should see the 11 `in-` folders.

**Step 4. Open Claude Code and look for the skills.** Close Claude Code completely and open it
again (skills are only read when a session starts). Then type `/in-`. You should see all 11.

> The normal Claude chat window does **not** show these. They only work inside **Claude Code**.

**Step 5. Make a trading folder.** The tools save your plan, limits and journal in a folder
called `trader/` inside whatever folder you opened. Use the same folder every time:

```bash
mkdir -p ~/trading
cd ~/trading
claude
```

(Or choose `~/trading` when the desktop app asks for a folder.)

## 3. Set your limits (one time)

In Claude Code, inside your trading folder, type:

```
/in-budget config
```

Claude will ask for your capital and limits and save them in `trader/config.json`. You can also
create the file yourself. Copy `in-budget/config.example.json` to `trader/config.json` and edit it:

| setting | meaning | default |
| --- | --- | --- |
| `capital_inr` | money you trade with | 10000 |
| `cash_buffer_pct` | share of capital that always stays in cash | 10 |
| `max_loss_per_trade_inr` | most one trade may lose if its stop-loss fills | 500 |
| `max_daily_loss_inr` | stop trading for the day after this much loss | 1000 |
| `max_trades_per_day` | trades allowed per day | 2 |
| `min_reward_risk` | smallest acceptable reward divided by risk | 1.5 |
| `no_entries_before` / `no_entries_after` | entry window (IST) | 09:30 / 14:45 |
| `flat_by` | close intraday trades by this time (IST) | 15:15 |
| `brokerage_per_order_inr` | flat brokerage per order, for the charges estimate | 20 |
| `other_charges_pct` | taxes and fees as a percent of turnover (rough) | 0.05 |
| `allow_options` | allow option sizing | true |
| `blocked` | stocks you never want to trade | [] |
| `lot_sizes` | lot size per index. **NSE changes these. Check your broker app.** | Nifty 65, Bank Nifty 30, Sensex 20 |

Tips:
- A per-trade loss limit of 1% to 5% of capital is common. A very large limit (like 20%) means a
  few losing trades can wipe out the account. The numbers are your decision.
- With a small account (for example ₹10,000), one lot of a Nifty option can cost more than your
  whole loss limit. The tool will then say **0 lots** instead of letting you take the trade.

## 4. How to use it: a trading day, step by step

You type these in Claude Code (they are skills, so they start with `/`). Each step uses the
result of the one before it. The order is:

**scan → news → entry → exit → timemachine → budget → risk → ticket → (you place the order) → alerts → close**

| Step | When (IST) | Command | What you get |
| --- | --- | --- | --- |
| 1. Find candidates | after 15:30 the day before, or before 09:15 | `/in-scanner daily --symbols RELIANCE,TCS,INFY` | a list of charts with a setup |
| 2. Check news | before the open | `/in-news check RELIANCE TCS` | headlines, flagged (results, SEBI, orders, etc.) |
| 3. Wait for the entry | after 09:30 | `/in-entry check RELIANCE --write` | the exact candle that confirms the breakout |
| 4. Plan the exit | before you enter | `/in-exit plan --write` | stop-loss, target, reward:risk |
| 5. Test the plan | before you enter | `/in-timemachine run` | how often the target or stop came first in the past |
| 6. Size it | before you enter | `/in-budget cash --write` | exact number of shares |
| 7. Check risk | before you enter | `/in-risk` | PASS, WARN or BLOCK |
| 8. Make the ticket | if no BLOCK | `/in-ticket show` | a ticket you copy into Upstox by hand |
| 9. Place the order | you do this | (in the Upstox app) | buy, then **place the stop-loss order immediately** |
| 10. Set alerts | after buying | `/in-alerts from-plan` then `/in-alerts watch` | bell when stop or target is hit |
| 11. Record the result | after selling | `/in-ticket close --id 1 --exit 1503.5` | your result after charges |

You can also just tell Claude what you want in plain words, for example "scan Nifty 50 for setups"
or "how many shares of RELIANCE can I buy with entry 1480 and stop 1465". Claude picks the skill.

### A worked example

```
/in-entry check RELIANCE --write
```
Suppose it says: *TRIGGER: 5m bar closed above ₹1,478 at 09:40 IST, price ₹1,480.*

```
/in-exit plan --stop price:1465 --target 2R --write
```
→ entry 1480, stop 1465, target 1510, reward:risk 2.00.

```
/in-budget cash --write
```
→ it shows each limit (max loss, cash after buffer, position cap) and the shares allowed.

```
/in-risk
```
→ if it prints `BLOCK`, **do not take the trade**. Read why. If there is no block, read the warnings.

```
/in-ticket show
```
→ a plain ticket: instrument, BUY, quantity, product (MIS/CNC), limit price, stop-loss trigger and target.
You type those into Upstox yourself.

## 5. How to scan the market

The scanner reads free Yahoo charts for NSE stocks (symbols like `RELIANCE.NS`). It reports charts
that match a rule. **A match is not a recommendation to buy.**

### 5.1 Build your stock list (once, and sometimes refresh)

```
/in-scanner nifty50         # the Nifty 50 stocks
/in-scanner universe        # every NSE stock in the EQ series (2,000+)
```

Both save `trader/universe.txt`. If NSE blocks the download, open the NSE website, save the CSV file
in your browser, and run `/in-scanner universe --file path/to/EQUITY_L.csv` (or `nifty50 --file ...`).

### 5.2 Scan the daily charts (end of day or before the open)

```
/in-scanner daily --symbols RELIANCE,TCS,INFY,HDFCBANK     # stocks you name
/in-scanner daily --universe --limit 100                   # first 100 in your list
/in-scanner daily --universe --min-price 100 --min-volume 500000
```

It looks for:

| Setup | Meaning |
| --- | --- |
| 20-day high breakout | today's close is above the highest high of the last 20 days |
| reclaimed the 20-day average | price moved back above its 20-day average |
| oversold (RSI under 30) / oversold bounce | fell hard, and today closed up |
| bull flag | a strong rise (10%+) followed by a tight pause above the 20-day average |

### 5.3 Scan the opening range (after 09:30 IST)

```
/in-scanner orb --symbols RELIANCE,TCS,SBIN
```

The *opening range* is the high and low of the first 15 minutes (09:15 to 09:30). A stock shows up
when a finished 5-minute candle **closes above** that high.

### 5.4 Useful options

| option | what it does |
| --- | --- |
| `--symbols A,B,C` | scan only these NSE symbols |
| `--universe` and `--limit N` | scan from `trader/universe.txt`, first N stocks |
| `--watchlist watchlist.json` | scan the hits from an earlier scan |
| `--min-price 50` | skip stocks below this price (default 50) |
| `--min-volume 200000` | skip thinly traded stocks (default 200,000 shares a day) |
| `--or-minutes 15` | length of the opening range |
| `--now "2026-11-23 10:15"` | pretend it is this time (IST), to replay a day |
| `--offline FILE_OR_FOLDER` | use saved Yahoo files instead of the internet |
| `--no-write`, `--json`, `--show N` | don't save the result, print JSON, show N lines |

### 5.5 What to do with the results

1. The scan saves `trader/watchlist.json`.
2. Run `/in-news --watchlist watchlist.json` and read the flagged headlines.
3. Run `/in-entry check SYMBOL` on the ones you like.
4. Then continue with exit, time machine, budget and risk (see section 4).

How long it takes: the scanner waits a little between requests to be polite to the free service.
Roughly 100 stocks take a couple of minutes, and the whole market takes 15 minutes or more.
Start with Nifty 50.

For options: only stocks in NSE's F&O list have options. The scanner does not check this, so look
up the lot size and premium in your broker app.

## 6. The 11 skills at a glance

| Skill | What it does | Example |
| --- | --- | --- |
| `/in-scanner` | finds charts with setups | `/in-scanner daily --symbols TCS,INFY` |
| `/in-news` | recent headlines, flagged by what moves a price | `/in-news check RELIANCE --hours 24` |
| `/in-entry` | finds the one *closed* candle that confirms a breakout; never buys | `/in-entry check SBIN --write` |
| `/in-exit` | sets stop-loss and target before you enter | `/in-exit plan --stop or-low --target 2R --write` |
| `/in-budget` | exact shares or option lots from your max loss, plus a charges estimate | `/in-budget cash --write` |
| `/in-risk` | checks the trade against your limits: PASS, WARN, BLOCK | `/in-risk` |
| `/in-ticket` | a plain ticket for you to place by hand, and a paper journal | `/in-ticket show` |
| `/in-timemachine` | replays your plan: 10,000 simulated sessions and past breakout days | `/in-timemachine run` |
| `/in-alerts` | price, stop and target alerts; market clock | `/in-alerts clock` |
| `/in-analyst` | quarterly results you paste in → what changed | `/in-analyst` (see below) |
| `/in-deals` | NSE bulk and block deals: who is buying or selling | `/in-deals summary --file trader/bulk.csv` |

Stops for `/in-exit`: `or-mid` (opening-range midpoint), `or-low` (opening-range low),
`price:1465`, `pct:1` (1% below entry), `atr:1.5` (1.5 times the average daily-range measure).
Targets: `2R` (twice your risk), `1.5R`, or `price:1510`.

**`/in-analyst`**: this one does not fetch results. Get the numbers from the company's results filing
(NSE or BSE announcements, or your broker app). Then:
```
python3 ~/.claude/skills/in-analyst/facts.py template > results.json
```
Fill in the quarters (oldest first, at least 5), and ask Claude to run `/in-analyst` on `results.json`. It shows growth,
margins and what changed.

**`/in-deals`**: run `fetch` to download today's bulk and block deal files. If NSE blocks it, save the CSV from the NSE
website (Market Data → Large Deals) and pass it with `--file`.

## 7. Options: how lots and stop-loss work here

You can only buy whole **lots** (for example, 65 units of Nifty). Cost of one lot = premium × lot size.

```
/in-budget option --underlying NIFTY --premium 100 --stop-premium 70 --target-premium 160 \
   --contract "NIFTY 25900 CE" --expiry 2026-12-02 --write
```

- **Lots** = the smaller of (max loss ÷ loss per lot) and (cash after buffer ÷ cost per lot).
- If one lot already breaks a limit, the answer is **0 lots**. Don't raise the limit to make it fit.
  Use a cash-segment ETF, or paper trade.
- No stop-premium yet? Give an estimate: `--delta 0.5 --underlying-stop-pts 60` (rough guess: delta changes).
- Remember: an option can lose its whole premium, time decay costs you every day, and a stop-loss can fill
  at a worse price if the market gaps.
- `/in-risk` warns when expiry is close (default: under 2 days) and blocks quantities that are not whole lots.

## 8. Paper trading

Paper trading means practising with pretend money. Do this for several weeks before real money.

```
/in-ticket log                          # record the planned trade as a paper trade
/in-ticket close --id 1 --exit 1503.5   # close it at a price (shows result after charges)
/in-ticket summary                      # wins, losses, total
```

The journal is saved in `trader/journal.json`, and `/in-risk` reads it to enforce your daily limits.

## 9. Troubleshooting

| Problem | What to do |
| --- | --- |
| `/in-` shows nothing | Use **Claude Code**, not the normal chat. Close and reopen it. Check `ls ~/.claude/skills`. |
| "could not fetch ... HTTP 403/404" | NSE or Yahoo blocked or changed the link. Save the file from the website and use `--file` or `--offline`. |
| "no data" / "market closed" | NSE is open Mon–Fri 09:15–15:30 IST, except holidays (not checked by these tools). |
| Prices look old | Yahoo's free data is delayed. Check your broker app. |
| `/in-risk` says `stale` | The order is from another day. Run `/in-budget ... --write` again today. |
| `0 shares` or `0 lots` | One unit already breaks a limit. See your `trader/config.json`. |
| An index symbol is not found | Use `NIFTY`, `BANKNIFTY` or `SENSEX`. Other indexes (FINNIFTY, MIDCPNIFTY) are best effort. |
| Python not found | Install Python 3 and use `python3` (Windows: `python`). |

## 10. What was tested, and what was not

- 43 automated tests pass on made-up (synthetic) data: `python3 -W ignore tests/test_all.py`.
- **Not tested on live data.** The NSE download links and news feeds were written from memory and may be
  blocked or changed; every tool has a `--file` or `--offline` fallback.
- Lot sizes, brokerage and tax rates change. Check them in your broker app and edit `trader/config.json`.
- NSE holidays are not checked.
- The Time Machine tests the past. The past is not a promise.

## 11. Uninstall and update

**Uninstall:**
```bash
cd ~/.claude/skills
rm -rf in-alerts in-analyst in-budget in-deals in-entry in-exit in-news in-risk in-scanner in-ticket in-timemachine
```

**Update:** unzip the new version and run `./install.sh` again. Your `trader/` folders and settings are kept.

---

*Inspired by the structure of the open-source US pack
[day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) (MIT). The code in this pack was
written fresh for the Indian market.*
