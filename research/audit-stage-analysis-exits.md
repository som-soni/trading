# Audit: the exits of the winning trades of four Stage analysis runs

The same four optimise-stage runs as `research/audit-stage-analysis-losers.md` (**2013-01-02 → 2021-12-31,
in-sample**):

| Report | Market | Rules | Winners | Of which still open on 2021-12-31 |
|---|---|---|---|---|
| 1269 | US | v2.6 | 73 | 8 |
| 1897 | US | v2.8 | 77 | 8 |
| 1889 | India | v2.8 | 32 | 5 |
| 1892 | India | v2.8, `W1_RANKS_ONLY=1`, `G7_BLOCK_STAGE=3` | 64 | 7 |

**Method.**
- **Replay.** Every trade (winners, and losers for the collateral check) is replayed from its own entry price and
  initial stop under seven exit rules, on stored daily bars resampled to the strategy's weekly bars. Each rule is a
  mechanical exit, nothing more.
- **Validation.** The replay of the *coded* exit reproduces the actual exit date and R on 559 of 560 trades. The
  miss is TJX in 1269: the v2.6 simulator did not test the stop on the fill session.
- **No verify-window data.** Price data are **cut at 2021-12-31**, the window's end. A replay still holding then is
  marked at that close, as the backtest marks its OPEN trades. Using 2022+ bars to judge an exit rule would tune it
  on the verify window.
- **R** is gross, (exit − entry) ÷ (entry − initial stop), for the actual and replayed trades alike (no costs).
- **Thresholds.** The rules and the 0.5R "material" threshold were fixed before the outcomes were tabulated. The
  two decisive-break rules in Step 6 (two closes, 3% below) were added *after* the investor replay was seen, and
  are labelled so.
- **Hindsight.** Post-exit data are used only inside the replays. The peak close while held is context, never the
  standard.

Per-winner marks are in `research/audit-stage-analysis-exits-winners.csv`, 246 rows. Each row has the exit, the
stage and line slope at exit, the swing lows the stop could have been raised to, every replay's R, and the
category.

## In short

- **No report uses a profit target or a time stop.** All four run `--no-target`. The reported target is used only
  to skip an *entry* whose fill would be at or above it. Every winner left by the 30-week trend exit, or was still
  held on 2021-12-31.
- **Every winner was sold with the stock still in Stage 2,** on the strategy's own stage machine, data up to the
  exit day. None was held into Stage 4. One (BERGEPAINT.NS, 1892) was held through 5 weeks of Stage 3, and still
  made +2.97R.
- **The guide's own exit rules capture less than the coded exit, in all four reports.** Those rules are a trailing
  stop under each correction low and selling half when the line flattens. The trailing stop is the cost: winners
  give up 9–50R per report (−41R and −44R in the US runs, −50R in 1892, −9R in India baseline 1889), and 3–7
  winners per report become losers. The coded exit captures 120–150% of that counterfactual.
- **The coded exit is a hair-trigger by the canonical reading.** 88–96% of the trend exits came on a single weekly
  close a median 1.1–1.6% below a line *still rising* more than 1% a month. Holding through such a close
  ("sell once the line has flattened") would have earned more on 4–14 winners per report. But net over all trades it
  is negative in two of four reports, and the two US runs disagree with each other. **Not supported.**
- **Money left on the table at exit is small. The big gap is at entry.** Category 2 (sold too early) is worth
  7–26R per report against the investor replay. Category 4 (sold too late) gave back 2–4R. The asymmetry
  Weinstein's method lives on is set by *where in Stage 2 the trade starts*: 62–83% of entries are new highs
  months into an advance (the losers audit). An exit can only ride the Stage 2 that is left.

## Step 1 — the exit-rule baseline

