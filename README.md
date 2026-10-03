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
```

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
      core/           indicators, swings, context — strategy-agnostic
      strategies/     one file per strategy, behind one interface
      backtesting/    simulator, metrics, reports, baseline, experiments
      marketdata/     cache, Postgres, universes, backfill
      screening/      the daily screener pipeline
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
| [`archive/README.md`](archive/README.md) | The original prompts and how they diverge from the code |

## A caution

The backtests here apply point-in-time screening, pessimistic fills, realistic
costs and portfolio-level capital constraints — but they still carry
**survivorship bias** (the universe is today's listed names) and have not been
validated out of sample. Nothing in this repository is investment advice.
