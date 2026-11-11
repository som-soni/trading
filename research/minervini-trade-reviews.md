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
| L1 | After a stop-out, a base that reclaims its failed breakout high should be bought again (Minervini's re-entry) | RADICO 2021 | S10 `RECLAIM_ON=1` as an optimise variant; compare CAGR and avg R with and without | Built (1.65, off). Open question: the stop. Under the shakeout low it is often wide (RADICO 11%, skipped at the 8% cap); `RECLAIM_STOP_DAYS=3` gives 7.5% there. Test both, rule fixed first |
| L2 | A base that starts right after a climax run (base high far above the 50-day, or a big gain into it) fails more often — and a cheat (S3/S4) inside it most of all: after an explosive run the only structure Minervini buys is the tight flag's breakout (the power play), not a shelf mid-flag | LUXIND 2021, BFINVEST 2017 | Event study + the strategy's trades: avg R by the base high's distance above the 50-day (<15%, 15–25%, 25–50%, 50%+), by the 3-month and 10-session gains into the base high, split by setup (cheat vs pivot breakout) | Not tested. Both cases were cheats in widening bases right after a climax; the textbook cheat study (prior advance ≥25%, not a climax) found no split by contraction pattern, so widening alone is not the lesson |

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
