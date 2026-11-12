# Strategy family review — 7. Shorts and mean reversion

*Review of 2026-11-12. Strategies: `mean_reversion` (Connors RSI(2)), `stage4_shorts` (Weinstein),
`parabolic_short` (Kullamägi). Brief: `research/strategy-family-review-briefs.md` §7. Procedure:
`.claude/skills/backtest-review/SKILL.md`. Analysis and plan only: no code edited, no job queued, nothing
committed.*

**Data rules followed.** Only optimise-stage runs (2013-01-01 → 2021-12-31) were read. No verify-stage run
exists for any of the three (`verify_runs` is empty for them), and none was opened. Legacy runs are quoted
only as context. Every extra figure below comes from stored prices up to 2021-12-31. The working scripts are
in the session scratchpad, not in the repository.

**In short**

- **None of the three has an edge as built.** All three lose to buy-and-hold. Two of them also lose money
  outright. None passes its own pre-set criterion.
- **`mean_reversion` is closest to a working edge, and it is losing it in the plumbing.** Across all
  479 US signals (n overlaps), the raw RSI(2) signal beats a random entry on the same series by
  **+0.17% a trade** (t ≈ 1.9). The result holds for thresholds 5–15. The backtest throws this away in
  three ways:
  - a 10 bps cost, about 60% of the gross gain per trade;
  - a 2-slot cap whose **skipped signals beat the traded ones** (US +0.37% vs +0.29%; India +0.50% vs
    +0.35%);
  - an oversold-first ranking that fills the slots with XLP and XLU.
- **`stage4_shorts` has no selection edge in this window, and its market filter points the wrong way.**
  Its trades did worse than random liquid shorts (US 24th percentile, India 16th). Its failed-rally
  signals made money for the short only when the index was *not* weak. That is because every 2013–2021
  sell-off reversed in a V. The window holds no Weinstein-style Stage 4 bear market, so it cannot test the
  method. The current version (1.4, new stage model) has never been run.
- **`parabolic_short` picks the right stocks but enters and stops badly.** Its shorts beat random liquid
  shorts at the **100th percentile** (+0.70% vs −0.70% a trade). The loss comes from three things:
  - the large-cap tier, mostly 2020 crash rebounds rather than parabolic runs;
  - stops under 3% (−0.58R, n = 74);
  - 25 gap-throughs worth −67R.
  The small-cap tier (run of 300% or more) made **+0.34R a trade, n = 105**. But five trades made 66% of
  that R, and borrow is assumed.
- **Shared fixes come first.**
  - `--const` is silently ignored for all three runners: only `--bt` flags reach them.
  - The Stage 4 hedge is judged against a US long book that itself made −2.1% a year with a −80%
    drawdown in this window.
  - Short-side rules need a window that contains a bear market.

---

## 0. Runs reviewed

| Strategy | Market | Run id | Version (current?) | Stage | Overrides | Role |
|---|---|---|---|---|---|---|
| mean_reversion | US | 1353 | 1.2 (current) | optimise | none | **baseline** |
| mean_reversion | India | 1351 | 1.2 (current) | optimise | none | **baseline** |
| mean_reversion | both | 1257/1258, 1333–1338 | 1.1 | optimise | none, `--rank vol`, `--trend off`, both | variants already tested |
| stage4_shorts | US | 1195 | 1.1 (current is 1.4) | optimise | none | **baseline** (latest US optimise run) |
| stage4_shorts | India | 1307 | 1.3 (current is 1.4) | optimise | none | **baseline** (latest India optimise run) |
| stage4_shorts | both | 1167–1173, 1199–1201, 2926–2935, 3422, 3426 | 1.0–1.1 | optimise | `--entries A`, `--entries AB`, `--no-market-filter` | variants already tested |
| parabolic_short | US | 1826 | 1.0 (current) | optimise | `--borrow-pct 15` (= the base case) | **baseline** |
| parabolic_short | US | 1827, 1828 | 1.0 | optimise | borrow 0%, 100% | cost sensitivity |

**Stage 4: the baseline's rules differ from today's code.** The baseline runs predate two versions:

- **1.3:** signals read total-return prices, so a demerger no longer counts as a breakdown.
- **1.4:** Stage analysis 2.11 rebuilt `stage_series`. Stage 4 now also starts on a close below support and
  no longer waits for the line to fall.

In the US, 1.2 and 1.3 were never run either. Section 2's signal-level figures were recomputed with
today's code (1.4 stage model), so they preview the current rules.

**Trials counted** (each optimise run is an attempt):

| Strategy | Optimise runs | Plus legacy | Used for the deflated Sharpe |
|---|---|---|---|
| mean_reversion | 10 | 12 more (3 measures × 2 caps × 2 markets, mixed windows) | N = 10 (optimise only; with the legacy runs SR₀ only rises) |
| stage4_shorts | 18 | — | N = 18 |
| parabolic_short | 3 (one rule set at three borrow fees) | — | N = 3 |

---

## 1. `mean_reversion` — Connors RSI(2) on index series

### 1.1 Scorecard (optimise, v1.2)

| Key parameter | US (1353) | India (1351) |
|---|---|---|
| CAGR | 0.50% | 0.59% |
| Benchmark CAGR | 14.01% (SPY) | 13.54% (Nifty 500) |
| Excess CAGR | −13.51% | −12.95% |
| Selection (vs index at same exposure) | −1.12 | −1.51 |
| Max drawdown / longest | −8.7% / 1,093 days | −5.2% / 1,078 days |
| Sharpe / Sortino / Calmar | 0.15 / 0.09 / 0.06 | 0.19 / 0.10 / 0.11 |
| Trades (per year) | 276 (30.7) | 209 (23.2) |
| Win rate | 66.3% | 64.1% |
| Average return per trade, net | +0.17% | +0.21% |
| Profit factor | 1.28 | 1.32 |
| Exposure (days with a position) / average invested | 26.1% / ≈10% | 20.6% / ≈8% |
| Turnover / costs paid | 7.68× / $7,221 (14% of starting equity) | 5.83× / ₹211,054 (11%) |
| Average hold | 4.5 calendar days | 4.6 calendar days |
| Result by exit | MEAN_REVERTED 275 (+0.00 "R"), TIME_STOP 1 | MEAN_REVERTED 206, TIME_STOP 3 (−0.05) |

