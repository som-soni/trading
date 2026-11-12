# Strategy review: portfolio momentum family

*2026-11-12. Brief: `research/strategy-family-review-briefs.md` §5. Procedure: `/backtest-review`, run once per
strategy. Evidence comes from **optimise-stage runs only (2013-01-01 to 2021-12-31)** and from stored prices
cut at 2021-12-31. Verify runs are quoted by their edge badge and nothing more. No code was edited, no job
was queued and nothing was committed. The working scripts are in the session scratchpad, not in the repo.*

Strategies: `quality_momentum`, `momentum_vol_scaled`, `momentum_dual_combo`, `dual_momentum`,
`momentum_baseline`, `rs_leaders`, `sector_rotation`.

---

## 0. Headline

1. **One strategy has a selection edge that survives every check here: `momentum_vol_scaled` in India.**
   Each month-end its top 20 beat its own eligible pool by **+1.06% a month** (t 2.9; n = 108 months). They
   beat every one of 1,000 random 20-name books drawn from the same pool. Returns fall steadily down the
   rank buckets, the top 20 led the pool in 8 of 10 years, and the deflated Sharpe is 1.00 (deflated IR
   0.86 over 25 trials). It is the family's best version. Protect it and paper-trade it. Do not re-tune it.
2. **The US problem is how the books are built, not the momentum idea.** `momentum_baseline`'s US top 10
   carries **83% annualised volatility against 31% for its pool**. Its arithmetic monthly return equals the
   pool's (1.14% against 1.20%, 43rd percentile of random books). Volatility drag then cuts the compounded
   return from 14.1% a year to 5.3%. A Jegadeesh-Titman top decile (about 100 names, no 200-day filter) of
   the same pool compounds at **17.8% a year** with 24% volatility. That is an implementation gap, but a
   fragile one: most of it is 2020.
3. **`quality_momentum` works in the US because its filter removes the lottery names.** In the US the
   quality pool returns no more than the full pool (1.16% against 1.15% a month), but its top 10 holds
   steadier stocks (1.56% a month, 97th percentile). Its edge is concentrated: the best 5% of trades made
   131% of net P&L, and 2020 alone gives +5.4% a month over the pool. In India the window is 2.7 years and
   the pool about 21 names, so selection cannot be judged.
4. **Dual momentum has a clear fidelity gap in the US.** Antonacci's absolute test compares against
   T-bills; the code compares against 7-10 year Treasuries. Re-simulated from stored series, the T-bill
   hurdle raises US CAGR at 6, 9 and 12-month lookbacks: **+4.2, +1.0 and +3.0 points**, with drawdown
   shallower each time. It is still behind the S&P 500 in-sample. 2013-2021 holds no long bear market,
   which is the case the rule is built for.
5. **No selection edge: `sector_rotation`, `rs_leaders`, the US sleeve of `momentum_dual_combo`.** US
   sector rotation returns the same as holding every sector equally (11.47% against 11.41%). Its top 3 sit
   at the 68th percentile of random 3-sector picks (India 81st). `rs_leaders` signals return about what
   SPY returned over the same dates (+1.45% against +1.43% over 20 sessions; n = 9,920).

---

## 1. Runs reviewed

Baseline per market: the latest non-archived optimise run of the current version, with the strategy's own
`backtest_args`. Where a market has no such run, the latest version that has one is used, and that is said.

| Strategy | Market | Run | Spec | Window | Note |
|---|---|---|---|---|---|
| quality_momentum | US | 3908 | v1.6-4312e8bd | 2013-01 to 2021-12 | |
| quality_momentum | India | 3968 | v1.6-4312e8bd | **2019-04** to 2021-12 | filings carry equity only from 2018 |
| momentum_vol_scaled | US | 2332 | v1.9-1c842ba9 | 2013 to 2021 | bench IWM |
| momentum_vol_scaled | India | 1832 | v1.9-1c842ba9 | 2013 to 2021 | bench Smallcap 250; 1867 (from 2019-04) is a sub-window |
| momentum_dual_combo | US | 4143 | v1.6-a22c5cbf | 2013 to 2021 | blended bench |
| momentum_dual_combo | India | 1879 | v1.6-a22c5cbf | 2013 to 2021 | blended bench |
| dual_momentum | US | 2344 | v1.1-cb93605d | 2013 to 2021 | |
| dual_momentum | India | 1601 | v1.1-cb93605d | 2013 to 2021 | |
| momentum_baseline | US | 2337 | v1.4-df30f7bc | 2013 to 2021 | |
| momentum_baseline | India | 2831 | v1.4-df30f7bc | 2013 to 2021 | 2832 (from 2019-04) is a sub-window |
| rs_leaders | US | 3395 | v1.4-a97259ef | 2013 to 2021 | |
| rs_leaders | India | 2901 | **v1.2**-a97259ef | 2013 to 2021 | current v1.4 not run in India: v1.3-1.4 changed only the simulator and the RS floor |
| sector_rotation | US | 3975 | v1.2-5e03b52f | 2013 to 2021 | |
| sector_rotation | India | 3984 | v1.2-5e03b52f | 2013 to 2021 | |

**Variants already tested on the current version.** These are not re-proposed:

| Strategy | Variants |
|---|---|
| quality_momentum | US: `--rank vol_scaled`, `--hold-rank 30`, `--top-n 20` (each with and without filings_covered), `--min-turnover 100000000`; India: filings_covered |
| momentum_vol_scaled | US: `--min-turnover` 50M / 100M, `--hold-rank 40`; India: `--min-turnover` 200M / 500M, `--hold-rank` 30 / 40 / 60, `--fill next_open` |
| momentum_dual_combo | India v1.5: `--momentum-weight` 0.3 / 0.7 |
| momentum_baseline | `--regime` index_sma / breadth (v1.0-1.2) |
| rs_leaders | `--rank-by setup` (v1.2), `CONFIRM_WINDOW=100000` (v1.2) |
| sector_rotation | `--weekly` (lookback 4 / 8 / 12 weeks), `--hold-rank 4`, `--ema-exit`, combinations, `--six` |

**Verify badges, quoted and not used.** quality_momentum, momentum_vol_scaled, momentum_dual_combo and
dual_momentum read "Return edge out-of-sample -- pre-set test not passed" in both markets.
momentum_baseline reads that in India and "Run out-of-sample -- no recorded verdict" in the US.
rs_leaders reads "No edge" (optimise) in both markets. sector_rotation reads "No edge" in the US and
"Edge in-sample only" in India.

---

## 2. Scorecards (optimise stage)

Metrics were computed from each run's stored equity and trade tables. Sharpe is daily with rf = 0, as in
the reports. For the portfolio books "avg trade" is P&L ÷ notional per holding period: these books have no
stop, so R is notional-relative. "Top 5%" is the share of total net P&L made by the best 5% of trades. A
share above 100% means the remaining 95% lost money net.

### US

