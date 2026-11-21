---
name: in-timemachine
description: >-
  Time Machine for NSE trades. Replays a trade plan before any rupee is risked: 10,000 simulated sessions built from the stock's own recent 5-minute moves, plus every past day the same opening-range breakout fired, and reports how often the target, the stop or the end-of-day exit came first, with break-even odds. Use when the user asks will this work, what are the odds, backtest this setup, or replay this trade.
argument-hint: "run [--symbol S --entry E --stop S --target T]"
---

# in-timemachine

Tests a plan against the stock's own history. The past is not a promise: a neat result on thin data is not an edge.

```bash
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run                    # plan from trader/plan.json
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run --symbol RELIANCE --entry 1480 --stop 1465 --target 1510 --entry-time 10:00
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run --offline FILE --sims 10000
```
Needs about 60 days of 5-minute bars (Yahoo's free feed; indices and liquid stocks work best).

## How to read it
1. Bootstrap: reshuffles real 5-minute moves, so it assumes no trend and no news. It tests whether your stop and target distances suit the stock's normal movement.
2. History: replays each past opening-range breakout with the same stop and target distance in percent. Under about 20 days it is a hint, not a result.
3. Break-even: with reward:risk R you need to hit the target 1/(1+R) of the time before charges. Say whether the odds beat that and by how much, then say charges raise the bar.
4. If the odds are below break-even, the plan loses money over time even if single trades win. Say so plainly.
