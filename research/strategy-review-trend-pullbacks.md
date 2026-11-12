# Strategy family review: trend pullbacks and stages

*Written 2026-11-12. Strategies: `stage_analysis` (v2.12), `trend_pullback` (v1.5), `ema_pullback` (v1.1),
`ema100_trend` (v1.0), `supertrend` (v1.1), `kell_cycle` (v1.2). Brief: `research/strategy-family-review-briefs.md`,
family 3. Procedure: `/backtest-review`, one strategy at a time.*

Every figure below comes from the **optimise stage (2013-01-01 → 2021-12-31)**, so all of it is in-sample.
Verify runs were not opened. Only their verdicts are quoted:

- `stage_analysis` 2.11 failed verify in both markets.
- `trend_pullback`'s US `--idle-index` variant (1.4) failed verify.
- No other strategy in this family has a verify run.

Figures marked *computed* were worked out here from stored data with scratchpad scripts. The sources were the
`prices` table up to 2021-12-31, the run tables, and each baseline's signal partition (`bsig_<key>__<spec>`).
They were not read from a report. No code was changed, no job was queued and nothing was committed.

## In short

- **None of the six strategies beats buy-and-hold in the optimise window**, except `kell_cycle` in India
  (+1.74 points a year). All twelve baselines have a lower Sharpe than their index, again except Kell India.
- **The setups add almost nothing to the screens they draw from.** This was measured on 60-session returns
  over and above an "above the 200-day, liquid" universe, on the same dates:
  - In the US, every setup's signals are within ±0.5 points of the screen's own bars.
  - In India, the excess comes from the screen, not the entry. Trend Template bars make +3.4 points and
    Established-uptrend bars +3.1 points, while Kell's setups add −0.3 and the pullback setups +0.1.
  - Only Weinstein's breakout adds something over its screen: +1.4 points in India and +0.5 in the US.
- **Where the edge is, it is momentum and group strength, not pullback timing.** The industry group's RS
  rating at the signal separates signals in all six strategy × market cases tested (three strategies, two
  markets). Signals in groups rated above 80 did best in every case. In India the gain is spread across
  everything above 40; in the US it sits mostly in the top bucket. It is not stable year to year. This is Weinstein's sector rule and Kell's "leaders
  in leading groups". It is also the best-documented effect behind both (industry momentum). It needs no code:
  `--min-group-rs`.
- **The second leak is idle capital.** Average invested capital was 28% (`trend_pullback` India), 40%
  (`stage_analysis` India) and 54% (`kell_cycle` India). India's ₹50 crore liquidity floor leaves
  `stage_analysis` about 450 stocks and 188 accepted plans in nine years.
- **The family's best version today is `kell_cycle` in India.** It has the family's only alpha with a t-statistic
  near 2 (10.5% a year, t = 2.03, beta 0.38) and the only Sharpe above the index (0.96 against 0.86). Its trades
  sit at the 100th percentile of a matched random-entry null. Its deflated Sharpe is 0.995 over 3 trials.
  - It still fails its own pre-set criteria: drawdown −35% against a bar of −25.9%, and it is negative without
    its best 5% of trades.
  - The rules that run today (1.1 market filter, 1.2 switch) have not been run yet; they are queued.
- **`stage_analysis` is the most faithful implementation of a documented method, and the most under-built.**
  - Its signals carry the family's only setup-level edge.
  - The data supports three Weinstein rules that the code softens or leaves out: group strength, positive RS,
    and the 2× volume test.
  - It failed verify (2.11), so any refinement is a new version, judged on forward data.
- **Retire `ema_pullback`, `supertrend` and `ema100_trend`.** None of them comes from a method with a documented
  record. None has a selection edge (the US `supertrend` picks are at the 3rd percentile of random). Their
  variants have already been tried.
- **`trend_pullback` cannot be judged without a 1.5 baseline.** Both 1.5 filters lowered the portfolio's
  average R, but they are being compared with a 1.4 run made before the price repairs. Run the 1.5 baseline,
  then retire the strategy unless the group filter rescues it.

## Runs reviewed

**Baselines.** Each is the latest non-archived optimise run of the strategy's own `backtest_args`, with no
overrides.

| Strategy | Current version | Baseline version | US run | India run | Rules in between |
|---|---|---|---:|---:|---|
| `stage_analysis` | 2.12 | 2.11 | #2263 | #2264 | 2.12 adds G10 (Stage 2's age), off by default, so it trades as 2.11. The 2.12 baseline and variants are queued (#1580–#1590) |
| `trend_pullback` | 1.5 | 1.4 | #1742 | #2994 | 1.5 adds two switches, both off. No 1.5 baseline exists; only variants (#4160, #4161, #4184, #4185; India #1563 running, #1564 queued) |
| `ema_pullback` | 1.1 | 1.1 | #1713 | #1710 | — |
| `ema100_trend` | 1.0 | 1.0 | #1773 | #2724 | — |
| `supertrend` | 1.1 | 1.1 | #3470 | #4166 | — |
| `kell_cycle` | 1.2 | 1.0 | #3919 | #3910 | 1.1 swaps in the Minervini market filter with the small-cap trend; 1.2 adds `MIN_STOP_ATR`, off by default. The 1.2 baseline and `MIN_STOP_ATR` 1.5 and 2.0 are queued (#1555–#1558, #1607, #1608) |

**Variants already tested** (optimise stage; not re-proposed below):

| Strategy | Variants tested |
|---|---|
| `stage_analysis` | `STOP_BUFFER_PCT=1`, `TREND_EXIT_BELOW_PCT=3`, `EXIT_ON_LOWER_HIGH=1`, `EXIT_DIST_WEEKS=3`, `EXIT_ON_STAGE3=1`, `W1_RANKS_ONLY=1`, `G7_BLOCK_STAGE=3` (alone and together), `VOL_MULT=0`, `MAX_STOP_PCT=100`, `--pe`, `--rank-by setup`. Queued: `MAX_STAGE2_WEEKS` 26/39/52, `--breakeven-r 2`, US `--max-positions 13` |
| `trend_pullback` | `--exit-mode ma --no-target`, `--idle-index`, `--equal-alloc 10`, `--max-positions 8 --equal-alloc 12.5`, `--pe`, India `--min-dollar-volume` 100M and 200M, `REQUIRE_NEAR_HIGHS=1`, `SKIP_FALLING_ADX=1`, both together |
| `ema_pullback` | `FAST_EMA=10` with `--ma-col ema10`, a 2R bracket with a 10-session time stop, `STOP_BUFFER_ATR` 0.5 and 1.0 |
| `ema100_trend` | `--pe`, `--equal-alloc 10`, `--max-positions 8 --equal-alloc 12.5` (US only) |
| `supertrend` | `MULTIPLIER` 2 and 4, `REQUIRE_SMA200=0`, `--max-positions 20`, `--rank-by random` |
| `kell_cycle` | `BREAK_MODE=2`, `SCREEN_LOOSE=1` |

## Family scorecard (optimise stage, baselines)

Buy-and-hold over the window: SPY 14.01% CAGR (−34.1% max drawdown, Sharpe 0.88); Nifty 500 13.54% (−38.3%,
0.86).