| | quality_mom | vol_scaled | dual_combo | dual_mom | baseline | rs_leaders | sector_rot |
|---|---|---|---|---|---|---|---|
| CAGR | 15.30% | 7.30% | 8.31% | 8.69% | 4.27% | 3.68% | 11.47% |
| Benchmark | SPY 14.01% | IWM 11.03% | blend | SPY 14.01% | SPY 14.01% | SPY 14.01% | SPY 14.01% |
| Excess CAGR | **+1.29** | -3.73 | -4.33 | -5.32 | -9.74 | -10.33 | -2.54 |
| Max DD (bench) | -42.7% (-34.1) | -48.1% (-42.3) | -38.5% (-37.4) | -36.1% | -75.3% | -15.9% | -30.7% |
| Longest DD | 701 d | 1,630 d | 1,061 d | 1,135 d | 2,506 d | 1,788 d | 680 d |
| Sharpe (bench) | 0.60 (0.88) | 0.39 (0.61) | 0.48 (0.75) | 0.54 | 0.31 | 0.42 | 0.72 |
| Sortino / Calmar | 0.56 / 0.36 | 0.37 / 0.15 | 0.44 / 0.22 | 0.49 / 0.24 | 0.30 / 0.06 | 0.26 / 0.23 | 0.68 / 0.37 |
| Volatility | 32.4% | 28.8% | 21.7% | 18.5% | 43.2% | 9.7% | 17.0% |
| Trades (per yr) | 444 (49) | 962 (107) | 989 (110) | 27 (3) | 448 (50) | 124 (14) | 98 (11) |
| Win rate | 52.3% | 47.5% | 47.7% | 55.6% | 44.6% | 36.3% | 67.3% |
| Avg / median trade | +2.87% / +0.65% | +0.57% / -0.50% | +0.65% / -0.50% | +3.61% / +1.12% | +1.21% / -1.75% | +0.40R | +3.12% / +1.60% |
| Profit factor | 1.57 | 1.25 | 1.50 | 2.89 | 1.08 | 1.67 | 3.41 |
| Exposure | 99% | 99% | 100% | 100% | 99% | 41% (days) | 99% |
| Turnover / yr | 5.2× | 6.1× | 4.5× | 2.9× | 5.2× | 1.6× | 3.7× |
| Avg days held | 73 | 67 | 69 | 121 | 72 | 51 | 100 |
| Top 5% of trades | 131% (n=22) | 240% (n=48) | 172% | 63% (n=1) | 696% (n=22) | 132% (n=6) | 46% (n=5) |
| Exit R | rebalance +0.29 | +0.06 | +0.06 / rotate +0.04 | rotate +0.04 | +0.12 | stop -1.07R (51), trend exit +1.43R (73) | rotate +0.03 |

### India

| | quality_mom | vol_scaled | dual_combo | dual_mom | baseline | rs_leaders | sector_rot |
|---|---|---|---|---|---|---|---|
| CAGR | 28.50% | 25.89% | 21.58% | 16.05% | 18.62% | 1.43% | 15.11% |
| Benchmark | N500 17.15%* | SC250 15.44% | blend | N500 13.54% | N500 13.54% | N500 13.54% | N500 13.54% |
| Excess CAGR | +11.35* | **+10.45** | +6.87 | +2.52 | +5.09 | -12.10 | +1.57 |
| Max DD (bench) | -30.9% (-38.3) | -50.5% (-60.8) | -28.3% (-49.3) | -26.3% | -54.4% | -17.5% | -31.4% |
| Longest DD | 161 d | 1,113 d | 931 d | 499 d | 1,113 d | 1,192 d | 691 d |
| Sharpe (bench) | 1.21 (0.86) | 1.21 (0.85) | 1.21 (0.87) | 0.85 (0.84) | 0.82 | 0.29 | 0.86 |
| Sortino / Calmar | 1.14 / 0.92 | 1.10 / 0.51 | 1.07 / 0.76 | 0.75 / 0.61 | 0.76 / 0.34 | 0.17 / 0.08 | 0.84 / 0.48 |
| Trades (per yr) | 124 (45) | 806 (90) | 832 (92) | 26 (3) | 416 (46) | 44 (5) | 42 (5) |
| Win rate | 51.6% | 50.5% | 51.3% | 76.9% | 51.4% | 27.3% | 57.1% |
| Avg / median trade | +5.52% / +0.68% | +3.65% / +0.05% | +3.72% / +0.28% | +5.79% / +2.44% | +3.76% / +0.33% | +0.31R | +8.76% / +1.91% |
| Profit factor | 2.29 | 2.17 | 2.86 | 12.2 | 1.77 | 1.50 | 3.38 |
| Turnover / yr | 4.9× | 5.1× (50 bps a side) | 3.8× | 2.5× | 5.0× | 0.7× | 1.8× |
| Avg days held | 78 | 81 | 82 | 125 | 78 | 40 | 233 |
| Top 5% of trades | 81% (n=6) | 94% (n=40) | 89% | 26% | 115% (n=21) | 166% (n=2) | 38% |

\* quality_momentum India covers 2019-04 to 2021-12 (2.7 years), so it is not comparable with the
2013-2021 columns.

**By year (strategy / benchmark), the books that matter:**

| Year | qm US | SPY | vs India | SC250 | baseline US | baseline India | N500 |
|---|---|---|---|---|---|---|---|
| 2013 | +28.3 | +26.4 | +13.1 | -9.3 | +73.5 | +7.2 | +2.7 |
| 2014 | +7.1 | +11.3 | +93.8 | +69.6 | **-40.1** | +43.2 | +37.8 |
| 2015 | -5.8 | -0.8 | +10.4 | +10.2 | -25.1 | +9.1 | -0.7 |
| 2016 | +16.5 | +9.6 | -11.1 | +0.4 | -21.8 | -8.1 | +3.8 |
| 2017 | +15.4 | +19.4 | +91.2 | +57.3 | +19.0 | +78.6 | +35.9 |
| 2018 | -14.9 | -6.3 | -25.5 | -26.8 | -13.0 | -21.2 | -3.4 |
| 2019 | +22.4 | +28.8 | +7.1 | -8.3 | +107.6 | +10.0 | +7.7 |
| 2020 | **+76.7** | +16.2 | +23.6 | +25.1 | +25.1 | +7.5 | +16.7 |
| 2021 | +12.2 | +27.0 | +95.7 | +61.9 | -11.0 | +81.4 | +30.2 |

quality_momentum US beats SPY in 4 of 9 years. The year it wins by most, 2020 (+60 points), outweighs the
rest. Excluding 2020 it trails SPY. vol_scaled India beats its segment index in 7 of 9 years.

---

## 3. Is the edge real?

### 3.1 Trials and the deflated Sharpe

Inputs:

- Trials: every optimise run of the strategy in that market, across all versions and variants. Runs that
  differ only in version but give identical results are counted once in "distinct".
- Deflated Sharpe ratio (Bailey and López de Prado): SR₀ = σ(trial SRs) × [(1-γ)Φ⁻¹(1-1/N) + γΦ⁻¹(1-1/(Ne))],
  with T the number of daily returns, and skew and kurtosis taken from the baseline's daily returns.
- It is computed twice: on the Sharpe (H₀: SR = 0) and on the **information ratio against the strategy's
  own benchmark** (H₀: no edge over buy-and-hold). The second is the one that answers the brief.

