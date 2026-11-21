---
name: in-alerts
description: >-
  Price alerts for Indian markets. Rings the terminal bell when a price, stop or target is hit, and reports NSE market status (09:15-15:30 IST), minutes to the close and to the flat-by time. Can load stop and target alerts straight from trader/plan.json. Use when the user asks alert me at, watch this price, tell me when it hits my stop, is the market open, or how long to the close.
argument-hint: "[add|from-plan|list|check|watch|clock]"
---

# in-alerts

Alerts on the user's own screen. They do not protect anyone who looks away: a real stop must be a stop-loss order at the broker.

```bash
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add RELIANCE above 1510 --label target
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add NIFTY below 25400
python3 "${CLAUDE_SKILL_DIR}/alerts.py" from-plan
python3 "${CLAUDE_SKILL_DIR}/alerts.py" list
python3 "${CLAUDE_SKILL_DIR}/alerts.py" check           # one look now
python3 "${CLAUDE_SKILL_DIR}/alerts.py" watch --every 60  # runs until Ctrl-C or the close
python3 "${CLAUDE_SKILL_DIR}/alerts.py" clock
```
Prices are Yahoo's free, delayed data; `watch` only runs 09:15-15:30 IST. Weekends are handled; NSE holidays are not, so confirm on nseindia.com.
