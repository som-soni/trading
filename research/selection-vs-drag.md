# Selection vs cash drag: what "lost to the index" actually meant

*2026-10-17. Measured, not argued: every table here comes from stored equity curves and the
universe in the database. Method is in `backtesting/metrics.deployment_stats`.*

---

## 1. The headline number was answering two questions at once

Every strategy is reported as "CAGR vs index". The index is 100% invested every day; the
strategies are not. So the gap mixes **a bad signal** with **idle capital**, and those need
opposite fixes — one says trade differently, the other says deploy more.

Two numbers now split it:

- **selection** — the index held at the strategy's *own* daily invested fraction. Beat it and the
  stock picking has edge at an equal risk budget, whatever the headline says.
- **drag** — the strategy with its idle cash earning the index instead of nothing. The gap to it is
  what sitting in cash cost.

Checked at both extremes: an index clone at full investment scores selection −0.00 and drag
+0.00; an all-cash strategy scores matched +0.00 and a drag equal to the whole index return.

## 2. It inverts the ranking

| strategy | market | CAGR | index | headline | invested | **selection** | drag |
|---|---|---:|---:|---:|---:|---:|---:|
| minervini | india | 1.49% | 10.17% | −8.68 | 17.8% | **+0.86** | +9.61 |
| chart_pattern | us | −0.28% | 19.76% | −20.04 | 2.0% | +0.04 | +20.09 |
| trend_pullback | india | 2.30% | 11.67% | −9.37 | 34.3% | −0.38 | +8.94 |
| minervini | us | −0.29% | 12.11% | −12.40 | 37.9% | −1.38 | +10.89 |
| donchian | india | 7.68% | 11.64% | −3.96 | 93.9% | **−2.26** | +1.68 |
| chart_pattern | india | 3.61% | 11.74% | −8.13 | 59.5% | −2.84 | +5.17 |
| breakout | us | 2.15% | 12.93% | −10.78 | 65.3% | −3.38 | +7.25 |
| trend_pullback | us | 1.75% | 12.91% | −11.16 | 77.5% | −4.06 | +6.88 |
| donchian | us | 6.53% | 12.93% | −6.39 | 96.6% | −4.47 | +2.01 |

**Donchian looked best on the headline and is among the worst at picking.** Its −3.96 came from
being 94% invested, not from choosing well: it is close to a worse-performing index tracker.
**Minervini India looked worst and is the only positive selection number** — its entire shortfall
is idle capital.

The practical consequence: **deploying more capital only helps where selection is positive.** For
seven of these nine, more exposure means losing faster. The previous recommendation to build on
donchian because its headline was least bad was wrong, and this is the measurement that shows it.

Caveat on the one positive: +0.86 over 474 trades, in a book whose top 10 trades are 221% of net
P&L, is not distinguishable from noise. The honest reading is **no strategy here has demonstrated
selection skill**, rather than "minervini India has a small edge".

## 3. Survivorship: real, but far smaller than a terminated-series count suggests

*Corrected 2026-10-17. The first version of this section said the universe contained no failures
at all. That was wrong, and the error was reading one measurement as if it answered a different
question.*

No price series ends early:

| market | symbols | history starts ≤2010-06-30 | history STOPS >180d before the end |
|---|---:|---:|---:|
| India | 3,465 | 946 | 0 (0.0%) |
| US | 5,438 | 2,428 | 8 (0.1%) |

But "no series ends" is not "nothing failed". **Indian stocks that collapse mostly keep trading
rather than delisting**, so the tape carries the whole collapse:

| of the pre-2012 cohort (1,046 names) | down ≥50% | ≥75% | ≥90% | ≥95% | ≥99% |
|---|---:|---:|---:|---:|---:|
| share, peak to last close | 47.4% | 23.8% | **12.0%** | 6.8% | **2.0%** |

