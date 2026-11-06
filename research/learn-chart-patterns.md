# Chart patterns — a field guide

**In short**

- A chart pattern is a pause in a trend that shows how buyers and sellers are trading. The bullish ones all tell the same story: selling gets smaller until a little buying can lift the price through the old high.
- A pattern is only complete when the price breaks its trigger level, the pivot. How it breaks (volume, close, follow-through) says more than the shape.
- Every pattern has a level that proves it wrong: the handle low, the second bottom, the flag low. That is where the stop goes.
- Context decides meaning. The same shape after a rise is a pause; after a fall it is usually just a bounce.
- In broad data the shapes alone are a weak edge. Use them to place triggers and stops, and get the edge from the stock, the market and the exits.

This guide covers the shapes that several weeks of bars make. Its companion, [Candlestick patterns](learn-candlestick-patterns.md), covers single bars. For how traders turn each pattern into a full trade, see the strategy guides linked in each section.

---

## 1. What a pattern is — and is not

In August 2023 NVIDIA peaked at 50.27 (split-adjusted). It then fell 22%, to 39.23 at the end of October. By late November it was back at the old high. It dipped once more, by 11%, and then went quiet. On 8 January 2024 it closed above 50.55 on 1.58 times its average volume, and it kept going.

```series
title: NVIDIA — a cup with handle, and the breakout in January 2024
from: 2023-07-01
to: 2024-02-15
tf: D
line: us:NVDA | NVIDIA, daily candles (split-adjusted) | candles
line: us:NVDA@sma50 | 50-day average
line: us:NVDA@vol | Volume | pane2 bars
level: 50.55 | Pivot 50.55 | 2023-08-24 2024-02-15 | pivot
level: 45.01 | Handle low 45.01 | 2023-12-04 2024-02-15 | stop
mark: 2023-08-24 | left rim
mark: 2023-10-31 | cup low | below
mark: 2023-11-20 | right rim
mark: 2023-12-04 | handle | below
mark: 2024-01-08 | breakout
caption: A rounded fall and recovery (the cup), a smaller dip near the top (the handle), then a close above the pivot of 50.55 on 1.58 times average volume. The handle low, 45.01, is where the pattern would have been proved wrong.
```

That shape is a **cup with handle**. It is a story about supply (shares for sale) and demand (buyers). After an advance, some holders take profits, and the price falls until buyers soak up the shares being sold. If large investors keep buying (accumulation), each wave of selling is smaller than the last. Eventually few sellers are left, and a small amount of buying pushes the price through the old high.

That is the whole theory. Every bullish continuation pattern below is a variation of it.

Three consequences follow:

1. **Context decides meaning.** After an advance, a shape is a *continuation* pattern: a pause before the uptrend carries on. The same shape after a decline is a *bear rally*: a short bounce inside a downtrend. So look for these shapes only in stocks near their highs with a rising 200-day average, after a real prior advance.
2. **A pattern is only complete at its trigger.** Until the price breaks the pivot, a cup with handle is just a stock that went down and came back up. Most of the information is in *how* the breakout happens: the volume, where the bar closes in its range, and whether the price keeps going.
3. **Every pattern needs an invalidation level.** This is the low that, if broken, proves the story wrong: the handle low, the second bottom, the flag low. That level is where the stop belongs. If the stop is too far away to size a position sensibly, the pattern is not a trade.

### The shared anatomy

Each pattern below is described the same way: its key points, the context it needs, its shape, its volume, then its trigger, invalidation and target.

For targets, the classical rule is the **measured move**. You add the pattern's height, or the height of the prior advance (the "pole"), to the pivot. Treat it as a first estimate, not a promise. Cap it at the real resistance above, such as an old high where sellers may be waiting (see [Supply and demand](learn-supply-demand.md)).

---

## 2. Bullish continuation patterns

### Cup with handle

The classic base described by William O'Neil, and NVIDIA's shape above. First an advance. Then a rounded correction, not a sharp V. Then a recovery to the old high. Then a small, quiet pullback, the handle, while the last sellers near the rim (the old high) hand their shares to new buyers.

```pattern
cup-with-handle
```

What makes a *good* cup:

