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

## 9. §8's recommendation, tested — and it was wrong

§8 said the cheap next test was to run `rs_leaders`' gate as a fully invested portfolio, because it
had the only positive selection among the per-symbol strategies in both markets (+1.40 India, +0.27
US) and threw away ~10 CAGR points sitting in cash. `backtesting/rs_rotation.py` does exactly that:
hold the top-N leaders when the market is in a confirmed recovery, hold the INDEX otherwise, never
cash. Fully invested by construction, so the headline excess *is* the selection number.

**It does not survive.** India from 2010, against the Nifty 500:

| rank | top N | gate ON | gate OFF (control) |
|---|---|---|---|
| rs_range | 20 | **-2.99** | +1.83 |
| momentum | 10 | **-3.72** | +9.57 |
| momentum | 20 | **-4.00** | +7.85 |
| vol_scaled | 10 | **-3.67** | +10.71 |
| vol_scaled | 20 | **-3.87** | +8.06 |

The +1.40 was an artefact of measuring a strategy that is barely invested, not a signal worth
deploying. Every converted variant loses by 3-4 points while fully invested.

### The control inverts between markets, which kills the simpler story

The obvious reading of the India column is "the recovery gate costs 5-14 CAGR points". The US says
otherwise:

| rank | top N | India gate ON | India gate OFF | US gate ON | US gate OFF |
|---|---|---|---|---|---|
| rs_range | 20 | -2.99 | +1.83 | -1.19 | -11.24 |
| momentum | 10 | -3.72 | +9.57 | **+1.71** | -21.41 |
| vol_scaled | 20 | -3.87 | +8.06 | **+0.66** | -6.23 |

**The gate's sign flips with the market.** It is not a signal at all — it is a lever on *how much
momentum you hold*, and its value follows whether that market pays a momentum premium. In India it
defaults you out of a book that works, which is expensive; in the US it defaults you into the index
and away from a book that does not, which helps. The US gate-ON runs all report a max drawdown of
-34.1%, which is SPY's: they are a mostly-index portfolio with a small excursion, and the +1.71 is
that excursion, not stock selection.

So §8's point 2 — "run the good gate fully invested and keep the selection" — was wrong twice. The
selection was not real, and the gate it was attributed to does not have a sign of its own.

### What the control run is actually worth

The gate-OFF column is a second, independent measurement of cross-sectional momentum, through a
different accounting engine (`rotation.simulate`, equal-weighted) than the one `momentum_vol_scaled`
uses (`portfolio_sim`, inverse-vol). India, vol_scaled, top 20: **18.22% CAGR here against 17.56%
there.** Two independently written engines agreeing to within 0.7 points on the same strategy is
worth more than either number alone — it is the only cross-validation in this document.

### A defect this found

The first version of the gate-OFF runs reported max drawdowns of **-100.5% with a negative Sharpe
on a positive CAGR**, which is impossible and is how the bug got caught. `rotation.simulate` valued
a holding at ZERO when its price was NaN on the day rather than marking it to its last trade. Both
existing callers happened to hide it by forward-filling at load; a stock cross-section does not,
because `baseline.load_prices` deliberately leaves gaps (ffilling before scoring would fabricate
momentum across them). India's frame carries 56,738 interior NaNs, and on 2010-02-06 every symbol
was NaN at once, so the whole book vanished for a session and equity printed bare cash.

Fixed in the engine rather than in each caller's loader. `dual_momentum` and `sector_rotation` x
{india, us} x {2010, 2020} — all eight reproduce their published CAGR and max drawdown to within
rounding, so no shipped result moves.

## 10. Where the shelf stands after that

Adding index mean reversion (`mean_reversion`, the first non-momentum mechanism) and the rs_leaders
conversion, the ledger now reads:

| mechanism | strategies | verdict |
|---|---|---|
| Cross-sectional momentum, fully invested | 4 | **The only one that compounds.** India yes, US unproven over a full cycle |
| Asset / sector rotation | 2 | India +3.0 to +3.7 from 2010; US negative in both |
| Per-symbol swing (breakout, pullback, base) | 6 | Positive selection in 11 of 59 runs, never above +2.24, never on the 2013 cohort |
| Short-horizon mean reversion on indices | 1 | Negative selection in all 12 runs, both markets, all three measures |
| Event-driven (post-earnings drift) | 1 | US -1.44, as the literature predicts 58 years on. India unreadable (§11) |
| Carry (selling index option spreads) | 1 | Undecidable from stored data: all 24 configurations change sign between 2 and 4 points of assumed slippage per leg, and the bhavcopy has no bid/ask |

Six mechanisms now, and the two newest are informative in different ways. **Post-earnings drift
reproduced a published prediction**: the Learn guide says the drift has mostly gone from large US
stocks since the 2000s, and the US run returns -1.44 selection over 1,548 trades. **Option selling
produced no verdict at all**, which is itself the finding — a short-premium result is a cost
assumption, and the one cost that decides it was never recorded. Both share a shape worth
remembering: drift wins under 30% of the time with large winners, option selling wins 71-77% of the
time with large losers, and neither shape is readable from a win rate.

The carry result has a second lesson that has nothing to do with options. At the guide's own sizing
— 1.5% of capital at maximum loss, one structure at a time — under 1% of the book is at risk on an
average day. Even granting the most favourable cost assumption, +0.97 CAGR points of selection on a
0.6% risk budget cannot compound. **A strategy has to be deployable at size before its edge is worth
measuring**, which is the same point §8 got wrong from the other direction.

Four mechanisms, one that works, and the one that works has a known size (~+3.4 walk-forward, not
the +5.6 headline) and a known weak spot (the US). That is a more useful map than it looks: it says
the remaining Learn strategies are worth building for *coverage of mechanisms not yet tested*, and
not worth building as further variations on breakouts, of which there are already six.

## 11. The fundamentals universe is selected on outcome

Found while measuring post-earnings drift, and it constrains anything built on fundamentals from
here on.

Company filings exist only for symbols the `financials` job has fetched, and that job's list
(`jobs/registry.py`) is:

- the `FINANCIALS_TOP` most liquid tradable stocks **by today's 20-day turnover** — 1,500 US, 500
  India; plus
- **every stock passing the Trend Template in the latest snapshot** — that is, every stock *currently*
  in an uptrend.

Both criteria read today's data. For the live Fundamentals and Quality pages that is exactly right:
they describe the present, and fetching statements for the names that matter now is the point. For a
**backtest** restricted to that set it is lookahead of the worst kind — the universe knows which
stocks went on to trend.

The size of it is measurable. Equal-weight, no selection, same dates as the strategy:

| | eligible universe (buy & hold) | broad index | premium |
|---|---|---|---|
| India, 2022-2026, 387 symbols | **31.49%** | 8.22% | **+23.27** |
| US, 2010-2026, 1,394 symbols | 13.75% | 12.04% | +1.71 |

India's +23 points is larger than any strategy effect in this document, and it is *not stock
selection* — it is the universe. The US slice is a wider share of its tape over a window three and a
half times longer, so its premium is small and its results remain readable.

**What follows from this:**

1. **Judge a fundamentals strategy against a buy-and-hold of its own eligible set**, never against
   the broad index. `backtesting/pead.py`'s `main()` computes and prints that control beside the
   headline, so the comparison cannot be skipped by a future reader.
2. **Treat any Indian fundamentals backtest as a diagnostic, not a result**, until the universe is
   reconstructed point in time.
3. **The fix is a point-in-time fetch list** — the most liquid names *as of each date* — which means
   backfilling filings for names that are no longer liquid or no longer trending. That is the same
   project as point-in-time constituents in §6, and the same reason it has not been done.
4. **Nothing already published moves.** PEAD is the only backtest drawing on this universe; the
   quality tracker and the Fundamentals page are live views of the present, where selecting on the
   present is correct.

## 12. The momentum sweep, re-run — and a rank buffer it never saw

