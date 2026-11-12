# Strategy family review — 6. Earnings events

*Family review per [the briefs](strategy-family-review-briefs.md) (§6), following `/backtest-review` for `pead`
and `earnings_gaps`. Written 2026-11-12. **Optimise stage only (2013-01-01 → 2021-12-31, in-sample).** Neither
strategy has a verify run (`verify_runs` is empty for both), so no verify trades, tables or figures were read.
Legacy runs are quoted as context only. Analysis and plan only: no code edited, no job queued, nothing committed.
Working scripts are in the session scratchpad (`fam6/`), not in the repo.*

**In short**

- **Neither strategy has an edge as built.** Both edge badges read "No edge" in the optimise stage. `pead` US makes
  6.98% a year against SPY's 14.01% (excess −7.03%). `earnings_gaps` makes 4.20% in the US (excess −9.81%) and 0.95%
  in India (excess −12.59%). Neither picks stocks better than chance: against a matched random-entry null the trades
  sit at the 62nd–86th percentile, never the 95th.
- **Both are implementation gaps, not dead methods.** An event study on stored data (US and India results days,
  2013–2021) finds the documented effects where the code does not look:
  - `pead` dates each surprise by the **SEC filing**, not the results release. 30.6% of its candidates enter 3 or more
    days after the news. It then **stops out 75% of its trades** (685 of 915) on the reaction-day low, which the
    method does not have; that stop costs 2.2 points per trade, in 8 of 9 years. And it selects on a profit-growth
    screen that shows no drift (+0.14% over 60 sessions, n = 2,539).
  - `earnings_gaps`' **ATR cap on the stop refuses 92% of US and 94% of Indian results-day reactions**, so its own
    setup S1 made 76 US trades in nine years. 87% of the strategy is now the flag setup S2. The **neglect** rule
    both originators insist on is off. Among US gaps of 10%+ on 3x volume, the ones that had not run up beforehand
    return 1.28% per trade (n = 633, 7 of 9 years positive). The ones up more than 30% lose.
- **The family's best version today:** `pead` US has the best scorecard (Sharpe 0.59, drawdown −21.4%) but no
  selection edge. **The closest thing to a working edge is a version not yet built:** post-earnings drift measured
  by the **price reaction** on the **announcement date**, in **Indian mid and small caps**. The top tenth of results-day
  reactions, using cutoffs known at the time, drifts +2.35% against the index over the next 60 sessions
  (t = 3.8, n = 1,220). It is positive in 8 of 9 years. It holds at ₹5 and ₹10 crore floors, fades at ₹20 crore and
  vanishes at the ₹50 crore floor every strategy here uses.
- **The plan:** first, five no-code `earnings_gaps` variants: neglect, its neighbours, the gap rule, and the India
  floor and ATR cap. Then three small `pead` code changes: announcement dates, a no-stop switch, and a price-reaction
  surprise with a liquidity flag. Pass criteria are fixed below, before any run.

---

## 0. Runs reviewed

Baseline = the latest non-archived optimise run of the current version with the strategy's own arguments.

| Strategy | Market | Run | Version · spec | Stage | Role |
|---|---|---|---|---|---|
| `pead` | US | **3370** | 1.4 · v1.4-1ea48216 | optimise | baseline |
| `pead` | US | 1323 | 1.2 | optimise | earlier version (trial count only) |
| `pead` | India | 684 | 1.0 | legacy (2022→) | context only. **No India optimise run exists.** Filing dates start in 2018, so an optimise run covers 2018–2021 at most. |
| `earnings_gaps` | US | **3857** | 1.10 · v1.10-05c9c7c5 | optimise | baseline |
| `earnings_gaps` | US | 3869 / 3870 / 3872 | 1.10 | optimise | variants already tested: catalyst off + rel. volume 5 + G1 off (± neglect); risk 2% |
| `earnings_gaps` | India | **3880** | 1.10 · v1.10-05c9c7c5 | optimise | baseline |
| `earnings_gaps` | India | 3881 / 3885 / 3886 | 1.10 | optimise | same variants as the US |
| `earnings_gaps` | both | 25 US + 17 India earlier runs | 1.1–1.9 | optimise | earlier versions and their variants (trial count, known choices) |

Run 1534 (US, v1.3, `--ma-col sma10`) reads 21.87% CAGR with a 0% win rate. Its trades never take the trend exit:
50 stops and 5 positions still open, valued at the end. The column was evidently missing, so the run is broken. It
is excluded from every comparison here and noted under shared fixes.

No paper book exists for either strategy (`paper_orders` holds only three momentum books).

---

## 1. `pead` — post-earnings announcement drift

### 1.1 Scorecard (run 3370, US, optimise, 2013-01-02 → 2021-12-31, 8.99 years)

| Key parameter | Value | Benchmark (SPY) |
|---|---|---|
| CAGR | 6.98% | 14.01% |
| Excess CAGR | **−7.03%** (−6.34% at standard costs) | — |
| Max drawdown · longest | −21.43% · 391 days | −34.10% |
| Sharpe · Sortino · Calmar | 0.59 · 0.54 · 0.33 | 0.88 · — · 0.41 |
| Trades (per year) | 915 (102) | — |
| Win rate | 30.3% | — |
| Mean return per trade ("R" here is return, not risk) | +1.15% (median −1.61%) | — |
| Profit factor | 1.34 | — |
| Exposure | 98.9% of days; 8.8 positions × 8% ≈ 70% of capital | 100% |
| Turnover · costs | 7.74× a year · $9,750 (10 bps a side) | — |
| Days held | mean 31.4, median 13 | — |

