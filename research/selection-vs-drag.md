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
