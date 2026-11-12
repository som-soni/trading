# Strategy review — summary across the eight families

*Written 2026-11-12. This summary combines the eight family reviews:
[base breakouts](strategy-review-base-breakouts.md), [momentum bursts](strategy-review-momentum-bursts.md),
[trend pullbacks and stages](strategy-review-trend-pullbacks.md), [trend following](strategy-review-trend-following.md),
[portfolio momentum](strategy-review-portfolio-momentum.md), [earnings events](strategy-review-earnings-events.md),
[shorts and mean reversion](strategy-review-shorts-mean-reversion.md) and
[special situations](strategy-review-special-situations.md).
Every figure comes from those files. They read only **optimise-stage** runs (2013-01-01 → 2021-12-31, in-sample),
quote verify runs by their verdict or badge only, and treat legacy runs as context. This file adds no new figures.
Analysis and plan only: no code was edited, no job was queued and nothing was committed.*

Commands are run from `scripts/` as `PYTHONPATH=. .venv/bin/python -m jobs enqueue …`. They are shortened below to
`python -m jobs enqueue …`, as the family files write them.

---

## 1. In short

- **Only two kinds of edge survive the checks, and both are in-sample.**
  - **Momentum selection, mostly in India.** `momentum_vol_scaled` India is the only strategy that passes every
    check: its top 20 beat their own pool by +1.06% a month (t 2.9, 108 months), at the 100th percentile of random
    books. The same Trend Template / RS screen carries `minervini` India (deflated Sharpe 0.98 over 55 trials) and
    `kell_cycle` India (alpha +10.5% a year, t 2.03).
  - **Faber's risk control.** `ma_trend` matches the index's Sharpe at about half its drawdown.
  - Nothing else has an edge as built. In the US only `quality_momentum` beats SPY (+1.29 points), and 2020
    carries that margin.
- **The edge sits in selection and exits, not in entries.**
  - Setups add almost nothing to the screens they draw from. In 9 of 11 base-breakout baselines, the signals
    trailed their own screen's pool. The pullback setups are within ±0.5 points of their screen in the US.
  - Trend exits beat each strategy's own exit wherever they were tried (Darvas with a 50-day exit: +5.5 points
    of CAGR in the US).
  - Industry-group strength separated signals in all six strategy × market cases tested.
- **The biggest gaps between method and code:**
  - Minervini's SEPA earnings leg is recorded but never enforced, and 89% of US trades are flat-base buy-stops or
    cheats rather than VCP pivots.
  - `pead` dates events by the SEC filing (30.6% enter 3 or more days late) and stops out 685 of 915 trades with a
    stop the method does not have.
  - `earnings_gaps`' ATR cap refuses 92% (US) and 94% (India) of results-day reactions, and its neglect rule is off.
  - Dual momentum's absolute test uses Treasuries, where Antonacci uses T-bills.
  - The documented 200-day leveraged-index rule behind Masonson's strategy has never been run.
  - Kullamägi's intraday entry cannot be tested on daily bars.
- **Shared mechanics hide or inflate edges.** These include:
  - India runs charged at 10 bps a side instead of the standard 27, which removes the whole India edge of both
    burst strategies;
  - luck in which signals win a slot (burst: traded +0.35R, skipped +0.00R; donchian rankings move CAGR by up to
    6 points);
  - crumb fills and idle capital;
  - `--const` silently dropped by portfolio runners.
- **The plan:**
  1. Protect what works. Open paper books now for `momentum_vol_scaled` India, `quality_momentum` and `minervini`
     India, with forward gates written down first, and no re-tuning.
  2. Run the cheap fidelity tests that need no code.
  3. Retire the four strategies that have neither a documented method nor a selection edge, and five more if
     they fail one last pre-set check.
  4. Read every short-side and trend-following verdict as conditional: 2013–2021 contains no long bear market.

---

## 2. Every strategy and its verdict

