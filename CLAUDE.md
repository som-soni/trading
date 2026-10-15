# Trading — working notes for Claude

Screening and backtesting run offline as scripts (`scripts/`, run with
`PYTHONPATH=.`). The web app in `scripts/swing_screener/web/` only *views*
results; it never runs a strategy. See `README.md` and `scripts/README.md`.

One exception: a chart indicator may run a strategy's *detectors* on demand, for
exploration — the Chart patterns indicator calls `/api/patterns`, which runs
`ChartPatternSpecStrategy.detect_live` on stored prices up to the date asked. It
reuses the strategy's own detectors and drawing (`chart_anatomy`), so there is one
implementation of the rules, never a second copy in JavaScript. It never makes a
trade decision (entry, stop, sizing), and it never stands in for a run's record:
what a backtest traded is drawn from that run's stored signals (`trade-anatomy`),
because current code may detect differently from the code that ran.

Scheduled offline work is a set of layered jobs (`scripts/jobs/registry.py`:
reference → data → analytics → screening → publish). Keep the layers honest:
only `marketdata/` downloads; `analytics/` and screening read stored data
(screening runs inside `cache.offline()`). A new recurring task is a new job
in the registry (with its layer, cadence and `after` dependencies), not a new
standalone script or cron entry, so it is logged and shows on the Data status
page. Jobs are run by the queue (`jobs/queue.py` + `python -m jobs worker`):
the portal, schedules (`job_schedules`, System → Schedules) and `jobs enqueue`
only *ask* through `jobs/queue.py`'s functions — never write the queue tables
elsewhere, so the backend stays swappable (RQ / Celery). The worker runs three
lanes (main: routines and downloads; backtest: `RESEARCH_JOBS`; fast: short
stored-data jobs, `FAST_JOBS` in `jobs/registry.py`): a new job runs in the
main lane unless you add it to one of those sets on purpose — then run
`PYTHONPATH=. .venv/bin/python -m tests.test_job_lanes`.

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
`definitions.presets()`: conditions only, thresholds as module constants.

Screens overlap on purpose — `above_200` is deliberately a looser `near_highs`,
because a different strategy draws from each — but a *question* is answered once.
Several screens ask the same thing at different thresholds (whether the close is
above the 200-day: C3, H1, A1; how far below the 52-week high: C7, H3, U7; whether
an average is falling: H2, U4). Each of those lives in exactly one predicate in
`screens/criteria.py`, and a criterion supplies only its own ceiling — named as a
module constant, never a literal, so the Screens page renders the live value. Reach
for the existing predicate instead of writing a second one, give a screen its own
constant rather than borrowing another's (so tuning one screen cannot move another),
and run `PYTHONPATH=. .venv/bin/python -m tests.test_screen_criteria`, which fails on
a re-inlined predicate or a bare threshold.

Naming follows from that: a criterion is named for the rule, and a screen keeping its
own variant of a shared rule prefixes it with its screen key (`stage2_above_sma200`
beside `above_sma200`); a threshold has one name per quantity, prefixed the same way
(`UPTREND_MAX_PCT_BELOW_52W_HIGH` beside `MAX_PCT_BELOW_52W_HIGH`). Do not rename the
Trend Template's unprefixed five — `MAX_PCT_BELOW_52W_HIGH`, `MIN_PCT_ABOVE_52W_LOW`,
`RS_MIN_MOM`, `RS_MIN_RANK`, `SMA200_RISING_BARS`. A fingerprint is keyed on constant
*names* (`strategies/base.py` `spec_params`), so renaming one of those fails the version
gate and invalidates every stored signal for a change that alters no behaviour.

A **strategy** (`strategies/`) draws its candidates from one screen (`screen_key`; its
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
- for the Fundamentals (company) page's strategy sections, `DOC`, `TESTS` and the
  threshold constants of the view (`scripts/fundamentals/sepa.py` for Minervini) — the
  page renders every rule from them; `fundamentals/growth.py` holds the shared metrics
  and `fundamentals/company.py` the page's tables; run
  `PYTHONPATH=. .venv/bin/python -m tests.test_fundamentals`;
- for a new strategy, register it in `strategies/__init__.py` and fill every
  attribute above — the page and the test pick it up automatically.

Write numbers as `{NAME}` placeholders that name a module constant or a numeric
class attribute (e.g. `{entry_channel}`), not as literals, so the page shows the
live value and a threshold change cannot leave stale text behind. After a new
backtest, update `status` if the measured result changed.

**A behaviour change also bumps `version` and adds a `changelog` entry**
(`(version, ISO date, what changed and why)`, newest first). That is not
bookkeeping: the backtester stamps the strategy's `spec_id` — `v<version>-<fingerprint>`
— into each run directory, ingest lifts it into `report_runs.spec_id`, and the
Strategies page's **Backtests** tab groups runs by it, so selecting a version shows
that entry plus everything that landed after it ("these runs do not reflect the
current rules"). An un-bumped change makes two different rule sets share a version
number; the page then shows the full spec id and says so, because the number alone
no longer identifies the run. `strategies/versions.lock.json` is the gate —
`PYTHONPATH=. .venv/bin/python -m tests.test_strategy_versions` fails when a
fingerprint moves without a version bump. Note the fingerprint is keyed on numeric
constants, so a change it cannot see (new code paths, a changed default that is not
a module constant) still needs the bump by hand.

Then run, from `scripts/`:

```bash
PYTHONPATH=. .venv/bin/python -m tests.test_strategy_docs
```

It fails on an undocumented or stale gate/flag/setup code, a broken
placeholder, or a parameter row pointing at something that no longer exists.
It cannot check that prose still matches behaviour — that is on you: re-read
the affected `*_docs` entries against the code you changed. Restart the web
server to see the updated page.

## Rule: a Learn guide is registered in two files, and stands on its own

A guide is one `research/learn-*.md`. The menu that lists it is assembled
somewhere that cannot see it, so **nothing at runtime objects when the two
disagree** — an unregistered guide simply never appears, and a topic missing
from `learn.js` throws only when someone opens it.

Adding a guide means registering it in three maps in `web/static/app.js`:
`GUIDE_ORDER` (its position), `GUIDE_TOPIC` (its topic) and `GUIDE_BLURB`
(the card's one-line description). A new **topic** also needs `LEARN_TOPICS`
there, and `FAMILY_LABEL` (its sidebar label) plus `FAMILIES` (its pattern
groups, `[]` for a guides-only topic) in `web/static/learn.js`. A guide is
only visible after it is ingested: `python -m jobs enqueue ingest`.

Then run, from `scripts/`:

```bash
PYTHONPATH=. .venv/bin/python -m tests.test_learn_guides
```

It fails on a guide missing from any registry, a registration with no file, a
topic whose vocabulary disagrees across the two static files, a topic that
would render an empty sub-menu, a missing H1 or a placeholder blurb.

**The Learn section stands on its own.** Guides are written for a reader who
has only this app: no references to outside documents, PDFs or private
notes, and no IDs, archetype codes or vocabulary borrowed from them. Outside
material may inform the structure of a guide; it is never cited in one, and
its numbers are never quoted. Every figure in a guide comes from a constant
or a measurement in this repository, and where neither exists the guide says
so rather than asserting a number. Keep the house sections — "What the
evidence says" and a checklist — and let them report nulls when that is what
the backtests found.
