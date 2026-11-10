# Oliver Kell's cycle of price action — a strategy spec

*Status: **draft 0, 2026-11-10.** The phase definitions are fixed here before any backtest, then checked by eye
against five known leaders in stored data. No strategy code exists yet, and no backtest has been run.*

**In short**

- Kell, the 2020 US Investing Championship winner, trades the same leading growth stocks as Minervini, but reads each
  leader's trend as a repeating **cycle** around its 10- and 20-day exponential averages. He enters at several
  points in that cycle, not only at the pivot breakout.
- His edge, as he describes it, comes from three habits Minervini's coded strategy lacks:
  - **early entries with tight stops** (the wedge pop, the EMA crossback);
  - **selling into exhaustion** rather than waiting for a trend break;
  - **re-entering the same leader** each time the cycle restarts.
- This note fixes six phase definitions and draws them on TSLA 2020, NVDA 2023, SMCI 2023–24, BSE 2023–24 and
  Dixon 2023–24. The definitions catch the phases he names, with three problems to settle before coding:
  1. crossbacks fire too often;
  2. two closes under the 20-EMA whipsaws in volatile leaders;
  3. exhaustion must be a partial sale, never a full exit.
- Pass criteria for the first backtest are written below, before it runs.

## 1. The method, as Kell describes it

The source is his book *Victory in Stock Trading* and his recorded interviews. His terms are kept; our numeric
definitions are in section 2.

| Phase | What happens | What he does |
|---|---|---|
| **Reversal extension** | A sharp sell-off, stretched far below the short averages | Nothing yet: it marks that sellers may be exhausted |
| **Wedge pop** | Price breaks out of a falling wedge or tight range and back above the 10/20-day EMAs, on rising volume | First buy, small, with a stop under the pop day's low |
| **EMA crossback** | In the new uptrend, the first pullback to the rising 10- or 20-EMA, which holds | Adds, with a stop under the pullback low |
| **Base-n-break** | A tight sideways base above the averages, then a breakout on volume | Adds or buys: the classic pivot |
| **Exhaustion extension** | Price far above the 10-EMA, often with gaps and climactic volume | Sells part into strength |
| **Exhaustion gap / EMA break** | A gap that fails, or closes under the 20-EMA | Sells the rest; waits for the cycle to restart |

Three ideas carry the method.

**Position size comes from the stop.** A wedge pop's stop sits a few percent away, under the pop day's low. With a
fixed account risk, a 4% stop buys two and a half times the shares of a 10% stop. The early entry is a sizing
advantage as much as a price advantage.

**He builds a position.** The full size is reached by adding at the crossback and the base-n-break, each with
its own stop. Only a stock that keeps working gets the full bet.

**The leader is traded again and again.** After the exhaustion sale and the EMA break, a leader often
consolidates and restarts with another wedge pop. He buys it again. Minervini's book shows the same follow-up
buys; our Minervini strategy has them only as a research switch (`ADD_ON_NEW_BASE`, 1.58).

## 2. Definitions (fixed before any backtest)

Bars are daily. EMA10 and EMA20 are exponential averages of the close (`core/indicators.ema`). ATR is the 14-day
Wilder ATR. An **uptrend** day has EMA10 > EMA20, EMA20 above its value 5 sessions earlier, and the close above
the 50-day simple average.

| Code | Phase | Definition (draft 0) |
|---|---|---|
| RX | Reversal extension | Close at least `EXT_DOWN_ATR` = 2.5 ATR below EMA20 |
| WP | Wedge pop | Within `POP_LOOKBACK` = 30 sessions of an RX or of 5 straight closes under both EMAs, and not already in an uptrend: close above both EMAs and above the highest high of the prior `POP_HIGH_DAYS` = 5 sessions, on volume ≥ `POP_VOL` = 1.3× its 50-day average. Stop: the pop day's low |
| CB | EMA crossback | In an uptrend, yesterday's low came within `CROSS_TOUCH_ATR` = 0.5 ATR of EMA20 (or under it) and yesterday closed at or above EMA20; today closes above yesterday's high. Stop: yesterday's low |
| BB | Base-n-break | In an uptrend, the prior `BASE_MIN_DAYS` = 10 sessions fit within `BASE_MAX_WIDTH` = 15% high to low; today closes above that high, on volume ≥ `BREAK_VOL` = 1.4×. Stop: the base low, capped at the strategy's maximum risk |
| EX | Exhaustion extension | In an uptrend, close at least `EXH_ATR` = 3 ATR above EMA10, or a gap up of `GAP_ATR` = 1 ATR or more when the prior close was already 2 ATR above EMA10 |
| BK | EMA break | Two closes in a row under EMA20 after an uptrend |

These are first guesses at his words, not tuned values. Each becomes a named constant. Section 4 says which ones
the chart check showed to be wrong.