| Strategy | Family | Verdict | Why |
|---|---|---|---|
| `minervini` | 1 Base breakouts | US: no edge. India: a narrow in-sample edge from the screen | US deflated Sharpe 0.08 (N 53), picks at the 76th percentile of random Trend Template stocks. India deflated Sharpe 0.98 (N 55), 91st percentile, but 3.4% CAGR without 2021. The earnings leg is never enforced |
| `minervini_coil` | 1 | No edge; retire after one v1.1 run | Picks worse than random inside its own screen (US 2nd percentile, India 17th) |
| `breakout` | 1 | No edge | 23rd / 17th percentile, deflated Sharpe 0.35 / 0.22. Only lever: VOL_MULT=1.0 (+5.2 / +5.1 points). Fold CAN SLIM's gaps into `minervini` |
| `darvas` | 1 | Small US selection edge; none in India; the exit is the weak point | US 98th percentile (858 trades). The 50-day exit adds +5.5 points (US) and +1.8 (India, standard cost) |
| `chart_pattern` | 1 | No signal or selection edge | Breakouts trail the liquid pool at 60 sessions. Its +0.3R comes from the bracket geometry. No 1.21 baseline exists |
| `delivery_breakout` | 1 | No edge; retire | 106 trades, −0.02R, 15th percentile, no documented record |
| `kullamagi` | 2 Momentum bursts | No demonstrated edge as built (implementation gap) | +0.11R / +0.12R, but the best 5% of trades make 3.8× / 3.4× the net R. US selection rests on 2020. The intraday entry is missing |
| `momentum_burst` | 2 | No edge in the 5-day method; the 20-day-exit variant is a fragile India edge | Run 3847: +3.48 points excess, but −0.62 at standard cost. Half its R comes from 2021, and it is path-dependent |
| `stage_analysis` | 3 Trend pullbacks | No edge as built; implementation gap suspected | Excess −4.74 (US) and −9.68 (India). Failed verify (2.11). India only 40% invested. Group strength and positive RS are missing |
| `trend_pullback` | 3 | No demonstrated edge; needs a 1.5 baseline | India's excess comes from the uptrend screen (+3.10); the pullback adds +0.08 |
| `ema_pullback` | 3 | No edge; retire | Sharpe 0.13 / −0.06. The setup does worse than its own screen. No documented method |
| `ema100_trend` | 3 | No edge; retire | Excess −5.05 / −10.02. A faithful build of a method with no record |
| `supertrend` | 3 | No edge; retire | US picks at the 3rd percentile of random. Traded signals did worse than skipped ones in both markets |
| `kell_cycle` | 3 | India: edge, in-sample only. US: none | India alpha +10.5% (t 2.03), 100th percentile, deflated Sharpe 0.995 (N 3). Fails its own drawdown and concentration criteria |
| `donchian` | 4 Trend following | US: no edge. India: a modest selection edge carried by 2021 | US trades at the 2.4th percentile. India at the 94th–99th, but CAGR is 6.2% without 2021. Crumb fills and stale fills leak the edge |
| `turtle_trend` | 4 | No edge; probes do not rescue it | Sharpe 0.17, timing at the 51.7th percentile. Seven probes give a best Sharpe of 0.25 |
| `ma_trend` | 4 | No return edge; a risk edge that largely holds | Sharpe equal to the index (US) or above it (India) at about half the drawdown. Narrowly misses one pre-set criterion per market |
| `momentum_vol_scaled` | 5 Portfolio momentum | Edge in India; none in the US | India top 20 beat the pool by +1.06%/month (t 2.9), deflated IR 0.86. US t 0.41 |
| `quality_momentum` | 5 | US edge is real but concentrated; India cannot be judged | The filter removes lottery names (97th percentile). The best 5% of trades make 131% of net P&L, and 2020 is the margin. India has 2.7 years of data |
| `momentum_dual_combo` | 5 | Edge in India (from its momentum sleeve); none in the US | India Sharpe 1.21, drawdown −28.3% against −50.5% for the sleeve alone |
| `dual_momentum` | 5 | US fidelity gap; India acceptable | Absolute test against Treasuries, not T-bills. A T-bill hurdle adds +3.0 points CAGR in a re-simulation |
| `momentum_baseline` | 5 | A correct naive control; poor US book | US top 10 carry 83% volatility against the pool's 31%. Volatility drag cuts 14.1% to 5.3% a year |
| `rs_leaders` | 5 | No edge | Signals return what SPY did (+1.45% against +1.43%, n 9,920). Deflated IR 0.02 |
| `sector_rotation` | 5 | No selection edge | US equals equal-weight sectors. Top 3 at the 68th (US) and 81st (India) percentile |
| `pead` | 6 Earnings events | No edge as built: implementation gap (US); India never run in optimise | Events dated by the SEC filing, 75% of trades stopped out, a growth screen with no drift. Matched-null 62nd–76th percentile |
| `earnings_gaps` | 6 | No edge as built: implementation gap | The ATR cap refuses 92% / 94% of reactions, so the flag setup makes 87% of trades. Neglect is off |
| `mean_reversion` | 7 Shorts & mean reversion | No edge as built; signal-level timing edge | Signals beat matched random entries by +0.19% (US) / +0.22% (India). Costs, the 2-slot cap and the ranking lose it |
| `stage4_shorts` | 7 | No edge; window gap | 24th / 16th percentile of random shorts. The market filter is inverted in a window of V-rebounds. v1.4 never run |
| `parabolic_short` | 7 | No edge as built; real selection edge | 100th percentile against random shorts. The small tier makes +0.34R (n 105), but 5 trades make 66% of it |
| `masonson_tqqq` | 8 Special situations | No edge as built; implementation gap suspected | Timing at the 10th percentile of random timing. The return is leverage beta. The 200-day rule has never been run |
| `etf_swing` | 8 | No edge, and no fair test yet | India deploys about 11% of capital (median pool of 3 ETFs). The US universe has never been run |
| `fno_income` | 8 | Gross carry edge detectable; net edge unproven | Gross t 2.49 (3.87 without the VIX gate). Costs take 64%, and 2020 makes 200% of the net |