The "R" column in this strategy's trades is the fractional return, because the strategy has no stop.

### 1.2 Is the edge real?

**Trials and deflated Sharpe.** N = 10 optimise trials. The trials' Sharpe ratios have a standard
deviation of 0.11 (annualised), which gives SR₀ ≈ 0.18. Inputs are daily returns from the `equity` table
(US T = 2,266; India T = 2,217).

| Run | Sharpe | Skew / kurtosis | PSR (> 0) | Deflated Sharpe |
|---|---|---|---|---|
| US 1353 | 0.15 | −1.32 / 24.0 | 0.68 | **0.47** |
| India 1351 | 0.19 | −0.15 / 42.5 | 0.71 | **0.51** |

Neither is distinguishable from the best of ten tries.

**Edge source: timing vs selection.** The control is a random entry, matched to each signal, on the same
series, on a random day above its 200-day, held for the same number of sessions (500 draws per series).
This uses all signals, before slots and costs:

| Market | Signals | Mean per trade (gross) | Null mean | Excess per trade | Notes |
|---|---|---|---|---|---|
| US | 479 | +0.33% | +0.14% | **+0.19%** | QQQ, IWM and XLB at the 91st–98th percentile; XLU at the 12th and XLP at the 21st |
| India | 351 | +0.42% | +0.20% | **+0.22%** | Bank at the 90th percentile; IT and Pharma at the 51st–54th |

Held-day return is 2–4 times the series' drift. SPY earns 0.10% a held day against 0.05% unconditional;
QQQ earns 0.20% against 0.08%.

**There is a timing edge at the signal level. The book does not capture it.**

**Plateau across thresholds.** These figures are excess over the series' drift for the same hold, and the
signals overlap, so the t-values are optimistic.

| RSI(2) below | US n | US excess | US t | India n | India excess | India t |
|---|---|---|---|---|---|---|
| 2 | 154 | +0.04% | 0.2 | 161 | +0.55% | 3.5 |
| **5 (shipped)** | 479 | **+0.17%** | 1.9 | 351 | **+0.25%** | 2.3 |
| 10 | 931 | +0.10% | 1.7 | 602 | +0.04% | 0.4 |
| 15 | 1,363 | +0.10% | 2.0 | 817 | +0.01% | 0.1 |
| 25 | 2,004 | +0.05% | 1.2 | 1,168 | +0.00% | 0.0 |

- **US:** a plateau from 5 to 15.
- **India:** a peak at 2–5 that vanishes by 10. It is fragile.

**Signals vs traded.** Every signal (2-slot cap removed) was matched to the baseline's trades:

| Market | Traded n / mean (gross) | Skipped n / mean (gross) |
|---|---|---|
| US | 257 / +0.29% | 222 / **+0.37%** |
| India | 198 / +0.35% | 153 / **+0.50%** |

The slot cap and the "most oversold first" ranking cost edge.

- **US:** the book traded XLP 35 times (−0.08% net) and XLU 28 times (−0.36%), against SPY 13 times and
  QQQ 14 times.
- **India:** the gap is wider still.

**Costs.** At 10 bps a side the round trip is 0.20%. That is about 60% of the US gross mean per trade.
The costs paid ($7,221 over 9 years, about 1.5% of equity a year) are larger than the US selection gap
(−1.12 a year). At a realistic cost for SPY-class funds (about 1–2 bps a side), selection would be near
zero or slightly positive. That figure is computed, not run.

**Concentration.** The best 5% of trades made 97.7% of total P&L in the US and 93.0% in India. With an
average of +0.2%, the total is a small number, so that ratio is mostly a symptom of the thin margin.

| Year | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|
| US signals, mean % (n) | +0.77 (42) | +0.59 (60) | +0.74 (45) | +0.45 (47) | +0.46 (57) | **−1.11** (52) | +0.55 (50) | **−0.47** (46) | +0.75 (80) |
| India signals, mean % (n) | +0.09 (45) | +0.53 (47) | **−0.37** (38) | +0.81 (21) | +0.48 (39) | −0.10 (35) | +0.24 (27) | +1.07 (33) | +0.87 (66) |

The US loses only in the two sudden-shock years (February 2018, February 2020), which is the documented
tail of a no-stop dip-buy.