*2026-10-24.* §4b chose `momentum_vol_scaled` from 18 variants on worst half-period excess and
walk-forward tested the choice. Neither step was committed, so neither could be repeated when the
ground moved: v1.1 took ETFs and liquid funds out of the universe (after which the walk-forward
kept 58% of the hindsight pick instead of 86%), and v1.2 added a rank buffer — buy into the top N,
hold until a name ranks outside `hold_rank` — because the stored book was held a median 33 days
and turned over 4.6–5.2× a year on a twelve-month signal. Both steps are now
`backtesting/momentum_sweep.py`, which reproduces the stored India run to the digit (CAGR 19.18%,
max drawdown −50.99%, turnover 4.58×).

Grid: rank (momentum / vol_scaled / residual) × holdings (20 / 50) × weighting (equal /
inverse_vol) × buffer (off / 1.5× holdings) = 24 variants. Vol targeting was left out; §4b already
rejected it, and each extra dimension cheapens a best-of-N result. Costs 50bps, the strategy's own
turnover floors, excess over its segment index (Smallcap 250 / IWM), compounded.

**The buffer helps almost everywhere.** Each variant against its unbuffered twin:

| window | excess improved | worst half improved |
|---|---|---|
| India from 2010 | **12 of 12** | **12 of 12** |
| India from 2020 | **12 of 12** | — |
| US from 2010 | **11 of 12** (one flat) | 11 of 12 |
| US from 2020 | 8 of 12 | — |

That is the shape that matters, not the size of the best cell: a best-of-24 winner is not a
finding, a change that improves 43 of 48 like-for-like pairs is. Turnover falls about a quarter
(4.58× → 3.43× on the shipped variant). The weak cell is the US from 2020, where it lowered both
top-20 vol_scaled variants (4.87 → 3.85, 5.53 → 4.46) — a single bull-market window, and the one
place it hurt.

**India — the shipped choice survives, buffered.** On the original criterion, worst half:

| variant | excess | before 2019 | after | worst half | max DD | turnover | 36m worst | 36m positive |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **vol_scaled/top20/inverse_vol/hold30** | +8.38 | +7.98 | +8.95 | **+7.98** | −52.1% | 3.43× | **−6.05** | 88% |
| residual/top20/inverse_vol/hold30 | +9.36 | +7.97 | +11.13 | +7.97 | −55.2% | 3.54× | −4.49 | 93% |
| vol_scaled/top20/inverse_vol (shipped) | +7.51 | +7.88 | +7.12 | +7.12 | −51.0% | 4.58× | −11.75 | 82% |

The shipped rank, holdings and weighting still win on worst half once buffered; residual ties it on
worst half (+7.97) with more full-window excess and a 3-point deeper drawdown. The buffer's
largest effect is the bad stretch: the worst rolling three years improves from −11.75 to −6.05.
Drawdown is about a point worse. **Walk-forward 2014–2026: +7.06 against the hindsight pick's
+8.92 — it keeps 79%**, back up from v1.1's 58%. It picks top-20 in 9 of 13 years; §4b's finding
that concentration is the robust parameter holds.

**US — no variant works over the cycle.** All 24 have negative excess over IWM from 2010; the best
is −0.20, the walk-forward −2.05. The buffer narrows the loss in 11 of 12 pairs but cannot make
one positive, which confirms §10's "a market difference, not a variant one". One shape is worth
noting: the US prefers **50** names to 20 in every pairing, the opposite of India — what a market
with ~40% less momentum spread should do, since there is less in the top tail to concentrate on.
From 2020 several US variants look healthy (+7.82 at best), but the walk-forward over those years
keeps 10% of the hindsight result: in that window, choosing was luck.

**What follows.** Turning the buffer on at 30 for `momentum_vol_scaled` is supported in both
markets and both windows, by the like-for-like count rather than by a winner. It is still
in-sample on the data that measured it, and only 1.5× was swept; the queued runs at 30 and 40
decide the width. The US arm should not be deployed under any variant tested here.