---

## 3. Each family's best version

| Family | Best version today | Status |
|---|---|---|
| 1 Base breakouts | `minervini` 1.66 India (run 4154): Sharpe 1.24 against 0.86, drawdown −18% against −38%, holds a passed verify verdict (1.64). US: Darvas entry + 50-day exit (run 2269, 12.26%) | Narrow; from the screen and the 150-day exit, not the VCP |
| 2 Momentum bursts | `momentum_burst` India, 20-day exit (run 3847): 17.02% CAGR, +3.48 points, Sharpe 1.02 | Not an edge yet: −0.62 at standard cost, path-dependent |
| 3 Trend pullbacks | `kell_cycle` India (run 3910): +1.74 points, Sharpe 0.96 against 0.86, alpha t 2.03 | Fails its own drawdown bar (−35.2% against −25.9%) |
| 4 Trend following | `ma_trend` index mode (runs 2335 US, 3826 India): Sharpe 0.97 against 0.99 (US) and 1.12 against 0.91 (India), drawdown about half | A risk-control edge, not a return edge |
| 5 Portfolio momentum | `momentum_vol_scaled` India v1.9, unchanged (run 1832): 25.89% against 15.44%, drawdown −50.5%. Shallower option: `momentum_dual_combo` India (−28.3%) | The only selection edge that survives every check. Protect it; do not re-tune |
| 6 Earnings events | By scorecard `pead` US (run 3370, Sharpe 0.59). Closest to an edge: India drift after a large price reaction, not yet built (+2.35% over 60 sessions, t 3.8, n 1,220) | An event study, not a backtest |
| 7 Shorts & mean reversion | `mean_reversion` US: signals beat random entries on a plateau of RSI thresholds 5–15, in 7 of 9 years | Lost to costs, slots and ranking |
| 8 Special situations | `fno_income` put spreads only: 87 puts +97k net against 61 calls −22k | Net depends on a cost only live quotes can measure |

```chart
title: Best versions — Sharpe against their benchmark, optimise stage 2013–2021
labels: vol_scaled India | combo India | minervini India | ma_trend India | kell India | ma_trend US | darvas+SMA50 US | Masonson US
series: Strategy | 1.21 | 1.21 | 1.24 | 1.12 | 0.96 | 0.97 | 0.79 | 0.73
series: Benchmark | 0.85 | 0.87 | 0.86 | 0.91 | 0.86 | 0.99 | 0.88 | 1.16
unit: Sharpe (daily, rf = 0)
caption: From the family files. Benchmarks: Smallcap 250, the blended benchmark, Nifty 500, buy-and-hold of the index, SPY (0.88, from the portfolio file's US scorecard) and QQQ. All in-sample.
```

---

## 4. The cross-family action plan — the 10 highest-value changes

Ranked by expected impact × strength of evidence × robustness × simplicity. Two kinds of change come first:
fidelity gaps in methods with a strong documented record, and protection for the momentum books whose verify badge
reads "Return edge out-of-sample — pre-set test not passed": `momentum_vol_scaled`, `quality_momentum`,
`momentum_dual_combo` and `dual_momentum`. The pass criteria are the family files' own, fixed before any run.
Each change is one trial: recompute the deflated Sharpe with the new N.

