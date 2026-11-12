# Strategy family review — 8. Special situations

*Family review per [the briefs](strategy-family-review-briefs.md) (§8), following `/backtest-review` for
`masonson_tqqq`, `etf_swing` and `fno_income`. Written 2026-11-12. **Optimise stage only (2013-01-01 →
2021-12-31, in-sample).** No verify run exists for any of the three (`verify_runs` is empty for them), and none
was read. Legacy and full-stage runs are quoted as context only. Analysis and plan only: no code edited, no job
queued, nothing committed. Working scripts are in the session scratchpad, not in the repo.*

**In short**

- **None of the three has an edge as built.** All three edge badges read "No edge" in the optimise stage.
- **`masonson_tqqq`:** the timing rule does worse than random timing. With the same 139 holding periods placed
  at random, the median CAGR is 35.0%; the rule makes 21.4%, at the 10th percentile. What return it has comes
  from 3x leverage, not from the timing. The method's documented edge (Gayed & Bilello's 200-day rule for leveraged
  index funds) has never been run here. The 20-EMA exit that every run carries is where the losses come from.
- **`etf_swing`:** a liquidity floor of ₹5 crore leaves about three ETFs eligible on a typical day. The book holds
  0.56 positions on average, so about 11% of the capital is deployed. The breakout picks no better than a random
  date for the same ETF (46th percentile). The US universe is fully stored (22 ETFs, every one liquid) and has
  never been run.
- **`fno_income`:** before costs it has a real, detectable carry (mean +0.048R per trade, t = 2.49; +0.059R,
  t = 3.87 without the VIX gate). The assumed 2-point slippage takes 64% of it. 2020 makes 200% of the net P&L,
  and calls lose money. Idle collateral earns nothing, and only one structure is open at a time, so it cannot
  compound. **This is the family's best version today:** the only one with a selection signal the data can
  detect. Its net edge depends on a cost that only live quotes can measure.
- **The plan:** first, four runs that need no code (US `etf_swing`; Masonson `--no-trend --exit-ema 200` and its
  neighbours; `fno_income` without the VIX gate and with wider spreads). Then three fidelity builds: a 2x leverage
  switch with a 200-day-only exit, re-entry on extremes, and laddered put spreads. One shared mechanics fix: idle
  cash earns the stored cash rate. One data gap: live option quotes. The paper-trading gate measures exactly what
  the backtest cannot.

---

## 0. Runs reviewed

| Run | Strategy | Market | Version / spec | Stage | Overrides | Role |
|---|---|---|---|---|---|---|
| 4065 | masonson_tqqq | US | 1.0 / v1.0-f48d6a36 | optimise | none | **baseline** |
| 4066–4068 | masonson_tqqq | US | 1.0 | optimise | `--mode hold3x / holdqqq / dd25` | comparisons, not trials |
| 4069–4078 | masonson_tqqq | US | 1.0 | optimise | `--macd std`, `--macd fast`, `--rsi`, `--keltner`, `--breadth`, `--no-trend`, `--trend-on 3x`, `--exit-ema 8`, `--exit-ema 10`, all extremes | variants already tested (10) |
| 4079–4083 | masonson_tqqq | US | 1.0 | full, `--end 2012-12-31` | 2000–2012 context | context only |
| 1829 | etf_swing | India | 1.0 / v1.0-f3285588 | optimise | none | **baseline** (US: never run) |
| 1322 | fno_income | India | 1.0 / v1.0-8ecb963e | optimise | none | **baseline** |
| 685 | fno_income | India | 1.0 | legacy (2012 → today) | 24-cell sweep in `status` | context only |

Every baseline is the current version with no `--const` override. These runners take `--bt` passthroughs only,
because `--const` does not reach a portfolio runner (`jobs/registry.py`, the portfolio branch of the backtest job).

---

## 1. `masonson_tqqq` — Masonson's TQQQ timing

### 1.1 Scorecard (run 4065, US, optimise)

| Key parameter | Strategy | QQQ buy-and-hold | Synthetic 3x held (4066) |
|---|---|---|---|
| CAGR | 21.13% | 23.01% | 57.32% |
| Excess CAGR vs QQQ | **-1.88%** (-2.25% at 6 bps) | — | +34.31% |
| Max drawdown | **-55.5%** (trough 2016-07-06, peak 2015-03-02) | -28.6% | -69.9% |
| Longest drawdown | 1,210 days | — | — |
| Sharpe / Sortino / Calmar | 0.73 / 0.57 / 0.38 | 1.16 / — / 0.81 | 1.07 |
| Trades (per year) | 139 (15.4) | — | 1 |
| Win rate | 42.8% | — | — |
| Average return per round trip (median) | +1.7% (-1.2%) | — | — |
| Profit factor | 1.59 | — | — |
| Exposure | 68.1% of sessions | 100% | 100% |
| Turnover / costs | 14.98× a year / $15,583 | — | — |
| Exits: BELOW_EMA20 | 132 trades, avg +2%, median 10 days | | |
| Exits: BELOW_SMA200 | 6 trades, avg -4%, median 4 days | | |

"R" in this runner is the round trip's return, not a multiple of risk: the strategy has no stop.

| Year | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|
| Strategy % | 50.8 | 25.9 | **-34.8** | -9.7 | 52.7 | -0.7 | 42.1 | 156.6 | **-9.4** |
| QQQ % | 32.4 | 19.2 | 9.4 | 7.1 | 32.7 | -0.1 | 39.0 | 48.4 | 27.4 |
| Round trips | 16 | 15 | 22 | 12 | 17 | 17 | 11 | 9 | 20 |

### 1.2 Is the edge real?

