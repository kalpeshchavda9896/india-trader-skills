---
name: in-ticket
description: >-
  Order ticket and paper journal for Indian trading. Prints a plain-words ticket for the user to place BY HAND in Upstox or any broker (instrument, buy, quantity or lots, MIS/CNC/NRML, limit price, stop-loss and target), and logs paper trades with P&L after charges. It never sends an order and has no broker connection or keys. Use when the user asks how do I place this, make the order ticket, log my paper trade, or show my paper results.
argument-hint: "[show|log|close|summary]"
---

# in-ticket

This skill has NO broker connection and cannot place, change or cancel an order. It writes down what the user should do, and keeps a paper journal. The user approves and places every real order themselves.

```bash
python3 "${CLAUDE_SKILL_DIR}/ticket.py" show                  # ticket for trader/orders.json
python3 "${CLAUDE_SKILL_DIR}/ticket.py" show --product MIS    # MIS intraday, CNC delivery, NRML F&O carry
python3 "${CLAUDE_SKILL_DIR}/ticket.py" log                   # record it as a paper trade
python3 "${CLAUDE_SKILL_DIR}/ticket.py" close --id 1 --exit 1503.5
python3 "${CLAUDE_SKILL_DIR}/ticket.py" summary
```

## Rules
1. Run /in-risk before showing a ticket. If it said BLOCK, do not show a ticket as ready.
2. Remind the user to check the live price and lot size in the app, and to place the stop-loss order the moment the buy fills.
3. Paper first. Do not suggest going live until paper results hold over many trades, not a few good days.
4. Never ask for broker credentials, API keys, OTPs or passwords.