- a rounded bottom — the stock spends time down there, because nervous holders need time to sell and leave;
- a handle in the **upper half** of the cup that drifts down on **below-average volume**;
- a rim at or near the 52-week high.

Red flags: V-shaped cups, handles that form in the lower half or drop fast, and wide, choppy price swings throughout.

Trigger: a close above the handle high on rising volume. Invalidation: the handle low. Measured move: the cup's depth. A **cup without a handle** is the same cup with the price still at the rim; the pivot is the rim itself. For the full trade, see [CAN SLIM breakouts](learn-strat-canslim-breakout.md).

### Double bottom

UnitedHealth fell to 216.84 in April 2019 (closing prices). It rallied to 266.65 in July. In late September it fell back to 215.26, just under the first low, and recovered at once. On 15 November it closed at 269.40, above the July high of 268.69. Volume that day was 2.3 times average.

Sixty sessions later it was 12.2% higher.

```series
title: UnitedHealth — a double bottom with an undercut, 2019
from: 2019-02-01
to: 2020-02-14
tf: D
line: us:UNH | UnitedHealth, daily candles | candles
line: us:UNH@sma200 | 200-day average
line: us:UNH@vol | Volume | pane2 bars
level: 268.69 | Pivot: July high | 2019-07-17 2020-01-31 | pivot
level: 215.26 | Second low | 2019-09-27 2020-01-31 | stop
mark: 2019-04-17 | first low | below
mark: 2019-07-17 | middle peak
mark: 2019-09-27 | second low | below
mark: 2019-11-15 | breakout
caption: The second low dipped just below the first and turned up at once. The breakout came above the middle peak.
```

That is a **double bottom**: a "W". The price sells off to the same area twice; the second time, no new sellers appear. Ideally the second low dips slightly *below* the first and then recovers at once.

That dip is a shakeout. It triggers the last stop orders sitting under the first low. Once those shares are sold, the selling is done.

```pattern
double-bottom
```

Trigger: the middle peak between the two lows. Invalidation: the second low. Measured move: the middle peak minus the low. The mirror image at highs, the **double top**, is a warning, covered in section 3.

Context still decides. Amazon made a similar W in early 2022. Its second low of 136.01 undercut the first, and on 21 March it closed above the middle peak at 161.49. But it was below a falling 200-day average, and the breakout came on light volume (0.8 times average). Sixty sessions later it was 33.3% lower.

```series
title: Amazon — the same W in the wrong place, 2022
from: 2021-11-01
to: 2022-06-30
tf: D
line: us:AMZN | Amazon, daily candles (split-adjusted) | candles
line: us:AMZN@sma200 | 200-day average
line: us:AMZN@vol | Volume | pane2 bars
level: 161.41 | Middle peak | 2022-02-08 2022-06-30 | pivot
mark: 2022-02-03 | first low | below
mark: 2022-02-08 | middle peak
mark: 2022-03-08 | second low | below
mark: 2022-03-21 | breakout, 0.8× volume
caption: The shape matches UnitedHealth's, but the setting does not. The whole W formed below a falling 200-day average, and the breakout came on less than average volume. The rally stalled near the 200-day, and on 6 April the price closed back below the middle peak.
```

### Flat base / Darvas box

The strongest stocks barely pull back at all. After an advance, the price moves sideways in a tight box, usually no more than 15% deep. The stock works off its gain through time spent going sideways, rather than through a fall in price.

Boxes stack: a breakout from one box becomes the floor of the next. That was Nicolas Darvas's original observation.

```pattern
flat-base
```

Trigger: the box high. Invalidation: the box low. Measured move: a tight box's own height is too small to be a useful target, so some traders add the **prior advance** instead. For the full trade, see [Darvas boxes](learn-strat-darvas.md).

Titan shows one. From early May to late June 2021 it rose about 24%. It then traded sideways for six weeks, between ₹1,662.50 and ₹1,792.95, a box less than 8% deep. On 3 August it closed at ₹1,840.20 on four times its average volume. By mid-October it was at ₹2,588.80, 44% above the box.

