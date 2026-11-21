---
name: in-deals
description: >-
  Large Deals Tracker for India. Reads NSE bulk and block deal files and shows who bought and sold what: net buying by stock, the biggest deals, filters by symbol, client name and minimum value in crore. India's stand-in for a politician-trade tracker. Use when the user asks any bulk deals, who is buying this stock, block deals today, or big institutional buying.
argument-hint: "[fetch|summary] [--file bulk.csv] [--symbol S]"
---

# in-deals

Bulk deals (over 0.5% of a company's shares) and block deals are public the same day. Big buyers can mean interest, but they also sell, trade for clients, and are often wrong.

```bash
python3 "${CLAUDE_SKILL_DIR}/deals.py" fetch
python3 "${CLAUDE_SKILL_DIR}/deals.py" summary --file trader/bulk.csv
python3 "${CLAUDE_SKILL_DIR}/deals.py" summary --file trader/block.csv --min-crore 25 --client "mutual fund"
python3 "${CLAUDE_SKILL_DIR}/deals.py" summary --file bulk.csv --symbol RELIANCE
```
If `fetch` fails (NSE often blocks scripts), save the CSV from nseindia.com (Market Data > Large Deals) in a browser and use `--file`.

## How to use it
Report net buying/selling in crore and the largest deals. Both sides of a deal are listed, so the same trade can appear as a buy and a sell. Never present a deal as a reason to buy by itself.
