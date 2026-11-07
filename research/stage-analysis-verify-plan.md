# Stage analysis 2.11 — the out-of-sample test and its pass criteria

Written 2026-11-06, before any 2.11 run exists. Nothing below may change after a verify run is seen.

## What is tested

Version 2.11 with its shipped defaults: every switch off, `--rank-by setup_momentum`, the weekly_ma exit. It is
tested in both markets: US against SPY, India against ^CRSLDX, each market's own benchmark in the backtest.

| Order | Stage | Window | Purpose |
|---|---|---|---|
| 1 | optimise | 2013-01-01 → 2021-12-31 | A sanity check that 2.11 runs and trades. It is not a verdict. A bug found here becomes a new version, and that version is what gets verified |
| 2 | verify | 2022-01-01 → today | **The test.** One run per market, once |
| 3 | full | 2013-01-01 → today | Context for a reader. It is never a verdict, and it is queued only after the verify run, because it contains the verify years |

## The claim being tested

Weinstein's method claims two things: it rides the advance (Stage 2) and it stays out of the decline (Stage 4).
It does not claim to beat the index on return. So the test asks for return per unit of risk at least as good as
the index, with clearly shallower losses. The verify window includes 2022, a bear market in the US, which is the
kind of year the method was built for.

## Pass criteria

All figures are on the strategy's daily equity and the benchmark's daily closes over the same dates.

**A market passes only if all three hold:**

1. **Drawdown:** the strategy's maximum drawdown is at least 5.0 points shallower than the benchmark's. For
   example, −15% against the index's −22%.
2. **Risk-adjusted return:** the Sharpe ratio (daily returns, annualised, no risk-free rate) is not lower than
   the benchmark's.
3. **Enough trades:** at least 30 closed trades. With fewer, the result is reported as *inconclusive*, neither a
   pass nor a fail.

The CAGR, excess return, profit factor, average R and share of time invested are all reported, but none of them
decides the result.

Each market is judged on its own. A pass in one market does not carry over to the other.

## What follows from the result

- **Pass:** the strategy has earned paper trading in that market. That is forward data, the only clean test
  left. It has not earned a live allocation.
- **Fail:** the result is reported as it is, and the strategy's `status` says so. Any later change is a new
  version, judged on new forward data, because these years are no longer out of sample.
- **Inconclusive:** reported as such. A second verify run of 2.11 would be a repeat (`--again`) and would be
  labelled one.

## Result (added 2026-11-07, after the verify runs; nothing above was changed)

Verify window 2022-01-03 → 2026-11-06, v2.11-66dbb1bc, judged on the criteria above.

| Market | CAGR (index) | Max drawdown (index) | Sharpe (index) | Closed trades | 1 Drawdown | 2 Sharpe | 3 Trades | Verdict |
|---|---|---|---|---|---|---|---|---|
| US vs SPY | 2.84% (9.32%) | −13.0% (−25.4%) | 0.32 (0.60) | 78 | yes (+12.4) | no (−0.28) | yes | **FAIL** |
| India vs ^CRSLDX | 5.87% (9.15%) | −18.8% (−18.8%) | 0.56 (0.69) | 73 | no (+0.0) | no (−0.13) | yes | **FAIL** |

Both markets fail. The strategy has not earned paper trading under 2.11; the result is in its `status`.
