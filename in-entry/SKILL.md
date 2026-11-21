---
name: in-entry
description: >-
  Entry Timer for NSE. Watches a setup bar by bar (5-minute by default) and says the moment a COMPLETED bar closes above the 15-minute opening range high (09:15-09:30 IST) or a level you give. Never buys anything. Use when the user asks when to enter, is it breaking out now, did RELIANCE trigger, or wants an entry on Nifty at a level.
argument-hint: "[check|watch] SYMBOL [--setup orb|level] [--level PRICE]"
---

# in-entry

Turns a setup into one moment: the bar that confirms it. A price poking above the high mid-bar is not an entry. A bar that CLOSES above it is. It then writes the time and price and stops.

```bash
python3 "${CLAUDE_SKILL_DIR}/entry.py" check RELIANCE                    # 15-min opening range, 5-min bars
python3 "${CLAUDE_SKILL_DIR}/entry.py" check NIFTY --setup level --level 25850
python3 "${CLAUDE_SKILL_DIR}/entry.py" check TCS --min-volume-x 1.5 --write   # saves trader/entry.json
python3 "${CLAUDE_SKILL_DIR}/entry.py" watch RELIANCE --until 14:45 --write
```
Flags: `--interval 1m|5m|15m`, `--or-minutes N`, `--now "2026-11-23 10:15"` (IST, replays a day), `--offline FILE`.

## The rule
- Opening range = high and low of the first 15 minutes of the session (bars 09:15, 09:20, 09:25).
- Trigger = first completed bar after it that closes above the level. A close exactly at the level is not above it.
- Time = that bar's close time (the 09:45 bar closes at 09:50 IST). Entries before `no_entries_before` (09:30) or after `no_entries_after` (14:45) are reported as too early/late, not as triggers.
- Only closed bars count. Yahoo can lag a few minutes: check your broker's live price before acting.

Next step after a trigger: /in-exit to set the stop and target BEFORE entering. Exit code 0 = triggered, 1 = not yet.
