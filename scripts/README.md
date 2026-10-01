# swing_screener

A data-only Python port of the two prompts in `prompts/screeners/` —
`uptrend-daily-v2-swing-review.md` (US) and
`t-trend-up-india-swing-review.md` (India). Same gates, watch flags, entry
rules, sizing, and decision logic; no LLM calls, no screenshots. Pulls
price data with [yfinance](https://pypi.org/project/yfinance/) (free, no
auth), caches it locally so re-runs only fetch new bars, and writes a
decision table, full-universe appendix, tradeable CSV, and watchlist to
`reports/`.

## Setup

```
cd scripts
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

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

## Run

```
python3 -m swing_screener.pipeline --market us
python3 -m swing_screener.pipeline --market india
```

`--refresh-universe` regenerates `universe_us.csv` first.
`--limit N` caps the universe for a quick test run.

Output goes to `reports/<market>_decision_table.csv`,
`_full_universe.csv`, `_tradeable.csv`, `_watchlist.csv`, plus a console
summary.

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

## Layout

```
swing_screener/
  config/           MarketConfig for US and India (account settings,
                     sector index maps, screener thresholds)
  providers/        pluggable price-data sources (yfinance implemented)
  cache.py          local parquet cache, incremental pulls
  universe.py       ticker list + lazy sector lookup
  screener.py       the loosened screener filter, replicated locally
  indicators.py     SMA/EMA/RSI/ATR/ADX (Wilder smoothing), resampling
  swings.py         swing highs/lows, H/L/P, overhead levels, base/drift
  gates.py          STEP 3: hard gates (M/W/T/D), watch flags (X1-X8),
                     setup gates (TC-01/TC-02/TC-04)
  entry.py          ENTRY RULES: trigger/entry/stop/target, Plan A vs B
  patterns.py       candlestick pattern classifier
  demand_supply.py  demand/supply point-scoring verdict
  regime.py         STEP 1 market regime + per-sector regime
  sizing.py         STEP 5 position sizing
  decision.py       STEP 6 decision classification + sector filter
  output.py         decision table, appendix, CSV, watchlist
  pipeline.py       CLI orchestrator
test_synthetic.py   fast sanity check of the gate->entry->decision path
                     using engineered OHLCV (real market data doesn't
                     always produce a reviewable setup on a small universe)
```

If a gate, flag, or formula ever changes in the prompts, change it here
to match — these are meant to stay in lockstep, not drift into two
different sets of rules.