- *Win rate, average R and profit factor* are the reports' figures, on closed trades.
- *Invested*, *alpha*, *beta* and *t* are *computed* from the equity table against the daily benchmark:
  - **Invested** is 1 − cash ÷ equity, averaged over the days.
  - **Alpha, beta and t** come from a CAPM regression of daily returns on the benchmark's daily returns.
    Alpha is annualised as alpha × 252, and *t* is alpha's t-statistic.

| Strategy | Mkt | Run | CAGR | Excess | Max DD | Longest DD (days) | Sharpe | Sortino | Calmar | Trades (closed) | Trades/yr | Win % | Avg R | PF | Avg days | Invested | Turnover | Alpha / t | Beta |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `stage_analysis` | US | 2263 | 9.27% | −4.74 | −21.2% | 472 | 0.82 | 0.73 | 0.44 | 157 (147) | 17.5 | 51.0 | +0.54 | 2.06 | 178 | 76% | 1.37× | +3.2% / 1.05 | 0.44 |
| `stage_analysis` | IN | 2264 | 3.86% | −9.68 | −18.5% | 408 | 0.51 | 0.44 | 0.21 | 95 (88) | 10.6 | 38.6 | +0.26 | 1.41 | 155 | 40% | 0.86× | +0.4% / 0.18 | 0.26 |
| `trend_pullback` | US | 1742 | 11.45% | −2.56 | −18.6% | 574 | 0.80 | 0.73 | 0.61 | 554 (545) | 61.6 | 32.5 | +0.25 | 1.43 | 39 | 82% | 7.64× | +5.4% / 1.23 | 0.46 |
| `trend_pullback` | IN | 2994 | 2.67% | −10.87 | −17.4% | 896 | 0.37 | 0.31 | 0.15 | 154 (153) | 17.1 | 30.7 | +0.15 | 1.25 | 38 | 28% | 2.64× | +0.7% / 0.28 | 0.16 |
| `ema_pullback` | US | 1713 | 0.66% | −13.35 | −39.1% | 1,109 | 0.13 | 0.11 | 0.02 | 1,528 (1,520) | 169.9 | 23.4 | −0.05 | 1.00 | 14 | 78% | 20.1× | −3.9% / −0.69 | 0.43 |
| `ema_pullback` | IN | 1710 | −1.71% | −15.24 | −53.8% | 1,863 | −0.06 | −0.05 | −0.03 | 661 | 73.5 | 25.0 | −0.03 | 0.93 | 15 | 49% | 12.1× | −5.2% / −1.25 | 0.30 |
| `ema100_trend` | US | 1773 | 8.96% | −5.05 | −28.2% | 723 | 0.59 | 0.54 | 0.32 | 535 (526) | 59.5 | 25.9 | +0.35 | 1.41 | 54 | 94% | 5.59× | +0.6% / 0.14 | 0.65 |
| `ema100_trend` | IN | 2724 | 3.52% | −10.02 | −27.1% | 794 | 0.33 | 0.32 | 0.13 | 361 (354) | 40.1 | 22.6 | +0.15 | 1.20 | 46 | 73% | 5.55× | −1.8% / −0.47 | 0.43 |
| `supertrend` | US | 3470 | 3.25% | −10.76 | −38.6% | 1,606 | 0.28 | 0.25 | 0.08 | 628 (618) | 69.8 | 40.1 | +0.09 | 1.08 | 50 | 90% | 6.31× | −3.9% / −0.95 | 0.58 |
| `supertrend` | IN | 4166 | 9.96% | −3.58 | −27.7% | 583 | 0.77 | 0.73 | 0.36 | 455 (445) | 50.6 | 42.7 | +0.24 | 1.64 | 59 | 77% | 4.52× | +3.1% / 0.87 | 0.52 |
| `kell_cycle` | US | 3919 | 2.28% | −11.73 | −24.1% | 1,083 | 0.21 | 0.18 | 0.09 | 718 (712) | 79.8 | 28.1 | +0.00 | 1.05 | 26 | 73% | 10.4× | −2.3% / −0.38 | 0.44 |
| `kell_cycle` | IN | 3910 | 15.28% | +1.74 | −35.2% | 731 | 0.96 | 0.86 | 0.43 | 381 (380) | 42.3 | 36.1 | +0.27 | 1.70 | 33 | 54% | 6.60× | +10.5% / 2.03 | 0.38 |

**R by exit reason** (*computed* from the trades tables; all trades, open ones included):

| Strategy | Mkt | Trend / target exits: n, avg R | Stops: n, avg R | Median days, stops |
|---|---|---|---|---:|
| `stage_analysis` | US | 114 trend exits, +0.99R | 33, −1.01R | 31 |
| `stage_analysis` | IN | 62, +0.81R | 26, −1.05R | 35 |
| `trend_pullback` | US | 177 targets, +2.99R | 368, −1.07R | 17 |
| `trend_pullback` | IN | 47 targets, +2.83R | 106, −1.04R | 15 |
| `ema_pullback` | US | 759, +0.97R | 761, −1.06R | 2 |
| `ema_pullback` | IN | 341, +0.92R | 320, −1.05R | 2 |
| `ema100_trend` | US | 339, +1.15R | 187, −1.12R | 6 |
| `ema100_trend` | IN | 269, +0.53R | 85, −1.04R | 6 |
| `supertrend` | US | 481, +0.42R | 137, −1.07R | 13 |
| `supertrend` | IN | 379, +0.46R | 66, −1.01R | 18 |
| `kell_cycle` | US | 366 EMA breaks, +1.08R | 346, −1.14R | 6 |
| `kell_cycle` | IN | 239, +1.10R | 141, −1.12R | 7 |

## Is the edge real? (all six)

### Trials and deflated Sharpe (*computed*)

**Trials** are the strategy's optimise-stage runs in that market, across versions and variants. The total for
both markets is in brackets.

**Deflated Sharpe** follows Bailey & López de Prado.

- Expected maximum Sharpe: SR₀ = √V·[(1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(N·e))].
  - V is the variance of the trials' reported Sharpes, converted to daily as ÷√252.
  - N is the number of trials.
  - γ is Euler's constant.
- The baseline is then tested with its own daily-return skew and kurtosis, and T ≈ 2,220–2,270 sessions.

The test is against zero, not against the index. The last column is the probability that the baseline's Sharpe
beats the benchmark's Sharpe: the probabilistic Sharpe ratio (PSR) with SR\* set to the benchmark's daily Sharpe.

