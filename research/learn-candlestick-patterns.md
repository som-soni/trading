# Candlestick patterns — a field guide

**In short**

- A candle shows one session in four prices: open, high, low and close. Its body and wicks show which side was in control and where it gave up.
- A candle means something only at a level, such as a prior low, a rising moving average or a pivot, and read together with volume.
- The trend matters more than any single candle. One bearish candle in a strong uptrend is usually just a pause.
- On their own, candle patterns predict very little. Academic tests and our own event study on two markets both find almost no edge.
- Use candles to describe what happened and to place stops, not as a reason to buy or sell.

This guide covers single bars and short groups of bars. Its companion, [learn-chart-patterns](learn-chart-patterns.md), covers the shapes that several weeks of bars make.

---

## 1. Anatomy of a candle

On 31 May 2024 Microsoft opened at $416.75, which was also the day's high. It then fell to $404.51 during the session. By the close, buyers had pushed it back to $415.13. Volume was about 2.5 times its 50-day average.

That one day tells a story. Sellers were in control for most of the session. Then buyers took back almost the whole drop. The close was near the top of the day's range, on heavy volume.

A candle draws this in one picture. The **body** spans the open and the close. The **wicks** are the thin lines above and below the body; they reach the high and the low. The **range** is the distance from the low to the high.

```pattern
anatomy
```

Three questions tell you most of what one candle can say:

1. **How big is the body compared with the range?** A large body means one side controlled the session. A tiny body means neither side won.
2. **Where in the range did it close?** A close in the top third means buyers were in control at the end of the day. A close in the bottom third means sellers were.
3. **Which wick is long?** A long wick marks prices the stock reached during the session but could not hold. A long lower wick means buyers stepped in on the dip and absorbed the selling.

Microsoft's candle had a small body, a close in the top third and a long lower wick. That is a hammer, described in section 3.

To make these questions exact, you can measure them. Common definitions:

| Measure | Definition | Common threshold |
|---|---|---|
| Body % | \|close − open\| / (high − low) | doji when ≤ 10% |
| Close location | (close − low) / (high − low) | top ≥ 0.66, bottom ≤ 0.34 |
| Wick ratio | wick length / body length | "long" when ≥ 2× the body |
| Gap % | open vs the prior close | a gap when beyond ±0.3% |
| Volume ratio | volume / 50-day average volume | notable above 1.2 or below 0.8 |

**Volume matters as much as the shape.** A reversal candle on twice the average volume shows many traders acting. The same shape on 0.6 times average volume is noise. Read every pattern below together with its volume.

---

## 2. Context first, pattern second

Here are two hammers, both in uptrends, both at the 50-day moving average and both on heavy volume.

```series
title: Microsoft — a hammer at the 50-day average that held, May 2024
from: 2024-03-15
to: 2024-07-31
tf: D
line: us:MSFT | Microsoft
line: us:MSFT@sma50 | 50-day average
line: us:MSFT@vol | Volume | pane2 bars
mark: 2024-05-31 | hammer at the 50-day, 2.5× volume
caption: The stock dipped below its 50-day average during the day and closed back near it. Ten sessions later it was 6.6% higher.
```

```series
title: Amazon — a hammer at the 50-day average that failed, September 2020
from: 2020-07-01
to: 2020-10-31
tf: D
line: us:AMZN | Amazon (split-adjusted)
line: us:AMZN@sma50 | 50-day average
line: us:AMZN@vol | Volume | pane2 bars
mark: 2020-09-04 | hammer, 1.8× volume
caption: The hammer came two days into a sharp drop from a record high. Ten sessions later the stock was 10.1% lower, well below the hammer's low.
```

The two candles look alike. The difference was the setting. Microsoft was pausing in an orderly way after a long rise. Amazon had just started a fast decline from a steep run, and one good afternoon did not stop it.

The same hammer can mean three different things:

- at the 50-day average after a three-week pullback in an uptrend, the uptrend *may be resuming*, so it is worth attention;
- in the middle of a range, away from any level, it means nothing;
- after a 40% collapse in a downtrend, it is usually just the first bounce, and sellers push the price down again.

Rules of thumb that hold up on real charts:

1. **Only read reversal candles at a level.** A level is a prior low, a moving average the stock has bounced from before, a pattern pivot or the edge of a gap. At a level, buyers and sellers are both active, and the candle shows which side won there. Away from a level, there is no contest to read.
2. **The trend matters more than the candle.** A bearish candle in a strong uptrend is usually just a pause. Do not bet against an uptrend because of one shooting star. At most, tighten your stop.
3. **A longer timeframe carries more meaning.** A weekly hammer at support counts for more than five daily candles.
4. **Wait for the confirming close** when the candle is your only reason to act. A hammer is only "confirmed" when the next bar closes above its body.

---

## 3. Single-candle patterns

### Doji — neither side wins

The body is about 10% of the range or less: the open and the close are nearly equal.

```pattern
doji
```

After a long advance, a doji on high volume is a warning. The buyers who drove the move met as much selling as buying for the first time. In a quiet range, a doji says nothing at all.

Variants:

- **Gravestone**: a long upper wick and a close near the low. A rally during the day failed. It is bearish at highs.
- **Dragonfly**: a long lower wick and a close near the high. A sell-off during the day was bought back. It is bullish at support.
- **Spinning top**: a small body with wicks on both sides. It shows indecision, a slightly weaker message than a doji.

### Hammer — a sell-off that was bought back

Microsoft on 31 May 2024 was a hammer. Sellers pushed the price down during the session. Buyers then bought it almost all the way back up.

The rule: a long lower wick, at least twice the body, and a close in the top third of the range. It must come **after a decline or pullback**.

```pattern
hammer
```

It is bullish at support. The low of the hammer is the natural place for a stop. If the price trades back below that low, the buying that made the hammer has failed. That is what happened to Amazon in September 2020.

The same shape after an *advance* is called a **hanging man**. It is a warning, not a sell signal, and much weaker evidence than a hammer.

### Shooting star — a rally that failed

This is the mirror image of the hammer. It has a long upper wick, at least twice the body, and a close in the bottom third, after an advance. Buyers pushed the price to new highs during the day; then sellers drove it back down.

It means something at resistance or after a fast, steep run-up. Inside a base it is an ordinary candle. The **inverted hammer** is the same shape after a decline. It is mildly bullish and needs the next bar to confirm it.

### Marubozu — one side in full control

The body is the whole range, or nearly so, with almost no wicks. A green marubozu through a pivot on heavy volume is exactly the breakout bar you want. A red one through support is a sign of distribution: large holders selling.

### NR7 — a quiet bar before a move

It is not a classical candlestick. An NR7 is the bar with the narrowest range of the last seven bars. Volatility tends to shrink before it expands.

A cluster of NR7 or inside bars near a pivot is the daily-chart version of a volatility contraction pattern (VCP). In a VCP each pullback in a base is smaller than the last; see [learn-vcp](learn-vcp.md). The direction of the next move comes from which way the price breaks, not from the NR7 itself.

---

## 4. Two-candle patterns

### Bullish engulfing

A down candle, then an up candle. The up candle's body opens at or below the prior close and closes at or above the prior open. The second session wipes out the whole first session and then reverses it.

```pattern
bullish-engulfing
```

It is strongest at support after a pullback, on rising volume. Put the stop below the engulfing bar's low.

**Bearish engulfing** is the mirror image, at highs. Both are among the few candle patterns with some modest support in published statistics. Both still fail often when they go against the main trend.

### Harami / inside bar

The second bar's range sits entirely inside the first bar's range. This is an **inside bar**: the range is shrinking, and the market is pausing. Like the NR7, it does not point up or down.

Trade the break of the inside bar's range, in the direction of the trend, rather than the bar itself. The **outside bar** is the opposite: its range covers the prior bar's range on both sides. The range is expanding, and where it closes in its range shows which side won.