## 3. Checked against five leaders

Each chart marks the events the draft definitions find, collapsed to the first day of a run. These are
illustrations chosen after the fact (famous winners), not evidence that the method makes money.

### Tesla, 2020

```series
title: TSLA, March–December 2020 — the cycle phases as draft 0 finds them
from: 2020-02-03
to: 2020-12-31
tf: D
line: us:TSLA | TSLA | candles
line: us:TSLA@ema10 | 10-day EMA
line: us:TSLA@ema20 | 20-day EMA
line: us:TSLA@vol | Volume | pane2 bars
mark: 2020-03-16 | RX reversal extension | below
mark: 2020-05-05 | CB crossback | below
mark: 2020-07-02 | EX exhaustion | above
mark: 2020-08-12 | BB base-n-break | below
mark: 2020-08-31 | EX exhaustion (split day) | above
mark: 2020-09-09 | BK EMA break | above
mark: 2020-11-18 | WP wedge pop | below
mark: 2020-11-24 | EX exhaustion | above
caption: The cycle as he describes it, almost to the letter. The 31 August exhaustion mark sat at the top before a 34% fall. The 18 November wedge pop restarted the trend before the S&P 500 inclusion run. No wedge pop was found at the April turn. On 13 April, the day before the high-volume pop, the stock already met the draft's uptrend test (its 50-day average had fallen far enough to be under the close), and a wedge pop must come before an uptrend.
```

### SMCI, 2023–2024

```series
title: SMCI, 2023 – April 2024 — exhaustion fires early in a parabolic run
from: 2023-09-01
to: 2024-04-30
tf: D
line: us:SMCI | SMCI | candles
line: us:SMCI@ema10 | 10-day EMA
line: us:SMCI@ema20 | 20-day EMA
line: us:SMCI@vol | Volume | pane2 bars
mark: 2023-11-14 | WP wedge pop | below
mark: 2023-12-14 | WP wedge pop | below
mark: 2024-01-09 | CB crossback | below
mark: 2024-01-19 | EX exhaustion | above
mark: 2024-02-05 | EX | above
mark: 2024-02-14 | EX | above
mark: 2024-03-20 | BK EMA break | above
mark: 2024-04-19 | RX | below
caption: Exhaustion fired first on 19 January at $42. The stock went on to about $118 in March. Selling everything at the first exhaustion would have kept a fraction of the move; selling a part and holding the rest to the EMA break kept most of it. Exhaustion must be a partial sale.
```

### Dixon Technologies, 2023–2024

```series
title: DIXON, March 2023 – September 2024 — many crossbacks and breaks in a long trend
from: 2023-03-01
to: 2024-09-30
tf: D
line: india:DIXON.NS | DIXON | candles
line: india:DIXON.NS@ema10 | 10-day EMA
line: india:DIXON.NS@ema20 | 20-day EMA
line: india:DIXON.NS@vol | Volume | pane2 bars
mark: 2023-05-22 | BB | below
mark: 2023-06-15 | EX | above
mark: 2023-07-10 | BK | above
mark: 2023-08-03 | WP | below
mark: 2023-09-20 | BK | above
mark: 2023-09-26 | WP | below
mark: 2023-11-13 | BK | above
mark: 2024-01-19 | BK | above
mark: 2024-05-15 | BK | above
mark: 2024-07-19 | BK | above
mark: 2024-07-30 | WP | below
caption: The stock rose more than fourfold, and draft 0 called an EMA break eight times along the way. In a stock with a wide daily range, two closes under the 20-EMA is noise. Each break was followed by a wedge pop or crossback, so a re-entry rule recovers some of the loss, but each round trip costs.
```

Event lists for the other two:

- **NVDA, Oct 2022 – Aug 2023.**
  - Base-n-break on 23 Feb 2023, the earnings gap, at $23.66 (split-adjusted).
  - Six crossbacks from March to May.
  - Exhaustion on 25 May, the AI-guidance gap. The stock went on to about $49 by August, so here too exhaustion was a
    point to sell part, not all.
  - No wedge pop at the January 2023 turn: the pop day's volume was under 1.3× its 50-day average.
- **BSE, Mar 2023 – Mar 2024.**
  - Wedge pops in March and April 2023, then twelve base-n-breaks and crossbacks through a roughly fivefold rise.
  - Exhaustion on 3 July and 31 August 2023.
  - The first EMA break came only on 26 December. A clean leader gives the cycle no trouble.

## 4. What the check settled, and what changes before coding