| Strategy | Mkt | Trials (distinct) | Sharpe | DSR (SR>0) | IR vs bench | σ(trial IR) | IR₀ | PSR(IR>0) | **DSR (IR)** |
|---|---|---|---|---|---|---|---|---|---|
| quality_momentum | US | 22 (21) | 0.60 | 0.91 | +0.21 | 0.12 | +0.23 | 0.73 | **0.47** |
| quality_momentum | India | 6 (5) | 1.21 | 0.94 | +0.62 | 0.90 | +1.17 | 0.85 | **0.19** |
| momentum_vol_scaled | US | 19 (18) | 0.39 | 0.79 | -0.07 | 0.09 | +0.16 | 0.42 | 0.24 |
| momentum_vol_scaled | India | 25 (21) | 1.21 | 1.00 | +0.77 | 0.20 | +0.41 | 0.99 | **0.86** |
| dual_momentum | US | 2 (1) | 0.54 | 0.95 | -0.37 | 0.00 | 0.00 | 0.13 | 0.13 |
| dual_momentum | India | 2 (2) | 0.85 | 0.99 | +0.13 | 0.18 | +0.09 | 0.66 | 0.55 |
| momentum_baseline | US | 11 | 0.31 | 0.71 | -0.03 | 0.10 | +0.16 | 0.47 | 0.29 |
| momentum_baseline | India | 11 | 0.82 | 0.96 | +0.37 | 0.18 | +0.29 | 0.86 | 0.60 |
| rs_leaders | US | 4 | 0.42 | 0.80 | -0.63 | 0.06 | +0.06 | 0.03 | 0.02 |
| rs_leaders | India | 3 (2) | 0.29 | 0.76 | -0.76 | 0.07 | +0.06 | 0.01 | 0.01 |
| sector_rotation | US | 11 (9) | 0.72 | 0.83 | -0.31 | 0.37 | +0.60 | 0.18 | 0.00 |
| sector_rotation | India | 9 (7) | 0.86 | 0.94 | +0.14 | 0.28 | +0.42 | 0.66 | 0.20 |

The family as a whole has 75 optimise runs in the US and 63 in India. Deflated against all of them
(σ(SR) 0.17 US, 0.31 India), the Sharpe-based DSR is 0.91 for vol_scaled India and 0.92 for combo India,
but 0.71 for quality_momentum US and 0.47-0.65 for the other US books.

**Reading.** Only `momentum_vol_scaled` India clears a deflated test against its own benchmark (0.86).
quality_momentum's US IR (+0.21) is no better than what the best of 22 tries would show by chance
(IR₀ +0.23). India's 0.19 reflects a 2.7-year window and widely spread trials. The combo has no IR here,
because its blended benchmark is not stored as a series. Its in-sample excess is +6.87 (India) and -4.33
(US).

### 3.2 Selection against a matched random null

For each month-end 2012-12 to 2021-11 (n = 108), the script rebuilds the strategy's own eligible pool
with the strategy's own code (`baseline.eligible_scores`, `QualityFilter`; stage boundary 2021-12-31). It
then scores each member on its next-month total return. The null draws N names at random from the same
pool, 1,000 times per month, and averages them over the months. "Pct" is where the strategy's top N falls
in that null distribution. t is for the monthly series of (top N minus pool).

| Book | Mkt | Pool (median) | Top N, %/mo | Pool %/mo | Random 5-95% | Pct | t | Top N compounded / vol | Pool compounded / vol |
|---|---|---|---|---|---|---|---|---|---|
| baseline top 10 | US | 756 | 1.14 | 1.20 | 0.77-1.63 | **43%** | -0.06 | **5.3% / 42%** | 14.1% / 15% |
| baseline top 20 | US | 756 | 1.11 | 1.20 | 0.88-1.55 | 33% | -0.12 | 7.6% / 35% | 14.1% / 15% |
| baseline top 50 | US | 756 | 1.39 | 1.20 | 0.99-1.45 | 92% | 0.39 | 14.0% / 27% | 14.1% / 15% |
| JT: no 200-day filter, top 10 | US | 1,000 | 1.32 | 1.15 | 0.69-1.62 | 74% | 0.16 | 6.1% / 45% | 13.2% / 16% |
| **JT: no 200-day filter, top decile (100)** | US | 1,000 | **1.60** | 1.15 | 1.00-1.31 | **100%** | 1.07 | **17.8% / 24%** | 13.2% / 16% |
| vol_scaled top 20, inverse-vol | US | 609 | 1.40 | 1.22 | 0.95-1.41 | 95% | 0.41 | 14.9% / 24% | 14.4% / 15% |
| quality top 10 | US | 296 | 1.56 | 1.16 | 0.80-1.54 | 97% | 0.72 | 16.2% / 27% | 13.6% / 15% |
| filings_covered top 10 | US | 625 | 1.62 | 1.22 | 0.78-1.65 | 93% | 0.49 | 13.7% / 36% | 14.4% / 15% |
| baseline top 10 | India | 69 | 1.65 | 1.21 | 0.78-1.64 | 95% | 0.99 | 17.6% / 26% | 13.4% / 19% |
| baseline top 20 | India | 70 | 1.49 | 1.10 | 0.84-1.38 | 99% | 1.61 | 16.6% / 21% | 12.0% / 19% |
| **vol_scaled top 20, inverse-vol** | India | 144 | **2.58** | 1.52 | 1.22-1.85 | **100%** | **2.92** | **32.5% / 23%** | 17.3% / 21% |
| JT-style, ₹10cr floor, momentum top 20 | India | 231 | 2.26 | 1.42 | 1.06-1.77 | 100% | 1.92 | 26.5% / 26% | 15.5% / 23% |
| quality top 10 (2018-08 on) | India | 21 | 1.57 | 1.27 | 0.70-1.79 | 85% | 0.84 | 18.4% / 19% | 14.5% / 17% |
| filings_covered top 10 | India | 34 | 2.10 | 1.23 | 0.58-1.94 | 98% | 1.39 | 23.7% / 27% | 13.5% / 20% |

(Top N and pool are gross equal-weighted month-end-to-month-end figures. They are not the runs'
equity curves: no costs, no whole-share rounding.)

**Rank buckets (next-month %, top N = 10 or 20):**

| Book | 1-N | N+1-2N | 2N+1-50 | 51-100 | 101+ | Top minus bottom decile |
|---|---|---|---|---|---|---|
| baseline US | 1.14 | 1.07 | 1.58 | 1.48 | 1.15 | +0.58 (t 0.99) |
| vol_scaled US | 1.35 | 1.13 | 0.54 | 1.32 | 1.21 | +0.23 (t 0.50) |
| quality US | 1.56 | 1.14 | 1.07 | 1.15 | 1.08 | +0.38 (t 0.84) |
| vol_scaled India | **2.54** | **2.07** | **1.71** | **1.58** | **0.29** | **+1.36 (t 1.86)** |
| baseline India | 1.65 | 1.61 | 1.08 | 1.12 | (pool < 100) | +0.63 (t 0.71) |

**Top N minus pool, mean %/month by year:**

