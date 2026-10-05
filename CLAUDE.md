# Trading — working notes for Claude

Screening and backtesting run offline as scripts (`scripts/`, run with
`PYTHONPATH=.`). The web app in `scripts/swing_screener/web/` only *views*
results; it never runs a strategy. See `README.md` and `scripts/README.md`.

## Rule: every strategy change updates its Strategy page in the same change

The web app's **Strategies** page is generated from each strategy's own code,
so it is only as accurate as that code's documentation attributes. Whenever you
change a strategy's screening or backtesting behaviour — a gate, watch flag,
setup, threshold, entry/stop/target placement, exit, decision logic, or the
backtest mechanics a strategy relies on (exit modes, order expiry, costs,
sizing) — update, in the same change:

- the strategy class in `scripts/swing_screener/strategies/<name>.py`:
  `status`, `thesis`, `how_it_works`, `caveats`, `gate_docs`, `watch_docs`,
  `setup_docs`, `entry_rules`, `exit_rules`, `param_docs`, `backtest_args`
  (the contract is documented in `strategies/base.py`);
- for the momentum baseline, `DOC` in `scripts/swing_screener/backtesting/baseline.py`;
- for a new strategy, register it in `strategies/__init__.py` and fill every
  attribute above — the page and the test pick it up automatically.

Write numbers as `{NAME}` placeholders that name a module constant or a numeric
class attribute (e.g. `{entry_channel}`), not as literals, so the page shows the
live value and a threshold change cannot leave stale text behind. After a new
backtest, update `status` if the measured result changed.

Then run, from `scripts/`:

```bash
PYTHONPATH=. .venv/bin/python -m tests.test_strategy_docs
```

It fails on an undocumented or stale gate/flag/setup code, a broken
placeholder, or a parameter row pointing at something that no longer exists.
It cannot check that prose still matches behaviour — that is on you: re-read
the affected `*_docs` entries against the code you changed. Restart the web
server to see the updated page.
