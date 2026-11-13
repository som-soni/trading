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

## Result (added 2026-11-13)

Every variant fails. Optimise stage, 2013-01-01 → 2021-12-31. The 2.12 baselines reproduced 2.11's figures
(#2263, #2264) exactly, so the data repairs did not move them.

| Market | Run | Variant | CAGR % | Max DD % | Sharpe | Trades | Avg R | Total R | PF | Avg R 2018–21 | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| US | #4281 | baseline (G10 off) | 9.27 | −21.2 | 0.82 | 157 | +0.54 | 79.7 | 2.06 | −0.14 | — |
| US | #4313 | G10 = 26 | 10.42 | −19.2 | 0.96 | 142 | +0.63 | 84.4 | 2.40 | −0.01 | FAIL (avg R +0.09, bar +0.15) |
| US | #4332 | G10 = 39 | 9.12 | −20.2 | 0.84 | 145 | +0.59 | 80.8 | 2.22 | −0.08 | FAIL (avg R, Sharpe) |
| US | #4371 | G10 = 52 | 9.18 | −20.2 | 0.84 | 153 | +0.56 | 80.0 | 2.21 | −0.08 | FAIL (avg R, Sharpe) |
| US | #4375 | breakeven at +2R | 9.21 | −21.5 | 0.82 | 157 | +0.54 | 79.2 | 2.05 | −0.14 | FAIL (PF, total R, CAGR all lower) |
| US | #4377 | 13 positions | 9.07 | −24.2 | 0.74 | 210 | +0.39 | 77.5 | 1.79 | −0.17 | FAIL (excess CAGR lower, Sharpe −0.08) |
| India | #4280 | baseline (G10 off) | 3.86 | −18.5 | 0.51 | 95 | +0.26 | 22.7 | 1.41 | −0.25 | — |
| India | #4372 | G10 = 26 | 4.24 | −16.1 | 0.56 | 85 | +0.29 | 22.9 | 1.44 | −0.27 | FAIL (avg R +0.03) |
| India | #4373 | G10 = 39 | 4.29 | −17.6 | 0.56 | 87 | +0.28 | 22.8 | 1.43 | −0.28 | FAIL (avg R +0.02) |
| India | #4374 | G10 = 52 | 3.90 | −18.5 | 0.52 | 90 | +0.26 | 21.2 | 1.38 | −0.30 | FAIL (avg R flat, Sharpe) |
| India | #4376 | breakeven at +2R | 3.30 | −21.5 | 0.45 | 95 | +0.20 | 18.0 | 1.32 | −0.36 | FAIL (PF, total R, CAGR all lower) |

Benchmarks over the window: SPY max drawdown −34.1%, ^CRSLDX −38.3%.

- **G10 fails as a rule.** No value passed, and in India the 52-week value did not lift average R at all. The US
  26-week run improved every figure, but by less than the bar written before the run, and the cut-off was read
  off these same years. G10 stays off.
- **Breakeven was the wrong tool for the finding.** The give-back it was meant to fix was trades that reached +2R
  and exited between 0 and +1R. A stop at entry only acts once price falls back to entry, so it cannot keep those
  gains; it only cut trades that dipped to entry and then recovered.
- **More US slots bought weaker trades.** The 53 extra trades dragged average R from +0.54 to +0.39 and deepened the
  drawdown. The idle money is not a missed edge.
- **What follows:** nothing passed, so there is no combined run and no new default. The strategy stays at 2.12 with
  G10 off, trading as 2.11, with no demonstrated edge in either window.