| Book | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | Years > 0 |
|---|---|---|---|---|---|---|---|---|---|---|
| vol_scaled India | +1.87 | +2.08 | +0.39 | +0.12 | +1.78 | -0.04 | +0.45 | +1.14 | +2.01 | 8 of 9 |
| quality US | +0.40 | -0.09 | -0.83 | +1.19 | -0.13 | -0.17 | +0.09 | **+5.37** | -2.42 | 4 of 9 |
| baseline US | +3.48 | -5.05 | -3.62 | -0.85 | +0.29 | +0.57 | +4.41 | +4.00 | -4.18 | 5 of 9 |
| JT decile US | +0.94 | -0.34 | -0.65 | -0.47 | +0.71 | +0.54 | +0.25 | **+4.98** | -2.23 | 5 of 9 |

**What this says.**

- **India, vol_scaled.** A real selection edge, consistent across years and monotone in rank. The
  Smallcap-250 excess is earned by picking stocks, not by exposure.
- **India, baseline.** The selection is weaker, because the ₹50cr floor leaves only about 69 eligible
  names. This is the large-cap end where India's premium fades (research ledger, §3.7).
- **US, baseline.** No selection edge at all. The top 10 are the highest-volatility names in the pool:
  83% average 63-day volatility against 31% for the pool. Their arithmetic return equals the pool's, but
  the variance drag destroys the compounded return. The 200-day filter adds nothing here: JT top 10
  without it is just as bad.
- **US, JT decile.** Spreading over a decile recovers a premium, but **2020 is +5.0%/mo of it**. The
  other eight years are 4 positive and 4 negative. It is a plausible fidelity fix with fragile evidence.
- **US, quality.** The quality pool earns the same as the full pool (1.16% against 1.15%), so the filter
  does not pick better companies on average. What it does is take the lottery names out of the top 10.
  The same pattern as the JT decile, through a different route: in both, the edge in 2013-2021 is mostly
  2020.

### 3.3 Signals against what was traded

Portfolio books produce no `backtest_signals`. For them, the "skipped signals" are ranks N+1 onward, shown
in the buckets above.

- **India vol_scaled:** the skipped ranks earn less in order (2.07, 1.71, 1.58, 0.29). Slots are not
  costing anything.
- **US baseline:** ranks 21-100 (1.48-1.58%) beat the top 10 (1.14%). The slots hold the worst part of
  the signal. Holding more names would capture the edge better (the remedy in §6.1).
- **US quality:** the top 10 is the only bucket above the pool, so going to `--top-n 20` dilutes it. That
  is consistent with run 4177 (top 20: 14.06% against 15.30%).

`rs_leaders`, US (v1.4-a97259ef signal rows, 2013-2021). Forward returns are from the next open. 60-session
MFE and MAE are measured from entry.

| Signal set | n | 5 d | 20 d mean / median | 60 d mean / median | MFE60 | MAE60 | SPY same dates, 20 d / 60 d |
|---|---|---|---|---|---|---|---|
| All gates + setup | 9,920 | +0.26% | +1.45% / +1.26% | +5.48% / +4.77% | +13.8% | -8.5% | +1.43% / +4.04% |
| High confidence (W1, W2 clear) | 2,175 | +0.47% | +1.72% / +1.61% | +5.20% / +4.86% | +14.3% | -8.9% | |
| High confidence, not traded | 2,051 | +0.50% | +1.77% | +5.25% | +14.3% | -8.8% | |
| Traded | 124 | +0.08% | +0.76% / +1.56% | +4.28% / +4.10% | +15.3% | -11.1% | +0.80% / +3.30% |
| Watch (failed W1 or W2) | 7,745 | +0.20% | +1.38% | +5.57% | +13.6% | -8.4% | |
| G1-G5 + setup, outside the recovery window (G6 failed) | 56,195 | -0.01% | +0.44% | +2.33% | +12.1% | -10.3% | +0.76% / +2.60% |

Over 20 sessions the signals match SPY. Over 60 sessions they lead by about 1.4 points. The volume
confirmation (W1) adds nothing: high confidence 5.20% against watch 5.57%. The trades taken are slightly
worse than the high-confidence signals skipped for cash. G6 does its job: outside the window the same
setups trail SPY. India's signal rows are no longer stored (pruned), so India cannot be checked.

### 3.4 Concentration

| Book | Best 5% of trades: share of net P&L | Best year | Worst year |
|---|---|---|---|
| quality US | 131% (22 trades) | 2020 +76.7% | 2018 -14.9% |
| vol_scaled India | 94% (40) | 2021 +95.7% | 2018 -25.5% |
| baseline US | 696% (22) | 2019 +107.6% | 2014 -40.1% |
| baseline India | 115% (21) | 2021 +81.4% | 2018 -21.2% |
| combo India | 89% (42) | 2017 +67.2% | 2018 -15.9% |
| dual_mom US / India | 63% / 26% (1 trade) | 2017 +28.3% / 2017 +44.9% | 2016 -25.7% / 2016 -15.4% |
| sector_rot US / India | 46% / 38% | 2013 +28.6% / 2014 +50.7% | 2015 -5.3% / 2015 -2.7% |
| rs_leaders US | 132% (6) | 2018 +17.6% | 2015 -3.6% |

Momentum books are right-skewed by nature: a few multi-baggers pay for many small losers. That is
expected, and is why the evidence has to be judged per year, not per trade. Even so, quality US relies on
one year to a degree the India books do not.

### 3.5 Capacity (trade notional at entry against the stock's 20-day average traded value)

| Book | Median weight | Median ADV of names bought | Book size at which a median position is 5% of ADV | 10th percentile |
|---|---|---|---|---|
| vol_scaled India | 5.3% | ₹23.8 cr | ₹25 cr | ₹11 cr |
| quality India | 10% | ₹98.7 cr | ₹49 cr | ₹27 cr |
| baseline India | 10% | ₹88.5 cr | ₹41 cr | ₹26 cr |
| quality US | 10% | $42.2 M | $21 M | $6 M |
| vol_scaled US | 5.4% | $70.6 M | $66 M | $21 M |

At the account sizes this project trades (₹20 lakh, $50k), capacity is not a constraint. vol_scaled
India's thinnest names cap a clean book at roughly ₹10 crore before market impact needs modelling.

---

## 4. The method: fidelity check per strategy

Everything in this section is a **hypothesis to test**. Where the data already speaks, that is said.

### 4.1 momentum_baseline: Jegadeesh and Titman (1993); Carhart / Fama-French UMD

| Rule | Originator / standard practice | This code | Kind | Matters? |
|---|---|---|---|---|
| Portfolio breadth | Top decile, equal- (or value-) weighted, so dozens to hundreds of names | **Top 10** (about 1% of a 750-name US pool) | different | **Yes, US**: §3.2, 5.3% against 17.8% compounded |
| Per-stock trend filter | None | Close above the 200-day average | added | Little: JT top 10 is as poor without it. Keep it in the control |
| Formation | 3-12 months; the factor uses 12-1 (t-12 to t-2) | 252 sessions ending 21 back (12 months, skip 1) | simplified | No |
| Holding | K = 3-12 months, overlapping cohorts (1/K rebalanced each month) | Full monthly rebalance | different | Turnover 5.2×; overlapping cohorts act as a natural buffer. Untested |
| Long / short | Winners minus losers | Long only | different | Known: the long-only leg gets part of the premium and avoids most of the crash risk (Daniel and Moskowitz 2016: crashes come from losers rebounding) |
| Universe | All listed, micro caps often excluded | Today's listed names (survivorship), $10 / ₹0 price floor, turnover floor | added | Survivorship flatters; stated in the caveats |