**Verdict.** There is a small, plausible timing edge at the signal level in the US, and a weaker one in
India, but no portfolio edge as built. Connors's rule has a strong documented record, though
(Connors & Alvarez's own tests, 1990s–2007). That record decayed after 2009: this repository's Learn
study shows SPY at +1.20% a signal for 1993–2009 against +0.31% for 2010–2026. So treat the result as an
**implementation gap first**:

- costs;
- slot allocation;
- universe composition.

Retire the strategy only if a faithful, cost-realistic version still fails.

### 1.3 Fidelity check (Connors & Alvarez, *Short Term Trading Strategies That Work* 2008; *High Probability ETF Trading* 2009)

| Rule | Connors | This code | Kind | Plausibly matters? |
|---|---|---|---|---|
| Trend filter | Close above the 200-day SMA | Same | — | — |
| Entry | RSI(2) < 5 (he also tests < 2 and < 10); buy at the close | Same, at the close | — | — |
| Exit | Close above the 5-day SMA (STTSW); RSI(2) > 65/70 (HPETF) | Either one | Same | — |
| Stops | None ("stops hurt") | None | Same | — |
| Time stop | None | 10 sessions | Added | No (binds 1–3 times in 9 years) |
| Catastrophe exit | None | Close below the 200-day | Added | Small; `--trend off` already tested (worse) |
| **Scaling in** | HPETF's TPS rule and the "aggressive" variants add units as the price closes lower (e.g. 10/20/30/40%). His best published ETF results use scale-in | One unit, no adds | **Missing** | **Yes.** It moves capital to the deepest dips, where the per-trade return is largest (India RSI < 2: +0.70%) |
| Cumulative RSI / R3 | Variants he published as stronger filters | Missing | Missing | Possibly; a variant, not the core |
| **Universe** | SPY, QQQ, DIA, IWM; HPETF adds about 20 liquid ETFs, including international and sector funds | SPY, QQQ, IWM + 11 sector SPDRs (US); 10 index series (India) | Different | **Yes.** Defensive sectors lose (XLU −0.32% gross, XLP −0.08%) |
| **Capital per signal** | Tests are per trade, fully invested on each signal | 25% per signal, at most 2 at once, about 10% average invested | **Different** | **Yes, for the portfolio metric.** It is why skipped signals beat traded ones |
| Ranking when several fire | Not part of the method (each ETF tested on its own) | Lowest RSI first | Added | Yes: it picks low-beta series (changelog 1.1) |
| **Costs** | Commission-only era tests | 10 bps a side | Different | **Yes: 60% of the gross edge** |

**Known choices, not re-proposed.**

- `--rank vol` and `--trend off` were tested in 1.1. Rank vol was neutral; trend off was worse.
- The liquidity check is 1.2.
- The 12 legacy runs varied the measure (RSI2, Bollinger, Double 7s) and the position cap (1 or 3). All
  were negative.

**Literature.**

- *Tested:* short-horizon reversal in stocks (Jegadeesh 1990; Lehmann 1990). Nagel (2012) ties reversal
  returns to the price of liquidity provision, highest in high-volatility markets.
- *Connors' own published backtests:* the RSI(2) rule on US indices.
- *Practitioner lore, widely repeated but untested here:* the edge on index ETFs persisted after 2010,
  smaller.
- *This repository's Learn study (stored data):* SPY signals are much weaker after 2010.

The rule has no stop and buys falling markets. Its known failure is a shock inside an uptrend (February
2018, February 2020), which matches the two losing US years above.

### 1.4 Diagnosis

| Weak parameter | Cause in the data | Evidence (n) |
|---|---|---|
| Excess CAGR | Structural: 8–10% average invested. A timing rule with about 5% of days in a trade per series cannot beat buy-and-hold standalone | Exposure 26%/21% of days |
| Selection | Costs about 1.5%/yr against a −1.12 gap; slot cap and ranking pick the weakest series | Costs $7,221; skipped beat traded (222 / 153 skipped) |
| Average return per trade | 10 bps × 2 = 0.20% against a +0.33% gross mean | 479 US signals |
| Tail | Shock years 2018 and 2020 | 52 and 46 US signals |

### 1.5 Improvements, ranked

| Priority | Change | Parameter it targets | Evidence (run, numbers, n — or source) | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| 1 | Cost at a realistic level per instrument: 2 bps a side for US funds, measured as spread plus commission; India index futures about 3–5 bps a side plus STT. Keep 10 bps as the stress level | Selection, average return per trade | 1353: costs $7,221 > the selection gap; gross +0.33%/trade on n = 479 | US selection from −1.1 to about 0 / +0.2 | None to the rules; honest only if the cost estimate is | Robust: the 10 bps level stays as the stress test | Mechanics (`--bt '--cost-bps 2'`) |
| 2 | Take every signal: equal small slices, enough slots that a signal is never skipped (e.g. 14 slots × 7% US, 10 × 10% India) | Selection, trade count | Skipped +0.37% vs traded +0.29% (US), +0.50% vs +0.35% (India) | Average return up; exposure up about 2× | More simultaneous positions in correlated dips (2018, 2020) | Holds in both markets; the threshold plateau holds 5–15 (US) | Mechanics (`--bt '--max-positions 14 --position-pct 7'`) |
| 3 | Universe faithful to Connors: broad funds plus cyclical sectors; drop the defensive XLU/XLP (US) | Average return per trade | XLU 31 signals −0.32%, XLP 45 −0.08% (gross, in-sample) | +0.05–0.10%/trade | Fewer signals; picked on in-sample per-series results | **Fragile** (per-series n 31–45, one window) | New rule (universe constant) |
| 4 | Scale-in (TPS-style: add on a lower close, up to 3 units) | Average return per trade | From the method (HPETF); RSI < 2 India +0.70%/trade (n = 161), but US RSI < 2 only +0.19% (n = 154) | Bigger capital at the deepest dips | Larger worst trade; shock years worse | Untested here; contradicted in the US | From the method (code) |
| 5 | Use as an overlay on a long book (lever the book on signals), not standalone | Excess CAGR | A standalone timing rule cannot beat B&H at 10% invested | Turns a +0.2%/trade timing edge into book return | Leverage; margin | Needs its own design | Mechanics / new runner — later |

### 1.6 Pass criteria (fixed before any run)

Change 1+2 combined, optimise, both markets:

- **(a)** selection ≥ 0 in both markets at the realistic cost;
- **(b)** net return per trade ≥ +0.10% in both markets, and still > 0 at 10 bps a side;
- **(c)** net per-trade return positive in at least 6 of 9 years in each market;
- **(d)** max drawdown no deeper than −15%;
- **(e)** the result holds at `--rsi-entry 10`: selection ≥ −0.2 and per trade > 0. That is the
  neighbouring value.

Change 3 or 4 enters only if 1+2 passes, and must add ≥ +0.05%/trade in both markets without breaking (d).

---

## 2. `stage4_shorts` — Weinstein Stage 4 shorts

### 2.1 Scorecard (optimise; US v1.1, India v1.3 — the current version 1.4 has no run)

| Key parameter | US (1195, v1.1) | India (1307, v1.3) |
|---|---|---|
| CAGR | −2.04% | −4.47% |
| Excess CAGR | −16.05% | −18.00% |
| Max drawdown / longest | −22.1% / 1,499 days | −35.5% / 2,066 days |
| Sharpe / Sortino / Calmar | −0.36 / −0.18 / −0.09 | −1.15 / −0.60 / −0.13 |
| Trades (per year) | 215 (23.9) | 280 (31.1) |
| Win rate | 23.7% | 22.5% |
| Average / median R | −0.26 / −0.75 | −0.39 / −0.54 |
| Profit factor | 0.63 | 0.38 |
| Exposure / average short | 23.4% of days / 7.8% of equity | 32.7% / 6.8% |
| Turnover / costs | 2.59× / $3,213 | 3.14× / ₹179,994 |
| Average hold | 10.0 sessions | 8.3 sessions |
| R by exit: STOP | 97 trades, −1.20 | 113 trades, −1.15 |
| R by exit: TREND | 70 trades, +0.62 | 86 trades, +0.19 |
| R by exit: STAGE | 29 trades, −0.42 | 58 trades, −0.38 |
| R by exit: TRAIL | 19 trades, +1.52 | 23 trades, +1.11 |
| CAGR at ×0.5 / ×2 costs | −1.75% / −2.62% | −3.94% / −5.51% |
| Hedge: 20% sleeve DD vs 20% cash | −70.3% vs −70.7% (pass needs ≥ 2 points better) | −51.7% vs −51.3% (worse) |

### 2.2 Is the edge real?

**Trials and deflated Sharpe.** N = 18. The trials' Sharpe ratios have a standard deviation of 0.39,
which gives SR₀ ≈ 0.72. The deflated Sharpe is **0.001 (US)** and **0.000 (India)**. Even the PSR for a
Sharpe above zero is only 0.14 in the US.

**Selection vs random.** The control is random liquid stocks shorted on the same entry dates over the same
dates (200 draws). The "weak" pool is the liquid stocks below a falling-structure 200-day (close and
50-day below the 200-day).

| Market | Trades | Trades' mean short return | Null: liquid | Null: weak | Percentile vs liquid / weak |
|---|---|---|---|---|---|
| US | 215 | −0.81% | −0.51% | −0.25% | 24th / 10th |
| India | 280 | −0.93% | −0.62% | −0.61% | 16th / 19th |

**No selection edge.** The picks did *worse* than shorting a random weak stock on the same day.

**Every signal, current code (v1.4 stage model).** These are short returns: positive means the short made
money. B signals fire on every touching day, so n overlaps heavily.

| Market | Entry, market state | Signals | Short return, 20 sessions | Short return, 60 sessions | Hit 1R against within 20 sessions |
|---|---|---|---|---|---|
| US | B, index weak (the shipped filter) | 2,603 | −0.72% | −3.83% | 69% |
| US | B, index not weak | 20,273 | −0.01% | −2.17% | 57% |
| US | A, index weak | 1,599 | −1.60% | −5.38% | 31% |
| India | B, index weak | 793 | −2.39% | **−10.89%** | 63% |
| India | B, index not weak | 1,031 | +2.31% | **+3.56%** | 52% |

**The market filter, decimated to one B signal per stock per 4 weeks** (US n = 6,141; India n = 489):

| Filter on the signal date | US n | US 60-session short return | India n | India 60-session short return |
|---|---|---|---|---|
| Below the 200-day OR the 200-day falling (shipped) | 880 | −4.76% | 228 | −8.21% |
| Below AND falling (closer to Weinstein's "market in Stage 4") | 279 | −10.34% | 83 | −3.37% |
| Index 50-day below its 200-day | 1,231 | −1.79% | 179 | −2.71% |

**Why this happens.** In 2013–2021 every index weakness was a V: 2015–16, Q4 2018, March 2020. Losers
rebound hardest right after a fall, which is the momentum crash Daniel and Moskowitz (2016) document.
The stricter the filter, the more of those rebounds it shorts. **This window contains no sustained
Stage 4 bear market**, the condition Weinstein's shorts are built for (2000–02, 2008, 2022). The
2013–2021 optimise window therefore cannot show the method's edge either way. That is a limit of the
window, not a verdict on Weinstein.

**Signals vs traded.** The traded B-and-filter signals were no better than the untraded ones:

- **US:** 60-session short return −5.1% (n = 174 matched) vs −3.7% (n = 2,429).
- **India:** −8.1% (n = 286) vs −12.5% (n = 507).

Slots are not the problem.

**Concentration.**

| Market | Total R | Best 5% of trades | Sum of positive R |
|---|---|---|---|
| US | −56.1 | +53.7 | +89.0 |
| India | −110.1 | +37.8 | +60.5 |

| Year | 2013 | 2015 | 2016 | 2018 | 2019 | 2020 |
|---|---|---|---|---|---|---|
| US, mean R (n) | — | +0.20 (39) | −0.40 (65) | −0.04 (40) | −0.68 (44) | −0.25 (27) |
| India, mean R (n) | −0.61 (31) | −0.19 (11) | −0.41 (40) | −0.28 (35) | −0.24 (62) | −0.48 (101) |

**Verdict.** No selection edge, no timing edge, no hedge value in this window. Weinstein's method has a
long practitioner record but no published statistics: his book shows examples. Two things count against
retiring it on this evidence:

- the fidelity gaps below;
- the window's lack of a bear market.

So it is an **implementation-and-window gap, not yet a failed method**.

### 2.3 Fidelity check (Weinstein, *Secrets for Profiting in Bull and Bear Markets*, 1988, ch. 7)

| Rule | Weinstein | This code | Kind | Plausibly matters? |
|---|---|---|---|---|
| **When to short** | The *market* itself in Stage 4 (the "forest to the trees" approach): index below a declining 30-week MA, a weak market-breadth picture | Index below its 200-day **or** the 200-day lower than 20 sessions ago (daily, either condition) | Simplified / looser | **Yes**, but the data say the window cannot reward any version of it (above) |
| **Sector** | Short weak stocks in weak *groups*; the group's own chart in Stage 4 | Missing | **Missing** | Likely: group weakness is half his selection |
| **Primary entry** | The **initial breakdown** below the support of a Stage 3 top, the 30-week MA flattening or turning down; or the first pullback to the breakdown point | B: a rally to the line after **≥ 40 sessions in Stage 4**; A: a 52-week closing low on 1.5× volume | **Different** | **Yes.** He warns against shorting late in Stage 4 after a large fall; B is late by construction, and A uses a 52-week low, not the top's support |
| Volume | Not required on a breakdown ("a stock can fall of its own weight") | A requires 1.5×; B none | Added threshold (A) | Small |
| Relative strength | Poor and falling; negative-zone RS | 63-session return below the index | Simplified | Small |
| **Initial stop** | Above the prior rally peak and above the 30-week MA (a wide stop) | B: 10-session high + 0.25 ATR, often only 1–5% away | **Tighter** | **Yes.** About half the trades exit by stop or stage within 5 sessions (US 45%, India 51%); stops under 3% hit 1R against 73–80% of the time |
| **Trailing** | A buy-stop moved down above each lower rally peak, and above the 30-week MA; hold while the MA declines | Close above the 50-day; 20-day-high trail from session 20; 60-session time stop | **Tighter / added** | **Yes.** The winners are the long holds (US 20–60 sessions +1.93R, n = 32; India +1.01R, n = 30); the 50-day exit cuts them |
| Stage exit | A weekly close above the 30-week MA | Same | — | — |
| Avoid | Crowded shorts and thin stocks | Short interest not stored | Missing (data) | Unknown |

**Known choices, not re-proposed.** These were all tested in 1.0–1.1:

- entry A alone (US −0.04% CAGR, the best US run; India −0.86%);
- entries A+B;
- no market filter (US worse, −8.25%; India −1.72%, the only variant to clear the sleeve drawdown test,
  failing at stress cost).

The 1.1 gap-geometry fix and the 1.2–1.3 corporate-action fixes are mechanics.

**Literature.**

- *Momentum's short side:* Jegadeesh and Titman (1993); the 52-week-high effect, George and Hwang (2004).
- *Losers rebound hardest after market falls:* Daniel and Moskowitz (2016). This is the failure mode
  measured above.
- *This repository's Learn event study (2012–mid-2025):* failed rallies lagged the index by a median 2–3%
  over 60 sessions. That is a relative effect, not an absolute short return, before stops and costs.
- *Weinstein's own record:* examples, not statistics.

### 2.4 Diagnosis

| Weak parameter | Cause in the data | Evidence (n) |
|---|---|---|
| Average R, win rate | Tight stops: half the trades are stopped or stage-exited within 5 sessions | US 45% of 215; India 51% of 280 |
| Average R | Winners are cut early by the 50-day trend exit; R by exit: TREND +0.62 vs TRAIL +1.52 (US) | 70 / 19 trades |
| Selection | Late-Stage-4 entries in a window of V-rebounds | Trades at the 10th–24th percentile of random shorts |
| Hedge value | Filter on in rebounds; the sleeve is 7–8% short on average | Sleeve tables, 1195 / 1307 |
| Hedge reference | The US long book it is blended with made −2.11%/yr with a −79.9% drawdown | momentum_baseline run 1165 |

### 2.5 Improvements, ranked

| Priority | Change | Parameter it targets | Evidence (run, numbers, n — or source) | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| 1 | Run the **current version (1.4)** baseline in both markets before anything else | All | No 1.4 run exists; the stage model changed | A valid baseline | — | n/a | Mechanics (no code) |
| 2 | **Weinstein's stop and trail:** initial stop above the prior rally peak and the 30-week line; trail only above each lower rally peak / the line; drop the 50-day close exit and the 20-day trail | Average R, win rate | 45–51% of trades exit within 5 sessions; long holds +1.0–1.9R (n = 30–32); TREND/TRAIL R | Fewer whipsaw stops, longer winners | Fewer, larger-risk trades; bigger give-back | Holds in both markets (same pattern); untested at neighbouring values | From the method (code, rescan not needed for exits only) |
| 3 | **Weinstein's entry:** the first breakdown below a Stage 3 top's support (the 1.4 stage model now marks it), and the first pullback to that level; drop the ≥ 40-session lateness | Selection | From the method; B is late by construction; the 1.4 stage model starts Stage 4 at the support break | Earlier, larger moves | More false breakdowns in bull years | Untested | From the method (code, rescan) |
| 4 | Sector / group in Stage 4 as a gate | Selection | From the method; group RS is stored (`group_rs_history`) | Fewer, better shorts | Fewer trades | Untested | From the method (code) |
| 5 | Judge on a window that contains bear markets: a pre-sample diagnostic stage 2000–2012 (US: 1,650–2,680 stored symbols a year), kept separate from optimise and verify | Validity of every figure | 2013–2021 has no sustained bear; the filter result inverts with the window | A meaningful test of a bear-market strategy | Survivorship is worse before 2013; it needs a new stage | n/a | Shared fix (code: `windows.py`) |
| 6 | Market filter AND instead of OR / "index 50-day below its 200-day" | Hedge value | **Contradicted here:** AND is worse in the US (−10.3% vs −4.8% at 60 sessions) | — | — | Window-dependent | Do not run in optimise alone; test only in the pre-sample window |

### 2.6 Pass criteria (fixed before any run)

These keep the strategy's own criterion (written 2026-10-25) and add:

- **(e)** average R ≥ 0 at base cost in both markets;
- **(f)** the share of trades exiting within 5 sessions below 30%;
- **(g)** trades beat the matched weak-stock null (above its 60th percentile).

Change 2 must improve average R by ≥ +0.15R in both markets over the 1.4 baseline and keep trades ≥ 100
per market. The hedge criterion (a)–(d) is judged against the family-5 long book (shared fix S2), not
against `momentum_baseline` US.

---

## 3. `parabolic_short` — Kullamägi parabolic short (US only)

### 3.1 Scorecard (optimise, v1.0, US)

| Key parameter | Borrow 15% (1826, base) | Borrow 0% (1827) | Borrow 100% (1828) |
|---|---|---|---|
| CAGR | −1.55% | −0.94% | −4.97% |
| Excess CAGR | −15.56% | −14.95% | −18.98% |
| Max drawdown | −18.5% | −14.8% | −38.0% |
| Sharpe | −0.24 | −0.13 | −0.83 |
| Trades | 398 | 399 | 397 |
| Win rate | 42.3% | 42.2% | 39.6% |
| Average R | −0.095 | −0.067 | −0.273 |

Base run (1826), further figures:

| Measure | Value |
|---|---|
| Sortino / Calmar | −0.15 / −0.08 |
| Longest drawdown | 1,030 days |
| Trades per year | 44.2 (302 of 398 in 2020–21) |
| Median R | −0.49 |
| Profit factor | 0.89 |
| Exposure / average short | 30.3% of days / 4.1% of equity |
| Costs paid | $11,304 |
| Average hold | 3.6 sessions |
| R by exit | STOP 231 (−1.15), TARGET 141 (+1.48), TIME 25 (+0.74) |
| Tiers | large 293 trades, −0.25R, 38% win; small 105 trades, **+0.34R**, 55% win |
| Hedge view | in the index's 12 worst months the book made −0.27%/month; correlation with the index −0.02 |

### 3.2 Is the edge real?

**Trials and deflated Sharpe.** N = 3 (one rule set at three fees). SR₀ ≈ 0.32; DSR **0.05**.

**Selection vs random.** The control is random liquid stocks shorted from the same close to the same exit
date (200 draws).

| Trades | Trades' mean short return | Null: liquid | Null: extended (close > 1.3 × 50-day) | Percentile vs liquid / extended |
|---|---|---|---|---|
| 398 | **+0.70%** | −0.70% | −0.63% | **100th / 96th** |

**The stock choice has an edge. The R is lost elsewhere.**

**Every signal (678 candidates, current code).** Short return: positive means the short made money.

| Group | n | 5 sessions | 20 sessions | 60 sessions | Median 20 | Hit 1R against within 20 |
|---|---|---|---|---|---|---|
| Large tier, all | 557 | +0.97% | −4.54% | −15.51% | −2.85% | 77% |
| — of which 2020 | 385 | +2.34% | −6.14% | — | −4.60% | — |
| — outside 2020 | 172 | −2.11% | −0.93% | — | +3.77% | — |
| **Small tier, all** | 121 | +2.82% | **+2.81%** | **+13.86%** | **+18.10%** | 59% |
| Traded | 398 | +0.18% | −3.34% | −8.80% | +2.18% | 73% |
| Skipped (mostly the risk budget, 269) | 280 | +2.87% | −3.10% | −12.22% | −3.09% | 75% |

- Large-cap runs of 50% keep running over 20–60 sessions: momentum, not exhaustion.
- 2020 alone holds 426 of 678 signals. Most of its large-tier "parabolas" are rebounds off the March
  crash low, not speculative blow-offs.
- Skipped and traded signals are similar at 20 sessions: slots are not the problem.

**Run size.** Average R rises with the size of the run:

| Run of at least | Trades | Average R |
|---|---|---|
| 100% | 155 | +0.17 |
| 200% | 110 | +0.28 |
| 300% | 106 | +0.33 |
| 500% | 37 | +0.59 |

**Stop width (traded):**

| Stop distance | 0–3% | 3–5% | 5–8% | 8–12% | 12–30% |
|---|---|---|---|---|---|
| Trades | 74 | 74 | 99 | 59 | 92 |
| Average R | **−0.58** | +0.04 | −0.02 | −0.01 | +0.05 |

**Gaps.** 25 stops filled worse than −1.5R and summed to −67.1R, more than the strategy's total
(−37.8R). The worst was ASTC at −9.6R.

**Concentration.**

- **All trades:** the best 5% of trades made +73.9R against a total of −37.8R.
- **Small tier:** the best 5 trades made 66% of its +35.7R. It was positive in 7 of 9 years, with
  2020–21 holding 71 of its 105 trades.

**Verdict.** There is a real selection edge in the signal, but no edge as built. Kullamägi's record is a
trader's record, documented through his blog and verified broker statements, not published tests. His
parabolic short is explicitly a small-cap, intraday-triggered setup. That points to **an implementation
gap**: the large tier and the daily-close entry are the two biggest departures, and both are where the
losses are.

### 3.3 Fidelity check (Kullamägi, "The Parabolic Short", qullamaggie.com, 2021, and his streams)

| Rule | Kullamägi | This code | Kind | Plausibly matters? |
|---|---|---|---|---|
| **The stock** | Mostly small/micro caps up 300–1,000%+, often on hype; large caps up 50–100% are a weaker, rarer case | Both tiers; large tier = 74% of trades | **Different weighting** | **Yes.** Large tier −0.25R (n = 293); small +0.34R (n = 105) |
| **Extension** | Far above every moving average after a multi-day vertical run | Run measured from the 20-session low; no MA-extension test | **Missing** | **Yes.** It lets 2020 crash rebounds in as "parabolic" (385 large-tier signals in 2020) |
| Up days | Usually 3–5+ in a row | ≥ 3, required | Simplified | Small (up-streak buckets do not sort R monotonically) |
| **Entry trigger** | Intraday: the opening-range low, the first red 5-minute candle, a failed VWAP bounce; stop at the high of the day, often a few % away | The close of the first red *daily* bar | **Different (data limit)** | **Yes.** Later entry, the stop wider in % but placed after the fall; daily bars cannot reproduce it. A daily proxy: short the next session below the red day's low |
| Stop | High of the day | High of the red day; skip below 1% or above 30% | Same | Stops under 3% lose −0.58R (n = 74) |
| Targets | Cover into the 10- and 20-day MAs | 50% at the EMA(10), the rest at the EMA(20), time stop of 10 | Same (split is ours) | — |
| Sizing | Risk 0.25–1%; positions 10–20% | 0.5% risk, 20% cap, 3% open risk | Same | — |
| **Borrow / locates** | Hard-to-borrow is part of the trade; often unavailable | Flat 15%; every name assumed shortable | **Missing (data)** | **Yes** for the small tier: the edge sits exactly where locates are scarcest |

**Known choices.** US only, because India allows no overnight cash shorts. The borrow levels 0/15/100 are
a stated sensitivity. Neither is re-proposed.

**Literature.**

- *Short-horizon reversal:* Lehmann 1990; Jegadeesh 1990.
- *Long-horizon overreaction:* De Bondt and Thaler 1985.
- *Lottery-like stocks underperform:* Bali, Cakici and Whitelaw (2011) on max-return stocks. This
  supports shorting extreme small-cap spikes.
- *Short-sale constraints keep overpricing alive:* Lamont and Thaler (2003). This is also why the
  backtest overstates what was tradable.
- *Kullamägi's own results:* trader testimony, not tested statistics.

### 3.4 Diagnosis

| Weak parameter | Cause | Evidence (n) |
|---|---|---|
| Average R | Large tier: momentum continuation, not exhaustion | 293 trades −0.25R; large-tier signals −15.5% short return at 60 sessions (n = 557) |
| Average R | Tight stops and gap-throughs | Stops < 3%: −0.58R (74); 25 gaps = −67R |
| Trade count / regime | 2020 crash rebounds flood the large tier | 426 of 678 signals in 2020 |
| Robustness | The small tier is concentrated | Top 5 trades = 66% of its R |

### 3.5 Improvements, ranked

| Priority | Change | Parameter it targets | Evidence (run, numbers, n — or source) | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| 1 | **Small tier only** (or a run of ≥ 300% for any size) | Average R | Small +0.34R (n = 105), positive in 7/9 years; R rises monotonically with the run threshold (100% +0.17 → 500% +0.59) | Average R from −0.10 to about +0.3 | About 106 trades in 9 years (≈12/yr); 2020–21 heavy; locates | Plateau across thresholds, yes; concentration, **fragile** (top 5 = 66%) | Parameter change, but needs a flag: `--const` does not reach this runner (code) |
| 2 | **Extension gate:** close ≥ k × its 50-day (and above the 200-day) on the signal day, so a crash rebound is not a parabola | Average R (large tier) | From the method; 2020 large-tier signals −6.1% short return at 20 sessions (n = 385) vs +3.8% median outside 2020 | Removes the rebound regime | Fewer trades | Untested: k must be checked at three values | From the method (code) |
| 3 | **Minimum stop width** 3% (skip narrower) | Average R | Stops < 3%: −0.58R (n = 74); 3–30% all about 0 | +0.1R | −19% of trades | Plateau above 3%, yes | Parameter change (`MIN_STOP_PCT=3`, needs a flag) |
| 4 | **Daily proxy for his trigger:** short the next session on a break below the red day's low, stop at the red day's high | Average R, gap risk | From the method (opening-range-low short) | Enters only when the turn confirms; shorter distance to the 10-day EMA | Misses gap-down opens | Untested | From the method (code, rescan) |
| 5 | Borrow realism: run at 100% borrow as the pass level for the small tier | Validity | 1828: −0.27R overall at 100% | Honest result | Lower R | n/a | Mechanics (`--bt '--borrow-pct 100'`) |

### 3.6 Pass criteria (fixed before any run)

The strategy's own criteria (2026-11-02) stay: ≥ 50 trades, ≥ +0.25R, CAGR > 0, average R > 0 at 100%
borrow. A new version of changes 1+3 must also meet:

- **(e)** average R ≥ +0.25 with the best 5 trades removed ≥ +0.10;
- **(f)** average R > 0 outside 2020–21;
- **(g)** the run threshold's neighbours (200%, 500%) both ≥ +0.20R;
- **(h)** gap-throughs (worse than −1.5R) ≤ 10% of trades.

---

## 4. Family summary

### 4.1 The family's best version today

**`mean_reversion` (RSI(2), US) is the closest to a working edge.** It is the only one of the three whose
raw signal beats a matched random entry across neighbouring thresholds (5–15) and in 7 of 9 years. It
loses that edge to three removable choices:

- the 10 bps cost;
- a 2-slot cap whose skipped signals beat the traded ones;
- a ranking that buys defensive sectors.

Its ceiling is low: about +0.2% a trade on roughly 5% of days per series. It can only matter as a
cost-light timing book or as an overlay on the long book. It cannot be a hedge, because it is long the dip
of the same market.

**`parabolic_short`'s small tier has the strongest per-trade result (+0.34R, n = 105) and a real selection
edge.** It is the family's best *hedge-like* candidate, with near-zero correlation to the index and to the
long book. But it rests on five trades, 2020–21, and borrow that may not have existed. It is a hypothesis
for a version 1.1, not a working edge.

**`stage4_shorts` is furthest away**, and the 2013–2021 window cannot judge it.

### 4.2 The improvement plan, ranked across the family

Nothing below is queued. The `--bt` commands work today; anything marked "code" needs the version bump,
the changelog entry and the Strategy page `DOC` update that CLAUDE.md requires before it is run. These
three strategies are portfolio-runner strategies, so `--const` is **not passed to them** (`jobs/registry.py`
`_run` passes only `--bt` for `portfolio_strategies()`). A `--const` variant would silently run the shipped
rules.

| # | Change | Strategies | Type | Needs code? | Pass criteria (fixed now) | Optimise-stage commands |
|---|---|---|---|---|---|---|
| 1 | Realistic cost + take every signal | mean_reversion | Mechanics | No | §1.6 (a)–(e) | see block A |
| 2 | Re-baseline the current version | stage4_shorts | Mechanics | No | Reference only; record the pass-criteria inputs | see block B |
| 3 | Small tier / run ≥ 300% + minimum stop 3% | parabolic_short | Parameter (via new flags) | **Yes**: CLI flags for `MIN_RUN_PCT_LARGE`, `MIN_STOP_PCT` or a `--tiers small` flag; version 1.1; changes `candidates()` (rescan: this runner has no signal cache) | §3.6 | after the code: block C |
| 4 | Weinstein stop and trail (exits only) | stage4_shorts | From the method | **Yes**: new exit mode flag (e.g. `--exits weinstein`); version 1.5; post-entry logic only | §2.6 | after the code: block D |
| 5 | Extension gate (close ≥ k × 50-day, above the 200-day) | parabolic_short | From the method | **Yes**: a flag with k ∈ {1.5, 2.0, 2.5}; version bump | §3.6, and the k plateau | block C with `--extension k` |
| 6 | Weinstein entry (Stage 3 → 4 breakdown and first pullback) + group in Stage 4 | stage4_shorts | From the method | **Yes**: a new entry code C; rescan | §2.6 (e)–(g) | block D with `--entries C` |
| 7 | Next-session break of the red day's low (trigger proxy) | parabolic_short | From the method | **Yes** | §3.6 | block C with `--trigger next_low` |
| 8 | Universe without XLU/XLP; scale-in | mean_reversion | Literature / method | **Yes** | Only if #1 passes; ≥ +0.05%/trade in both markets | later |

**Block A** (mean_reversion, no code; one variant per change first, then the combination):

```bash
python -m jobs enqueue backtest --market us    --strategies mean_reversion --stage optimise --bt '--cost-bps 2'
python -m jobs enqueue backtest --market india --strategies mean_reversion --stage optimise --bt '--cost-bps 4'
python -m jobs enqueue backtest --market us    --strategies mean_reversion --stage optimise --bt '--max-positions 14 --position-pct 7'
python -m jobs enqueue backtest --market india --strategies mean_reversion --stage optimise --bt '--max-positions 10 --position-pct 10'
python -m jobs enqueue backtest --market us    --strategies mean_reversion --stage optimise --bt '--cost-bps 2 --max-positions 14 --position-pct 7'
python -m jobs enqueue backtest --market india --strategies mean_reversion --stage optimise --bt '--cost-bps 4 --max-positions 10 --position-pct 10'
# neighbour check (criterion e)
python -m jobs enqueue backtest --market us    --strategies mean_reversion --stage optimise --bt '--cost-bps 2 --max-positions 14 --position-pct 7 --rsi-entry 10'
python -m jobs enqueue backtest --market india --strategies mean_reversion --stage optimise --bt '--cost-bps 4 --max-positions 10 --position-pct 10 --rsi-entry 10'
```

The cost levels (2 bps US funds; 4 bps India index futures) are estimates to confirm before the run. The
combined run must also pass (b) at `--cost-bps 10`, which is one more pair of runs.

**Block B** (stage4_shorts v1.4 baseline, no code):

```bash
python -m jobs enqueue backtest --market us    --strategies stage4_shorts --stage optimise
python -m jobs enqueue backtest --market india --strategies stage4_shorts --stage optimise
```

**Block C** (parabolic_short, after the flags exist; names are placeholders for the flags to be added):

```bash
python -m jobs enqueue backtest --market us --strategies parabolic_short --stage optimise --bt '--tiers small'
python -m jobs enqueue backtest --market us --strategies parabolic_short --stage optimise --bt '--tiers small --min-stop-pct 3'
python -m jobs enqueue backtest --market us --strategies parabolic_short --stage optimise --bt '--tiers small --min-stop-pct 3 --borrow-pct 100'
# plateau (criterion g): the run threshold applied to every size
python -m jobs enqueue backtest --market us --strategies parabolic_short --stage optimise --bt '--min-run-pct 200 --min-stop-pct 3'
python -m jobs enqueue backtest --market us --strategies parabolic_short --stage optimise --bt '--min-run-pct 500 --min-stop-pct 3'
```

**Block D** (stage4_shorts, after the exit mode exists):

```bash
python -m jobs enqueue backtest --market us    --strategies stage4_shorts --stage optimise --bt '--exits weinstein'
python -m jobs enqueue backtest --market india --strategies stage4_shorts --stage optimise --bt '--exits weinstein'
```

Every run is another trial. The count after this plan would be:

| Strategy | Trials now | Trials after the plan |
|---|---|---|
| mean_reversion | 10 | about 20 |
| stage4_shorts | 18 | about 22 |
| parabolic_short | 3 | about 8 |

Report each result's deflated Sharpe with the new N.

**What would justify the one verify run.**

- **mean_reversion:** only the 1+2 combination, after it passes §1.6 on optimise, and with the cost level
  fixed in advance. Note the 1.1 options (`rank vol`, `trend off`) came from a 2000–2026 study, so verify
  is already in-sample for them. Do not verify those.
- **parabolic_short:** a 1.1 that passes §3.6 including (e)–(h).
- **stage4_shorts:** not before a faithful version has been tested in a window that contains a bear market
  (S3).

### 4.3 Shared fixes (proposed once, for the family)

| # | Fix | Affects | Why | Code |
|---|---|---|---|---|
| S1 | **Pass `--const` to portfolio-runner strategies**, or refuse it loudly | all three | `jobs/registry.py` drops `--const` for `portfolio_strategies()`, so a constant variant runs the shipped rules and reads as a result | Yes (jobs layer; `tests.test_job_lanes` unaffected) |
| S2 | **Judge every short book as a hedge against the family-5 verified long book** (`momentum_dual_combo`, which `parabolic_short` already uses), not `momentum_baseline` | stage4_shorts, parabolic_short | The US `momentum_baseline` optimise run used in the Stage 4 sleeve test made −2.11%/yr with a −79.9% drawdown (run 1165). A hedge is meaningless beside a broken book | Yes (`LONG_BOOK` constant + `find_long_book`) |
| S3 | **A pre-sample diagnostic window, 2000–2012**, for short and dip-buying rules: never a verdict, never used to tune what verify then judges | stage4_shorts, parabolic_short (mean_reversion's options already saw it) | 2013–2021 holds no sustained bear market; its V-rebounds invert every market filter tested. US prices exist for 1,650–2,680 symbols a year then (survivorship worse) | Yes (`backtesting/windows.py` stage; asof boundary) — needs your decision, as it changes the stage protocol |
| S4 | **Per-instrument cost model with a stress level** in every run (as `stage4_shorts` already reports) | mean_reversion, parabolic_short | A flat 10 bps on SPY-class funds is about 60% of the RSI(2) edge; parabolic shows borrow at 3 levels but not the trading cost | Yes |
| S5 | **Report gap-throughs** (losses worse than −1.5R) in every short report | stage4_shorts, parabolic_short | 25 parabolic gaps = −67R, more than the strategy's total loss | Yes (report only) |

### 4.4 The paper-trading gate

No paper book exists for any of the three: `books` / `paper_orders` hold only the three momentum books,
started 2026-11-05. Strategies refined before October 2026 have no clean historical hold-out, so forward
data is the final test.

| Strategy (version that would go to paper) | Gate to start paper | What the paper record must show to confirm |
|---|---|---|
| mean_reversion (1.3 = cost + all signals, if it passes §1.6) | Optimise pass, then its one verify run passing the same criteria | **At least 60 trades over at least 12 months, both markets together.** Net per trade ≥ +0.10% after the real fills (market-on-close slippage logged); win rate ≥ 60%; no single trade worse than −5%; the slippage per side measured ≤ the cost assumed in the backtest |
| parabolic_short (1.1 small tier, if it passes §3.6) | Optimise pass; verify once | **At least 30 shorts over at least 12 months**, each with a **logged borrow quote and locate**. At least 70% of signals locatable; average R ≥ +0.20 at the actual fees; gap-throughs ≤ 10%. A record of missed locates is itself the result |
| stage4_shorts | Not eligible | Only a faithful version that passes in a bear-containing window (S3). Its paper test must span a market Stage 4: a calm-market paper record says nothing about a bear-market hedge |

---

## 5. What could not be determined, and what would settle it

| Open question | Why it is open | What would settle it |
|---|---|---|
| How v1.4 of stage4_shorts performs as a book | Never run | Block B |
| The realistic per-side cost for the US funds and India index futures | Not stored | Broker fills, or a spread study on the stored quotes |
| Whether parabolic small-cap names were borrowable, and at what fee | No borrow or short-interest data stored | A locate log in paper trading; historical borrow data (not stored) |
| Whether Weinstein's shorts work in a real bear market | 2013–2021 has none; 2022+ is verify | The pre-sample window (S3) |
| The intraday triggers (Kullamägi's opening-range low; Connors' close vs next open) | Daily bars only | Intraday data, or the daily proxies in plan #7 |
| Signal counts are overlapping events | B fires on every touching day; RSI signals cluster across series | The t-values above are optimistic. The decimated filter table (one per stock per 4 weeks) is the honest one |
