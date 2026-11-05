# Audit: the losing trades of four Stage analysis runs

| Report | Market | Rules | Overrides | Trades | Losers | CAGR | Index |
|---|---|---|---|---|---|---|---|
| 1269 | US | `stage_analysis` v2.6 (`v2.6-6514891e`) | none | 157 | 84 | 8.09% | 14.0% |
| 1897 | US | v2.8 (`v2.8-f1aa5af2`) | none | 155 | 78 | 8.04% | 14.0% |
| 1889 | India | v2.8 (`v2.8-f1aa5af2`) | none | 85 | 53 | 1.31% | 13.5% |
| 1892 | India | v2.8 (`v2.8-2af5c0af`) | `W1_RANKS_ONLY=1`, `G7_BLOCK_STAGE=3` | 163 | 99 | 9.67% | 13.5% |

All four are **optimise-stage runs (2013-01-02 → 2021-12-31, in-sample)**. Nothing here is a verified result.

**Method.** Each trade is judged as of its **signal date**, using the run's own stored signal row (`backtest_signals`
under the run's spec id), stored daily bars, and the strategy's own functions (`stage_series`, `ma30`). A buy-stop
rests for 10 business days, and the setup fires again the following week. So the row a trade was bought on is
not simply the latest row before the fill. It is the latest tradable row whose close, as a buy-stop, explains the
fill price (fill = max(fill-session open, signal close), within 0.6%). That match covers 557 of the 560 trades. The
3 it misses (TDG twice, HINDPETRO) are winners and are marked unverifiable. The stored slope matches the
recomputed one on all 557.

Every check also runs on the **winners**, so each proposed rule comes with what it would also have removed. All
thresholds were fixed in the audit script before any outcome was tabulated.

Per-loser marks for all 314 losers are in `research/audit-stage-analysis-losers.csv`. Each row has the report and
trade id, signal and entry, stage at signal, setup type, every check with its value, and the category. The trade id
is the row number in the report's trade table.

## In short

- **The classic implementation bug is not here.** No trade in any report was bought under a declining 30-week
  line. The median 4-week slope at entry is +2.0% to +2.7%, and only three entries had a line that had not turned up
  (DPZ, HELE), and all three won. G5 together with the stage machine does its job.
- **The real misidentification is the base, not the stage.** The "Stage 1 base" is the longest window of up
  to 104 weeks that is no deeper than 30%. In practice it stretches until it hits that cap: median depth 28.8–28.9%,
  median length 37–42 weeks. 68–80% of its weeks were already Stage 2, and the high being cleared was set a median
  3–8 weeks earlier. So most entries (62–83%) are new highs in a running Stage 2 advance, not breakouts from a
  Stage 1 base.
- **By Weinstein's book, most losers are invalid setups:** category 1–2 is 83–95% per report. **But the same flags
  sit on the winners, and the winners are larger.** Trades that pass every Weinstein check had a *lower* win rate
  and average R than the flagged ones in all four reports. In US v2.8 that was 17 trades, 35% wins, −0.29R, against
  51% and +0.61R. No entry rule passes the collateral check in more than one market.
- **Losses respected the stop.** Only 3–5 losers per report lost more than 1.05R, all overnight gaps through the
  stop (worst −1.76R, INFY.NS in 1892). The median stop-out was −1.0R and the median trend exit −0.4R to −0.6R.
- **Two execution findings are worth testing:**
  1. The stop sits exactly on the 30-week line, with no buffer. The guide's pseudocode puts it 1% below. In 46 of
     the 111 stop-outs across the four reports, the low on the stop-out day was within 1% below the stop.
  2. Report 1892's edge comes almost entirely from buying while the market index read Stage 4. That trade group
     was 44 trades and +89.6R of the run's +108.2R total. `G7_BLOCK_STAGE=3` blocks *only* Stage 3, which lets
     Stage 4 through.

## Step 1 — the three-layer rule baseline

### Rules side by side