| Exit reason | Trades | Mean return | Total P&L | Median days |
|---|---|---|---|---|
| STOP (close under reaction-day low) | 685 (75%) | −3.2% | −$117,263 | 6 |
| DRIFT_WINDOW (60 sessions) | 157 | +14.6% | +$115,274 | 87 |
| NEXT_RESULTS | 73 | +12.0% | +$43,365 | 71 |

| Year | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|
| Return % | 12.6 | −0.7 | −4.2 | 18.4 | 24.0 | −8.6 | 21.7 | 0.2 | 4.7 |

### 1.2 Is the edge real?

| Check | Result |
|---|---|
| Trials | 2 optimise runs, both near-identical (Sharpe 0.59, 0.60). On its own trials SR₀ ≈ 0 and DSR = 0.96. Against the family's 29 US optimise trials (σ of Sharpe 0.22), SR₀ = 0.49 and **DSR = 0.62**. Inputs: daily equity returns, T = 2,266, skew −0.76, kurtosis 7.6, broken run 1534 excluded. DSR tests Sharpe > 0, not Sharpe > SPY's 0.88, which no run reaches. |
| Selection vs timing (matched null, 200 draws per trade, same entry/exit dates) | Mean trade +1.15% vs null +0.94% from liquid stocks (5–95%: 0.35–1.59) → **76th percentile**. Against the filing universe alone: null +1.08% → **62nd percentile**. No selection edge. |
| Signals vs traded | 1,547 candidates passed every entry rule (rebuilt without the price floor); 906 were bought. Bought: +0.46% excess over 60 sessions (n = 885). Skipped (slots, same-day ties): −0.76% (n = 600). The SUE tie-break helps slightly, and slots are not costing the edge. There is no edge at the signal level either. |
| Concentration | The best 5% of trades (46) made 185% of the total P&L. Without them the book lost $35,117. Best year +24.0% (2017), worst −8.6% (2018). |
| Stop cost | Held 60 sessions with no stop, the same 915 trades return +3.37% each, against +1.15% as traded and SPY's +3.01% over the same days. The stop costs **2.2 points a trade**, and the cost is positive in 8 of 9 years. Without it the picks are a market-like basket, not an edge. |

**Verdict.** No selection edge and no edge over buy-and-hold. Post-earnings drift has a strong published record,
so this is an implementation gap until a faithful version is tested (step 1.3). The literature also predicts it
is weak in liquid US stocks after 2005, which the event study confirms (§1.4).

### 1.3 The method — fidelity

Sources: Ball & Brown (1968); Bernard & Thomas (1989, 1990), the standardised-surprise (SUE) decile method: hold
about 60 trading days, with part of the drift arriving at the next announcement. Also Chan, Jegadeesh & Lakonishok
(1996) and Brandt, Kishore, Santa-Clara & Venkatachalam (2008), on the announcement-day return as a second,
independent surprise measure.

| Rule | Originators' version | This code | Kind | Matters? (evidence) |
|---|---|---|---|---|
| Event date | The results announcement (press release / earnings date) | The SEC 10-Q/10-K **filing** date (US). For candidates, the filing comes ≥3 days after the 8-K 2.02 release on 30.6% of events; for 4th quarters the median is 8 days after (75th percentile 24). | different | **High.** Candidates entering 3–7 days late have −1.32% excess at 20 sessions (n = 154). The release dates are already stored (`results_announcements`, 8-K 2.02 since 2005), and `earnings_gaps` uses them. |
| Surprise measure | SUE: the year-on-year EPS change ÷ its own standard deviation, ranked in deciles. Long the top decile (and short the bottom). | Net profit ≥25% YoY, accelerating, revenue ≥10%, top 20% of the season so far — a growth screen. SUE only breaks ties. | different | **High.** On announcement dates the code's filters show +0.14% drift over 60 sessions (t = 0.5, n = 2,539), against +0.62% for SUE decile 10 (t = 2.0, n = 2,672). |
| Decile cutoffs | From the **previous** quarter's distribution, so no look-ahead | An expanding rank within the season. The first filer passes by definition: 600 of 4,601 filings that pass the growth filters (13%) are first in their season. | different | Moderate. A tradable fix exists (prior-quarter cutoffs). |
| Price reaction | None in Bernard & Thomas. A second signal in Chan et al. and Brandt et al. | Must beat the index by 0–20% over 2 sessions | added | Supported as a *selection*: SUE top-two deciles AND reaction top-two deciles drift +1.47% (t = 2.8, n = 1,238). The 20% cap removes few (25 events). |
| Stop | None: hold the window | Close below the reaction-day low | added | **High.** 75% of trades stopped, at a cost of 2.2 points a trade (§1.2). |
| Holding / next results | ~60 trading days. Bernard & Thomas (1990) find part of the drift at the next announcements. | 60 sessions, or the close of the next filing day | similar | Low |
| Long / short | A hedge portfolio, long D10 and short D1 | Long only | simplified | Low here. US decile 1 shows no negative drift in 2013–2021 (+0.01%, n = 2,677), so a short leg would add nothing. |
| Universe | All listed stocks. The drift is largest in small and illiquid names (Chordia, Goyal, Sadka, Sadka & Shivakumar 2009). | $10M / ₹50 crore floors, and only the companies the `financials` job fetched, chosen on **today's** liquidity and trend (the caveat's outcome-selected universe) | different | **High in India** (§1.4: the drift exists at ₹5–10 crore and is gone at ₹50 crore); moderate in the US. |
| Sizing | Equal-weight deciles | 8% each, at most 15 | similar | Low. Cash drag: about 70% invested. |