| # | Change | Family · strategies | Type | Pass criteria (fixed now) | Command or file |
|---|---|---|---|---|---|
| 1 | **Protect the momentum edge.** Open paper books with the forward gate written down first, and no re-tuning: `momentum_vol_scaled` India, `quality_momentum` US and India, and `minervini` India (the only base-breakout strategy with a passed verify verdict) | 5 · vol_scaled, quality; 1 · minervini | mechanics | **vol_scaled India:** 12 month-end rebalances and ≥ 150 closed holding periods. Excess over the Smallcap 250 ≥ +3 points. Top 20 beat the pool by ≥ +0.3%/month, positive in ≥ 7 of 12 months. Costs ≤ 50 bps a side. Stop if the book is 15 points behind or costs exceed 100 bps. **quality:** excess ≥ +2 points, and it beats a paper `filings_covered` control by ≥ 2 points over 12 rebalances. **minervini India:** ≥ 12 months and ≥ 30 closed trades. Average R ≥ +0.15R, profit factor ≥ 1.2, drawdown no deeper than −15%. Fills within 2× the modelled 32 bps. Every signal reconciles with a replay | Paper book set-up (`books` / `paper_orders`); no code. Today only the `dual_momentum`, `momentum_baseline` and `momentum_dual_combo` India books exist (opened 2026-11-05) |
| 2 | **Enforce the earnings leg** (SEPA, Darvas, CAN SLIM) in the US | 1 · minervini, darvas (breakout via minervini) | from the method | `guide` against the `covered` control: average R ≥ control + 0.15R, CAGR ≥ control + 2 points, drawdown no more than 3 points deeper, ≥ 150 trades. `acceptable` points the same way | `python -m jobs enqueue backtest --market us --strategies minervini --stage optimise --bt '--fundamentals covered'` (then `guide` and `acceptable`); darvas: `--const REQUIRE_EPS_GROWTH=1 --bt '--exit-mode ma --ma-col sma50 --no-target'` |
| 3 | **A 50-day trend exit as Darvas's default**, once the SMA100 neighbour confirms it | 1 · darvas | mechanics | SMA100 within 2 points of SMA50's CAGR in each market. SMA50 beats the box trail at standard cost in both markets (already: US +5.5, India +1.8). Average R ≥ baseline + 0.05R in both | `python -m jobs enqueue backtest --market us\|india --strategies darvas --stage optimise --bt '--exit-mode ma --ma-col sma100 --no-target'`. Then `strategies/darvas.py` `backtest_args` and `exit_rules`, v1.1, `signal_version` pinned to 1.0 |
| 4 | **The neglect gate for earnings gaps**: refuse a gap after a 60-session run-up above 10% (neighbours 0% and 20%). In India also lower the floor to ₹10 crore and turn the ATR cap off | 6 · earnings_gaps | from the method | **US:** mean R ≥ 0.20 (baseline 0.075), profit factor ≥ 1.35, null ≥ 90th percentile, ≥ 200 trades, drawdown no deeper than −25%. Both neighbours ≥ 0.15R. Positive in ≥ 6 of 9 years. ≥ 0.15R at doubled slippage. **India E4:** ≥ 120 trades, CAGR ≥ 3%, mean R ≥ 0.25, null ≥ 90th percentile, drawdown no deeper than −15%. The ₹20 crore neighbour ≥ 0.20R, and ≥ 0.20R at 27 bps | `python -m jobs enqueue backtest --market us --strategies earnings_gaps --stage optimise --const NEGLECT_GATE=1 --const NEGLECT_MAX_RUN_PCT=10` (and 0, 20, India). India: `--min-dollar-volume 100e6 --const MAX_STOP_ATR=99` |
| 5 | **Industry-group strength filter** for every member that keeps trading; then Kell's combination with `SCREEN_LOOSE=1` | 3 · kell_cycle, stage_analysis, trend_pullback; 1 · minervini | from the method (Weinstein, Kell, Minervini) and the literature (industry momentum) | **Family 3, at both 40 and 60:** average R up ≥ 0.10. Sharpe up ≥ 0.05. Drawdown no more than 2 points deeper. Trades ≥ 60% of baseline. Better in ≥ 5 of 9 years. Excess at standard cost improves. Carry 40 forward if both pass. **minervini at 50 (its pre-set value):** average R ≥ baseline + 0.10R in both markets, CAGR not lower by more than 1 point. **Kell combination:** the spec's §6 criteria, unchanged | `python -m jobs enqueue backtest --market <m> --strategies <key> --stage optimise --bt "--min-group-rs 40"` (and 60; minervini 50). Kell: `--market india --strategies kell_cycle --stage optimise --const SCREEN_LOOSE=1` |
| 6 | **Trade the VCP, not every flat base** | 1 · minervini | from the method | Average R ≥ baseline + 0.10R in both markets. CAGR no lower than baseline − 1 point in either. India ≥ 120 trades. A rescan; `signal_version` not pinned | `python -m jobs enqueue backtest --market us\|india --strategies minervini --stage optimise --const FLAT_COIL_ON=0 --const SHAKEOUT_ON=0 --const CHEAT_MIN_CONTRACTIONS=2` |
| 7 | **`pead` as the method describes it**: date events by the results announcement and drop the reaction-low stop (US); add an India price-reaction (EAR) mode at a ₹5–10 crore floor | 6 · pead | from the method; from the literature (Chan, Jegadeesh & Lakonishok 1996) | **US P1+P2:** mean return per trade ≥ +2.5%, null ≥ 80th percentile, drawdown no deeper than −30%. Beats the null in ≥ 6 of 9 years. ≥ 75th percentile at 20 bps. **India P4:** 60-session excess ≥ +1.5% after 27 bps, null ≥ 95th percentile, ≥ 300 trades, drawdown no deeper than −25%. ₹5 and ₹10 crore both pass. Cut-offs at the 85th and 95th percentile both ≥ +1.0%. ≥ 7 of 9 years positive | `scripts/swing_screener/backtesting/pead.py` v1.5: `load_events` reuses `EarningsGapsStrategy._announcements`, `--no-stop`, `--surprise {growth,sue_ear,ear}`, `--min-turnover`. Make the mode and floor module constants so they enter the fingerprint |
| 8 | **Dual momentum's absolute test against T-bills** (Antonacci) | 5 · dual_momentum US, momentum_dual_combo US | from the method | US CAGR ≥ run 2344 + 1.5 points, drawdown no deeper, ≤ 30 switches. Same direction at 9- and 6-month lookbacks. ≥ 6 of 9 years no worse than as coded by more than 2 points. Passes at 20 bps | `backtesting/dual_momentum.py` `pick()`, `run()`, `current_pick()`: `ABS_HURDLE` constant, v1.2. Then `python -m jobs enqueue backtest --market us --strategies dual_momentum --stage optimise` |
| 9 | **Is the burst's best result luck?** Rerun the 20-day exit with random ranking, then with a 12.5% position cap | 2 · momentum_burst | mechanics | India excess at standard cost ≥ 0 under random ranking. 2021 ≤ 50% of R. P2–P5 of the family file (years, neighbour, deflated Sharpe ≥ 0.90 with N = 35 + new runs, no damage). If it falls to about the signals' +0.14R, run 3847 was luck | `python -m jobs enqueue backtest --market india --strategies momentum_burst --stage optimise --bt '--exit-mode ma --ma-col sma20 --time-stop-bars 250 --rank-by random'` (then `--max-position-pct 0.125`) |
| 10 | **Minervini candidate D on 1.66**, both markets: lean exits, and the segment test in place of the index test | 1 · minervini | mechanics / known choice combined | US: CAGR ≥ 5%, Sharpe ≥ 0.45, drawdown no deeper than −25%. India: standard-cost CAGR ≥ 9.3%, drawdown no deeper than −20%. Average R ≥ +0.20R in both. Fails if India drops by more than 1 point. It must say that it includes LIGHT_VOLUME_EXIT=0, which failed verify on its own | `python -m jobs enqueue backtest --market us\|india --strategies minervini --stage optimise --const PARTIAL_R=0 --const STRENGTH_EXT_PCT=0 --const TIME_STOP_DAYS=0 --const LIGHT_VOLUME_EXIT=0 --const BREAKEVEN_R=0 --const MKT_INDEX_TEST=0` |

