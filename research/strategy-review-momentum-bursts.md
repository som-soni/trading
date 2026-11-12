# Strategy family review — 2. Momentum bursts

*Family review per [the briefs](strategy-family-review-briefs.md) (§2), following `/backtest-review` for
`kullamagi` and `momentum_burst`. Written 2026-11-12. **Optimise stage only (2013-01-01 → 2021-12-31,
in-sample).** Neither strategy has a verify run (`verify_runs` is empty for both), and none was read. Analysis and
plan only: no code edited, no job queued, nothing committed. Every figure not quoted from a run report was computed
from stored prices up to 2021-12-31 by scripts in the session scratchpad, not in the repo.*

**In short**

- **Neither strategy has a demonstrated edge as built.** Both edge badges say "No edge" in both markets. No
  baseline beats buy-and-hold, and no baseline Sharpe survives deflation for the family's 35 optimise runs.
- **`kullamagi` (Kullamägi breakouts):** it makes a small positive average R (+0.11 US, +0.12 India). That R
  comes from about 5% of trades: without them the book loses 352R (US) and 93R (India). The US stock choice beats
  a random liquid stock (98th percentile), but only 2020 carries it. India shows no selection edge, and at India's
  standard cost the R is about zero.
- **The largest fidelity gap is the entry, and daily bars can only bound it.** Kullamägi buys the opening-range
  break with the stop at the day's low. On the same US bars, a buy at the pivot with the day's low as stop is
  worth between **+0.13R (pessimistic) and +0.44R (optimistic)** a trade. The code's buy at the close is worth
  **+0.04R**. A version that can be coded without look-ahead (buy-stop at the pivot, stop at yesterday's low)
  gets only +0.08R in the US and −0.02R in India. Settling this needs intraday bars.
- **`momentum_burst` (Bonde's 4% burst, 5-day hold):** none in the US (−0.005R a trade, 74th percentile against random entries). In
  India the selection is real (99th percentile) but tiny: +0.06R, which India's standard cost removes.
- **The family's best version today is `momentum_burst` in India with a 20-day-average exit** (run 3847): 17.0%
  CAGR, +3.5 points over the Nifty 500, Sharpe 1.02, deflated Sharpe 0.89. It is not yet an edge. At the
  standard Indian cost its excess is −0.6 points. 2021 made half its R. The signals that won slots made +0.35R,
  the ones skipped +0.00R. The same rules in the US lose to random stocks.
- **The plan:** six runs that need no code, each with pass criteria fixed below: a leadership gate, exits and
  universe for `kullamagi`; a bigger burst and a path-dependence check of the 20-day exit for `momentum_burst`.
  Then one data step that decides the family: intraday bars for the signal days. Two fixes are shared by the
  family: judge at standard cost, and run a random-ranking control.

---

## 0. Runs reviewed

| Run | Strategy | Market | Version / spec | Stage | Overrides | Role |
|---|---|---|---|---|---|---|
| 2312 | kullamagi | US | 1.3 / v1.3-19a348fa | optimise | none | **baseline** (v1.4's defaults are v1.3's rules; v1.4 adds an off-by-default entry floor and has no plain run) |
| 2308 | kullamagi | India | 1.3 / v1.3-19a348fa | optimise | none | **baseline** |
| 3888, 3890, 3891 / 3894, 3895 | kullamagi | US / India | 1.4 | optimise | `--pe` loss throttle; with 12.5% cap; with 25% cap × 5 slots | variants already tested |
| 3892 / 3896 | kullamagi | US / India | 1.4 / v1.4-7f831307 | optimise | `ENTRY_MIN_ADR_PCT=5` | variant already tested |
| 2364 / 2365 | kullamagi | US / India | 1.3 | optimise | `--max-position-pct 0.125` | variant already tested |
| 3236 / 2311, 3243 / 2310 | kullamagi | US / India | 1.3 | optimise | `TRAIL_EMA=1 TRAIL_SMA=20`; `TIGHT_MAX_ADR=2` | variants already tested |
| 1535–1540, 2209–2211, 2214, 2265, 2266 | kullamagi | both | 1.0, 1.2 | optimise | older rules and their variants | trials (count), not evidence |
| 2202 | momentum_burst | US | 1.0 / v1.0-e8ce18ba | optimise | none | **baseline** |
| 1831 | momentum_burst | India | 1.0 / v1.0-e8ce18ba | optimise | none | **baseline** |
| 2206 / 2205 | momentum_burst | US / India | 1.0 | optimise | `--time-stop-bars 10` | variant already tested |
| 2366 / 2367 | momentum_burst | US / India | 1.0 | optimise | `--max-position-pct 0.125` | variant already tested |
| 3851 / 3847 | momentum_burst | US / India | 1.0 | optimise | `--exit-mode ma --ma-col sma20 --time-stop-bars 250` | variant already tested |

Trials: `kullamagi` 27 optimise runs (14 US, 13 India), `momentum_burst` 8 (4 each); 35 for the family. No
paper book exists for either strategy (`paper_orders` holds only the three rebalance books).

---

## 1. `kullamagi` — Kullamägi breakouts

### 1.1 Scorecard (optimise, 2013–2021)

| Key parameter | US (2312) | India (2308) |
|---|---|---|
| CAGR / benchmark | 5.85% / 14.01% (SPY) | 1.81% / 13.54% (Nifty 500) |
| Excess CAGR (modelled cost) / at standard cost | −8.16 / −8.71 points | −11.72 / −14.52 points |
| Max drawdown / benchmark | −41.4% / −34.1% | −21.4% / −38.3% |
| Longest drawdown | 1,720 days | 1,466 days |
| Sharpe / Sortino / Calmar | 0.37 / 0.35 / 0.14 | 0.22 / 0.16 / 0.08 |
| Trades (per year) | 1,202 (134) | 333 (37) |
| Win rate / median R | 39.0% / −1.01R | 40.2% / −1.02R |
| Average R / profit factor | +0.105 / 1.13 | +0.118 / 1.12 |
| Exposure (days with a position) / average positions | 66.7% / 2.7 | 32.4% / 0.8 |
| Turnover / costs (share of gross P&L moved) | 25.0× / $11,163 (2.0%) | 8.0× / ₹2.99 lakh (4.9%) |
| Days held, mean / median | 7.3 / 5 | 7.5 / 6 |
| Median stop distance | 3.9% | 3.5% |

| R by exit | US trades | US avg R | US total R | India trades | India avg R | India total R |
|---|---|---|---|---|---|---|
| Stop | 667 | −1.06 | −709 | 181 | −1.07 | −194 |
| Trend exit (close < 10-day) | 267 | +2.89 | +771 | 72 | +3.00 | +216 |
| Breakeven (after the partial) | 262 | +0.24 | +64 | 80 | +0.22 | +17 |

| Equity return by year | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|
| US | −7.5% | −15.3% | −17.2% | +8.5% | +28.7% | −10.9% | +26.4% | **+64.4%** | −0.6% |
| India | −2.5% | +1.9% | +7.8% | −2.2% | +2.0% | −3.4% | −0.3% | +3.9% | +9.9% |

**Funnel.** US: 4,547 accepted signals, 1,202 traded; 2,019 lost to full slots, 914 to cash, 412 already held;
2,039 more were WATCH (stop over 1 ADR or under 1%). India: only **451 symbols** ever clear the ₹50 crore
liquidity floor; 493 accepted, 333 traded, so the book is idle two-thirds of the time.

### 1.2 Is the edge real

| Check | US | India |
|---|---|---|
| Sharpe (daily, annualised) | 0.37 | 0.22 |
| Probabilistic Sharpe > 0 | 0.87 | 0.75 |
| Deflated Sharpe, N = market's trials (14 / 13) | 0.52 | 0.28 |
| Deflated Sharpe, N = strategy's 27 / family's 35 | 0.35 / 0.23 | 0.20 / — |
| Best trial (2364, 12.5% cap), deflated, N = 14 / 27 | 0.66 / 0.49 | — |

Deflated Sharpe inputs: daily equity returns of the run (T = 2,266 US, 2,217 India), their skew (0.71 / 2.40) and
kurtosis (11.6 / 44.5), and the standard deviation of the trials' annualised Sharpes (0.20 US, 0.24 India, 0.25 all
27, 0.29 family). No result is near 0.95.

**Selection vs timing: matched random-entry null** (300 draws per trade, same entry and exit dates).

| Pool | Trades | Traded stocks, close to close | Trade return incl. exits | Null mean [95%] | Percentile |
|---|---|---|---|---|---|
| US, liquid stocks | 1,196 | +0.85% | +0.76% | +0.38% [+0.04, +0.80] | 98th (trade 96th) |
| US, Big movers screen (G1, G2 pass) | 1,196 | +0.85% | +0.76% | +0.40% [−0.25, +1.15] | 91st (88th) |
| India, liquid stocks | 333 | +0.62% | +0.54% | +0.50% [−0.04, +1.10] | 68th (58th) |
| India, Big movers screen | 333 | +0.62% | +0.54% | +0.38% [−0.38, +1.14] | 74th (65th) |

In the US the chosen stocks beat a random liquid stock by about 0.45% a trade, so there is a little selection.
Against other big movers the evidence is weaker. India shows none. The exits move the % return little: what they
do is turn it into R.

**Signals vs traded** (every S1 signal with all gates, scored by replaying the strategy's exits; the replay matches
the run's trades: correlation 0.99 US, 1.00 India).

| | US n | US R | US 20 / 60-day return | India n | India R | India 20 / 60-day return |
|---|---|---|---|---|---|---|
| Traded | 1,202 | +0.100 | +2.6% / +7.2% | 333 | +0.119 | +3.7% / +9.1% |
| Accepted, not traded (slots, cash, held) | 3,378 | +0.018 | +5.0% / +12.5% | 160 | −0.113 | +2.1% / +6.4% |
| WATCH (stop outside 1%–1 ADR) | 2,008 | −0.098 | +2.3% / +9.0% | 387 | +0.194 | +3.2% / +10.0% |

The skipped US signals went up *more* over 20–60 days, but the stop at the day's low and the 10-day trail
captured less of it (+0.02R). Slots did not cost R in the US. Cash and slots bind mostly in 2020, which alone
produced 2,594 of the 4,580 valid US signals.

**Concentration.** US: the best 5% of trades (60) made 3.8 times the book's net R; without them, −352R. India:
the best 17 made 3.4 times; without them, −93R. Removing the best 1% leaves −0.03R (US) and −0.04R (India) a trade.
Best year: US 2020 (+116R; +64% equity). Worst: US 2015 (−28R). In India, 2015 and 2021 are the good years;
2018 is the worst (−12R).

**Verdict.** No edge as built. Kullamägi's method has a long, public (self-reported, unaudited) record, so this is
treated as an implementation gap until a faithful version has been tested. §1.3 shows where that version differs.

### 1.3 The method: fidelity check

Source: Kullamägi's blog and recorded streams, as summarised in the Learn guide *Kullamägi's momentum breakouts*.
These are practitioner material, not tested evidence; he gives ranges, not one rule set.

| Rule | Kullamägi | This code | Gap | Matters? |
|---|---|---|---|---|
| Leadership | Top 1–2% by 1-, 3- and 6-month gain | 20-day high ≥ 50% above the 63-day low (G2) | **Different** | **Yes**: signals outside the top 10% by any of those gains lose (US −0.11R, n = 1,275; India −0.28R, n = 110) |
| Speed | ADR ≥ 4%, ideally ≥ 5% | ADR ≥ 4% (G1); 5% tested (3892) | Same; known choice | Tested: +0.17R, still fails |
| Liquidity | ~$5m / ₹5 crore a day | $10m / **₹50 crore** (20-day) | Stricter | India: 451 symbols, 0.8 positions on average |
| Rest | 2–8 weeks, higher lows, narrowing | Fixed 10 sessions, span ≤ 3 ADR | Simplified | Untested; the fixed window puts the pivot at the 10-day high |
| Surfing averages | Rising 10/20/50-day | G4, same (v1.3) | Same | Rests on the 50-day earn +0.31R US (n = 554), on the 10-day ±0 (n = 3,165) |
| Volume dry-up / breakout volume | Liked | Not required | Known choice (v1.1 audit) | Data agrees: no relation in either market |
| **Entry** | **Opening-range high, intraday** | **The breakout day's close** | **Different** | **The largest gap; see the next table** |
| Stop | Low of day at entry (opening-range low), ≤ 1 ADR | Whole day's low, 1%–1 ADR | Simplified | Tight stops (< 0.46 ADR) lose (−0.10R US) |
| Partial | ⅓–½ after 3–5 days, stop to entry | ⅓ on day 3 | Same | — |
| Trail | Close below 10-day (20-day for slower) | 10-day SMA; EMA20 tested | Same | Slower trails do better in both markets (§1.4) |
| Market | Nasdaq above rising 10/20 EMAs | G6, same | Same | Neutral in the data, kept as his rule |
| Results | Sells before results unless well in profit | Holds through | Missing | Weak: entries with results ≤ 10 days ahead +0.08R vs +0.13R (US, n = 125); −0.05R vs +0.15R (India, n = 61) |
| Sizing / exposure | 0.25–1% risk; press when trading well | 1%, 25% cap, 10 slots; `--pe` tested | Known choice | Halves US drawdown, no CAGR gain |
| Episodic pivot | His second setup | Not here | Missing | Lives in `earnings_gaps` (family 6) |

**The entry, bounded on daily bars.** The test uses the same gate-passing bars where the high crossed the pivot. "Intraday" buys at
max(open, pivot), skips an open more than 1 ADR above it, and stops at the day's low. *Optimistic* assumes no
stop on the entry day. *Pessimistic* scores any day that closes below the entry as −1R. *Implementable* is a
buy-stop at the pivot with yesterday's low as the stop (known in advance; a same-day touch counts as stopped). Caveat: G1, G2 and
G6 read the entry day itself, the same for every column.

| Entry (exits as the code) | US n | US avg R | US years > 0 | India n | India avg R | India years > 0 |
|---|---|---|---|---|---|---|
| Close of the breakout day (code) | 4,580 | +0.039 | 4/9 | 493 | +0.043 | 5/9 |
| Intraday at the pivot, optimistic | 9,257 | **+0.435** | 8/9 | 1,375 | +0.400 | 5/9 |
| Intraday at the pivot, pessimistic | 9,257 | **+0.127** | 6/9 | 1,375 | +0.077 | 3/9 |
| Buy-stop at the pivot, yesterday's low as stop | 6,047 | +0.082 | 5/9 | 903 | −0.019 | 3/9 |
| Next session's open | 3,803 | −0.065 | 2/9 | 424 | +0.061 | 5/9 |

```chart
title: Kullamägi breakouts — average R by entry method, same bars, optimise stage
labels: Close (code) | Intraday, pessimistic | Intraday, optimistic | Buy-stop, prior-day low | Next open
series: US | 0.039 | 0.127 | 0.435 | 0.082 | -0.065
series: India | 0.043 | 0.077 | 0.400 | -0.019 | 0.061
unit: R per trade, after modelled slippage
caption: Event replay over the stored v1.3 signals, 2013–2021. The intraday rows are bounds, not results: the true value of an opening-range entry needs intraday bars.
```

The intraday entry pays 1.5% (US) to 1.9% (India) less than the close on the days that closed above the pivot.
It also buys the 4,278 US (719 India) days that crossed and failed, at −0.38R (−0.45R) even when no stop is
assumed on the entry day. Even the pessimistic bound beats the close entry in both markets. Only intraday
bars can say how much.

### 1.4 Diagnosis (all 4,580 US / 493 India valid signals, close entry)

| Finding | US | India | Status |
|---|---|---|---|
| Momentum rank ≥ 90th percentile (any of 1/3/6 months) vs below | +0.097 (n 3,306) vs −0.106 (1,275) | +0.136 (383) vs −0.279 (110) | Plateau over 90–100th in the US (+0.16, +0.08, +0.07); but US ≥ 90th without 2020: −0.04 |
| Rest surfs the 50-day vs the 10-day | +0.313 (554) vs −0.001 (3,165) | +0.217 (58) vs −0.030 (328) | Both markets; India n small |
| ADR quintiles, low → high | −0.09, +0.03, +0.06, +0.06, +0.14 | +0.05, +0.20, +0.07, +0.11, −0.21 | US only; ADR floor 5 already tested |
| Stop distance quintiles, tight → wide | −0.16, +0.06, −0.02, +0.07, +0.24 | not monotone | US only |
| Breakout volume (× 50-day) | no relation | top quintiles worse | Contradicts a volume rule |
| Breadth (10-day up-4% ÷ down-4% days) | non-monotone; hottest quartile −0.33 | non-monotone | No filter supported |
| Year | 2020 = 57% of signals; without 2020 +0.003 | 2015, 2017 carry it | **The US result is a 2020 result** |

| Exit replay on all valid signals | US avg R | India avg R | Without 2020 (US) |
|---|---|---|---|
| 10-day trail, ⅓ on day 3 (code) | +0.039 | +0.043 | +0.003 |
| 20-day trail, ⅓ on day 3 | +0.056 | +0.116 | — |
| 50-day trail, ⅓ on day 3 | +0.236 | +0.201 | +0.031 |
| 20-day EMA trail (tested as 3236 / 2311) | +0.082 | +0.098 | — |
| 20-day trail, no partial | +0.127 | +0.270 | −0.036 |
| ½ on day 5, 10-day trail | +0.001 | +0.126 | — |

Slower trails rank in the same order in both markets (10 < 20 < 50 days). That is a plateau, not a single peak.
But without the best 1% of trades every exit turns negative, and in the US most of the gain is 2020. So the exit
is a *fragile* improvement. A 50-day trail is also off-method: it is closer to Minervini than to Kullamägi.

**Costs.** India's runs model 10 bps a side; the report's standard cost is 27 bps. On a 3.5% median stop that is
about 0.10R a trade more, which takes India's +0.12R to about +0.02R. US costs barely move it (5 vs 6 bps).

### 1.5 Ranked improvements

| # | Change | Targets | Evidence | Robustness | Type |
|---|---|---|---|---|---|
| K1 | Intraday bars for signal days; test the opening-range entry with the opening-range-low stop | avg R, CAGR | Bounds +0.13 to +0.44R vs +0.04R (US), n 9,257 | Bounds hold in 6–8 of 9 US years; India 3–5 | from the method; **needs data** |
| K2 | Leadership gate: top 10% by 1/3/6-month gain. First approximated with the existing RS filter | avg R, win rate | −0.11R / −0.28R below the gate; plateau above it | Both markets, 90–100th plateau; US depends on 2020 | from the method; no code first, then a new gate |
| K3 | Slower trail: TRAIL_SMA = 20 (his "slower stock" option), neighbour 50 | avg R, CAGR | Replay: 10 < 20 < 50 in both markets | Plateau yes; years no; best 1% decides | parameter change (post-scan, cached signals); **fragile** |
| K4 | India universe: ₹10 crore floor (neighbour ₹20 crore) | exposure, CAGR | 451 symbols, 0.8 positions on average; Learn guide uses ₹5 crore | Untested; price bands not modelled | mechanics |
| K5 | Buy-stop at the pivot, yesterday's low as stop | avg R | US +0.08 vs +0.04; India −0.02 vs +0.04 | Mixed across markets | new rule (rescan); only if K1 is impossible |
| — | Results blackout | drawdown | n 125 / 61, weak | Not robust | not proposed now |
| — | Volume, breadth, ADR 5, loss throttle, 5 slots, EMA trail, tight rest 2 ADR | — | Tested or contradicted (above) | — | known choices, not re-proposed |

---

## 2. `momentum_burst` — Bonde's 4% burst

### 2.1 Scorecard (optimise, 2013–2021)

| Key parameter | US (2202) | India (1831) | India, 20-day exit (3847) | US, 20-day exit (3851) |
|---|---|---|---|---|
| CAGR / benchmark | −2.15% / 14.01% | 3.68% / 13.54% | **17.02%** / 13.54% | −0.46% / 14.01% |
| Excess, modelled / standard cost | −16.16 / −16.94 | −9.86 / −17.37 | **+3.48 / −0.62** | −14.47 / −14.79 |
| Max drawdown | −61.8% | −32.5% | −27.3% | −47.9% |
| Longest drawdown | 1,978 days | 1,477 days | 713 days | 1,424 days |
| Sharpe / Sortino / Calmar | −0.01 / −0.01 / −0.03 | 0.35 / 0.31 / 0.11 | 1.02 / 0.95 / 0.62 | 0.09 / 0.09 / −0.01 |
| Trades (per year) | 2,546 (283) | 1,127 (125) | 639 (71) | 1,249 (139) |
| Win rate / median R | 45.0% / −0.14R | 44.6% / −0.13R | 33.7% / −0.44R | 29.6% / −0.72R |
| Average R / profit factor | −0.005 / 0.97 | +0.058 / 1.10 | +0.354 / 1.92 | +0.002 / 0.99 |
| Exposure / average positions | 74.6% / 4.7 | 60.9% / 2.3 | 78.4% / 3.7 | 89.9% / 6.4 |
| Turnover / costs | 38.1× / $14,465 | 20.5× / ₹7.28 lakh (4.6%) | 10.1× / ₹5.42 lakh | 15.4× / $6,267 |
| Days held, mean | 6.0 | 6.5 | 19.2 | 16.8 |
| Median stop distance | 5.1% | 5.2% | 5.2% | 5.2% |

| R by exit (baselines) | US trades | US avg R | US total R | India trades | India avg R | India total R |
|---|---|---|---|---|---|---|
| Time (5 sessions) | 1,657 | +0.56 | +925 | 814 | +0.48 | +387 |
| Stop | 882 | −1.06 | −937 | 313 | −1.03 | −322 |

| Equity return by year | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|
| US (2202) | +12.4% | −1.7% | −23.9% | −18.4% | −25.1% | +13.1% | −0.6% | +46.0% | −2.4% |
| India (1831) | −6.8% | +21.6% | −9.8% | −13.3% | +11.7% | −11.6% | −2.7% | +20.8% | +34.8% |
| India, 20-day exit (3847) | +4.6% | +11.0% | −3.0% | −1.7% | +41.5% | −6.3% | −6.5% | +32.8% | **+125.6%** |
| Nifty 500 | +3.6% | +37.8% | −0.7% | +3.8% | +35.9% | −3.4% | +7.7% | +16.7% | +30.2% |

**Funnel.** US: 7,095 accepted, 2,546 traded; 3,063 lost to cash and 1,419 to slots. At 1% risk and a 5% stop
a position is about 20% of equity, so the 25% cap and cash bind long before the 10 slots. India: 1,641 accepted,
1,127 traded, 417 lost to cash.

### 2.2 Is the edge real

| Check | US 2202 | India 1831 | India 3847 (20-day exit) |
|---|---|---|---|
| Sharpe | −0.01 | 0.35 | 1.02 |
| Probabilistic Sharpe > 0 | 0.49 | 0.85 | 0.999 |
| Deflated, N = 4 (market) / 8 (strategy) | 0.26 / 0.08 | 0.53 / 0.35 | 0.98 / 0.95 |
| Deflated, N = 35 (family) | — | — | **0.89** |

(Inputs: T = 2,266 / 2,217 daily returns; skew 0.32 / 0.50 / 0.02; kurtosis 9.9 / 13.7 / 8.9; trial Sharpe s.d.
0.20 US, 0.31 India, 0.33 strategy, 0.29 family.) The deflated Sharpe is against zero, not against the
benchmark's 0.86.

| Matched random-entry null | Trades | Traded stocks, close to close | Trade incl. exits | Null mean [95%], liquid pool | Percentile (liquid / Near-highs screen) |
|---|---|---|---|---|---|
| US 2202 | 2,539 | +0.21% | +0.23% | +0.15% [−0.04, +0.34] | 74th / 78th |
| India 1831 | 1,127 | +0.64% | +0.61% | +0.32% [+0.09, +0.58] | **100th / 99th** |
| India 3847 | 638 | +2.09% | +2.02% | +0.64% [+0.04, +1.29] | **100th / 100th** |
| US 3851 | 1,241 | −0.10% | −0.04% | +0.35% [−0.05, +0.85] | **1st / 0th** |

India's bursts are a real, small selection: 0.3% a trade over five days, about 0.06R on a 5.2% stop. US bursts
are no better than a random stock. Held for weeks, they do *worse* than a random stock.

| Signals vs traded | US n | US 5-day R | US 20-day exit R | India n | India 5-day R | India 20-day exit R |
|---|---|---|---|---|---|---|
| Traded (baseline) | 2,546 | −0.007 | +0.045 | 1,127 | +0.050 | +0.174 |
| Accepted, not traded | 4,570 | **+0.040** | +0.024 | 514 | +0.075 | +0.057 |
| Traded in the 20-day-exit run / not | 1,249 / 5,867 | — | 0.000 / +0.038 | 639 / 1,002 | — | **+0.346 / +0.004** |
| All valid signals | 7,116 | +0.023 | +0.032 | 1,641 | +0.058 | +0.137 |

In the US the skipped signals were better (+0.047R, about 1.6 standard errors). In India's 20-day-exit run the
traded 639 made +0.35R a trade against +0.00R for the 1,002 skipped. The best run's result therefore depends on
which signals won a slot; the signals as a whole made +0.14R.

**Concentration.** US 2202 nets −13.5R. India 1831: the best 56 trades (5%) made 2.9 times its +65R; without them,
−121R. India 3847: the best 32 made 1.3 times its +226R; 2021 alone made +114R (50%). From 2013 to 2020 its CAGR is
7.8% against the Nifty 500's 11.7%.

**Verdict.** The base (5-day hold) has no edge: none in the US, and in India one that costs remove. The 20-day-exit
variant in India is the family's strongest result, but it is fragile (§2.4).

### 2.3 The method: fidelity check

Source: Pradeep Bonde (Stockbee), as he describes it on his blog and in his teaching, summarised in the Learn guide
*Momentum bursts*. Practitioner material, self-reported results.

| Rule | Bonde | This code | Gap | Matters? |
|---|---|---|---|---|
| Burst | Close ≥ 4% up on more volume than yesterday | Same (S1) | Same | Bigger bursts do better (below) |
| Close near the high | Strong close | Top 30% of the range | Same | Top third of closes slightly better |
| Not already moving | First day out of a quiet stretch | Yesterday ≤ 2% (G4), narrow ranges (G5) | Simplified | Without G4/G5: same R (Learn guide); not re-tested |
| Universe | Any liquid stock (≥ 100k shares) | Near highs, rising 200-day (G1–G3), $10m / ₹50 crore | **Added trend filter**; stricter floor | Removing G1–G3: same R a trade (US +0.023 vs +0.027; India +0.052 vs +0.054), 2–3× the signals |
| Market | Breadth: counts of 4% up and down days | Index above its 20-day EMA (G6) | Different | No breadth relation in the data; G6 off: same R |
| **Entry** | **Intraday, as it crosses +4% or its opening range** | **Close of the burst day** | **Different** | Bounds below: the gain is not established |
| Stop | Low of the day so far | Whole day's low, ≥ 1% | Simplified | Wider-stop quintile best (US +0.10R) |
| Exit | 3–5 days, often into strength | Close of session 5 | Simplified | 10 sessions tested: better in the US (2206) |
| Selection | Reads every chart, takes few | 12-1 month momentum ranking | Different | Skipped US signals beat traded ones |

**The entry, bounded.** The test uses events I rebuilt from stored prices, with the trend, quiet and market tests read on the
day before. It reproduces the stored signals: 7,263 vs 7,120 US, 1,653 vs 1,641 India.

| Entry (5-session hold) | US n | US avg R | India n | India avg R |
|---|---|---|---|---|
| Close of the burst day (code) | 7,263 | +0.027 | 1,653 | +0.054 |
| Buy-stop at +4%, day's low as stop, optimistic | 15,035 | +0.052 | 3,113 | +0.081 |
| Same, pessimistic (close below entry = −1R) | 15,035 | −0.288 | 3,113 | −0.308 |
| Buy-stop at +4%, yesterday's low as stop | 15,631 | −0.093 | 3,128 | −0.111 |
| Close entry, no trend filter (Bonde's universe) | 20,148 | +0.023 | 3,061 | +0.052 |

Unlike Kullamägi's, the burst's intraday entry is not clearly better. Even the optimistic bound adds only
+0.03R. Many +4% crossings fade, and the strong-close and volume filters, which cannot be known intraday, do real
work. On daily bars this is not where the burst's edge is missing.

### 2.4 Diagnosis

| Finding (all valid signals, 5-day hold) | US | India | Status |
|---|---|---|---|
| Burst size quartiles, small → large | −0.049, +0.016, +0.019, +0.107 | −0.035, +0.058, +0.061, +0.147 | **Monotone in both markets** |
| Stop distance quintiles, tight → wide | −0.02, −0.02, +0.01, +0.05, +0.10 | not monotone | US |
| Volume vs 50-day average | no relation (lowest quartile best) | no relation | Contradicts a volume rule |
| Breadth (5- or 10-day up ÷ down) | no relation | no relation | No filter supported |
| Hold: 3 / 5 / 10 sessions / 20-day exit | +0.010 / +0.023 / +0.062 / +0.032 | +0.038 / +0.058 / +0.046 / +0.137 | Longer helps in the US; in India the 20-day exit |
| Years with positive 5-day R | 4/9 (2018–2021) | 4/9 | Not robust |
| Results within 10 days of entry | +0.03 (n 218) vs −0.00 | +0.15 (216) vs +0.04 | A blackout would hurt bursts |

```chart
title: Momentum bursts — average R by size of the burst day (quartiles), optimise stage
labels: 4.0–4.5% | 4.5–5.3% | 5.3–7.1% | over 7.1%
series: US | -0.049 | 0.016 | 0.019 | 0.107
series: India | -0.035 | 0.058 | 0.061 | 0.147
unit: R per trade, 5-session hold
caption: All 7,116 US and 1,641 India valid signals of v1.0-e8ce18ba, replayed with the strategy's exits. India's quartile edges are 4.0–4.5–5.2–6.5%. Bursts under about 4.5% lose in both markets.
```

**Why the 20-day exit is fragile.** (1) At the standard Indian cost its excess is −0.62 points; the run models
10 bps a side against a standard 27. (2) Half its R is 2021; 2013–2020 trail the index by about 4 points a year.
(3) The traded signals' +0.35R against +0.00R for the skipped ones points to path luck in which signals won a
slot. (4) The same rules in the US lose to random stocks.

### 2.5 Ranked improvements

| # | Change | Targets | Evidence | Robustness | Type |
|---|---|---|---|---|---|
| B1 | BURST_MIN_PCT = 5 (fixed before any run, never run); neighbour 6 | avg R, win rate | Size quartiles monotone in both markets | Plateau yes; both markets yes; years untested | parameter change (scan constant, rescan) |
| B2 | Path check of the 20-day exit: random ranking; then with a 12.5% position cap | excess, drawdown | 3847 traded +0.35R vs skipped +0.00R | Decides whether 3847 is luck | mechanics (no code) |
| B3 | Combine B1 with the 20-day exit, India first | excess at standard cost | B1 and B2 both pass | Only after both pass | mechanics + parameter |
| B4 | 3-session hold (fixed before any run, never run) | — | Replay predicts worse (+0.010 / +0.038) | — | parameter; run only to close the registration |
| — | Drop the trend filter (Bonde's universe) | — | Same R, more signals; cash-bound book | — | not proposed |
| — | Breadth market filter; volume above average; results blackout | — | Contradicted by the data | — | not proposed |
| — | 10-session hold, 12.5% cap, 20-day exit | — | Tested (2206/2205, 2366/2367, 3851/3847) | — | known choices |

---

## 3. The family's best version today

**`momentum_burst` in India with the 20-day-average exit (run 3847)** is the closest to a working edge:

- the only optimise run in the family that beats its benchmark (+3.48 points);
- the highest Sharpe (1.02) and deflated Sharpe (0.89 over the family's 35 runs);
- a selection edge at the 100th percentile against random liquid stocks.

It is not an edge yet: at standard costs it trails the index, 2021 carries it, and the signals that won slots
did far better than the rest. Its useful part is a combination: **pick the burst (a big up day out of a quiet
stretch), then hold it like a trend trade.** That is no longer Bonde's 3–5-day method.

**`kullamagi`** is the most faithful build of the method with the strongest documented record. Its one
measurable US selection edge rests on 2020. Its most likely missing edge, the intraday entry with the
opening-range stop, cannot be measured on daily bars. The bounds say it could be worth 0.1–0.4R a trade.

---

## 4. Improvement plan (ranked across the family)

### 4.1 Pass criteria, fixed now, before any run

Every variant is judged against its own market's baseline (2312 / 2308 / 2202 / 1831, or 3847 for B2–B3).

| Criterion | Requirement |
|---|---|
| P1 — the strategy's own criterion (unchanged) | Beats the benchmark CAGR and makes a positive average R after costs, in at least one market — **read at the standard cost** (`excess_std_cost` > 0), not only at the modelled slippage |
| P2 — years | Average R positive in at least 5 of 9 years, and no single year more than 50% of the total R |
| P3 — neighbour | The listed neighbouring value moves the same way (at least half the gain) |
| P4 — trials | Deflated Sharpe ≥ 0.90 with N = every family optimise run to date (35 + each new run) |
| P5 — no damage | Max drawdown no more than 5 points worse than the baseline; trades per year at least half the baseline's |

A variant that passes P1–P5 in one market becomes a version candidate. One that passes only the per-change
target below, without P1, is kept as a component for the combination run and not shipped alone.

### 4.2 Ranked plan

| Rank | Change | Strategy | Per-change target (beyond P2–P5) | Needs code? |
|---|---|---|---|---|
| 1 | **B2**: path check of the 20-day exit (random ranking; then 12.5% cap) | momentum_burst | India: excess at standard cost ≥ 0 with random ranking; 2021 ≤ 50% of R. If random ranking falls to about the signals' +0.14R, 3847 was path luck | No |
| 2 | **K2**: leadership gate, approximated with `--min-rs 90` (neighbour 80) | kullamagi | avg R ≥ +0.15 in both markets (base +0.105 / +0.118); US avg R excluding 2020 > 0 | No first; yes if it passes (new gate G8 on 1/3/6-month rank: `evaluate()` change, rescan, v1.5, changelog, `gate_docs`, `param_docs`, `status`) |
| 3 | **B1**: `BURST_MIN_PCT=5` (neighbour 6) | momentum_burst | avg R ≥ +0.05 US / +0.10 India (base −0.005 / +0.058); ≥ 100 / 40 trades a year | No (`--const`, new spec id, rescan); adopting it bumps to v1.1 with `setup_docs`, changelog, `status` |
| 4 | **K1 / shared F2**: intraday bars for the signal days | both | Kullamägi opening-range entry, opening-range-low stop: avg R ≥ +0.15 at standard cost on ≥ 1,000 US events | Yes: a new `marketdata/` job (data layer), then an entry mode. Needs your approval and a data source |
| 5 | **K3**: `TRAIL_SMA=20` (neighbour 50) | kullamagi | avg R +0.05 over the base in both markets; US without 2020 > 0 | No (post-scan constant, cached signals); adoption bumps the version, `signal_version` may stay 1.3 |
| 6 | **K4**: India floor ₹10 crore (neighbour ₹20 crore) | kullamagi | Average positions ≥ 1.5; avg R at standard cost ≥ the base's | No |
| 7 | **B3**: B1 + 20-day exit | momentum_burst | P1–P5 in India | No; adoption = v1.1 (`backtest_args` exit change; `signal_version` stays 1.0 only if B1 is not part of it) |
| 8 | **B4**: `--time-stop-bars 3` (fixed before any run) | momentum_burst | Expected to fail; runs only to close the registration | No |
| 9 | **K5**: buy-stop at the pivot, yesterday's low as stop | kullamagi | Only if rank 4 cannot be done; avg R ≥ +0.10 in both markets | Yes (`evaluate()`/`build_plans`, order type `stop`, rescan, v1.5) |

### 4.3 Commands (optimise stage only; run one change at a time, from `scripts/`)

```bash
# 1. B2 — path check of the 20-day exit (India first, then US for symmetry)
python -m jobs enqueue backtest --market india --strategies momentum_burst --stage optimise --bt '--exit-mode ma --ma-col sma20 --time-stop-bars 250 --rank-by random'
python -m jobs enqueue backtest --market india --strategies momentum_burst --stage optimise --bt '--exit-mode ma --ma-col sma20 --time-stop-bars 250 --max-position-pct 0.125'

# 2. K2 — leadership gate (RS-rating approximation), then its neighbour
python -m jobs enqueue backtest --market us    --strategies kullamagi --stage optimise --bt '--min-rs 90'
python -m jobs enqueue backtest --market india --strategies kullamagi --stage optimise --bt '--min-rs 90'
python -m jobs enqueue backtest --market us    --strategies kullamagi --stage optimise --bt '--min-rs 80'
python -m jobs enqueue backtest --market india --strategies kullamagi --stage optimise --bt '--min-rs 80'

# 3. B1 — bigger burst, then its neighbour
python -m jobs enqueue backtest --market us    --strategies momentum_burst --stage optimise --const BURST_MIN_PCT=5
python -m jobs enqueue backtest --market india --strategies momentum_burst --stage optimise --const BURST_MIN_PCT=5
python -m jobs enqueue backtest --market us    --strategies momentum_burst --stage optimise --const BURST_MIN_PCT=6
python -m jobs enqueue backtest --market india --strategies momentum_burst --stage optimise --const BURST_MIN_PCT=6

# 5. K3 — slower trail (post-scan: reuses the cached signals)
python -m jobs enqueue backtest --market us    --strategies kullamagi --stage optimise --const TRAIL_SMA=20
python -m jobs enqueue backtest --market india --strategies kullamagi --stage optimise --const TRAIL_SMA=20
python -m jobs enqueue backtest --market us    --strategies kullamagi --stage optimise --const TRAIL_SMA=50
python -m jobs enqueue backtest --market india --strategies kullamagi --stage optimise --const TRAIL_SMA=50

# 6. K4 — India universe
python -m jobs enqueue backtest --market india --strategies kullamagi --stage optimise --min-dollar-volume 100e6
python -m jobs enqueue backtest --market india --strategies kullamagi --stage optimise --min-dollar-volume 200e6

# 7. B3 — only if B1 and B2 pass
python -m jobs enqueue backtest --market india --strategies momentum_burst --stage optimise --const BURST_MIN_PCT=5 --bt '--exit-mode ma --ma-col sma20 --time-stop-bars 250'

# 8. B4 — closes the up-front registration
python -m jobs enqueue backtest --market us    --strategies momentum_burst --stage optimise --bt '--time-stop-bars 3'
python -m jobs enqueue backtest --market india --strategies momentum_burst --stage optimise --bt '--time-stop-bars 3'
```

Check in the first job's log that a `--rank-by` or `--time-stop-bars` passed with `--bt` overrides the copy in
the strategy's `backtest_args` (`--rank-by setup_momentum`, `--time-stop-bars 5`), not the reverse. These are
20 runs, each a trial, so the family count goes from 35 to 55 and P4 is read against that.

---

## 5. Shared fixes (proposed once, for the family)

| # | Fix | Why | Needs code? |
|---|---|---|---|
| F1 | **Judge India at the standard cost.** Every pass reads `excess_std_cost` and R after 27 bps a side | India's runs model 10 bps. The gap is 0.06–0.10R a trade, which is the whole India edge in both baselines | No (criterion) |
| F2 | **Intraday bars for signal days only** (a 5-minute window for the few thousand signal dates) | The one fidelity gap both originators say matters, and daily bars can only bound it (§1.3, §2.3) | Yes: a `marketdata/` job; source and cost to be decided by you |
| F3 | **Random-ranking control** for each baseline before any ranking change | Burst US: skipped signals beat traded ones; burst India 20-day exit: traded +0.35R vs skipped +0.00R | No (`--bt '--rank-by random'`) |
| F4 | **Keep G6 as the method's rule; do not tune it.** No breadth filter | Neutral in both strategies; breadth is non-monotone in both | — |
| F5 | **Update `momentum_burst`'s `status`.** It still reads "NOT YET MEASURED" although eight optimise runs exist, and it lists two up-front variants that were never run | CLAUDE.md: `status` names every figure's stage after a backtest | Docs only, no version bump |
| F6 | Episodic pivots belong to `earnings_gaps` (family 6) | Both originators' second setup; do not add a copy here | — |
| F7 | `--idle-index` as a diagnostic for `kullamagi` India | 0.8 positions on average: the benchmark comparison is mostly cash drag. A diagnostic, not a change of criterion, unless you decide otherwise | No |

---

## 6. Verify and the paper-trading gate

**Spending the verify run.** Only a version, not a `--const` variant, that passes P1–P5 in the optimise stage at
standard cost, in the market it will trade. Before the run, write its verify criterion into `status`: P1 at
standard cost over 2022 onward, and positive average R. Report the result even if it fails.

**Paper-trading gate for the family's best version** (`momentum_burst`, India, 20-day exit, if rank 1 and rank 3
or 7 pass). No paper book exists today.

| Measure | Gate |
|---|---|
| Length | 12 months and at least 60 closed trades (3847 traded 71 a year) |
| Average R after actual costs | ≥ +0.15R (the run's +0.35R less standard costs and a margin for price-band fills) |
| Win rate | 25–40% (3847: 33.7%) |
| Slippage at the stop | Average realised fill no more than 0.10R worse than the stop price |
| Drawdown | Max drawdown no deeper than −25% |
| Against the index | Return at least the Nifty 500's over the same 12 months |
| Concentration | The best 5% of trades no more than 150% of net R |
| Band locks | Every upper- or lower-band lock that blocked an entry or exit logged; more than 5% of trades affected stops the test |

For `kullamagi` US, if K1 or K2 produces a passing version: at least 100 closed trades (about 9 months at
134 a year), average R ≥ +0.10 after costs, at most 60% of trades ending at the full stop (run 2312: 55%, median
two sessions), and entry fills within 0.05R of the modelled price.

---

## 7. What could not be determined

- **The value of the intraday entry** for either method: daily bars give bounds of +0.13R to +0.44R (Kullamägi,
  US) and −0.29R to +0.05R (burst, US). Intraday bars on the signal days would settle it.
- **Survivorship.** Today's stock lists only. Fast stocks that collapsed and were delisted are missing, which
  flatters both strategies by an unknown amount.
- **India price bands** are not modelled. A lower liquidity floor (K4) makes this matter more.
- **Whether `--min-rs` stands in for Kullamägi's 1/3/6-month leadership.** It is the TT-08 cross-sectional RS
  rating. The replay used the maximum of 1-, 3- and 6-month percentiles, so a pass with `--min-rs` needs the coded
  gate before adoption.
- **Whether an argument passed with `--bt` overrides `backtest_args`** (rank and hold flags). Check it on the first job.
- **Method notes for the computed figures.** The event replays apply the strategy's exits to stored prices with
  the run's slippage and no portfolio limits. The entry-method comparisons read G1, G2 and G6 on the entry day for
  every column. The burst events were rebuilt from prices and reproduce the stored signals to within 2%. Scripts
  (session scratchpad): `mb/score.py`, `mb/dsr.py`, `mb/null.py`, `mb/sig_k.py`, `mb/sig_b.py`, `mb/entry_k.py`,
  `mb/entry_k2.py`, `mb/k_more.py`, `mb/diag_k.py`, `mb/b_fid.py`, `mb/diag_b.py`, `mb/results.py`.
