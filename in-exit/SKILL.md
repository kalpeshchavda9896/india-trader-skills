---
name: in-exit
description: >-
  Exit Planner for NSE. Sets the stop-loss and target before you enter: opening-range midpoint or low, a price, a percent, or an ATR stop, with a target in R multiples or a price. Writes trader/plan.json with risk per share, reward:risk and a flat-by time (15:15 IST default). Use when the user asks where to put the stop, what is my target, what is my SL, or plan the exit.
argument-hint: "plan [--stop or-mid|or-low|price:X|pct:X|atr:K] [--target 2R|price:X]"
---

# in-exit

Decide how a trade ends before it starts. The stop is where the idea has failed; the target is where you take what you came for. Both are written down first so nobody decides in the middle of a fast move. A stop is a plan, not a guarantee: a gap or fast market can fill past it.

```bash
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan                           # from trader/entry.json, stop or-mid, target 2R
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --stop or-low --target 1.5R --write
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --symbol RELIANCE --entry 1480 --stop price:1465 --target price:1510 --write
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --symbol TCS --entry 3200 --stop pct:1 --target 2R
python3 "${CLAUDE_SKILL_DIR}/exit.py" show
```
Stops: `or-mid`, `or-low` (need entry.json from /in-entry), `price:X`, `pct:X`, `atr:K` (K x 14-bar ATR; needs bars, or `--offline FILE`).

## How to use it
1. Pick the stop from the chart (below the swing low or the opening range), not from how much you want to risk.
2. If the stop is more than about 3% away, say so: a wide stop means a small position.
3. Reward:risk under your minimum (1.5 by default) gets a note; /in-risk enforces it.
4. Long trades only. For options, plan the stop on the underlying, then use /in-budget option with premium numbers.

Hands off to /in-timemachine, /in-budget, /in-alerts via `trader/plan.json`.
