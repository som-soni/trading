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
| Market gate closed (index below a rising 50-day, 5 sessions to confirm) | 2 | AMZN 2002; EBAY 2003 (by two sessions) |
| Base anchored on an older, higher high (`vcp_spec` base high) | 1 | EBAY 2003 |
| Trend Template on the signal day (G1–G8) | 1 | AMZN 2002 (G4) |
| 3-C / cheat shelf: width (`CHEAT_SHELF_PCT`) | 1 | AMZN 2002 |
| 3-C / cheat shelf: volume (`CHEAT_DRYUP`, `CHEAT_VOL_CONTRACT`) | 1 | AMZN 2002 |
| Stop more than `MAX_STOP_PCT` below the fill | 1 | AMZN 2002 |
| No RS-line rule (the book's tip-off, absent from the strategy) | 2 | AMZN 2002, EBAY 2003 |

| Case | Book's entry | Strategy buys? | Deciding rules |
|---|---|---|---|
| [AMZN, Oct 2002](#1-amazoncom-amzn-october-2002--3-c-out-of-a-22-week-base) | 3-C, 10 Oct 2002 | No, and no later setup through 2003 | market gate, G4, shelf width and volume, stop 12.4% |
| [EBAY, Jan 2003](#2-ebay-ebay-january-2003--a-7-week-base-after-the-market-low) | 7-week base, 6 Jan 2003 | No: it never sees the 7-week base. Shown only recent bars, it buys the same day (S8) | base anchored on the Dec 2001 high; market gate closed until 8 Jan |

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
