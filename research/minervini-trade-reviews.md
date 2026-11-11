# Minervini SEPA — trade reviews and the lessons to test

A running list. Each entry is one backtest trade reviewed on the chart against Minervini's own rules, and the
lesson it suggests, written as a measurable hypothesis. **Nothing here is a rule yet.** The lessons are tested
together, in one batch, once enough reviews have collected — each with its decision rule written before its run,
on the optimise window (2013–2021) first. Two cases are an anecdote; a lesson is adopted only if it holds across
the strategy's trades *and* across textbook setups rebuilt from stored prices.

The trades come from the 1.63 India optimise run (`v1.63-9a651e2c`, in-sample) unless stated.

## Lessons to test

| # | Lesson (hypothesis) | From | How to test | Status |
|---|---|---|---|---|
| L1 | After a stop-out, a base that reclaims its failed breakout high should be bought again (Minervini's re-entry) | RADICO 2021, UFLEX 2016 | S10 `RECLAIM_ON=1` as an optimise variant; compare CAGR and avg R with and without | Built (1.65, off). Two open parameters: the stop — under the shakeout low it is often wide (RADICO 11%, skipped at the 8% cap; `RECLAIM_STOP_DAYS=3` gives 7.5%) — and the window: UFLEX reclaimed 27 sessions after its failed high, past `RECLAIM_DAYS=20`. Test 20 vs 30 and both stops, rule fixed first |
| L2 | A base that starts right after a climax run (base high far above the 50-day, or a big gain into it) fails more often — and a cheat (S3/S4) inside it most of all: after an explosive run the only structure Minervini buys is the tight flag's breakout (the power play), not a shelf mid-flag | LUXIND 2021, BFINVEST 2017, GLENMARK 2020 (a one-day news spike), TMPV 2021, APCOTEX 2021 (a two-day spike) | Event study + the strategy's trades: avg R by the base high's distance above the 50-day (<15%, 15–25%, 25–50%, 50%+), by the 3-month and 10-session gains into the base high, split by setup (cheat vs pivot breakout) | Not tested. Both cases were cheats in widening bases right after a climax; the textbook cheat study (prior advance ≥25%, not a climax) found no split by contraction pattern, so widening alone is not the lesson |
| L3 | A cheat (S3/S4) confirmed on below-average volume fails more often: Minervini wants the stock to come out of the shelf on rising volume, and the strategy asks the shelf to dry up but sets no volume floor on the close through it | GLENMARK 2020 (0.6x), TMPV 2014 (1.0x), APCOTEX 2021 (1.2x); LUXIND 1.5x and BFINVEST 2.1x passed | The strategy's cheat trades and the textbook cheat event study: avg R by the cross day's volume ÷ its 50-day (<1x, 1–1.4x, 1.4x+), and by how far the close cleared the shelf | Not tested |
| L4 | A buy that sits just above the 50-day fails more often — the 50-day exit (EX-06) is then the trade's real stop, a day or two away. Two routes there: the stock regains a flat or falling 50-day (Minervini buys above a *rising* one; the gates ask only that the close is above it), or a base that began far above the 50-day sits long enough for it to rise into the shelf | TMPV 2014 (buy 1.7% over a falling 50-day), APCOTEX 2021 (2.7% over a rising one), LUXIND 2021 (about 5%) | The strategy's trades and textbook breakouts: avg R and the share sold by EX-06 within 10 sessions, by the buy's distance above the 50-day (<3%, 3–6%, 6%+), by the 50-day's 10-session slope, and by how many of the last 20 closes were below it | Not tested |

## Fixes found by the reviews (bugs, not hypotheses — they ship in the next version, measured with the batch)

| # | Fix | From | Where | Status |
|---|---|---|---|---|
| F1 | The results blackout misses an announcement ON the signal date: it blocks only dates strictly after it (`f > d`), so a signal on results day is bought at the next open, into the reaction. Make it `>=` | LTTS 2019 (board meeting 17 Jan, signal 17 Jan, filled into a 5x-volume reversal on the 18th), MARICO 2016 (results 29 Apr, the signal day) | `backtesting/spec.py` `results_blackout`, used by every strategy run with `--results-blackout` — a version bump for each | Not applied. Rough size: 15 of 201 India verify trades and 16 of 400 US had results within the four days up to the fill (avg R +0.53 / −0.08 against +0.38 / −0.04 for all), an upper bound on the leak |
| F2 | A flat base's pivot (S6 / S8) can be stale: it is the base's last *confirmed* swing high, which lags `SWING_K` sessions, so a higher high made in the last few sessions is ignored and the "breakout" can be a close through a level the stock already traded and closed above. Use the base's highest high through yesterday, as S9 does | MARICO 2016 (pivot 252.9 on 28 Apr; the stock had closed above it on 18, 21 and 22 Apr and made 263.5 on the 22nd), STAR 2015 (S8 filled at 1,261 under the 1,281 poke of the day before), ZEEL 2016 (pivot 458.95 after closes of 462–464 and a high of 466.4) | `minervini_spec.flat_base` (pivot) — evaluate and the chart share it | Not applied. Count how many S6/S8 trades had a higher high inside the base than their pivot before measuring |
| F3 | The results blackout tests the SIGNAL date, so a resting buy-stop (S2 / S8, kept up to 10 sessions) placed 15+ days before results can fill inside the window and hold through them. Test the fill date too (or cancel a resting order once results fall within the window) | ZEEL 2014 (S2 orders from 24 Dec; filled 10 Jan, results 22 Jan) | `portfolio_sim` pending orders / `spec.results_blackout` | Not applied. Small here: results day moved 1.5x and the loss came on 27 Jan from the market |

Already measured and rejected, so not lessons on their own: selling early on weakness after the buy (a close back
under the pivot, a run of down days; [CAGR gaps](minervini-cagr-gaps.md), early-weakness exits), and a cheat's
pullback count or contraction pattern (textbook cheat event study, [system-swing-longs](system-swing-longs.md) §6).

## Reviews

### RADICO.NS — S8 flat base, 20 Sep 2021, −1.05R

- **Trade:** flat base from 30 Jul 2021 (high 945, 7 weeks, 12% deep, 3rd base by the backtest's count). Buy-stop
  filled 20 Sep at 947.37, stop 881.55 (6.9%); stopped 30 Sep at 880.23.
- **Fine by Minervini:** Stage 2, Trend Template met, RS 74–75, market in an uptrend, volume dried up through the
  base (0.2–0.4x the 50-day), stop within 8%.
- **Issues:** supply at the pivot — 17 Sep ran to 958 on 3.4x volume and closed at 924.8; 20 Sep ran to 965 on 1.9x
  and closed at 931, both back inside the base. Then 21 Sep fell 4.7% on 2.3x volume (a violation he would sell on).
  A late base (about 4x off the March 2020 low).
- **The real miss:** the shakeout held the base (low 864 vs 833); 6 Oct closed back over 945 on 2.9x volume, 7 Oct over
  965, 12 Oct +15% on 8.7x, and it reached 1,267 by January. No setup fired on any session from 22 Sep to 14 Oct: the
  flat base had aged past 35 sessions and the shakeout widened the VCP. → **L1**.

### LUXIND.NS — S4 cheat (3C), 14 Sep 2021, −0.76R

- **Trade:** base from the 27 Jul 2021 high of 4,350 (2nd base, +434% advance); shelf 3,925–4,143 in the middle third.
  13 Sep closed 4,156 through the shelf on 1.5x volume; bought the 14 Sep open at 4,212.60, stop 3,905.35 (7.3%);
  sold 20 Sep by the 50-day exit at 3,988.
- **Fine by Minervini:** RS 89, a leader on fundamentals, strong market, stop within 8%. The 50-day exit beat the
  stop — the stock reached 3,430 by 29 Sep. 1.64 would take it too.
- **Issues:** the base followed a climax run — +136% in three months (1,846 on 27 Apr to 4,350), the base high 30%
  above the 50-day and 108% above the 200-day, where the strategy's own EX-04 sells part into strength. The 50-day
  had caught up by September, so the whole shelf sat about 5% over it. The pullbacks widened (8.4% → 12.3%; VCP-06
  rejected it), so the cheat fired in a loosening base. Day one closed back under the shelf. → **L2**.

### BFINVEST.NS — S4 cheat (3C), 1 Jan 2018, −1.08R

- **Trade:** base from the 24 Nov 2017 high of 431 (24 sessions, 3rd base by the chart's count); shelf 374–396.5 in the
  middle third. 29 Dec closed 396.7 through it on 2.1x volume; bought the 1 Jan open at 399.14, stop 372.20 (6.7%);
  stopped 16 Jan at 371.08.
- **Fine by Minervini:** RS 92, Trend Template met, stop within 8%, liquid (about ₹13 crore a day).
- **Issues:** the base IS the top of a blow-off. 272.6 on 15 Nov to 431 on 24 Nov, +58% in seven sessions on 3–7x
  volume (+173% from the 24 Aug low): the base high was 70% above the 50-day and 125% above the 200-day. A run like
  that is a power play at best, bought only through the flag's high (431), and a cheat mid-flag is not one of his
  entries. The pullbacks widened (10.2% → 16.5%; VCP-06 rejected it). Day one closed at 388.5, back under the shelf.
  The decline into the stop came on 0.3x volume — no selling, just no buyers, while the 50-day rose to meet the price
  (it was 366.5 on the stop day). An investment holding company with no growth fundamentals on record (SEPA "no
  data"): Minervini wants earnings behind a leader; the backtest's fundamentals filter is optional and thin in India
  before 2020. → **L2** (second case).

### GLENMARK.NS — S4 cheat (3C), 28 Aug 2020, −1.06R

- **Trade:** base from the 22 Jun 2020 high of 573.05 (48 sessions, 1st base); shelf 471–497.7 in the middle third.
  27 Aug closed 497.8 through it; bought the 28 Aug open at 497.75, stop 468.60 (5.9%); stopped 31 Aug at 467.90,
  three sessions in.
- **Fine by Minervini:** Trend Template met, a tight stop, the shelf itself quiet (0.2–0.3x the 50-day for a week).
- **Issues:** the base high is a one-day news spike — 22 Jun opened at 450, ran to 573 on 11.3x volume and closed at
  520 (the COVID-drug approval), +211% from the March low and 63% above the 50-day. The real structure under it is a
  range of about 415–510, so the "middle third" and the base depth are measured from a wick. The pullbacks widened
  (21.4% → 26.4%; VCP-06 rejected it). The cross was barely one: the close cleared the shelf by 0.1 on 0.6x average
  volume — no demand at the pivot. Fundamentals rated weak (SEPA) and RS 76. Nothing was missed by the stop: the stock
  ranged 444–536 for the next seven months. → **L2** (third case, the spike variant), **L3**.

### LTTS.NS — S4 cheat (3C), 18 Jan 2019, −0.99R

- **Trade:** base from the 3 Sep 2018 high of 1,855 (91 sessions, 3rd base, six pullbacks 21.8% → 8.6%, the final tight
  area dry at 0.93x); shelf 1,621.75–1,672 in the middle third, the VCP's own pivot 1,739.95 just above. 17 Jan closed
  1,693.4 through the shelf on 1.6x volume; bought the 18 Jan open at 1,720.15, stop 1,613.60 (6.2%); sold 31 Jan by
  the 50-day exit at 1,619.13.
- **Fine by Minervini:** a long, properly contracting base with a dry tight area; RS 96; a cheat within 1% of the
  pivot is nearly the pivot buy itself.
- **The issue: results.** The board met on 17 Jan, the signal day, and the fill on the 18th was the reaction: a run to
  1,757.7 then a close at 1,641.2 on 5.0x volume — a heavy-volume reversal Minervini would sell on, and a session he
  would not have bought into at all (he does not buy just before results). The strategy's 14-day results blackout
  should have blocked it, but it only looks at announcements after the signal date. → **F1**.
- The stock never made a new high in the next six months (best close 1,774.6, June 2019); the trend exit cut it near −1R.

### UFLEX.NS — S2 VCP pivot buy, 20 Jul 2016, −1.07R

- **Trade:** the first pivot-breakout loser reviewed. Base from the 21 Jun 2016 high of 245 (19 sessions, 1st base);
  pullbacks 15.8% (the Brexit sell-off, 24 Jun) → 5.5%, the tight area dry at 0.46x. Buy-stop at the 245 pivot
  filled 20 Jul at 249.04 (the session closed 248.3 on 1.9x volume), stop 230.30 (7.5%); stopped 3 Aug at 229.61.
- **Fine by Minervini:** a textbook VCP — contracting, dry, a confirmed breakout on volume, RS 88, results not due
  until 17 Aug. This is a loss he would also have taken.
- **What went wrong:** no follow-through. After the breakout day, nine sessions on 0.2–0.4x volume, a poke to 252.9 on
  25 Jul, then a slow drift into the stop. The base had followed an +85% run (base high 26.5% over the 50-day, the
  edge of **L2**'s buckets). Selling a stalled breakout early is already measured and rejected (early-weakness exits).
- **The miss:** the base held (low 223.9 against 206), and on 31 Aug–1 Sep it broke through the 252.9 failed high on
  3.2x and 4.5x volume and ran to 322.9 by mid-October, +28%. No setup fired from 15 Aug to 30 Sep: the base was 52
  sessions old (past the flat base's 35) and its last pullback widened (VCP-06). S10 would have seen the failed
  high, but 27 sessions after it — outside `RECLAIM_DAYS` = 20. → **L1** (second case, the window).

### MARICO.NS — S6 flat base, 2 May 2016, −1.06R

- **Trade:** flat base from the 14 Mar 2016 high of 252.9 (6 weeks, 7% deep, 2nd base). 29 Apr closed 259.1 through it on
  1.5x volume; bought the 2 May open at 262.29, stop 246.00 (6.2%); 3 May fell 4.8% on 1.5x, stopped 5 May at 245.63.
- **Fine by Minervini:** a shallow, orderly base in a leader of a defensive group, RS 86, not extended (the base high
  was 10% over the 50-day), volume on the cross.
- **Issues — two mechanical ones:** (1) results were announced on 29 Apr, the signal day, so the blackout missed it
  (→ **F1**, second case). (2) The pivot was stale: the detector still read the base high as 252.9, its last confirmed
  swing high, though the stock had closed above it on 18, 21 and 22 Apr and made 263.5 on the 22nd — that high is
  confirmed only five sessions later, on the 29th. So the "breakout" was the fourth close over a level already
  cleared, and the buy at 262.29 sat right under the real ceiling, 263.5; the next day it touched 268.7 and reversed.
  Read correctly, the pivot was 263.5 and nothing broke out until June (→ **F2**).
- Fundamentals rated weak (SEPA). The stock reached 300.9 by August, through a later base the strategy did not trade.

### TMPV.NS (Tata Motors) — S4 cheat (3C), 22 Jan 2014, −1.11R

- **Trade:** base from the 14 Oct 2013 high of 400.75 (67 sessions, 1st base, five pullbacks 5.8% → 11.4%, widening —
  VCP-06 rejected it); shelf 361.6–375.4 in the middle third. 21 Jan closed 380.7 through it on 1.0x volume; bought the
  22 Jan open at 377.97, stop 359.80 (4.8%); the 50-day exit sold it at the 27 Jan open, which gapped to 358.61 —
  below the stop.
- **Fine by Minervini:** a long base, RS 72, a tight stop; results not due until 10 Feb.
- **Issues:** the stock had closed under its 50-day on all 20 sessions before the signal, and the 50-day itself was
  drifting down (376.3 → 374.3). The cross put the price back over it by 1.7%, so the 50-day exit sat right under the
  buy — the trade's real stop was the 50-day, two sessions away. Minervini buys above a *rising* 50-day. The cross
  came on average volume (1.0x), and the pullbacks widened. The market wobbled in the last week of January (the 2014
  emerging-market sell-off). The stock went on to 448.6 by June. → **L4**, **L3**.

### TMPV.NS (Tata Motors) — S8 flat base, 17 Nov 2021, −0.05R

- **Trade:** flat base from the 14 Oct 2021 high of 530 (21 sessions, 1st base). Buy-stop filled 17 Nov at 531.35,
  stop 494.85; the session closed 530.2 on 1.1x volume, so the light-volume exit sold it at the next open, 530.65.
- **The rules worked.** The base sat on a news spike — 383 to 530 in four sessions on 3–5.5x volume (the EV-unit
  investment, 12–13 Oct), the base high 65% over the 50-day — so it is an **L2** case, but the unconfirmed breakout
  was cut at breakeven and the stock fell to 443 by 29 Nov.

### APCOTEXIND.NS — S4 cheat (3C), 9 Nov 2021, −0.53R

- **Trade:** base from the 13 Sep 2021 high (3rd base, four pullbacks 11.5% → 21.3%, widening — VCP-06 rejected it);
  shelf 380.2–404.5 in the middle third. 8 Nov closed 408.7 through it on 1.2x volume; bought the 9 Nov open at
  405.21, stop 378.25 (6.7%); the 50-day exit sold it 16 Nov at 391.82.
- **Fine by Minervini:** results already out (28 Oct), the 50-day rising, a tight shelf, RS 78. The 50-day exit beat
  the stop — the stock was at 345.8 by 30 Nov.
- **Issues:** the base high is a two-day news spike — 9 Sep +12.7% on 13.6x volume, 13 Sep +10% on 13.4x, from 343 to
  444 (33% over the 50-day, +55% in three months) — so the base and its thirds are measured from the spike (**L2**).
  The pullbacks widened. The cross came on 1.2x (**L3**), and day one closed at 402, back under the shelf. By November
  the 50-day had risen to 394.5, 2.7% under the buy, so the trend exit was the real stop (**L4**). Fundamentals rated
  weak (SEPA).

### STAR.NS (Strides Pharma) — S8 flat base, 21 Aug 2015, −0.94R

- **Trade:** flat base from the 17 Jul 2015 high of 1,257.83 (5 weeks, 10% deep, 3rd base). The buy-stop filled 21 Aug
  at 1,260.99, stop 1,189.35 (5.7%); the session closed 1,258.3 on 1.1x volume, so the light-volume exit sold at the
  next open — 24 Aug, the global sell-off after China's devaluation — which gapped to 1,198.2 (filled 1,196.41).
- **Fine by Minervini:** a proper flat base, not extended (the base high 15% over the 50-day), results already out (30
  Jul). The exit cost nothing extra: the stop would have been hit the same morning (low 1,075.6; 931 the next day).
- **Issues:** the pivot was stale again. On 19 Aug the stock ran to 1,269 and closed 1,255.6; on the 20th to 1,281.2
  and closed 1,233.3 — two pokes through 1,257.83 that failed, the RADICO pattern of supply waiting at the pivot. Those
  highs were not yet confirmed swing highs, so the buy-stop still sat at 1,257.83 and filled on the 21st *under* the
  previous day's 1,281 (→ **F2**, second case). The fill day itself was light (1.1x). Fundamentals rated weak (SEPA).
  The market shock is the larger cause and not a lesson: no rule sees it coming.

### ZEEL.NS — S2 VCP pivot buy, 10 Jan 2014, −1.05R

- **Trade:** base from the 11 Nov 2013 high of 292 (41 sessions, 3rd base, four pullbacks 6.6% → 5.7%, dry at 0.72x);
  S2 orders rested from 24 Dec and filled 10 Jan at 295.54 (closed 295.1 on 1.8x volume), stop 273.85 (7.3%); stopped
  27 Jan at 273.44.
- **Fine by Minervini:** a sound VCP and a confirmed breakout; not extended (base high 17% over the 50-day, the buy 5%
  over it).
- **Issues:** no follow-through (a high of 300.4 the next day, then back into the base). Results came on 22 Jan, 12 days
  after the fill: the blackout passed it because it judges the order's signal date, and the order had been resting
  since before the window (→ **F3**). The stop itself came from the market — 27 Jan 2014, the emerging-market
  sell-off, the same day TMPV was sold. Two of these reviews lost on that one week; the market filter stayed open.

### ZEEL.NS — S8 flat base, 15 Jun 2016, −0.36R

- **Trade:** flat base from the 16 May 2016 high of 458.95 (4 weeks, 6% deep, 1st base). The buy-stop filled 15 Jun
  at 460.14, stop 448.95 (2.4%); the session closed 457.8 on 0.6x, so the light-volume exit sold at the next open.
- **Issues:** the pivot was stale (→ **F2**, third case): the stock had closed above 458.95 on 7, 9 and 13 Jun (462–464)
  and made 466.4 on the 14th, none of them confirmed swing highs yet. The real ceiling was 466–475, cleared on 25 Jul
  on 1.4x volume.
- **The miss:** it then ran to 578.9 by October, +26%. The base was not bought again: after a light-volume exit the
  base stays closed (the 1.62 switch `REENTRY_AFTER_LIGHT_VOLUME`, runs #1449–1450, tests exactly this), and the
  25 Jul S6 signal came the day before results (26 Jul), so the blackout refused it — correctly.