**Why this order.**
- Rank 1 costs no backtest time. It protects the only edges with out-of-sample badges, and forward data is the
  only clean test for strategies refined before October 2026.
- Ranks 2 and 6 close Minervini's two largest fidelity gaps. Minervini has the strongest documented record in
  the system. Neither needs code.
- Ranks 3 and 4 have the strongest evidence of the no-code changes:
  - The Darvas exit already holds in both markets.
  - The neglect gate shows a plateau across 0 / 10 / 20% and is positive in 7 of 9 years.
- Rank 5 is the clearest signal-level pattern across families. It is not stable year to year, and the industry
  labels carry some look-ahead.
- Ranks 7 and 8 need code. Each stands on a published rule:
  - The India EAR drift is the most robust single result in the review (D10−D1 positive in 9 of 9 years).
  - The T-bill hurdle helps at all three lookbacks.
- Rank 9 decides whether a family's best result is real.
- Rank 10 has a rising US sequence behind it (2.42% → 5.02% → 8.20%). It is ranked last because India is
  untested and one of its parts failed verify.

**Next tier** (each in its family file, with pass criteria):
- `kullamagi` leadership gate (`--bt '--min-rs 90'`, neighbour 80). Holds in both markets, but the US gain
  disappears without 2020.
- Masonson's slow exit (`--bt '--no-trend --exit-ema 200'`, neighbours 150 and 100). This is the documented rule.
- `mean_reversion`: realistic costs and every signal taken (`--bt '--cost-bps 2 --max-positions 14 --position-pct 7'`).
  The cost levels are estimates to confirm first.
- `donchian` v1.6: minimum fill, entry expiry of 1 session, market filter. Needs code and the seed band first.
- `stage_analysis` India liquidity floor at ₹10 / ₹20 crore.
- `quality_momentum` US turnover-floor plateau at $50M and $200M.
- `ma_trend` GTAA mode.
- `fno_income` without the VIX gate, with wider spreads.
- `etf_swing` US baseline.
- `momentum_baseline` JT breadth. Fragile: 2020 carries it.

**Retire** (status text, then unregister only after your approval):
- Now: `ema_pullback`, `supertrend`, `ema100_trend` and `delivery_breakout`.
- After one pre-set check each:
  - `minervini_coil` (its v1.1 run);
  - `breakout` (VOL_MULT neighbour and trend-exit runs);
  - `trend_pullback` (1.5 baseline and group filter);
  - `turtle_trend` as a standalone strategy (one TSMOM trial).
- Re-scope `sector_rotation` as a drawdown-overlay study, not a return strategy.

---

## 5. Shared fixes (each proposed once)