| Element | Canonical Weinstein | Learn guide "Stage analysis" | Code (all four reports) |
|---|---|---|---|
| Profit target | None: ride the whole Stage 2 | "No profit target. The trend, not a number, ends the trade." | **None.** `--no-target`; `target_rules`: the target is reported only, and "a buy-stop that would fill at or above that target is skipped" (entry only) |
| Time stop | None | None | None |
| Main exit | A break below the 30-week MA, decisive, especially once the MA has flattened (investor). Tighter for traders: swing lows, Stage 3 signs | "A weekly close below the 30-week average. Sell at the next open." | `--exit-mode weekly_ma --ma-weeks 30`: "a week that closes below the 30-week simple average of weekly closes sells the whole position at that close". One close, any slope |
| Stop progression | Raise the stop under successive bases and swing lows | "After each correction in Stage 2, raise the stop to just below the correction's low. Never lower it." | **Not modelled.** `stop_rules`: "It never moves." |
| Stage 3 | Exit into or soon after the top: MA flattening, churn, heavy directionless volume | "When the 30-week line flattens (within ±1% of its value 4 weeks ago) after a long advance, move the stop up close to the price, or sell half." | Not acted on by default. W2 blocks *entries* in Stage 3. v2.8 switches, all **off** in these runs: `EXIT_ON_STAGE3`, `EXIT_DIST_WEEKS`, `EXIT_ON_LOWER_HIGH` |
| Stage 4 | Never be in it | "A weekly close below a line that has turned down is the method's clearest sell." | The weekly close below the line sells before Stage 4 can be confirmed (3 weeks); the initial stop below that |
| Fill | — | Next open after the weekly close | That Friday's close |

The four reports share one exit rule. 1269 differs only in simulator mechanics: v2.7 changed fill timing and
tested the stop on the fill session.

**Gaps:**
- **The guide omits** canonical Weinstein's "decisive" break. It sells on any weekly close below the line, rising or
  not, so the investor's "especially once the MA has flattened" is lost. It also omits Stage 3's volume signature
  (heavy, directionless volume).
- **The code omits the guide's** trailing stop and Stage 3 half-sale, and fills at Friday's close instead of
  Monday's open.
- **The code adds nothing the methodology lacks on the exit side.** The skip-above-target rule is entry-side.
- **The guide is vague** on what a "correction" is for the trailing stop (no swing definition), on "long advance"
  before the Stage 3 warning, and on whether to sell half or tighten the stop.

## Step 2 — each winner's exit, data up to the exit date

| | 1269 | 1897 | 1889 | 1892 |
|---|---|---|---|---|
| Exit rule that fired | TREND_EXIT 65, open at the end 8 | 69, 8 | 27, 5 | 57, 7 |
| Stage at exit (machine) | 2: all 73 | 2: all 77 | 2: all 32 | 2: all 64 |
| Weeks held in Stage 3 / 4 | 0 / 0 | 0 / 0 | 0 / 0 | one trade 5 weeks of Stage 3 / 0 |
| Line rising more than 1% / 4 weeks at the trend exit | 88% | 90% | 93% | 96% |
| Median close below the line at the trend exit | 1.6% | 1.4% | 1.2% | 1.1% |
| Swing lows confirmed while held (stop never raised) | median 4 | 4 | 4 | 4 |
| Median give-back, peak close to exit (context only) | 1.4R | 1.3R | 1.4R | 1.4R |

Read mechanically, the code skipped no action Weinstein's rules require except the stop raises. No winner had the
line broken on a weekly close without an exit, and none was held into Stage 4. What it did do is the canonical
investor's forbidden action: it sold mid-Stage 2 on a single shallow close below a line that was still rising.

## Step 3 — the replays (mechanical, cut at 2021-12-31)