| Strategy | Mkt | Trials (both) | Sharpe | Trials' mean / sd | SR₀ (annual) | PSR > 0 | Deflated | PSR > index |
|---|---|---:|---:|---|---:|---:|---:|---:|
| `stage_analysis` | US | 18 (39) | 0.82 | 0.66 / 0.12 | 0.21 | 0.99 | 0.96 | 0.43 |
| `stage_analysis` | IN | 21 (39) | 0.51 | 0.42 / 0.25 | 0.48 | 0.93 | 0.54 | 0.16 |
| `trend_pullback` | US | 10 (18) | 0.80 | 0.58 / 0.18 | 0.28 | 0.99 | 0.94 | 0.40 |
| `trend_pullback` | IN | 8 (18) | 0.37 | 0.39 / 0.17 | 0.25 | 0.87 | 0.64 | 0.08 |
| `ema_pullback` | US | 5 (10) | 0.13 | −0.16 / 0.47 | 0.56 | 0.65 | 0.10 | 0.01 |
| `ema_pullback` | IN | 5 (10) | −0.06 | −0.15 / 0.24 | 0.29 | 0.42 | 0.15 | 0.00 |
| `ema100_trend` | US | 4 (5) | 0.59 | 0.58 / 0.03 | 0.03 | 0.96 | 0.95 | 0.20 |
| `ema100_trend` | IN | 1 (5) | 0.33 | — | 0 | 0.84 | 0.84 | 0.06 |
| `supertrend` | US | 7 (14) | 0.28 | 0.34 / 0.24 | 0.33 | 0.80 | 0.44 | 0.04 |
| `supertrend` | IN | 7 (14) | 0.77 | 0.67 / 0.13 | 0.18 | 0.99 | 0.96 | 0.40 |
| `kell_cycle` | US | 3 (6) | 0.21 | 0.13 / 0.16 | 0.14 | 0.74 | 0.59 | 0.02 |
| `kell_cycle` | IN | 3 (6) | 0.96 | 1.05 / 0.10 | 0.08 | 1.00 | 0.995 | 0.62 |

Read it this way:

- Several baselines have a Sharpe that is probably above zero, even after deflation. That is long-only beta in
  a bull decade, not an edge.
- Only Kell India has a better-than-even chance of beating the index's Sharpe.
- `stage_analysis` India has had 21 trials, and its Sharpe is no better than the best of them by chance (deflated
  0.54).

### Selection vs timing: a matched random-entry null (*computed*)

**How the null was built.** For each baseline trade, 600 random stocks were drawn from the eligible universe on
the trade's entry date and held over the same dates.

- **Trend universe:** the market's liquidity floor (US $10M a day, India ₹50 crore, 20-day average) and a close
  above the 200-day.
- **Liquid universe:** the floor alone.

The table compares close-to-close returns, entry date to exit date. "Pctl" is where the trades' mean falls in the
null distribution of 600 means.

| Strategy | Mkt | n | Trades' mean | Null mean (trend) | 5–95% band | Pctl (trend) | Pctl (liquid) | Index, same windows |
|---|---|---:|---:|---:|---|---:|---:|---:|
| `stage_analysis` | US | 157 | 7.44% | 5.43% | 2.46 – 9.10 | 86 | 89 | 5.75% |
| `stage_analysis` | IN | 95 | 5.83% | 3.21% | −0.16 – 7.17 | 90 | 93 | 3.69% |
| `trend_pullback` | US | 554 | 1.45% | 1.17% | 0.41 – 2.07 | 74 | 82 | 1.16% |
| `trend_pullback` | IN | 154 | 2.04% | 1.05% | −0.28 – 2.40 | 89 | 88 | 1.18% |
| `ema_pullback` | US | 1,528 | 0.60% | 0.25% | −0.01 – 0.56 | 96 | 99 | 0.28% |
| `ema_pullback` | IN | 661 | 0.68% | 0.38% | −0.02 – 0.76 | 89 | 92 | 0.50% |
| `ema100_trend` | US | 535 | 2.91% | 1.97% | 0.81 – 3.45 | 89 | 89 | 1.94% |
| `ema100_trend` | IN | 361 | 1.27% | 1.18% | 0.28 – 2.24 | 56 | 79 | 1.24% |
| `supertrend` | US | 628 | 0.99% | 1.98% | 1.05 – 2.97 | **3** | 5 | 1.90% |
| `supertrend` | IN | 455 | 3.17% | 2.40% | 1.42 – 3.40 | 88 | 90 | 2.60% |
| `kell_cycle` | US | 718 | 0.77% | 0.44% | −0.09 – 0.94 | 87 | 92 | 0.53% |
| `kell_cycle` | IN | 381 | 4.16% | 1.66% | 0.89 – 2.45 | **100** | 100 | 1.66% |

**Caveat: buy-stop entries flatter the trades.** A buy-stop fills only after the price has risen, so the
trades' close-to-close return already contains part of the trigger move. This applies to `stage_analysis`,
`trend_pullback`, `ema_pullback` and `ema100_trend`, so their percentiles in the 74–96 range are an upper bound.

**Kell and Supertrend are unbiased.** `kell_cycle` buys at the signal close and `supertrend` at the next open.

- **Kell India's 100th percentile is a real selection edge**, although part of it is the Trend Template and
  RS ≥ 70 screen (next section).
- **US Supertrend picks worse than random.** Its turn-up comes after a pullback, and those stocks lag.

The trades' gain over the null is not steady by entry year:

- `stage_analysis` US: +33 points in 2017 and −19 in 2020.
- `kell_cycle` India: positive in 7 of 9 years.

### Signal edge vs portfolio mechanics (*computed*)

**What counts as a signal.** Every signal in the run's spec-id partition with all hard gates passed, a setup,
and no watch flag that blocks a buy. Dates run to 2021-12-31.

- `stage_analysis`: a completed breakout with W1 and W2 off.
- `trend_pullback`: S1 or S2, with W1, W2, W8 and W9 off.
- `kell_cycle`: S1–S3.

**Episodes and the yardstick.** Signals in one stock less than 10 sessions apart form one episode, judged from
its first signal. The yardstick is the excess over the same-date trend-universe mean ("x20", "x60", in
percentage points).

| Strategy | Mkt | Signal episodes | x20 | x60 | Traded eps: n, x20 / x60 | Skipped eps: n, x20 / x60 |
|---|---|---:|---:|---:|---|---|
| `stage_analysis` | US | 2,847 | +0.05 | +0.65 | 157: −0.07 / +1.37 | 2,690: +0.06 / +0.60 |
| `stage_analysis` | IN | 626 | +0.60 | +2.15 | 95: +1.73 / +1.89 | 531: +0.40 / +2.20 |
| `trend_pullback` | US | 10,274 | +0.10 | +0.32 | 553: +2.32 / +3.26† | 9,721: −0.03 / +0.15 |
| `trend_pullback` | IN | 3,773 | +1.19 | +3.18 | 154: +3.32 / +6.56† | 3,619: +1.10 / +3.03 |
| `ema_pullback` | US | 23,725 | +0.03 | +0.20 | 1,489: +1.47 / +1.59† | 22,236: −0.06 / +0.10 |
| `ema_pullback` | IN | 2,004 | +0.46 | +0.68 | 633: +0.95 / +1.02† | 1,371: +0.23 / +0.51 |
| `ema100_trend` | US | 5,302 | +0.11 | +0.23 | 474: +1.04 / +0.89† | 4,828: +0.03 / +0.16 |
| `ema100_trend` | IN | 413 | +0.02 | +0.89 | 274: +0.47 / +1.33† | 139: −0.86 / +0.01 |
| `supertrend` | US | 26,208 | +0.01 | −0.14 | 628: +0.20 / **−1.88** | 25,580: 0.00 / −0.10 |
| `supertrend` | IN | 1,811 | +0.22 | +0.07 | 455: **−0.22 / −1.00** | 1,356: +0.37 / +0.43 |
| `kell_cycle` | US | 25,977 | +0.02 | +0.20 | 714: +1.90 / +2.29 | 25,263: −0.03 / +0.14 |
| `kell_cycle` | IN | 11,902 | +1.35 | +3.14 | 380: +3.90 / +6.09 | 11,522: +1.26 / +3.04 |