RCOM (₹930 → ₹0.85), EDUCOMP (₹1,106 → ₹0.95), FEL (₹773 → ₹0.35) and SKIL (₹2,010 → ₹1.06) are
all present, with every bar of the way down. A ranking strategy would have dropped them long
before the bottom, which is exactly the point: **the drawdown that would have hurt a momentum book
is in the data.**

What is genuinely missing is narrower:

- **Fully delisted companies.** Yahoo deletes the ticker, so the history is unrecoverable from
  this source — DHFL, SINTEX, PUNJLLOYD and VIDEOIND all return nothing, while JETAIRWAYS, RCOM,
  EDUCOMP and ABAN still return full history.
- **Acquired companies**, which usually exit at a premium. Their absence biases measured returns
  **downward**, not upward — the opposite direction to the delisting gap.

So the two missing cohorts push in opposite directions, and the larger, more damaging one
(collapse) is already represented. The honest statement is that survivorship inflates these
results by an unknown but **probably modest** amount, not that the tape is a fantasy.

## 4. The momentum baseline, re-tested against something that does include failures

The baseline's advertised edge is measured against the Nifty 500. But its edge concentrates in
small caps (`research/momentum-trend-research.md` §liquidity sweep), so the right control is a
small-cap index — which drops and replaces its constituents, so it carries the failures the
stock-picking universe cannot.

| series | CAGR | maxDD | Sharpe | <2019 | ≥2019 |
|---|---:|---:|---:|---:|---:|
| Nifty 500 (the usual benchmark) | 10.17% | −38.3% | 0.69 | 8.60% | 11.97% |
| Nifty Midcap | 11.84% | −42.0% | 0.73 | 11.60% | 12.15% |
| **Nifty Smallcap 250** | **11.99%** | **−60.8%** | 0.71 | 8.07% | 16.65% |
| momentum top-50, ₹10cr, 25bps | 18.04% | −44.4% | 0.87 | 11.78% | 25.72% |
| momentum top-50, ₹10cr, 50bps | 15.65% | −46.6% | 0.78 | 9.71% | 22.93% |

So the +5.48 "excess" at 50bps decomposes roughly as:

- **~1.8 points is small-cap segment beta** — available from an index fund, no skill involved
- **~3.7 points is momentum on top of that**, and that 3.7 is the part measured on a tape with
  zero failures, against an index that has them

Published delisting-bias estimates for small-cap portfolios are of the same order as that 3.7.
But see §3 as corrected: the collapses are in the tape, and only outright delistings are missing,
so the realistic discount is smaller than a full delisting-bias adjustment. **The defensible alpha
is most of +3.7, not a coin flip between that and zero** — which is a materially different
conclusion from the one this document first drew.

Two things do survive the control, because survivorship affects the level more than the shape:

- **drawdown is better than the segment's**: −46.6% against the smallcap index's −60.8%
- **Sharpe is better**: 0.78 against 0.71

And one thing does not: the edge over small caps is **+1.64 before 2019 and +6.28 after**. It is
concentrated in a single regime — the post-2020 Indian small-cap bull — which is the same window
that makes it look robust out of sample.

## 4b. Walk-forward: was picking 1 of 18 a procedure, or luck?

*2026-10-17.* The 2019 split is a single, chosen cut. Two stronger tests.

**Is the excess stable?** Rolling 36-month excess over the Smallcap 250, quarterly:

| windows | median | mean | worst | best | positive |
|---:|---:|---:|---:|---:|---:|
| 55 | +3.71 | +4.51 | **−11.72** | +18.87 | **42 (76%)** |

Persistent but uneven. You can spend three years behind the segment.

**Was the choice repeatable?** At each year-end, pick the variant with the best *trailing* excess
using only data available then, hold it one year, chain forward:

| | CAGR excess |
|---|---:|
| walk-forward (trailing data only) | **+3.75** |
| the variant chosen with full hindsight | +4.36 |

**It survives.** The procedure keeps 86% of the hindsight result, so the selection-effect discount
is about 0.6 points, not the whole edge. Five of thirteen years underperform, the worst by 17.7.