```series
title: Titan — a flat base after an advance, 2021
from: 2021-04-01
to: 2021-09-15
tf: D
line: india:TITAN.NS | Titan, daily candles | candles
line: india:TITAN.NS@vol | Volume | pane2 bars
zone: 1662.5 1792.95 | Box ₹1,662–1,793 | 2021-06-22 2021-08-02
mark: 2021-05-04 | advance starts | below
mark: 2021-08-03 | breakout
caption: An advance, then six weeks sideways in a shallow box near the high instead of a deep pullback. The breakout closed clear of the box high on four times the usual volume.
```

### Bull flag

A near-vertical advance (the pole), then a short, shallow drift downward (the flag). In the textbook case the flag gives back less than half the pole, over a few weeks.

The rare, famous variant is the **high tight flag**: a gain of 80% or more, of which no more than about 25% is given back. Almost only a leading stock that big investors are buying heavily can produce it.

```pattern
bull-flag
```

Trigger: the pole high. Invalidation: the flag low. Measured move: the pole height. The old saying is that "flags fly at half mast": the flag sits halfway up, and the move after it repeats the pole. For the full trade, see [Flags, pennants and high tight flags](learn-strat-flags.md).

Dixon Technologies made a high tight flag in 2019. In eight weeks, to 10 October, it rose from ₹312 to ₹646.40 (split-adjusted). It then drifted down for four weeks, to a low of ₹532.51, giving back 18%. On 14 November it closed at ₹652.63, above the pole high, on 19 times its average volume. By early February 2020 it was at ₹952.71.

```series
title: Dixon Technologies — a high tight flag, 2019
from: 2019-07-15
to: 2020-02-14
tf: D
line: india:DIXON.NS | Dixon Technologies, daily candles (split-adjusted) | candles
line: india:DIXON.NS@vol | Volume | pane2 bars
level: 646.4 | Pole high | 2019-10-10 2020-01-15 | pivot
level: 532.51 | Flag low | 2019-11-07 2019-12-31 | stop
mark: 2019-08-13 | pole starts | below
mark: 2019-10-10 | pole high
mark: 2019-11-07 | flag low | below
mark: 2019-11-14 | breakout
caption: The pole more than doubled the price; the flag gave back less than a fifth of it, in a quiet drift. The breakout above the pole high came on the heaviest volume on the chart, and the flag low was the stop.
```

### Ascending triangle

A flat resistance line that the price tests again and again from below, while the lows keep **rising**. The price gets squeezed into the corner. Sellers wait at one fixed price. Buyers are willing to pay more on every dip.

```pattern
ascending-triangle
```

Trigger: the resistance line. Invalidation: the last rising low. Measured move: the triangle's height at its left edge. Descending and symmetrical triangles also exist in the classical catalogue. The ascending form has the clearest bullish logic.

Saia shows the shape. Between February and April 2023 it reached about $298–306 three times and turned back each time. Its lows meanwhile kept rising, from $180 in October 2022 to $245 in late April. On 14 June it closed at $313.35, through the top line, on 1.7 times its average volume. By 1 September it was at $438.58.

```series
title: Saia — an ascending triangle, 2022–23
from: 2022-09-01
to: 2023-07-31
tf: D
line: us:SAIA | Saia, daily candles | candles
line: us:SAIA@vol | Volume | pane2 bars
level: 306.4 | Resistance | 2023-02-02 2023-07-31 | pivot
trend: 2022-10-21 180.17 2023-04-26 244.69 | Rising lows | stop | 2023-06-14
mark: 2023-02-02 | top
mark: 2023-03-06 | top
mark: 2023-04-28 | top
mark: 2022-10-21 | low | below
mark: 2023-01-05 | higher low | below
mark: 2023-04-26 | higher low | below
mark: 2023-06-14 | breakout
caption: Sellers met every rally at about the same price, while buyers paid more on each dip. The squeeze ended with a close through the flat top on above-average volume.
```

### Volatility contraction pattern (VCP)

Mark Minervini's general version of all of the above. What matters is not the shape's name. What matters is that **each pullback is shallower than the one before**, typically no more than 0.8 times the last. Volume shrinks as this happens, and the pattern ends in a tight, flat stretch near the highs.

A cup with handle *is* a VCP with two contractions: the cup, then the smaller handle. A high tight flag is a VCP with one.

```pattern
vcp
```

Trigger: the final contraction's high. Invalidation: the final contraction's low. That is what makes VCPs attractive: the stop is *close*, so even a modest move pays a lot compared with what you risk. See [VCP](learn-vcp.md) for how to read one, and [SEPA and the VCP](learn-strat-vcp-sepa.md) for the full trade.

