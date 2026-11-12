# Strategy family review — 1. Base breakouts

*Family review per [the briefs](strategy-family-review-briefs.md) (§1), following `/backtest-review` for
`minervini`, `minervini_coil`, `breakout`, `darvas`, `chart_pattern` and `delivery_breakout`. Written 2026-11-12.
**Optimise stage only (2013-01-01 → 2021-12-31, in-sample).** Verify runs exist only for `minervini`; only their
verdicts are quoted (1.54 failed in both markets; 1.64 passed its pre-set India criterion), never their trades,
tables or figures. Legacy runs are context only. Analysis and plan only: no code edited, no job queued, nothing
committed. Working scripts are in the session scratchpad, not in the repo.*

**In short**

- **No strategy in the family beats buy-and-hold in the optimise window.** Every edge badge reads "No edge".
  The closest are `minervini` in India (10.31% CAGR, Sharpe 1.24 against the index's 0.86, max drawdown −18%
  against −38%, deflated Sharpe 0.98 over 55 trials) and `darvas` with a 50-day trend exit in the US (12.26%,
  Sharpe 0.79, an already-run variant).
- **The edge is in the screen, not in the setups.** In India the Trend Template pool beats the liquid universe by
  2.8% per 60 sessions (t = 3.5). In the US it beats it by only 0.5% (t = 0.9). The setups add nothing on top.
  In 9 of 11 baselines the scanned signals trailed their own screen's pool over the next 60 sessions. This is
  why India works and the US does not.
- **Exits decide the results.** In every strategy where it was tried, letting winners run to a moving-average
  trend exit beat the strategy's own exit (darvas US +5.5 points of CAGR; minervini's 150-day exit after +3R is
  the change that made 1.64). Fixed brackets and tight trails cut off the few trades that pay for everything.
- **Breakout-volume confirmation has hurt in all six in-sample tests** (three strategies × two markets). That runs
  against the textbook. In `minervini` it is a known choice: turning it off failed its verify run.
- **Minervini fidelity gaps, ranked.** (1) Fundamentals are recorded but never enforced. SEPA without its
  earnings leg is a different method. (2) The book mostly trades flat-base buy-stops and cheats, not VCP pivots:
  in the US 89% of trades are S8 or S4 and 5% are VCP pivots (S1/S2). (3) More than half the US trades (487 of
  895) are sold at the next open by the light-volume rule, which Minervini does not use. (4) Group leadership is
  never tested.
- **Retire two strategies once their last check is done.** `minervini_coil` picks worse than random within its
  own screen (US 2nd percentile). Run v1.1 once, then retire it. `delivery_breakout` has no documented record,
  no selection edge (15th percentile) and 106 trades: retire it as a standalone strategy.

---

## 0. Runs reviewed

Baseline = the latest non-archived optimise run of the current version with the strategy's own `backtest_args`
and no override. Where the current version has no optimise run, the newest earlier version is used and said so.

| Run | Strategy | Market | Version / spec | Stage | Overrides | Role |
|---|---|---|---|---|---|---|
| 4156 | minervini | US | 1.66 / v1.66-ebac5f47 | optimise | none | **baseline** |
| 4154 | minervini | India | 1.66 / v1.66-ebac5f47 | optimise | none | **baseline** |
| 4157 / 4158 | minervini | India / US | 1.66 | optimise | `CHEAT_MIN_SMA50_PCT=3` | variant tested |
| 3309 | minervini_coil | US | 1.0 / v1.0-03f49df5 | optimise | none | baseline (**1.1 never run**; 1.1 imports minervini 1.64's exits, cap and segment gate) |
| 2817 | minervini_coil | India | 1.0 / v1.0-03f49df5 | optimise | none | baseline (same caveat) |
| 3852 / 3848 | minervini_coil | US / India | 1.0 | optimise | `--time-stop 0` | variant tested |
| 3033 | breakout | US | 1.6 / v1.6-1b012d45 | optimise | none | **baseline** |
| 2560 | breakout | India | 1.6 / v1.6-1b012d45 | optimise | none | **baseline** |
| 2358 / 2359, 3849 / 3834 | breakout | US / India | 1.6 | optimise | `VOL_MULT=1.0`; `--exit-mode ma --no-target` | variants tested |
| 2010 | darvas | US | 1.0 / v1.0-97e389ad | optimise | none | **baseline** |
| 2011 | darvas | India | 1.0 / v1.0-97e389ad | optimise | none | **baseline** |
| 2269–2274, 2320, 2331, 2354/2355, 3104, 3109/3110 | darvas | both | 1.0 | optimise | SMA50 exit, ATR trail, market gate, pyramid, equal alloc, PE, momentum rank | variants tested |
| 1905 | chart_pattern | US | 1.20 / v1.20-f15d06e4 | optimise | none | baseline (**1.21 has no plain run**; its defaults trade as 1.20) |
| 1830 | chart_pattern | India | 1.19 / v1.19-4c8e91c3 | optimise | none | baseline (1.20 added switches only, all on) |
| 3074 / 1906 | chart_pattern | US / India | 1.21 | optimise | every pattern off but ATRI | variant tested |
| 3064 / 2596 | chart_pattern | US / India | 1.16 | optimise | `BO_VOL=0` | variant tested (older rules) |
| 1729 | delivery_breakout | India | 1.0 / v1.0-16050f0b | optimise | none | **baseline** (US has no delivery data) |

Not read: minervini verify runs (1.54 and 1.64, both markets). No other family member has a verify run.

### How the edge checks were computed

- **Trials and deflated Sharpe.** N is the number of optimise runs recorded in `report_runs` for the strategy and
  market, across versions and variants. This is a lower bound: the minervini research notes cite earlier runs that
  are no longer stored. The deflated Sharpe uses Bailey & López de Prado's expected maximum Sharpe of N trials,
  from the standard deviation of those trials' Sharpes. It uses the baseline's daily returns (count T, skewness,
  kurtosis) from its `equity` table. For `minervini_coil` and `delivery_breakout`, with 1–2 runs, the family's
  89 runs per market supply N and the variance, which is conservative.
- **Matched random-entry null** (300 draws per run). For each baseline trade, one stock is drawn from the pool on
  the trade's entry date and held over the same dates, close of the entry session to close of the exit session.
  The traded stock is measured the same way. Measuring from the entry close removes the breakout day, which a
  buy-stop fill is conditioned on. Two pools are used. *Screen*: the strategy's own screen, rebuilt from stored
  prices on top of the liquidity floor. That is the Trend Template with RS rank ≥ 70 for minervini and the coil;
  close > a rising 200-day and within 15% of the 52-week high for breakout, darvas and chart_pattern; close above
  the 200-day for delivery. *Liquid*: the market's turnover floor only (0.32 bp of the top-1,000 turnover in the
  US, 1 bp in India), with 260 bars of history. Indices and funds are excluded.
