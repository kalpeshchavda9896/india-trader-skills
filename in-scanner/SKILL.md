---
name: in-scanner
description: >-
  Chart Scanner for NSE stocks. Scans daily charts for 20-day breakouts, bull flags, oversold bounces and the 20-day-average reclaim, and 5-minute charts for opening-range breakouts (09:15 IST start). Builds the NSE equity or Nifty 50 universe from NSE's public CSVs and writes trader/watchlist.json for in-news and in-entry. Use when the user says scan the Indian market, find NSE setups, what is breaking out, Nifty 50 scan, build my watchlist, or at the start of the trading day.
argument-hint: "[universe|nifty50|daily|orb] [--symbols A,B]"
---

# in-scanner

Finds NSE charts that match a rule. A scan is a list of charts, not a list of things to buy. Most people who trade lose money; the scanner only saves you flipping through charts.

`${CLAUDE_SKILL_DIR}` is this skill's folder. Python 3.8+, nothing to install.

```bash
python3 "${CLAUDE_SKILL_DIR}/scan.py" nifty50                          # trader/universe.txt (Nifty 50)
python3 "${CLAUDE_SKILL_DIR}/scan.py" universe                         # all NSE EQ shares (big, slow to scan)
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily --symbols RELIANCE,TCS,INFY   # after 15:30 or before 09:15 IST
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily --universe --limit 100
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb --symbols RELIANCE,TCS         # after 09:30 IST
```
Flags: `--min-price 50`, `--min-volume 200000`, `--or-minutes 15`, `--now "2026-11-23 10:15"`, `--offline FILE|DIR`, `--file CSV` (a CSV you saved from nseindia.com if the download is blocked), `--no-write`, `--json`.

## How to run it
1. Setup once: run `nifty50` (or `universe`). If NSE blocks the download, save the CSV in a browser and pass `--file`.
2. Before the open: `daily`. During the day: `orb`.
3. Show the hits with the setup names and the close. Say plainly: a setup on a chart is not a prediction.
4. Hand over: `trader/watchlist.json` is read by /in-news and /in-entry.

Data is Yahoo Finance's free, delayed chart feed (`SYMBOL.NS`). Indices: NIFTY, BANKNIFTY, SENSEX. The scanner pauses between requests; a 500-stock scan takes minutes. Exit code 0 = hits found, 1 = none or could not run.