| # | Fix | Applies to | Evidence | Code? |
|---|---|---|---|---|
| X1 | **Judge India at the standard 27 bps a side.** Charge it in every runner; until then, read `cagr_std_cost` / `excess_std_cost` | breakout, darvas, chart_pattern, delivery_breakout, kullamagi, momentum_burst, earnings_gaps, every India comparison | Darvas India 8.07% → 5.59% at standard cost; chart_pattern 7.40% → 5.82%. The extra 0.06–0.10R a trade is the whole India edge of both burst strategies | The criterion: no. The runner change: yes (mechanics, noted in each changelog) |
| X2 | **A cost multiplier** (`--cost-mult 2`) for the doubled-cost check, plus `--cost-bps` on the runners that lack one, and per-instrument costs for funds and index futures | all; etf_swing, mean_reversion, parabolic_short named | The doubled-cost check cannot be run today. It is estimated from turnover (0.5–1.9 points a year) or recomputed from trades. A flat 10 bps is about 60% of RSI(2)'s gross gain | Yes |
| X3 | **A seeded random-ranking control and noise band** (`--rank-seed`), run before any ranking claim | every slot-limited strategy; donchian and momentum_burst first | Rankings move donchian's CAGR by up to 6 points. Burst India: traded +0.35R against skipped +0.00R. Burst US: skipped signals beat traded ones | `--rank-by random` exists; the seed needs code (`backtest.rerank_signals`) |
| X4 | **Minimum fill fraction**: skip a fill under 50% of the intended size rather than hold a slot with a crumb | `portfolio_sim` (opt-in); donchian first | 11–39% of donchian trades are under 3% of equity, holding 16–39% of slot-days | Yes (`--min-fill-frac`, default off) |
| X5 | **A trend exit for breakout entries**: hold to a close below the 50-day, moving to the 150-day after +3R | darvas (rank 3), breakout, chart_pattern; minervini has it | minervini 1.64's 150-day exit was its largest single gain. darvas SMA50 +5.5 / +1.1 points. Unmanaged moves beat managed ones in every positive base-breakout strategy | `backtest_args` per strategy |
| X6 | **No breakout-volume veto**, as a hypothesis | breakout (VOL_MULT 1.0–1.2), chart_pattern (BO_VOL=0 on 1.21) | Positive in 6 of 6 in-sample tests, but minervini's version failed verify | Constants; rescan |
| X7 | **Industry-group strength** (rank 5) | stage_analysis, kell_cycle, trend_pullback, minervini | Groups rated above 80 did best in all six strategy × market cases | No (`--min-group-rs`) |
| X8 | **A lower India liquidity floor where it starves the book**, at the strategy level and judged at standard cost | stage_analysis (₹10 / 20 crore), kullamagi (₹10 / 20 crore), earnings_gaps and pead (₹10 crore), etf_swing (a floor relative to the slot) | stage_analysis is 40% invested with about 450 stocks. trend_pullback rose step by step at lower floors. The earnings drift vanishes at ₹50 crore. **Not** for vol_scaled India: higher floors cost it 4.5–9.8 points, and lower floors were not tested | No (`--min-dollar-volume`); etf_swing needs code |
| X9 | **Every variant must be identifiable.** Pass `--const` to portfolio-runner strategies, or refuse it loudly. Make `--bt` modes that change rules (pead surprise mode and floor, etc.) module constants so they move the fingerprint | `jobs/registry.py` `_run`; pead, etf_swing, masonson_tqqq, the short runners | `_run` passes only `--bt` to `portfolio_strategies()`, so a `--const` variant silently runs the shipped rules. `--bt` passthroughs share the default's spec id | Yes |
| X10 | **Comparison books read the current version.** Short hedges are judged beside `momentum_dual_combo`; turtle's sleeve test reads the current `momentum_baseline` | stage4_shorts, parabolic_short, turtle_trend | The Stage 4 sleeve's long book (run 1165) made −2.11% a year with a −79.9% drawdown. Turtle reads baseline v1.0 (1165) although v1.4 (2337) exists | Yes (`LONG_BOOK`, `find_long_book`) |
| X11 | **Idle cash earns the stored cash rate** in every runner, as `masonson_tqqq` already does. `--idle-index` stays a reporting diagnostic only, never a rule | etf_swing, fno_income (code); minervini, kullamagi, stage India (reporting) | About 89% (etf_swing) and 99% (fno_income) of equity earns 0%, understating CAGR by about 5–6 points at India's rates. `--idle-index` as a rule is beta, and its verify failed for `trend_pullback` | Yes for the cash rate |
| X12 | **Benchmarks and nulls that match the method**, in the reports: 60/40 and S&P TR for dual momentum, equal-weight sectors for sector rotation, risk-adjusted terms for trend following, a timing null for single-instrument runners, volatility drag and gap-throughs reported | dual_momentum, sector_rotation, ma_trend, turtle_trend, donchian, masonson_tqqq, etf_swing, fno_income, short books | SPY's price index flatters dual's excess by about 2.1 points. The US sector deficit is equal-weight against cap-weight. Masonson's "beat the index" is leverage; its timing sits at the 10th percentile | Yes (reporting; no version bump) |
| X13 | **One announcement-date loader and one price-reaction definition** for earnings strategies | pead, earnings_gaps | pead's filing date lags the news on 30.6% of events | Part of rank 7 |
| X14 | **Docs and records** | momentum_burst and etf_swing `status` (stale), donchian `status` (quotes v1.4), Masonson's page commands (`--market india`, which its runner refuses), the three special-situation pages listing `momentum_baseline`'s CLI, run 1534 (broken, to archive) | CLAUDE.md: `status` names the stage of every figure | Docs / page code |