**What the literature says.** The drift is among the most replicated anomalies. Its size has shrunk since
publication. Martineau (2022, *Critical Finance Review*) argues it is essentially gone in US large and mid caps
after the mid-2000s. Chordia et al. (2009) find it concentrated in illiquid stocks, where costs absorb much of it.
Forecast-based surprises (Livnat & Mendenhall 2006) give larger drift than time-series SUE. Only four quarters of
consensus are stored, so that version cannot be tested here. The expected answer is: weak in liquid US names,
stronger in less-covered markets and smaller stocks. The data agree (§1.4).

**Known choices (already decided, not re-proposed).** Year-ago figures as first published, not restated (1.0); the
reaction measured on total return (1.2); a split-correct price floor (1.3); one position per company (1.4).

### 1.4 Diagnosis — an event study on stored data

All results announcements 2013–2021 (US: 8-K 2.02, n = 37,920 events at the $10M floor; India: board meeting or
exchange broadcast). The reaction day is the higher-volume of the announcement session and the next. The drift is
measured from the close 2 sessions after the reaction to 62 sessions after, minus the index. Deciles are within
each calendar quarter (look-ahead in the cutoffs; a tradable check with prior-quarter cutoffs follows).

**US, $10M floor — drift over sessions +2…+62, by decile**

| Decile | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| SUE (n ≈ 2,660 each) | +0.01% | −0.28 | +0.42 | −0.30 | −0.31 | −0.06 | +0.60 | −0.36 | −0.09 | **+0.62** (t 2.0) |
| Price reaction (n ≈ 3,790 each) | +1.82% | +0.33 | +0.01 | −0.30 | −0.45 | −0.38 | −0.23 | +0.56 | +0.14 | **+0.96** (t 2.7) |

| US selection | Drift | t | n |
|---|---|---|---|
| All events (universe level) | +0.25% | 2.2 | 37,920 |
| The code's growth filters, announcement-dated | +0.14% | 0.5 | 2,539 |
| SUE D9–10 and reaction D9–10 | +1.47% | 2.8 | 1,238 |
| SUE D10 and reaction D10 | +2.82% | 2.4 | 327 |
| Tradable: SUE ≥ previous quarter's 80th pct and reaction ≥ its 90th | +1.66% | 1.9 | 635 |

The tradable US combination is fragile: 2020 contributes +13.2% while 2018, 2019 and 2021 are negative. The US
drift in liquid names is weak, as published. Decile 1 of the reaction is the second-best decile: losers bounce.