- **Signals.** Every stored bar in `backtest_signals` for the run's spec id with hard gates passed and a
  tradeable setup. That is S1 only for breakout, and only `confirmed` breakout bars for chart_pattern; for
  chart_pattern India, the v1.20 FWDG-off partition stands in for the pruned 1.19 one. Consecutive bars (gaps of
  ≤ 10 sessions) are one *episode*. Forward returns run from the next open to the close 5, 20 and 60 sessions
  later, with maximum favourable/adverse excursion over 60 sessions. They are shown as excess over the same-date
  mean of the liquid pool (and, in one column, of the screen pool), using prices up to 2021-12-31. An episode is
  *traded* if the backtest entered that stock within 15 sessions of the episode. **Caveat:** for buy-stop
  strategies a traded episode is one whose price went on to cross the trigger. Traded-vs-skipped therefore
  flatters the traded side by construction. The useful comparison is all episodes against the pools.

---

## 1. `minervini` — Minervini SEPA (focus)

### 1.1 Scorecard (baselines 4156 US, 4154 India)

| Key parameter | US (4156) | India (4154) |
|---|---|---|
| CAGR / benchmark | −0.13% / 14.01% | 10.31% / 13.54% |
| Excess CAGR | **−14.14%** | **−3.23%** |
| CAGR excluding 2021 | 2.03% | **3.44%** (2021 alone: +84.3%) |
| Max drawdown / benchmark | −35.8% / −34.1% | −18.0% / −38.3% |
| Longest drawdown | 1,119 days | 739 days |
| Sharpe / Sortino / Calmar | 0.04 / 0.03 / 0.00 | 1.24 / 1.06 / 0.57 |
| Trades (per year) | 895 (99.5) | 181 (20.1) |
| Win rate / avg R / median R | 36.9% / +0.02R / −0.09R | 38.8% / +0.30R / −0.16R |
| Profit factor | 0.99 | 1.49 |
| Exposure / avg positions | 89.5% of days / 4.8 of 8 | 69.3% / 2.7 of 8 |
| Turnover / costs | 11.6× / $10,108 (8 bps) | 2.0× / ₹2.84 lakh (32 bps) |
| Days held, mean / median | 17.8 / 3 | 44.8 / 10 |
| Median stop distance | 5.8% | 6.7% |
| Best / worst year | 2013 +23.3% / 2021 −15.9% | 2021 +84.3% / 2018 −5.8% |

R by exit reason (closed trades):

| Exit | US n | US avg R | US sum R | India n | India avg R | India sum R |
|---|---|---|---|---|---|---|
| Light-volume breakout (next open) | 487 | −0.06 | −29.9 | 53 | −0.21 | −11.0 |
| Trend exit (50-day; 150-day after +3R) | 212 | +0.53 | +113.1 | 64 | +1.31 | +83.8 |
| Stop | 89 | −1.04 | −92.4 | 30 | −1.06 | −31.8 |
| Time stop | 69 | +0.11 | +7.5 | 14 | +0.22 | +3.0 |
| Breakeven stop | 35 | +0.63 | +22.0 | 17 | +0.54 | +9.2 |

R by setup:

| Setup | US n | US avg R | India n | India avg R |
|---|---|---|---|---|
| S8 flat-base buy-stop | 568 | +0.06 | 82 | +0.15 |
| S4 cheat (3C) | 226 | −0.02 | 58 | −0.03 |
| S2 VCP coil (buy-stop at pivot) | 43 | −0.03 | 13 | +0.97 |
| S9 shakeout | 37 | −0.11 | 12 | +1.38 |
| S1 VCP pivot breakout | 5 | −0.50 | 2 | +6.74 |
| S3, S5, S6 | 13 | — | 11 | — |

### 1.2 Is the edge real?

| Check | US | India |
|---|---|---|
| Trials N (recorded optimise runs) | 53 | 55 |
| Sd of the trials' Sharpes | 0.22 | 0.24 |
| Expected best Sharpe of N trials (annual) | 0.51 | 0.55 |
| Baseline Sharpe; skew / kurtosis of daily returns | 0.04; −0.49 / 6.8 | 1.24; −0.14 / 13.7 |
| **Deflated Sharpe** (P[true Sharpe > best-of-N]) | **0.08** | **0.98** |
| Null, screen pool (Trend Template): traded mean vs null mean | 0.55% vs 0.40% → **76th pct**, +0.01R | 8.74% vs 6.14% → **91st pct**, +0.35R |
| Null, liquid pool | 90.7th pct, +0.05R | 99.7th pct, +0.76R |
| Trades' own unmanaged return vs managed (actual fills) | 0.55% → 0.25% | 8.74% → 6.28% |
| Signal episodes (n) / 60-session excess vs liquid pool | 12,525 / +0.24% (month t = 0.16) | 6,291 / **+2.40%** (t = 4.49) |
| Same, vs the Trend Template pool | **−0.23%** | **−0.91%** |
| Traded / skipped episodes, 60-session excess (see caveat) | +1.38% (908) / +0.15% (11,617) | +6.11% (187) / +2.29% (6,104) |
| Best 5% of trades' share of total R | 45 trades = 872% of a net +20R | 9 trades = 118% of +53R |

**Reading.**
- **US: no edge.** The deflated Sharpe is 0.08. The trades pick no better than a random Trend Template stock
  (76th percentile, +0.01R), and the signals beat neither pool. The net +20R is the residue of large offsetting
  sums: +113R from trend exits against −92R from stops and −30R from the light-volume exit.
- **India: a real but narrow edge, from the screen.** The deflated Sharpe of 0.98 survives 55 trials. But the
  signals trail the Trend Template pool by 0.9% per 60 sessions. The Trend Template pool itself beats the liquid
  universe by 2.77% per 60 sessions (t = 3.5, 36 non-overlapping windows). Most of what India earns is momentum
  selection by the Trend Template, plus the 150-day trend exit. The VCP timing adds nothing measurable.
- **Concentration.** India's CAGR is 3.44% without 2021. Nine trades make 118% of the total R. US: 2013 alone made
  +23%, and every year from 2017 on is flat or negative.
- **Exits give back about half the move.** Over the same dates, the traded stocks' unmanaged return is 0.55% (US)
  and 8.74% (India) per trade; the managed result is 0.25% and 6.28%. Exits are still the lever, as
  `minervini-cagr-gaps.md` found.

### 1.3 The method: fidelity check against Minervini

Sources: *Trade Like a Stock Market Wizard* (2013), *Think & Trade Like a Champion* (2017), and the repo's
`research/minervini-backtest-spec.md`, `minervini-cagr-gaps.md`, `minervini-trade-reviews.md` and
`creator-mark-minervini.md`.

