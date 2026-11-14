# Stage 4 shorts — the final test (v1.5) and a 2000–2012 presample proposal

*2026-11-14. Every figure below is from the **optimise stage (2013-01-01 → 2021-12-31)**: in-sample. Verify was not opened.*

## In short

- **Verdict: fails both pass criteria in both markets. Retirement recommended.**
- Weinstein's entry trades too rarely to hedge anything. With the market in Stage 4 and the group weak, it made 17 shorts in the US and 2 in India over nine years, and none were open in the March 2020 crash.
- The v1.4 rally entry (B), re-run under the corrected measurement, also fails. An index-futures short at the same beta gives the same or better drawdown relief, with no stock-picking risk.
- The results hold at double costs.
- Before 2013, prices are deep enough in the US and thin in India. A presample stage is possible, but three data gaps come first (section 4).

## 1. What changed for this test

| Change | Detail |
|---|---|
| Measurement | Interest at the cash rate is credited on equity. There are two comparators, both earning the cash rate: an index short at the strategy's own beta (5 bps a month roll), and a cash sleeve. |
| Long book | US: **quality_momentum** (v1.7). Its filings-only variant is the one US long book that passed verify. India: **momentum_vol_scaled** (v1.10). |
| India calendar fix | Signals on sessions missing from the benchmark calendar (e.g. 18 on the 2020-11-14 Muhurat session) now roll to the previous benchmark session instead of being dropped. |
| Entry (v1.5) | **C** is the weekly close below a Stage 3 top's low. **P** is the first pullback to that broken level within 8 weeks. Both need the stock's industry group ranked at most 30 out of 99, and the benchmark itself in Stage 4. |
| Exits | The stop is set above the last swing high and lowered to each lower swing high. The position also closes on a weekly close above the 30-week line. |
| India lots | A proxy check: a short counts only if one futures lot (a contract worth at least ₹5 lakh) fits a ₹20 lakh account. |

The pass criteria were fixed before any run:

1. Beat the beta-matched index short on Sharpe **and** on maximum drawdown, in both markets.
2. A 20% sleeve beside the long book must cut the combined drawdown by at least 2 points against a 20% cash sleeve, without lowering Sharpe.

## 2. Results (optimise stage, ×1 costs)

| Run | Trades | Avg R | CAGR (incl. interest) | Max DD | Excess Sharpe | Index short: Sharpe / DD | C1 | Sleeve DD gain vs cash | Sleeve Sharpe vs cash | C2 |
|---|---|---|---|---|---|---|---|---|---|---|
| US, C+P (v1.5) | 17 | −0.78 | +0.04% | −3.8% | −0.40 | −0.91 / −1.7% | ✗ (DD) | 0.0 pt | 0.571 vs 0.574 | ✗ |
| US, B (rally) | 209 | −0.19 | −1.18% | −19.1% | −0.30 | −0.91 / −8.5% | ✗ (DD) | +0.3 pt | 0.567 vs 0.574 | ✗ |
| India, C+P (v1.5) | 2 | −1.18 | +6.94% | −0.4% | −0.68 | +0.82 / 0.0% | ✗ | 0.0 pt | 0.820 vs 0.822 | ✗ |
| India, B (rally) | 253 | −0.37 | +3.13% | −14.6% | −0.95 | −0.89 / −2.3% | ✗ | −0.1 pt | 0.787 vs 0.822 | ✗ |

At ×2 costs nothing changes sign. US B's sleeve gain falls to +0.2 points; India B's falls to −0.5 points with drawdown −17.2%.

How to read the comparators:

- The US index short's Sharpe is very negative because shorting the index lost money through 2013–2021.
- The strategy beats it on Sharpe only by being out of the market most of the time. Its drawdown is still deeper.
- In India the C+P book is cash with two losing trades. Its 6.9% is the cash rate.

```chart
title: 20% sleeve beside the long book — combined max drawdown (optimise 2013–2021, ×1 costs)
labels: US C+P | US B | India C+P | India B
series: Stage 4 short sleeve | 34.75 | 34.43 | 40.25 | 40.39
series: Cash sleeve | 34.75 | 34.75 | 40.25 | 40.25
series: Index short sleeve | 34.67 | 34.40 | 40.25 | 39.72
unit: max drawdown, % (lower is better)
caption: From each run's sleeve_blend.csv. Long book alone: US −42.7% (quality_momentum), India −50.5% (momentum_vol_scaled). The pass bar was 2 points below the cash sleeve.
```

