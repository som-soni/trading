# swing_screener

A data-only Python port of the two prompts now in [`archive/prompts/`](../archive/prompts/) —
`uptrend-daily-v2-swing-review.md` (US) and
`t-trend-up-india-swing-review.md` (India). No LLM calls, no screenshots.

> **The code and the prompts have DIVERGED.** The prompts still document
> M1 as a hard gate (it is now watch flag X9), percent-based risk caps
> (now ATR-relative), and an overhead-resistance rule that vetoed the
> breakouts it was meant to catch (now excludes the setup's own swing
> high). Treat the code as the source of truth and the prompts as
> historical until they are regenerated. They are archived, with the
> full list of divergences, in [`archive/README.md`](../archive/README.md). Pulls
price data with [yfinance](https://pypi.org/project/yfinance/) (free, no
auth), stores everything in Postgres so re-runs only fetch new bars, and
writes one filterable CSV per market to `reports/`.

## Setup

```
cd scripts
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Needs a local Postgres with a `trading` database. Connection config lives
in `scripts/.env` (gitignored — never commit it):

```
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=<yours>
PGDATABASE=trading
```

Schema (tables: `prices`, `universe_history`, `backtest_signals`) is
created automatically on first use — see `db.py`, or run
`python3 -c "from swing_screener import db; db.init_schema()"` explicitly.

## Command reference

Every command runs from `scripts/` with `PYTHONPATH=.` set. Scheduled and
routine work goes through **`python -m jobs`** (see "Jobs" below); the rest are
manual tools, grouped by what they are for:

| command | purpose |
|---|---|
| `jobs` | Every offline job and pipeline: pull data, analytics, screening, publish (`list`, `run`, `status`, `schedule`) |
| `screening.daily` | The `daily` pipeline for both markets (kept for old cron entries) |
| `screening.pipeline` | One strategy over one market, on stored prices (`--pull` to fetch first) → candidate CSV |
| `screening.inspect` | Why one symbol did or didn't qualify |
| `screening.history` | What changed between two runs |
| `backtesting.backtest` | Backtest a strategy (portfolio-level by default) |
| `backtesting.baseline` | The momentum baseline every strategy must beat |
| `backtesting.experiments` | Controlled A/B over one signal set |
| `backtesting.report` | Re-render a finished run as markdown + charts |
| `backtesting.index_investing` | Index-investing backtests: SIP timing, trend overlays, allocation, rotation |
| `marketdata.backfill` | Pull long history (do this first) |
| `marketdata.index_data` | Total-return index series (separate store — see below) |
| `marketdata.migrate` | Apply additive schema migrations |

### Flags that matter

**`backtesting.backtest`**

| flag | effect |
|---|---|
| `--market {us,india}` `--start YYYY-MM-DD` | required |
| `--strategy {trend_pullback,breakout,donchian,chart_pattern}` | which strategy to run |
| `--sample N` | seeded RANDOM subset of N candidates — **prefer over `--limit`**, which slices alphabetically and is therefore biased |
| `--max-positions N` | position cap (default: the market config's 10) |
| `--exit-mode {bracket,trail_atr,ma,donchian}` | how open positions are managed |
| `--no-target` | drop the fixed profit target so winners can run |
| `--atr-mult` `--ma-col` `--donchian-bars` | parameters for the above |
| `--accept-labels` | which `classify()` labels to trade; add `"TRADE ON TRIGGER"` to test whether the confidence tiers separate outcomes |
| `--per-symbol` | the OLD unlimited-capital mode, kept for comparison only |
| `--no-signal-cache` | recompute gates from scratch — needed only when gate logic changed |
| `--refresh-history` | pull fresh data first (skip if backfill already ran) |

**`backtesting.baseline`**

| flag | effect |
|---|---|
| `--top-n N` | how many names to hold (50 behaved better than 10 or 20) |
| `--lookback` `--skip` | momentum window; defaults are the 12-1 convention |
| `--rebalance {ME,QE,W-FRI}` | pandas offset alias; quarterly cut turnover with no loss of return |
| `--min-turnover` | **the real universe control** — the turnover floor decides whether you own microcaps or large caps |
| `--liquidity-top N` | rank within the N most liquid; largely inert above ~250 because the turnover floor already binds |
| `--cost-bps` | per side; 5 is reasonable for the US, 25 for Indian delivery |
| `--no-trend-filter` | drop the >200DMA requirement |

**`backtesting.index_investing`**

| flag | effect |
|---|---|
| `--market {us,india}` | required |
| `--family A B C D` | A accumulation timing · B lump-sum overlays · C allocation/rebalancing · D rotation (default: all) |
| `--cost-bps` | per side, on top of each series' expense ratio (default 2 US, 10 India) |
| `--no-tax` | pre-tax only; by default every table carries both pre- and after-tax columns |
| `--quick` | 40 placebo draws instead of 200, annual instead of quarterly A5 starts |

**`marketdata.index_data`** — `--refresh` (fetch/update), `--list` (coverage),
`--validate` (flag impossible single-day moves), `--calibrate-dividends`.

**`backtesting.report`** — `--list`, `--all`, or `--market/--strategy/--run`.

## Reports

Every backtest writes a self-contained directory:

```
reports/<market>/<strategy>/<run>/
  report.md      headline table, verdict, charts, trade breakdown, caveats
  trades.csv     every trade with entry/exit/R/costs
  equity.csv     daily equity, cash, positions, drawdown
  figures/       equity curve, drawdown, annual returns, R distribution, exposure
