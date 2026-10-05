# Trading

A local, data-only system for screening and backtesting equity strategies in
the **US** and **India** markets. No LLM calls at runtime, no screenshots —
price data from yfinance, stored in Postgres, run from the command line.

Two things live here: a **screener** that produces a daily list of trade
candidates, and a **backtester** that measures whether a strategy is worth
running at all.

> **Read [`research/`](research/) before trusting any strategy in this repo.**
> The findings so far: the hand-built `trend_pullback` strategy has no edge in
> either market, while simple cross-sectional momentum beats the index in
> India (+6.23% CAGR) but not the US. The results ledger, methodology and known
> biases are all there.

---

## Quick start

```bash
cd scripts
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Needs a local Postgres with a `trading` database. Put credentials in
`scripts/.env` (gitignored):

```
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=<yours>
PGDATABASE=trading
```

Then pull history — **do this first; nothing is trustworthy on two years of
data**:

```bash
PYTHONPATH=. python3 -m swing_screener.marketdata.backfill --market india --years 16
```

---

## What do you want to do?

Every command runs from `scripts/` with `PYTHONPATH=.` set.

### Get today's trade candidates

```bash
# both markets, with a cross-market summary
python3 -m swing_screener.screening.daily

# one market
python3 -m swing_screener.screening.pipeline --market india

# a different strategy
python3 -m swing_screener.screening.pipeline --market india --strategy breakout

# breakouts from a named chart pattern (cup-and-handle, flat base, VCP...)
python3 -m swing_screener.screening.pipeline --market us --strategy chart_pattern
```

Writes `reports/<market>_<strategy>_universe.csv` — one row per stock that
passed the screen, with every gate, flag and decision as its own column, so it
can be filtered in a spreadsheet.

### Understand why one stock did or didn't qualify

```bash
python3 -m swing_screener.screening.inspect --market india --symbol RELIANCE.NS
```

Gate-by-gate pass/fail with reasons, watch flags, setups, and the entry plan
and sizing if it clears everything. `--fresh` bypasses the cache.

### See what changed since yesterday

```bash
python3 -m swing_screener.screening.history --market india          # diff last two runs
python3 -m swing_screener.screening.history --market india --list   # list recorded runs
```

### Backtest a strategy

```bash
# portfolio-level: one capital pool, position cap, costs — the default
python3 -m swing_screener.backtesting.backtest --market india --start 2013-01-01

# a seeded random subset, for speed (a full 14-year run takes ~9 hours)
python3 -m swing_screener.backtesting.backtest --market india --start 2013-01-01 --sample 500

# a different strategy
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --strategy breakout

# let winners run instead of taking a fixed target
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 \
    --exit-mode donchian --no-target
```

Produces `reports/<market>/<strategy>/<run>/` containing `report.md` (with
charts), `trades.csv`, `equity.csv` and `figures/`.

### Compare a strategy against the momentum baseline

```bash
python3 -m swing_screener.backtesting.baseline --market india --start 2013-01-01 \
    --top-n 50 --rebalance QE --cost-bps 25
```

Rank by 12-1 month momentum, hold the top N, rebalance, exit on dropping out.
Two real parameters. **Any strategy that cannot beat this is not worth its
complexity.**

### Test one variable at a time

```bash
# which exit policy is best, on an identical signal set
python3 -m swing_screener.backtesting.experiments --market india --start 2013-01-01 \
    --sample 500 --exits

# how sensitive is it to the position cap
python3 -m swing_screener.backtesting.experiments --market india --start 2013-01-01 \
    --sample 500 --caps

# risk-per-trade and notional cap together: can the book afford its own slots?
python3 -m swing_screener.backtesting.experiments --market us --start 2013-01-01 \
    --strategy donchian --sample 500 --sizing \
    --exit-mode donchian --no-target --donchian-bars 50
```

**`--caps` and `--sizing` hold the exit policy fixed while varying one other
thing, so pass the strategy's real exit policy.** They default to
`bracket`+target; donchian measured with a fixed target is not donchian, and
the mistake is invisible in the output unless you check the trade count and
median holding days against the strategy's own run.

### Change position sizing

`max_positions` x `max_position_pct` can exceed 100% of capital, in which case
the book runs out of cash before it runs out of slots and silently declines
most signals. Both markets ship 10 slots x 25% = 250%.

```bash
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 \
    --strategy donchian --exit-mode donchian --no-target \
    --risk-pct 0.005 --max-position-pct 0.15
