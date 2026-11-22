# Contributing

Thanks for helping. This project is a set of planning tools for the Indian stock market. It must never place orders or ask for broker passwords, OTPs or API keys.

## Ground rules
- Python 3.8+, standard library only. No new dependencies.
- No order placement and no broker connection.
- Keep each skill's `SKILL.md` and script in step.
- `_shared/inmkt.py` is the source of the shared helper. Edit it there, then run `./build.sh` to copy it into every skill folder.

## Run the tests
```bash
python3 -W ignore tests/test_all.py
```
All tests must pass before you open a pull request.

## Pull requests
1. Fork, then create a branch.
2. Make a small, focused change and add or update a test.
3. Describe what changed and why. Mention anything you could not test on live data.

## Reporting problems
Use the issue templates. For a data problem include the exact command, the error text and your date and time (IST). Never paste personal account details.

Planning tools only. Not investment advice.