```

`report.md` leads with a plain-English verdict and the numbers that decide it —
CAGR, max drawdown, Sharpe, Sortino, Calmar, exposure, turnover, costs — always
beside the buy-and-hold benchmark, with **excess CAGR** called out. A caveats
block states the survivorship bias and cost model on every run, and a
"Reproduce" block carries the exact command.

To render a run that already happened without re-simulating:

```
python3 -m swing_screener.backtesting.report --list
python3 -m swing_screener.backtesting.report --all
```

## Index investing

A separate suite for the question the stock-level backtests cannot answer:
not *which stock*, but *when to put money into the index*.

```
# once: fetch the total-return series (~21 series, 150k rows)
PYTHONPATH=. python3 -m swing_screener.marketdata.index_data --refresh
PYTHONPATH=. python3 -m swing_screener.marketdata.index_data --validate

PYTHONPATH=. python3 -m swing_screener.backtesting.index_investing --market us
PYTHONPATH=. python3 -m swing_screener.backtesting.index_investing --market india --family A
```

Four families: **A** contribution timing (day-of-month, day-of-week,
frequency, lump-sum vs DCA, dip-buying, value averaging), **B** lump-sum
timing overlays (Faber 10-month, 200-DMA, absolute momentum, vol targeting,
sell-in-May), **C** static allocation and rebalancing cadence, **D** rotation
between index sleeves.

Three things differ from the stock-level backtests, and they are the reason
this is a separate store rather than a flag on `backtest.py`:

* **`index_series`, not `prices`.** These series are fetched with
  `auto_adjust=True`, i.e. dividends included, because dividends (~1.9%/yr
  US, ~0.8%/yr measured for India) swamp every effect being tested. The
  screener's `prices` table stays unadjusted, as stops and pivots need real
  traded levels. Price-only indices carry an empirically calibrated dividend
  accrual (`--calibrate-dividends`), never a guessed one.
* **Cash earns a real rate** — the 13-week T-bill (`^IRX`, 1960 onward) for
  the US, the realised LIQUIDBEES yield for India — accrued on *calendar*
  days. Every strategy that waits in cash is credited with the interest it
  would actually have earned.
* **Tax is modelled, and reported beside the pre-tax figure.** Each strategy
  is simulated twice, because a taxed run pays its bill out of the book as it
  goes, so that run's CAGR *is* the after-tax number and cannot double as the
  pre-tax one. India's 20% STCG / 12.5% LTCG changes the ranking of
  rebalancing cadences outright.

`--validate` exists because Yahoo applies some NSE splits to only part of a
series: NIFTYBEES printed −89.9% then +896.9% across 2019-12-19..23, GOLDBEES
−99% then +9900%. Unrepaired, those produce a −90% "max drawdown" on a market
that fell 38%. `index_data.repair` fixes the three artefact shapes and logs
every repair; `tests/test_index_investing.py` checks it leaves a real −20.5%
crash untouched.

Verification: `PYTHONPATH=. python3 -m tests.test_index_investing` — 13 checks,
no database needed. The important one asserts no signal reads a price it would
trade at.

## Jobs: pull data, analytics, screening — separately or chained

Offline work is split into jobs, in layers; each layer reads only what the
layers above it produced (`jobs/registry.py`):

| layer | jobs | network | cadence |
|---|---|---|---|
| reference | `universe`, `names`, `classify`, `industries` | yes | weekly / monthly |
| data | `prices`, `indexes`, `earnings`, `fundamentals` | yes | prices & indexes daily, the rest weekly |
| analytics | `breadth`, `sectors` | no | daily, after prices |
| screening | `screen` (one step per strategy), `quality` | `screen` no, `quality` yes | daily / weekly |
| publish | `report`, `ingest` | no | after screening |

Data jobs never screen, and screening never downloads: `screen` reads stored
prices (`cache.offline()`) and refuses to run when they are two or more
trading days behind (`--allow-stale` overrides). Every job is idempotent and
records each step in the run log, which the web app's **Data status** page
shows.

```
python -m jobs list                                 # every job and pipeline, with its last run per market
python -m jobs run prices --market india            # just pull data
python -m jobs run breadth sectors --market us      # just analytics
python -m jobs run screen --market us --strategies all
python -m jobs run daily --market india             # pipeline: universe (if stale) → prices → indexes → breadth → sectors → screen → report → ingest
python -m jobs run daily --market us --from screen  # resume part-way
python -m jobs run weekly                           # universe, names, classify, earnings, fundamentals, quality
python -m jobs run monthly                          # re-classify industries
python -m jobs status                               # how current every dataset is
python -m jobs schedule                             # suggested crontab: India after its close, US the next morning
```

Each run logs to `logs/jobs/<timestamp>_<name>.log` and prints a cross-market
summary of tradeable/watchlist candidates after the report. A single strategy
can still be run directly: `python3 -m swing_screener.screening.pipeline
--market us --strategy breakout` (stored prices; `--pull` to fetch first,
`--limit N` for a quick test run).

**Output**: `reports/<market>_universe.csv` — one row per stock that
passed the loose screener, every outcome as an explicit column
(`decision`, `tradeable`, `watchlist_candidate`, `uptrend_intact`,
`gate_<code>` per hard gate, `watch_<code>` per watch flag...). Filter it
in a spreadsheet however you want instead of cross-referencing several
files. A timestamped snapshot also goes to `reports/history/`, and every
run is recorded in Postgres so you can diff decisions across runs — see
"Run history" below.

## Inspect a single stock

```
python3 -m swing_screener.screening.inspect --market india --symbol RELIANCE.NS
```

Full gate-by-gate breakdown (every hard gate pass/fail with its reason,
watch flags, setup gates) plus the entry plan/sizing/decision if it clears
everything. `--fresh` bypasses the cache and pulls live data instead.

## Run history / diffing

```
python3 -m swing_screener.screening.history --market india              # diff latest vs previous run
python3 -m swing_screener.screening.history --market india --list        # list recorded runs
python3 -m swing_screener.screening.history --market india --from <run_id> --to <run_id>
```

Every `pipeline.py`/`daily.py` run (not `--limit` test runs) appends to
Postgres's `universe_history` table and prints what changed since the
prior run automatically — symbols whose decision flipped, and symbols
that newly entered/left the filtered universe.

## Backtest

```
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --sample 500
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --exit-mode trail_atr --no-target
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --per-symbol   # old mode
```

**Portfolio-level by default.** One shared pool of capital, a cap on
simultaneously held positions (`max_open_positions`, default 10), costs on
both sides (slippage bps + commission), sizing that compounds off current
equity, and ranking when more signals trigger than there are free slots.
Signals arriving with no slot are *missed*, as they would be in a real
account.

This matters: the old per-symbol mode held an average of 24 and a peak of
51 positions at once — 51% of the account at risk simultaneously, needing
~13x the stated capital. Its aggregate P&L was never achievable. It is
kept as `--per-symbol` for comparison only, and prints a warning saying so.

Reports: CAGR, max drawdown (and longest stretch underwater), volatility,
Sharpe, Sortino, Calmar, exposure, turnover, profit factor, costs paid, a
buy-and-hold benchmark comparison with excess CAGR, an ASCII equity curve
with a drawdown panel, and a caveats block. Writes `<stem>_trades.csv` and
`<stem>_equity.csv` to `reports/`.

Fills are deliberately pessimistic: a bar that gaps past the stop fills at
the open, not the stop (16.4% of stop exits gap through, averaging -1.50R
rather than -1.00R); a buy-stop that gaps above its trigger fills at the
open, which also widens the risk denominator; an order gapping clean past
its target is cancelled rather than booked.

`--exit-mode` tests whether the fixed measured-move target caps the right
tail that trend-following depends on: `bracket` (the strategy's own
stop+target), `trail_atr`, `ma`, `donchian`, with `--no-target` to let
winners run. R is always measured against the stop accepted *at entry*,
never the trailed stop.

Use `--sample N` rather than `--limit N`: `--limit` slices the candidate
list in universe-file order, which is roughly alphabetical and therefore a
biased sample. `--sample` is a seeded random subset.

True walk-forward: every simulated day sees only data up to and including
itself. Candidate selection is **point-in-time** — a symbol qualifies if it
would have been screened in on at least one bar *in the window*, not if it
passes today. Selecting on today's row leaked the present into the past and
silently discarded 2,167 of 3,290 real candidates over a 14-year window.

`classify()` is the single arbiter of whether a signal is tradeable; the
backtest no longer re-implements its risk/R thresholds inline.

`--deep-lookback-days` (default 1000 trading days, ~4 years) controls how
far back candidate history is pulled — needs to comfortably exceed your
backtest window plus ~24 months, since several gates need two years of
trailing history.

**Signal caching**: the expensive part (rebuilding swing structure,
running every gate for a given symbol-day) is cached in Postgres's
`backtest_signals` table on first run. Re-running after tweaking a
*trade-simulation* parameter (stop-buffer multiplier, risk/R thresholds,
pending-order expiry days, position sizing) reuses the cached gate/setup
results and only re-runs the cheap part — should turn a slow full
walk-forward into a fast iteration loop. Pass `--no-signal-cache` if
you've changed actual gate logic (`gates.py`/`swings.py`), not just
trade-sim parameters, since those need a fresh recompute.

The first pass over a long window is slow (~13s/symbol over 14 years,
because `build_context` rebuilds swing structure per bar), but it populates
the cache — subsequent runs over the same window take minutes.

## Long history (do this before judging any strategy)

```
python3 -m swing_screener.marketdata.backfill --market us --years 16
python3 -m swing_screener.marketdata.backfill --market us --only-short   # resume
python3 -m swing_screener.marketdata.backfill --market us --report       # coverage
```

The incremental cache only ever extends the tail; it will not fetch more
history *before* an existing start date. Without this, every backtest runs
on ~2 years — one bull market — which is the single environment where a
trend strategy is structurally handicapped (it sits partly in cash while
the index compounds). 16 years brings 2015-16, Q4 2018, the 2020 crash and
the 2022 bear into the window. Checkpoints per symbol; ~26 min and ~15M
bars for the US universe.

## Baseline (the reference every strategy must beat)

```
python3 -m swing_screener.backtesting.baseline --market us --start 2013-01-01 --top-n 50
```

Cross-sectional momentum: rank by 12-1 month return, hold the top N
equal-weight, rebalance monthly, within the top 1,000 by dollar volume.
Two real parameters, no gates or setups. Deliberately *not* built on the
`Strategy` ABC — ranking is a decision across symbols on one date, whereas
the ABC evaluates one symbol in isolation.

Without a baseline there is no way to answer whether 14 hard gates and 9
watch flags beat the simplest expression of the same idea. Measured over
13.75 years, they have to clear roughly 9% CAGR at a -50% drawdown (top-50)
— and SPY itself did 12.79% at -34%.

## Experiments (controlled A/B)

```
python3 -m swing_screener.backtesting.experiments --market us --start 2013-01-01 --exits
python3 -m swing_screener.backtesting.experiments --market us --start 2013-01-01 --caps
```

Collects signals **once** and simulates every variant against the identical
set, so only the knob under test differs. Re-scanning per variant would let
scan-level differences leak into the comparison.

## Earnings dates (D2 gate)

Auto-fetched via `yfinance`'s `Ticker.calendar` (confirmed working for
both US and NSE tickers) for whatever small set of tickers survives the
loose screener filter — one request per ticker, cached in
`data/earnings_cache_<market>.csv` with a 7-day refresh window. If a date
is ever wrong or missing, override it in `data/earnings_<market>.csv`
(`symbol,next_earnings_date`) — overrides always win over the auto-fetch.

## Universe

The ticker list is a CSV you maintain, not re-derived every run (sector
tags barely change — see `universe.py`):

- `data/universe_us.csv` — one `ticker` column. Generate it once from
  Nasdaq Trader's official symbol directory:
  `python3 -c "from swing_screener.universe import fetch_us_universe_from_nasdaqtrader as f; f()"`
  or pass `--refresh-universe` to the CLI.
- `data/universe_india.csv` — one `ticker` column, NSE symbols with the
  `.NS` suffix (e.g. `RELIANCE.NS`). Generate it once via yfinance's
  screener wrapper (an unofficial but working proxy for Yahoo's own equity
  screener — ~3,400 NSE equities, paginated automatically):
  `python3 -c "from swing_screener.universe import fetch_india_universe_from_yfinance_screener as f; f()"`
  or pass `--refresh-universe` to the CLI.

Sector tags are looked up lazily (yfinance `.info`) only for tickers that
survive the loose screener filter, and cached forever in
`data/sector_cache_<market>.csv`.

## Chart patterns (`--strategy chart_pattern`)

Six classical bases are detected geometrically in
[`core/chart_patterns.py`](swing_screener/core/chart_patterns.py), which is
strategy-agnostic: a detector returns the pivot to clear, the structural low a
stop belongs under, the measured move the pattern projects, its depth, length
and a 0-1 quality score — and no opinion about whether any of that is
tradeable.

| code | pattern | pivot | stop under | measured move |
|---|---|---|---|---|
| `CUPNH` | cup without a handle yet — price still pinned to the rim | right rim | recent low | cup depth |
| `CUP` | cup-and-handle, 12-50% deep; handle 5-20 bars, 2-15% deep, drifting under 1.2%/bar on volume below the cup's | right rim | handle low | cup depth |
| `DBOT` | double bottom, lows within 5%, 8%+ rally between | middle peak | second low | peak minus low |
| `FLAT` | flat base / Darvas box, under 15% over 25-65 bars | box top | box low | the prior advance |
| `FLAG` | bull flag; 20%+ pole retracing under 40% | pole high | flag low | pole height |
| `ATRI` | ascending triangle, 3 highs within 3%, rising lows | resistance | last swing low | triangle height |
| `VCP` | 2+ contractions, each under 0.8x the last, final under 12% | last high | last swing low | base height |

The strategy on top of it (`strategies/chart_pattern.py`) adds the opinions:
gates P1-P7 (SMA200 intact and not falling, within 15% of the 52-week high,
ATR% under 10, no earnings inside 10 days, a pattern scoring at least 0.45,
and price no more than 4% above the pivot), a uniform entry a tick through the
pivot, a stop never wider than 2 ATR, and rejection of anything whose own
measured move projects under 2R.

### The noise floor — read this before trusting any of it

`tests/test_chart_patterns.py` measures how often each detector fires on a
**pure random walk**. Measured 2026-10-04 over 150 seeded walks of 420 bars:

| pattern | random walks | liquid US stocks |
|---|---|---|
| `VCP` | 44.0% | 27% |
| `FLAT` | 31.3% | 11% |
| `DBOT` | 30.7% | 27% |
| `FLAG` | 11.3% | 4% |
| `ATRI` | 8.7% | 10% |
| `CUPNH` | 4.7% | — |
| `CUP` | 0.7% | 0.2% |
| **any** | **75%** | **55%** |

(Real-market column: 519 liquid US names, same day. The two columns are not
perfectly matched — different volatility, drift and history length — so read
the order of magnitude, not the decimals.)

Three quarters of random walks contain one of these shapes, and `VCP`, `DBOT`
and `FLAT` appear in noise about as readily as in the market. A rule that
fires on 75% of noise cannot be selective no matter whose name is on it, and
it explains the backtest without appeal to anything subtler: the strategy's
most-traded patterns were `FLAT` (57 trades) and `ATRI` (34), which are
exactly the ones noise produces. `CUP` is the outlier in the other direction —
rare in both columns — and is the only one of the seven whose match says
something unusual is on the chart.

The test enforces per-pattern ceilings a few points above those rates, so
loosening a detector fails loudly rather than quietly raising the noise floor.

### Topping structures (`DTOP`, `HSTOP`) — veto, not entry

The book is long-only, so a top cannot be sold. `detect_topping()` is a
separate call from `detect_patterns()` precisely so a bearish match can never
reach code that builds entries, and the strategy consumes it as watch flag
`XP5`, which caps confidence (`confirmed` -> WATCH, `forming` -> TRADE ON
TRIGGER) and never creates or blocks a setup by itself.

For these two codes the fields carry mirrored meanings: `pivot` is the
**neckline**, `stop_ref` the peak, and `measured_move` projects **down**.

A top is only a veto while it is LIVE, which took three rules to get right,
each from a live false positive:

- price takes out the last peak, so it was resistance rather than a reversal
  (PLTR showed a "confirmed H&S, head 207.52" while trading at 188, having
  already cleared its 187.28 right shoulder);
- the neckline break fails and price recovers above it — a *failed* top is a
  bullish event, and vetoing a long on it is exactly backwards (DOCU, neckline
  63.50, price 69.01);
- the structure is simply old (TECH, a neckline of 48.25 against a 72.40 price).

And one conceptual trap: **a cup's two rims are a double top** until the
breakout happens. GILD's cup matched its own geometry as a "forming double
top". A forming top therefore requires price to have given back half the
distance from the peak to the neckline — short of that, the decline is
indistinguishable from a handle. With all four rules, live tops appear on
~9% of names that pass the trend gates.

### Confidence, and why a match is not ideal

A detector's bounds are what it ACCEPTS; the textbook describes what is
IDEAL. `chart_patterns.py` keeps the two apart (`IDEAL_CUP_DEPTH`,
`IDEAL_HANDLE_BARS`, `RIM_RECOVERY_TOL`, ...) and reports the gap instead of
dropping the match, because a 49%-deep cup whose right side has not reached
its own rim is a real structure worth watching — it is just not the thing the
pattern's statistics are about.

Each match carries `flaws` (plain-language deviations, `major` or `minor`)
and a `confidence` grade derived from them:

| grade | means |
|---|---|
| `textbook` | no major deviations, at most one minor |
| `moderate` | one major, or two to three minors |
| `low` | two or more majors, or four or more minors |
| `unassessed` | that detector does not grade yet (only `CUP` does so far) |

It is a measure of **resemblance, not probability** — nothing here forecasts.
`find_pattern` groups its output by grade and prints the flaws under each
name; the daily screener carries them as `pattern_confidence` and
`pattern_flaws`.

Worked example — PLTR, 2026-10-02, graded `low`:

```
cup is 49% deep, beyond the textbook 12-33% — a deep base is a damaged one;
right rim 194.68 is 6.2% below the left rim 207.52 — the cup has not
  recovered to its own rim, so what looks like a handle may still be part
  of the right side;
