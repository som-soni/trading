# Minervini's book case studies — each run through our Minervini strategy

*Each case study in Mark Minervini's* Think & Trade Like a Champion *(2017), checked against the
strategy as it stands. The method: the strategy's own code on stored daily bars. That means
`trend_template_row` for the Trend Template, `vcp_spec.detect` and `MinerviniSpecStrategy.bases_live`
for the base, cheat and setups, and the market gate's index test on SPY. Each case records what the
book says, what our data shows, whether the strategy would have bought, and the rule that decided it.*

**How to read this.** These are the author's chosen examples, picked after the fact from his best
trades. A miss on one of them is not evidence that a rule is wrong. The tally at the end counts how
often each rule is the deciding reason. A rule that keeps blocking his examples is a candidate for an
**optimise-stage** variant (2013–2021), judged across all trades. It is never a reason to loosen a
threshold until one chart passes.

Prices are split-adjusted in storage. Each case quotes them at the book's scale, and says the factor.

This log is the narrative. The **score** lives in the permanent eval set, `tests/minervini_book_cases.py`. It holds
the figures of both books pinned to dates, and `tests.test_vcp_book_examples` scores them. Each case here names
its eval id. On 2026-11-09 the set caught 12 of 35 buy points, held 4 of 4 setups to avoid, and could not score 15
figures with no stored prices.

---

## Tally — the rule that decided each case