Known choice: this strategy is the naive **control** (CLAUDE.md, its own docstring). Close its gaps in a
*new* strategy or as `--bt` research runs. Leave this one as it is.

### 4.2 momentum_vol_scaled: Barroso and Santa-Clara (2015)

| Rule | Originator | This code | Kind | Matters? |
|---|---|---|---|---|
| Vol scaling | Scale the **whole momentum portfolio's** exposure to a constant target (12% a year in their paper), from its own trailing 6-month daily realised variance | Ranks each stock by return ÷ own volatility, weights by inverse 63-day volatility, **no portfolio scaling** (`vol_target` None) | different | Stated openly in the thesis. For a long-only book the crash it targets is mostly absent, so it plausibly matters less. Legacy India test: vol targeting cut CAGR at every level (momentum-trend-research §6). **Untested in the US optimise stage** |
| Portfolio | Long-short deciles | Long-only top 20 | different | As 4.1 |
| Ranking | 12-1 return | 12-1 ÷ 252-day volatility ("Sharpe momentum") | different | **Helps in India** (vol_scaled top 20 2.58%/mo against JT momentum top 20 2.26% on comparable pools). Nothing in the US |
| Universe | n/a | ₹10cr / $20M floor, no liquidity rank | known choice | India's premium lives in small and mid caps (ledger §3.7). The US floor sweep (50M-500M) is done |
| Benchmark | n/a | Smallcap 250 / IWM | known choice | Correct: segment beta is not counted as skill |
| Market filter | n/a | Removed in v1.7 after failing its verify run | known choice | Do not re-propose |

### 4.3 quality_momentum: quality (Asness, Frazzini and Pedersen, "Quality minus junk") plus momentum

| Rule | Literature | This code | Kind | Matters? |
|---|---|---|---|---|
| Quality definition | Composite score: profitability, growth, safety, payout, ranked cross-sectionally | Hard screen: TTM ROE ≥ 12% and TTM sales growth ≥ 0 | simplified | The screen removes junk, which is what the data says it does (§3.2). A composite rank is untested |
| How the two combine | Usually an integrated rank (average of ranks) or a sequential screen | Sequential: screen, then top 10 by momentum | common practitioner form | OK |
| Breadth | Factor portfolios are broad | Top 10 | different | In the US, top 10 beats top 20 inside the quality pool (§3.3, run 4177). Breadth is not the gap here |
| "Quality momentum" (Gray and Vogel 2016) | 12-1 top decile, then the 50 smoothest paths ("frog in the pan"), quarterly rebalance | Not used. `--rank path_quality` exists as a whole-pool ranker only | missing | A different idea under the same name. Untested as a second-stage filter |
| Point-in-time data | Required | Filing dates or lags, a backfilled universe, the coverage control | faithful | Good. Judged against filings_covered |

### 4.4 dual_momentum: Antonacci, *Dual Momentum Investing* (2014), Global Equities Momentum

| Rule | Antonacci (GEM) | This code | Kind | Matters? |
|---|---|---|---|---|
| Relative menu | S&P 500 against ACWI ex-US | US: S&P 500 TR, Nasdaq 100, EFA, gold. India: Nifty 50 TR, Midcap 50, Nasdaq 100 in INR, gold | added | GEM-faithful US: 8.37% against 8.69% as coded. India GEM-like (N50 against NDX_INR): 11.10% against 16.05%. **The wider menu helps in India.** Keep it |
| Absolute hurdle | The equity's 12-month return **against T-bills** | Against the **safe asset's** return (7-10y Treasuries in the US) | **different** | **Yes, US**: the T-bill hurdle gives 11.69% / -28.6% against 8.69% / -36.1% (12-month lookback). Better at 6 and 9 months too (§5.4). India's safe asset is a liquid fund, so India already matches |
| Safe asset | US aggregate bonds | IEF (7-10y) | different threshold | Minor. AGG is not stored |
| Lookback | 12 months | 12 months | faithful | 6 / 9 / 12 months swing CAGR from 6.7% to 13.0% (bond hurdle): **fragile, do not tune** |
| Benchmark | ACWI or 60/40 | SPY price index, while the strategy holds total-return series | different | Flatters the excess by about 2 points (SPY TR 16.13% against price 14.01% over the window). Against the S&P 500 TR the in-sample deficit is -7.4. A 60/40 benchmark (11.00%, -19.2%) is the fair one for an allocation rule |

The method's documented value is avoiding long bear markets (2000-02, 2008). The optimise window holds
none, so in-sample it can only show the cost of insurance. This is a limit of the window, not proof that
the method fails.

### 4.5 momentum_dual_combo

No originator. It applies the "combine uncorrelated strategies" principle to two sleeves, so its fidelity
is its sleeves'. The rule it adds (a 50/50 split, monthly rebalance) is simple and was tested at 0.3 / 0.7
in India. **The US combo inherits a sleeve without a US edge** (vol_scaled US, §3.2), so in the US it
cannot be better than its dual sleeve plus noise.

### 4.6 rs_leaders: O'Neil, *How to Make Money in Stocks*

| Rule | O'Neil | This code | Kind | Matters? |
|---|---|---|---|---|
| Market (M) | Buy only in a confirmed uptrend: from a follow-through day until distribution turns it | Only the **40 sessions** after a 10%-correction recovery | simplified / stricter | Already tested open (`CONFIRM_WINDOW=100000`, run 1402): worse in the US. The signal data agrees: setups outside the window trail SPY (§3.3). Known choice |
| Base | Flat base: at least 5 weeks, at most about 15% deep; cup-with-handle 7-65 weeks, 12-33% | 15-40 sessions, at most 25% deep | different threshold | Untested. A 15% depth is the textbook flat base |
| Buy point | Buy-stop at the pivot, within 5% of it | Close through the pivot, buy next open | different | Pays gaps. Known (caveats) |
| Volume | At least 40-50% above average on the breakout | 1.4× the 50-day | faithful | The data says W1 adds nothing (§3.3) |
| Stop | 7-8% below the buy | 10-session low, capped at 8% | similar | OK |
| Profit taking | Take most gains at +20-25%; hold big winners past 8 weeks | No partial; 50-day close exit | missing | `PARTIAL_GAIN_PCT` exists but is not traded (`--no-target`). Untested |
| RS | RS rating 80+, ideally 90+, in leading groups | RS ≥ 80, group ≥ 80 | faithful | |

It is not a portfolio momentum strategy. It is a breakout system with low exposure (41% of days), and it
belongs with the base-breakout family's review.

### 4.7 sector_rotation: Moskowitz and Grinblatt (1999, industry momentum); Faber (2010, sector relative strength)