**India — drift by price-reaction decile, by liquidity floor (tradable: top 10% by the previous quarter's cutoff)**

| Floor (20-day traded value) | D1 | D10 | Tradable top 10% | All events | Tradable top 10%, by year 2013→2021 |
|---|---|---|---|---|---|
| ₹5 crore | −1.37% (n 1,177) | **+2.17%** (t 3.5, n 1,173) | **+2.35%** (t 3.8, n 1,220) | +0.64% | 4.9, 6.2, 5.7, 2.8, 4.1, −3.9, 2.9, 1.4, 2.4 |
| ₹10 crore | −1.39% | +1.70% (t 2.5) | +2.04% (t 2.9, n 891) | +0.43% | 3.3, 4.7, 3.9, 2.8, 1.9, −3.0, 0.3, 3.1, 4.0 |
| ₹20 crore | −1.56% | +1.32% (t 1.7) | +1.59% (t 2.0, n 650) | +0.19% | 3.6, 5.7, 2.5, 4.1, −0.4, −4.7, −0.4, 3.2, 4.9 |
| ₹50 crore (current) | −0.34% | +0.25% (t 0.3) | −0.19% (n 409) | −0.36% | — |

India reaction deciles are close to monotone at ₹5 crore: D1 −1.37% rising to D9 +2.26% and D10 +2.17%. The D10 − D1
spread is positive in all 9 years. This needs no fundamentals, so it can run on the full announcement history
(2007→) rather than the 2018→ filings. Its universe is every company with a results announcement, not the
outcome-selected `financials` list. The price panel still lacks delisted companies (survivorship), which flatters
"all events" more than the D10 − D1 spread.

### 1.5 Ranked improvements

| # | Change | Targets | Evidence | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| P1 | Date each event by the **results announcement** (`results_announcements`: earliest 8-K 2.02 within 0–120 days of the quarter end, else the filing; India: board meeting or broadcast), and measure the reaction from it | selection, avg return | 30.6% of candidates enter ≥3 days late; that cohort is −1.32% at 20 sessions (n = 154) | Removes late entries; reaction measured on the real news | Events with no 8-K (≈30% of US quarters) keep the filing date | Holds in both markets by construction (India's dates are already the announcement) | from the method (code) |
| P2 | **Drop the reaction-low stop** (expose `run(use_stop=False)` as `--no-stop`) | CAGR, avg return, exposure | 685 of 915 trades stopped; +1.15% → +3.37% per trade with no stop, positive in 8 of 9 years | CAGR toward SPY's; win rate up | Deeper drawdown (60-day holds through 2020); excess will still be about zero without P3 | Robust as mechanics; not an edge on its own | from the method (code: flag only) |
| P3 | **Select by surprise deciles with prior-quarter cutoffs**: SUE ≥ the previous quarter's 80th percentile AND reaction ≥ its 90th; drop the growth and season filters | selection edge, excess | US: code's filters +0.14% (n = 2,539) vs +1.66% tradable (n = 635) | A first real selection signal in the US | Fewer events (~70 a year) | **Fragile in the US** (2020-led, 3 negative years) | from the method + literature (code) |
| P4 | **India price-reaction drift**: an EAR-only mode (`--surprise ear`), announcement dates from 2013, floor ₹5–10 crore (`--min-turnover`) | the whole India case | +2.35% per 60 sessions (t = 3.8, n = 1,220), 8 of 9 years, plateau ₹5–10 crore | A testable India strategy on 9 years instead of 4 | Small, less liquid names; costs at 27 bps a side take ~0.5% of the 2.35% | **Robust** across years and two floors; fades at ₹20 crore | from the literature (code) |
| P5 | US liquidity floor | — | At $1M the SUE D10 drift is +1.56% but D1 is +0.69%: little spread for much more cost | — | — | — | not proposed |
| P6 | A short leg | — | US D1 shows no negative drift | — | — | — | not proposed (data contradict) |

---

## 2. `earnings_gaps` — earnings gaps and episodic pivots

### 2.1 Scorecard (optimise, 2013–2021)

| Key parameter | US (run 3857) | India (run 3880) |
|---|---|---|
| CAGR · benchmark | 4.20% · 14.01% | 0.95% · 13.54% |
| Excess CAGR | **−9.81%** | **−12.59%** |
| Max drawdown · longest | −20.26% · 808 days | −7.79% · 1,230 days |
| Sharpe · Sortino · Calmar | 0.42 · 0.39 · 0.21 | 0.27 · 0.14 · 0.12 |
| Trades (per year) | 586 (65) | 56 (6) |
| Win rate · mean R · profit factor | 38.6% · +0.075R · 1.19 | 30.4% · +0.159R · 1.40 |
| By setup | S1 76 trades +0.060R · **S2 510 (87%)** +0.082R | S1 9 +0.385R · S2 47 +0.116R |
| By exit | trend exit 485 +0.31R · stop 98 −1.06R | trend exit 44 +0.48R · stop 12 −1.02R |
| Exposure · positions | 90.4% of days · 4.1 avg (cap 10) | 27.3% of days · 0.4 avg |
| Turnover · costs | 8.29× · $4,763 | 0.85× · ₹31,607 |
| Days held | mean 23.1, median 19 | mean 24.0, median 20.5 |

| Year | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|
| US return % | 9.5 | 16.2 | −8.3 | 7.0 | 5.6 | 0.0 | 4.0 | 3.7 | 1.9 |
| India return % | 1.0 | 1.4 | −2.6 | 4.9 | −0.5 | −2.6 | −0.3 | 3.3 | 4.2 |

Funnel (US): 2.89M bars evaluated. G2 (reaction day) drops 1.81M and G1 (200-day) 1.03M; G3 (results link) drops
14,745 and G4 (stop width) 5,842. 13,949 signal bars survive. Of those, 586 trades; slots and cash refused only 718
signal bars. India: 858 signal bars → 56 trades, and slots never bound.

### 2.2 Is the edge real?

| Check | US | India |
|---|---|---|
| Trials | 28 optimise runs (27 with trades, 1534 excluded). Trial Sharpes mean 0.24, σ 0.22, max 0.55 → SR₀ = 0.46, **DSR = 0.46** (T = 2,266, skew −0.22, kurtosis 6.5) | 21 runs (19 with trades), σ 0.31, max 0.52 → SR₀ = 0.58, **DSR = 0.19** (skew −1.53, kurtosis 42.5) |
| Matched null (200 draws, same dates, liquidity floor) | Trades +0.58% close-to-close vs null +0.20% (5–95%: −0.30 to 0.72) → **86th percentile** | +1.82% vs +0.75% (−1.12 to 2.94) → **81st percentile**, n = 56 |
| Signals vs traded (1,158 US / 95 India distinct setups) | All setups: +0.77% at 20 sessions, −0.04% excess. Traded S2 +2.36% excess at 20; untraded S2 −2.28%. Those never reached the buy-stop: the trigger is the filter, not slots. | Traded S2 +3.78% excess at 20 (n = 47); untraded −2.91% (n = 38) |
| Concentration | Best 5% of trades (29) made 285% of P&L; without them −$41,452 | Best 3 trades made 197%; without them −₹171,457 |

**Verdict.** No edge over buy-and-hold and no significant selection edge. The 86th-percentile US result is
suggestive, not proof. Episodic pivots (Bonde) and Kullamägi's EP are practitioner methods with no peer-reviewed
test. Their logic is the post-announcement under-reaction of §1, taken at the largest reactions. Treat "no edge as
built" as an implementation gap first, because §2.3 shows the code mostly does not trade the setup the method describes.

### 2.3 The method — fidelity

Sources: Pradeep Bonde (Stockbee) on episodic pivots, and Kristjan Kullamägi's published EP rules: a big gap on
earnings, buy on the day (opening-range high), stop at the low of the day, sell part after 3–5 days, trail the rest
with the 10- or 20-day average. Both prefer stocks with little prior run-up and strong growth. This is practitioner
lore, not tested evidence.

| Rule | Originators' version | This code | Kind | Matters? (event-study evidence, US $10M floor unless stated) |
|---|---|---|---|---|
| Catalyst | Any big news (Bonde); earnings mostly (Kullamägi) | Results-linked only (G3), switch tested off in combos | simplified | Low: no other news history stored |
| The move | Opening gap ≥10% on very heavy volume | Close ≥10% OR open ≥5%, volume ≥3× | different | **US:** close-only moves are negative (−1.36% excess at 20 sessions, t −2.2, n = 350). **India:** close-only works (+3.68%, n = 199): results there come out in market hours. |
| Close near the high | Not required | ≥0.7 of the range | added | Cuts 69% of US EPs (1,031 → 322) with no benefit. Among neglected EPs: ≥0.7 +0.84%, 0.5–0.7 +3.15%, <0.5 +0.81%. |
| **Neglect** (no run-up before the news) | Central for both | W1 note only; G7 off (and at 30% when on) | missing | **High.** EP + 60-day run-up ≤10%: +1.28% a trade (t 2.7, n = 633, 7 of 9 years). Run-up >30%: −0.74R. Plateau at ≤0%, ≤10% and ≤20% (+1.26 / +1.28 / +1.08%). |
| Stock trend | None; neglected stocks often sit below the 200-day | G1 above the 200-day | added | Neutral once neglect is applied (above +1.44%, n = 236; below +1.32%, n = 378). Without neglect, EP above 200-day is only +0.33%. |
| Growth | Big earnings and sales growth | Not used (G6 off; "sales OR EPS" when on) | missing | Sales growth ≥25% + neglect: +2.60% (n = 120, 8 of 9 years). EPS growth ≥25% adds nothing (+0.40% x60 vs +2.99% without). |
| Entry | Day 1, opening-range high, intraday | Buy-stop above the whole day's high from the next session; ENTRY_AT_CLOSE switch | different (daily bars) | Mixed: neglected EPs, buy-stop +2.22% (n = 279 filled, 8/9 years) vs at the close +1.28% (n = 633) |
| **Stop width** | Low of the day, risk set by position size | Low of the day, but **≤1.5 ATR and ≤12%** | added | **High.** The ATR cap refuses **92% of US** (672 of 734) and **94% of Indian** results-day reactions passing G1–G2. Those it keeps do no better (US: −0.82% vs +0.39%). This is why S1 has 76 US trades in 9 years. |
| Trade management | Sell ⅓–½ after 3–5 days, stop to break-even, trail with the 10/20-day | 20-day close exit only | simplified | Untested (needs code) |
| Second entry | Later setups in the same stock | S2 flag, now 87% of trades | added | S2 is the strategy as run |
| Market | Trades EPs mainly in healthy markets (lore) | G5 off | missing | Tested in combos (best US run 3185, Sharpe 0.55) |
| Universe | Liquid; small and mid caps welcome | $10M · ₹50 crore | different | **India:** G1+G2 events return +3.55% at ₹50 crore (n = 52), +5.52% at ₹20 crore (n = 76), +4.23% at ₹10 crore (n = 112). A plateau, with 2× the sample below ₹50 crore. |

**Known choices (tested, not re-proposed alone).** Looser reaction thresholds (rel. volume 2, move 7, gap 4, close
position 0.5, 0.8; 1.3–1.5); MIN_REL_VOLUME 0 and 5; MIN_MOVE_PCT 8 and 15; MAX_STOP_ATR 2.0 (US worse: Sharpe 0.30,
738 trades; India better: 0.36, 62 trades) and 2.5; FLAG_ON=0 (US 118 trades, Sharpe −0.05); ENTRY_AT_CLOSE=1 alone
(US 218 trades, Sharpe 0.41; India 15); Kullamägi combos with REQUIRE_GAP + 10% gap + close entry + G1 off
(± growth 25, ± neglect at 30%: US 102 and 44 trades); volume-only without the results link (3869/3870: Sharpe
−0.16/−0.18); risk 2% (3872: Sharpe 0.51, scaling only). **Not yet tested alone:** neglect at 10–20%,
MIN_CLOSE_POS 0, REQUIRE_GAP at 10% with the buy-stop, MAX_STOP_ATR off, and a lower India floor.

### 2.4 Diagnosis

- **The strategy does not trade its own setup.** G4's ATR cap removes nine in ten results-day reactions, so S2 (a
  flag up to 25 sessions later) carries 87% of trades. The flag "rest" can be a continuing rally: its high may rise
  every day as long as the range stays under 12%.
