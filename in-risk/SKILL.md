---
name: in-risk
description: >-
  Risk Manager for Indian trades. Checks a proposed trade (trader/orders.json) against the limits in trader/config.json: stop required, max loss per trade, daily loss, trades per day, cash buffer, position cap, reward:risk, entry window 09:30-14:45 IST, market hours, option expiry distance and lot rounding. Returns PASS, WARN or BLOCK. Use when the user asks is this trade ok, check my risk, am I over my limit, or before any order ticket.
argument-hint: "[--orders FILE]"
---

# in-risk

Checks every proposed trade against the user's own limits and says BLOCK when it breaks one. It reads, checks and reports. It cannot place or cancel anything.

```bash
python3 "${CLAUDE_SKILL_DIR}/check.py"                    # trader/orders.json
python3 "${CLAUDE_SKILL_DIR}/check.py" --now "2026-11-23 10:30"
```
Exit code 0 = no blocks (read the warnings), 2 = at least one BLOCK.

## Checks
| check | level |
| --- | --- |
| stale order (not today), zero size, option qty not whole lots, blocked ticker, missing stop, stop not below entry | BLOCK |
| cost leaves less than the cash buffer; position over the cap | BLOCK |
| loss at the stop over `max_loss_per_trade_inr` | BLOCK |
| trades today at the limit; daily loss limit would be passed (reads trader/journal.json from /in-ticket) | BLOCK |
| reward:risk under `min_reward_risk`, or no target | WARN |
| before 09:30 or after 14:45 IST, market closed | WARN |
| option within `min_days_to_expiry` of expiry; any option (it can lose its whole premium) | WARN |

Report each line in plain words. On a BLOCK, say which rule and what number would fix it; never suggest loosening the limit just to pass.
