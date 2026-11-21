---
name: in-analyst
description: >-
  Earnings Analyst for Indian companies. Given quarterly results the user supplies (revenue, EBITDA, net profit, EPS for 5+ quarters), computes quarter-on-quarter and year-on-year change, margins and margin shifts, and flags what changed. Use when the user asks how were the results, analyse Q2 numbers, did profit grow, or are margins falling.
argument-hint: "[template|read] results.json"
---

# in-analyst

Reads a company's quarterly results and says what changed. It does NOT fetch results: there is no free, stable Indian source, so the user pastes the numbers from the NSE/BSE results filing, the investor presentation or their broker app.

```bash
python3 "${CLAUDE_SKILL_DIR}/facts.py" template > results.json     # fill in, oldest quarter first, 5+ quarters
python3 "${CLAUDE_SKILL_DIR}/facts.py" read results.json
python3 "${CLAUDE_SKILL_DIR}/facts.py" read results.csv            # columns: period,revenue,ebitda,pat,eps
```

## How to use it
1. Help the user fill the file from the filing; keep one unit (for example Rs crore) throughout and use consolidated numbers consistently.
2. Lead with what moved: profit, margin and the growth trend, not every line.
3. State the limits: numbers show what happened, not what the market expected. One-off gains, tax changes and a lower base can distort a quarter. A good result can still fall if the market wanted more.