### Why it fails

- **The market gate confirms after the fall.** The benchmark's weekly Stage 4 covered 6.4% of US sessions in 2013–2021. Those were 2015-09-04 → 11-05, 2019-01-04 → 02-28 and 2020-03-13 → 06-11, each starting after most of the decline. India's 20.9% is longer but also late (2020: 13 March → 15 October).
- **A Stage 3 top must break inside that window.** Stocks that topped earlier are already in Stage 4 when the market confirms, so C and P find almost nothing: 21 US candidate signals in nine years.
- **Loosening the entry (B) brings back the v1.4 problem.** Many trades, a negative average R, and a sleeve that does no better than holding cash.

## 3. Recommendation

**Retire stage4_shorts.** I did not set the `retired` flag: that is the owner's decision.

The hedge question is better answered by an index-futures short or puts sized to the long book. In every blend here that already matched or beat the stock-short sleeve on drawdown, with no stock-selection risk. If a hedge sleeve is wanted, build it as its own strategy: an index short driven by a market-regime rule, judged on the same two criteria.

## 4. Proposal: a 2000–2012 presample stage

Stored prices go back before 2013, so the older bears (2000–02, 2008–09, 2011) could test strategies outside both the optimise and verify windows.

### What the data allows

| | US | India |
|---|---|---|
| Benchmark | SPY from 1993 | ^CRSLDX from 2005-09-26; Smallcap 250 from 2005-04-01; NIFTY from 2007-09-17 |
| Liquid names (≥ market turnover floor) | 891 (2000), 1,519 (2008), 1,680 (2012) — vs 1,839 in 2013 | 14 (2000), 259 (2005), 386 (2007), 294 (2008), 297 (2012) |
| Industry-group ranks | from 2010 | from 2010 |
| Quarterly filings | from 2009-05 | from 2018-06 |
| Cash rate | ^IRX | flat 6.5% before April 2006 |
| Usable window | **2000-01-01 → 2012-12-31** | **2006-07 → 2012-12-31** (benchmark start plus about 34 weeks of stage warm-up) |

### How to add it without breaking the stage rules

1. Add a `presample` stage to `backtesting/windows.py` (2000-01-01 → 2012-12-31, with India's start clamped to its first usable date). `marketdata/asof.py` and `paths.run_dir` already enforce and tag any stage's bounds.
2. Treat it as a second hold-out, not a tuning window. Allow one run per version, recorded in `verify_runs` (or a sibling table), with `--again` for a knowing repeat. Fix the pass criteria before the run, exactly as for verify.
3. Never tune on it. A rule changed after reading a presample result is a new version.
4. Extend `tests.test_backtest_stages` so every registered strategy is checked to stay inside the presample bounds, and add the row to the stage table in CLAUDE.md.
5. A combined verdict would need both hold-outs (presample and verify) to pass the criteria fixed beforehand. Optimise stays the only place to tune.

### Gaps to close first

- **Survivorship.** The universe is today's listings plus what was stored. Dot-com and 2008 failures are mostly missing. That flatters long books and works against shorts, so a short tested there would be judged against a market without its best shorts. Fix: a point-in-time delisted universe, or label every presample result as survivor-biased.
- **Group ranks start in 2010.** Any group gate, this strategy's or the peer-group screens', refuses everything before 2010. Backfill `group_history` from stored prices (it is computed from prices, so this is possible).
- **Long books cannot all run there.** quality_momentum needs filings, which in the US start in 2009, so the US hedge comparison would have to use momentum_baseline or a price-only book. India's momentum_vol_scaled can run from about 2006.
- **India depth.** About 300 liquid names and a flat assumed cash rate before 2006. Treat India presample results as indicative only.

### Decision for the owner

1. Add the `presample` stage at all?
2. If added, does a presample result count as a verdict (a second hold-out), or only as context like `full`?

For stage4_shorts itself, the presample would be a test of a strategy that has already failed. I would not reopen it there unless the stage is added for every strategy.