| Rule | Originator | This code | Kind | Matters? |
|---|---|---|---|---|
| Ranking | Past 6-12 month return, top 3 of about 10 sectors (Faber also averages 1/3/6/12 months) | 126-session return, top 3 | faithful | Faber's average lookback: US 9.29%, India 12.80%. **Worse** than as coded (§5.5) |
| Trend / absolute filter | Faber tests a 10-month SMA filter; Antonacci uses dual momentum on sectors | None by default | missing | Cuts drawdown (US -30.7% to -21.7%, India -31.4% to -22.5%) but costs 2.4-3.5 points of CAGR in-sample (§5.5) |
| Choice set | 9-10 sectors or 20 industries | US 11 SPDRs; India 2-6 series before 2021 | different | India ranks almost nothing for half the window |
| Benchmark | Equal-weight sectors / market | SPY / Nifty 500 | different | The fair control is equal-weight sectors: US 11.41% against 11.47%. The whole US deficit is cap-weight against equal-weight, not selection |

---

## 5. Diagnosis per strategy

### 5.1 quality_momentum: a real but concentrated US edge; India unproven in-sample

- **Where it comes from:** removing the high-volatility names from the momentum top 10 (§3.2), not
  better-than-average companies.
- **Losers:** 2018 (-14.9% against -6.3%) and 2021 (top 10 minus pool -2.42%/mo). 2015 and 2017 trail too.
- **Concentration:** 131% of net P&L is in 22 trades, and 2020 is about the whole margin.
- **Not explained by coverage:** filings_covered (run 3911) makes 13.26%, -56.7%. The filter adds +2.04
  CAGR and 14 points less drawdown against its own control.
- **Already measured:** `--min-turnover 100000000` (run 4183) is better on every axis (18.42%, -39.3%,
  Sharpe 0.73 against 15.30%, -42.7%, 0.60). It has one value; its neighbours are untested.
- **India:** 2.7 years and about 21 names a month passing (§3.2). In-sample, filings_covered beats the
  filter (39.05% against 28.50%). No in-sample case for the filter in India. Its verify pass is the only
  evidence there, and it is not used here.

### 5.2 momentum_vol_scaled: protect India; the US has nothing to fix

- **India:** every check passes (§3). The weaknesses are the 2018 small-cap year (-25.5%), the -50.5%
  drawdown over 2013-2021, and costs (the caveats: +1.82 excess at 100 bps legacy).
- **Already tried and failed:** rank buffers (hold-rank 30/40/60 cost 0.8-2.9 points CAGR with deeper
  drawdowns), higher floors (₹20cr / ₹50cr cost 4.5-9.8 points) and the market filter (failed verify).
- **US:** no selection edge at any floor (§3.2, the variant runs). Fidelity work cannot help when the
  ranking itself does not separate winners in this window.

### 5.3 momentum_baseline: a correct control that is a poor book in the US

- **US:** -75.3% drawdown, 2014-2016 lost 40%, 25% and 22%. The cause is the 83%-volatility top 10 (§3.2).
- **India:** +5.09 excess, but with a large-cap pool of about 69 names (₹50cr floor). vol_scaled's ₹10cr
  pool shows where the premium lives.
- Both are expected results for a deliberately naive control. They argue for a JT-faithful sibling
  strategy, not for changing this one.

### 5.4 dual_momentum: the US hurdle is the gap; India is fine as built

Re-simulated from stored series. The as-coded result is reproduced exactly: 8.69%, 27 switches.

| US variant (2013-2021) | CAGR | Max DD | Sharpe | Switches |
|---|---|---|---|---|
| As coded (hurdle IEF, 12 m) | 8.69% | -36.1% | 0.54 | 27 |
| **Hurdle T-bills, 12 m** | **11.69%** | **-28.6%** | **0.68** | 22 |
| Hurdle IEF / T-bills, 9 m | 13.04% / 14.01% | -25.1% / -22.7% | 0.83 / 0.87 | 28 / 29 |
| Hurdle IEF / T-bills, 6 m | 6.74% / 10.95% | -41.2% / -35.7% | 0.45 / 0.66 | 36 / 31 |
| GEM-faithful (S&P TR vs EFA, T-bills, IEF safe) | 8.37% | -33.8% | 0.59 | 16 |
| S&P 500 TR / SPY price / 60-40 | 16.13% / 14.01% / 11.00% | -33.8% / -34.1% / -19.2% | 0.98 / 0.88 / 1.15 | |

The T-bill hurdle is better at all three lookbacks (a plateau, not a peak). At 12 months it is better or
equal in every year (2015 -3% → +9%, 2019 +7% → +16%, 2016 -26% → -22%). The 2016 loss is a whipsaw that
stays.

### 5.5 sector_rotation: no selection edge; the method's modest record holds here

Re-simulated (as coded reproduced: 11.47% / 15.11%):

| Variant (2013-2021) | US CAGR / DD / Sharpe | India CAGR / DD / Sharpe |
|---|---|---|
| As coded (126 d, top 3) | 11.47% / -30.7% / 0.72 | 15.11% / -31.4% / 0.87 |
| + sector above its 10-month SMA, else T-bills | 9.06% / -21.7% / 0.68 | 11.58% / -22.5% / 0.79 |
| Faber average of 1/3/6/12 m | 9.29% / -32.5% / 0.61 | 12.80% / -37.0% / 0.75 |
| Faber average + 10-month SMA | 7.57% / -18.5% / 0.59 | 9.97% / -23.6% / 0.69 |
| 12 m, top 3 | 10.21% / -32.1% / 0.65 | 12.54% / -39.9% / 0.75 |
| 12 m + absolute (beat T-bills) | 8.65% / -32.1% / 0.57 | 9.36% / -23.3% / 0.72 |
| **Equal-weight all sectors (control)** | **11.41% / -36.6% / 0.75** | **12.12% / -37.0% / 0.76** |

Random-pick null: US top 3 at the 68th percentile, India at the 81st (108 months, 1,000 draws). No
faithful variant raises CAGR. The filters trade return for drawdown, which a market filter on the
benchmark would do as well.

### 5.6 rs_leaders: little selection, low exposure

The trend-exit trades (+1.43R, n = 73) pay for the stops (-1.07R, n = 51), and PF is 1.67. But the
signals do not beat SPY over 20 sessions, and the book is in cash most of the time, so it cannot beat
buy-and-hold. India has 44 trades, below the ~30-per-pattern bar for any sub-split.

### 5.7 momentum_dual_combo: right in India, carried by its momentum sleeve

India: Sharpe 1.21, -28.3% drawdown against the sleeve's -50.5%. The diversification works as designed.
US: both sleeves trail; fix the sleeves (§6) before the combo.

---

## 6. The improvement plan, ranked across the family

Rank = expected impact × strength of evidence × robustness × simplicity. Each line is one trial. Pass
criteria are fixed here, **before any run**. Every run is optimise-stage. "Neighbours" means the
pre-listed alternative values must point the same way.

### 6.1 Ranked table

