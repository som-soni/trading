# swing_screener

A data-only Python port of the two prompts in `prompts/screeners/` —
`uptrend-daily-v2-swing-review.md` (US) and
`t-trend-up-india-swing-review.md` (India). Same gates, watch flags, entry
rules, sizing, and decision logic; no LLM calls, no screenshots. Pulls
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

## Run the daily screener

```
python3 -m swing_screener.daily                    # both markets
python3 -m swing_screener.daily --markets us        # one market
```

Auto-refreshes a market's ticker list if it's more than 7 days old
(`--refresh-stale-days` to change), runs both markets with per-market
failure isolation, logs to `logs/daily_<date>.log`, and prints a
cross-market summary of tradeable/watchlist candidates. Or run a single
market directly: `python3 -m swing_screener.pipeline --market us`
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
python3 -m swing_screener.inspect --market india --symbol RELIANCE.NS
```

Full gate-by-gate breakdown (every hard gate pass/fail with its reason,
watch flags, setup gates) plus the entry plan/sizing/decision if it clears
everything. `--fresh` bypasses the cache and pulls live data instead.

## Run history / diffing

```
python3 -m swing_screener.history --market india              # diff latest vs previous run
python3 -m swing_screener.history --market india --list        # list recorded runs
python3 -m swing_screener.history --market india --from <run_id> --to <run_id>
```

Every `pipeline.py`/`daily.py` run (not `--limit` test runs) appends to
Postgres's `universe_history` table and prints what changed since the
prior run automatically — symbols whose decision flipped, and symbols
that newly entered/left the filtered universe.

## Backtest

```
python3 -m swing_screener.backtest --market us --start 2025-01-01
```

True walk-forward simulation — every simulated day only sees data up to
and including itself (no lookahead), and only takes a trade if it would
have graded as `TRADE - HIGH CONFIDENCE` live (gates + setup + signal +
risk ≤7% + target ≥2R + demand/supply not "Supply in control"). Entries
are simulated as resting buy-stop orders checked against *future* days'
highs (not instant same-day fills — see the module docstring for the full
methodology and its stated limitations, e.g. no historical earnings
calendar, today's screener applied retroactively).

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

## Layout

```
swing_screener/
  config/           MarketConfig for US and India (account settings,
                     sector index maps, screener thresholds)
  providers/        pluggable price-data sources (yfinance implemented)
  db.py             Postgres connection + schema (prices, universe_history,
                     backtest_signals)
  cache.py          Postgres-backed price cache, incremental pulls,
                     precomputed indicators stored alongside raw OHLCV
  universe.py       ticker list + lazy sector lookup
  screener.py       the loosened screener filter, replicated locally
  indicators.py     SMA/EMA/RSI/ATR/ADX (Wilder smoothing), resampling
  swings.py         swing highs/lows, H/L/P, overhead levels, base/drift
  gates.py          STEP 3: hard gates (M/W/T/D), watch flags (X1-X9) —
                     X9 is the former M1 hard gate, demoted to a
                     discretionary flag (see gates.py for why)
  entry.py          ENTRY RULES: trigger/entry/stop/target, Plan A vs B
  patterns.py       candlestick pattern classifier
  demand_supply.py  demand/supply point-scoring verdict
  regime.py         STEP 1 market regime + per-sector regime
  sizing.py         STEP 5 position sizing
  decision.py       STEP 6 decision classification + sector filter
  output.py         the single filterable per-market report
  history.py        run history + diffing (Postgres-backed)
  backtest.py        walk-forward backtest with Postgres-cached signals
  inspect.py        single-stock gate/decision debug tool
  pipeline.py       single-market CLI orchestrator
  daily.py          both-markets wrapper for a morning run
test_synthetic.py   fast sanity check of the gate->entry->decision path
                     using engineered OHLCV (real market data doesn't
                     always produce a reviewable setup on a small universe)
```

If a gate, flag, or formula ever changes in the prompts, change it here
to match — these are meant to stay in lockstep, not drift into two
different sets of rules.
