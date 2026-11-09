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
| Market gate closed (index below a rising 50-day) | 1 | AMZN 2002 |
| Trend Template on the signal day (G1–G8) | 1 | AMZN 2002 (G4) |
| 3-C / cheat shelf: width (`CHEAT_SHELF_PCT`) | 1 | AMZN 2002 |
| 3-C / cheat shelf: volume (`CHEAT_DRYUP`, `CHEAT_VOL_CONTRACT`) | 1 | AMZN 2002 |
| Stop more than `MAX_STOP_PCT` below the fill | 1 | AMZN 2002 |
| No RS-line rule (the book's tip-off, absent from the strategy) | 1 | AMZN 2002 |

| Case | Book's entry | Strategy buys? | Deciding rules |
|---|---|---|---|
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