| # | Change | Strategies | Parameter it targets | Type | Evidence | Robustness | Code? |
|---|---|---|---|---|---|---|---|
| 1 | **Paper books for the family's best versions** (vol_scaled India, quality US and India). Only dual_momentum, momentum_baseline and combo (India) have one, since 2026-11-05 | vol_scaled, quality | the forward test | mechanics | `paper_orders`: 3 books, 1 rebalance each, India only | n/a | No (book set-up) |
| 2 | **Dual momentum: absolute hurdle against T-bills, not the safe asset** (Antonacci) | dual_momentum (US), combo US | excess CAGR, drawdown | from the method | Scratch re-sim §5.4: +3.0 CAGR, DD 7.5 points shallower, Sharpe +0.14; better at 6 / 9 / 12 m | Plateau over lookbacks; better or equal in every year at 12 m; one market (India already uses near-cash). Window has no bear | Yes: new constant `ABS_HURDLE` (`"safe"` / `"tbill"`) read in `pick()`; version 1.2, changelog, docs |
| 3 | **JT-faithful breadth for the US momentum books:** top decile (~100) or top 50, no 200-day filter | momentum_baseline as a research run, then a new sibling strategy | volatility, drawdown, excess CAGR | from the method | §3.2: top 10 at the 43rd percentile with 83% vol. Decile 17.8% compounded against 13.2% pool. Top 50: 14.0% / 27% vol. Legacy ledger: top 50, no 200DMA, +2.77 vs SPY | **Fragile:** 2020 is most of the decile's edge, 4 of 8 other years negative | No for the research runs (`--bt`). Yes for a new strategy (registration, docs, version 1.0) |
| 4 | **quality_momentum US: confirm the turnover-floor plateau** (run 4183 at $100M is better on all axes; test $50M and $200M) | quality (US) | drawdown, Sharpe | parameter (CLI floor) | 4183: 18.42% / -39.3% / 0.73 against 15.30% / -42.7% / 0.60 | Unknown until the neighbours run. Adopt only on a plateau | Yes if adopted: a per-market floor attribute, version 1.7 |
| 5 | **Benchmarks that match the method** (reporting only): dual_momentum against 60/40 (S&P TR / IEF) and the S&P 500 TR; sector_rotation against equal-weight sectors | dual_momentum, sector_rotation | honest excess | mechanics | §4.4: SPY price flatters dual's excess by ~2.1 points; §5.5: US sector deficit is cap-weight against equal-weight | n/a | Yes: `benchmark_key` per strategy, docs. No version bump (no rule changes) |
| 6 | **Barroso and Santa-Clara portfolio vol target on the US books** (`--vol-target 0.20`, neighbours 0.15 / 0.25) | quality US, momentum_baseline US | drawdown | from the literature | Untested in the US. Legacy India: cut CAGR at every target (contradicts) | Must hold at all three targets | No (`--bt`) |
| 7 | **Quality second stage, Gray-Vogel style:** within the quality pool, take the top 20 by 12-1 and hold the 10 with the smoothest path | quality (US) | volatility, concentration | from the literature | Untested here; the published result is US practitioner evidence | One trial; must beat the default on both halves of the window | Yes: a new `--variant`, version 1.7 |
| 8 | **rs_leaders: O'Neil flat base and profit-taking** (`BASE_MAX_DEPTH_PCT=15`; trade the +22% partial) | rs_leaders | avg R, win rate | from the method | §4.6; signals ≈ SPY, so the upside is small | Low: India n = 44 | Depth: `--const` (rescan). Partial: drop `--no-target` from `backtest_args`, version bump |
| 9 | **Retire or re-scope:** `sector_rotation` as a return strategy (keep as a drawdown-overlay study); `momentum_vol_scaled` and `momentum_dual_combo` in the **US** as "runnable, not recommended" | sector_rotation, vol_scaled US, combo US | n/a | decision | §3.2, §5.5 | Robust: no edge in any check | Status text only |

Not proposed (already tested, or contradicted by the data):

- rank buffers on vol_scaled India;
- market filters on the momentum books (vol_scaled India failed verify; baseline regime variants worse);
- Masonson's sector switches;
- an open recovery window for rs_leaders;
- higher floors for vol_scaled India;
- tuning dual momentum's lookback (fragile: 6.7% to 13.0% between neighbours).

### 6.2 Per key parameter

| Parameter | Ranked changes |
|---|---|
| Excess CAGR | #2 (dual US), #3 (US breadth, fragile), #4 (quality floor) |
| Max drawdown | #2, #4, #6; for vol_scaled India none: its drawdown is the price of its edge, and every fix tried failed |
| Volatility / Sharpe | #3 (83% → 24% book volatility), #7 |
| Concentration (quality US) | #7, #3 (breadth inside the quality pool contradicts it: top 20 worse) |
| Trade count / costs | none needed; turnover is 4-6× and costs are inside the runs at 5 / 50 bps |

### 6.3 Pass criteria, fixed before any run

All comparisons are with the same strategy's baseline run (§1), same stage, same window.

| # | Must improve | Must not worsen beyond | Robustness checks |
|---|---|---|---|
| 2 | US CAGR ≥ +1.5 points over run 2344 **and** max drawdown no deeper | Switches ≤ 30 | Same direction at `--lookback-months 9` and `6`; at least 6 of 9 years no worse than as coded by more than 2 points; cost doubled to 20 bps still passes |
| 3 | Compounded CAGR above SPY (14.01%) **and** above run 2337 by ≥ 5 points; volatility ≤ 30% | Max DD no deeper than -45% | Top 50 and top 100 both pass; excess > 0 with 2020 removed (yearly table); `--cost-bps 10` still passes |
| 4 | Sharpe ≥ 0.70 and max DD ≥ 3 points shallower than run 3908, at **both** $50M and $200M | CAGR no lower than 3908's 15.30% | Must also beat filings_covered at the same floor by ≥ 2 CAGR points (the v1.6 rule) |
| 6 | Max DD ≥ 8 points shallower than baseline at all three targets | CAGR ≤ 2 points lower | Monotone or flat across 0.15 / 0.20 / 0.25 |
| 7 | CAGR ≥ default and annualised volatility ≥ 3 points lower | Max DD no deeper | Holds in 2013-2016 and in 2017-2021 separately; beats filings_covered by ≥ 2 points |
| 8 | Avg R ≥ +0.1R over run 3395, PF ≥ 1.67 | Trades ≥ 100 (US) | US and India same direction |

### 6.4 Commands (optimise stage; one change per run first, combinations after)

