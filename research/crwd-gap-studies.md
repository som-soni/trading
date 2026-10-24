# Three gaps CRWD suggested, measured on every liquid stock

*Stage: **optimise**, 2013-01-01 → 2021-12-31. These studies exist to inform rule changes, so they ran
inside the same data boundary as an optimise backtest and never saw 2022 onward. Reproduce with
`PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.gap_studies --market us` (and `india`);
raw output in `reports/<market>/_research/gap_studies.json`.*

## Why

CRWD gained about 120% in 2026 and no strategy here traded it in time. Tracing it bar by bar found
three rules that *might* be costing trades across the universe, not just in one stock:

1. **Trend lag.** Every trend gate (close above the 200-day, 50 above 200, the Trend Template's
   50 > 150 > 200 stack) repairs slowly after a fall, so a V-shaped recovery is invisible during its
   strongest phase. CRWD's +65% May happened while every gate was still shut.
2. **Stop caps.** breakout and chart_pattern refuse a stop more than 8% below entry; stage_analysis
   15%; earnings_gaps 1.5 ATR. CRWD's natural stops ran 9–10%.
3. **Volume vs size.** Volume confirmation asks for 1.5–3× average; a +20.5% CRWD results day managed
   2.46×. Perhaps heavily traded stocks rarely reach the threshold.

One stock is an anecdote. Each question below is answered on every stock that cleared the market's
liquidity floor (US $10M/day, India ₹50 crore/day).

## In short

| Gap | Verdict | Evidence |
|---|---|---|
| Trend lag | **Not a gap — the lag earns its keep** | 72% of reclaims fail within 20 sessions; entries at the stack beat entries at the reclaim in both markets |
| Stop caps | **A real gap, both markets** | breakouts with wider stops earn *more* per unit of risk, not less |
| Volume vs size | **Hypothesis refuted — and something bigger found** | relative volume does not depend on size in the US; but high volume on a big up day predicts *worse* returns |

## 1. Trend lag — not a gap

Events: a stock 30%+ below its 52-week high and below its 200-day closes back above the 200-day.

| | US (9,100 events) | India (950) |
|---|---|---|
| fell back below the 200-day within 20 sessions | **72%** | **72%** |
| stacked (50 > 150 > 200) within a year | 82% | 77% |
| median sessions from reclaim to stack | 61 | 62 |
| median gain already made by the stack | 11.5% | 10.4% |
| 120-session excess, buying the **reclaim** | +4.8% (hit 49%) | −0.3% (hit 42%) |
| 120-session excess, buying the **stack** | **+7.9%** (hit 52%) | **+5.8%** (hit 47%) |

Waiting costs about a tenth of the move and buys a better trade. Most reclaims are dead-cat bounces,
and the stack is what separates the rest. CRWD was the exception the rule correctly gives up.
**No change recommended.**

## 2. Stop caps — a real gap

Events: a close above the prior 55-day high, above the 200-day, on 1.5× volume, counted once per 20
sessions. The natural stop sits under the last 10 sessions' low; the trade exits there (or at the open
if it gaps through) or after 60 sessions. Bucketed by how far below entry that stop sits.

| Stop width | US n | US avg R | US win | US PF | India n | India avg R | India PF |
|---|---|---|---|---|---|---|---|
| < 5% | 8,480 | +0.11 | 34% | 1.16 | 150 | +0.14 | 1.20 |
| 5–8% | 12,880 | +0.11 | 42% | 1.20 | 817 | +0.27 | 1.45 |
| **8–12%** | 9,870 | **+0.16** | 48% | 1.35 | 1,190 | **+0.31** | 1.62 |
| **12–15%** | 3,719 | **+0.29** | 52% | 1.72 | 648 | **+0.27** | 1.65 |
| **> 15%** | 6,382 | **+0.24** | 51% | 1.64 | 950 | **+0.31** | 1.94 |

Measured in R — the right unit when position size comes from the stop — the setups an 8% cap refuses
are *better* than the ones it keeps, in both markets. Tight stops win less often (34% in the US) and
make it up with more 3R+ winners, but not enough.

Limits: this is a generic breakout, not any strategy's exact rules, and wider stops mean smaller
positions. It justifies **testing** wider caps as optimise-stage variants of breakout, chart_pattern
and stage_analysis — not changing them on this alone.

## 3. Volume vs size — refuted, and a bigger question

Events: up days of 8% or more.

| Liquidity quintile | US median rel. volume | US ≥ 3× | India median | India ≥ 3× |
|---|---|---|---|---|
| Q1 smallest | 1.79× | 28% | 3.53× | 59% |
| Q3 | 1.76× | 26% | 2.83× | 47% |
| Q5 largest | 1.78× | 24% | 2.64× | 41% |

In the US, relative volume on a big day does not depend on size at all; India shows a mild effect.
The size-filter hypothesis is wrong.

But forward returns by relative volume, *within* each size band, point the other way from every
volume-confirmation rule here:

| 60-session excess | < 1.5× | 1.5–3× | ≥ 3× |
|---|---|---|---|
| US small | **+14.4%** | +5.1% | +0.5% |
| US mid | +5.1% | +7.1% | +0.7% |
| US large | +5.0% | +5.0% | +0.9% |
| India small | **+10.6%** | +5.0% | +0.8% |
| India large | +2.1% | +2.3% | **−4.0%** |

The ≥ 3× bucket is the worst in every band in both markets. A big up day on enormous volume is
disproportionately a news spike or a blow-off that gives back, not institutional accumulation.

Limits: these are big up days, not breakouts from a base, and the events overlap in time. It does not
show that volume confirmation hurts a particular strategy — it shows the assumption behind it is not
supported here, which is worth an optimise-stage test: each volume-confirming strategy with the
condition off.

## Recommended next tests (optimise stage only)

1. Stop caps widened (e.g. 8% → 12% and → 15%) on breakout and chart_pattern; stage_analysis' 15%
   cap removed; earnings_gaps' 1.5 ATR raised to 2.5.
2. Volume confirmation off, one arm per strategy that requires it.
3. Trend lag: nothing to test.

Each is a variant judged against its own optimise-window control. Whatever survives goes to a single
verify run per version — with the pass criterion written down first.