| Check | Inputs | Result |
|---|---|---|
| Trials | 11 timing runs in optimise (baseline + 10 variants); 3 comparison modes not counted | 11 |
| Deflated Sharpe, absolute | daily returns, T = 2,266; trial Sharpes 0.50–0.86 (sd ≈ 0.11); skew -0.77, kurtosis 9.1 | E[max SR] = 0.17; DSR = 0.95. This only says the return is above zero, and a 3x Nasdaq fund will be. |
| Deflated Sharpe, excess over QQQ | daily (strategy − QQQ), trial excess Sharpes -0.64 to +0.24 | Excess SR 0.09 vs E[max] 0.43; **DSR = 0.16: no edge over QQQ** |
| **Timing null** (stands in for the selection null: one instrument, so timing is the only choice) | 2,000 draws, the same 139 holding lengths placed at random over 2013–2021, open-to-open, 5 bps a side, cash at the T-bill rate | CAGR 21.4% vs null median **35.0%** (p5 17.6, p95 56.2): **10th percentile**. Sharpe 0.76 vs 0.90 (22nd). Max DD -53.9% vs -62.8% (78th: the rule does cut drawdown a little) |
| Exposure-matched static mix | 68% synthetic 3x + 32% T-bills, rebalanced daily | CAGR 42.1%, Sharpe 1.09, max DD -54.3%: **the same drawdown at twice the return** |
| Signals vs traded | one instrument, every signal is traded | not applicable |
| Concentration | 139 round trips | Best 5% (7 trades) = **151% of net P&L**. Trades held ≤ 5 days: 59, summing to -173% of entry value. Held ≥ 30 days: 26, summing to +430% |

**Verdict.** The timing **destroys** value: random entries and exits with the same holding periods do better
two times in three. The rule's return is leverage beta, minus the cost of short whipsaw trades: 59 trades of
five days or less, almost all exits on the 20-EMA. The drawdown is chop in 2015-16, not a crash.

### 1.3 The method — fidelity

Sources: Masonson's Tradeline interview ([creator notes](creator-les-masonson.md) §4.2, §6), and the
leveraged-index timing literature his rule belongs to.

| Rule | Originator / literature | This code | Kind | Matters? |
|---|---|---|---|---|
| Leverage path | Start with QQQ, then QLD (2x), and use TQQQ only once the rules have worked (57:16) | 3x only; `LEVERAGE` is fixed, with no switch | simplified | **Yes.** Decay grows with the square of leverage. 2x is his recommended step and has never been run |
| Line in the sand | "Below it, no position"; no longs below the 200-day (68:15) | Close of ^NDX > SMA200 | same | — |
| Exit | A close below the 8, 10 or 20 EMA, "whichever you are comfortable with" (61:26) | Close below EMA20. The **entry also requires** a close above it | same as his choice | **Yes, this is the loss source.** 132 of 139 exits; 8 and 10 were worse |
| Oversold extremes (RSI, Keltner, breadth, bullish %) | After a decline, indicators drop to extremes and reverse, and "you get back in" (60:46). A weight-of-evidence test: "three or four" together (12:08) | **Every** entry needs at least one switched-on extreme within 10 sessions, including re-entries in a healthy uptrend after a 20-EMA exit | different | **Yes.** It is why exposure falls to 7–22% with the extremes on. He describes a re-entry trigger after a decline, not a gate on every entry |
| Combining | 3–4 indicators lined up | any **one** extreme | different | Probably. Untested |
| MACD histogram | above zero as the momentum check | `--macd std / fast` switch | same | Tested: worse (4069, 4070) |
| Bullish percent | named (72:05) | missing | missing | Low |
| Breadth members | each date's members | **today's** Nasdaq 100 (survivorship) | different | Low. Breadth alone traded 5 times |
| His backtest | 29% CAGR at a 45% drawdown (his AI-assisted test, 73:00) | not reproduced | — | Unknown settings |
| **Literature: 200-day rule for leveraged index funds** | Gayed & Bilello, *Leverage for the Long Run* (2016): hold a leveraged S&P fund above its 200-day average, T-bills below. Leverage pays only when volatility is low and trends persist, and both coincide with the index being above its average. **There is no short-EMA exit** | not runnable: no switch removes the EMA exit (`--no-trend` keeps it) | **missing** | **Yes. This is the documented edge.** The nearest run today is `--no-trend --exit-ema 200` (§7.1) |
| Literature: volatility-managed exposure | Moreira & Muir (2017): scaling exposure down when realised volatility is high improves Sharpe. Leveraged-ETF decay scales with variance (Cheng & Madhavan 2009) | none | missing | Plausibly. A hypothesis |

**What the literature says about the class.** Moving-average timing earns its keep by sidestepping **long**
bear markets (1929–32, 2000–02, 2008), at the cost of whipsaw in sideways years. **2013–2021 has no long bear
market.** Its two drawdowns, Q4 2018 and the 2020 crash, were short V-shapes, the worst case for a trend rule.
So the optimise window is structurally adverse to this method: an honest optimise result can show less whipsaw,
not the crash protection. The 2000–2012 context runs (4079–4083) are where that benefit would show, as context,
never as a verdict. The combined set made +3.3% a year there against the 3x held at -36%.

**Known choices, not re-proposed.** These are already measured: MACD std/fast, RSI, Keltner, breadth, all the
extremes together, `--no-trend`, the trend read on the 3x series, and exits at 8 and 10 EMA. The settings were
fixed before the first run (changelog 1.0).

### 1.4 Diagnosis

- **Exit reason:** the 20-EMA makes 132 of 139 exits. The median hold is 8–10 days. The short trades are where the
  money goes (59 trades of ≤ 5 days sum to -173%).
