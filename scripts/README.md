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

Every command runs from `scripts/` with `PYTHONPATH=.` set. All ten entry
points, grouped by what they are for:

| command | purpose |
|---|---|
| `screening.daily` | Both markets, one summary — the morning run |
| `screening.pipeline` | One market's screen → candidate CSV |
| `screening.inspect` | Why one symbol did or didn't qualify |
| `screening.history` | What changed between two runs |
| `backtesting.backtest` | Backtest a strategy (portfolio-level by default) |
| `backtesting.baseline` | The momentum baseline every strategy must beat |
| `backtesting.experiments` | Controlled A/B over one signal set |
| `backtesting.report` | Re-render a finished run as markdown + charts |
| `marketdata.backfill` | Pull long history (do this first) |
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

## Run the daily screener

```
python3 -m swing_screener.screening.daily                    # both markets
python3 -m swing_screener.screening.daily --markets us        # one market
```

Auto-refreshes a market's ticker list if it's more than 7 days old
(`--refresh-stale-days` to change), runs both markets with per-market
failure isolation, logs to `logs/daily_<date>.log`, and prints a
cross-market summary of tradeable/watchlist candidates. Or run a single
market directly: `python3 -m swing_screener.screening.pipeline --market us`
(`--refresh-universe`, `--limit N` for a quick test run).

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
| `CUP` | cup-and-handle, 12-50% deep, handle in the upper half | right rim | handle low | cup depth |
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

Status: **not backtested.** The thresholds are the conventional published ones
(O'Neil, Darvas, Minervini), not numbers fitted to this data. The first
question to settle is whether shape adds anything over `breakout`, which
requires no shape at all — if it does not, the shape is decoration. Detection
itself is cheap (~1ms per symbol-day against `build_context`'s ~11ms), so
testing it costs no more than any other strategy.

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

  marketdata/       data in, storage
    cache.py db.py migrate.py universe.py earnings.py backfill.py

  screening/        the day-to-day screener
    screener.py pipeline.py daily.py output.py history.py inspect.py portfolio.py

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
