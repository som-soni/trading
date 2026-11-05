# Audit: the losing trades of Minervini run #2077

Run #2077: `minervini` v1.46 (`v1.46-f0433e82`), US, **optimise stage 2013-01-02 → 2021-12-31 (in-sample)**,
with one override, `--const FAIL_DAYS=3` (the failed-breakout exit switched on). 1,287 trades, 870 losers
(67.6%), 417 winners, average −0.024R, CAGR −1.96%.

Method: every trade is judged as of its **signal date**, from the run's own stored signal row
(`backtest_signals`, spec `v1.46-f0433e82`: gates, setups, base measurements), stored daily bars, and
results-announcement dates from SEC 8-K Item 2.02 filings (fetched for this audit; the backtest itself
never had them). Every check runs on the winners as well, so each proposed rule is shown with what it
would also have removed. All thresholds were fixed before the outcomes were looked at.

Per-trade marks for all 870 losers: `research/audit-minervini-run2077-losers.csv` (one row per loser:
the trend template, base quality, breakout volume, fundamentals, results date, market, entry against the
pivot, stop width, loss against the stop, and the category).

## In short

- **Losses respected the stop.** 858 of 870 losers lost no more than 1.05R; the 12 that lost more were
  overnight gaps through the stop, the worst −1.69R (EGHT, 23 Feb 2021). The median loser lost 0.22R in
  two days.
- **The coded screening rules are not where the losses come from.** Every gap against full SEPA that the
  code does not check (cheat trigger volume, contraction on cheat bases, weak fundamentals, RS 70–74,
  stop width) flags winners about as often as losers. Adding any of them would trim the strategy, not
  fix it.
- **Three genuine execution problems account for 680 of the 870 losers (78%):**
  1. the failed-breakout exit this run switched on (`FAIL_DAYS=3`): 336 losers, −121.9R;
  2. coil (S2) fills bought on a close the code already knew was on light volume, then sold at the next
     open: 268 losers, −20.3R;
  3. the 14-day results blackout keyed on the 10-Q/10-K **filing** date, not the announcement: 76 losers
     bought within 14 days before results, −20.5R.
- **The remaining 183 losers (21%) are normal losses**, and a 27% win rate on cleanly valid setups
  (36% in the run without the failed-breakout exit) is within what a breakout strategy loses. The
  strategy's real weakness is on the other side: its winners are too small (average R ≈ 0 overall), and
  no loser filter can fix that.

## Step 1 — the rule baseline

### Coded entry rules (as the strategy defines them)

Hard gates, all required on the signal session (`gate_docs`):

| Code | Rule |
|---|---|
| G1 | TT-05: close above the 50-day SMA |
| G2 | TT-01: close above the 150-day SMA |
| G3 | TT-01: close above the 200-day SMA |
| G4 | TT-02/TT-04: 50-day > 150-day > 200-day |
| G5 | TT-03: 200-day higher than 21 sessions ago (`SMA200_RISING_BARS = 21`) |
| G6 | TT-06: close ≥ 30% above the 52-week low (`MIN_PCT_ABOVE_52W_LOW = 30.0`) |
| G7 | TT-07: close ≤ 25% below the 52-week high (`MAX_PCT_BELOW_52W_HIGH = 25.0`) |
| G8 | TT-08: RS rating ≥ 70 (`RS_MIN_RANK = 70`) |

There is also a market gate (`MKT_FILTER = 1`: index above its `MKT_INDEX_SMA = 50`-day, breadth, follow-through
day), a liquidity floor (`MIN_TURNOVER_USD_M = 20`), at most `MAX_BASE_COUNT = 3` bases into an advance, and a
results blackout (`EARNINGS_BLACKOUT_DAYS = 14`).

Setups that buy (`setup_docs`, `entry_rules`):