- **Losers come from stops** (US 98 trades, −1.06R each, −$54k) and from unneglected, close-only reactions (above).
- **The trigger, not the portfolio, separates winners.** Slots refused 1.5% of signal bars. Setups whose buy-stop
  filled beat those that did not by 4–6 points at 20 sessions.
- **India is a sample problem, not a direction problem.** The ₹50 crore floor leaves 451 symbols and 10 S1 setups
  in 9 years. Results-day reactions there are positive at every floor tested.
- **Concentration:** 285% of US P&L in 5% of trades. Changes must be judged on more than a few large winners.

### 2.5 Ranked improvements

| # | Change | Targets | Evidence (n) | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| E1 | **Neglect gate** at 10%: `NEGLECT_GATE=1`, `NEGLECT_MAX_RUN_PCT=10` | avg R, selection, concentration | EP ≤10% run-up +1.28% vs >30% −0.74R (n = 633 vs 153) | Mean R up; fewer trades | Trade count down perhaps 30–40% | Plateau 0/10/20%; 7/9 years; holds at 20 bps a side (0.21R at a 3% stop floor) | from the method |
| E2 | **Drop close position**: `MIN_CLOSE_POS=0` (with E1) | trade count, avg R | Close ≥0.7 removes 69% of EPs, no gain | More S1 trades | Some weak-close days enter | Not monotone in close position; tested only at 0.5/0.8 in combos | from the method |
| E3 | **US gap rule**: `REQUIRE_GAP=1`, `MIN_GAP_PCT=10` (US only) | win rate, avg R | Close-only US moves −1.36% at 20 sessions (t −2.2) | Removes a losing subset | Fewer trades | US only: India's close-only moves are positive | from the method (market-specific) |
| E4 | **India floor + ATR cap**: `--min-dollar-volume 100e6`, `MAX_STOP_ATR=99` (India) | trade count, CAGR | G1+G2 events +4.2–5.5% per trade at ₹10–20 crore; the ATR cap refuses 94% | India sample 2–3× | Thinner names, wider stops | Plateau ₹10–50 crore; ATR 2.0 already moved Sharpe 0.27 → 0.36 | parameter / mechanics |
| E5 | **US ATR cap off with E1** (`MAX_STOP_ATR=99`) | S1 count | G4-refused US events no worse than kept ones (+0.39% vs −0.82%) | S1 becomes a real share | Wider stops, smaller positions | ATR 2.0 alone hurt the US (v1.9), so only with E1 | parameter |
| E6 | Sales-growth gate (revenue only, ≥25%) | avg R | +2.60% with neglect, 8/9 years, but n = 120 | Higher R, few trades | Needs code (G6 is sales OR EPS) | Fragile: n < 150 | from the method (code) |
| E7 | Kullamägi's management: partial sale after 3–5 days, stop to break-even, trail | drawdown, win rate | Untested here | Smoother equity | Caps the big winners that carry the book | Unknown | from the method (code, last) |