**Not proposed as shared fixes**, because the families disagree:
- **An index market filter.** It helped `donchian` (US 3.61% → 9.31%, India 11.85% → 17.23%). But entries with
  the index below its 200-day did as well or better in 9 of 12 pullback baselines. Every short-side filter
  inverted in this window. The market filter failed verify on vol_scaled India. Keep it strategy by strategy.
- **Entry timing.** The pullback, crossback and turn-up setups carry no information beyond their screens. Work on
  selection and exits.

**Data decisions only you can make.** Each is a new `marketdata/` job or a change to the stage protocol, so none
is proposed as part of this plan's work:
- Intraday bars for signal days only. These would settle Kullamägi's entry, Kell's entries, the parabolic
  trigger and the earnings opening range.
- Live option quote capture for `fno_income`.
- A 2000–2012 pre-sample diagnostic stage for short-side rules: never a verdict, and never used for tuning.
- Point-in-time industry classification and constituent lists.

---

## 6. Order of work

Backtest time is the constraint. The worker runs five lanes. `chart_pattern` runs in the long lane at about
4.5 hours each, so queue its runs first and let everything else run beside them. Portfolio-runner strategies use
the portfolio lane. Most other runs take minutes to an hour.

| Wave | What | Backtest time |
|---|---|---|
| 0 — now, no runs | Open the rank-1 paper books with their gates written down. Fix the X14 docs. Decide on retirements and the data decisions above | none |
| 1 — missing baselines | `chart_pattern` 1.21, US and India (long lane, about 9 hours together; queue first). `minervini_coil` v1.1. `trend_pullback` 1.5. `stage4_shorts` v1.4. `etf_swing` US. Let the queued `stage_analysis` 2.12 and `kell_cycle` 1.2 baselines finish | long lane about 9 h; the rest minutes to an hour each |
| 2 — no-code variants | Ranks 2, 3, 4, 5, 6, 9 and 10. Then the next tier that needs no code. Then breakout VOL_MULT=1.2. In the long lane after its baseline: `chart_pattern` BO_VOL=0 and the trend exit, both markets (about 4 × 4.5 h) | about 18 h in the long lane; the rest run in parallel |
| 3 — shared mechanics code, written while wave 2 runs | X1 runner costs, X2 cost multiplier, X3 rank seed, X4 minimum fill, X9 `--const` passthrough, X11 cash rate, X10 comparison books. Each is a mechanics change in each affected strategy's changelog. Rerun the affected baselines once afterwards | one baseline per affected strategy and market |
| 4 — strategy code | `pead` v1.5 (rank 7), `dual_momentum` v1.2 (rank 8), `darvas` 1.1 (if rank 3 passes), `stage_analysis` 2.13 (G6 positive RS), `donchian` 1.6 (after the X3 band: 10 seeds per market), `parabolic_short` 1.1, `stage4_shorts` Weinstein exits, `ma_trend` GTAA, `turtle_trend` TSMOM (one trial), `fno_income` put-only ladder, Masonson 2x. Each with a version bump, changelog, docs and `tests.test_strategy_docs` / `tests.test_strategy_versions` | minutes to an hour each; donchian's band is 20 runs |
| 5 — combinations | Per strategy, once: only the parts that passed alone, against the same criteria. Recompute the deflated Sharpe with every new trial. The families add about 24 runs (base breakouts), 20 (bursts), 15 (pullbacks) and up to 30 (trend following) | one run per strategy and market |
| 6 — verify, once per version | Only a shipped version that passed every row of its criteria, including neighbours and costs, with the verify criterion written first. **Not** `momentum_vol_scaled` India: it has had its verify, and nothing here changes it. **Not** `stage_analysis`: its 2022+ window is spent, so paper trading judges it | one run each |
| 7 — paper | The gates below | forward data |

**Paper-trading gates** (from the family files; a book that misses its gate goes back to optimise as a new
version, and is never tuned on its paper months):