| Rule | Definition (fixed in advance) |
|---|---|
| code | The static initial stop, intraday; a weekly close below the 30-week line sells at that close. Validated 559 of 560 |
| guide | The guide's full set: a weekly close below the line → next open; the stop raised under each confirmed weekly swing low (lowest low of 2 weeks either side, known 2 weeks later) × 0.99 made after the entry, never lowered; sell half at the week's close when the 4-week slope falls to ≤ 1% after having been above it (the guide's Stage 3 warning) |
| trail | The guide's trailing stop and next-open exit only |
| flat_half | The guide's Stage 3 half-sale and next-open exit only |
| investor | Canonical investor: a weekly close below the line sells (next open) only once the line's 4-week slope is ≤ 1%, or the stage machine reads Stage 4; the static initial stop |

**Sum of R across winners:**

| Report | Actual | code replay | guide | trail | flat_half | investor |
|---|---|---|---|---|---|---|
| 1269 | 133.2 | 133.5 | 92.7 | 95.1 | 127.3 | 129.1 |
| 1897 | 130.6 | 131.0 | 86.9 | 87.4 | 126.4 | 119.5 |
| 1889 | 55.0 | 55.2 | 45.9 | 46.3 | 54.1 | 55.0 |
| 1892 | 177.4 | 178.0 | 127.4 | 145.8 | 152.5 | 185.7 |

**Sum of R across all trades, for the collateral check:**

| Report | Actual | guide | trail | flat_half | investor |
|---|---|---|---|---|---|
| 1269 | 80.7 | 51.0 | 53.2 | 77.3 | 88.3 |
| 1897 | 79.2 | 44.5 | 44.8 | 76.6 | 69.7 |
| 1889 | 14.2 | 14.2 | 13.9 | 15.6 | 11.0 |
| 1892 | 109.0 | 74.2 | 90.0 | 87.9 | 113.2 |

## Step 4 — categories (one per winner)

Precedence:
1. **4 (too late)** if the guide replay sold earlier for at least 0.5R more, or the trade was held into Stage 4.
2. **2 (too early, parameterization)** if the trend exit came on a close below a line rising more than 1% and the
   investor replay made at least 0.5R more.
3. **1 (rule gap)** needs a foreign rule such as a target or time stop. There is none, so the category is empty by
   construction.
4. **3** otherwise. A winner still held on 2021-12-31 made no exit to judge.

| Report | 1 Rule gap | 2 Too early | 3 Weinstein-consistent | 4 Too late | Open at the end |
|---|---|---|---|---|---|
| 1269 | 0 | 8 | 51 | 6 | 8 |
| 1897 | 0 | 7 | 56 | 6 | 8 |
| 1889 | 0 | 4 | 20 | 3 | 5 |
| 1892 | 0 | 14 | 40 | 3 | 7 |

Category 3 is the large majority, 63–73% of winners. **These are exits that look early only because the price
later rose.** Do not "fix" them: no mechanical Weinstein rule here would have held them for materially more.

**Category 2, by id: actual R → investor R**

| Report | Winners |
|---|---|
| 1269 | 7 KKR 1.88→3.68; 9 UNP 1.43→6.60; 23 VC 1.74→2.29; 27 CHE 0.12→2.60; 30 EW 2.87→3.81; 47 FISV 4.71→6.87; 58 ULTA 0.86→2.06; 74 LRCX 5.09→6.42 |
| 1897 | 7 KKR; 9 UNP; 13 PTC 1.89→2.88; 24 VC 1.52→2.03; 36 EW; 60 ULTA; 87 HLF 2.04→2.57 |
| 1889 | 3 HCLTECH 5.12→9.35; 47 BAJFINANCE 0.11→0.74; 68 NESTLEIND 1.02→2.43; 75 PIDILITIND 1.90→2.79 |
| 1892 | 20 SUNPHARMA 4.78→5.34; 26 HCLTECH 6.70→12.02; 33 TMPV 1.21→1.94; 56 ASHOKLEY 0.65→1.66; 72 TATASTEEL 0.30→2.92; 73 HINDPETRO 4.26→5.88; 74 PETRONET 2.98→4.37; 101 RELIANCE 0.40→3.26; 103 DABUR 0.24→0.96; 136 NESTLEIND 2.05→4.05; 137 BHARTIARTL 0.03→1.47; 144 DIVISLAB 2.10→5.62; 147 BERGEPAINT 2.97→3.85; 148 HINDPETRO 0.80→1.78 |

**Category 4, by id: actual R → guide R**

| Report | Winners |
|---|---|
| 1269 | 31 DIN 0.38→1.07; 56 EFX 0.13→0.71; 77 TSEM 0.85→1.47; 81 FCFS 0.82→1.33; 84 ICUI 5.21→6.09; 91 CNC 1.06→2.10 |
| 1897 | 25 URI 2.82→3.70; 26 WLK 0.02→0.58; 37 DIN; 58 EFX; 81 FCFS; 112 HELE 0.70→1.34 |
| 1889 | 7 HEROMOTOCO 1.01→1.68; 23 KTKBANK 0.01→0.95; 25 MRF 0.70→1.23 |
| 1892 | 76 KTKBANK 0.02→0.98; 104 INFY 0.09→0.89; 146 NAUKRI 2.62→3.59 |

None of these was held into Stage 3 or 4. They are winners whose last advance rolled over gently, where the
trailing stop sold at a higher swing low before the close below the line.

## Step 5 — within and across reports

| Report | Winners' R, actual | Guide-rule replay | Captured | Category 2 (left on the table) | Category 4 (given back) | Avg winner / avg loser |
|---|---|---|---|---|---|---|
| 1269 | 133.2 | 92.7 | 144% | +15.6R (8) | 4.3R (6) | 1.82R / −0.63R |
| 1897 | 130.6 | 86.9 | 150% | +11.2R (7) | 3.9R (6) | 1.70R / −0.66R |
| 1889 | 55.0 | 45.9 | 120% | +7.2R (4) | 2.1R (3) | 1.72R / −0.77R |
| 1892 | 177.4 | 127.4 | 139% | +25.7R (14) | 2.7R (3) | 2.77R / −0.69R |

- **Against the guide's own rules, nothing is left on the table.** The coded exit captures more than the guide's
  rules would in every report. The shortfall runs the other way, and its source is the guide's trailing stop under
  each swing low. Over the trade, that stop sits at a swing low a median 1.0–1.3R above the entry (the
  `highest_trail_R` column), and a normal Stage 2 pullback takes it out.
- **Against the canonical investor exit,** the gap is category 2, 7–26R per report. It is driven by one parameter:
  selling on *any* weekly close below the line, even a 1% dip below a steeply rising line. That money is not free.
  The same investor rule makes 12–13 US winners and 13 winners in 1892 into losers, and worsens 14–39 losers per
  report. Net over all trades: +7.6R (1269), −9.5R (1897), −3.2R (1889), +4.2R (1892).
- **Both sides together:** every variant cuts some Stage 2 runs short (category 2) and almost never overstays a top
  (category 4 is 2–4R, with no Stage 4 holds). Weinstein's asymmetry, the full Stage 2 ridden and Stage 4 refused,
  is half realized. The refusal side is complete, and the riding side is clipped by a hair-trigger line rule.
- **Ranking by realized asymmetry** (average winner against average loser):
  1. **1892** (2.77R / −0.69R)
  2. **1269 ≈ 1897** (1.82 / −0.63 and 1.70 / −0.66)
  3. **1889** (1.72 / −0.77)

  **The exit rule is identical in all four, so the exit does not explain the ranking. The entries do.** 1892's
  larger winners come from trades started early in a Stage 2: transitions averaged +1.56R against +0.20R for
  continuations, and the trades bought in recoveries while the market read Stage 4 averaged +2.04R. 1889 starts
  late and in fewer of them.

## Step 6 — exit-rule changes

The rule syntax is the strategy's module constants (`--const NAME=value`), the simulator's `ExitPolicy` and its
`weekly_ma` branch in `backtesting/portfolio_sim.py`. Net figures are per-trade replays: they ignore slot
competition, because a longer hold blocks a later entry, so only a backtest settles a change.

**No fixed profit target to remove.** Nothing to change. `--no-target` is already Weinstein's rule.

### Rejected: the guide's trailing stop under each correction low

- **Current:** `stop_rules`: "It never moves."
- **Proposed:** the stop raised to 0.99 × each confirmed weekly swing low made after the entry (2 weeks either side).
- **Effect:**

  | Report | Winners | Winners turned losers | Losers improved | Net, all trades |
  |---|---|---|---|---|
  | 1269 | 133.2 → 95.1R | 6 | 38 | −27.5R |
  | 1897 | 130.6 → 87.4R | 7 | 30 | −34.4R |
  | 1889 | 55.0 → 46.3R | 3 | 20 | −0.3R |
  | 1892 | 177.4 → 145.8R | 7 | 38 | −19.0R |

- **Verdict:** rejected. It realizes the guide's text and works against Weinstein's "ride the full Stage 2". On
  weekly bars a 2-week swing low is a normal pullback, not a base. **The guide is the root cause here.** Its
  "correction" is undefined, and the obvious mechanical reading is far tighter than the method intends. The guide
  should define a correction as a *base* within Stage 2 (several weeks sideways), not a swing low, or present the
  trail as the trader's option with that cost stated in general terms.

### Rejected: the guide's Stage 3 half-sale

- **Proposed:** sell half at the week's close when the line's 4-week slope falls to ≤ 1% after having been above it.
- **Net, all trades:** −3.4R, −2.6R, +1.4R, −21.1R.
- **Verdict:** rejected. The trend exit almost always comes first. Where the half-sale does fire, it sells the half
  that would have run.

### Not supported: a decisive break (the category-2 fix)

**Current:** "a week that closes below the 30-week simple average of weekly closes sells the whole position at
that close". In code: `trend_break = ma == ma and float(bar["close"]) < float(ma)`.

Three readings, each needing a new `ExitPolicy` field defaulting to today's behaviour:

| Report | (a) investor (line slope ≤ 1% / 4 weeks, or Stage 4) | (b) two weekly closes in a row below* | (c) a weekly close more than 3% below* |
|---|---|---|---|
| 1269 | +7.6R | +1.4R | +11.3R |
| 1897 | −9.5R | −14.2R | −11.1R |
| 1889 | −3.2R | +2.3R | −1.6R |
| 1892 | +4.2R | +14.6R | +16.1R |

\* added after the investor replay was seen.

Winners turned into losers: 8–13 per US report and 7 in 1892.

**Verdict:** not supported. The two US runs share one rule set and disagree in sign. The only consistent positive
is 1892, and an optimise A/B is the place to test
it, not this audit. If tested, use reading (c) as `--const TREND_EXIT_BELOW_PCT=3`: a new constant, 0 by default,
read by the simulator's `weekly_ma` branch as
```python
float(bar["close"]) < float(ma) * (1 - TREND_EXIT_BELOW_PCT / 100)
```
Test it in India first, with the pass criteria decided before the run.

### The A/B and its pass criteria (decided 2026-11-06, before any run)

Shipped in 2.10 as `TREND_EXIT_BELOW_PCT` (0 = off). India only, optimise stage, four runs: the baseline and
`W1_RANKS_ONLY=1 G7_BLOCK_STAGE=3`, each with the switch off and at 3.

**It passes only if, in both India configurations, the run at 3 beats its own off twin on all three:**
- CAGR higher by at least 1.0 point;
- max drawdown no worse by more than 2.0 points;
- profit factor not lower.

Anything less leaves it off. A pass earns a verify run, once, at the same value. It is not a change to the shipped
rule. The US is not tested: its two runs disagree in sign on the per-trade replay, so a US run now would be a
second fishing trip on the same years.

### Already expressible, nothing to change

Weekly closes are true weekly bars (`weekly_line`). The stage machine exists as `EXIT_ON_STAGE3`. That switch never
fires before the trend exit, on 0 of 240 baseline trades (2.8 A/B), which this audit confirms from the other side:
no winner is held into Stage 3 except one.

### Unverifiable

- What the 28 winners still open on 2021-12-31 would have done. Their exits are outside the window, by design.
- The intraday order of a stop and a recovery within one session.
- "Heavy, directionless volume" as a Stage 3 sign. The replays did not test it. The v2.8 distribution exit is the
  nearest coded version, and it cut drawdown but cost return in the optimise A/B.

## What this shows

On the sell side the code is a faithful, slightly stricter version of Weinstein. It has no target, sells on the
weekly close below the 30-week line, and never holds into Stage 4. The guide's extra exit rules, applied
mechanically, give back more than they save.

The exit is not where these strategies lose to their index. A strategy that buys a median 14–25 weeks into Stage 2
can only ride what is left of it. The lever is the entry, the same conclusion the losers audit reached from the
other side.

### Result (2026-11-06): fails, the switch stays off

v2.10, optimise stage (2013-01-01 → 2021-12-31), India vs ^CRSLDX:

| Configuration | Switch | CAGR | Excess | Max DD | Trades | PF | Avg R |
|---|---|---|---|---|---|---|---|
| Baseline | off | 1.31% | −12.23 | −20.7% | 85 | 0.97 | +0.01 |
| Baseline | 3 | 1.22% | −12.32 | −23.4% | 80 | 0.92 | −0.02 |
| W1 + G7 | off | 9.67% | −3.86 | −27.1% | 163 | 1.54 | +0.30 |
| W1 + G7 | 3 | 11.56% | −1.97 | −25.4% | 127 | 1.99 | +0.58 |

The W1 + G7 configuration passes all three tests (+1.89 CAGR points, drawdown 1.7 points better, PF higher). The
baseline fails all three (−0.09 points, drawdown 2.7 points worse, PF lower). The criteria ask for both, so the
switch stays off and earns no verify run. The split is the replay's mixed sign again: a looser exit helps where the
entries ride V-recoveries out of a Stage 4 market and hurts where they do not. Re-tuning the threshold on these
same years to rescue the baseline would be the fishing this section was written to prevent.

The off runs reproduce reports 1889 and 1892 exactly, so 2.10 with its switches off trades as 2.8 did.