| Element | Canonical Weinstein | Learn guide "Stage analysis" (as written) | Code, v2.6 / v2.8 (all four) |
|---|---|---|---|
| Bars | Weekly | Weekly (Friday close, summed volume) | Weekly bars from daily (`resample_weekly`, W-FRI), **evaluated every session against the week so far** |
| The line | 30-week MA | 30-week average of weekly closes | `MA_WEEKS = 30` SMA of weekly closes, this week's partial close included |
| Line state | Flattening, then turning up | Setup: "stopped falling: within ±1% of its value 4 weeks ago, or rising". Entry: "higher than 4 weeks ago" | G5: slope over `SLOPE_WEEKS = 4` ≥ −`FLAT_BAND_PCT` = −0.5% (flat passes), with hysteresis in the stage machine |
| Stage of the stock | Stage 1 → 2 transition; never Stage 4; not Stage 3 | Implied by the table; "Buying Stage 1" and "late Stage 2" listed as mistakes | G9: the machine's stage ≠ 4. W2: Stage 3 → WATCH (not bought). Stage 1 or 2 passes |
| Base | Sideways range after a decline | "Moved sideways for at least 12 weeks" (no measure) | Longest window ≤ `BASE_MAX_WEEKS = 104` with (high − low) / high ≤ `BASE_MAX_DEPTH_PCT = 30`, ≥ `BASE_MIN_WEEKS = 12` |
| Resistance | Top of the base / overhead | "Highest weekly high of the previous 26 weeks" (pseudocode `max(weekly_high[-27:-1])`) | The base window's own highest high, recomputed every week |
| Breakout | Close above resistance | Weekly close above resistance and above a rising line | Last close ≤ resistance < this week's close so far (G4: close > line) |
| Volume | Expanding on the breakout | ≥ 2× the previous **10** weeks' average | W1: ≥ `VOL_MULT = 2.0` × the previous `VOL_WEEKS = 4` completed weeks, with this week's **partial** volume |
| Relative strength | RS vs market turning positive | Stock ≥ index over **13 weeks** (Mansfield given as a variation) | G6: Mansfield (`MANSFIELD_WEEKS = 52`) > 0, **or ≤ 0 but higher than `MANSFIELD_RISE_WEEKS = 4` weeks ago** |
| Market | Forest first: no buying in a bear market | Index above a 30-week line that is not falling. Table: Stage 4 → skip; Stage 1/3 → half size | G7: the index's machine stage ≠ `G7_BLOCK_STAGE` (4). No size rule |
| Sector | Strong groups | Sector in Stage 1 or 2 (not 3 or 4) | G8: sector index stage ≠ 4 (Stage 3 passes; unmapped sectors pass) |
| Overhead supply | Avoid heavy supply just above | "Avoid heavy overhead supply" (no measure) | Not checked (reported only) |
| Universe | — | ₹10 cr / $10 m median turnover, price ≥ ₹50 / $5 | Daily G1–G3 (`near_highs` screen): close > 200-day, 200-day not falling, within 15% of the 52-week high; the market's liquidity floor; no price floor (split-adjusted history) |
| Entry | Initial breakout, or first pullback to the breakout level | Next session's open; or a buy-stop above resistance; investor: half now, half on the pullback | Buy-stop at the signal close, resting 10 business days; skipped if it would fill at or above the reporting target. No pullback or half entry |
| Initial stop | Below the base or the 30-week MA | Prose: "just below the **higher** of the line and the last significant low within the base". Pseudocode: `min(sma30, base_low) * 0.99` | `max(line, lowest weekly low of the base)`, no buffer. If more than `MAX_STOP_PCT = 15`% away → W3 → not bought |
| Exit | Weekly close below the MA; trailing stops; act on Stage 3 | Weekly close below → next open; trail under each correction; Stage 3: tighten or sell half | Weekly close below the line → that Friday's close; fixed initial stop, never trailed. v2.8 switches (off): `EXIT_ON_STAGE3`, `EXIT_DIST_WEEKS`, `EXIT_ON_LOWER_HIGH` |
| Ranking | Strongest RS first | — | Setup score, then 12-1 momentum (`--rank-by setup_momentum`) |