handle is only 6 bars — handles usually take 8-20 (2-4 weeks), so this one
  may still be forming
```

**Anchor the cup to the prior peak.** Where several swing highs qualify as
the left rim, take the HIGHEST. Keeping the best-scoring one instead (the
first version did) reports the most flattering reading of every chart: PLTR's
prior peak is 207.52, but anchoring to a later 187.28 swing high scored
better — a 43% cup with its right rim 4% *above* the left, rather than a 49%
cup still 6% *below* it — so that is what it published, and it disagreed with
every human who looked at the chart.

The handle bounds are the fussiest part and were tightened after a manual
chart review: the first version accepted a 6-bar 8.5% rejection at the rim on
rising volume, a 37-bar drift, and a 0.5%-deep flat pause as "handles". Each
bound in `detect_cup_handle` names the live example it exists to exclude.
**The backtest below predates that change**, so its `CUP` row is stale.

Two details that are easy to get wrong and are deliberate here:

- **Pivots are computed from bars before the current one.** Otherwise the
  breakout bar's own high defines the level it is breaking, every pattern
  "breaks out" by construction, and a backtest of it means nothing. Lows (for
  stops) and volume do use the current bar, which is known at the close.
- **Overhead supply within 1 ATR of the entry does not cap the target.** A
  base's ceiling is a zone, not a line — a cup's two rims, a triangle's three
  touches and a box top print at slightly different prices. Capping inside
  that zone says "this breakout cannot travel past the level it is breaking":
  on a 400-symbol US sweep it collapsed 20 of 25 targets below 0.5R. Both
  numbers are reported, `structural_r` (what the pattern projects) and
  `target_r` (after the cap), so the two never get confused.

### Status: backtested, and it lost

US, 2020-01-02 → 2026-10-02, 300-symbol sample, bracket exit:

| | strategy | benchmark |
|---|---|---|
| CAGR | **-3.26%** | +13.63% |
| max drawdown | -38.98% | -34.10% |
| Sharpe | -0.26 | 0.74 |
| trades / win rate | 140 / 19.0% | — |
| avg R per trade | -0.214 (PF 0.75) | — |

Total R by pattern: `FLAT` -11.9 (57 trades), `DBOT` -7.5 (13), `ATRI` -4.7
(34), `CUP` -3.0 (3), `FLAG` +0.1 (26), `VCP` +2.4 (7). Nothing with a
meaningful sample made money; 111 trades stopped out against 26 that reached a
target.

### Does selectivity help? (`chart_pattern` vs `chart_pattern_cup`)

Same window, same seeded 300-symbol sample, same exit; the only difference is
that the `_cup` variant switches off the five detectors that fire on random
data.

| | full set | cup only |
|---|---|---|
| CAGR | -4.08% | **-0.24%** |
| max drawdown | -42.2% | **-13.0%** |
| trades / win rate | 146 / 18.2% | 32 / 25.0% |
| avg R per trade | -0.213 | **-0.019** |
| profit factor | 0.71 | 0.94 |
| t-stat on avg R | -1.24 | -0.04 |

Every headline favours the selective detector, and **none of it is
significant**: the difference is +0.194R, Welch t = 0.42, bootstrap 95% CI
[-0.67, +1.12], P(cup better) = 0.66. Both expectancies are indistinguishable
from zero. 32 trades in 6.75 years is the price of selectivity — settling this
needs roughly 10x the sample (full universe, full 13.75-year window).

Two things worth carrying forward. A full day of detector work — tightening
the handle, anchoring cups to the prior peak, adding `CUPNH`, adding the
topping veto — moved per-trade expectancy from **-0.214R to -0.213R**. And of
the cup run's 32 trades, 27 were `CUPNH` (-0.25R) against 5 `CUP` proper
(+1.23R); five trades is not a finding.

**The exit is not the problem.** All eight exit policies over that identical
193-signal set:

| variant | CAGR% | maxDD% | excessCAGR% | win% | avgR |
|---|---|---|---|---|---|
| `donchian-20d-noTarget` | **+0.27** | -28.55 | -13.37 | 22.8 | -0.028 |
| `trail_atr-5ATR-noTarget` | -0.00 | -31.04 | -13.64 | 20.9 | +0.014 |
| `donchian-50d-noTarget` | -0.19 | -34.54 | -13.82 | 19.3 | -0.039 |
| `ma-sma50-noTarget` | -1.32 | -26.31 | -14.95 | 25.2 | -0.113 |
| `ma-sma20-noTarget` | -2.14 | -23.37 | -15.77 | 33.1 | -0.127 |
| `trail_atr-3ATR-withTarget` | -3.17 | -28.11 | -16.81 | 27.0 | -0.156 |
| `bracket-withTarget` | -3.26 | -38.98 | -16.90 | 19.0 | -0.214 |

The exit choice is worth about three points of CAGR and none of the 13-17
point shortfall against the benchmark. Letting winners run (`--no-target`)
helps, as it did for `donchian` — but it lifts the strategy to roughly zero,
not to an edge. There is no edge in the entry for a better exit to protect.

One market, one window — so this is not proof that the shapes
carry no information. It is, however, a measured loss, which is where the
burden of proof now sits. The thresholds are the conventional published ones
(O'Neil, Darvas, Minervini) and were not fitted to this data, so the result is
at least not an artefact of tuning. Detection itself is cheap (~1ms per
symbol-day against `build_context`'s ~11ms), so re-measuring costs little:

```
# does a different exit policy rescue the same signals?
python3 -m swing_screener.backtesting.experiments --market us --start 2020-01-01 \
    --strategy chart_pattern --sample 300 --exits