| Issue | Seen in | Change for draft 1 |
|---|---|---|
| Crossbacks fire on every touch of the 20-EMA | NVDA (6 from March to May), BSE, Dixon | Only the first crossback after a wedge pop or base-n-break is an entry; later ones are adds only while the position is under full size |
| Two closes under EMA20 whipsaws in volatile stocks | Dixon (8 breaks), SMCI | An EMA break needs the close under EMA20 by at least 0.5 ATR, or a close under the most recent crossback's low. Compare both in the first backtest, each fixed now |
| Exhaustion as a full exit gives up the parabolic leg | SMCI, NVDA | Exhaustion sells a third, once per leg; the rest goes at the EMA break |
| Wedge pops are rare: the volume rule and the uptrend test both shut them out | NVDA (January: 1.08× volume on the turn day), TSLA (April: the uptrend test passed a day before the pop) | The uptrend test also requires EMA10 to have been above EMA20 for 5 sessions, so a fresh turn is still a pop. Keep 1.3× volume; report how many pops each volume threshold finds as a diagnostic, without tuning on it |

## 5. How a backtest would trade it (draft)

- **Candidates.** The same qualifying screen as Minervini's (`trend_template`), so the comparison isolates the
  entry and exit rules. A wedge pop can come before the Trend Template is met, because the 50- and 150-day averages
  lag. The first backtest therefore also tests "RS rating ≥ 70 and within 35% of the 52-week high" in place of the
  full template, as a fixed second variant.
- **Entries.** WP, the first CB and BB, each sized so that the stop risks the configured account risk. The total
  position is capped at 25% of equity. Adds only while earlier entries in the same stock are in profit.
- **Exits.** The stop of each entry; a third sold at the first EX of a leg; the rest at the BK.
- **Market.** The strategies' shared market gate. Kell watches the leaders and growth ETFs rather than the index.
  The small-cap trend gate (Minervini 1.59, `MKT_SEGMENT_MOM_DAYS`) is the nearest coded idea and runs as a variant.
- **Re-entry.** A stock exited at a BK is eligible again at its next WP or BB.

## 6. Pass criteria for the first backtest (decided now)

Optimise stage only (2013–2021), both markets, with the draft-1 definitions and nothing tuned after the first run:

1. **Expectancy:** at least +0.30R per trade in India and above zero in the US, net of costs.
2. **Better than Minervini on the same screen:** a higher CAGR than the Minervini strategy's best like-for-like run
   in each market (today India 8.26%, US 3.08%, with room after +3R), at a maximum drawdown no more than 5 points
   deeper.
3. **Not one stock's result:** with the best 5% of trades removed, expectancy stays above zero in India.

If all three pass, the strategy gets one verify run (2022 on) as its first version, with the same criteria. If any
fails, the result goes in this note as a failure. The definitions are then revised once, as draft 2, with the reason
stated, and draft 2 gets its own run.

## 7. Open questions

- Should the cycle's own EMAs be weekly for slower stocks (India large caps)? Not in the first version.
- He trades mostly US growth stocks. Whether a 10/20-EMA cycle suits India's small caps, with their wider daily
  ranges, is exactly what the Dixon chart puts in doubt.
- His championship result is a concentrated, high-turnover, small-account record from 2020, an unusual year for
  growth stocks. The spec takes his method, not his returns.

## 8. Results — draft 1 (optimise stage, 2013–2021, in-sample)

Built as strategy `kell_cycle` v1.0 (spec id `v1.0-a4345dde`), with the section-4 changes and the section-5
trading rules. Six optimise-stage runs are queued: both markets × {default break (a), break (b) `BREAK_MODE=2`,
loose screen `SCREEN_LOOSE=1`} (queue #1412–#1417). No verify run is made until all three section-6 criteria
pass and the owner says so.

### Diagnostics recorded before the runs

**Wedge-pop volume** (diagnostic only; the rule keeps 1.3×). Pops found over 2013–2021, on every bar and on the
bars that also passed the Trend Template:

| Market | Symbols | 1.0× | 1.3× (used) | 1.6× |
|---|---:|---:|---:|---:|
| India, all bars | 2,309 | 45,198 | 39,931 | 35,224 |
| India, Trend Template days | | 4,511 | 3,996 | 3,475 |
| US, all bars | 4,998 | 106,127 | 77,054 | 55,921 |
| US, Trend Template days | | 10,602 | 7,681 | 5,332 |

Raising the bar from 1.0× to 1.3× drops about 11% of India's pops but 28% of the US's. India's pops come mostly
on heavy volume anyway.

**The break rule on the check charts.** With break (a), Tesla 2020 keeps the spec's marks. The WP of 14 April is
newly found once the uptrend test needs EMA10 > EMA20, and BKs fire on 11 August and 8 September. On Dixon,
March 2023 to September 2024, break (a) calls 9 BKs (draft 0 called 8) and break (b) calls 5. So break (b) is
the variant that actually addresses the whipsaw the Dixon check found.

### Backtest results

Pending: the runs are queued behind the rest of the backtest lane. Each run is reported here with CAGR,
Sharpe, max drawdown, trade count and expectancy in R, plus each criterion's pass or fail, including failures.