### How the four variants differ

- **1269 vs 1897** (US): identical scan and rules (`signal_version` 2.6). v2.7 changed only the simulator's fill
  timing and sizing (an exit frees cash only for later fills; the fill session tests the stop). v2.8 added three
  exits that are off. So the differences are fill mechanics and data corrections, not rules.
- **1889 vs 1892** (India): 1892 sets `W1_RANKS_ONLY=1`, so a low-volume breakout trades, ranked behind
  confirmed ones. It also sets `G7_BLOCK_STAGE=3`. The gate's test is `mstage == G7_BLOCK_STAGE`, so it refuses
  **only** market Stage 3 and **admits Stage 4**. The 2.4 changelog says this was intended: the machine confirms
  Stage 4 late, and the index rose while labelled Stage 4 in 15 of 16 episodes. But the variant's name reads as a
  tightening when it loosens the canonical rule.

### Gaps, both directions

**Canonical criteria the guide leaves out or leaves vague:**
- What "sideways" means: no depth, no range test.
- Whether a continuation breakout later in Stage 2 counts. The guide's own 26-week-high resistance does not
  require a pause either.
- "Last significant low" and "heavy overhead supply" are undefined.
- Canonical RS "turning positive" becomes a 13-week return race.

**Guide criteria the code leaves out or changes:**
- The ±1% flat band. The code uses 0.5%, and its comment calls that "the Learn guide's own rule". The 0.5% actually
  comes from the stages guide's 200-day rule ("more than 0.5% below its value 20 sessions ago"), not from this guide.
- The rising-line entry condition (the code accepts a flat line).
- The 10-week volume baseline. The code uses 4, and its comment "the guide compares the breakout week with the
  previous four" is not in this guide or any other Learn guide.
