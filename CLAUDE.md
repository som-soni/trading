# Trading — working notes for Claude

Screening and backtesting run offline as scripts (`scripts/`, run with
`PYTHONPATH=.`). The web app in `scripts/swing_screener/web/` only *views*
results; it never runs a strategy. See `README.md` and `scripts/README.md`.

Scheduled offline work is a set of layered jobs (`scripts/jobs/registry.py`:
reference → data → analytics → screening → publish). Keep the layers honest:
only `marketdata/` downloads; `analytics/` and screening read stored data
(screening runs inside `cache.offline()`). A new recurring task is a new job
in the registry (with its layer, cadence and `after` dependencies), not a new
standalone script or cron entry, so it is logged and shows on the Data status
page. Jobs are run by the queue (`jobs/queue.py` + `python -m jobs worker`):
the portal, schedules (`job_schedules`, System → Schedules) and `jobs enqueue`
only *ask* through `jobs/queue.py`'s functions — never write the queue tables
elsewhere, so the backend stays swappable (RQ / Celery).

## Markets come from config

The markets are `scripts/swing_screener/config/MARKETS` (name, exchange, badge, flag,
currency, ticker suffix, time zone). The web app reads them from `GET /api/markets`
for its header market selector, badges and currency, and the server iterates
`MARKETS` — don't hard-code `"us"` / `"india"` in new UI or endpoint code, so a new
country stays a config entry plus its data pipeline.

## Screens vs strategies

A **screen** (`scripts/swing_screener/screens/`) only qualifies stocks — named
criteria in `screens/criteria.py`, no entry, stop or decision — and is judged
by a forward-return **screen study** (`screens/study.py`, over month-end
snapshots). In the web app a screen is a list of conditions over the daily
stock snapshot (`screens/snapshot.py`, field catalog `FIELDS`); the built-in
screens' conditions live in `screens/definitions.py`, generated from the
criteria constants, and must return exactly what the coded criteria return —
`PYTHONPATH=. .venv/bin/python -m tests.test_screen_definitions` checks it, so
run it after changing a criterion, a built-in definition or a snapshot field.
A new field needs a `FIELDS` entry and a value in `snapshot._row` (point in
time) or `_add_present` (present only). Built-in screens with no coded twin
(e.g. "Strong stocks in leading groups", on the peer-group fields) are
`definitions.presets()`: conditions only, thresholds as module constants. A **strategy**
(`strategies/`) draws its candidates from one screen (`screen_key`; its
`screen_gates` map its gate codes to that screen's criteria, evaluated by the
same code) and adds its own trade rules, setups, entry/stop/target, exits and
sizing; strategies are what get **backtested**. A qualification rule belongs in
a screen criterion; a trade rule (earnings, volatility, setup quality) belongs
in the strategy. A refactor that must not change behaviour is proven with
`PYTHONPATH=. .venv/bin/python -m tests.golden_strategies --check` (record the
baseline with `--write` before you start).

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
- for a screen, its `Criterion` docs and `name` / `description` / `thesis` in
  `screens/__init__.py` (numbers as `{NAME}` placeholders of `screens/criteria.py`
  constants) — the Screens pages and every strategy that uses the screen render them;
- for the long-term quality tracker, `DOC`, `TESTS` and the threshold constants in
  `scripts/fundamentals/quality.py` — its Quality page and Strategies
  entry render every rule from those constants, so change a rule's text with its logic;
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