| Setup | Coded rule | Entry |
|---|---|---|
| S1 MV-01 | finished VCP (VCP-01…10); close crosses the pivot on ≥ `VOL_MULT = 1.4`× 50-day volume, close in the upper `UPPER_HALF = 0.5` of the range, ≤ `BUY_RANGE_PCT = 5`% above the pivot | next open |
| S2 MV-02 | finished VCP; close ≤ pivot and within `COIL_PCT = 8`% | buy-stop 0.1% above the pivot for 10 sessions; **fills at the close of a session that closes at or above the pivot**; sold at the next open if that session's volume was under 1.4× |
| S3/S4 MV-03/04 | base passes VCP-01/02/03/05 only (still forming); 7-session shelf ≤ `CHEAT_SHELF_PCT = 8`% wide in the lower/middle third; shelf volume dry-up; a turn first (`CHEAT_RALLY_FRAC = 0.33`); volume contracting into the shelf (`CHEAT_VOL_CONTRACT = 0.9`); close through the shelf high. **No volume test on the trigger** | next open; stop under the shelf |
| S5 MV-05 | power play: ≥ 2× in 40 sessions, a 10–30-session flag ≤ 25% deep | next open |
| S6 | flat base 20–35 sessions, ≤ 15% deep, quiet, close through its high on ≥ 1.4× volume | next open |
| S7 | near miss: an S1 breakout of a base that missed one VCP rule narrowly | next open |

Stops: under the tight area / shelf / flag low, plus `STOP_BUFFER_PCT = 0.5`%; refused above `MAX_STOP_PCT = 10`%.
Exits: the stop; a third sold at +`PARTIAL_R = 2`R or 25% above the 50-day; breakeven stop after +2R; climax
signs; first close under the 50-day (trend exit); time stop if +1R is not reached within `TIME_STOP_DAYS = 15`;
and **in this run only**, a close back below the pivot within 3 sessions (`FAIL_DAYS = 3`).

### Against canonical SEPA

