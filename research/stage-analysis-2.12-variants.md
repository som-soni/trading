# Stage analysis 2.12 — optimise A/B and its pass criteria

Written 2026-11-11, before any 2.12 run exists. Nothing below may change after a run is seen.

## Why these variants

They come from a review of the 2.11 optimise runs (2013–2021): run #2263 (US) and run #2264 (India). The verify runs
were not read beyond their headline verdict, which was FAIL in both markets.

| Variant | Finding it tests | Evidence |
|---|---|---|
| `MAX_STAGE2_WEEKS` = 26, 39, 52 (G10) | Entries made late in Stage 2 are weak | Entries more than 30 weeks into Stage 2 averaged +0.13R (US, 48 trades) and −0.25R (India, 13 trades), against +0.74R and +0.35R for the rest |
| `--breakeven-r 2` | Trend exits give back gains | Median give-back from the best price was 1.3R (US) and 1.5R (India). 9 + 9 trades reached +2R and still exited below +1R |
| `--max-positions 13` (US only) | Money sits idle in the US | 76% invested on average. With 1% risk and stops about 13% away, 10 slots can hold at most about 77% of equity. 5,916 signals were turned away because every slot was full |

The 30-week cut-off was read off these same runs. So the test tries three values, and only a result that holds
across all three counts.

## Runs

All runs are in the optimise stage (2013-01-01 → 2021-12-31), with the strategy's own `backtest_args`.

- **Baseline:** 2.12 with G10 off, in each market. It should trade like 2.11. Because the data has had split
  repairs since then, every variant is compared with this baseline, not with #2263 or #2264.
- **G10:** `--const MAX_STAGE2_WEEKS=26`, `=39` and `=52`, in each market.
- **Breakeven:** `--bt '--breakeven-r 2'`, in each market.
- **More US slots:** `--bt '--max-positions 13'`, US only.

## Pass criteria (each market judged on its own, against its own 2.12 baseline)

**G10 (MAX_STAGE2_WEEKS).** One value passes if all four of these hold:

- average R rises by at least 0.15;
- Sharpe rises by at least 0.05;
- maximum drawdown is no more than 2.0 points deeper;
- the trade count is at least 75% of the baseline's.

In the US, the average R of entries made in 2018–2021 must also rise.

The rule passes only if all three values lift average R above the baseline. If only one value passes, the result
is curve-fitting and the rule fails. When it passes, the value carried forward is the middle one of those that
passed, not the best one.

**Breakeven at +2R.** It passes if all three of these hold:

- the profit factor rises;
- total R rises;
- CAGR is not lower.

**US, 13 positions.** It passes if all three of these hold:

- excess CAGR rises by at least 1.5 points;
- Sharpe falls by no more than 0.03;
- maximum drawdown stays at least 5.0 points shallower than SPY's over the same window.

## What follows

- **Results:** each one is reported as it comes in, including the ones that fail.
- **If anything passes:** the passing changes run together in one combined optimise run. If the combination still
  passes, it ships as a new version with those defaults on.
- **No verify run:** the 2022 onwards window is spent. 2.11's verify run already showed those years
  (research/stage-analysis-verify-plan.md). A version that passes here earns paper trading, which is forward data,
  not a second look at the same years.