A detail worth more than the headline: the walk-forward **always picks top-20**, and alternates
only between `vol_scaled`/`momentum` and `equal`/`inverse_vol`. Concentration is the robust
parameter; the weighting is close to noise. A future version should not over-specify weighting.

Note on arithmetic: the mean of annual excesses was +6.74, which looks better than the hindsight
pick and is not comparable to it — mean annual arithmetic excess overstates compounded excess when
returns are volatile. Compounding both gives the +3.75 above.

## 5. What this changes

1. **Stop ranking strategies by headline excess.** It ranked the worst picker first.
2. **Do not "fix deployment" on a negative-selection strategy.** It makes it worse.
3. **Benchmark small-cap strategies against a small-cap index**, not the broad one, or segment beta
   is counted as skill.
4. **Cost assumptions decide this edge**: 25bps → +7.87 over Nifty 500, 100bps → +0.79. Round-trip
   cost on Indian small caps with monthly rebalancing is the single most load-bearing assumption in
   the whole result, and it is currently a flat constant.

## 6. What would settle it

Point-in-time constituent lists plus prices for delisted names. The second half is the hard part:
Yahoo deletes delisted tickers outright, so the cheap path is closed and the history would have to
come from NSE's own archives or a paid vendor.

That project is worth less than this document first implied. The failures that would have hurt a
momentum book — the 12% of the cohort down 90%+ — are already in the tape; what is missing is the
final removal of names a ranking strategy had long since sold, plus acquisitions that bias the
other way. Treat the momentum result as "a small edge with better drawdown than small-cap beta,
inflated by an unknown but probably modest amount", and spend the effort on walk-forward
robustness and cost realism before on reconstructing delisted history.

## 7. The whole shelf, decomposed