---

## 3. The family's best version today

**By scorecard, `pead` US (run 3370)**: Sharpe 0.59 against `earnings_gaps`' 0.42 and 0.27, and the shallowest
drawdown relative to its return. **It has no edge.** Its picks rank at the 62nd–76th percentile of a matched random
null, and its stop turns a market-like basket into a 7%-a-year book.

**The closest to a working edge is a combination neither strategy runs yet:** the drift after a large positive
**price reaction on the announcement date**, held about 60 sessions, in **Indian stocks below the current liquidity
floor**. It is the only result here that is significant (t = 3.8, n = 1,220), positive in 8 of 9 years, uses cutoffs
known at the time, and stands on a published mechanism. `earnings_gaps`' India results-day reactions (+3.5% to
+5.8% per trade at every floor) are the same effect seen through a larger threshold. In the US, the
**neglected-EP subset of `earnings_gaps`** (E1) is the best candidate: +1.28% a trade at the close, +2.22% with the
buy-stop, 7–8 of 9 years. It is still in-sample, carried by the top 5% of trades (149%), and below SPY on its own.

---

## 4. Improvement plan, ranked across the family

| Rank | Change | Strategy · market | Needs code? | Why this rank |
|---|---|---|---|---|
| 1 | E1 neglect gate at 10% (+ neighbours 0, 20) | `earnings_gaps` US and India | No | Strongest per-trade evidence the code can test today; the originators' central rule |
| 2 | E4 India floor ₹10 crore + ATR cap off | `earnings_gaps` India | No | Fixes the sample problem; a plateau across floors |
| 3 | P4 India price-reaction drift (EAR mode, announcement dates, ₹5–10 crore) | `pead` India | Yes (v1.5) | The only robust edge found; no fundamentals needed; removes the outcome-selected universe |
| 4 | P1 + P2 announcement dates and no stop | `pead` US | Yes (v1.5, same change as 3) | Fidelity; 2.2 points a trade; prerequisite for any `pead` verdict |
| 5 | E1 + E2 + E3 (+ E5) combined | `earnings_gaps` US | No | Only after each passes alone |
| 6 | P3 SUE + reaction deciles with prior-quarter cutoffs | `pead` US | Yes | Fragile in the US; run once P1–P2 are in |
| 7 | E6 sales-growth gate | `earnings_gaps` | Yes | n = 120 |
| 8 | E7 partial-sale management | `earnings_gaps` | Yes | Untested; last |

Every run below is another trial. The family has 29 US and 19 India optimise trials already. Each new variant's
Sharpe joins the deflation set, and the pass criteria include the deflated Sharpe.

### 4.1 Pass criteria (fixed now, before any run)

All against the baseline of the same strategy and market, on the optimise stage, with the run's own report
and the same matched-null procedure as §1.2/§2.2 (200 draws, same dates, liquidity floor).