| SEPA criterion | Implementation | Gap |
|---|---|---|
| Trend template (TT-01…08) | G1–G8, exact | none (TT-03's preferred 4–5 months is a watch flag only) |
| RS ≥ 70 | G8 | none |
| VCP: contractions shrinking, tight, volume drying up | S1/S2 full check; S7 one rule missed narrowly | **cheats (S3/S4) and flat bases (S6) skip the contraction checks** by design |
| Volume on the breakout | S1, S6, S7 | **none on cheats or power plays; S2 fills before the volume test** |
| Earnings and sales growth (SEPA's fundamentals) | computed per trade (`sepa` label) but **not gated** | absent as a rule; 29% of trades have no data |
| Avoid buying just before results | 14-day blackout | **keyed on the SEC filing date, which comes weeks after the announcement** |
| Market in a confirmed uptrend | market gate | coded; its state per trade is not stored |
| Industry group leadership, institutional sponsorship | not checked | absent (not auditable from stored data) |
| Stop ≤ 7–8% typical, 10% absolute | `MAX_STOP_PCT = 10` | 24% of trades risked 8–10% |

## Step 2 — the checks, per losing trade

Each loser's row in the CSV marks, as of its signal date:

| Check | present / marginal / absent | Source |
|---|---|---|
| Trend template | marginal when RS 70–74, < 40% above the 52-week low, < 2% above the 50-day, ≥ 20% below the 52-week high, or the 200-day rising < 5 months | signal row, bars |
| Base quality | absent when a cheat or flat base sits on a base failing VCP-06; marginal for S7 | signal row `vcp_fail` |
| Breakout volume | S1/S6/S7 coded; S2 at the fill session; S3/S4/S5 on the trigger session: ≥ 1.4× present, 1.0–1.4× marginal, < 1.0× absent | bars |
| Fundamentals | `sepa` label: ACCEPTABLE/LEADER present, WEAK absent, NO DATA unverifiable | run's trade record |
| Results within 14 days after entry | absent when an 8-K Item 2.02 fell in the window; unverifiable without SEC coverage that year (317 trades) | SEC |
| Market | unverifiable: the gate is coded but its state is not stored per trade | — |
| Entry against the pivot | ≤ 2% present, 2–5% marginal, > 5% absent | trade record |
| Stop width | ≤ 8% present, 8–10% marginal, > 10% absent | trade record |
| Loss within the stop | ≥ −1.05R present, otherwise a gap through the stop | trade record |

How often each SEPA gap is flagged, losers against winners (base rate: 32% of trades win):

| Criterion flagged | Losers | Winners | Win rate when flagged | Mean R when flagged |
|---|---|---|---|---|
| Fundamentals WEAK | 498 | 236 | 32% | −0.038 |
| Cheat/power-play trigger volume < 1.0× | 295 | 105 | 26% | +0.001 |
| Cheat/flat base failing VCP-06 | 288 | 96 | 25% | −0.007 |
| Stop width > 8% | 210 | 95 | 31% | −0.060 |
| Close < 2% above the 50-day | 130 | 60 | 32% | −0.006 |
| RS 70–74 | 114 | 64 | 36% | −0.048 |
| Results within 14 days (SEC) | 76 | 34 | 31% | −0.084 |
| S7 near miss | 64 | 29 | 31% | +0.008 |
| < 40% above the 52-week low | 58 | 32 | 36% | −0.073 |
| Cheat shelf 7–8% wide | 51 | 15 | 23% | −0.127 |

The other two checks barely fire: only 2 trades entered more than 5% above the pivot, and 12 losers went
past −1.05R, all of them on gaps.

## Step 3 — classification

Taken literally, the prompt's precedence would put 681 losers (78%) in "invalid setup — rule gap". The
reason is that 57% of *all* trades have WEAK fundamentals and 31% are cheats on non-contracting bases. But
those criteria flag winners at the same rate (table above), so they are not why these trades lost. A loss
is attributed to a criterion only when that criterion separates losers from winners. On that basis:

| Category | Losers | % of losers | Total R | Mean R |
|---|---|---|---|---|
| 1. Invalid setup, rule gap | 0 | 0% | — | — |
| 2. Invalid setup, marginal (cheat shelf 7–8% wide, not otherwise flagged) | 7 | 0.8% | −4.1 | −0.59 |
| 3. Valid setup, flawed execution | 680 | 78.2% | −162.7 | −0.24 |
| — failed-breakout exit (`FAIL_DAYS=3`) | 336 | 38.6% | −121.9 | −0.36 |
| — S2 filled on a known light-volume close | 268 | 30.8% | −20.3 | −0.08 |
| — bought inside the results blackout (filing-date proxy) | 76 | 8.7% | −20.5 | −0.27 |
| 4. Valid setup, normal loss | 183 | 21.0% | −100.7 | −0.55 |

Precedence when a loser has two flags: results blackout, then S2 light fill, then failed-breakout exit,
then shelf width. The CSV gives every loser's category and all its marks, so the counts can be redone
under any other precedence.

## Step 4 — patterns

- **Category 1 — no criterion qualifies.** The most-flagged gaps are fundamentals WEAK (498 losers) and
  cheat trigger volume under 1.0× (295). Neither changes the odds: 32% and 26% win rates against 32%
  overall.
- **Category 2 — one weak candidate.** The cheat shelf at 7–8% wide, the top of `CHEAT_SHELF_PCT`'s range:
  66 trades, 23% win, −0.127R. Narrower shelves do not improve steadily, though (≤ 4%: +0.035R;
  4–5%: −0.042R; 5–6%: +0.019R; 6–7%: −0.058R), so this looks like noise in one bucket rather than a
  threshold that is too loose.
- **Category 3 — the recurring flaw is exits and fills that act on information the plan already
  rejects.**
  - **The failed-breakout exit.** It sold 387 trades: 362 losers and 25 winners, which averaged
    +0.19R. The strategy's own exit text says Minervini lets a dip below the pivot run to the stop, and
    about two in three breakouts close back under the pivot within ten sessions. Run-level comparison,
    same version and stage:

    | | Plain run (`FAIL_DAYS=0`) | This run (`FAIL_DAYS=3`) |
    |---|---|---|
    | Average R | +0.002 | −0.024 |
    | Win rate | 36.0% | 32.1% |
    | CAGR | −0.82% | −1.96% |

  - **S2 light-volume fills.** 517 of the 574 S2 trades were bought on a close that had already failed
    the volume test, then sold at the next open. The fill and the volume test read the same session's
    close. The 208 "winners" among them averaged +0.08R, an overnight gap rather than a trade.
  - **The results blackout.** It looks at `quarterly_results.filed`, which comes 35–53 days after the
    quarter ends, while the announcement comes at about 30. So buys landed days before reports. For
    example, MS (#123) was bought 15 Jan 2014 with results on 17 Jan. The 110 trades with results
    inside 14 days averaged −0.084R, against −0.017R for the rest.
- **Category 4 — within expectations on risk, not on reward.** Cleanly valid setups (no results-blackout,
  S2-light-fill or shelf flag) won 27.1% of the time at −0.012R in this run. That rate includes the
  failed-breakout exit; the plain run wins 36%.
  - All but 3 of these losses stayed within 1.05R; the worst was −1.66R, a gap.
  - The losers are in order. The problem is the size of the winners: a 36% win rate needs an average
    win near 2R to pay, and this strategy averages about 0R.

## Step 5 — what to change, what to leave

**Fix, in order of impact (all execution):**

1. **Do not adopt `FAIL_DAYS=3`; keep `FAIL_DAYS = 0`.** It costs 121.9R across 336 losers, and the
   plain run beats it on every headline figure.
2. **Base the results blackout on announcement dates.** Its own docstring already names data as the
   fix, and the dates exist: SEC 8-K Item 2.02 filings go back to 2004. This is the coded rule doing what
   it says, not a new rule.
3. **Do not fill an S2 buy-stop on a light-volume close.** Leave the order resting, the same way it
   already rests after a poke through the pivot that closes back below it.

**Leave alone (implicated only by category 4, or not separating winners from losers):**

- the trend template thresholds, including RS 70 and 30% above the low;
- the cheat entries' lack of a trigger-volume test;
- cheats and flat bases on bases failing VCP-06 (the same result came from replaying 418 cheats on
  5 Nov 2026);
- the 10% stop cap. Stop width shows no gradient: 5–6% is the worst bucket (−0.064R) and 6–7% is
  positive;
- the near-miss setup S7 (+0.008R);
- the shelf width, unless tested as a variant (`CHEAT_SHELF_PCT=7`) and judged on the optimise stage;
- a fundamentals gate. WEAK trades average −0.038R against +0.031R for ACCEPTABLE/LEADER (181 trades).
  The direction agrees with SEPA, but the gap is inside the noise for samples this size, and a gate would
  remove 236 winners. Improve the coverage first (next list).

**What the report should capture, so the next audit needs no reconstruction:**

1. The signal date and the signal row's key values in `trades.csv`: trigger-session volume ratio, close
   versus the 50-day, `pct_below_52w_high`, `pct_above_52w_low`, `vcp_fail`, base depth, and shelf or
   tight-area width. Today they exist only in the signal cache, which the weekly `prune_signals` job
   deletes after two versions. **After that, this audit cannot be repeated.**
2. The results date the blackout used, and its source (filing or announcement).
3. The market gate's state at entry (confirmed, pilot, or off).
4. For S2, the fill session's volume ratio, and whether the fill was at the close or intraday.
5. Fundamentals coverage: 370 trades (29%) are NO DATA, so the SEPA earnings criterion cannot be judged
   for them.
6. A CIK or identifier map for symbols with no SEC 8-K coverage (317 trades unverifiable for the
   results date: foreign issuers and renamed tickers).

## Step 6 — the coded fixes

### Fix 1 — the failed-breakout exit stays off

- **Current rule** (`minervini_spec.py`, the strategy default): `FAIL_DAYS = 0`. Exit text: "EX-02 — failed
  breakout: switched off. A close back below the pivot soon after the buy would sell here, but Minervini
  lets a dip below the pivot run to the stop…". This run overrode it with `--const FAIL_DAYS=3`.
- **Proposed rule:** no code change: `FAIL_DAYS = 0` stays, and the `FAIL_DAYS=3` variant is recorded as
  rejected in the strategy's `status` text: −0.024R against +0.002R per trade, 2013–2021 optimise stage,
  in-sample.
- **Losers it addresses:** the 387 `FAILED_BREAKOUT` exits of this run (362 losers; every one is in the CSV
  with `exit_reason = FAILED_BREAKOUT`).
- **Collateral:** 25 winners exited this way (+4.6R); without the exit they would have run to the other
  exits. Judged at the run level, which needs no hindsight: the plain run is better on win rate, average R
  and CAGR.

### Fix 2 — the results blackout on announcement dates

- **Current rule** (`backtesting/spec.py`, `results_blackout`):
  > "Drop a signal whose company files results within `days` calendar days AFTER the signal date. Results
  > dates are the filing dates stored in `quarterly_results` …"

  ```sql
  SELECT DISTINCT symbol, filed FROM quarterly_results
  WHERE market=%s AND symbol = ANY(%s) AND filed IS NOT NULL
  ```
- **Proposed rule:** a signal is dropped when the company **announces** results (an 8-K Item 2.02, not
  amended) within `EARNINGS_BLACKOUT_DAYS = 14` calendar days after the signal date. The filing date is the
  fallback only for a symbol with no stored announcements.
  - A new `marketdata` job (data layer) stores the dates in a table `results_announcements (market,
    symbol, announced DATE, accession, items)` from `data.sec.gov/submissions` (the source
    `marketdata/news.py` already reads, with the older `files[]` pages for history).
  - The blackout then reads, inside `asof`:

  ```sql
  SELECT symbol, announced AS d FROM results_announcements
  WHERE market=%s AND symbol = ANY(%s) AND announced <= %s          -- asof.end_date()
  UNION ALL
  SELECT symbol, filed FROM quarterly_results q
  WHERE market=%s AND symbol = ANY(%s) AND filed IS NOT NULL AND filed <= %s
    AND NOT EXISTS (SELECT 1 FROM results_announcements a WHERE a.market=q.market AND a.symbol=q.symbol)
  ORDER BY 1, 2
  ```

  The Python loop is unchanged: block when `0 < next_date - signal_date <= 14` days. This changes backtest
  behaviour, so it needs a version bump, a changelog entry and an updated W4 text.
- **Losers it would have excluded (76):** 7 NEU, 9 ETD, 22 DDS, 24 ACHC, 27 CRM, 42 NOW, 45 TRIP, 64 VC,
  71 VRTX, 74 CPAY, 75 THRM, 76 BHC, 102 CRM, 123 MS, 160 IBKR, 167 BR, 173 AZO, 176 HPQ, 220 KNX, 291 UNH,
  296 SABR, 300 DPZ, 325 OMF, 327 TXN, 332 JAZZ, 369 CRM, 407 COHR, 410 TAP, 440 DAR, 444 LFUS, 506 COHR,
  507 SLM, 516 ARCB, 548 XPO, 569 NVDA, 616 DXC, 654 OMCL, 659 CACC, 669 FIVE, 710 ILMN, 729 FDS, 755 NBIX,
  757 FTNT, 758 SABR, 806 RGEN, 808 HRL, 810 KWR, 831 OMCL, 868 CACI, 888 ADUS, 889 OPLN, 904 SNPS, 917 MDT,
  954 CMG, 956 TTMI, 961 REXR, 962 RS, 976 CRMT, 999 CGNX, 1001 KNSL, 1002 SMG, 1003 ABBV, 1010 WMS,
  1065 MTCH, 1126 EWBC, 1130 OMCL, 1137 ABR, 1138 TPR, 1139 BC, 1141 GTES, 1144 M, 1192 MS, 1203 TRMB,
  1260 MET, 1263 TDC, 1265 CATY. Together −20.5R.
- **Collateral:** 34 winners (+11.3R): 63 FCFS, 69 MX, 82 JACK, 214 SAIA, 326 MPWR, 408 CACI, 436 FIVN,
  438 AEIS, 521 NTAP, 524 AA, 549 HQY, 570 TTMI, 617 CEVA, 618 TRMB, 621 KRO, 624 NVDA, 652 SIGI, 760 MOS,
  807 FRPT, 820 AGX, 866 WWD, 873 SBAC, 965 MGRC, 1008 LITE, 1014 NDSN, 1066 MTD, 1104 KSS, 1109 BBWI,
  1140 IMO, 1175 HGV, 1222 HRB, 1259 OMCL, 1267 CRC, 1269 VSAT.
  - The ratio is 76:34, close to the base rate. The damage sits in buys 7–14 days before results
    (69 trades, −0.170R); buys 0–7 days before were positive (41 trades).
  - So this sample alone would not justify a *new* rule. The case for the fix is that the 14-day
    blackout is already the strategy's rule (and Minervini's), and today it is not applied as written.
    Verify on the optimise stage before shipping.
  - 317 trades had no SEC coverage and stay on the filing-date fallback.

### Fix 3 — an S2 buy-stop does not fill on a light-volume close

- **Current rule:**
  - Entry text: "Fills only on a session that CLOSES at or above the pivot, at that close…"
  - Exit text: "Unconfirmed breakout (MV-02 buys only). If the session that filled the buy-stop traded less
    than {VOL_MULT} times its 50-day average volume … the whole position is sold … the fill itself never
    depends on that session's volume."
  - Code (`backtesting/portfolio_sim.py`, the pending-order loop):

  ```python
  lvl = meta.get("confirm_close_above")
  if lvl is not None and float(bar["close"]) < float(lvl):
      skip("poked through the pivot but closed back below it", sym, today)
  else:
      triggered.append((sym, order, bar))
  ```
- **Proposed rule:** the confirming close must also carry the volume. A close through the pivot on under
  `VOL_MULT = 1.4`× the 50-day average leaves the order resting until its 10 sessions run out, exactly as
  a close back below the pivot does.

  ```python
  lvl = meta.get("confirm_close_above")
  mbv = meta.get("min_breakout_vol")
  v50 = float(bar.get("vol_sma50", float("nan")))
  if lvl is not None and float(bar["close"]) < float(lvl):
      skip("poked through the pivot but closed back below it", sym, today)
  elif (lvl is not None and mbv and v50 == v50 and v50 > 0
        and float(bar.get("volume", 0) or 0) < mbv * v50):
      # the close that would fill is already known to be unconfirmed: the order keeps resting
      skip("closed through the pivot on light volume", sym, today)
  else:
      triggered.append((sym, order, bar))
  ```

  The entry-day `LIGHT_VOLUME_BREAKOUT` check in `_manage` then never fires for these orders; keep it as a
  guard. Only minervini's S2 sets both `confirm_close_above` and `min_breakout_vol`. rs_leaders and darvas
  set `min_breakout_vol` alone: their buy-stops fill intraday, before the session's volume is known, so
  they are unchanged.

  As built (minervini 1.51, on the `minervini-next` branch), the check is behind
  `S2_FILL_NEEDS_VOLUME = 1`, and fix 2 is behind `RESULTS_BY_ANNOUNCEMENT = 1`. Both are signal-exempt,
  so a variant with either set to 0 reuses the scan.
- **Losers it would have excluded (305 S2 light-volume exits;** 268 of them have no other flag): every row
  in the CSV with `exit_reason = LIGHT_VOLUME_BREAKOUT`. Together −23.9R.
- **Collateral:** 208 "winners" (+15.9R, mean +0.08R): one-night holds that gapped up, not trades that
  worked. Net +8.0R; the R figures already include costs, and the fix saves 517 round trips of them.
  - Not verifiable from this report: some resting orders would fill later on a properly confirmed close.
    Those trades are not in this run.

### Not expressible as a data rule from the stored report

None of the fixes needed a pattern the system cannot express. The two SEPA checks that cannot be audited
from stored data, industry-group leadership and institutional sponsorship, have no proposed rule, because
no trade in this report can be shown to have failed them.