# does shape beat the shapeless breakout, on one axis?
python3 -m swing_screener.backtesting.compare --market us --start 2020-01-01 \
    --strategies breakout chart_pattern --sample 300
```

## Chart links

Every report names a symbol AND links straight to its chart, because a
candidate has to be looked at before it is traded and retyping tickers is the
friction that stops you doing it:

- the pipeline CSV gains a `chart` column, next to `symbol`;
- `report.md` renders the ticker itself as the link, in both the candidates
  and watchlist tables;
- `find_pattern` prints the link under each match.

[`screening/links.py`](swing_screener/screening/links.py) holds everything
provider-specific — the URL template and the yfinance-suffix-to-exchange map
(`.NS` -> `NSE:`, `.BO` -> `BSE:`). Point `CHART_URL` elsewhere and every
report follows. US tickers are passed bare because the universe CSV carries no
exchange; TradingView resolves them itself, which is a guess on its part for a
ticker that also trades abroad.

## Known gaps (by design, not oversight)

- **India sector/breadth indices**: the tickers in
  `config/india.py` (`SECTOR INDEX MAP`, `NIFTY500`, `NIFTYMIDCAP150`) are
  best-effort guesses at Yahoo's naming and some don't resolve (confirmed:
  `NIFTY_MIDCAP_150.NS`, `NIFTY_FIN_SERVICE.NS` 404 as of this build).
  The pipeline degrades gracefully — it logs a warning and skips that
  sector/index rather than crashing — but sector grouping and the
  market-regime downgrade will be incomplete until you fix the symbols or
  swap in the Chartink OAPI endpoint the India prompt already uses.
- **Kite Connect**: not wired up. It's a paid add-on (₹500/mo) on top of a
  Zerodha account, with a daily-refreshing access token that's extra
  friction for an unattended script — `providers/base.py` is the
  interface to implement against if you want to add it later for
  better/official NSE data.
- **Candlestick/demand-supply thresholds**: the prompt names some patterns
  without pinning exact numbers (what counts as "a gap", "3-bar
  reversal", "high-volume down bar"). `patterns.py` and
  `demand_supply.py` comment exactly where a judgment call was made.
- **Backtest earnings**: no historical point-in-time earnings calendar is
  cached, so D2 is never enforced in `backtest.py` — see its module
  docstring for the full list of backtest-specific methodology caveats.
- **Survivorship bias (the largest remaining flaw)**: the ticker list is
  today's listed names, so every company delisted, acquired or bankrupted
  during the window is absent. Returns are biased upward, and the bias
  grows the further back the window reaches. Only point-in-time
  constituent data (CRSP, Norgate, Sharadar) fixes it. Every backtest
  prints this in its caveats block.
- **Dividends** are excluded on both the strategy and the benchmark, so
  absolute returns understate reality for both. Since the strategy is only
  ~70-99% invested, a price-only comparison mildly flatters it.
- **Signal generation is O(n^2) per symbol**: `build_context` rebuilds the
  weekly/monthly resamples and swing structure for every screened-in bar,
  so a 14-year window costs ~13s/symbol on the first pass. The Postgres
  signal cache makes re-runs fast; making the first pass fast would need
  incremental swing detection.
- **The confidence tiers do not discriminate.** Measured over 484 trades,
  `TRADE - HIGH CONFIDENCE` performed no better than the `TRADE ON
  TRIGGER` tier it downgrades (25.1% vs 29.7% win rate; both t<0.4 after
  correcting for censoring and regime). The X1-X9 watch-flag machinery
  carries no measurable information as currently calibrated.

## Layout

Code is grouped by topic, so a strategy or the backtesting machinery can be
read as a unit:

```
swing_screener/
  paths.py          every filesystem location, defined once
  config/           MarketConfig for US and India (account, thresholds,
                     sector maps, costs, position caps)
  providers/        pluggable price-data sources (yfinance implemented)

  core/             market primitives, strategy-agnostic
    indicators.py    SMA/EMA/RSI/ATR/ADX (Wilder), resampling
    swings.py        swing highs/lows, H/L/P, overhead levels
    chart_patterns.py cup-and-handle, double bottom, flat base, flag,
                      ascending triangle, VCP — geometry only
    context.py       StockContext: the per-symbol frames every strategy reads
    patterns.py      candlestick classifier
    demand_supply.py demand/supply point-scoring verdict
    regime.py        market + per-sector regime
    sizing.py        position sizing

  strategies/       one file per strategy, behind one interface
    base.py          the Strategy ABC + StrategyResult/TradePlan/Decision
    trend_pullback.py  gates W/T/D, flags X1-X9, setups TC-01/02/04
    breakout.py      gates B1-B7, setups BO-01/02 — NOT validated
    donchian.py      N-day channel breakout, M-day-low exit — NOT validated
    chart_pattern.py gates P1-P7, one setup per named pattern — NOT validated
    __init__.py      registry + known defects left unfixed

  backtesting/      everything that evaluates a strategy
    backtest.py      signal generation + portfolio/per-symbol runners
    portfolio_sim.py the engine: shared capital, position cap, costs, exits
    metrics.py       equity-curve stats + ASCII equity curve
    report.py        markdown reports with charts
    baseline.py      cross-sectional momentum baseline
    experiments.py   controlled A/B over one signal set

  marketdata/       data in, storage (the only package that downloads)
    cache.py (incl. offline mode) db.py migrate.py universe.py names.py industries.py
    refresh.py backfill.py index_data.py earnings.py fundamentals.py freshness.py

  analytics/        market-wide measures from stored prices only
    breadth.py sectors.py

  screening/        the day-to-day screener
    screener.py pipeline.py daily.py output.py history.py inspect.py portfolio.py watchlist.py

  runlog.py         run log: every job's steps, timestamps, results (Data status page)
  web/              the read-only web viewer

jobs/               the offline jobs: registry (layers, cadence, dependencies), runner, CLI

tests/
  test_chart_patterns.py  draws each classical pattern on a synthetic chart
                     and asserts the detector finds it, that the current
                     bar never defines a pivot, and that a random walk
                     produces nothing. No database needed.
  golden_baseline.py  behaviour-preservation harness: records the full
                     gate/flag/setup/plan/decision output for a fixed sample,
                     so a refactor that changes behaviour shows up as a
                     field-level diff rather than surfacing in a backtest
```

Generated output lives **outside** this directory, at the repository root:
`reports/<market>/<strategy>/<run>/`, `logs/`, `data/`, `research/`.
Superseded material lives in `archive/`.

Adding a strategy means adding one file under `strategies/` and registering
it. If that ever requires editing the pipeline, the backtester, the reporter
or the storage layer, the abstraction has broken and should be fixed rather
than worked around.

See [`research/`](../research/) for findings — the results ledger, methodology
and known biases.