| Book | Opens | Confirms the edge if |
|---|---|---|
| `momentum_vol_scaled` India | Now | 12 rebalances and ≥ 150 holding periods. Excess over the Smallcap 250 ≥ +3 points. Top 20 beat the pool by ≥ +0.3%/month in ≥ 7 of 12 months. Costs ≤ 50 bps a side |
| `quality_momentum` US and India | Now | Excess ≥ +2 points, and it beats a paper `filings_covered` control by ≥ 2 points over 12 rebalances |
| `momentum_dual_combo` India | Open since 2026-11-05 | 12 rebalances. Excess over the blend > 0. Drawdown no deeper than 1.2× the benchmark's |
| `minervini` India | Now | ≥ 12 months and ≥ 30 trades. Average R ≥ +0.15R, profit factor ≥ 1.2, drawdown no deeper than −15%. Fills within 2× 32 bps |
| `darvas` US, SMA50 exit | After v1.1 ships | ≥ 60 trades. Average R ≥ +0.15R, profit factor ≥ 1.25, drawdown no deeper than −20%. Still beats a random near-highs stock |
| `kell_cycle` India | After the P1 / P3 version ships | ≥ 40 trades and ≥ 12 months. ≥ +0.20R, profit factor ≥ 1.3, drawdown never beyond −25%. Beats the momentum paper book. Expectancy ≥ 0 without the best 5% |
| `ma_trend` index mode, US and India | Now (best version) | 24 month-end decisions with 0 rule mismatches. Drawdown ≤ 0.6× the index's, judged only if the index falls ≥ 10% |
| `earnings_gaps` US (E1); `pead` India (EAR) | After each passes optimise | E1: ≥ 40 trades over ≥ 9 months, ≥ +0.15R, profit factor ≥ 1.3. pead India: ≥ 60 trades over two seasons, 60-session excess ≥ +1.0% |
| `momentum_burst` India, 20-day exit | Only if ranks 9 and B1/B3 pass | 12 months and ≥ 60 trades. ≥ +0.15R, drawdown no deeper than −25%, at least the Nifty 500's return, band locks logged |
| `fno_income` put spreads | After F1/F5 pass | ≥ 9 months and ≥ 40 structures at quoted bid/ask. Median slippage ≤ 2.5 points a leg; retire if it is above 3.1 |
| `mean_reversion`, `parabolic_short`, `donchian` India, Masonson, `stage_analysis` US | After their own optimise pass (and verify where one is allowed) | As in their family files. `parabolic_short` must log a borrow locate for each short. `stage4_shorts` is not eligible until a bear-containing test exists |

---

## 7. What could not be determined

- **Survivorship.** Prices cover today's listed names only. This flatters every absolute figure, India small caps
  and fast stocks most. It needs point-in-time constituent lists.
- **Bear markets.** 2013–2021 holds no long bear market. Short rules, trend following, dual momentum and
  Masonson's crash protection cannot be judged here. Forward data, full-stage context runs, or a pre-sample stage
  (your decision) would settle it.
- **Doubled costs, and real costs.** There is no cost multiplier (X2). India price bands are not modelled. Option
  bid/ask, borrow availability and fees, and fund and futures spreads are not stored. Paper fills would settle them.
- **Intraday entries.** Kullamägi's (bounded at +0.13R to +0.44R a trade in the US), Kell's, the parabolic
  trigger and the earnings opening range. Intraday bars for signal days would settle them.
- **Fundamentals history.** India results are point in time only from late 2020 (2018 for quarterly results), so
  SEPA's earnings leg is US-only in optimise. Only 4 quarters of consensus estimates are stored.
- **Slot effects.** Stored signals do not mark which lost a slot, and buy-stop episodes are conditioned on
  reaching the trigger. The simulator's skip log and the seed band (X3) would settle them.
- **Look-ahead in group RS.** Industry classification is today's.
- **Small-cap effect.** How much of India's screen excess is size rather than momentum. A size-matched null would
  settle it.
- **Trial counts are lower bounds.** Earlier runs cited in research notes are no longer in `report_runs`.
  `ma_trend`'s lookback set was chosen on 1981–2026 data. fno_income's legacy sweep dispersion is assumed. The
  deflated Sharpes are optimistic.
- **Open checks to make on the first jobs.** Does a `--rank-by` or `--time-stop-bars` passed through `--bt`
  override `backtest_args`? Is `--min-rs` a fair stand-in for Kullamägi's 1/3/6-month leadership? A pass still
  needs the coded gate.

**Consistency notes** (where the family files differ, and how this summary reads them):
- **Group-RS thresholds.** minervini's plan pre-sets 50; the pullback family pre-sets 40 and 60. Each keeps its own
  pre-set value; do not pick the better after the fact.
- **RS rank.** RS ≥ 90 separates `kullamagi` signals, but RS buckets do not order `minervini`'s R. These are
  different strategies, so both stand. Neither supports raising minervini's RS floor.
- **India floors.** Lower floors help the starved strategies (X8), while higher floors hurt vol_scaled. Both point
  the same way. No lower floor is proposed for vol_scaled.
- **vol_scaled years.** The portfolio file's headline says "8 of 10 years"; its year table and §8 say 8 of 9.
  This summary uses 8 of 9.
- **Masonson's CAGR.** The run's CAGR is 21.13%. The 21.4% in its file comes from the timing-null simulation
  (open-to-open), not the run.