---

## 3. Topping structures — patterns that say get out

Salesforce peaked at 236.88 in April 2021 (closing prices). It fell to 210.54, then rallied to a higher peak of 309.96 in November. The next rally, in January 2022, stopped at 232.63, below the November peak. The low between them, 211.00, was almost exactly the May low. On 11 February 2022 it closed at 207.90, below both lows.

```series
title: Salesforce — a head-and-shoulders top, 2021–22
from: 2021-03-01
to: 2022-06-30
tf: D
line: us:CRM | Salesforce, daily candles | candles
line: us:CRM@sma200 | 200-day average
level: 210.5 | Neckline | 2021-05-12 2022-06-30 | stop
mark: 2021-04-28 | left shoulder
mark: 2021-11-08 | head
mark: 2022-01-31 | right shoulder
mark: 2022-02-11 | breaks neckline | below
caption: Three rallies, the middle one highest. The neckline joined the lows near 210. After the break the price bounced back above it in March, then fell to 163.60 by May.
```

That is a **head-and-shoulders top**. Three rallies, with the middle one the highest. The third rally fails below the second. That is the first *lower high* after an advance, which is the definition of an uptrend starting to break down.

It is confirmed when the price breaks the neckline: the line through the lows between the rallies. The measured move then points downward. A bullish base should never be bought while a topping pattern is in force above it.

Two other topping structures:

- **Double top.** Two rallies to the same area, the second on weaker volume. It is confirmed when the price breaks below the low point between them. The logic is the mirror of the double bottom.
- **Climax run.** This is not a geometric pattern. After a long advance, the price makes the steepest rally of the whole move. It has the biggest weekly gains, the widest bars and often record volume. It also has exhaustion gaps: gaps that the price soon falls back into.

A climax run marks the moment the last buyers arrive. Minervini and O'Neil both sell *while the price is still rising* here.

Monolithic Power made a double top in 2024, after rising more than 50% since April. On 29 August it reached $959.64, then fell to a low of $795.95 a week later. In mid-October it rallied back to $954, on about a fifth less volume than at the first top. On 31 October it closed at $759.30, below the September low, on almost six times its average volume. By 20 November it was at $560.06.

```series
title: Monolithic Power — a double top, 2024
from: 2024-06-15
to: 2024-12-31
tf: D
line: us:MPWR | Monolithic Power, daily candles | candles
line: us:MPWR@vol | Volume | pane2 bars
level: 795.95 | Middle low | 2024-09-06 2024-12-31 | stop
mark: 2024-08-29 | first top
mark: 2024-09-06 | middle low | below
mark: 2024-10-14 | second top
mark: 2024-10-31 | breaks down
caption: Two rallies stopped at the same price, the second on lighter volume. The pattern was confirmed only when the price closed below the low between them.
```

---

## 4. Reading a breakout

The pattern makes the stock worth watching. The breakout is the actual trade. Here is what separates a real breakout from a false one, roughly in order of importance:

1. **Volume.** On the breakout day, volume should be clearly above average. A common rule is at least 1.4 times the 50-day average. A pivot cleared on low volume is more likely to fail, as Amazon's was in 2022.
2. **Where it closes.** You want a full-bodied close above the pivot, near the day's high (see [Candlestick patterns](learn-candlestick-patterns.md)). A move above the pivot during the day that closes back inside the base is not a breakout.
3. **Tightness just before.** The best breakouts come after the quietest final stretch: inside bars and NR7s (the narrowest bar of the last seven) at the pivot. Wide, choppy trading at the pivot means big holders are selling into the base (distribution), not buying.
4. **Follow-through.** Real breakouts usually keep going without falling back much. A close back below the pivot, and then below the breakout day's low, is a strong sign of failure. A *shallow, quiet* first pullback to the pivot that holds is normal. It is often a second chance to buy, the "retest".
5. **Market and group.** In weak markets and weak industry groups, breakouts fail in large numbers. Check the market's trend and the stock's group before you trust any breakout.

What happens after a failure, and how to trade it, is in [Failed breakouts and bull traps](learn-strat-failed-breakouts.md). Buying the retest is in [Pullback to support](learn-strat-pullback-support.md).