All ten registered strategies now carry a measured run — 73 runs in total, 59 per-symbol and 14 portfolio. Below, every one of them in the two windows where
several share a start date, with the headline split into SELECTION (the strategy against the
index held at the strategy's *own* exposure — the only column that says whether the signal picks)
and DRAG (what idle cash cost). Each strategy is measured against the index it declares, so
`momentum_vol_scaled` is scored against small caps and the rest against the broad index.

### 2013-01-01 — the per-symbol swing strategies

| strategy | market | CAGR | excess | invested | **SELECTION** | drag |
|---|---|---|---|---|---|---|
| donchian | india | 7.7% | -4.0 | 94% | **-2.26** | -1.7 |
| donchian | us | 6.5% | -6.3 | 97% | **-4.48** | -2.0 |
| chart_pattern | india | 5.7% | -5.9 | 79% | **-2.17** | -3.7 |
| breakout | us | 2.1% | -10.7 | 65% | **-3.38** | -7.2 |
| trend_pullback | india | 2.3% | -9.4 | 34% | **-0.38** | -8.9 |
| trend_pullback | us | 1.8% | -11.1 | 77% | **-4.06** | -6.9 |

**Eight measured runs, four strategies, two markets, not one positive selection number.**
(The table shows one row per strategy-market; `chart_pattern` india and `trend_pullback` us each
have a second variant, both also negative; `minervini`'s 2013 run stored no equity curve.)
This is the central finding of the whole exercise: the per-symbol swing machinery — entry trigger, stop,
target, exit — has never once picked better than holding the index at the same risk budget.
The two closest to flat (`trend_pullback` india at -0.38, and `minervini`'s best 2010 variant
at +0.87) get there by barely trading.

### 2020-01-01 — the four portfolio strategies, plus rs_leaders

| strategy | market | CAGR | bench | excess | invested | **SELECTION** | drag |
|---|---|---|---|---|---|---|---|
| dual_momentum | india | 23.9% | 12.6% | +11.3 | 100% | **+11.30** | 0.0 |
| dual_momentum | us | 19.8% | 13.4% | +6.4 | 100% | **+6.36** | 0.0 |
| momentum_baseline | india | 23.6% | 12.6% | +11.0 | 100% | **+10.98** | 0.0 |
| momentum_baseline | us | **-13.5%** | 13.4% | -26.9 | 100% | **-26.88** | 0.0 |
| momentum_vol_scaled | india | 25.7% | 20.8% | +4.9 | 100% | **+4.90** | 0.0 |
| momentum_vol_scaled | us | 12.2% | 7.5% | +4.8 | 100% | **+4.75** | 0.0 |
| sector_rotation | india | 15.9% | 12.6% | +3.3 | 100% | **+3.28** | 0.0 |
| sector_rotation | us | 10.7% | 13.4% | -2.7 | 100% | **-2.68** | 0.0 |
| rs_leaders | india | 3.8% | 12.6% | -8.8 | 17% | **+1.40** | -10.4 |
| rs_leaders | us | 3.8% | 13.4% | -9.7 | 19% | **+0.27** | -10.0 |

A fully-invested strategy has no drag, so for those nine rows selection *is* the headline — which
is the point: the decomposition only does work where exposure is partial, and the partial-exposure
row is the one that loses 10 CAGR points to cash while picking slightly above zero.

### The same strategies over 2010-01-01, where one exists

| strategy | india | us |
|---|---|---|
| dual_momentum | +3.72 | **-1.41** |
| sector_rotation | +2.95 | **-2.81** |
| momentum_vol_scaled | +5.57 | **-3.04** |
| minervini (best of 14 variants) | +0.87 | +0.46 |

**The 2020 window flatters everything by roughly a factor of three.** `dual_momentum` india goes
from +3.72 over sixteen years to +11.30 over six; US goes from *negative* to +6.36. Any decision
made on 2020-onward numbers is a decision made on one bull market. The 2010 column is the one to
read, and in it **nothing has demonstrated US edge over a full cycle.**

### The one measured validation of a fix

`momentum_baseline` US 2020 is the outlier in the table: -13.5% CAGR, -82.3% max drawdown, 57%
annualised volatility. Its best and worst trades say why — NVAX, RIOT, FCEL, MARA, ABTS, AMTX.
An unfiltered top-10 by 252-day return, with no liquidity floor and equal weights, bought the
2021 micro-cap/crypto/SPAC tail at the top.

`momentum_vol_scaled` was built to fix exactly that (top-20 instead of top-10, a $20m turnover
floor, inverse-volatility weights, 50bps costs). Same window, same market, same ranking idea:

| | momentum_baseline | momentum_vol_scaled |
|---|---|---|
| CAGR | -13.5% | **+12.2%** |
| max drawdown | -82.3% | -47.7% |
| ann. volatility | 56.8% | — |

That is a 26-point CAGR swing from three sizing and liquidity constraints, with the alpha source
untouched. It is the largest measured effect in this entire document, and it is not a signal
improvement.

## 8. What to build next — and what not to

The Learn module describes ~20 strategies; four portfolio strategies and six per-symbol ones are
now implemented and measured. The table above argues against building the remaining fifteen next,
because strategy *count* is not what is binding. Three things are, in order of measured size:

1. **Sizing and liquidity constraints, not signals** (26 CAGR points, measured above). No new
   strategy in the Learn list has a plausible claim to that magnitude.
2. **Cash drag** (10 CAGR points on every partial-exposure strategy). The fix is structural: run
   the good gate as a fully-invested cross-sectional portfolio rather than as a per-trade swing
   strategy. `rs_leaders` has the only positive selection among per-symbol strategies in both
   markets (+1.40 / +0.27); as a monthly top-N through `rotation.simulate` it would keep that
   and lose the -10 by construction. The gate already exists, so this is a cheap test.
3. **Window dependence** (3× on dual_momentum). Before trusting the one strategy that works,
   walk it forward the way §4b did for the momentum baseline.

The honest summary of the shelf: **one idea works** (cross-sectional momentum, fully invested,
with liquidity and volatility constraints), **it works in India and is unproven in the US over a
full cycle**, and **the per-symbol swing family has shown positive selection in 11 of 59 runs, never above
+2.24, and never once on the eight-run 2013 cohort.**