- The 26-week resistance (the code uses the base's own high), the 13-week RS, and entry at the next open after a
  completed week.
- The 1% stop buffer, the trailing stop, and the Stage 3 tightening.
- The sector filter excluding Stage 3, half size in market Stage 1 or 3, and overhead supply.

The guide has not changed since it was written (one commit, `70e4cef`). So these are code drift, not a guide that
moved.

**The guide contradicts itself in three places:**
- The stop is the "higher of" in prose and `min(...)` in pseudocode.
- The line is "within ±1% … or rising" in the setup and "higher than 4 weeks ago" at entry. The pseudocode asks
  for `flat and … rising`.
- The stop is "just below" in prose and ×0.99 in pseudocode.

**Code with no basis in either source:**
- The daily `near_highs` gates G1–G3.
- The longest-window, 30%-deep, 104-week base.
- Resistance redefined every week. This is why a stock re-qualifies as a "breakout" each week it makes a new high.
- `CONFIRM_WEEKS = 3`, `STAGE1_MIN_WEEKS = 6`.
- The 10-day order expiry and the skip-above-target rule, which acts on a target the guide says does not exist.
- 12-1 momentum ranking, which is loosely Weinstein's preference for the relatively strongest.
- G9 has a canonical basis (never buy Stage 4) but no explicit rule in the guide.

## Step 2 — the checks applied at each entry

Each check is marked present / marginal / absent / unverifiable, using only what was known at the signal date
(thresholds fixed in advance):

| Check | Absent | Marginal | Source |
|---|---|---|---|
| Line turned up | 4-week slope ≤ 0 | 0 < slope ≤ 0.5% (the code's own band) | Canonical, guide entry rule |
| Base after a decline, not a Stage 4 rally | Machine read Stage 4 in any of the 8 completed weeks before | — | Canonical |
| Base is a pause (a real consolidation) | The high being cleared was set < 6 weeks before (`STAGE1_MIN_WEEKS`) | — | Canonical (base), guide ("sideways") |
| Genuine resistance | Close not above the guide's 26-week high | Clears the base high by < 1% | Guide, canonical |
| Volume expanding | < 1.5× the prior 10 weeks | 1.5–2.0× | Guide (10-week, 2×) |
| RS positive | Mansfield ≤ 0 | 0 < Mansfield ≤ 2% | Canonical ("turning positive") |
| Weekly close confirms | Signal mid-week and that week's own close finished back at or below resistance | — | Canonical / guide (weekly closes) |
| Not Stage 3 | Machine reads Stage 3 | — | Canonical |
| Market not in Stage 4 | Index machine reads Stage 4 | — | Canonical, guide's table |
| Entry not chased | Fill > 3% above the signal close (a gap over the buy-stop) | — | Execution |
| Stop sensible | Stop < 5% away | — | Execution |
| Loss within stop | Loss worse than −1.25R | — | Execution |
| Not extended | Close > 25% above the line | — | Guide ("late Stage 2") |

**Unverifiable:** sector Stage 3 (G8 stores only pass or fail, and sectors use today's classification), and "heavy"
overhead supply. A higher weekly high within the two years before the base, less than 10% above the entry, is
recorded, but it is not used for any category.

**Weekly-timeframe note.** The code does not approximate the 30-week line from daily data. It resamples true
weekly bars. The approximation is *when* it reads them: every session, against the week so far. 22–56% of
entries were signalled mid-week (1897: 22%, 1269: 34%, 1889: 35%, 1892: 56%). That caused two misreads:

1. **The breakout failed to hold the Friday close.** In 6 / 5 / 3 / 25 losers (1269 / 1897 / 1889 / 1892), the
   signal week closed back at or below resistance. A weekly-close rule would never have bought them.
2. **Low "volume" was really a partial week.** In 1892, 66% of the 135 low-volume trades were mid-week reads.
   Their median volume was 0.87× when read mid-week and 1.16× once the week closed.

The second explains why W1 in India looks like it filters little: part of what it measures is the day of the week.

## Step 3 — categories (one per loser)

Precedence: any **absent** setup check gives category 1. Otherwise any **marginal** one gives category 2.
Otherwise an execution flag gives category 3. Anything left is category 4.

| Report | Losers | 1 Rule gap | 2 Marginal | 3 Execution | 4 Normal loss |
|---|---|---|---|---|---|
| 1269 US v2.6 | 84 | 54 (64%) | 18 (21%) | 2 (2%) | 10 (12%) |
| 1897 US v2.8 | 78 | 55 (71%) | 12 (15%) | 1 (1%) | 10 (13%) |
| 1889 India v2.8 | 53 | 31 (58%) | 13 (25%) | 0 | 9 (17%) |
| 1892 India W1 + G7 | 99 | 90 (91%) | 4 (4%) | 1 (1%) | 4 (4%) |

## Step 4 — within each report

**Category 1: which criterion fails** (counts among the category-1 losers; a loser can fail several):

| Criterion | 1269 | 1897 | 1889 | 1892 |
|---|---|---|---|---|
| No pause: the high was set < 6 weeks before | **46** (34 on this alone) | **46** (38 alone) | **20** (13 alone) | 52 (7 alone) |
| Volume < 1.5× the 10-week average | 3 | 1 | 3 | **78** |
| Signal week's close fell back below resistance | 6 | 5 | 3 | 25 |
| Market index in Stage 4 | 0 | 0 | 0 | 24 |
| Mansfield RS ≤ 0 (allowed as "improving") | 6 | 6 | 10 | 5 |
| Stage 4 within 8 weeks (a Stage 4 rally) | 8 | 8 | 1 | 5 |
| Below the guide's 26-week high | 1 | 1 | 3 | 4 |

**Category 2: the borderline value.**
- 1269: breakout under 1% above the base high (11), volume 1.5–2× (11).
- 1897: under 1% (9), volume (6).
- 1889: volume (6), line barely turned (4).
- 1892: under 1% (4), volume (3).

**Category 3: the recurring flaw.** Only a gap over the buy-stop: WLK +6.6% and NKE +4.8% (1269), DECK +3.8% (1897),
TATASTEEL.NS +9.5% (1892), all small losses. The 16 gap losses worse than −1.05R carry setup flags as well, so
precedence puts them in categories 1–2.

**Category 4: containment and the valid-setup win rate.** The category-4 losses stayed inside the stop:

| Report | Category-4 median | Worst | Valid setups (all checks present) | Their win rate / avg R | The flagged trades |
|---|---|---|---|---|---|
| 1269 | −0.47R | −1.00R | 19 | 37% / +0.32R | 137: 47% / +0.54R |
| 1897 | −1.00R | −1.01R | 17 | 35% / −0.29R | 137: 51% / +0.61R |
| 1889 | −0.93R | −1.11R | 11 | 18% / −0.39R | 74: 41% / +0.25R |
| 1892 | −0.50R | −0.67R | 5 | 0% / −0.39R | 157: 40% / +0.70R |

The valid-setup samples are small, 5–19 trades. Still, the direction is the same in all four reports: the trades
closest to textbook Weinstein did worse than the ones the textbook would reject.

## Step 5 — across the four reports

- **Lowest share of category 1–2 losers: 1889 (India baseline), 83%.** The US baselines are at 85–86% and 1892 at
  95%. What lowers 1889's share is not a rule. Indian entries more often follow a real pause: the median high was
  set 8 weeks before, against 3 in the US. 1889 still has the worst result: 1.31% CAGR, 38% wins, PF 0.97.
- **1892 has the most category-1 losers and the best result** (9.67% CAGR, PF 1.54). Both of its changes move away
  from Weinstein:
  - **W1 ranks only.** It trades low-volume breakouts: 78 of its losers, but also 44 winners worth +138R.
  - **`G7_BLOCK_STAGE=3`.** It admits market Stage 4. Its 44 trades in a Stage 4 market won 45% at +2.04R on
    average, against about +0.15R for the rest. They were +89.6R of the run's +108.2R. They cluster in April–October
    2020, March–June 2016 and December 2018–April 2019: V-shaped recoveries where the index's own 30-week line was
    still falling while the market rose.

  That is a market-layer stage reading that is faithful to the 30-week-line definition but late. The canonical
  rule (skip a Stage 4 market) would have removed most of this variant's edge.
- **The blind spot all four share:** the base detector and the weekly-reset resistance. No variant requires a
  consolidation, so every variant mostly buys new highs in a running advance and labels them "Breakout into
  Stage 2". None of them trails the stop, so none can act on the Stage 3 warning. Every one acts on partial weeks.
- **Closest to a correct Weinstein implementation:** the v2.8 baseline (1897 for the US, 1889 for India). It
  requires breakout volume, blocks a Stage 4 market, blocks a Stage 4 stock, and sells on a weekly close below the
  line. 1269 is the same rule set on the older simulator. Being closest to Weinstein is not the same as performing
  best, and in India the two point in opposite directions.

## Step 6 — rule fixes

The rule syntax is the strategy's module constants, switched with `--const NAME=value` on an optimise-stage
backtest, plus the gate code in `StageAnalysisStrategy.evaluate()` and `build_plans()`.

"Removes" counts trades the rule would have refused. Net R is minus the sum of their R, so a positive net means
the rule helps. This is trade-count arithmetic: a refused trade frees a slot that another signal would fill, so
only a backtest gives the real effect.

### Rejected: the collateral is as large as the benefit, or larger

| Candidate rule | 1269 | 1897 | 1889 | 1892 |
|---|---|---|---|---|
| F1 require a pause: the high cleared was set ≥ 6 weeks before | L46 / W49, net −55.6R | L46 / W52, −58.1R | L20 / W12, −2.3R | L52 / W40, −93.4R |
| F2 act only on a completed week whose close holds above resistance | L6 / W3, −4.9R | L5 / W2, −5.4R | L3 / W2, +1.3R | L25 / W13, −12.8R |
| F4 no Stage 4 in the 8 weeks before | L8 / W3, −0.6R | L8 / W3, −0.6R | L1 / W2, −1.2R | L5 / W12, −46.5R |
| F5 volume ≥ 1.5× the 10-week average | L3 / W4, −7.3R | L1 / W4, −9.4R | L3 / W1, −2.1R | L78 / W44, −81.4R |
| F5b volume ≥ 2.0× the 10-week average (the guide's rule) | L34 / W23, −22.4R | L25 / W24, −25.3R | L14 / W8, −2.4R | L88 / W51, −98.5R |
| F6 breakout ≥ 1% above the base high | L26 / W24, −17.6R | L27 / W26, −24.0R | L16 / W8, +2.4R | L57 / W40, −97.4R |
| F7 line rising, slope > 0.5% (the guide's entry rule) | L2 / W1, −0.6R | L0 / W3, −9.1R | L5 / W6, −4.7R | L4 / W3, +2.0R |
| F8 skip a fill more than 3% above the signal close | L7 / W5, −3.6R | L7 / W3, +4.3R | L2 / W1, −4.2R | L2 / W0, +0.5R |
| F9 only Stage 1 → 2 transitions (Stage 2 ≤ 13 weeks old) | L69 / W60, −68.0R | L62 / W60, −59.0R | L36 / W17, −6.3R | L67 / W39, −21.0R |
| Market not in Stage 4 (canonical G7) | — | — | — | L24 / W20, −89.6R |

Each of these is a real Weinstein criterion. Applying it removes winners at least as fast as losers, so adding one
would trim variance, not fix a defect. **Do not change the entry rules in response to these losses.**

### Candidate 1: a stop buffer (guide-sourced execution fix; test it, don't adopt it)

- **Current rule** (`build_plans`):
  ```python
  structural = max(float(line), base_low)
  stop = round_tick(max(structural, floor_), cfg.tick_size, "down")
  ```
  This places the stop exactly on the line.
- **Proposed rule:** a new constant `STOP_BUFFER_PCT = 0` (off by default; signal-exempt, because only
  `build_plans` reads it), with
  ```python
  structural = max(float(line), base_low) * (1 - STOP_BUFFER_PCT / 100)
  ```
  Test it with `--const STOP_BUFFER_PCT=1`, which is the guide's pseudocode ×0.99.
- **Losers it might have saved** (the stop-out day's low stayed within 1% below the stop):
  - 1269: 4, 18, 26, 35, 40, 98, 123, 124, 147
  - 1897: 4, 21, 30, 31, 45, 46, 47, 72, 76, 94, 98, 121, 122, 145
  - 1889: 1, 14, 15, 18, 38, 54, 66
  - 1892: 3, 4, 13, 14, 15, 42, 51, 69, 87, 97, 100, 102, 106, 133, 134, 138
  
  Whether they then recovered is unknown, and this is the post-entry path, not an entry judgement.
- **Collateral:** not countable from a trade list. Every position becomes about 7% smaller (1R widens by roughly
  1 point on a 13% stop), and some trades are stopped later instead of earlier. Only an optimise-stage A/B can judge
  it. The guide is partly the source: its prose ("just below") and pseudocode (×0.99) agree on a buffer, but its two
  stop formulas disagree on higher or lower.

### Candidate 2: Mansfield RS must be positive (US only; not supported across markets)

- **Current rule** (G6): `elif m_now > m_then: result.ok("G6", ...)`, so negative-but-improving passes.
- **Proposed rule:** a switch `G6_NEGATIVE_IMPROVING_OK = 1`. At 0, a Mansfield ≤ 0 fails G6.
- **Effect by report:**

  | Report | Losers removed (ids) | Winners removed (ids) | Net |
  |---|---|---|---|
  | 1269 | 2, 124, 128, 129, 131, 138 (−5.2R) | 31 (+0.4R) | +4.9R |
  | 1897 | 2, 122, 126, 127, 129, 136 | 37 | +4.9R |
  | 1889 | 11, 32, 36, 37, 69, 70, 71, 72, 76, 83 | 9, 29, 75, 77, 80, 81, 82, 84 | −3.2R |
  | 1892 | 7, 11, 27, 32, 34 | 35, 45, 153, 158, 161 | −4.5R |

- **Verdict:** 7 trades in the US, reversed in India. Not supported. At most it is a US optimise variant, and it
  should not be adopted on this evidence.

### Candidate 3: describe the setup honestly (documentation; no behaviour change)

The setup is named "Breakout into Stage 2" from a "Stage 1 base". Across the four reports, 62–83% of trades are
continuations in Stage 2 that is already months old (median 14–25 weeks into it), and the base is pinned at the
30% cap. Changes needed:

- `setup_docs`, `how_it_works` and `pattern_docs["Base"]` should say what the setup is: a weekly close above the
  highest high of the longest ≤30%-deep window, which in Stage 2 is usually a new high. Resistance moves up every
  week.
- Correct the code comments that attribute `FLAT_BAND_PCT = 0.5` and `VOL_WEEKS = 4` to this Learn guide. It says
  ±1% and 10 weeks.
- Note `G7_BLOCK_STAGE`'s `==` semantics in `param_docs`: at 3 it admits Stage 4.

### Candidate 4: fix the Learn guide (the guide is a source of the vagueness)

- Define "sideways": a range depth, or the line flat for a set time.
- Pick one line condition for the setup and the entry.
- Pick one stop formula ("higher of", then 1% below), and correct the pseudocode `min(...)`.
- Define "last significant low" and "heavy overhead supply" measurably.
- Say whether a continuation breakout later in Stage 2 is a valid buy.
- Per the Learn rule, the guide must not cite these backtests. It should state its definitions as definitions.

### Not expressible today

Nothing the audit needed is out of reach of the rule language: true weekly bars and RS against an index both
exist. Three things are missing:

- **Acting only on completed weeks.** This needs a switch in `evaluate()`: evaluate only on a week's last session.
- **The trailing stop under each Stage 2 correction.** This needs simulator support. There is no per-correction
  trail.
- **A sector Stage 1–2 filter.** G8 refuses only Stage 4, and stores no history of the sector stage it read.

## What this does and does not show

It shows that the losses are not caused by a stage-detection bug in the stock's own stage. They are the price
of a setup that buys new highs above a rising line, and the winners come from the same setup. It does not show
that the strategy has an edge: every report trails its index in this in-sample window.

The two things worth an A/B are the stop buffer and, separately, how the market layer reads Stage 4. The second is
a decision, not a bug fix, because the canonical rule and the measured result point opposite ways.

## Result of candidate 1 (2026-11-06): mixed, `STOP_BUFFER_PCT` stays off

v2.10, optimise stage (2013-01-01 → 2021-12-31). No pass criteria were written before this run, so it reads as
exploration, not a verdict.

| Market | Buffer | CAGR | Excess | Max DD | Trades | PF | Avg R |
|---|---|---|---|---|---|---|---|
| US vs SPY | off | 8.04% | −5.97 | −24.1% | 155 | 1.93 | +0.49 |
| US vs SPY | 1% | 7.19% | −6.82 | −21.3% | 149 | 1.94 | +0.46 |
| India vs ^CRSLDX | off | 1.31% | −12.23 | −20.7% | 85 | 0.97 | +0.01 |
| India vs ^CRSLDX | 1% | 1.89% | −11.64 | −17.8% | 72 | 1.09 | +0.06 |

The buffer lowers drawdown in both markets (2.8 and 2.9 points). Return moves in opposite directions: +0.58
points in India, −0.85 in the US. Fewer trades in both, probably because a wider stop makes more setups fail the
`MAX_STOP_PCT` limit (W3). PF is flat in the US. Nothing here earns a verify run. If the buffer is pursued, write
the criteria first. Lower drawdown at about equal return is the only claim these runs leave open.
