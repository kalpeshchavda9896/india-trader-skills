---
name: in-news
description: >-
  News Monitor for Indian stocks. Pulls recent Yahoo Finance and Google News headlines for NSE symbols and flags what tends to move a price: results, orders, rating changes, SEBI or RBI actions, dividends, bonus or split, management changes. Use when the user asks what is the news on RELIANCE, any news on my watchlist, why is this stock moving, or before taking a trade.
argument-hint: "[SYMBOLS] [--watchlist FILE] [--hours 36]"
---

# in-news

Headlines for the stocks you watch, with a flag for what usually matters. A headline is not a signal: read the story, check the date and ask whether the price has already moved.

```bash
python3 "${CLAUDE_SKILL_DIR}/news.py" check RELIANCE TCS --hours 24
python3 "${CLAUDE_SKILL_DIR}/news.py" check --watchlist watchlist.json
```
Flags: `--offline-dir DIR` (saved RSS files `SYMBOL.xml`), `--now`, `--json`.

## How to use it
1. Run for each symbol on the watchlist or the one you are about to trade.
2. Lead with flagged headlines (results, orders/deals, rating/target, regulatory, corporate action, management, guidance).
3. A SEBI or regulatory flag, or results due today, is a reason to skip or size down. Say so.
4. Sources are free and can lag. For results dates and exact filings, check NSE/BSE announcements.

Exit code 0 = some headlines found, 1 = none.