### Piercing line / dark cloud cover

These are weaker versions of the engulfing pair. The second body takes back more than half of the first body but does not engulf it.

- Piercing line (bullish, at lows): a gap down, then a close above the midpoint of the prior red body.
- Dark cloud cover (bearish, at highs): a gap up, then a close below the midpoint of the prior green body.

Read them the same way as an engulfing pattern, with less confidence.

### Tweezers

Two bars in a row with nearly equal lows (tweezer bottom) or equal highs (tweezer top). The same price level held twice in a row. They are mostly useful as evidence *that the level matters*, not as a pattern on their own.

---

## 5. Three-candle patterns

### Morning star / evening star

The classic reversal in three steps. A morning star forms at a low:

- first, a strong red bar (sellers in control);
- then a small-bodied bar, the "star", that gaps or drifts lower (the selling is running out);
- last, a strong green bar that closes well into the first bar's body (buyers take over).

```pattern
morning-star
```

The evening star is the mirror image, at highs. A looser version is the **3-bar reversal**: a close down, then a close back up through the first bar's open. The bearish version is the mirror.

### Three white soldiers / three black crows

Three full-bodied candles in a row in the same direction, each closing near its high (or, for crows, its low). After a long decline, three white soldiers mark a real change in how the stock trades.

*Late* in an advance, three ever-larger white soldiers on rising volume start to look like a climax. A climax is a final burst of buying before a top. See the climax-run section in [learn-chart-patterns](learn-chart-patterns.md).

---

## 6. Quick reference

| Pattern | Bars | Bias | Where it means something | Invalidation |
|---|---|---|---|---|
| Doji | 1 | neutral | after a one-way move | — (a warning, not a trade) |
| Hammer | 1 | bullish | at support after a decline | close below its low |
| Hanging man | 1 | mildly bearish | after an advance | close above its high |
| Shooting star | 1 | bearish | at resistance after an advance | close above its high |
| Inverted hammer | 1 | mildly bullish | after a decline, needs confirmation | close below its low |
| Marubozu | 1 | with its color | through a level, on volume | retrace through the level |
| NR7 / inside bar | 1–2 | neutral (contraction) | near a pivot | — (trade the break) |
| Bullish engulfing | 2 | bullish | at support, rising volume | close below pattern low |
| Bearish engulfing | 2 | bearish | at highs/resistance | close above pattern high |
| Piercing line | 2 | bullish | at lows | close below pattern low |
| Dark cloud cover | 2 | bearish | at highs | close above pattern high |
| Morning star | 3 | bullish | at lows, volume on bar 3 | close below star's low |
| Evening star | 3 | bearish | at highs | close above star's high |
| Three white soldiers | 3 | bullish | after a decline/base | — context-dependent |
| Three black crows | 3 | bearish | after an advance | — context-dependent |

---

## 7. Where candles help in a swing trade

Candles are best used as a description of how the last few bars behaved at the levels that matter. Most swing methods enter on price levels and chart structure, such as a break through a pivot. They do not buy "because yesterday was a hammer". Candles help in three places.

**1. Judging the entry day.** On the day the price moves through your entry trigger, look at the candle. A full-bodied close near the top of the range, on above-average volume, is what a healthy breakout looks like. A shooting-star close back under the pivot is the first sign of a failed breakout. See [learn-strat-failed-breakouts](learn-strat-failed-breakouts.md).

**2. Placing the stop.** Reversal candles mark natural points where the idea is proven wrong: the hammer's low, the engulfing bar's low. These stops are usually tighter, and more tied to what the price actually did, than a fixed percentage.

**3. Reading a pullback.** When you buy a dip in an uptrend, the candles show what kind of dip it is. An orderly pullback has small-range candles (inside bars, NR7s, dojis) with lower wicks near the rising 50-day average. Distribution has wide red marubozus on rising volume. The pullback can be the same depth with the opposite meaning. See [learn-strat-pullback-support](learn-strat-pullback-support.md).

---

## 8. What the evidence says