```

The sizing appears in the run directory name, so configurations don't
overwrite each other. Check `report.md` for the line reporting how many
signals were declined for insufficient cash — if it dwarfs the trade count,
the book is the binding constraint, not the strategy.

### Decide when to put money into the index

A separate question from which stock to buy, so a separate suite — SIP
timing, trend overlays, allocation and rotation, on dividend-inclusive index
series going back to 1980 (US) and 1997 (India).

```bash
# once: fetch total-return index series, then check them for vendor artefacts
python3 -m swing_screener.marketdata.index_data --refresh
python3 -m swing_screener.marketdata.index_data --validate

python3 -m swing_screener.backtesting.index_investing --market us
python3 -m swing_screener.backtesting.index_investing --market india --family A
```

Four families: **A** contribution timing (day-of-month, day-of-week,
frequency, lump sum vs DCA, dip-buying, value averaging), **B** lump-sum
timing overlays, **C** static allocation and rebalancing cadence, **D**
rotation between index sleeves. Results carry pre-tax *and* after-tax columns,
cash earns the real T-bill/liquid-fund rate, and every calendar experiment is
scored against a randomised-day null — because the best of 30 contribution
days is a selected maximum before it is a finding. See
[`research/index-investing-research.md`](research/index-investing-research.md).

### Browse charts and reports in a web UI

A read-only viewer: TradingView-style price charts (candles, volume, SMAs,
RSI, daily/weekly/monthly), the screener's entry/stop/target levels drawn on the
chart, backtest trades overlaid as markers, plus every screening run and
backtest/index report. Strategies still run offline; this only displays results.

```bash
cd scripts
PYTHONPATH=. python3 -m swing_screener.web          # http://127.0.0.1:8000
```

The **Strategies** page explains every strategy — thesis, each hard gate,
watch flag and setup, entry/stop/target and exit rules, live parameter values
per market, and its backtest results. It is generated from the strategy
classes themselves (`strategies/docs.py`), and
`PYTHONPATH=. python3 -m tests.test_strategy_docs` fails when a strategy's
code and documentation drift apart — run it after any strategy change (see
`CLAUDE.md`).

Reports (`report.md`, figures, trades, equity, CSVs) and `research/*.md` are
loaded into Postgres (`report_runs`, `report_figures`, `report_tables`) at
startup, and again with the **Refresh reports** button or
`python3 -m swing_screener.web.ingest` after a new run. Prices and screener
history come from the existing `prices` / `universe_history` / `index_series`
tables.

### Keep a watchlist

Every full screening run updates the watchlist automatically: a name is on it
while its strategy marks it `tradeable` or `watchlist_candidate` (the same
rule as the daily summary's watchlist section) and drops off when it no longer
does. Add your own names in the web UI (Watchlist page, or ☆ next to the symbol
on the chart) or from the command line — the screener never touches those.

```bash
python3 -m swing_screener.screening.watchlist --list
python3 -m swing_screener.screening.watchlist --add AAPL --market us --note "breakout above 235"
python3 -m swing_screener.screening.watchlist --remove AAPL --market us
python3 -m swing_screener.screening.watchlist --sync-latest   # rebuild from the latest recorded runs
```

Removing a screener name hides it until it drops off the screen and is flagged
again, so the next run doesn't put it straight back.

### Re-render a finished run as a report

```bash
python3 -m swing_screener.backtesting.report --list
python3 -m swing_screener.backtesting.report \
    --market india --strategy momentum_baseline --run 2013-01-01_top20_mom252_ME_25bps
```

No re-simulation — it rebuilds from the run's saved CSVs.

---

## Layout

```
trading/
  scripts/        code — see scripts/README.md for the full guide
    swing_screener/
      core/           indicators, swings, chart patterns, context — strategy-agnostic
      strategies/     one file per strategy, behind one interface
      backtesting/    simulator, metrics, reports, baseline, experiments,
                      index-investing suite (core/allocate/accumulate/stats)
      marketdata/     cache, Postgres, universes, backfill
      screening/      the daily screener pipeline
      web/            read-only viewer (FastAPI + static JS) and report ingest
    tests/            behaviour-preservation harness
  data/           inputs: universe lists, earnings overrides
  reports/        generated output — one directory per run (gitignored)
  logs/           run logs (gitignored)
  research/       findings: results ledger, methodology, known biases
  archive/        superseded material, kept not deleted
```

## Further reading

| | |
|---|---|
| [`scripts/README.md`](scripts/README.md) | Full command reference, how the strategy works gate by gate, known gaps |
| [`research/`](research/) | What has been tested and what the numbers were |
| [`research/index-investing-research.md`](research/index-investing-research.md) | Index investing: SIP timing, overlays, allocation — results and caveats |
| [`archive/README.md`](archive/README.md) | The original prompts and how they diverge from the code |

## A caution

The backtests here apply point-in-time screening, pessimistic fills, realistic
costs and portfolio-level capital constraints — but they still carry
**survivorship bias** (the universe is today's listed names) and have not been
validated out of sample. Nothing in this repository is investment advice.