```bash
# 3 -- JT breadth, research runs on the control (no code)
python -m jobs enqueue backtest --market us --strategies momentum_baseline --stage optimise --bt '--top-n 50 --no-trend-filter'
python -m jobs enqueue backtest --market us --strategies momentum_baseline --stage optimise --bt '--top-n 100 --no-trend-filter'
python -m jobs enqueue backtest --market us --strategies momentum_baseline --stage optimise --bt '--top-n 50'

# 4 -- quality floor neighbours (no code)
python -m jobs enqueue backtest --market us --strategies quality_momentum --stage optimise --bt '--min-turnover 50000000'
python -m jobs enqueue backtest --market us --strategies quality_momentum --stage optimise --bt '--min-turnover 200000000'
python -m jobs enqueue backtest --market us --strategies quality_momentum --stage optimise --bt '--min-turnover 50000000 --variant filings_covered'
python -m jobs enqueue backtest --market us --strategies quality_momentum --stage optimise --bt '--min-turnover 100000000 --variant filings_covered'
python -m jobs enqueue backtest --market us --strategies quality_momentum --stage optimise --bt '--min-turnover 200000000 --variant filings_covered'

# 6 -- portfolio vol target (no code)
for t in 0.15 0.20 0.25; do
  python -m jobs enqueue backtest --market us --strategies quality_momentum --stage optimise --bt "--vol-target $t"
done

# 2 -- after the dual_momentum v1.2 code change (T-bill hurdle as the default in the US)
python -m jobs enqueue backtest --market us --strategies dual_momentum --stage optimise
python -m jobs enqueue backtest --market us --strategies dual_momentum --stage optimise --bt '--lookback-months 9'
python -m jobs enqueue backtest --market us --strategies dual_momentum --stage optimise --bt '--lookback-months 6'
python -m jobs enqueue backtest --market us --strategies dual_momentum --stage optimise --bt '--cost-bps 20'
python -m jobs enqueue backtest --market us --strategies momentum_dual_combo --stage optimise

# 8 -- rs_leaders base depth (rescan)
python -m jobs enqueue backtest --market us --strategies rs_leaders --stage optimise --const BASE_MAX_DEPTH_PCT=15
python -m jobs enqueue backtest --market india --strategies rs_leaders --stage optimise --const BASE_MAX_DEPTH_PCT=15
```

**Code notes.**

- **#2:** `backtesting/dual_momentum.py` `pick()` and `run()`, plus `current_pick()`, which shares the
  rule. Add a hurdle series (`CASH_YIELD` accumulated, as `index_data.cash_rate_series`). Bump to 1.2 with
  a changelog entry. Update `entry_rules`, the absolute-test caveat (it currently says the T-bill gap
  exists) and `param_docs`. Run `tests.test_strategy_docs` and `tests.test_strategy_versions`.
  `momentum_dual_combo` picks it up through its sleeve; its caveats already say sleeves version
  separately.
- **#3, if it passes:** register a new `PortfolioStrategy` (e.g. `momentum_decile`) rather than editing
  the control. It needs every doc attribute, `strategies/__init__.py` registration and a version 1.0.
- **#4 / #7:** quality_momentum 1.7 with a per-market floor attribute or a new `--variant`. The variant
  set is "fixed before any run, not to be added to after one", so #7 is a new version with its own
  pre-registered criterion, as written above.
- **#5:** `benchmark_key` per strategy (the vol_scaled pattern). Reporting only, but the Strategies page's
  edge badge will move. Say so in the status.

### 6.5 What would justify a verify run

For each version, once and only after its optimise pass:

- **dual_momentum v1.2 (US):** pass criteria #2 met. The verify criterion is written before the run:
  excess over **60/40** > 0 and drawdown no deeper than the S&P 500 TR.
- **A JT-decile sibling (US):** #3 met including the 2020-excluded check.
- **quality_momentum 1.7:** #4 or #7 met.

**No new verify for vol_scaled India.** It has had its verify, and nothing here changes it.

---

## 7. Shared fixes

1. **Paper books** for every strategy whose verify return edge held (vol_scaled, quality, dual, combo),
   in the markets where the in-sample edge exists. Today only three India books exist, opened 2026-11-05
   with one rebalance each.
2. **Benchmark honesty.** A strategy holding total-return series (dual_momentum, sector ETFs) is
   compared with a price index. Strategies whose method has a natural control should report against it:
   equal-weight sectors, 60/40, the segment index (vol_scaled already does).
3. **Breadth before rules in the US.** The US momentum books (baseline, vol_scaled, quality,
   combo-momentum) all hold 10-20 names from pools of 300-1,000. In that market the top ranks are
   lottery stocks. Any new US momentum rule should be tested on a broad book first (§6.1 #3), or it is
   tuning noise.
4. **Report volatility drag.** Arithmetic monthly return against compounded return (§3.2) explains most
   of the US gap. The report's headline shows only the compounded figure.

---

## 8. The family's best version and its paper-trading gate

**Best version today: `momentum_vol_scaled`, India, v1.9, as it stands.** It is the only strategy with a
selection edge that holds against a matched random null (100th percentile, t 2.9, 108 months), is
monotone in rank, holds in 8 of 9 years and survives deflation for its 25 trials (DSR on IR 0.86). Next
best: `momentum_dual_combo` India, which holds the same edge with roughly half the drawdown (-28.3%
against -50.5%) for about 4 points of CAGR. For a holder who cannot sit through a 50% drawdown, the combo
is the version to run.

**Paper-trading gate** (forward data from the first paper rebalance; write it down before the book opens):

| Item | vol_scaled India | combo India |
|---|---|---|
| Book | Open one (none exists) | Exists since 2026-11-05 (1 rebalance) |
| Minimum record | 12 month-end rebalances **and** at least 150 closed holding periods | 12 rebalances |
| Must hold | Excess CAGR over the Smallcap 250 ≥ +3 points (the in-sample +10.45, discounted ~70% for selection and costs) | Excess over the blended benchmark > 0; max DD no deeper than 1.2× the benchmark's |
| Selection check | Top 20 against the eligible pool, monthly, using this review's method: mean ≥ +0.3%/mo with ≥ 7 of 12 months positive | n/a |
| Costs | Real fills against the close: slippage plus charges ≤ 50 bps a side on average (the backtest's assumption) | Same for the momentum sleeve |
| Stop the paper test | Book 15 points behind the Smallcap 250 at any point, or realised costs above 100 bps a side | Book behind the blend by 10 points |

For quality_momentum, open a paper book in both markets with the same gate shape. Excess over SPY / Nifty
500 must be ≥ +2 points, and it must beat a paper filings_covered control by ≥ 2 points over 12
rebalances, because its US in-sample case rests on one year.

---

## 9. What could not be determined

| Question | Why not | What would settle it |
|---|---|---|
| Survivorship effect on the momentum books | Delisted names are not stored | Point-in-time constituent lists (Nifty Smallcap 250 history, CRSP-like data) |
| quality_momentum India's selection edge | 2.7 years, about 21 names a month pass | Forward data. The filings cannot reach further back |
| The combo's IR and deflated IR | Its blended benchmark is not stored as a series | Store the blend in the run's equity table |
| rs_leaders India signal edge | Signal rows for India's spec are pruned | A rescan, or keep both versions' rows |
| Dual momentum's documented bear-market value | 2013-2021 has no long bear | A full-stage context run from 2005 (US) is allowed as context, never a verdict |
| Whether the JT decile's 2020 dependence is structural | One window | Forward data, or a run from 2001 (full stage, context only) |
| Real execution costs of vol_scaled India's thin names | Flat bps model | The paper book's fills |

---

### Method notes

- The pool study and the null are gross of costs and use total-return closes (`baseline.load_prices`'
  `tr`), month-end to month-end. They match the runs' rebalance dates but not their whole-share rounding.
- The dual-momentum and sector re-simulations reproduce the stored runs' CAGR and switch counts exactly
  before any variant was computed. They are scratch estimates, not backtests, and do not replace the
  optimise runs in §6.4.
- No verify-stage trade, table or figure was opened. The verify edge badges are quoted in §1 only.