† Buy-stop fill bias: a traded episode is one whose price went up through the trigger.

What the table shows:

- **US signals have no 20-session edge in any strategy.** Every US signal set is within ±0.11 points at 20
  sessions.
- **India signals have an edge, but it comes from the screen.** See the next table.
- **`supertrend`'s slot ranking chooses worse than the signals it skips** in both markets: 12-1 momentum, among
  turn-ups that come after a pullback.
- **Kell's portfolio layer chooses better.** Its RS ≥ 70 rank and market filter lift traded India episodes to
  +6.1 points at 60 sessions, against +3.0 for the skipped ones. That comparison is free of fill bias.

**Does the setup add anything to the screen?** (*computed*) Wednesday screen bars (gates passed, no setup)
against setup episodes, x60:

| Strategy | Screen bars, US | Setup episodes, US | Setup − screen, US | Screen bars, IN | Setup episodes, IN | Setup − screen, IN |
|---|---:|---:|---:|---:|---:|---:|
| `stage_analysis` (near-highs + weekly gates) | +0.14 (n 226,516) | +0.68 | **+0.54** | +0.76 (18,770) | +2.17 | **+1.41** |
| `trend_pullback` (established uptrend) | −0.21 (6,563) | +0.32 | +0.52 | +3.10 (3,522) | +3.18 | +0.08 |
| `ema_pullback` | +0.28 (54,210) | +0.20 | −0.09 | +1.64 (4,191) | +0.68 | −0.96 |
| `supertrend` (above 200-day) | +0.10 (372,438) | −0.14 | −0.25 | +0.11 (33,842) | +0.07 | −0.05 |
| `kell_cycle` (Trend Template + RS) | +0.39 (169,205) | +0.20 | −0.20 | +3.44 (63,848) | +3.14 | −0.30 |

(`ema100_trend` stores no gate-passing bars without a setup.)

### Concentration (*computed*)

| Strategy | Mkt | Total R | Avg R without the best 5% | Best 5% (n) | Best year | Worst year |
|---|---|---:|---:|---:|---|---|
| `stage_analysis` | US | 92.0 | +0.29 | 8 | 2017 +36.0% | 2020 −12.8% |
| `stage_analysis` | IN | 37.6 | +0.10 | 5 | 2017 +17.6% | 2020 −9.6% |
| `trend_pullback` | US | 141.8 | 0.00 | 28 | 2020 +40.6% | 2016 −9.3% |
| `trend_pullback` | IN | 23.8 | −0.08 | 8 | 2021 +14.2% | 2018 −7.1% |
| `ema_pullback` | US | −56.3 | −0.44 | 76 | 2020 +47.3% | 2021 −28.4% |
| `ema_pullback` | IN | −20.1 | −0.41 | 33 | 2020 +19.1% | 2019 −18.2% |
| `ema100_trend` | US | 205.1 | −0.23 | 27 | 2017 +36.3% | 2016 −6.6% |
| `ema100_trend` | IN | 60.0 | −0.24 | 18 | 2017 +19.5% | 2021 −11.4% |
| `supertrend` | US | 66.0 | −0.12 | 31 | 2013 +35.6% | 2018 −15.5% |
| `supertrend` | IN | 109.7 | +0.02 | 23 | 2017 +32.8% | 2015 −10.3% |
| `kell_cycle` | US | 9.5 | −0.40 | 36 | 2020 +18.9% | 2016 −14.7% |
| `kell_cycle` | IN | 109.7 | −0.08 | 19 | 2021 +58.2% | 2018 −19.9% |

**Only `stage_analysis` stays positive without its best 5% of trades.** That fits its long holds: an average
of 155–178 days.

**Every other strategy's R is its tail.** That is expected of trend exits, but it makes each result fragile to a
handful of trades.

### Market regime at entry (*computed*)

This checks whether a family-wide index filter would help. Average R by whether the index closed above its
200-day at entry:

| Strategy | US above: n, R | US below: n, R | India above: n, R | India below: n, R |
|---|---|---|---|---|
| `stage_analysis` | 127, +0.50 | 30, +0.93 | 84, +0.39 | 11, +0.46 |
| `trend_pullback` | 504, +0.26 | 50, +0.24 | 141, +0.17 | 13, +0.02 |
| `ema_pullback` | 1,425, −0.07 | 103, +0.35 | 594, −0.01 | 67, −0.18 |
| `ema100_trend` | 395, +0.38 | 140, +0.40 | 230, +0.13 | 131, +0.24 |
| `supertrend` | 503, +0.08 | 125, +0.20 | 317, +0.25 | 138, +0.23 |
| `kell_cycle` | 687, −0.04 | 31, +1.24 | 334, +0.37 | 47, −0.27 |

**Not supported in this window.** Trades entered with the index below its 200-day did as well or better in 9 of
12 cases (2013–2021 has no long bear market). So no family market filter is proposed. The strategies' own
filters stay as they are.

---

## 1. `stage_analysis` — Weinstein's stage analysis

**Edge verdict: no edge as built.**

- Excess CAGR is −4.74 points in the US and −9.68 in India, and 2.11 failed verify in both markets.
- The trades sit at the 86th–90th percentile of random (with buy-stop bias). Alpha is +3.2% a year in the US,
  with t = 1.05.
- Weinstein's method has a long practitioner record. So this is treated as an implementation gap, and the fixes
  below come first.

### Fidelity check

The method as Weinstein teaches it is in *Secrets for Profiting in Bull and Bear Markets* (1988).