| # | Rule | Minervini | This code (1.66) | Kind | Matters? |
|---|---|---|---|---|---|
| 1 | **Fundamentals** (SEPA's earnings leg) | Leaders show strong, ideally accelerating, quarterly EPS and sales growth and widening margins; most of his big winners had them | Recorded per signal (`sepa`), **never enforced**; `--fundamentals guide/acceptable/leader` exist but have never been run in optimise | **missing** | **Likely large.** Untestable in India before late 2020; testable in the US (stored from 2009, about 76% of US trades scorable). US 4156 by verdict: LEADER +0.46R (n 28), ACCEPTABLE −0.06R (100), WEAK −0.02R (547), NO DATA +0.11R (217). That is a hypothesis on n = 28, not a finding |
| 2 | **What is bought** | The VCP pivot, plus low-cheat / 3C entries and power plays as earlier entries in the same base | 63% (US) / 46% (India) of trades are **S8 flat-base buy-stops**; 25% / 33% are **S4 cheats**; VCP pivots (S1+S2) are 5% / 8% | **different mix** | Likely. The VCP detector rarely leads to a trade; the book is mostly an O'Neil flat-base strategy |
| 3 | Pivot entry | Buy as price crosses the pivot intraday, on expanding volume | S2 fills only on a *close* through the pivot on ≥ 1.4× volume; S8 fills intraday at the buy-stop | different | Moderate: S2 pays the close |
| 4 | **Light-volume exit** | Low breakout volume is a warning, not an automatic next-morning sale | Any S2/S8 fill on < 1.4× volume is sold at the next open (US: 487 of 895 trades, −0.06R; India 53, −0.21R) | **added** | Known choice: 1.54 turned it off and **failed verify**; 1.55 restored it. Reported, not re-proposed alone |
| 5 | Stop | Never more than 10%; average loss 5–6% | Under the tight low, max 8%; median 5.8% / 6.7% | close | — |
| 6 | Sells | Sell into strength; a leader may be held to its 50-day; breakeven once up 2–3× the risk | Part sold at +2R or 25% over the 50-day; climax sale; 50-day exit → 150-day after +3R; 15-session time stop; breakeven at +2R | simplified | Known: the 150-day exit (1.64) was the largest single gain; "lean exits" helped the US, not India (cagr-gaps) |
| 7 | Sizing | Risk about 1.25–2.5% of equity per trade; 4–6 concentrated positions (up to about 10–12) | 1% risk, halved by progressive exposure most of the time; 8 slots; India averages 2.7 positions | different | Known: 1.5% risk with a 9% open-risk cap **lowered** India CAGR (cagr-gaps). Closed until the average trade improves |
| 8 | Progressive exposure | Size up after wins, down after losses | PE-01..03 | match | — |
| 9 | Market direction | Read the market through leaders and his own trades' follow-through, plus the indices | Benchmark above a rising 50-day + breadth + small/mid-cap index up over 63 sessions | different | Known: the segment test is 1.64's; it cut India's drawdown more than it added return |
| 10 | **Leadership group** | Leaders come from leading industry groups | Not applied (`--min-group-rs` exists; never run for minervini) | **missing** | Plausible, untested |
| 11 | RS | RS ≥ 70, preferably 80–90+ | ≥ 70 | threshold | **Contradicted:** RS bucket does not order R (US 70–80 0.00R, 80–90 −0.01R, 90+ +0.08R; India 0.47 / 0.28 / 0.04R) |
| 12 | Results | Avoid a new buy just before results | 14-day blackout on recorded announcements | match | — |
| 13 | Base count | Prefer early-stage bases | ≤ 3 | match | Base 4+ trades are not worse here (US +0.11R, n 86) |
| 14 | Universe | Live leaders, many young growth companies | Today's listed names (survivorship); turnover floor scaled to the market | data limit | Flatters every run; cannot be fixed without point-in-time constituents |

**Literature.** Minervini's own record (US Investing Championship 1997, 155%) and the documented success of
O'Neil-style growth-leader breakouts are practitioner evidence, not peer-reviewed tests of a rule set. The
published evidence behind the *screen* is strong: cross-sectional momentum (Jegadeesh & Titman 1993) and
52-week-high proximity (George & Hwang 2004). That matches what the data show: the Trend Template carries the
edge where momentum worked (India), and little where large-cap index returns dominated (US 2013–2021). The
fundamentals leg has a research analogue too: earnings momentum and post-earnings drift (Chan, Jegadeesh &
Lakonishok 1996; Bernard & Thomas 1989). That is the strongest documented reason to expect rule 1 to matter.

**Known choices, not re-proposed:** LIGHT_VOLUME_EXIT off alone (failed verify); the gap backstop, the reaction
add and follow-up buys (each failed its in-sample rule); 1.5% risk; the 6% stop cap; re-entry after a
light-volume exit (US-only win); the 150-day after +3R, the segment gate and the 8% cap (adopted in 1.64).

### 1.4 Diagnosis

- **The US loses on the stop and the light-volume exit.** Stops: 89 trades, −92R. Light-volume exits: 487
  trades, −30R. Trend exits recover +113R. With turnover of 11.6× a year, doubling costs would take roughly
  another 1.9 points a year (estimate: turnover × 2 × 8 bps; there is no cost-multiplier flag).
- **S8 dominates both books** (568 US, 82 India). It is O'Neil's flat base, bought on an intraday buy-stop and
  sold the next morning unless volume is heavy. Turning off `FLAT_COIL_ON` raised CAGR in both markets on older
  versions (US 1.51: −4.13% → −1.08%; India 1.52: 3.71% → 4.42%). It has not been tested on 1.64+.
- **Fundamentals have never been applied in a run.** The only evidence is the verdict split above (n = 28 LEADER).
- **India's figures rest on 2021.** Every change should be judged with and without 2021 (minimum: count the
  years improved).

### 1.5 Ranked improvements

