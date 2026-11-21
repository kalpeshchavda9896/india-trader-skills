---
name: in-budget
description: >-
  Budget Manager for Indian retail traders. Turns a plan into an exact quantity in rupees: whole shares for cash trades, whole lots for Nifty, Bank Nifty, Fin Nifty, Midcap Nifty and Sensex option buying. Sizes to a maximum loss per trade and a cash buffer, refuses if one lot does not fit, and estimates charges. Use when the user asks how many shares or lots, what quantity, how much to buy, position size, or what is my risk.
argument-hint: "[cash|option|config]"
---

# in-budget

The stop decides the size: the further away the stop, the fewer shares or lots. It writes a proposal only (`trader/orders.json`). Sizing to a maximum loss keeps each loss small; it does not make a trade win.

```bash
python3 "${CLAUDE_SKILL_DIR}/size.py" config
python3 "${CLAUDE_SKILL_DIR}/size.py" cash --write                         # sizes trader/plan.json
python3 "${CLAUDE_SKILL_DIR}/size.py" cash --symbol RELIANCE --entry 1480 --stop 1465 --target 1510 --write
python3 "${CLAUDE_SKILL_DIR}/size.py" option --underlying NIFTY --premium 100 --stop-premium 70 --target-premium 160 --contract "NIFTY 25900 CE" --expiry 2026-11-25 --write
python3 "${CLAUDE_SKILL_DIR}/size.py" option --underlying NIFTY --premium 100 --delta 0.5 --underlying-stop-pts 60
```

## Step 1: set the rules once
If `trader/config.json` does not exist, copy `config.example.json` from this folder and ask the user, in plain words: capital (`capital_inr`), the most one trade may lose (`max_loss_per_trade_inr`), the daily loss limit, trades per day, the cash buffer, and whether options are allowed. Keep `paper` true until they have practised. "Up to 20% loss" is a very high per-trade limit (five losses wipe the account); suggest 1-5% and let them decide.

## Step 2: size it
- Cash: quantity = the smallest of max loss / risk per share, cash after buffer / price, and the position cap.
- Options: lots = the smaller of max loss / ((premium - stop premium) x lot size) and cash after buffer / (premium x lot size). You cannot buy part of a lot. If one lot breaks a limit the answer is 0 lots, with the reason; do not raise the limit to make it fit. Suggest a cash-segment ETF or paper trading instead.
- Lot sizes in the config (Nifty 65, Bank Nifty 30, Sensex 20 as of Nov 2026) are examples: NSE revises them. Ask the user to confirm the lot size in their broker app.
- Charges are rough (flat brokerage plus a percent of turnover). If charges eat the gain, say the trade is too small.

Then run /in-risk. Never state a quantity without showing the max loss next to it.