| Rule | Weinstein | This code | Kind | Matters? Evidence here |
|---|---|---|---|---|
| Universe | Any stock on a weekly chart | Daily Near-highs screen first (G1–G3): above a rising 200-day, within 15% of the 52-week high | Added | **No.** Stage-1 breakouts blocked by G2 did worse at 60 sessions: US −2.05 (n 133), India +2.98 (n 20) |
| What gets bought | The breakout from a Stage 1 base, early in Stage 2 | The base is re-measured every week, so about 95% of entries are new highs in a Stage 2 already 14–25 weeks old | Different | **Mixed.** At the signal, Stage-1-labelled breakouts did not beat Stage-2 ones (x60 US +0.31 vs +0.80, n 522/2,050; India +0.37 vs +3.04, n 121/417). By trade age (2.12 changelog), entries more than 30 weeks into Stage 2 averaged +0.13R against +0.74R (US, n 48). G10 is queued |
| Volume | At least 2× the average of the prior weeks on the breakout week | 2× the 4-week average, measured on a part week mid-week | Simplified | **Supported.** Low-volume (W1) breakouts made x60 −0.09 vs +0.86 in the US (n 21,151 / 1,030) and +0.81 vs +2.02 in India (1,591 / 310). The rule stays; `W1_RANKS_ONLY` gains came from using idle cash |
| Weekly close | Acts on the Friday close | Evaluated every session against the week so far | Different | **Hypothesis.** Breakouts on the week's last session made x60 +3.21 vs +0.58 mid-week in India (n 170 / 140), but +0.72 vs +1.05 in the US (603 / 427) |
| Relative strength | Mansfield RS positive, ideally crossing into positive; never buy negative RS | Positive, *or negative but improving* | Looser | **Supported, small n.** Negative-RS breakouts made x60 −1.30 in the US (n 94) and −2.98 in India (66). RS above +25 made +2.21 in the US (579) and +4.65 in India (141) |
| Sector / group | Buy in Stage 2 groups with strong group RS ("forest to the trees") | Blocks only a sector index in Stage 4 (G8); no group strength | Simplified | **Supported.** By industry-group RS, breakouts above 80 made x60 +1.10 in the US (959) and +7.72 in India (116). Those at or below 40 made −0.10 (449) and −1.72 (160). Year to year it is mixed: in India, positive in 4 of 8 years |
| Market | Buy aggressively in a Stage 2 market; defensive in Stage 3; nothing in Stage 4 | Blocks only Stage 4 (G7) | Simplified | **Not supported here.** `G7_BLOCK_STAGE=3` lowered US CAGR (7.65 vs 8.04, 2.8) and raised India's (2.24 vs 1.31). This is a known choice |
| Overhead supply | Avoid breakouts into nearby resistance; best clear of all overhead | Not modelled | Missing | **Weak.** Breakouts clear of the 2-year high made x60 +1.04 vs +0.33 in the US (775 / 255) and +1.93 vs +2.29 in India (232 / 78) |
| Stops and exit | Initial stop under the base or line; trail under each correction's low; tighten in Stage 3; the investor sells on a weekly close under the line | Stop at the higher of the line and the base low, never moved; sells on a weekly close under the line | Simplified | **Plausible.** Median give-back from the best price was 1.3R in the US and 1.5R in India (2.12 doc). `--breakeven-r 2` is queued as the cheap proxy. Stage 3, distribution and lower-high exits were tested: none beat the line on return |
| Building a position | Half on the breakout, half on the pullback | Single entry | Missing | Low. Not proposed |
| Exposure | Fully invested across 5–10+ groups in a Stage 2 market | 1% risk with ~13% stops, 10 slots: 76% invested in the US, **40% in India** | Different | **Matters.** India has 450 stocks above the ₹50 crore floor and 188 accepted plans in 9 years. The US turned away 5,916 signals for full slots (13 slots queued) |

**Literature.**

- Weinstein's record is practitioner evidence: the book and his *Professional Tape Reader* newsletter. No
  peer-reviewed test of the full method is known to me.
- The parts it relies on have published support:
  - Moving-average timing has modest support (Brock, Lakonishok & LeBaron 1992, on the Dow index).
  - Buying near 52-week highs (George & Hwang 2004) is supported.
  - Industry momentum (Moskowitz & Grinblatt 1999) is supported.
- Long-hold breakout systems are known to live on a few large winners and to give back much of each move at a
  trend exit. Both are seen here.

**Known choices, already tested.**

- No exit tried beat the line on return.
- `W1_RANKS_ONLY` helps India only, through utilisation.
- An audit of the losing trades found no stage-detection error worth a rule.
- The 30-week line is the method's own and was not varied.

### Diagnosis

- **The low return is mostly low exposure, not bad picks.**
  - US: beta 0.44, 76% invested, and avg R +0.54 on 157 trades. That is the family's best trade quality.
  - India: 40% invested, with 4.5 positions on average against 10 slots.
- **The breakout adds a little over its screen** (+0.5 points US, +1.4 India at 60 sessions). Among breakouts,
  RS and group strength separate the good from the bad far more than stage age does.
- **2017 carried the US** (+3.81R a trade, n 4). 2018–2020 were near zero or negative. Below ~30 trades a year,
  yearly cuts are hypotheses.

### Ranked improvements

| # | Change | Targets | Evidence | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| 1 | Industry-group strength filter, `--min-group-rs 40` and `60` | Avg R, excess CAGR | Breakouts by group RS above (n 2,825 US / 577 India); the same ordering in Kell and trend_pullback signals. Weinstein's sector rule | +0.1 to +0.3R a trade | Fewer signals; India may become even more idle | India: improves across every bucket above 40. US: not monotone (40–60 +0.97, 60–80 +0.27, 80+ +1.10). Year-unstable (US driven by 2018 and 2020) | From the method; no code |
| 2 | India liquidity floor ₹50 cr → ₹10 / ₹20 cr, `--bt '--min-dollar-volume 100000000'` and `200000000` | Exposure, excess CAGR (India) | 450 stocks pass and 40% is invested. `trend_pullback` at the same floors improved step by step: CAGR 2.67 → 3.13 → 4.14%, avg R 0.150 → 0.189 → 0.223 (runs 2994, 4015, 4016) | +2 to +4 points CAGR | More slippage in thinner names; drawdown deeper | Two neighbouring values; India only, because the US is slot-bound, not signal-bound | Mechanics; no code |
| 3 | G6 requires positive Mansfield RS (drop "negative but improving"): new constant `G6_REQUIRE_POSITIVE`, default 0 | Avg R, win rate | x60 −1.30 (n 94) and −2.98 (n 66) for negative RS. Weinstein's own rule | Small: removes about 3–10% of signals | None material | Small n: **hypothesis**. One threshold (zero), so no plateau needed | From the method; code (evaluate → rescan) |
| 4 | Signals only on the week's last session: new constant `WEEK_CLOSE_ONLY` | Avg R, India | India +3.21 vs +0.58 x60 (n 170 / 140); US the opposite (+0.72 vs +1.05) | Uncertain | Later entries by up to 4 days | **Fragile**: one market only, small n | From the method; code |
| — | Already queued: G10 26/39/52, breakeven at 2R, US 13 slots (`research/stage-analysis-2.12-variants.md`) | Avg R, give-back, exposure | See that file | — | — | Pass criteria already fixed | — |

## 2. `trend_pullback` — measured pullback in an established uptrend

**Edge verdict: no demonstrated edge; no documented method behind the exact rules.**

- US: alpha +5.4% (t 1.23) at beta 0.46. The trades sit at the 74th percentile of random.
- India is 28% invested.
- The US `--idle-index` variant failed verify.

### Fidelity check

The rules come from "the strategy's original rule set", with no named originator. Against the standard
pullback-to-moving-average methods:

