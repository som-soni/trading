# Cross-sectional momentum baseline

`momentum_baseline` · family **momentum_baseline** · **v1.0** · fingerprint `df30f7bc`

> Reference portfolio, not a screener strategy. Beats the index in India; not in the US (see research/momentum-trend-research.md).

Rank by 12-1 month momentum, hold the top N, rebalance on a calendar; the benchmark every strategy must beat.

## Thesis

Stocks that have outperformed over the past year keep outperforming for months (cross-sectional momentum), so simply holding the strongest names should beat the index after costs.

## How it works

1. On each rebalance date, score every eligible stock by its return over the last `--lookback` bars, skipping the most recent `--skip` bars (the 12-1 convention, which avoids the short-term reversal of the latest month).
2. Only the `--liquidity-top` most liquid names are ranked, so the list is not filled with speculative microcaps.
3. With the trend filter on (the default), a stock must also be above its 200-day moving average to be held.
4. Hold the top `--top-n` names, equal-weighted by default (`--weighting inverse_vol` sizes by inverse volatility).
5. A holding is sold when it drops out of the top N at a rebalance or loses its trend; there are no stops, targets or entry triggers.
6. Costs of `--cost-bps` per side are charged on every trade; whole shares only unless `--fractional`.

## Parameters

| parameter | value | meaning |
|---|---|---|
| --top-n | `None` |  |
| --lookback | `None` | momentum lookback in bars |
| --skip | `None` | bars to skip (12-1 convention) |
| --rebalance | `None` | pandas offset alias: ME, QE, W-FRI |
| --no-trend-filter | `None` | drop the >200DMA requirement |
| --cost-bps | `None` |  |
| --fractional | `None` | allow fractional shares — without it any stock priced above its per-name allocation is silently skipped |
| --rank | `None` | ranking signal: raw momentum, volatility-scaled (Barroso-Santa-Clara), market-residual (Blitz), or path quality (share of positive days) |
| --weighting | `None` | equal capital, or inverse to each name's volatility |
| --vol-target | `None` | annualised portfolio vol to scale gross exposure to, e.g. 0.15. Never leverages — exposure caps at 100% |
| --index-overlay | `None` | hold nothing while the benchmark is below its long moving average (cut SPY's max drawdown -50.8% -> -23.0%) |
| --overlay-months | `None` |  |
| --min-turnover | `None` | 20-day average turnover floor in account currency (overrides the market config). This is the real universe control — see --liquidity-top. |
| --liquidity-top | `None` | rank momentum only within the N most liquid names (0 = whole universe). Guards against the rank filling with speculative microcaps. |
| --no-ingest | `None` | skip updating the viewer database after the run |

## Known caveats

- Survivorship bias: the universe is today's listed names, which flatters every backtest here.
- Results depend on the rebalance cadence and N; compare runs with the same settings.
- Optional overlays (`--index-overlay`, `--vol-target`, alternative `--rank` signals) are experiments, not the baseline itself.

## Changelog

| version | date | change |
|---|---|---|
| 1.0 | 2026-10-09 | Brought into the registry so it carries a version and a generated spec. Defaults unchanged: top 10, 12-1 momentum, monthly rebalance, 5bps a side, 200-day trend filter on. |

## Commands

```bash
python3 -m swing_screener.backtesting.baseline --market india --start 2013-01-01 --top-n 20 --cost-bps 25
```

---

*Generated from `scripts/swing_screener/backtesting/baseline.py`. Do not edit by hand — re-run `python3 -m swing_screener.strategies.docs --write`.*