---

## 5. What the evidence says

Be honest about this, because the pictures are convincing.

**Random prices make patterns too.** Harry Roberts (1959) generated random price series and showed that they produce familiar shapes, including head-and-shoulders tops. A shape on a chart is therefore not, by itself, evidence that anyone is accumulating or distributing.

**Automated tests find a little information.** Lo, Mamaysky and Wang (2000) detected patterns by computer on US stocks from 1962 to 1996. Several patterns shifted the distribution of the next returns slightly. The effect was real but small, far smaller than practitioners claim.

**Bulkowski's statistics.** Thomas Bulkowski's catalogues are the largest public collection of pattern statistics. Most patterns' "success rates" fall apart once you look closely at how success was measured. His best performers are the rarer, stricter shapes, such as the high tight flag, not the common loose ones.

**Event studies on stored data.** Each strategy guide measured one pattern on daily prices for today's NSE and US stock lists. The samples start in 2010 or 2012 and run to recent years. Their method notes give the exact rules. The headline results:

| Pattern (guide) | Outcome measured | India | US |
|---|---|---|---|
| Base breakout ([CAN SLIM](learn-strat-canslim-breakout.md)) | +20% before −8%, within 60 sessions | 29.5% (any day: 25.6%) | 18.0% (any day: 18.6%) |
| Darvas box ([Darvas](learn-strat-darvas.md)) | +2R before the stop | 31.1% | 24.5% |
| Bull flag ([Flags](learn-strat-flags.md)) | Measured-move target before the stop | 30.5% | 25.9% |
| High tight flag ([Flags](learn-strat-flags.md)) | Measured-move target before the stop | 23.5% | 20.0% |
| Volume breakout ([Failed breakouts](learn-strat-failed-breakouts.md)) | Closed back below the level within 10 sessions | 57% | 53% |

What these show:

- **The shapes alone are a thin edge.** Base breakouts did slightly better than a random liquid stock in India and no better in the US.
- **Failure is normal.** More than half of volume breakouts dipped back below their level within two weeks.
- **Heavy breakout volume cut both ways.** In the CAN SLIM study, it raised the chance of a quick gain and of hitting the stop by similar amounts.

**What practitioners claim instead.** O'Neil and Minervini say patterns work only as the *last step for timing the entry*. The stock must also be a leader, in a leading group, in a supportive market, with strong earnings. That combined claim is harder to test and is still open.

**Limits.** The event studies use today's stock lists, so delisted companies are missing (survivorship bias). They have no costs, and their windows overlap. Pattern rules written by a computer also differ from patterns seen by a trained eye.

The working conclusion: **patterns are a way to read structure, stops and triggers. They are not an edge on their own**. Use them to know where a trade is proven wrong (the invalidation) and where it triggers (the pivot). Use them also to see what would be abnormal, such as volume or a failure signal. Do not expect the shape itself to make money.

## 6. Practising

1. Open a leading stock's chart and find last year's bases yourself. Mark each pivot, invalidation level and measured-move target.
2. Write the pivot and the stop down *before* the breakout, not after. Hindsight makes every chart look clean.
3. Record what happened after each breakout: did it follow through, retest, or fail? After fifty examples you will have your own statistics.
4. Compare the patterns that worked with the ones that failed. Look at the market, the group and the volume, not just the shape.

## Further reading

- William O'Neil, *How to Make Money in Stocks* — cup with handle, flat base, double bottom, and CAN SLIM, his checklist of conditions to have in place before buying.
- Mark Minervini, *Trade Like a Stock Market Wizard* — VCP, pivots, and the logic of tightness and volume behind every pattern above.
- Thomas Bulkowski, *Encyclopedia of Chart Patterns* — the statistics, and a cure for believing too much in patterns.
- Nicolas Darvas, *How I Made $2,000,000 in the Stock Market* — the box theory that became the flat base.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — stage analysis: when in a stock's life cycle patterns are worth trading at all.
- Harry Roberts, "Stock-Market 'Patterns' and Financial Analysis", *Journal of Finance* (1959).
- Andrew Lo, Harry Mamaysky and Jiang Wang, "Foundations of Technical Analysis", *Journal of Finance* (2000).