- **Year:** 2015 (-34.8% against QQQ's +9.4%, 22 round trips) and 2021 (-9.4% against +27.4%, 20 round trips) are
  the chop years. 2020 (+156.6%) carries the whole run, which is the concentration problem in another form.
- **Neighbouring exits:** EMA 8 → 10 → 20 gives CAGR 15.3 → 17.6 → 21.1%, and EMA-20 without the trend rule gives
  25.7%. **The longer the exit, the better**, with no plateau found yet. That points straight at the untested
  slow end (100–200 days).

### 1.5 Ranked improvements

| # | Change | Targets | Evidence | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| M1 | Slow exit: `--no-trend --exit-ema 200` (in and out on the 200-day EMA of ^NDX), with neighbours 100 and 150 | excess CAGR, trades, timing-null rank | Exits 8/10/20 rise monotonically (4076, 4077, 4065); Gayed & Bilello; timing null at the 10th percentile | Far fewer round trips (≈ 15–30), most of the 3x run-up kept | Drawdown in a fast crash: 2020's -30% index fall becomes roughly -45% to -60% at 3x before the exit | To check: the 100/150/200 plateau, costs at 10 bps, years | parameter (existing flags) / from the literature |
| M2 | **2x leverage** with a 200-day-only exit (new `--leverage` and `--no-ema-exit`) | max DD, Calmar | His QQQ → QLD → TQQQ path; QLD tracking already measured (1.25 points short, `tracking()`) | Max DD near QQQ's, CAGR above it if timing is neutral | Less upside than 3x | 2x and 3x both; costs doubled | from the method (code) |
| M3 | Extremes as **re-entry only after a BELOW_SMA200 exit**, needing 2 of N | exposure, excess | 4078: DD -28.2% at 22% invested; the gate starves ordinary re-entries | Keeps the extremes' drawdown cut without the 22% exposure | More rules = more overfitting, his own warning (73:45) | 1 vs 2 of N; window 10 vs 20 | from the method (code) |
| M4 | Volatility-scaled leverage: 3x × min(1, target vol / 20-day realised vol), cash for the rest | Sharpe, max DD | Moreira & Muir; decay ∝ variance | Smaller 2015-16 and 2020 drawdowns | Model choice; turnover | Targets 15/20/25%; 2x and 3x | from the literature (code) |

---

## 2. `etf_swing` — the Ep. 44 swing system on ETFs

### 2.1 Scorecard (run 1829, India, optimise; US never run)

| Key parameter | Strategy | Nifty 50 buy-and-hold |
|---|---|---|
| CAGR | 0.76% | 13.54% |
| Excess CAGR | **-12.78%** (-13.34% at standard cost) | — |
| Max drawdown / longest | -9.3% / 1,935 days | -38.3% |
| Sharpe / Sortino / Calmar | 0.27 / 0.17 / 0.08 | 0.86 / — / 0.35 |
| Annualised volatility | 3.1% | — |
| Trades (per year) | 74 (8.2) | — |
| Win rate | 31.5% | — |
| Average R (median R) | +0.17 (-0.48) | — |
| Profit factor | 1.32 | — |
| Exposure | 41.2% of days; **0.56 positions on average (peak 3 of 5) ≈ 11% of capital** | 100% |
| Turnover / costs | 1.64× / ₹58,488 | — |
| Median hold | 18 days | — |

| ETF | Trades | Mean return | P&L ₹ |
|---|---|---|---|
| GOLDBEES | 21 | -0.6% | -66,871 |
| NIFTYBEES | 18 | +0.5% | +21,039 |
| CPSEETF | 16 | +1.0% | +54,895 |
| BANKBEES | 15 | +1.6% | +83,446 |
| MON100 | 3 | +3.3% | +38,281 |
| ITBEES | 1 | +2.5% | +10,034 |

**Universe.** Of the 15 listed ETFs, 12 have prices; SILVERBEES, AUTOBEES and MASPTOP50 have none. Only 6 ever
traded. The ₹5 crore 50-day traded-value floor is about 125× the ₹4 lakh slot. GOLDBEES, NIFTYBEES, BANKBEES and
CPSEETF clear it on 45–54% of days. MON100 and ITBEES clear it on 14%. JUNIORBEES, PSUBNKBEES, MID150BEES,
PHARMABEES, MAFANG and HNGSNGBEES clear it on 0–2%. **The median eligible pool on an entry date is 3 ETFs.**

### 2.2 Is the edge real?

| Check | Inputs | Result |
|---|---|---|
| Trials | 1 optimise run | 1. PSR(SR > 0) = 0.78 (SR 0.27, skew -0.8, kurtosis 27, T = 2,217) |
| Selection null | per trade, a random ETF from that date's eligible pool, same dates; 1,000 draws; n = 74 | Mean +0.68% vs null median +0.20% (p5 -0.32, p95 +0.74): **93rd percentile**. Weak, from a pool of ~3 |
| Timing null | same ETF, random date, same holding length; 500 draws | Null median +0.75%: **46th percentile. No timing edge** |
| Signals vs all days | 216 breakout signals vs 17,902 eligible ETF-days (to 2021-12-31) | Forward 5 / 20 / 60 sessions: +0.57 / +1.46 / +2.64% vs +0.34 / +1.13 / +3.42%. A slight short-term lift, **worse at 60 sessions** |
| Traded vs untraded signals | 73 traded vs 143 untraded. The untraded are mostly repeat signals while the ETF was already held; slots never filled (peak 3 of 5) | 20-session +1.24% vs +1.57%. **Slots and ranking are not what loses here** |
| Signals by ETF (20-session lift) | BANKBEES +1.9, CPSEETF +2.0, GOLDBEES -1.0, MON100 -1.4, NIFTYBEES -0.3 points | Mixed. No pattern on ≥ 30 signals per ETF |
| Concentration | 74 trades | Best 4 trades (5%) = **162% of net P&L**; 2021 alone = ₹147.6k against ₹140.8k total |

**Verdict.** There is no edge, and no fair test yet. The run measures a book that was 89% idle cash earning
nothing, choosing among about three ETFs. The breakout adds nothing over a random date for the same ETF.
Stock-picking ideas (ranking) cannot help, because the rank was never binding.

### 2.3 The method — fidelity

Source: Sandeep Rao, "The Long & The Short" Ep. 44 ([notes](swing-trading-video-series.md)).

| Rule | Originator | This code | Kind | Matters? |
|---|---|---|---|---|
| Category filter | The instrument's own index above its 21- or 50-day average | The ETF's close > EMA21 (the ETF is its own index) | simplified, faithful | — |
| Entry | N-day breakout, N = 7, 15 or 21 (example 10) | 21 | same | — |
| Scan | Top performers over the past week | 5-day return rank | same | **Not binding** (slots never full) |
| "To tighten it" | Above the 200- or 50-day; a minimum average volume | ₹5 crore / $20M 50-day value floor; **no 200-day** | different threshold / missing | **Yes.** The floor empties the India universe. The 200-day is untested |
| Liquidity | "Only liquid ETFs with real volume" | absolute floor ≈ 125× the position size | different threshold | **Yes** |
| Slots | 5 × 20%, one in, one out | same | same | — |
| Trail | 21-day EMA (or 9/7, Supertrend, 3–4% from the peak) | EMA21 on the close | same | — |
| Sizing | Equal, **or** risk-based at 1% of capital | equal only | simplified | Possibly |
| Reward to risk | at least 3 : 1 | not enforced (the trail decides) | missing | Low |
| Universe | gold, **silver**, index ETFs, US index ETFs | silver missing from data; **US never run** | gap | **Yes** |
| Idle money | — (practice: a liquid fund) | earns 0 | mechanics | Yes: ≈ 5 points of CAGR at India's rates with 89% idle |

**Literature.** Trend following across asset classes has a long documented record. Faber (2007) uses a 10-month
average on five asset classes. Moskowitz, Ooi & Pedersen (2012) and Hurst, Ooi & Pedersen (2017) find time-series
momentum on 1–12 month lookbacks in futures, sized by volatility, across many dozens of markets. That record rests
on **breadth (many uncorrelated markets)**, **lookbacks of months** and **volatility-scaled sizing**. This build
has three to six correlated India ETFs, a 21-day trigger and equal weights. The strategy's caveat cites
short-term reversal against the one-week rank. That evidence is for single stocks. Moskowitz & Grinblatt (1999)
report industry portfolios with momentum even at one month, so for sector ETFs the caveat is less certain. Either
way the rank is not binding in India.

**Known choices.** None tested yet. The one-week rank is kept on purpose as the series' rule (caveat).

### 2.4 Diagnosis

- **Deployment, not selection, explains the CAGR:** 0.56 positions × 20% ≈ 11% invested. The trades' own
  economics (PF 1.32, +0.17R) would not beat the index even fully deployed. Read with the timing null, they are a
  coin flip.
- **GOLDBEES is the main loser** (21 trades, -₹66.9k). Gold's 21-day breakouts in 2013–2021 mostly failed: an asset
  with no equity drift (the series' own point, Ep. 43).
- Every per-ETF pattern rests on fewer than 30 trades: hypotheses only.

### 2.5 Ranked improvements

| # | Change | Targets | Evidence | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| E1 | **Run the US baseline** (22 ETFs, all liquid on ≥ 83% of days) | everything: the first fair test | The US universe is stored and unmeasured | 5 slots actually filled; ranking becomes binding | — | the first measurement | mechanics (no code) |
| E2 | Liquidity floor relative to the slot (e.g. 50-day value ≥ 20× the position, ≈ ₹0.8 crore at today's account) | India deployment | 6 of 12 ETFs never eligible; median pool 3 | India pool of 6–8 ETFs; more positions | Wider spreads on small ETFs: run at 20 bps too | 10×/20×/40× | from the method (code) |
| E3 | Idle cash earns the stored cash rate (shared fix S1) | CAGR (accounting) | 89% idle at 0% | ≈ +4–5 CAGR points in India | none on the trades | — | mechanics (code) |
| E4 | 200-day filter (the series' "tighten" option) | win rate, DD | method; Faber | Fewer failed breakouts in down-trending assets (gold 2013–15) | Fewer trades | 50- vs 200-day | from the method (code) |
| E5 | Rank by a 63- or 126-session return instead of 5 | US average R | TSMOM / industry momentum; matters only where slots fill | Better picks in the US only | Departs from the series' rule | 63/126/252 | from the literature (code). **Rank last in India** (not binding) |
| E6 | Risk-based (1%) or inverse-volatility sizing | DD, Sharpe | series' option; TSMOM | Gold and silver sized down against equity ETFs | — | — | from the method (code) |

---

## 3. `fno_income` — NIFTY credit spreads

### 3.1 Scorecard (run 1322, India, optimise)

| Key parameter | Strategy | Nifty 50 buy-and-hold |
|---|---|---|
| CAGR | 0.41% | 12.55% |
| Excess CAGR | -12.14%. **Meaningless:** 0.6% of capital is at risk on an average day | — |
| Max drawdown / longest | -5.1% (a floor: open structures are not marked) / 1,814 days | -38.4% |
| Sharpe / Sortino / Calmar | 0.30 / 0.05 / 0.08 | 0.79 / — / 0.33 |
| Structures (per year) | 148 (16.5) | — |
| Win rate | 75.7% | — |
| Average R (wins / losses) | +0.017 (+0.13 / -0.33) | — |
| Profit factor | 1.21 | — |
| Exposure | 40.2% of days; average risk/equity 0.60% | — |
| Costs | ₹133,886 = **64% of gross P&L** (₹209,043) | — |
| Median credit / round-trip cost | 32.6 points / 4 points (2 legs × 2) = 12% of the credit | — |
| Break-even slippage | **≈ 3.1 index points per leg** | — |
| Exits | PROFIT_TARGET 112 (+0.13R, median 7 days); STOP 36 (-0.33R, 9 days); TIME_EXIT 0 | — |

| Side | Structures | Win rate | Net P&L ₹ | Gross P&L ₹ | Average R |
|---|---|---|---|---|---|
| Put spreads | 87 | 80.5% | **+97,174** | +174,271 | +0.037 |
| Call spreads | 61 | 68.9% | **-22,017** | +34,772 | -0.012 |

| Year | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|
| Structures | 26 | 10 | 28 | 16 | 5 | 20 | 7 | 24 | 12 |
| Net P&L ₹k | -41.9 | +1.7 | -21.9 | -1.1 | +2.6 | -25.8 | +2.6 | **+150.6** | +8.3 |

### 3.2 Is the edge real?

| Check | Inputs | Result |
|---|---|---|
| Trials | 1 optimise + 24 legacy sweep cells (2012 → today; legacy, includes verify years) + 3 null runs made for this review (below) | **28** |
| Deflated Sharpe | T = 2,206 daily; skew 3.5, kurtosis 149 (the equity steps only at closes); the trials' Sharpe dispersion is not stored for the legacy cells, **assumed sd 0.3** | E[max SR] = 0.61 vs SR 0.30: **DSR = 0.17** |
| Per-trade t-statistics (n = 148) | mean R / standard error | Net t = **0.88**; gross (zero cost) t = **2.49** |
| **VIX-gate null** (the gate is the strategy's timing choice): the same runner with `vix_percentile = 0`, run read-only inside the optimise boundary | n = 216 | Net mean R +0.030 (t = 1.92), CAGR 1.06%, ex-2020 **+₹3.2k** (vs -₹75.5k gated); gross +0.059R (t = **3.87**). **The gate removes value** |
| Signals vs traded | one structure at a time, so a signal is skipped only while one is open | The ungated null above is the nearest comparison |
| Concentration | 148 structures | Best 5% (7) = 132% of net P&L. **2020 = 200% of net P&L** (24 of 24 won after the COVID volatility spike); without 2020 the net is -₹75.5k |

**Verdict.** **A gross carry edge is there and statistically detectable**, as the variance-risk-premium
literature predicts. It sits on the put side. It does not survive the assumed cost outside 2020, and the gate
meant to improve it makes it worse. The size of the carry is also tiny, so even if the net is real it cannot
compound at this risk budget.

### 3.3 The method — fidelity

Sources: the Learn guide's income chapter ([learn-fno-income](learn-fno-income.md)); Tom Sosnoff's two videos
([video notes](video-strategy-notes.md) §3: 16–25 delta, 35–50 DTE, only at high IV, take 50%, strangles are most
of his profit); Kundan's put ratio spread (§5); [F&O and leverage](system-fno-leverage.md) (naked selling out of
scope).

| Rule | Originator | This code | Kind | Matters? |
|---|---|---|---|---|
| Short delta | 16–25 (Sosnoff); 0.15–0.30 (guide) | 0.25 ± 0.10 | same | — |
| Days to expiry | 35–50 (Sosnoff) | the **nearest** expiry in 20–45, so monthly entries often sit near 20–30 days | different | **Probably.** Less premium per fixed cost, more gamma |
| Profit target | 50% | 50% | same | — |
| Time exit | out well before expiry. The tastytrade "21 days" rule is practitioner lore, not in our notes | 6 days | different | Untested |
| Stop | 2× credit (guide); practitioners often do not stop defined-risk spreads (lore) | 2× credit, checked on settle | same as the guide | 36 stops at -0.33R; untested without |
| Volatility gate | only at high implied volatility (IV rank) | India VIX ≥ 40th percentile of 252 days | same idea | **The data contradicts it** (§3.2) |
| Structure | short strangles carry most of his profit | spreads only | **known choice** (naked selling out of scope by the system rule) | Wings give back part of the premium |
| Trend side | above the 50-day sell puts, below and falling sell calls (guide) | same | same | **Calls lose net** (61 trades) |
| Credit ≥ 25% of width | guide | credit/width ≥ 0.65 × delta | **known choice, measured** (changelog 1.0: the flat rule left 23 trades in 14 years) | — |
| Event filter | skip results, RBI and Budget | missing | missing | Slightly. The caveat says it makes this worse, not better |
| Positions | many small concurrent positions across expiries ("trade small, trade often", practice) | **one at a time**, 1.5% max loss | different | **Yes, for compounding and concentration** (2020 = 200%) |
| Collateral | earns interest. Put-write benchmarks such as CBOE PUT hold T-bills; NSE accepts pledged liquid funds | idle equity earns 0 | **missing** | **Yes:** ≈ 5–6 CAGR points at India's rates |
| Put ratio spread (Kundan) | weekly: buy 1 put 200 below, sell 2 at 400 below, buy 1 at 800 below, on the expiry after next; +1% target, -1% stop, out by Friday; skip when the debit > 0.7% | not built | **missing** | Untested. Weekly NIFTY chains are stored only from 2019 (68–73 expiries a year), so the optimise window has about 150 weeks |
| Bid / ask | real fills | 2 points per leg assumed; the bhavcopy has none | data gap | **Decides the sign** (break-even ≈ 3.1) |

**Data, point in time.** `derivatives_bhav` is the daily NSE bhavcopy, one file per day, so it is point in time
by construction. It has settle, close, OI and volume for every NIFTY strike and expiry from 2012, weekly expiries
from 2019, and no bid/ask, intraday prices or lot sizes. India VIX and the repo rate are stored. There are no US
chains.

**Literature.** The variance risk premium is well documented: implied volatility exceeds realised on average
(Bakshi & Kapadia 2003; Carr & Wu 2009), and out-of-the-money index puts are the most expensive options
(Coval & Shumway 2001). That matches the put-side carry found here. Practitioner experience (tastytrade's own
studies, not peer-reviewed) favours ~45 DTE, managing winners at 50% and many small positions. The known failure
mode is the one the caveats name: a gap through both strikes, which a daily settle understates.

### 3.4 Diagnosis

- **Costs:** the fixed 2-point slippage is 12% of the median credit, and it takes 64% of the gross. A wider spread
  collects more credit for the same per-leg cost.
- **Side:** the call spreads give back what the puts earn (-₹22k net on 61 trades). That fits equity drift and a
  steeper put skew.
- **Gate:** the VIX ≥ 40th-percentile entries are the post-shock regimes where call-side and trend losses cluster
  (2013, 2015, 2018 are negative). Without the gate, 2013–2021 ex-2020 breaks even.
- **Exits:** 112 targets at +0.13R against 36 stops at -0.33R. A stop costs 2.6 targets, so the 75.7% win rate is
  close to break-even before costs, as the textbook shape predicts.

### 3.5 Ranked improvements

| # | Change | Targets | Evidence | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| F1 | **Put side only** (flat when the trend would sell calls) | average R, ex-2020 P&L | PE +₹97k vs CE -₹22k (87 / 61 trades); put-skew literature | Net mean R ≈ +0.04 on ~87 trades | Fewer trades | Must hold with and without the gate | from the literature / data (code: a `put_only` structure) |
| F2 | Drop the VIX gate (`--vix-percentile 0`), neighbours 20 and 60 | trade count, ex-2020 | Null: +0.030R vs +0.017R net; ex-2020 +₹3.2k vs -₹75.5k | More trades, less 2020 dependence | Against the method's IV rule. The data wins only if the plateau holds | 0/20/40/60 | parameter (no code) |
| F3 | Wider spreads, `--width-pct 2.5` and `3.0` | cost share | cost is fixed per leg, 12% of the median credit | Cost share roughly halves | Larger max loss per lot, so fewer lots at the same risk | 1.5/2.5/3.0; cost at 3 and 4 points | parameter (no code) |
| F4 | ~45 DTE (the expiry nearest 45 within 35–50) and exit at 21 DTE | gamma losses, stops | Sosnoff's rules; untested here | Fewer stops per credit | Less frequent turnover | 35–50 vs 20–45 windows | from the method (code) |
| F5 | **Ladder:** up to 4 concurrent put spreads, one new entry a week, the same 1.5% each | compounding, concentration | one-at-a-time = 0.6% at risk; 2020 = 200% of P&L | Many more entries; returns spread across years | Correlated losses in one gap: cap total max loss at 6% | 2/4/6 rungs | from the method (code) |
| F6 | Collateral earns the stored repo/T-bill rate (shared S1) | CAGR (accounting) | idle at 0% | ≈ +5–6 CAGR points; the fair comparison with the index | none on the trades | — | mechanics (code) |
| F7 | Kundan's weekly put ratio spread as a structure | a second carry structure | the method; untested | Unknown: the asymmetry is the claimed edge | Only ~150 weeks in optimise; the 1x2 tail needs the far hedge | must pass on 2019–2021 alone; small n is fragile | from the method (code) |
| F8 | Event filter (RBI, Budget, results dates) | tail losses | guide | Small | Needs a stored calendar | — | from the method (code + data) |

Not re-proposed (legacy context): condors (worse than single spreads at every delta), deltas 0.15/0.35, and
cost sweeps of 1–6 points.

---

## 4. The family's best version today

**`fno_income`, put side only.** It is the only strategy in the family whose signal the stored data can detect.
The gross per-trade edge is t = 2.49 gated, and t = 3.87 without the gate. The put side carries it. It is the
mechanism the literature documents best: the variance risk premium on index puts. It is not yet a working edge:
the net is positive only through 2020, and it depends on a cost (≈ 3.1 points per leg to break even) that the
bhavcopy cannot supply. That is why its paper-trading gate (§8) is mainly a measurement of real fills.

`masonson_tqqq` has the best headline. Its no-trend variant beat QQQ by 2.69 points. But that return is
leverage beta, and its timing ranks at the 10th percentile against random timing. It becomes a candidate only if
the slow-exit or 2x versions (M1, M2) turn the timing null neutral or positive. `etf_swing` has not had a fair
test: the US universe has never been run, and India deploys 11% of its capital.

No combination of rules across the three is proposed. They trade different instruments with different payoffs,
and none has an edge to combine yet.

---

## 5. Improvement plan, ranked across the family

Pass criteria below are fixed **now, before any of these runs**. Every run adds a trial to its strategy's count
(Masonson 11 → up to 17; fno_income 28 → up to 34; etf_swing 1 → up to 6). The deflated Sharpe in §1.2/§3.2 is
recomputed with the new count.

| Rank | Change | Strategy | Needs code? | Why this rank |
|---|---|---|---|---|
| 1 | E1: US baseline | etf_swing | no | The first fair measurement; costs one run |
| 2 | M1: slow exit `--no-trend --exit-ema 200` (+100, 150) | masonson_tqqq | no | Closes the main fidelity gap with existing flags |
| 3 | F2 + F3: no VIX gate; wider spreads | fno_income | no | Data-led; existing flags |
| 4 | S1: idle cash earns the cash rate | etf_swing, fno_income | yes | Accounting fix; every later comparison needs it |
| 5 | F1 + F5: put-only, laddered | fno_income | yes | Turns the detectable carry into something that can compound |
| 6 | M2: 2x leverage, 200-day-only exit | masonson_tqqq | yes | His own leverage path |
| 7 | E2 + E4: relative liquidity floor; 200-day filter | etf_swing | yes | Fixes the India opportunity set |
| 8 | M3, M4, F4, E5, E6 | various | yes | Method and literature refinements after the base fixes |
| 9 | F7, F8 | fno_income | yes (+ data) | New structure; small optimise sample |

### 5.1 Pass criteria (written before any run)

| Change | Must improve | Must not worsen beyond | Robustness checks |
|---|---|---|---|
| **E1** (US etf_swing baseline) | Pass = Sharpe ≥ SPY's **and** max DD ≤ half of SPY's, with ≥ 100 trades. Excess CAGR is reported but is not the test (slots can sit idle) | — | Selection null (random eligible ETF, same dates) ≥ 90th percentile; timing null ≥ 75th; cost at 20 bps keeps Sharpe ≥ SPY's − 0.1; no year > 50% of P&L |
| **M1** (and M2) | The original 1.0 rule, unchanged: excess CAGR vs QQQ > 0, max DD no deeper than QQQ's (-28.6%), ≥ 20 round trips | — | Both neighbours (EMA 150 and 100, or 2x at the other exit) also have excess > 0; 10 bps a side keeps excess > 0; timing null ≥ 50th percentile (timing no longer destroys value); 2020 < 60% of total P&L |
| **F2 / F3** | Net mean R > 0 with t ≥ 2.0 at 2 points per leg | Max DD no worse than 2× baseline (-10%) | Still ≥ 0 net at 3 points per leg; ex-2020 net P&L > 0; the neighbouring value (20/60 percentile; 2.5/3.0% width) agrees in sign; ≥ 100 structures |
| **S1** | Trade lists identical to the pre-fix runs (no behaviour change in selection) | — | CAGR rises by about the idle share × the cash rate (±0.5 points) |
| **F1 + F5** | Net mean R > 0 with t ≥ 2.0; CAGR (with S1) > the cash rate + 1 point | Max DD ≤ -10%; worst year ≥ -5% | 3 points per leg still ≥ 0; ex-2020 > 0; 2 and 6 rungs agree in sign; ≥ 150 structures |
| **E2 + E4** (India) | Average positions ≥ 1.5; profit factor ≥ 1.3 | Max DD ≤ -20% | 10× and 40× floors agree; 20 bps cost; ≥ 100 trades |

### 5.2 Optimise-stage commands

Runnable today (no code):

```bash
# E1 — etf_swing, US baseline (its cost row needs a --cost-bps flag first, see below)
python -m jobs enqueue backtest --market us --strategies etf_swing --stage optimise

# M1 — Masonson slow exit (in and out on the index's EMA), with neighbours and doubled costs
python -m jobs enqueue backtest --market us --strategies masonson_tqqq --stage optimise --bt='--no-trend --exit-ema 200'
python -m jobs enqueue backtest --market us --strategies masonson_tqqq --stage optimise --bt='--no-trend --exit-ema 150'
python -m jobs enqueue backtest --market us --strategies masonson_tqqq --stage optimise --bt='--no-trend --exit-ema 100'
python -m jobs enqueue backtest --market us --strategies masonson_tqqq --stage optimise --bt='--no-trend --exit-ema 200 --cost-bps 10'

# F2 — fno_income without the VIX gate, and the neighbours
python -m jobs enqueue backtest --market india --strategies fno_income --stage optimise --bt='--vix-percentile 0'
python -m jobs enqueue backtest --market india --strategies fno_income --stage optimise --bt='--vix-percentile 20'
python -m jobs enqueue backtest --market india --strategies fno_income --stage optimise --bt='--vix-percentile 60'
# F3 — wider spreads, then the cost check on the better width
python -m jobs enqueue backtest --market india --strategies fno_income --stage optimise --bt='--width-pct 2.5'
python -m jobs enqueue backtest --market india --strategies fno_income --stage optimise --bt='--width-pct 3.0'
python -m jobs enqueue backtest --market india --strategies fno_income --stage optimise --bt='--width-pct 3.0 --cost-points 3'
```

The etf_swing runner has no cost flag. Its 20 bps robustness row needs E2's code change (a `--cost-bps`
argument). A `--bt` passthrough moves no fingerprint, so these runs share the current spec id. They are filed by
their `overrides.json`, which the Backtests tab shows.

With code (each one is a version bump, a changelog entry and doc updates per CLAUDE.md; then
`PYTHONPATH=. .venv/bin/python -m tests.test_strategy_docs` and `-m tests.test_strategy_versions`):

| Change | File / constants | Default behaviour changes? | Version | Then run |
|---|---|---|---|---|
| S1 cash yield | `backtesting/etf_swing.py` `run()`; `backtesting/fno_income.py` `run()` — idle equity × `index_data.cash_rate_series` per calendar day, as `masonson_tqqq.simulate` does | yes (equity, not trades) | etf_swing 1.1, fno_income 1.1 | both baselines again (`--stage optimise`) |
| M2 2x + 200-day-only exit | `masonson_tqqq.py`: `--leverage {2,3}` (passes `LEVERAGE` to `synthetic`), `--no-ema-exit` (drop `c > ema_x` from `state` and the BELOW_EMA reason) | no (off by default), but new constants move the fingerprint | 1.1 | `--bt='--leverage 2 --no-ema-exit'`, `--bt='--leverage 3 --no-ema-exit'`, `--bt='--leverage 2 --no-trend --exit-ema 200'` |
| M3 re-entry extremes | `signals()`: an extreme required only after a BELOW_SMA200 exit; `EXTREME_MIN_COUNT` = 2 | no (switch) | 1.2 | `--bt='--rsi --keltner --breadth --reentry-only'` |
| M4 vol-scaled leverage | `simulate()` gains a daily exposure series; `VOL_TARGET`, `VOL_WINDOW` = 20 | no (switch) | 1.3 | `--bt='--vol-target 0.20'` (and 0.15, 0.25) |
| F1 put-only | `fno_income.py` `STRUCTURES` + `put_only`; the doc says `both_sides` duplicates the default today — reuse or retire it | no | 1.2 | `--bt='--structure put_only'` (± `--vix-percentile 0`) |
| F5 ladder | `run()` keeps a list of open structures; `MAX_RUNGS`, `ENTRY_EVERY_DAYS`, `MAX_TOTAL_RISK_PCT` | yes if made the default; keep it a switch | 1.3 | `--bt='--structure put_only --rungs 4'` (and 2, 6) |
| F4 45 DTE | `DTE_MIN, DTE_MAX` → choose the expiry nearest `DTE_TARGET` = 45; `CLOSE_DAYS_BEFORE` as a flag | switch | 1.4 | `--bt='--dte-target 45 --close-days 21'` |
| E2 / E4 | `etf_swing.py`: `MIN_VALUE` as a multiple of the slot (`MIN_VALUE_X_SLOT`); a `TREND_SMA` filter; CLI flags for both and for `COST_BPS` | yes (floor) | 1.1 | India and US baselines; `--bt='--trend-sma 200'` |

None of these touch a per-symbol `evaluate()` or the signal cache: all three are portfolio runners, so
`signal_version` and `signal_exempt_consts` do not apply.

### 5.3 What would justify a verify run

Only a version that meets **every** row of its pass criteria above, including the robustness checks, and only
once per version. For Masonson that is a version passing the 1.0 rule as written. For fno_income it is the
put-only ladder (with S1) passing at 3 points per leg. Even then, its verify verdict stays conditional on costs
until §8 measures them. For etf_swing it is the US version passing E1. The pass rule is written into the
changelog before the verify run is queued.

---

## 6. Shared fixes (proposed once, for the family)

| # | Fix | Applies to | Type |
|---|---|---|---|
| S1 | **Idle cash earns the stored cash rate.** `masonson_tqqq` already does this. `etf_swing` (≈ 89% idle in India) and `fno_income` (≈ 99% idle) book 0%, which understates CAGR by ≈ 5–6 points at India's rates and makes every excess-CAGR comparison unfair | etf_swing, fno_income | mechanics, code |
| S2 | **The Strategy page shows the wrong parameters.** All three pages list `momentum_baseline`'s CLI (`--top-n`, `--lookback` …) under params, not their own runner's flags or `param_docs` | all three | docs / page code |
| S3 | **Wrong page commands.** Masonson's "Backtest in-sample" and "Verify" commands say `--market india`, which its runner refuses (`choices=[us]`). etf_swing offers India only, though its US universe is stored | masonson_tqqq, etf_swing | docs |
| S4 | **Stale status.** etf_swing still reads "Not yet backtested" after run 1829. CLAUDE.md asks for the status to name the stage of every figure | etf_swing | docs |
| S5 | **Timing / selection null in the report.** All three trade one instrument or a handful. Add the matched random-timing null (§1.2) to these runners' reports, so "beat the index" is not read as "the rule works" | all three | report code |
| S6 | **A data gap: live quotes.** Option bid/ask (fno_income) is the one input that decides a verdict, and no stored data has it. Historical Nasdaq 100 membership (Masonson's breadth) is a smaller gap. A quote-capture job would be a new `marketdata/` job in the registry (a data-layer change, requiring explicit approval), not part of the read-only Kite module | fno_income, masonson_tqqq | data |

---

## 7. What could not be determined, and what would settle it

- **The real cost of an option round trip.** Only live bid/ask capture or paper fills (§8) can settle it. This is
  the whole fno_income verdict.
- **The trial Sharpe dispersion for fno_income's 24 legacy cells:** only one legacy run is ingested. The DSR above
  assumes an sd of 0.3; rerunning the sweep in optimise would replace the assumption, but it costs 24 trials.
- **Crash protection for the Masonson rule** cannot be shown in 2013–2021, which has no long bear market. Only the
  2000–2012 context and forward data can show it.
- **Masonson's own settings** (his 29% CAGR / 45% DD claim) are unknown (open question in the creator notes).
- **India ETF history:** SILVERBEES, AUTOBEES and MASPTOP50 have no stored prices; several others start in
  2019–2021. Fetching them is a `marketdata/` job, not a review step.
- **The VIX-gate null and the zero-cost runs** were made for this review in the scratchpad, read-only, inside the
  optimise boundary. They count as trials (included above) and are not ingested runs.

---

## 8. The paper-trading gate

No paper book exists for any of the three (`paper_orders` holds only `momentum_baseline`, `dual_momentum` and
`momentum_dual_combo`). Every rule here was refined after October 2026's cut-off, so forward data is the only
clean test.

**fno_income, put spreads (the family's best version), after F1/F5 pass in optimise:**

| Item | Gate |
|---|---|
| What is recorded | Each rung's entry and exit **at the quoted bid/ask** (both legs), next to the settle the backtest would have used |
| Length | ≥ 9 months **and** ≥ 40 structures, including at least one India VIX spell above its 80th percentile |
| Cost (the main question) | Median measured slippage ≤ **2.5 points per leg** (break-even ≈ 3.1). Above 3.1, the strategy is retired as untradable at this size, whatever its P&L |
| Return | Net mean R > 0. Win rate between 65% and 85% (the backtest's shape: 75.7% gated, 77.3% ungated) |
| Risk | No single loss beyond 1.1× its sized maximum loss (gap risk); worst month ≥ -3% of the book at 4 rungs |
| Stop the test | Three stops in a row that each lose more than 1.5× the backtest's average stop (-0.33R) |

**masonson_tqqq, if M1 or M2 passes:** a slow rule makes few trades, so the gate is execution, not P&L. Run it
for 12 months, with ≥ 4 signals, on the real fund (QLD or TQQQ). Each fill must land within 10 bps of the
synthetic next-open price, and tracking against the synthetic must stay within the 3.5% a year already measured.
The P&L verdict needs a full market cycle, years, and the gate says so.

**etf_swing:** no paper book until E1 (US) passes its optimise criteria.