| P | Change | Targets | Evidence | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| 1 | Enforce SEPA fundamentals, US: `--fundamentals guide`, against a `covered` control (and `acceptable` as the neighbour) | avg R, excess CAGR | Method rule 1; earnings-momentum literature; 4156 LEADER +0.46R (n 28) | Fewer, better trades | Trades fall sharply (NO DATA names drop) | Untested; US only (India data start late 2020) | from the method |
| 2 | Candidate D on 1.66 in **both** markets: lean exits (no partial, strength sale, time stop, light-volume exit or breakeven) + segment test in place of the index test | US CAGR, US drawdown | 3907 (1.63, US): 8.20% CAGR, Sharpe 0.60, −19.6%, 379 trades, +0.24R; never run in India | US positive; India unknown | Includes LIGHT_VOLUME_EXIT=0, which failed verify alone; win rate falls to ~29% | One US run; India untested; neighbours: lean only (#3804 US 2.42%) and lean + 150 (#3820 US 5.02%) form a rising sequence, not a spike | mechanics / known choice combined |
| 3 | Trade the VCP, not every flat base: `FLAT_COIL_ON=0`, `SHAKEOUT_ON=0`, `CHEAT_MIN_CONTRACTIONS=2` | avg R, US drawdown | Rule 2; FLAT_COIL_ON=0 helped both markets on 1.51/1.52; CHEAT_MIN_CONTRACTIONS=2 +0.9 points India on 1.63 | Higher R, fewer trades | India may fall under 120 trades | Each part was positive alone in both markets, on older rules | from the method |
| 4 | Industry-group leadership: `--min-group-rs 50` | avg R | Rule 10 (leaders from leading groups) | Small | Fewer trades | Untested | from the method |
| 5 | Report every run with `--idle-index` beside the plain figure | excess CAGR (as read) | India 69% of days exposed, 2.7 positions; cagr-gaps estimated +5.7 points from idle cash on #2778 | Comparability, not edge | None | Reporting only | mechanics (reporting) |
| — | RS ≥ 80/90 | — | RS does not order R in either market | — | — | Contradicted | not proposed |

---

## 2. `minervini_coil` — coil breakout (a Minervini experiment)

### 2.1 Scorecard (3309 US, 2817 India; v1.0 — v1.1 never run)

| Key parameter | US (3309) | India (2817) | US `--time-stop 0` (3852) | India `--time-stop 0` (3848) |
|---|---|---|---|---|
| CAGR / excess | −3.58% / −17.59% | 0.55% / −12.98% | 4.08% / −9.93% | 1.58% / −11.96% |
| Max drawdown / longest | −30.9% / 2,003 days | −16.0% / 1,783 days | −13.1% | −14.7% |
| Sharpe / Sortino / Calmar | −0.42 / −0.33 / −0.12 | 0.14 / 0.10 / 0.03 | 0.50 | 0.32 |
| Trades (per year) | 573 (63.7) | 184 (20.5) | 347 | 161 |
| Win / avg R / PF | 42.1% / −0.07R / 0.77 | 41.8% / −0.02R / 1.11 | 37.7% / +0.11R / 1.33 | 36.6% / +0.11R / 1.31 |
| Exposure / positions | 81.6% / 4.6 | 56.7% / 1.7 | — | — |
| Days held mean / median | 26.5 / 22 | 30.0 / 23 | — | — |
| Exits (US) | time stop 267 (+0.11R), trend 192 (+0.20R), stop 106 (−1.05R), breakeven 7 | time 62, trend 71, stop 43, breakeven 8 | — | — |

### 2.2 Is the edge real?

| Check | US | India |
|---|---|---|
| Trials | 2 (family distribution used: N 89, sd 0.32) | 2 (N 89, sd 0.28) |
| Deflated Sharpe / PSR vs 0 | 0.00 / 0.10 | 0.05 / 0.66 |
| Null, Trend Template pool | **2nd pct**, −0.12R | 17th pct, −0.13R |
| Null, liquid pool | 5th pct | 71st pct |
| Signal episodes / 60-session excess vs liquid / vs TT pool | 4,493 / +0.13% / −0.73% (t −1.27) | 2,883 / +2.03% / −1.24% |
| Best 5% of trades | 29 trades; total R is negative (−40R) | 9 trades; total R −3R |

**Reading.** The thesis asked whether a tight, quiet range near the high carries the VCP's edge without the swing
structure. **It does not.** Inside its own Trend Template screen the coil picks worse than random (US 2nd
percentile). Its time-stop-free variant earns +0.11R only through Minervini's exits. Its status already fixed the
criterion: beat the benchmark with a positive average R, *and* beat minervini in that market. v1.0 fails both.

**Fidelity.** By design it drops the VCP's swing structure. That is the experiment, not a gap.

**Plan.** Run v1.1 once (it has never been run, and its exits changed with 1.64). If it fails its own criterion,
retire it. Keep `core/contraction.py` as the chart's contraction gauge. No tweaks: no selection edge means entry
filters are the wrong place to work.

---

## 3. `breakout` — volume breakout (judged against O'Neil's CAN SLIM pivot)

### 3.1 Scorecard (3033 US, 2560 India)

| Key parameter | US (3033) | India (2560) | US `VOL_MULT=1.0` (2358) | India `VOL_MULT=1.0` (2359) |
|---|---|---|---|---|
| CAGR (at standard cost) / excess | 0.20% (0.04%) / −13.81% | 0.67% (−0.20%) / −12.86% | 5.40% (5.16%) / −8.61% | 5.72% (4.13%) / −7.81% |
| Max drawdown / longest | −31.5% / 1,970 days | −15.0% / 1,059 days | −32.9% | −15.6% |
| Sharpe / Sortino / Calmar | 0.08 / 0.07 / 0.01 | 0.14 / 0.10 / 0.04 | 0.42 | 0.69 |
| Trades (per year) | 437 (48.6) | 128 (14.2) | 818 | 226 |
| Win / avg R / median R / PF | 33.3% / +0.02R / −1.01R / 1.00 | 35.2% / +0.07R / −1.01R / 1.08 | 35.6% / +0.09R / 1.14 | 40.5% / +0.25R / 1.37 |
| Exposure / positions | 93.3% / 4.1 of 10 | 53.1% / 1.2 of 10 | 96.0% / 7.3 | 72.9% / 2.2 |
| Exits | stop 289 (−1.05R), target 144 (+2.17R) | stop 81, target 44 (+2.12R) | — | — |
| Median stop distance | 4.6% | 5.7% | — | — |

### 3.2 Is the edge real?

| Check | US | India |
|---|---|---|
| Trials / deflated Sharpe | 11 / 0.35 | 12 / 0.22 |
| Null, near-highs pool | **23rd pct**, −0.05R | **17th pct**, −0.19R |
| Null, liquid pool | 40th pct | 50th pct |
| Signal episodes / 60-session excess vs liquid | 10,970 / +0.09% (t −0.27) | 1,998 / −0.29% (t −1.24) |
| Best 5% of trades | 22 trades = 816% of a net +8R | 6 = 183% |
| Best / worst year | 2021 +20.9% / 2015 −8.4% | 2017 +11.3% / 2018 −6.2% |

**No edge of any kind:** no selection, no signal, no portfolio edge. The bracket (stop about 4.6%, target 2–3R)
makes it a coin-flip payoff game.

### 3.3 Fidelity against O'Neil

| Rule | O'Neil (*How to Make Money in Stocks*) | This code | Kind |
|---|---|---|---|
| Base | Cup 7+ weeks, flat base 5+ weeks ≤ 15% deep, after a prior uptrend | 20 sessions with range ≤ 6 ATR | different (shorter, ATR-scaled) |
| Pivot volume | 40–50%+ above average | > 1.5× (50%) | match; **contradicted by the data** (VOL_MULT 1.0 is better in both markets) |
| Buy range | Within 5% of the pivot | ≤ 4 ATR above the 20-day | different |
| Stop | 7–8% below the buy | 2 ATR, median 4.6% | tighter |
| Profit | Most profits taken at 20–25% (hold 8 weeks if +20% within 3 weeks) | Fixed 2–3R ≈ 9–14% | different |
| RS | ≥ 80 | none (`--min-rs 50` tried: small) | missing |
| Market (M) | Buy only in a confirmed uptrend | none (`--market-filter` tried: no change) | missing (tested) |
| Earnings (C, A) | Quarterly EPS +25%+, annual growth | none | **missing** |
| Leaders (L, I) | Leading group, institutional sponsorship | none | missing |

**Plan.** No selection edge means the CAN SLIM gaps worth closing are the *qualifying* ones (C, A, L), not the
entry. They overlap minervini's, so test them once there (§1.5 P1, P4) rather than build them twice. For
breakout itself, run only the volume neighbour and the combined exit (§7). If it still sits under its null,
retire it in favour of minervini plus darvas.

---

## 4. `darvas` — Darvas box

### 4.1 Scorecard (2010 US, 2011 India)

| Key parameter | US (2010) | India (2011) | US SMA50 exit (2269) | India SMA50 exit (2272) |
|---|---|---|---|---|
| CAGR (at standard cost) | 6.76% (6.56%) | 8.07% (**5.59%**) | **12.26%** (12.10%) | 9.19% (7.37%) |
| Excess CAGR | −7.25% | −5.46% | −1.75% | −4.34% |
| Max drawdown / longest | −38.2% / 1,030 days | −27.5% / 761 days | −26.9% | −26.5% |
| Sharpe / Sortino / Calmar | 0.49 / 0.44 / 0.18 | 0.63 / 0.59 / 0.29 | 0.79 | 0.68 |
| Trades (per year) | 858 (95.4) | 537 (59.7) | 622 | 404 |
| Win / avg R / median R / PF | 39.3% / +0.16R / −0.28R / 1.21 | 36.8% / +0.21R / −0.40R / 1.38 | 39.5% / +0.25R / 1.47 | 36.6% / +0.33R / 1.59 |
| Exposure / positions | 99.1% / 9.5 of 10 | 92.7% / 5.7 of 10 | 98.7% / 9.4 | 94.6% / 6.1 |
| Exits | box trail 645 (+0.54R), stop 203 (−1.04R) | trail 381 (+0.68R), stop 146 | — | — |
| Days held mean / median | 36.5 / 27 | 34.6 / 24 | — | — |
| Median stop distance | 6.8% | 8.1% | — | — |
| Best / worst year | 2013 +36.9% / 2018 −15.3% | 2021 +69.8% / 2018 −11.8% | — | — |

Other variants already run (do not re-propose): ATR trail ×3 (US 5.31%, India 9.81%); market gate (US 5.88%,
India 6.85%); pyramid at the box (US 7.81%; with momentum rank 10.56%); momentum rank with SMA50 (US 9.92%); equal
allocation 10% (US 7.11%); 8 slots (US 4.60%); progressive exposure (US 4.57%, India 5.62%).

### 4.2 Is the edge real?

| Check | US | India |
|---|---|---|
| Trials / deflated Sharpe | 10 / **0.80** | 5 / **0.94** |
| Null, near-highs pool | **98th pct**, +0.08R | 36th pct, −0.07R |
| Null, liquid pool | 94th pct | 86th pct |
| Signal episodes (boxes) / 60-session excess vs liquid / vs near-highs | 28,541 / +0.41% / +0.26% | 2,675 / +0.44% / −1.17% |
| Signals skipped for full slots (funnel) | 62,794 bar-signals; 9.5 of 10 slots used on average | 5.7 of 10 |
| Best 5% of trades | 42 = 173% of +135R | 26 = 170% of +109R |

**Reading.** Darvas is the only US strategy here whose trades beat a random stock from their own screen (98th
percentile, 858 trades). The edge is small (+0.08R a trade) but it is the family's only US selection signal. In
India it has none. The book is full almost all the time in the US, so ranking decides which boxes are bought. A
momentum rank did worse than the default with the SMA50 exit (9.92% vs 12.26%), so ranking is not the obvious lever.

### 4.3 Fidelity against Darvas (*How I Made $2,000,000 in the Stock Market*, 1960)

| Rule | Darvas | This code | Kind | Matters? |
|---|---|---|---|---|
| Box at new highs | Stocks at new (preferably all-time) highs, boxes stacking upward | 250-session high top, 3-session confirmations | close | — |
| **Earnings** ("techno-fundamentalist") | Bought only companies with rising earnings, in growth industries | `REQUIRE_EPS_GROWTH` switch, **off, never run** | **missing** | Likely; US-testable |
| Volume | Unusual volume on the breakout was a key sign | `REQUIRE_BREAKOUT_VOLUME` off | simplified | Family data say volume confirmation hurts (§7 F2): keep off |
| Initial stop | Accounts differ: the book's practice is a stop close under the breakout price; most rule summaries use the box bottom | One tick under the box bottom (median 6.8% / 8.1%) | **possibly different** | Unresolved: a tighter stop is a testable variant (needs code) |
| Trailing | Raise the stop under each new box's bottom | Same | match | Data: the box trail is the weak point (three in four exits); an SMA50 exit beats it in both markets |
| Pyramiding | Added on each new box breakout | Not in the rules; one-add variant tested | missing | Tested: higher CAGR only with momentum rank, avg R falls |
| Market | Stopped buying when boxes failed together (1957) | Switch tested: worse in both markets | known choice | — |
| Concentration | A few large positions | 10 slots, 1% risk | different | Untested |

### 4.4 Ranked improvements

| P | Change | Targets | Evidence | Robustness | Type |
|---|---|---|---|---|---|
| 1 | Make the trend exit the default: `--exit-mode ma --ma-col sma50 --no-target` | CAGR, avg R, drawdown | 2269/2272: +5.5 points US, +1.1 India (+1.8 at standard cost); avg R +0.10 / +0.12; US drawdown 11 points shallower | Two markets; the neighbour (SMA100) is still to run; the ATR trail is worse in the US, so this is a trend-exit effect, not "any looser exit" | mechanics (`backtest_args`, version bump) |
| 2 | Darvas's earnings rule, US: `REQUIRE_EPS_GROWTH=1` on top of P1 | avg R | Method; literature on earnings momentum | Untested; US only | from the method |
| 3 | Stop under the breakout level, not the box bottom | avg R, win rate | Method (book practice); 6.8–8.1% median stops are wide for a breakout | Needs code; fragile until tested | from the method (new rule) |
| — | Market gate, pyramid, momentum rank, PE | — | All run; none beat their comparison in both markets | — | known |

---

## 5. `chart_pattern` — classical patterns (Bulkowski, Brandt)

### 5.1 Scorecard (1905 US v1.20, 1830 India v1.19)

| Key parameter | US (1905) | India (1830) | US ATRI only (3074, 1.21) | India ATRI only (1906, 1.21) |
|---|---|---|---|---|
| CAGR (at standard cost) / excess | 4.95% (4.82%) / −9.06% | 7.40% (5.82%) / −6.13% | 7.11% / −6.90% | 6.09% (5.30%) / −7.45% |
| Max drawdown / longest | −25.6% / 1,618 days | −20.4% / 540 days | −19.2% | −12.8% |
| Sharpe / Sortino / Calmar | 0.41 / 0.39 / 0.19 | 0.64 / 0.63 / 0.36 | 0.59 | 0.73 |
| Trades (per year) | 504 (56.0) | 253 (28.1) | 328 | 104 |
| Win / avg R / PF | 25.3% / +0.31R / 1.16 | 27.7% / +0.30R / 1.36 | 23.4% / +0.30R / 1.41 | 29.7% / +0.49R / 1.66 |
| Exposure / positions | 100% / 8.6 of 10 | 95.3% / 4.0 | 100% / 7.8 | 83.5% / 2.0 |
| Exits | stop 369 (−1.06R), target 125 (+4.34R) | stop 180, target 69 (+3.78R) | — | — |
| R by pattern (n) | ATRI +0.45 (243), SYMM +0.32 (85), RECT +0.09 (75), FWDG +0.14 (55), IHS +0.20 (15), DBOT −0.81 (9) | ATRI +0.52 (81), SYMM +0.33 (69), FWDG −0.07 (46), RECT +0.41 (39) | — | — |

### 5.2 Is the edge real?

| Check | US | India |
|---|---|---|
| Trials / deflated Sharpe | 13 / 0.65 | 14 / 0.80 |
| Null, near-highs pool | 54th pct, +0.03R | **13th pct**, −0.24R |
| Signal episodes (confirmed breakouts) / 60-session excess vs liquid | 7,860 / −0.23% (t −1.50) | 754 / −1.13% (t −1.12) |
| Traded / skipped, 60-session excess | −0.15% / −0.23% | −0.87% / −1.22% |
| Best 5% of trades | 25 = 125% of +151R | 12 = 110% of +74R |

**Reading.** Pattern breakouts carry **no** forward information: confirmed breakouts trail the liquid pool at
5, 20 and 60 sessions in both markets. Their trades pick no better than random stocks. The positive average R comes
from the bracket geometry (a stop capped at 2 ATR, a measured-move target 3.8–4.3R away, about 26% wins), not from
the patterns. The ATRI-only result was chosen by slicing in-sample trades, and ATRI shows no signal edge either
(US 60-session excess −0.0%, India −1.6%).

### 5.3 Fidelity

| Rule | Bulkowski / Brandt | This code | Kind |
|---|---|---|---|
| Trend context | Bulkowski: results depend on breakout direction and prior trend; Brandt trades with the major trend | No trend test at all (the near_highs screen's criteria are not applied) | **missing** |
| Pattern length | Brandt: 8–12+ weeks, clear horizontal boundaries | Detector minimums, many shorter | different |
| Breakout volume | Bulkowski: heavy volume helps some patterns; Brandt does not require it | BO-01 volume required | different; **data: BO_VOL=0 better** (1.16: US 13.07% vs 5.28%, India 4.97% vs 2.87%) |
| Stop | Brandt: the "last day rule" (below the breakout bar's low) | Invalidation, capped at 2 ATR | different |
| Target | Measured move, which Bulkowski shows is often not reached | Measured-move bracket | match |
| Breakout buffer / compression | Brandt | BUFFER_ATR, COMPRESSION_ADX_MAX tested | known: buffer helped US only; ADX gate worse |

**Plan.** Run the current 1.21 baseline first (none exists). Then test the two changes that touch the method's
missing context: a trend filter (stock within the near-highs screen) and `BO_VOL=0` on current code. A trend
exit is the third variant. With no signal edge, pattern sub-selection is last.

---

## 6. `delivery_breakout` — India delivery-% breakout

| Key parameter | India (1729) |
|---|---|
| CAGR (at standard cost) / excess | −0.28% (−1.26%) / −13.81% |
| Max drawdown / longest | −14.8% / 949 days |
| Sharpe / Sortino / Calmar | −0.03 / −0.02 / −0.02 |
| Trades (per year) / signals | 106 (11.8) from 666 signal bars (176 episodes) |
| Win / avg R / PF | 35.8% / −0.02R / 0.95 |
| Exposure / positions | 37.4% / 0.6 of 5 |
| Exits | stop 63 (−0.99R), breakeven 25 (+0.61R), trail 18 (+2.50R) |
| Deflated Sharpe | 0.02 (family trials) |
| Null, above-200 pool / liquid pool | **15th pct** (−0.25R) / 24th pct |
| Signal episodes, 60-session excess vs liquid / vs above-200 | −0.51% / −1.55% (t −0.43) |

**Verdict.** The source is a trading video with no documented record, so the skill's rule applies: retire or
rethink before any tweak. No check finds anything. **Retire it as a standalone strategy.** If the
delivery-share idea is kept, test it as a *filter* on minervini's India trades. That is a scratchpad study on
stored `delivery_daily`, with no new strategy and no queued run: does a delivery spike in the 5 sessions before
entry order R on the 181 trades of run 4154?

---

## 7. Family summary

### 7.1 The family's best version today

**`minervini` 1.66 in India** is the closest to a working edge. It is the only member whose risk-adjusted
return beats its index in-sample (Sharpe 1.24 vs 0.86, drawdown −18% vs −38%). Its deflated Sharpe survives
55 trials (0.98), and its trades beat random liquid stocks (99.7th percentile). It is also the only member with a
passed verify verdict (1.64, India, on its pre-set criterion). The edge is narrow. It comes from the Trend
Template's momentum selection and the 150-day trend exit, not from the VCP. India's CAGR is 3.4% without 2021.

**In the US, the closest combination is a Darvas box entry with a 50-day trend exit** (2269: 12.26% CAGR, Sharpe
0.79, −26.9%, 622 trades). It is the only US strategy with a measurable selection edge (98th percentile). The
second-best US result is minervini candidate D (3907, 1.63: 8.20%, −19.6%). No US configuration beats SPY
(14.0%) in this window.

The combination of rules the family evidence supports:
- a momentum-qualified universe (Trend Template / RS);
- a simple base breakout entry (box or flat base);
- no breakout-volume veto;
- a trend exit (50-day, moving to the 150-day after +3R);
- a small/mid-cap segment gate;
- SEPA fundamentals (untested).

### 7.2 Ranked improvement plan

Pass criteria are fixed here, before any run. Each command is optimise stage. "Baseline" means the run named in §0.
India is judged at the **standard cost** (`cagr_std_cost`), because the non-SEPA runners model 10 bps where the
standard is 27 (§7.3 F4). Common robustness checks for every adoption:
- the neighbouring value points the same way;
- at least 5 of 9 years are not worse than baseline;
- the result holds without 2021;
- doubled costs, estimated from turnover, do not erase the gain.

| # | Change | Strategies | Type | Pass criteria (fixed now) | Needs code? |
|---|---|---|---|---|---|
| 1 | **SEPA / Darvas / CAN SLIM earnings rule, US** | minervini, darvas | from the method (shared) | `guide` against the `covered` control: avg R ≥ control + 0.15R; CAGR ≥ control + 2 pts; max DD no more than 3 pts deeper; ≥ 150 trades; `acceptable` points the same way | Only if adopted: `backtest_args` (`--fundamentals guide`, US) or the darvas switch; version bump, changelog, `filter_rules`/`gate_docs`; post-scan for minervini, so `signal_version` may stay |
| 2 | **Darvas trend exit as default** | darvas | mechanics | SMA100 neighbour within 2 pts of SMA50's CAGR in each market; SMA50 beats the box trail at standard cost in both (already: US +5.5, India +1.8); avg R ≥ +0.05R over baseline in both | Yes: `backtest_args`, `exit_rules`, version 1.1, changelog; `evaluate()` unchanged, so `signal_version` can be pinned to 1.0 |
| 3 | **Minervini candidate D on 1.66, both markets** | minervini | mechanics / known choice combined | US: CAGR ≥ 5%, Sharpe ≥ 0.45, max DD no deeper than −25%; India: standard-cost CAGR ≥ 9.3% and max DD no deeper than −20%; avg R ≥ +0.20R in both. Fails if India drops by more than 1 point (then it can only ship as a per-market setting, which needs code) | If adopted: constants (or per-market constants), version bump; post-scan, `signal_version` pin allowed. Must state that it includes LIGHT_VOLUME_EXIT=0, which failed verify alone |
| 4 | **VCP-faithful setup mix** | minervini | from the method | avg R ≥ baseline + 0.10R in both markets; CAGR no lower than baseline − 1 pt in either; India ≥ 120 trades | `FLAT_COIL_ON` / `SHAKEOUT_ON` are read by `evaluate()`: a rescan, no `signal_version` pin; `setup_docs`, version bump |
| 5 | **No breakout-volume veto** | breakout, chart_pattern | evidence (shared F2) | breakout: VOL_MULT 1.0 and 1.2 both beat 1.5 by ≥ 2 pts at standard cost in both markets; chart_pattern: BO_VOL=0 on 1.21 beats the 1.21 baseline by ≥ 2 pts in both markets, avg R not lower | Constant change, version bump; read by `evaluate()`: rescan |
| 6 | **Trend exit for bracket strategies** | chart_pattern, breakout | mechanics (shared F1) | CAGR ≥ baseline + 2 pts and max DD no deeper than baseline + 3 pts, in both markets | `backtest_args`; version bump |
| 7 | Group leadership `--min-group-rs 50` | minervini | from the method | avg R ≥ baseline + 0.10R in both markets; CAGR not lower by > 1 pt | Only if adopted (`backtest_args`) |
| 8 | Trend context for patterns: trade only while the stock passes the near_highs screen | chart_pattern | from the method | avg R ≥ +0.10R over the 1.21 baseline in both markets; ≥ 150 US / 80 India trades | Yes: apply the screen's criteria as gates (`evaluate()`, rescan) |
| 9 | Darvas stop under the breakout level | darvas | from the method | avg R up and CAGR ≥ trend-exit version in both markets | Yes: new stop rule (`evaluate()`/plan), rescan |
| 10 | Close the coil experiment | minervini_coil | — | Its own status criterion | No; retire if it fails |
| 11 | Retire delivery_breakout | delivery_breakout | — | — | Unregister after approval |

**Commands** (run from `scripts/`; one variant per change first, then the best combination):

```bash
# 0. Baselines that do not exist yet (current versions)
python -m jobs enqueue backtest --market us    --strategies chart_pattern  --stage optimise
python -m jobs enqueue backtest --market india --strategies chart_pattern  --stage optimise
python -m jobs enqueue backtest --market us    --strategies minervini_coil --stage optimise
python -m jobs enqueue backtest --market india --strategies minervini_coil --stage optimise

# 1. Earnings rule (US)
python -m jobs enqueue backtest --market us --strategies minervini --stage optimise --bt '--fundamentals covered'
python -m jobs enqueue backtest --market us --strategies minervini --stage optimise --bt '--fundamentals guide'
python -m jobs enqueue backtest --market us --strategies minervini --stage optimise --bt '--fundamentals acceptable'
python -m jobs enqueue backtest --market us --strategies darvas --stage optimise --bt '--exit-mode ma --ma-col sma50 --no-target' --const REQUIRE_EPS_GROWTH=1

# 2. Darvas trend exit: the neighbour
python -m jobs enqueue backtest --market us    --strategies darvas --stage optimise --bt '--exit-mode ma --ma-col sma100 --no-target'
python -m jobs enqueue backtest --market india --strategies darvas --stage optimise --bt '--exit-mode ma --ma-col sma100 --no-target'

# 3. Minervini candidate D on 1.66 (both markets)
python -m jobs enqueue backtest --market us --strategies minervini --stage optimise --const PARTIAL_R=0 --const STRENGTH_EXT_PCT=0 --const TIME_STOP_DAYS=0 --const LIGHT_VOLUME_EXIT=0 --const BREAKEVEN_R=0 --const MKT_INDEX_TEST=0
python -m jobs enqueue backtest --market india --strategies minervini --stage optimise --const PARTIAL_R=0 --const STRENGTH_EXT_PCT=0 --const TIME_STOP_DAYS=0 --const LIGHT_VOLUME_EXIT=0 --const BREAKEVEN_R=0 --const MKT_INDEX_TEST=0

# 4. VCP-faithful setup mix
python -m jobs enqueue backtest --market us    --strategies minervini --stage optimise --const FLAT_COIL_ON=0 --const SHAKEOUT_ON=0 --const CHEAT_MIN_CONTRACTIONS=2
python -m jobs enqueue backtest --market india --strategies minervini --stage optimise --const FLAT_COIL_ON=0 --const SHAKEOUT_ON=0 --const CHEAT_MIN_CONTRACTIONS=2

# 5. Breakout volume
python -m jobs enqueue backtest --market us    --strategies breakout --stage optimise --const VOL_MULT=1.2
python -m jobs enqueue backtest --market india --strategies breakout --stage optimise --const VOL_MULT=1.2
python -m jobs enqueue backtest --market us    --strategies chart_pattern --stage optimise --const BO_VOL=0
python -m jobs enqueue backtest --market india --strategies chart_pattern --stage optimise --const BO_VOL=0

# 6. Trend exit for the bracket strategies
python -m jobs enqueue backtest --market us    --strategies chart_pattern --stage optimise --bt '--exit-mode ma --ma-col sma50 --no-target'
python -m jobs enqueue backtest --market india --strategies chart_pattern --stage optimise --bt '--exit-mode ma --ma-col sma50 --no-target'
python -m jobs enqueue backtest --market us    --strategies breakout --stage optimise --const VOL_MULT=1.0 --bt '--exit-mode ma --ma-col sma50 --no-target'
python -m jobs enqueue backtest --market india --strategies breakout --stage optimise --const VOL_MULT=1.0 --bt '--exit-mode ma --ma-col sma50 --no-target'

# 7. Group leadership
python -m jobs enqueue backtest --market us    --strategies minervini --stage optimise --bt '--min-group-rs 50'
python -m jobs enqueue backtest --market india --strategies minervini --stage optimise --bt '--min-group-rs 50'
```

chart_pattern runs in the long lane (hours each). Add `--bt '--idle-index'` to a copy of any run that is adopted,
for the context figure. Items 8 and 9 need code first. Each new run is another trial: this plan adds about 24
optimise runs to the family. The deflated Sharpe of whatever is adopted must be recomputed with them.

**What would earn a verify run.** One configuration per strategy that passes its criteria above in both markets
(or, for an earnings rule, in the US), clears the robustness checks, and is shipped as its own version. Pass
criteria for that verify run are written before it runs. Minervini's next verify is the first since 1.64. Its
criterion should hold the 1.64 India conditions (CAGR > 0, avg R > 0, max DD no deeper than −25%) and add the US
as a condition rather than a report.

### 7.3 Shared fixes (proposed once, for the family)

| # | Fix | Applies to | Evidence | Needs code? |
|---|---|---|---|---|
| F1 | **Trend exit for breakout entries**: hold to a close below the 50-day, moving to the 150-day after +3R | darvas, breakout, chart_pattern (minervini has it) | minervini 1.64 (150-day after +3R: largest single gain, both markets); darvas SMA50 +5.5 / +1.1 pts; the trades' unmanaged move is larger than the managed one in every positive strategy | `backtest_args` per strategy; a `TREND_LOOSE` option for `--exit-mode ma` would need code |
| F2 | **No breakout-volume veto** | breakout, chart_pattern, darvas (keep off) | In-sample: breakout VOL_MULT 1.0 +5.2 / +5.1 pts with higher avg R; chart_pattern BO_VOL=0 (1.16) +7.8 / +2.1 pts; minervini light-volume exit off (1.53) +6.1 / +2.1 pts. 6 of 6 positive in-sample, but minervini's version **failed verify**, so treat it as a hypothesis, not a finding | Constants |
| F3 | **Earnings leg** (SEPA, Darvas, CAN SLIM C/A) | minervini, darvas, breakout | Method; earnings-momentum literature; never run | Flags exist; US only |
| F4 | **India cost model**: non-SEPA runners charge 10 bps in India where the standard is 27 bps | breakout, darvas, chart_pattern, delivery | darvas India 8.07% → 5.59% at standard cost; chart_pattern 7.40% → 5.82% | Yes, mechanics: use the market's standard cost in every runner (a backtest mechanics change: note it in each strategy's changelog) |
| F5 | **A cost multiplier** for the robustness gate (`--cost-mult 2`) | all | The skill's doubled-cost check is not runnable today; estimates from turnover range from 0.5 to 1.9 points a year | Yes, mechanics |
| F6 | **Idle cash** reported with `--idle-index` | minervini (India 69% exposure), delivery, breakout India | cagr-gaps §2 | No (flag exists); reporting only |
| F7 | **Work on exits, universe and qualification, not entry filters** | all | Signals trail their own screen in 9 of 11 baselines; no strategy except darvas US shows a selection edge inside its screen | — (a prioritisation rule) |

Survivorship bias (today's listed names) flatters every run in the family and cannot be fixed without
point-in-time constituents. Every absolute CAGR above is optimistic by an unknown amount.

### 7.4 The paper-trading gate

No family strategy has a paper book: `paper_orders` holds only the momentum books. Every strategy here was
refined before October 2026, so forward data is the only clean test.

| Book | Start when | Confirms the edge if, after ≥ 12 months **and** ≥ the trade count |
|---|---|---|
| `minervini` (India), the current or next adopted version | Now (it holds a passed verify verdict) | ≥ 30 closed trades; avg R ≥ +0.15R; profit factor ≥ 1.2; max drawdown no deeper than −15% of the book; the best 3 trades under 100% of total R (reported either way); fills within 2× the modelled 32 bps per side; every signal and skip reconciles with a backtest replay of the same days |
| `darvas` (US) with the SMA50 exit | After plan item 2 passes and ships as 1.1 | ≥ 60 closed trades; avg R ≥ +0.15R; profit factor ≥ 1.25; max drawdown no deeper than −20%; trade selection still beats a same-day random near-highs stock (the §4.2 null, re-run on the paper trades) |
| `minervini` (US) | Only after an earnings rule or candidate D passes | Same thresholds as India, ≥ 60 trades |

A paper book that misses its gate goes back to the optimise stage as a new version. It is not tuned on the paper
results.

### 7.5 What could not be determined, and what would settle it

- **Fundamentals in India before late 2020.** Not stored point in time, so the SEPA earnings leg cannot be tested
  in India in the optimise window. Settled by forward paper data, or by a point-in-time India results history.
- **Slot-skipped signals vs traded.** The stored signals do not mark which signals lost a slot. For buy-stop
  strategies, traded episodes are conditioned on reaching the trigger. A replay of the skipped-for-slots orders,
  from the simulator's own log, would settle whether ranking costs darvas or chart_pattern anything.
- **Darvas's own initial stop.** Sources differ on whether he set it under the breakout or under the box bottom.
  The book's examples, read directly, would settle what to test.
- **Doubled costs.** Estimated from turnover only, until F5 exists.
- **How much survivorship bias** inflates these figures. Settled only by point-in-time constituent lists.