**Published research.** Academic tests of candlestick rules on daily stock data find **no reliable predictive value on their own** after costs. Examples are Marshall, Young and Rose (2006) on the Dow stocks, and Horton (2009). Fock and colleagues found the same on intraday data.

**Practitioner statistics.** Thomas Bulkowski's large pattern catalogues find that single candle patterns are barely better than a coin flip. They improve only when filtered by trend and by confirmation. Those are the context rules in section 2.

**An event study on stored data.** We counted how stocks did in the ten sessions after each pattern. We compared that with ordinary days in the same setting.

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to October 2026. Liquid days only: close at least ₹20 or $5, and 50-day average turnover at least ₹5 crore or $5 million. Uptrend: close above the 200-day average, 50-day above the 200-day, and the 50-day higher than ten sessions earlier. At the 50-day: the low within 1% above the average or below it, and the close no more than 1% below it. Hammer: lower wick at least twice the body, close in the top third, close below the close five sessions earlier. Bullish engulfing: as defined in section 4. Shooting star: the mirror of the hammer, after a rise. Outcome: the close ten sessions later. Caveats: today's lists only (survivorship bias), no costs, overlapping windows.

| Ten sessions later | India: share higher | India: median | US: share higher | US: median |
|---|---|---|---|---|
| Every liquid day | 50.0% | 0.00% | 52.6% | +0.36% |
| Uptrend, low at the 50-day | 50.6% | +0.09% | 53.3% | +0.38% |
| Hammer at the 50-day, in an uptrend | 51.4% | +0.18% | 52.2% | +0.26% |
| The same, on 1.5× volume or more | 51.0% | +0.18% | 51.2% | +0.14% |
| Bullish engulfing at the 50-day, in an uptrend | 48.7% | −0.19% | 53.0% | +0.37% |
| Uptrend, any day | 50.8% | +0.13% | 52.6% | +0.32% |
| Shooting star in an uptrend | 49.3% | −0.11% | 52.5% | +0.30% |

| Number of events | India | US |
|---|---|---|
| Hammers at the 50-day, in an uptrend | 6,715 | 32,522 |
| …on 1.5× volume or more | 635 | 3,823 |
| Bullish engulfing at the 50-day, in an uptrend | 7,300 | 28,836 |
| Shooting stars in an uptrend | 50,351 | 119,412 |

What this shows:

- **The bullish patterns added almost nothing.** A hammer or engulfing bar at the 50-day did about as well as any day the stock touched its 50-day in an uptrend.
- **Heavy volume did not help on its own.** In the US, hammers on high volume did slightly worse than ordinary ones.
- **A shooting star did not end uptrends.** Ten sessions later, stocks were higher about as often as on any uptrend day. Do not sell a strong stock because of one bearish candle.

**Why candles are fragile.** Candle shapes depend on how the trading session works. A stock that gaps often produces "patterns" all the time; this happens around earnings, with ADRs (foreign shares listed in the US) and in thinly traded names. A market that trades 24 hours a day produces different candles from one with an exchange session. The same price path, cut into bars differently, gives different candles.

**Limits.** Our study tests the patterns alone, with fixed definitions and a fixed holding time. It does not test candles used for stop placement or combined with a breakout, which is how most traders use them. Treat candles as a *description* of what happened, not a *prediction*.

## Further reading

- Steve Nison, *Japanese Candlestick Charting Techniques* — the book that introduced candles to Western traders. Read it for the vocabulary, not for win rates.
- Thomas Bulkowski, *Encyclopedia of Candlestick Charts* — statistics for each pattern. It is the most honest source on how weak single patterns are.
- Ben Marshall, Martin Young and Lawrence Rose, "Candlestick technical trading strategies: Can they create value for investors?", *Journal of Banking & Finance* (2006).
- [learn-chart-patterns](learn-chart-patterns.md), [learn-strat-failed-breakouts](learn-strat-failed-breakouts.md), [learn-strat-pullback-support](learn-strat-pullback-support.md).