| Rule | Standard methods | This code | Kind | Matters? |
|---|---|---|---|---|
| Trend context | Price above a rising 50- or 200-day; weekly trend up (Elder's triple screen) | 14 gates: weekly, daily and monthly structure, swing lows, momentum, earnings | Added (heavy) | The screen carries the India excess (+3.10 x60), and the pullback adds +0.08 |
| Entry | Buy the resumption over the prior bar's high (continuation), or buy the oversold close (Connors-style mean reversion) | Buy-stop over today's high after a measured pullback; Plan A / Plan B | Close to standard | — |
| Exit | Continuation: trail under swing lows or the 20/50-day. Mean reversion: quick exit on a close above a short average | A fixed measured-move target and a 2R plan test | Different | **The data contradicts a trailing exit here.** The SMA50 exit gave 3.00% against 11.45% (US, run 3850) |
| Plan filter | — | 2R test, ATR/12% stop cap, HIGH CONFIDENCE only: 97% of India's triggered setups are discarded (1,233 WATCH of 1,636) | Added | Explains India's 28% invested; the discarded signals were no worse than the traded ones at the signal level |

**Literature.** Buying pullbacks inside uptrends is mostly practitioner lore.

- Short-term reversal is documented in the cross-section (Jegadeesh 1990; Lehmann 1990).
- Connors & Alvarez's RSI(2) pullbacks are a practitioner test on index stocks, with quick exits.
- Neither supports a fixed 2–3R target system in particular.

**Known choices.** The legacy runs tried seven exit policies; none rescued it. Equal allocation lowered the US
CAGR (6.56% and 7.67% against 11.45%).

### Diagnosis

The 1.5 filters were cut from the US in-sample run on about fifteen slices. In the portfolio, both *lowered*
average R:

| Run | Variant | CAGR | Trades | Avg R | Max DD |
|---|---|---:|---:|---:|---:|
| 1742 (1.4) | baseline | 11.45% | 554 | +0.247 | −18.6% |
| 4160 | `REQUIRE_NEAR_HIGHS=1` | 8.66% | 535 | +0.133 | −17.2% |
| 4161 | `SKIP_FALLING_ADX=1` | 7.73% | 458 | +0.139 | −22.3% |
| 4184 | both | 4.82% | 422 | +0.137 | −27.2% |
| 4185 (India) | `REQUIRE_NEAR_HIGHS=1` | 2.37% vs 2.67% | 108 | +0.173 vs +0.150 | −10.1% |

The 1.5 runs were made after the split repairs and the 1.4 baseline before them, so the comparison is not like
for like. That is why a 1.5 baseline is needed. If the 1.5 baseline lands near 1.4, both filters fail.

### Ranked improvements

| # | Change | Targets | Evidence | Robustness | Type |
|---|---|---|---|---|---|
| 1 | Run the 1.5 baseline (US and India) and judge the 1.5 switches against it | Clean comparison | Above | — | Housekeeping; reuses cached signals |
| 2 | `--min-group-rs 40` / `60` (shared fix, India mainly) | Avg R | Group RS ≤ 40: x60 +0.70 against +2.07 to +4.34 above it (India, n 737 / 2,834); US +0.03 vs +0.76 at 80+ | Plateau; year-unstable (India positive in 4 of 9 years) | From the literature; no code |
| 3 | Retire if neither passes | — | No documented method, 18 trials, and the verify of its only promising variant failed | — | Status change |

## 3. `ema_pullback` — first touch of the rising 21-day EMA

**Edge verdict: no edge. Retire.**

- Sharpe 0.13 (US) and −0.06 (India); deflated 0.10 and 0.15 over 5 trials each.
- Alpha −3.9% (US) and −5.2% (India).
- Setup episodes are no better than its own screen's bars (−0.09 US, −0.96 India at 60 sessions).
- The Learn guide's own event study found that the touch adds nothing, so the method has no documented record to
  fall back on.

**Fidelity.**

- Teachers buy the intraday turn off the EMA with a stop under that day's low. Daily bars buy over the touching
  day's high instead (caveat known).
- A later re-touch is not a new setup.
- Neither gap can be closed on daily data.

**Diagnosis.** Half of the 1,528 US trades are stopped in a median 2 days. Trend exits average +0.97R and stops
−1.06R, at a 24% win rate. Every variant made it worse: a 10-day EMA gave −13.1%, a 2R bracket with a 10-day time
stop −13.2%, and a wider stop buffer stayed negative.

**Improvement.** None proposed; each new variant is another trial with no supported hypothesis. Retiring it needs
a `status` and `caveats` update (and, if it is unregistered, `strategies/__init__.py`).

## 4. `ema100_trend` — Somani's weekly and daily 100-EMA trade

**Edge verdict: no edge.**

- Excess −5.05 (US) and −10.02 (India).
- US alpha +0.6% (t 0.14).
- India trades sit at the 56th percentile of random; US at the 89th, with buy-stop bias.
- The setup adds +0.1 points over the trend universe at 20 sessions.

**Fidelity** (`research/video-strategy-notes.md`):

| Rule | Video | Code | Kind |
|---|---|---|---|
| Universe | Nifty 500 | 500 most-traded by 50-day value, point in time, in both markets | Equivalent (US is an extension) |
| Weekly filter | Weekly close above the 100-week EMA, a 2-year-plus uptrend | Every one of the last 104 weekly closes above a rising 100-week EMA | Faithful, strict |
| Trigger | Daily close back above the 100-day EMA after a dip, then its high breaks | Same; buy-stop for 5 sessions | Faithful |
| Faster trigger | 1-hour chart | Not tested (no intraday bars) | Missing |
| Stop | "Under the low" | Under the dip's lowest low | An interpretation |
| Exit | A close under the EMA, then a break of that candle's low | Same (`ma_low`) | Faithful |
| Above the 200-day, 1% risk sizing, 10 slots | — | Added | Added |

**Diagnosis.**

- The implementation is faithful, and the method (a YouTube setup) has no record.
- US trend exits average +1.15R and stops −1.12R, at a 26% win rate. The total is carried by the top 5% of
  trades: without them the average is −0.23R.
- At 94% invested, US CAGR is 8.96% against 13.20% for SPY scaled to the same exposure.

**Improvement.** Retire. If it is kept, the one untested fidelity gap (the 1-hour trigger) needs intraday data the
store does not have.

## 5. `supertrend` — Supertrend(10, 3), long only, above the 200-day

**Edge verdict: no edge. The US selects worse than random.**

- US trades are at the 3rd percentile of the null.
- In both markets the traded signals underperformed the skipped ones at 60 sessions (US −1.88 vs −0.10; India
  −1.00 vs +0.43).
- The setup is −0.25 (US) and −0.05 (India) against its screen.

**Fidelity.**

- The indicator (Seban's Supertrend) is implemented literally.
- It is not a method with a documented record on single stocks.
- The trend-following-on-stocks study that is usually cited (Wilcox & Crittenden, *Does trend following work on
  stocks?*, 2005, a fund white paper, not peer-reviewed) enters at **new all-time highs** with a **wide (about 10
  ATR) trailing stop**. This code enters on the flip after a pullback with a 3-ATR line. That is a different
  strategy.

**Neighbouring values.**

| MULTIPLIER | US CAGR | India CAGR | Note |
|---|---:|---:|---|
| 2 | −1.17% | 6.36% | v1.0 |
| 3 | 3.25% | 9.96% | v1.1 baselines |
| 4 | 10.31% | 8.32% | |

US CAGR rises with the multiplier while India's peaks at 3: no common plateau. Random ranking raised the US CAGR
(3.96%) and lowered India's (8.24%).

**Improvement.** Retire. The literature-faithful version (new-high entries, wide trailing stop) overlaps
`stage_analysis` and `donchian` (the trend-following family), and would be a new strategy, not a refinement.

## 6. `kell_cycle` — Oliver Kell's cycle of price action

**Edge verdict: an edge in India, in-sample only; none in the US.**

- **India:**
  - Excess +1.74 points and Sharpe 0.96 against 0.86.
  - Alpha +10.5% a year (t 2.03).
  - The 100th percentile of the null, which is free of fill bias.
  - Deflated Sharpe 0.995 over 3 trials. PSR of beating the index's Sharpe: 0.62.
- **But** it fails the spec's own criteria (`research/kell-cycle-spec.md` §6):
  - Its drawdown is −35.2% against a bar of −25.9%.
  - Without its best 5% of trades it averages −0.08R.
- **The current rules (1.1, 1.2) have no run yet.**
- **US:** +0.00R a trade, alpha −2.3%.

### Fidelity check

The method is in *Victory in Stock Trading* (Kell, 2021) and his interviews. His record is the 2020 US Investing
Championship, a one-year contest. That is a practitioner record, not a long audited one.

| Rule | Kell | This code | Kind | Matters? Evidence here |
|---|---|---|---|---|
| Universe | Leading growth stocks in leading groups | Trend Template plus RS ≥ 70 (`--spec`); no group or fundamental test | Simplified | **Group: supported.** Kell India signals in groups rated ≤ 40 made x60 +0.75 against +3.6 to +4.3 in stronger groups (n 2,375 / 8,408); US 80+ +0.77 against about 0. **Fundamentals: not supported.** By SEPA grade, R showed no consistent order (small n) |
| Market | Reads the index's own cycle; aggressive only when it is constructive | The Minervini filter (1.1 adds the small-cap 63-day trend) | Different | Unclear: US entries below SPY's 200-day did better (+1.24R, n 31) |
| Wedge pop | Break of a falling wedge or tight range back over the 10/20 EMA, on volume | After a reversal extension or 5 closes under both EMAs, a close over the 5-day high on 1.3× volume | Simplified (no wedge geometry) | Untested |
| Crossback / base-n-break | First pullback to the rising EMA; tight base and breakout | First CB after WP/BB; 10-day ≤ 15% base on 1.4× volume | Faithful / simplified | India S2 +0.47R (n 142), S1 +0.32 (78), S3 +0.12 (161); US all about 0 |
| Entry timing | Intraday, stop under the day's low | At the close | Different | Daily bars cannot see intraday. A close entry is dearer for the same stop |
| Stop width | Tight: the size comes from the stop | Pop-day low / prior-day low | Faithful | **US expectancy does not depend on width.** By stop-width quartile, US avg R was +0.03, −0.02, +0.05, 0.00 (n about 180 each). The stop-out rate falls from 76% to 31%, but R stays flat. The queued `MIN_STOP_ATR` is therefore unlikely to fix the US |
| Exhaustion sale, EMA break | Sell part into the stretch; sell the rest on the break | 1/3 at the first EX of a leg; the rest at the break (0.5 ATR under EMA20) | Faithful, guessed thresholds | `BREAK_MODE=2`: India better (16.60%), US much worse (−2.87%) |
| Concentration, adds | Few names, built to full size in winners | 8 slots, a 6% open-risk cap, adds while in profit | Simplified | India 54% invested; the open-risk cap refused 2,370 signals and 180 adds |
| Re-entry into the leader | Yes | Yes | Faithful | — |

### Diagnosis

- **India works because of momentum, which the screen supplies.** Trend Template plus RS bars beat the universe
  by +3.4 points at 60 sessions, before any setup.
- **Kell's contribution is in the exits and the rank.** EMA-break exits average +1.10R, and the traded episodes
  beat the skipped ones by +3 points at 60 sessions.
- **The US failure is the market's.** The plain 12-month momentum baseline made −2.1% a year in the US over the
  same window, against 16.5% in India (spec §8).
- **Drawdown is concentrated.** 2018 cost −19.9% in India, and 2014, 2017 and 2021 were each +52 to +58%.

### Ranked improvements

| # | Change | Targets | Evidence | Robustness | Type |
|---|---|---|---|---|---|
| — | Already queued: the 1.2 baseline and `MIN_STOP_ATR` 1.5 and 2.0 | US stop-outs | The stop-width quartiles predict no US gain in R | Pass criteria fixed in the spec | — |
| 1 | `--min-group-rs 40` / `60` | Avg R, drawdown | Above; Kell's "leading groups" | India positive in 5 of 9 years (one flat) | From the method; no code |
| 2 | On 1.2, the combination `SCREEN_LOOSE=1` (+ group filter if it passes) | CAGR (India) | 1.0: 19.37% and Sharpe 1.15 against 15.28%, but drawdown −33.9% | One value (a switch); the result rests on the spec's criteria | Parameter (combination step) |
| 3 | `--bt '--max-open-risk 8'` / `10` (spec default 6) | Exposure (India) | 54% invested; 2,370 open-risk refusals | Raises drawdown, which is already failing; run only if #1 cuts drawdown | Mechanics; no code |
| 4 | Scope: India only; keep the US runs as a control, not a target | — | The US momentum baseline was negative in this window | — | Decision |

---

## The family's best version today

**`kell_cycle` in India** is the closest to a working edge.

- It is the only member with an alpha near statistical significance (t 2.03). Most of that is earned per trade,
  not from exposure.
- It is the only one with a selection edge free of fill bias (100th percentile).
- It is the only one whose Sharpe probably beats the index's.

Its edge is **Trend Template and RS momentum selection plus Kell's exits**, not the cycle's entry points. Those
entry points add nothing over the screen's own bars.

**`stage_analysis` US is the best risk-reducer.** It has Sharpe 0.82, drawdown −21% against −34%, and +0.54R a
trade. It is also the one strategy whose setup adds to its screen. But it has failed verify, and trails buy-and-hold
by 4.7 points a year.

**The combination worth building toward.** Momentum and RS selection, a strong-group filter, Kell's EMA-break exit
(or Weinstein's weekly line for longer holds), and capital that is actually used. The plan below gets there one
evidenced step at a time, starting from the two strategies that already carry the pieces.

## Improvement plan, ranked across the family

The pass criteria are fixed here, before any run. Each variant is compared with its own **current-version
baseline** in the same market. That baseline is queued for `stage_analysis` 2.12 and `kell_cycle` 1.2. For
`trend_pullback` 1.5 it still has to be queued (P0).

| Rank | Change | Strategies | Type | Needs code? | Pass criteria (each market on its own) |
|---|---|---|---|---|---|
| P0 | 1.5 baseline for `trend_pullback`; let the queued 2.12 and 1.2 baselines finish | trend_pullback, stage_analysis, kell_cycle | Housekeeping | No | — |
| P1 | **Industry-group strength filter**, 40 and 60 | stage_analysis, kell_cycle, trend_pullback | From the method (Weinstein, Kell) and the literature (industry momentum) | No | (a) Avg R up ≥ 0.10 at **both** 40 and 60. (b) Sharpe up ≥ 0.05 at both. (c) Max drawdown no more than 2 points deeper. (d) Trades ≥ 60% of baseline. (e) Avg R of the kept trades above the baseline's in ≥ 5 of 9 entry years. (f) Excess CAGR at standard costs (`excess_std_cost`) also improves. Carry forward 40 if both pass (the looser one), never the better of the two |
| P2 | **India liquidity floor** ₹10 / ₹20 crore | stage_analysis (India) | Mechanics | No | (a) Excess CAGR up ≥ 2 points at both values. (b) Avg R not lower by more than 0.05. (c) Max drawdown no more than 3 points deeper. (d) Average invested up ≥ 10 points. (e) `cagr_std_cost` up as well (thin names cost more) |
| P3 | **Kell combination**: `SCREEN_LOOSE=1` on 1.2, plus P1 if it passed | kell_cycle (India) | Parameter / combination | No | The spec's three §6 criteria, unchanged: expectancy ≥ +0.30R; CAGR above Minervini's best like-for-like at a drawdown no more than 5 points deeper; with the top 5% removed, expectancy > 0 |
| P4 | **G6 positive Mansfield RS** (`G6_REQUIRE_POSITIVE`) | stage_analysis | From the method | Yes: version 2.13, changelog, `gate_docs` G6, `param_docs`. It changes `evaluate()`, so a rescan; do not pin `signal_version`. Run `tests.test_strategy_docs` and `tests.test_strategy_versions` | (a) Avg R up ≥ 0.05. (b) Sharpe not lower. (c) Trades ≥ 85% of baseline. (d) In both markets |
| P5 | **Open-risk cap 8 / 10** | kell_cycle (India) | Mechanics | No | Only if P1 or P3 brings drawdown under the spec's bar. (a) CAGR up ≥ 2 points at both values. (b) Drawdown still within the spec's bar. (c) Sharpe not lower |
| P6 | **Weekly-close-only signals** (`WEEK_CLOSE_ONLY`) | stage_analysis | From the method | Yes (2.13 or later; `evaluate()` → rescan; setup_docs and caveats) | (a) Avg R up ≥ 0.10 in **both** markets. (b) Sharpe not lower. Fragile: rank last |
| P7 | **Retire** `ema_pullback`, `supertrend`, `ema100_trend`; and `trend_pullback` if P0 and P1 fail | — | Decision | Status and caveats text (and the registry if unregistered) | — |

**Exact optimise-stage commands** (run from `scripts/`; not queued):

```bash
# P0
python -m jobs enqueue backtest --market us    --strategies trend_pullback --stage optimise
python -m jobs enqueue backtest --market india --strategies trend_pullback --stage optimise

# P1: group strength (after the current baselines exist)
for m in us india; do for g in 40 60; do
  python -m jobs enqueue backtest --market $m --strategies stage_analysis --stage optimise --bt "--min-group-rs $g"
  python -m jobs enqueue backtest --market $m --strategies kell_cycle     --stage optimise --bt "--min-group-rs $g"
  python -m jobs enqueue backtest --market $m --strategies trend_pullback --stage optimise --bt "--min-group-rs $g"
done; done

# P2: India liquidity floor
python -m jobs enqueue backtest --market india --strategies stage_analysis --stage optimise --bt '--min-dollar-volume 100000000'
python -m jobs enqueue backtest --market india --strategies stage_analysis --stage optimise --bt '--min-dollar-volume 200000000'

# P3: Kell combination (add --bt "--min-group-rs 40" only if P1 passed for kell_cycle India)
python -m jobs enqueue backtest --market india --strategies kell_cycle --stage optimise --const SCREEN_LOOSE=1

# P5 (conditional)
python -m jobs enqueue backtest --market india --strategies kell_cycle --stage optimise --bt '--max-open-risk 8'
python -m jobs enqueue backtest --market india --strategies kell_cycle --stage optimise --bt '--max-open-risk 10'

# P4 / P6 need code first (stage_analysis 2.13), then:
python -m jobs enqueue backtest --market us    --strategies stage_analysis --stage optimise --const G6_REQUIRE_POSITIVE=1
python -m jobs enqueue backtest --market india --strategies stage_analysis --stage optimise --const G6_REQUIRE_POSITIVE=1
```

**Trial budget.** P1–P3 add 15 runs: 12 for P1, 2 for P2, 1 for P3. Count them in the next deflated-Sharpe
calculation. The best of 15 is not an edge unless the pass criteria hold at both neighbouring values.

**Then the combination.** The changes that passed are run together once per strategy and market, against the same
criteria. Only that combined run can ship as a new version with the defaults on.

**Verify.**

- `kell_cycle` has never been verified. It earns its one verify run only when the combined India run passes all
  three §6 criteria, with those criteria written into the run's plan before it starts.
- `stage_analysis` follows its 2.12 plan: its 2022+ window is spent, so the next judge is paper trading, not a
  second verify.

## Shared fixes

1. **Industry-group strength (P1).** One portfolio-level filter (`--min-group-rs`) for every member that keeps
   trading.
   - It is the clearest signal-level pattern in the family. In all six strategy × market cases, the groups rated
     above 80 did best. India is broadly ordered above 40; the US gain is mostly in the top bucket, so 60 may
     work better there than 40.
   - It is the sector rule in both Weinstein's and Kell's methods.
   - Caveats:
     - Industry classification is today's, so some look-ahead.
     - The effect is concentrated in 2017, 2020 and 2021.
2. **Use the capital.** The family's return gap to buy-and-hold is partly beta: 0.16 to 0.65 against an index
   held at 100%.
   - India's ₹50 crore floor starves the weekly and pullback strategies (P2).
   - 1% risk with 10 slots caps the US at about 75–80% invested (stage's 13 slots is queued).
   - The `--idle-index` route is closed: it is beta, and its verify failed for `trend_pullback`.
3. **Not a shared fix: an index market filter.** Entries with the index below its 200-day did as well or better in
   9 of 12 baselines (2013–2021).
4. **Not a shared fix: entry timing.** The pullback, crossback and turn-up setups carry no selection information
   beyond their screens. Effort spent tuning entries is better spent on selection and exits.

## Paper-trading gate

**Status.** No member of this family has a paper book. The only books are `momentum_baseline`, `dual_momentum` and
`momentum_dual_combo` in India, started on 2026-11-05.

**What to paper.** `kell_cycle`, India, as the version that comes out of P1 and P3. Paper it from the day that
version ships, at its backtest settings.

**What would confirm the edge:**

| Measure | Gate |
|---|---|
| Sample | At least 40 closed trades, and at least 12 months (about one year at 42 trades a year) |
| Expectancy | ≥ +0.20R a trade after costs (the backtest showed +0.27R) |
| Win rate | ≥ 30% |
| Profit factor | ≥ 1.3 |
| Stop-outs | Average R of stop exits no worse than −1.3R (slippage check; backtest −1.12R) |
| Drawdown | No deeper than the Nifty 500's over the same months plus 5 points, and never beyond −25% |
| Against the momentum baseline paper book (same months) | Equal or better CAGR at a shallower drawdown; otherwise Kell adds nothing over plain momentum |
| Concentration | With the best 5% of trades removed, expectancy ≥ 0 |

A failure on expectancy or drawdown stops the paper book. It does not lead to retuning on those months.

**`stage_analysis` US** may be papered alongside as a risk-reducer once 2.13 ships. Its gate: ≥ 30 closed trades
(about 18–24 months), avg R ≥ +0.30, drawdown at least 5 points shallower than SPY's, Sharpe not lower than SPY's.

## What could not be determined

- **Doubled costs.** No run in the family has a `cost_sensitivity` table. The standard-cost CAGR is the only cost
  check available. A `--cost-mult 2`-style run, or the table, would settle it.
- **Whether the 1.5 filters fail on like-for-like data.** That needs the 1.5 baseline (P0).
- **Stage 2 age, per signal.** The signal rows store the stage but not its age, so G10 could be checked only from
  trades (2.12 changelog), not at the signal level. The queued G10 runs settle it.
- **Group-RS look-ahead.** Industry membership is today's classification. A point-in-time industry history would
  remove the doubt.
- **Kell's intraday entries.** They cannot be tested without intraday bars. The close entry is a known, deliberate
  approximation.
- **The size effect in India.** Part of the India screens' +3 points at 60 sessions may be small-cap
  outperformance. A size-matched null (the same market-cap bucket) would separate it from momentum.