| Variant | Must improve | Must not worsen beyond | Robustness checks (all required) |
|---|---|---|---|
| E1 (US) | Mean R ≥ 0.20 (baseline 0.075); profit factor ≥ 1.35; matched-null percentile ≥ 90 | Trades ≥ 200; max DD no deeper than −25%; top-5% share of P&L ≤ 175% | Neighbours 0% and 20% both mean R ≥ 0.15; mean R > 0 in ≥ 6 of 9 years; with slippage doubled (recomputed from the trades) mean R ≥ 0.15 |
| E1 (India) | Mean R ≥ 0.25; null percentile ≥ 80 | Trades ≥ 40 | Same neighbours positive; read alongside E4 |
| E4 (India) | Trades ≥ 120; CAGR ≥ 3%; mean R ≥ 0.25; null percentile ≥ 90 | Max DD no deeper than −15% | ₹20 crore floor also mean R ≥ 0.20; ≥ 6 of 9 years positive; at 27 bps a side (standard) mean R ≥ 0.20 |
| E2 / E3 / E5 (US, each on top of E1) | Mean R ≥ E1's, trades ≥ E1's × 0.8 (E3: ≥ 0.6) | Max DD no deeper than E1's − 3 points | Positive in ≥ 6 of 9 years |
| Combined US | Excess CAGR against SPY **held at the same exposure** > 0; DSR (with every family trial) ≥ 0.80 | Max DD no deeper than −25% | Passes all the above on its components |
| P1 + P2 (`pead` US) | Mean return per trade ≥ +2.5%; null percentile ≥ 80 | Max DD no deeper than −30% | Positive excess against the null in ≥ 6 of 9 years; at 20 bps a side still ≥ 75th percentile |
| P3 (`pead` US) | Null percentile ≥ 90; excess CAGR ≥ −3% | Trades ≥ 250 | No single year > 40% of P&L; ≥ 6 of 9 years positive |
| P4 (`pead` India, EAR mode) | Mean 60-session excess per trade ≥ +1.5% after 27 bps a side; null percentile ≥ 95; trades ≥ 300 | Max DD no deeper than −25% | ₹5 and ₹10 crore floors both pass; the reaction-top cutoff at 85th and 95th percentile both ≥ +1.0%; ≥ 7 of 9 years positive |

A variant that fails is reported as failed, with its numbers, and is not tuned further on the same idea.

### 4.2 Optimise-stage commands (from `scripts/`)

No-code variants (`earnings_gaps`; every `--const` changes `evaluate()`, so each rescans):

```bash
# E1 — neglect at 10%, and its neighbours, both markets
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market us    --strategies earnings_gaps --stage optimise --const NEGLECT_GATE=1 --const NEGLECT_MAX_RUN_PCT=10
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market us    --strategies earnings_gaps --stage optimise --const NEGLECT_GATE=1 --const NEGLECT_MAX_RUN_PCT=0
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market us    --strategies earnings_gaps --stage optimise --const NEGLECT_GATE=1 --const NEGLECT_MAX_RUN_PCT=20
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market india --strategies earnings_gaps --stage optimise --const NEGLECT_GATE=1 --const NEGLECT_MAX_RUN_PCT=10

# E4 — India: ₹10 crore floor with the ATR cap off, then the ₹20 crore neighbour
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market india --strategies earnings_gaps --stage optimise --min-dollar-volume 100e6 --const MAX_STOP_ATR=99
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market india --strategies earnings_gaps --stage optimise --min-dollar-volume 200e6 --const MAX_STOP_ATR=99

# E2, E3, E5 — each on top of E1 (US), only if E1 passes
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market us --strategies earnings_gaps --stage optimise --const NEGLECT_GATE=1 --const NEGLECT_MAX_RUN_PCT=10 --const MIN_CLOSE_POS=0
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market us --strategies earnings_gaps --stage optimise --const NEGLECT_GATE=1 --const NEGLECT_MAX_RUN_PCT=10 --const REQUIRE_GAP=1 --const MIN_GAP_PCT=10
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market us --strategies earnings_gaps --stage optimise --const NEGLECT_GATE=1 --const NEGLECT_MAX_RUN_PCT=10 --const MAX_STOP_ATR=99

# Combined US (only the parts that passed)
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market us --strategies earnings_gaps --stage optimise --const NEGLECT_GATE=1 --const NEGLECT_MAX_RUN_PCT=10 --const MIN_CLOSE_POS=0 --const REQUIRE_GAP=1 --const MIN_GAP_PCT=10 --const SCREEN_GATE=0
```