| Rule | Cases it blocked | Cases |
|---|---|---|
| Market gate closed (index below a rising 50-day, 5 sessions to confirm) | 4 | AMZN 2002; EBAY 2003 (by two sessions); WMT 1981–82 (every buy point); AAPL 2004 (2nd and 3rd buys) |
| Base anchored on an older, higher high (`vcp_spec` base high) | 1 | EBAY 2003 |
| Trend Template on the signal day (G1–G8) | 1 | AMZN 2002 (G4) |
| 3-C / cheat shelf: width (`CHEAT_SHELF_PCT`) | 1 | AMZN 2002 |
| 3-C / cheat shelf: volume (`CHEAT_DRYUP`, `CHEAT_VOL_CONTRACT`) | 1 | AMZN 2002 |
| Stop more than `MAX_STOP_PCT` below the fill | 1 | AMZN 2002 |
| Liquidity floor (turnover under the strategy's scaled floor) | 1 | WMT 1981–82: $0.6–1.6m a day against $2.8m |
| No RS-line rule (the book's tip-off, absent from the strategy) | 2 | AMZN 2002, EBAY 2003 (NFLX 2009: the RS line *lagged* at the breakout, so it must not become a hard gate) |
| Exit: the rest sold on the first close below the 50-day (EX-06) | 2 (caught, but the winner cut short) | NFLX 2009: +1.55R, against a 525% move; AAPL 2004: +1.2R, against +277% |
| Breakout volume under `VOL_MULT` (1.4× the 50-day) | 1 | AAPL 2004: 2 Jun (0.90×), 25 Aug (1.21×) |
| Close more than `BUY_RANGE_PCT` (5%) past the pivot | 1 | AAPL 2004: 26 Aug, 5.0% past it, on 2.3× volume |

| Case | Book's entry | Strategy buys? | Deciding rules |
|---|---|---|---|
| [AMZN, Oct 2002](#1-amazoncom-amzn-october-2002--3-c-out-of-a-22-week-base) | 3-C, 10 Oct 2002 | No, and no later setup through 2003 | market gate, G4, shelf width and volume, stop 12.4% |
| [EBAY, Jan 2003](#2-ebay-ebay-january-2003--a-7-week-base-after-the-market-low) | 7-week base, 6 Jan 2003 | No: it never sees the 7-week base. Shown only recent bars, it buys the same day (S8) | base anchored on the Dec 2001 high; market gate closed until 8 Jan |
| [NFLX, Oct 2009](#3-netflix-nflx-october-2009--a-27-week-vcp-months-after-the-market-low) | VCP breakout, 15 Oct 2009 | **Yes, the same day** (S1), after a 3-C two months earlier stopped out. But it sells the rest in Dec 2009 at +14% and never re-enters | caught; exit EX-06 |
| [WMT, 1981–82](#4-wal-mart-wmt-1981-82--a-leader-breaking-out-through-a-bear-market) | Buy points Oct 1981 and Mar 1982 | **Sees every setup** (a 3-C, VCP breakouts on 2 Nov 1981 and 30 Mar 1982) but buys none | liquidity floor; market gate |
| [AAPL, 2004](#5-apple-aapl-2004--three-buy-points-through-a-nasdaq-correction) | Three buys: Mar, Jun, Aug 2004 | **Buys the first** (S7, 27 Feb), sells it at +1.2R on 3 May; refuses the second and third | exit EX-06; breakout volume; buy range; market gate |

---|---|---|---|
| [AMZN, Oct 2002](#1-amazoncom-amzn-october-2002--3-c-out-of-a-22-week-base) | 3-C, 10 Oct 2002 | No, and no later setup through 2003 | market gate, G4, shelf width and volume, stop 12.4% |

---

## 1. Amazon.com (AMZN), October 2002 — 3-C out of a 22-week base

*Book: Figure 7-3, chapter 7. Eval id `ttlc-7.3-amzn` (scored a miss). Prices × 20 (the 2022 split).*

**What the book says.** AMZN bottomed in October 2001. Its first leg rose more than 300% in eight months
and turned the 200-day up: a confirmed Stage 2. From May to October 2002 it built a 22-week base, a
"perfect" 3-C. The tip-off was the RS line making new highs before the price broke out. He bought on 10
October 2002 as it cleared the pivot. That was the day the market bottomed after a 31-month bear market.

```series
title: AMZN, 2001–2003 — the book's Figure 7-3 redrawn from stored data
from: 2001-01-02
to: 2003-08-01
tf: W
line: us:AMZN | AMZN (weekly) | log candles
line: us:AMZN@sma150 | 30-week (150-day) average
line: us:AMZN@sma200 | 40-week (200-day) average
line: us:AMZN / us:SPY | RS line (AMZN ÷ SPY) | pane2
band: 2002-05-15 2002-10-09 | the 22-week base
mark: 2001-09-28 | stock bottoms | below
mark: 2002-10-10 | entry: 3-C, the day the market bottomed | below
caption: Stored prices are split-adjusted: multiply by 20 for the book's scale ($0.90 here is his $18). The RS line, in the lower pane, made 52-week highs in September and early October 2002, with the price still about 12% below its May high.
```

```series
title: AMZN, May–November 2002 — the base, the 3-C shelf and the entry, daily
from: 2002-04-15
to: 2002-11-29
tf: D
line: us:AMZN | AMZN | candles
line: us:AMZN@sma50 | 50-day average
line: us:AMZN@vol | Volume | pane2 bars
level: 1.02 | base high $20.40 | 2002-05-15 2002-11-29
zone: 0.8005 0.882 | 3-C shelf, 9.2% wide | 2002-09-30 2002-10-09
level: 0.882 | shelf high (pivot) $17.64 | 2002-09-30 2002-11-29 | pivot
level: 0.7965 | stop $15.93 | 2002-10-10 2002-11-29 | stop
mark: 2002-07-24 | base low $12.26 | below
mark: 2002-10-10 | closes through the shelf, 1.6× volume | below
caption: Prices ×20 for the book's scale. The shelf's volume did not dry up: 1.06× its 50-day average, against the strategy's 0.8× limit. The stop under the shelf sat 12.4% below the next open, beyond the 10% cap.
```

**What the data shows.**

| Item | Stored data |
|---|---|
| Base | High $20.40 on 15 May 2002, low $12.26 on 24 Jul; 113 sessions (his 22 weeks), 39.9% deep |
| Base shape | Detector: two legs, 10% then 39% — "wide and loose", fails VCP-06 as a VCP (VCP-10 once more of the base forms) |
| 3-C shelf (as of 9 Oct) | High $17.64, low $16.01, range 9.2%; 66% up the base (the cheat zone) |
| Trigger | 10 Oct close $17.96, through the shelf high, on 1.6× 50-day volume — his entry day |
| RS line (AMZN / SPY) | 52-week highs on 17–18 Sep and 7–10 Oct, with price still ~12% below the May high |
| Trend Template | Fails on 9 and 10 Oct: 50-day $15.62 under the 150-day $15.88 (G4). Passes from 15 Oct |
| Market gate | 10 Oct: SPY 80.6 against a 50-day of 88.2. Back above it 31 Oct; 50-day rising (10 sessions) from late Nov |
| Fill and stop | Next open $18.18; stop under the shelf low ≈ $15.93, 12.4% risk |
| Outcome | Low over the next 16 months $18.07; high $61.15 on 21 Oct 2003 (+236% from the fill) |

**Would the strategy buy?** No. Five checks refuse it, any one of them sufficient:

1. **Market gate closed.** A buy at the bear-market low is the point of this trade. The bottoming pilot
   (1.46, `MKT_PILOT`) tested buying small after a follow-through day or a breadth turn, and it failed its
   criteria.
2. **G4.** The 50-day stayed under the 150-day until 15 October.
3. **Shelf width.** 9.2% against `CHEAT_SHELF_PCT` = 8.
4. **Shelf volume.** 1.06× the 50-day with no quiet days (the test is ≤ 0.8×, or 2 days ≤ 0.5×). It was
   also 1.08× the rally before it (the test is ≤ `CHEAT_VOL_CONTRACT` = 0.9).
5. **Stop.** 12.4% against `MAX_STOP_PCT` = 10.

**Earlier attempts in the same base.** The 10 October shelf was the base's second 3-C attempt after the turn, not
its first:

| Date | Shelf high | Close | Misses |
|---|---|---|---|
| 9 Sep 2002 | $15.48 | $16.51 | width only: 8.2% against 8% |
| 10 Oct 2002 (his entry) | $17.64 | $17.96 | width 9.2%; volume 1.06× the 50-day; 1.08× the rally |

On 9 September the shelf missed by 0.2 points of width and passed every volume test. The same day failed the
Trend Template (the 50-day was under the 150-day) and the market gate, so the trade would still have been refused.
Since 2026-11-09 the Chart's Trade setups card shows both attempts on this base: "3-C refused", each with its
checks and a box round the shelf. Before that, the base read only "not a VCP".

**Why the VCP checks see no contractions here.** A new contraction counts only after a rally back into the top
quarter of the base (above $18.37 here). The right side peaked at $17.93, 70% of the way up. So every right-side
dip folds into the 39% decline, and the base reads as two contractions, 10% then 39%: "wide and loose". A 3-C
buys in the middle third, before the right side gets that high, so the VCP view is the wrong lens for it. The
cheat rules skip the contraction checks for that reason.

**Afterwards.** The Trend Template held from 15 October, but no later base qualified:

| Base | Failed rule | Reason |
|---|---|---|
| Dec 2002 – Mar 2003 | VCP-04 | one pullback |
| Mar – May 2003 | VCP-08 | the tight area wasn't ready |
| Jun 2003 | VCP-06 | final contraction 0.78× the reference; needs ≤ 0.6 |
| Jul 2003 | VCP-08 | the tight area wasn't ready |

The strategy misses the whole move.

**Why he took it — a reconstruction.** *This is inference from his stated principles and the stored prices; the
book does not give his full reasoning.*

1. **The strongest stock in a collapsing market.** From 24 July to 9 October the index made a lower low while
   AMZN made a much higher one: the divergence he looks for during a decline (the "sore thumb", see
   [creator note](creator-mark-minervini.md) §2.1). Its sellers were gone and buyers had been taking stock all
   through the decline. The RS line making new highs said the same in one line.

   | | Sept 2001 low → 9 Oct 2002 | 24 Jul → 9 Oct 2002 | 15 May → 9 Oct 2002 |
   |---|---|---|---|
   | AMZN | +182% | +20% | −15% |
   | SPY | −20% | −8% | −29% |

2. **A changed business.** *General knowledge, not stored data, which holds no fundamentals for 2002.* Amazon
   reported its first-ever quarterly profit in early 2002, a turn from dot-com survivor to a business that earns.
   That is what draws institutions in, and the 182% climb off the low was their footprint.
3. **He does not wait for the market.** Setups appear before or at the market's low, and the low is never
   known in time. So he buys a few leaders small and adds only if they work ([creator note](creator-mark-minervini.md)
   §2.2–2.3). A leader breaking out on the day of the low is his "coincident" setup, which he reads as cause, not
   coincidence.
4. **Small risk against a large possible gain.** A stop under the shelf risked about 9% from his buy at $17.64,
   probably less with a tighter stop and a small first position. The first objective, the old high at $20.40, was
   16% away, and a true leader out of a bear market can run for years.
5. **The weekly chart looked right.** A 40% base is deep, but he allows deeper bases after a bear market. The
   right side was two-thirds rebuilt, with weekly closes bunched together. The 3-C bought below the old high,
   before the crowd waiting for $20.40.

**In one line:** a leader with a changed business, holding up while the market made new lows, offering a
low-risk entry as the market exhausted itself. Our rules refuse it chiefly because they want the *market* to
confirm first; his edge here was trusting the *stock*.

**The caveat is hindsight.** Other stocks looked strong in October 2002 and failed. He expected many such buys to
stop out; Amazon is the one in the book. The bottoming pilot (1.46) bought at market lows and counted every such
case, losers included, and it failed its criteria. What remains untested is the narrower version: only stocks
whose RS line makes new highs while the index makes new lows. That is the RS-line study below.

**Takeaways.**

- The RS-line lead is the clearest gap. The book names it, the data shows it, and the strategy has no
  RS-line rule. It is worth a study across all breakouts before any rule: does a new RS-line high before
  the price breakout predict a better trade?
- The market-gate miss has already been tested and failed. A single example doesn't reopen it.
- The shelf thresholds wait on the tally. They are a candidate only if later cases miss on them too. Two specifics:
  - The width miss on 10 October is one bar: the 7-session window starts on 1 October, the bounce off the dip.
    From 2 to 9 October, highs and lows span 7.2%, and the closes 2.8%.
  - A close-based width, or a shelf that starts after the last swing low, would pass it. A candidate variant if
    the pattern repeats.
- Our cheat fills at the next open; he bought at the shelf high. From $17.64, the same stop risks 9.7%, inside the
  cap; from the $18.18 open it risks 12.4%. A buy-stop fill for cheats, as S8 already uses, is a second candidate.

---

## 2. eBay (EBAY), January 2003 — a 7-week base after the market low

*Book: Figure 7-4, chapter 7. Eval id `ttlc-7.4-ebay` (scored a miss). Stored prices match the book's scale (×1).*

**What the book says.** Some leaders bottom before the market. eBay bottomed in late 2000, almost two years
before the October 2002 market low. After the low, it built a tight 7-week base. By then it was in a confirmed
Stage 2 with a top RS ranking, and its RS line had been rising for a long time. The RS line reached new highs
well ahead of the price, the tip-off to institutional buying. From the point it emerged from the base, the
stock gained 234% in 24 months.

```series
title: EBAY, 2000–2003 — the book's Figure 7-4 redrawn from stored data
from: 2000-01-03
to: 2003-02-28
tf: W
line: us:EBAY | EBAY (weekly) | log candles
line: us:EBAY@sma150 | 30-week (150-day) average
line: us:EBAY@sma200 | 40-week (200-day) average
line: us:EBAY / us:SPY | RS line (EBAY ÷ SPY) | pane2
band: 2002-11-22 2003-01-03 | the 7-week base
mark: 2000-12-20 | stock bottoms | below
mark: 2002-10-09 | market bottoms | below
mark: 2003-01-06 | emerges from the 7-week base
caption: The RS line, in the lower pane, made one 52-week high after another from October 2002, while the price sat under its December 2001 high. That old high, $7.65, is what our detector measures the base from.
```

```series
title: EBAY, November 2002 – February 2003 — the 7-week base and the breakout, daily
from: 2002-10-15
to: 2003-02-28
tf: D
line: us:EBAY | EBAY | candles
line: us:EBAY@sma50 | 50-day average
line: us:EBAY@vol | Volume | pane2 bars
level: 7.654 | Dec 2001 high $7.65 (our detector's base high) | 2002-10-15 2003-02-28
zone: 6.955 7.455 | 7-week base, 6.7% deep | 2002-12-02 2003-01-03
level: 7.47 | buy-stop $7.47 | 2002-12-31 2003-02-28 | pivot
level: 6.96 | stop $6.96 | 2003-01-06 2003-02-28 | stop
mark: 2003-01-06 | breakout, 2.4× volume | below
mark: 2003-01-31 | low $6.74, probably a bad print | below
caption: Shown only these bars, the strategy finds the flat base and fills its buy-stop on 6 January. With the full history it measures the base from the December 2001 high instead, a 13-month base that fails its trend rule.
```

**What the data shows.**

| Item | Stored data |
|---|---|
| Stock low | $2.94 on 20 Dec 2000 |
| Held up | From its low to the market's low (9 Oct 2002): EBAY +90%, SPY −38%. From SPY's March 2002 high: EBAY −9%, SPY −34% |
| The 7-week base | High $7.46 on 2 Dec 2002, low $6.96; 20 sessions, 6.7% deep; volume below its 50-day average through December |
| Breakout | 6 Jan 2003: close $7.68, from $7.36, on 125M shares (2.4× the 50-day) |
| Trend Template | Passes every session from mid-November 2002 |
| RS line (EBAY / SPY) | 52-week highs from 27 Sep 2002 and through December, with the price below its old high |
| Market gate | Closed until 8 Jan 2003 (SPY back above a rising 50-day, held 5 sessions); open 8–16 Jan; closed again until 21 Apr |
| Outcome | From the $7.68 close to $24.92 on 31 Dec 2004 (+224%) |

**Would the strategy buy? No. It never sees the 7-week base.** Our detector takes as the base high the
highest swing high no close has yet cleared. For eBay on 6 January that was the **5 December 2001 high, $7.65**,
13 months earlier and just above the 7-week base. So it measures one long base from December 2001, and that
base fails VCP-03: 142 closes below the 200-day inside it, against a limit of 10. The 7-week base is part of it,
not a base of its own. Only the 6 January close of $7.68 cleared the old high, and by then there was no finished
base to break out of.

**Shown only the bars from August 2002**, without the old high, the strategy catches it on the book's day:

| | Counterfactual (bars from Aug 2002 only) |
|---|---|
| Setup | S8, flat base coiled: 20 sessions, 6.7% deep |
| Buy-stop | $7.47, resting from 31 Dec 2002 |
| Fill | 6 Jan 2003, the breakout day |
| Stop | $6.96 (under the last 5 sessions' low), 6.8% risk |

Two things would still stand in the way:

1. **The market gate.** It opened on 8 January, two sessions after the fill. The strategy places no buy-stop
   while the gate is closed.
2. **A single bar on 31 January 2003.** It opened at $7.78, traded down to $6.74 and closed at $7.91. A 13%
   intraday drop that closes near the high is very likely a bad print in the stored data. Taken at face
   value, it hits the $6.96 stop. Not fixed here; noted for the data-quality check.

**What came after.** With the full history, the strategy's first entries come in March 2003 (S8, a fill on light
volume, sold the next open, with the market gate closed anyway). Then come refused breakouts in June, October and
December 2003 (breakout volume short, or near misses). It never holds eBay through the 234% run.

**Why he took it.** *Inference from his principles.* It fits his "leaders that bottom early" type:

- eBay rose 90% from its own low while the market fell 38%.
- It held its gains through the market's final leg down.
- Its RS line made new highs before the price did.
- It formed a tight, quiet base just after the market's low.

Unlike Amazon, it needed no early entry. He bought a breakout from a finished base, with the market already
turning up.

**Takeaways.**

- **A structural blind spot: a short base under an older high.** The detector measures every base from the
  highest uncleared swing high, however old. A tight base forming just below a high from a year earlier is
  absorbed into one long base that a broken trend disqualifies. Minervini counts the recent base. A candidate
  change: let a base restart after a long enough interval (a "base on a base"), or anchor a flat base on its own
  recent high. Test it across all trades before adopting. eBay and his other "late emerging" leaders are the
  cases it would catch.
  - **Built (1.56) as a research switch, off:** `TREND_BREAK_RESETS` / `--vcp trend_break_resets=1`. A base with
    more closes below the 200-day than VCP-03 allows restarts at the highs after its last close below it.
  - **With it on**, S8 fills on 2003-01-06. The book eval set rises from 12 to 14 of 35 buy points: eBay and
    Microsoft's 1991 handle. It still holds 4 of 4 setups to avoid.
  - Optimise-stage variants are queued for both markets. The switch stays off unless they beat the baseline.
- **The RS-line lead again**: two cases of two. The study of RS-line highs ahead of price is worth doing.
- **The market gate's confirmation delay** cost this trade two sessions. Not a reason to drop it on one case.
- **Data:** the 31 Jan 2003 bar of EBAY looks wrong; check it before relying on that date.

---

## 3. Netflix (NFLX), October 2009 — a 27-week VCP months after the market low

*Book: Figure 7-5, chapter 7 (the same base as* Trade Like a Stock Market Wizard *fig. 10.31). Eval id
`tlsmw-10.31-nflx`, pinned and caught. Prices × 10 (the 2025 split).*

**What the book says.** Netflix bottomed in October 2008. The S&P 500 did not bottom until March 2009, and
while the index made its new low, Netflix rose 125%. That put it in Stage 2, with a soaring RS line and RS rank.
Then, as the market rallied, Netflix corrected 27% and went sideways for 27 weeks, long enough to wear out most
investors. Its RS line looked weak, and it was, for a while: the stock was digesting the rally. To a trained eye
it was a textbook VCP. Leaders do not all emerge at the market low; Netflix came out months after it. From the
VCP it rose more than 500% in 21 months, on eight straight quarters of rising sales and earnings growth averaging
45%.

```series
title: NFLX, 2004–2009 — the book's Figure 7-5 redrawn from stored data
from: 2004-01-02
to: 2009-11-30
tf: W
line: us:NFLX | NFLX (weekly) | log candles
line: us:NFLX@sma150 | 30-week (150-day) average
line: us:NFLX@sma200 | 40-week (200-day) average
line: us:NFLX / us:SPY | RS line (NFLX ÷ SPY) | pane2
band: 2009-04-13 2009-10-14 | the 27-week base
mark: 2008-10-27 | stock bottoms | below
mark: 2009-03-09 | market bottoms | below
mark: 2009-10-15 | emerges from the base
caption: Prices ×10 for the book's scale. The RS line soared into April 2009, then drifted while the index rallied and the stock built its base. It did not make a new high before the breakout, which is the point he makes.
```

```series
title: NFLX, April–December 2009 — the VCP, the stopped 3-C, the breakout and the strategy's exit, daily
from: 2009-03-16
to: 2010-01-29
tf: D
line: us:NFLX | NFLX | candles
line: us:NFLX@sma50 | 50-day average
line: us:NFLX@vol | Volume | pane2 bars
level: 0.718 | base high $7.18 | 2009-04-13 2009-10-15
level: 0.6899 | pivot $6.90 | 2009-09-15 2010-01-29 | pivot
level: 0.6291 | stop $6.29 | 2009-10-15 2010-01-29 | stop
mark: 2009-08-07 | 3-C cheat bought $6.43 | below
mark: 2009-09-01 | cheat stopped out | below
mark: 2009-10-15 | breakout, 2.3× volume | below
mark: 2009-10-23 | +2R: a third sold, stop to breakeven
mark: 2009-12-17 | first close below the 50-day: the rest sold
caption: Prices ×10. The strategy buys the breakout on Minervini's day. A third goes at +2R; the rest is sold the next session after the first close below the 50-day average, at $7.70. Four months later the stock was at $14; by July 2011, $43.
```

**What the data shows.**

| Item | Stored data |
|---|---|
| Stock low | $2.56 on 27 Oct 2008. To SPY's low on 9 Mar 2009: NFLX +115%, SPY −19% |
| The base (detector) | High $7.18 on 13 Apr 2009, low $5.18; 129 sessions (about 26 weeks; he says 27), 27.8% deep |
| Contractions | 9%, 27%, 18%, 8% — his footprint is "27W 27/7 3T" (three contractions to 7%); ours counts one more, early |
| Tight area and pivot | Final contraction 8.1%; volume 0.63× the 50-day (dried up); pivot $6.90, in the upper zone |
| Breakout | 15 Oct 2009: close $7.19, 4.3% over the pivot, on 2.3× volume, in the top of the day's range |
| Trend Template and market gate | Both pass on 15 Oct |
| RS line (NFLX / SPY) | 52-week highs in April 2009 only; it lagged through the base and the breakout |
| Outcome | From $6.90 to $43.54 on 13 Jul 2011 (+531%) |

**Would the strategy buy? Yes, on his day.** It is a pinned case in the eval set, caught as S1 on 15 Oct 2009:
buy at the pivot, $6.90, stop $6.29 (8.8%). It also took an earlier attempt: a 3-C in the middle third of the base
on 7 Aug 2009 (buy $6.43, stop $5.96), stopped out on 1 Sep. Then it re-entered on the breakout, as EN-04 allows
(two entries per base). That is his "it can take two or three tries".

**But it does not keep the winner.** The exits as they stand:

| Date | Rule | Price | R |
|---|---|---|---|
| 23 Oct 2009 | EX-04: a third sold at +2R; EX-03: stop to breakeven | $8.11 | +2.0 |
| 18 Dec 2009 | EX-06: the rest sold after the first close below the 50-day (17 Dec, $7.68 vs $7.87) | $7.70 | +1.3 |
| Trade | | | **+1.55R, about +14%** |

After that it never gets back in. The next bases fail the tight-area or contraction rules. From August 2010 the
setups are counted as the 4th to 6th base of the advance and skipped as late. The stock went on to $14 by April
2010 and $43 by July 2011.

**Why he took it, and held it.** *Inference from his stated principles.*

- Netflix was a leader that rested. It had already proven itself by doubling while the market made its final low.
- He explicitly does not need the RS line to lead here: the market is catching up with the stock (creator note
  §4, "Lead and rest").
- The base was a clean VCP with dry volume at the pivot, and the business was accelerating (by his account, 45%
  average earnings growth).
- He sells on his own rules, not on a first close below the 50-day. A strong stock's ordinary pullback, like
  Netflix's in December 2009, is exactly what he holds through.

**Takeaways.**

- **The entry rules work here; the exit is the leak.** This is the repo's own audit finding again: "winners are too
  small". A single close under the 50-day in the second month of a new advance ended a 500% trade at +14%. Two
  things could be tested as optimise variants, never tuned on this one chart:
  - a 50-day exit that needs volume, or two closes;
  - a longer trend exit once the trade is well in profit.
  The queued +3R breakeven and sell-half variants touch the same part of the trade.
- **The RS line lagged at this breakout.** A "new RS-line high before the breakout" rule would have refused his best
  trade here. So the RS-line study should treat it as evidence for a setup, never as a gate.
- **Late bases.** The 2010–2011 bases were skipped as the 4th to 6th base of the advance. That follows the rule he
  states (favour early bases), so it is not a miss.

---

## 4. Wal-Mart (WMT), 1981–82 — a leader breaking out through a bear market

*Book: Figure 7-8, chapter 7. Eval ids `ttlc-7.8-wmt-1` (a setup, refused by the plan) and `ttlc-7.8-wmt-2`
(caught as S1). Prices × 3 (the 2024 split); stored data is split-adjusted throughout. No SPY before 1993:
the index here is the long S&P 500 price series, and the market gate is a proxy on it, without breadth.*

**What the book says.** In 1981 Wal-Mart was a small, fast-growing company few knew; on some days it traded
40,000–50,000 shares. Through the bear market of the early 1980s it held up. Each time the indexes rallied
against the trend, it broke out of a base and tried to advance right off the market's lows. Leaders show this
strength cycle after cycle; such a divergence cannot hide. He marks two buy points, in autumn 1981 and spring
1982, before the August 1982 market bottom.

```series
title: WMT and the S&P 500, 1980–1982 — the book's Figure 7-8 redrawn from stored data
from: 1980-12-01
to: 1982-08-31
tf: D
line: us:WMT | WMT | log
line: us:WMT@sma200 | 200-day average
line: us:SP500_PRICE_LONG | S&P 500 | pane2
mark: 1981-09-29 | 3-C cheat | below
mark: 1981-11-02 | VCP breakout | below
mark: 1982-03-30 | VCP breakout | below
mark: 1982-08-12 | market bottom | below
caption: Prices ×3 for the book's scale. The S&P 500 (lower pane) fell 27% from November 1980 to August 1982. Wal-Mart rose 80% over the same span, above a rising 200-day almost throughout.
```

```series
title: WMT, 1980–1984 — the RS line through the bear market and the run after it, weekly
from: 1980-01-04
to: 1984-06-29
tf: W
line: us:WMT | WMT (weekly) | log
line: us:WMT / us:SP500_PRICE_LONG | RS line (WMT ÷ S&P 500) | pane2
band: 1980-11-28 1982-08-12 | S&P 500 bear market
caption: The RS line made 52-week highs again and again through 1981 and into early 1982 while the index fell. From the March 1982 buy point the stock rose 325% within 21 months; he says 360%.
```

**What the data shows.**

| Item | Stored data (book scale) |
|---|---|
| Held up | S&P 500 −27% from its Nov 1980 high to its 12 Aug 1982 low; WMT +80% over the same span |
| RS line (WMT / S&P 500) | 52-week highs repeatedly through 1981, the last on 4 Feb 1982 |
| Setups the detector finds | A complete VCP breaking out 25 Mar 1981; a 3-C in the middle third on 29 Sep 1981 (buy $0.287); a complete VCP breaking out 2 Nov 1981 (buy $0.312); a complete VCP breaking out 30 Mar 1982 (buy $0.343, stop $0.328) |
| Liquidity | $0.6–1.6m traded a day (50-day average), under the strategy's floor of $2.8m in 1981 dollars |
| Market gate (proxy) | Closed on every one of those dates: the index was below a falling 50-day average |
| Outcome | From the 30 Mar 1982 buy, $0.343 to $1.46 within 21 months (+325%) |

**Would the strategy buy? It sees every setup and buys none.** This case is the opposite of Amazon and eBay. The
pattern rules agree with him: the detector finds VCPs breaking out on 2 Nov 1981 and 30 Mar 1982, and a 3-C on
29 Sep 1981, at his marked buy points. Two portfolio rules refuse them:

1. **Liquidity.** Wal-Mart was a small company then, and its turnover was a third to a half of the floor. That is
   the book's own point: a future giant, unknown at the time.
2. **The market gate.** Every buy point came on a countertrend rally inside the bear market, with the index under
   a falling 50-day average. Breaking out *while the market falls* is the strength he describes. It is exactly
   what the gate is built to sit out.

**Why he took it.** *Inference from his principles.* The divergence was impossible to miss. The index made lower
lows; the stock made higher highs above a rising 200-day, and its RS line kept setting new highs. Each base
was tight and broke out on the market's rallies. He reads that as institutions buying a leader before the market
turns, and he buys it small and adds as it proves itself.

**Takeaways.**

- **Third case in four blocked by the market gate.** In each, the stock had already proven itself against a
  falling index. The pattern so far: the gate refuses the strongest stocks at the moment they are strongest.
  The bottoming pilot tested the broad version and failed. The narrower one — let a stock through the closed
  gate only when its RS line is at a new high — is the same RS-line study the earlier cases point to. It now
  has three cases behind it.
- **Liquidity is a floor we keep on purpose.** It protects fills and slippage. The book's examples include
  small companies that later became giants, and the floor will always refuse those early. That is a known
  cost, not a rule to tune on one case.
- **The detector is right about the setups here.** No pattern rule needs changing for this case.

---

## 5. Apple (AAPL), 2004 — three buy points through a Nasdaq correction

*Book: Figure 7-9, chapter 7. Eval ids `ttlc-7.9-aapl-1` and `ttlc-7.9-aapl-2`, both scored misses (see below).
Prices × 27.76 to the book's chart, which was itself split-adjusted in 2005. QQQ stands in for the Nasdaq
Composite, which is not stored.*

**What the book says.** Leaders of one cycle rarely lead the next, but some emerge late in a bull market and lead
in the next one. What to watch is how they hold up in a bear market or a sizeable correction. Apple broke out of
a base in March 2004, just as the market was topping. Each time the market made a new low, Apple made a higher
low and built another base. That gave three buy points, the last a textbook one right off the market's low in
August 2004. It rose 125% in six months.

```series
title: AAPL and the Nasdaq, Sep 2003 – Aug 2004 — the book's Figure 7-9 redrawn from stored data
from: 2003-09-02
to: 2004-09-15
tf: D
line: us:AAPL | AAPL | candles
line: us:AAPL@sma50 | 50-day average
line: us:QQQ | QQQ (Nasdaq-100) | pane2
level: 0.423 | 1st pivot $11.74 | 2004-02-01 2004-05-31 | pivot
level: 0.3885 | 1st stop $10.78 | 2004-02-27 2004-05-03 | stop
level: 0.514 | 2nd pivot $14.27 | 2004-05-10 2004-07-15 | pivot
level: 0.5893 | 3rd pivot $16.36 | 2004-07-20 2004-09-15 | pivot
mark: 2004-02-27 | 1st buy: S7 breakout, bought | below
mark: 2004-04-15 | +2R: a third sold
mark: 2004-04-30 | close under the 50-day: rest sold | below
mark: 2004-06-02 | 2nd: crossed on 0.90× volume, refused | below
mark: 2004-08-26 | 3rd: 2.3× volume but 5.0% past the pivot, refused | below
caption: Prices ×27.76 for the book's scale. QQQ (lower pane) topped in January and made lower lows into 12 August; Apple made higher lows and broke out three times. The market gate was closed from 10 March to 10 June and from 23 June to 24 September.
```

**What the data shows.**

| Buy | Date | What the strategy sees | Decision |
|---|---|---|---|
| 1st ("I'm buying here") | 27 Feb 2004 | S7 near miss (only VCP-10: volume 0.83× against 0.8×) out of the base from 15 Oct 2003; close $11.86 on 1.48× volume; Trend Template and gate pass | **Bought** at the 1 Mar open, $11.95, stop $10.78 (9.7%) |
| 2nd ("follow-up buy") | 2 Jun 2004 | S7 near miss (only VCP-08: tight area 4 sessions, needs 5); close $14.34 through the $14.27 pivot | Refused: volume 0.90× (needs 1.4×); gate closed |
| 3rd ("3rd buy") | 25–26 Aug 2004 | Base from 28 Jun not complete (VCP-06: final contraction 0.63× the reference, needs ≤ 0.6). 25 Aug closed 0.1% over the $16.36 high on 1.21×; 26 Aug closed $17.18 on 2.29× | Refused: 25 Aug light volume, 26 Aug 5.0% past the pivot (limit 5%); gate closed until 24 Sep |

The first trade, managed by the strategy's exits:

| Date | Rule | Price | R |
|---|---|---|---|
| 15 Apr 2004 | EX-04: a third sold at +2R; EX-03: stop to breakeven | $14.27 | +2.0 |
| 3 May 2004 | EX-06: rest sold after the first close under the 50-day (30 Apr, $12.78) | $12.89 | +0.8 |
| Trade | | | **about +1.2R** |

After that, the November 2004 – January 2005 bases are skipped: a flat base whose stop was 12.2% away, and a cheat
on the 4th base of the advance. From the first buy to February 2005 the stock rose from $11.95 to $45 (+277%).

**Why the eval set scores both cases as misses.** `ttlc-7.9-aapl-1`'s window opens on 1 Mar 2004. The strategy's
signal came on the 27 Feb close and filled at the 1 Mar open: it caught the book's first buy, two sessions before
the window as drawn. `ttlc-7.9-aapl-2` is a real miss (volume, gate).

**Why he took them.** *Inference from his principles.* Apple was the stock that would not go down. The Nasdaq made
lower lows in April–May and again in August; Apple made higher lows each time and built a new, tighter base
above the last. To him every new base after a market low is another entry into a leader that has already proven
itself, and the third, right off the market's August low, is the textbook one.

**Takeaways.**

- **The exit again.** Like Netflix, the strategy bought his first buy point and sold it on the first close under the
  50-day, at +1.2R, before a +277% run. The EX-06 variants queued on 2026-11-09 test exactly this.
- **Breakout-day rules, at the margin.** The second buy failed on volume (0.90× against 1.4×). The third split
  across two days: the light-volume day just cleared the pivot, and the volume day landed 5.0% past it. A
  breakout measured over two sessions, or a buy range a little wider for a gap off a tight base, would have
  taken it. Both are candidates only if the tally repeats them.
- **The gate, a fourth time.** It was closed for the second and third buys, the same pattern as Amazon, eBay and
  Wal-Mart: a stock making higher lows against an index making lower ones. That pattern is the RS-line study's Q2.
- **The eval set.** `ttlc-7.9-aapl-1`'s window could start on 27 Feb, the signal date; then it is caught. The window
  was read off the book's chart. Moving it is a correction of the record, not of the strategy.