`backtest.py` has no cost flag (it applies the market's per-side slippage), so the doubled-cost check for
`earnings_gaps` is a recomputation from each run's `trades` table. It subtracts one more slippage per side from
every fill and every exit, then reads the report's `cagr_std_cost` column beside it. No extra run is needed.

Code changes (`pead`, after approval). One version bump (1.4 → 1.5), changelog entry, and the docs in the same change:

| Change | File · what | Changes the scan? | Docs to update |
|---|---|---|---|
| P1 announcement dates | `backtesting/pead.py` `load_events`: join `results_announcements` (8-K 2.02; India board meeting/broadcast), earliest date 0–120 days after the quarter end, fallback `filed`. Reuse `EarningsGapsStrategy._announcements` (or move it to a shared module) so there is one loader. | Yes (events) | `how_it_works` (Data), entry rule "The reaction", caveat "event date can lag" (remove), `status` |
| P2 no stop | `main()`: `--no-stop` → `run(use_stop=False)`; a `STOP_ON_REACTION_LOW` CLI default | No (exit only) | exit rule "Stop", `param_docs` |
| P3/P4 surprise mode | `--surprise {growth,sue_ear,ear}` with module constants `SUE_TOP_PCT`, `EAR_TOP_PCT` (prior-quarter cutoffs); `--min-turnover` overriding `cfg.screener.min_dollar_volume` | Yes | entry rules (filing filters per mode), `description`, `param_docs`, caveat on the universe (EAR mode does not depend on the `financials` list) |

Then `PYTHONPATH=. .venv/bin/python -m tests.test_strategy_docs` and `tests.test_strategy_versions`
(`versions.lock.json`). `pead` has no signal cache, so `signal_version` does not apply.

```bash
# after the v1.5 change
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market us    --strategies pead --stage optimise                                   # P1 alone (new default dates)
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market us    --strategies pead --stage optimise --bt '--no-stop'                  # P1 + P2
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market us    --strategies pead --stage optimise --bt '--no-stop' --bt '--surprise sue_ear'
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market india --strategies pead --stage optimise --bt '--no-stop' --bt '--surprise ear' --bt '--min-turnover 50000000'
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market india --strategies pead --stage optimise --bt '--no-stop' --bt '--surprise ear' --bt '--min-turnover 100000000'
PYTHONPATH=. .venv/bin/python -m jobs enqueue backtest --market india --strategies pead --stage optimise --bt '--no-stop' --bt '--surprise ear' --bt '--min-turnover 50000000' --bt '--cost-bps 27'
```

Because `--bt` passthroughs move no fingerprint, a `--surprise`/`--min-turnover` experiment shares the spec id of the
default run. Name the mode in the run directory (`main()` builds `name`), or make the mode and floor module
constants so they enter the fingerprint. The second is preferred: it keeps the Backtests tab honest.

### 4.3 What would justify a verify run

One verify per version, only for a candidate that passed every row of §4.1, including neighbours and doubled costs,
on its final rules. Verify pass criteria are fixed in advance: excess CAGR over the benchmark held at the same
exposure > 0, matched-null percentile ≥ 80, and mean R (or 60-session excess for `pead`) at least half the
optimise figure. For `pead` India, the verify window (2022→) is also the period of the old legacy run 684, whose
headline is known. Say so in the verify record, because it is not a clean hold-out for that market.

---

## 5. Shared fixes (proposed once, for the family)

| Fix | Applies to | Why |
|---|---|---|
| **One announcement-date loader** (`results_announcements`) for every earnings strategy | `pead` (adopt), `earnings_gaps` (already uses it in G3) | `pead`'s filing date lags the news on 30% of events; two loaders would drift apart |
| **The price reaction as a surprise measure**, computed the same way (reaction day = higher-volume of announcement day and next; excess over the index) | both | It carries the India drift and selects `earnings_gaps`' events; one definition avoids two thresholds for the same question |
| **India liquidity floor for event strategies** at ₹10 crore (strategy-level, not the market config) | both, India | Both effects live below ₹50 crore and vanish at it; the guides' own floor is ₹5 crore |
| **A universe that does not depend on today's outcome** | `pead` | The `financials` list is chosen on today's liquidity and trend; EAR mode and announcement-based events avoid it |
| **Pre-move run-up as a recorded field** (60-session return before the reaction) | both | The strongest single conditioner of earnings-gap outcomes; `pead` could report it as a diagnostic |
| Broken run 1534 (`--ma-col sma10`, no trend exits) | backtester | A run whose exit column is missing should fail, not report 21.87% CAGR; archive it |

---

## 6. What could not be determined, and what would settle it

| Unknown | Why | What would settle it |
|---|---|---|
| Opening-range entries (Kullamägi's day-1 buy) | Daily bars only | Intraday bars for results days |
| Forecast-based surprise (SUE against consensus) | Four quarters of estimates stored | A point-in-time estimates history |
| Before-open vs after-close release timing | Not stored; inferred from the higher-volume day | 8-K acceptance timestamps |
| Delisted companies | Prices are today's listed names (survivorship) | Point-in-time listings |
| India fundamentals before 2018 | `quarterly_results` India starts 2018 | Older filings; until then India `pead` is EAR-only |
| Kullamägi's partial-sale management | Not implemented | E7, after E1–E5 |
| Whether US PEAD survives costs at all | Weak, fragile in this window | P3 on optimise, then forward data |

The event study is an approximation, not a backtest. It uses closes on back-adjusted prices, no slots, the
reaction day picked by volume, and no costs except where stated. Its in-quarter decile cutoffs carry look-ahead;
the "tradable" rows use prior-quarter cutoffs. It ranks hypotheses. The runs in §4.2 decide them.

---

## 7. The paper-trading gate

Strategies refined before October 2026 have no clean historical hold-out, so forward data is the final test.
Neither strategy has a paper book today.

| Candidate | Paper record that would confirm the edge |
|---|---|
| `earnings_gaps` US with E1 (neglected EPs) | At least **40 closed trades over at least 9 months** (about three results seasons). Mean R ≥ +0.15 after real fills, profit factor ≥ 1.3, max drawdown ≤ 12% at 1% risk per trade, no single trade > 40% of P&L. Buy-stop fills within 0.3% of the modelled trigger on average. Log every G3 refusal caused by the weekly announcement refresh (the live-lag caveat). |
| `pead` India, EAR mode (after P4 passes) | At least **60 closed trades across at least two results seasons (≥ 6 months)**. Mean 60-session excess over the Nifty 500 ≥ +1.0% after costs. Also log the bottom-decile reactions (not traded): their excess should be below the top decile's, so the spread is visible forward, not only the long book. Fills at the close of R+2 within 0.5% of the modelled price. |
| `earnings_gaps` India with E4 | Too few events (~12 a year) for a stand-alone gate. Paper it alongside `pead` India and judge the two together after 12 months. |

A paper record that misses these levels is a failure of that version, reported as such. The next version starts
its own record.
