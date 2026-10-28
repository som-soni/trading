# Level indicators — pivot points, Fibonacci retracements, Zig Zag and Darvas boxes

**In short**

- Level indicators output prices, not a line through time: a pivot, a swing high, a retracement level, a box top. They say where to pay attention, not what will happen.
- Floor-trader pivot points come from the previous period's high, low and close. Everyone gets the same numbers, which is their main appeal. Published evidence that stocks respect them is thin.
- Swing pivots and the Zig Zag find turning points after the fact. A swing pivot is confirmed only n bars later, and the Zig Zag redraws its last leg as new bars arrive. Neither is a live signal.
- Fibonacci levels and Darvas boxes are measured from those swings. On stored prices, pullbacks did not stop at Fibonacci ratios more often than chance.
- Use a level as a reference for an entry, a stop or a target. Let what the price does at the level decide.

Most indicators in this course turn prices into a reading that moves every day. The ones here mark prices instead. Drawing levels by hand, as zones, is covered in [Support and resistance — drawing the levels that matter](learn-support-resistance.md) and [Supply and demand — zones, and why price levels matter](learn-supply-demand.md). The trades built on two of these tools are in [Retracements and measured moves — Fibonacci levels, honestly](learn-strat-retracements.md) and [Darvas boxes — buying the breakout from a range at new highs](learn-strat-darvas.md). How this family fits with the others is in [Indicators — the map](learn-ind-map.md).

---

## 1. What this family measures

Reliance Industries ended September 2026 at ₹1,187.00, near the low of the month. From September's high, low and close, the standard formula gives a monthly pivot of ₹1,233.90 for October. On 21 October Reliance traded up to ₹1,234.30, 40 paise above the pivot, and turned down. It closed the day at ₹1,209.

Stories like this are why pivot points are popular. They are also chosen after the fact: nobody remembers the months when the price sailed through. Section 2 shows a second stock in the same month, and section 8 what the published evidence says.

```series
title: Reliance Industries, August–October 2026 — September's range sets October's pivots
from: 2026-08-01
to: 2026-10-27
tf: D
line: india:RELIANCE.NS | Reliance
line: india:RELIANCE.NS@zigzag.zz | Zig Zag (5%)
mark: 2026-09-04 | September high ₹1,333.00
mark: 2026-09-30 | September low ₹1,181.70
mark: 2026-10-13 | October low ₹1,152.20
mark: 2026-10-21 | high ₹1,234.30; pivot ₹1,233.90
caption: October's monthly pivot, ₹1,233.90, came from September's high, low and close. The October high stopped 40 paise above it. One month on one stock proves nothing; it shows what the levels are, not that they work.
```

A level indicator answers one question: **which prices are worth watching?** It does not say whether the price will stop there, bounce, or go straight through.

That makes this family different from the others. An oscillator gives a reading you can correlate with RSI; a level is just a price. So the overlap measurement used for the other families does not apply here. The evidence comes from worked examples, a few published studies, and the event study in the retracements guide.

## 2. Floor-trader pivot points

**The question.** Given last period's high, low and close, where are this period's balance point and its likely extremes? The method comes from floor traders in the futures pits, who needed levels they could work out by hand before the open.

### 2.1 Traditional pivots

```
P  = (H + L + C) ÷ 3            the pivot: last period's "typical price"
R1 = 2 × P − L                  S1 = 2 × P − H
R2 = P + (H − L)                S2 = P − (H − L)
R3 = H + 2 × (P − L)            S3 = L − 2 × (H − P)
H, L, C = the previous period's high, low and close
```

R stands for resistance, S for support. The period is a choice. Day traders use yesterday's bar; on a daily chart, monthly pivots are typical; on a weekly chart, yearly ones.

**Worked example.** Reliance's October 2026 pivots, from September 2026:

| Input or level | Arithmetic | Value |
|---|---|---|
| September high (H), 4 Sep | — | ₹1,333.00 |
| September low (L), 30 Sep | — | ₹1,181.70 |
| September close (C) | — | ₹1,187.00 |
| Range (H − L) | 1,333.00 − 1,181.70 | ₹151.30 |
| P | (1,333.00 + 1,181.70 + 1,187.00) ÷ 3 | ₹1,233.90 |
| R1 | 2 × 1,233.90 − 1,181.70 | ₹1,286.10 |
| S1 | 2 × 1,233.90 − 1,333.00 | ₹1,134.80 |
| R2 | 1,233.90 + 151.30 | ₹1,385.20 |
| S2 | 1,233.90 − 151.30 | ₹1,082.60 |
| R3 | 1,333.00 + 2 × (1,233.90 − 1,181.70) | ₹1,437.40 |
| S3 | 1,181.70 − 2 × (1,333.00 − 1,233.90) | ₹983.50 |

One property is worth knowing. R1 minus last period's high works out to (2C − H − L) ÷ 3. When last period closed mid-range, R1 sits right on last period's high, and S1 on its low. So "the price stopped at R1" is often "the price stopped at last month's high", an older and simpler level.

### 2.2 Fibonacci and Camarilla pivots

Two variants keep the idea and change the spacing.

```
Fibonacci:  P as above;  R1, R2, R3 = P + 0.382, 0.618, 1.000 × (H − L);  S1, S2, S3 = P − the same
Camarilla:  R1, R2, R3 = C + 1.1 × (H − L) ÷ 12, ÷ 6, ÷ 4;  S1, S2, S3 = C − the same
```

Camarilla levels are centred on the close, not on P, and sit much closer together. The same September inputs give:

| Reliance, October 2026 | Traditional | Fibonacci | Camarilla |
|---|---|---|---|
| R3 | ₹1,437.40 | ₹1,385.20 | ₹1,228.61 |
| R2 | ₹1,385.20 | ₹1,327.40 | ₹1,214.74 |
| R1 | ₹1,286.10 | ₹1,291.70 | ₹1,200.87 |
| P | ₹1,233.90 | ₹1,233.90 | (centred on C, ₹1,187.00) |
| S1 | ₹1,134.80 | ₹1,176.10 | ₹1,173.13 |
| S2 | ₹1,082.60 | ₹1,140.40 | ₹1,159.26 |
| S3 | ₹983.50 | ₹1,082.60 | ₹1,145.39 |

### 2.3 What happened in October

| October 2026 | Reliance | Apple (AAPL) |
|---|---|---|
| September H / L / C | ₹1,333.00 / 1,181.70 / 1,187.00 | $345.34 / 309.90 / 333.02 |
| Traditional P / R1 / S1 | ₹1,233.90 / 1,286.10 / 1,134.80 | $329.42 / 348.94 / 313.50 |
| October low | ₹1,152.20 on 13 Oct | $325.81 on 1 Oct |
| October high | ₹1,234.30 on 21 Oct | $351.73 on 23 Oct |
| Close on 27 Oct | ₹1,196.20 | $347.10 |

Reliance's high stopped at P. Its low fell between Camarilla S2 and S3, ₹17 above Traditional S1. Apple's highs stalled within about $2 of R1 for four sessions from 13 October. It then poked above R1 on 23 October and closed back below it. Its October low went $3.61 under P without stopping there.

Read that table with care. With 21 levels from three methods, some level is near almost any turn. Camarilla's levels on Reliance were only about ₹14 apart. And Apple's R1 was $3.60 above September's high, itself an obvious level.

**How traders use them.** A common reading: above P, the bias is up and R1 is the first target; below P, the bias is down and S1 is the first target. Day traders use daily pivots this way. Swing traders look for a pivot that lines up with a level drawn by hand, a "confluence", and treat the pair as a zone.

**Pitfalls.** The levels come from one period's three prices, so one wild month gives levels far apart for the next. They take no account of where volume traded or where earlier turns happened. And they reset every period, so a level that mattered last month simply disappears.

## 3. Swing pivots — turning points, confirmed late

**The question.** Where did the price actually turn? Every other tool in this guide is measured from these points.

```
swing high: a bar whose high is above the highs of the n bars before it and the n bars after it
swing low:  a bar whose low is below the lows of the n bars before it and the n bars after it
common settings: n = 5 or 10 bars each side
```

The catch is in "the n bars after it". **A swing pivot is confirmed only n bars after it happens.** Until then it is a candidate.

**Worked example.** Reliance's swing highs in mid-2026, with 10 bars each side:

| Swing high | On | Confirmed at the close of |
|---|---|---|
| ₹1,473.40 | 5 May 2026 | 19 May |
| ₹1,344.90 | 22 Jun 2026 | 6 Jul |
| ₹1,345.90 | 20 Jul 2026 | 3 Aug |
| ₹1,337.00 | 7 Aug 2026 | 21 Aug |
| ₹1,333.00 | 4 Sep 2026 | 18 Sep |

The highs were flat to falling for four months. Read as structure, that is a stock failing to make higher highs, a mark of a downtrend or a range.

The October low of ₹1,152.20 on 13 October shows the delay. With 5 bars each side it became a swing low at the close of 21 October. With 10 bars each side it was still unconfirmed on 27 October. A wider setting finds fewer, more important turns, and reports them later.

**Pitfalls.** Many charts draw swing pivots on the bar where they happened, not where they were confirmed. Looking back, that makes them appear on time. Any rule that "buys at the swing low" must wait the n bars, at a different price.

## 4. Zig Zag — swings above a size, and a line that repaints

**The question.** Ignoring every move smaller than a set percentage, what were the swings? It joins swing points that reversed by at least that much with straight lines.

```
start a leg from the last confirmed swing point
in an up leg: track the highest high; when the low falls deviation % below it,
              that high is confirmed as a swing high and a down leg begins
in a down leg: the same in reverse
the last leg runs from the last confirmed swing to the latest extreme
default deviation: 5%
```

The right deviation depends on the stock. A 5% threshold on a volatile stock catches daily noise:

| Swing points in 2025 | Median ATR % | Zig Zag 5% | Zig Zag 10% |
|---|---|---|---|
| Block (XYZ) | 3.8% | 73 | 26 |
| Apple (AAPL) | 2.2% | 28 | 6 |
| Reliance (RELIANCE.NS) | 1.7% | 10 | 6 |

ATR % is the average daily range as a share of the price ([Volatility indicators](learn-ind-volatility.md)). Scaling the deviation to a stock's ATR % keeps the swings comparable from one stock to another.

```series
title: Block (XYZ), June–October 2026 — the Zig Zag at 5% and at 10%
from: 2026-06-01
to: 2026-10-27
tf: D
line: us:XYZ | Block
line: us:XYZ@zigzag.zz | Zig Zag 5%
line: us:XYZ@zigzag(deviation=10).zz | Zig Zag 10%
mark: 2026-08-27 | high $86.92
mark: 2026-10-01 | low $72.28
caption: At 5% the line follows almost every wiggle of a stock that moves nearly 4% a day. At 10% it keeps the swings that matter. The final leg of each line is provisional: it ends at the latest extreme and moves as new bars arrive.
```

**It repaints.** "Repainting" means an indicator changes its past values when new bars arrive. The Zig Zag's last leg always does. Here is what the 10% Zig Zag on Block showed when viewed on different days:

| Viewed at the close of | Close | Last point of the line | What it meant |
|---|---|---|---|
| 27 Aug 2026 | $84.85 | $86.92 high, 27 Aug | Provisional: a high only until a 10% drop follows |
| 2 Sep 2026 | $82.46 | $76.96 low, 2 Sep | $86.92 now confirmed; this low is provisional |
| 10 Sep 2026 | $79.07 | $76.96 low, 2 Sep | Unchanged |
| 1 Oct 2026 | $74.04 | $72.28 low, 1 Oct | The $76.96 "low" has vanished |
| 27 Oct 2026 | $74.87 | $81.17 high, 16 Oct | The fall since 16 October, 8% by the close, is not drawn at all |

On 2 September the chart showed a swing low at $76.96. A month later that low was gone, replaced by one at $72.28. And on 27 October the latest fall did not appear, because it was still short of 10%.

**Never use the Zig Zag as a live signal.** Every past turn on it looks perfect because it was drawn after the fact. Use it to label history: the size of past swings, or the swing points to measure a retracement from.

## 5. Fibonacci retracements

**The question.** How much of the last swing has a pullback given back?

```
level at ratio r = swing high − r × (swing high − swing low)       (for a pullback in a rise)
usual ratios: 23.6%, 38.2%, 50%, 61.8%, 78.6%
```

38.2% and 61.8% come from the Fibonacci sequence; 50% does not, but is always drawn. [Retracements and measured moves](learn-strat-retracements.md) explains where each ratio comes from.

**Worked example.** Block rose from a low of $48.21 on 12 February 2026 to a high of $86.92 on 27 August. That is a rise of $38.71. It then fell to $72.28 on 1 October.

| Ratio | Arithmetic | Level |
|---|---|---|
| 23.6% | 86.92 − 0.236 × 38.71 | $77.78 |
| 38.2% | 86.92 − 0.382 × 38.71 | $72.13 |
| 50% | 86.92 − 0.5 × 38.71 | $67.57 |
| 61.8% | 86.92 − 0.618 × 38.71 | $63.00 |
| Actual low, 1 Oct | (86.92 − 72.28) ÷ 38.71 | 37.8% retraced |

The low came within 15 cents of the 38.2% level, and the stock rallied to $81.17. Now look at the repainting table. On 2 September the Zig Zag showed the pullback ending at $76.96, near the 23.6% level. Which level "held" depended on the day you looked.

**What the evidence says.** The retracements guide counted thousands of completed pullbacks in US and Indian stocks. Their depths formed a smooth hump, with no spikes at the Fibonacci ratios. About one pullback in three ended within 3 points of one of the three main levels. That is what chance gives, because those bands cover the busiest part of the hump.

## 6. Darvas boxes

**The question.** After a new high, what range is the stock holding, and where does it break out?

Nicolas Darvas, a professional dancer, described the method in *How I Made $2,000,000 in the Stock Market* (1960).

```
box top:    after a new high, a high that is not exceeded for three sessions
box bottom: after the top is set, a low that holds for three sessions
buy:        a buy-stop just above the box top
stop:       just below the box bottom; each new, higher box raises it
```

The box is a level indicator with a rule attached: buy strength above the top, sell weakness below the bottom. It is a cousin of the flat base and the channel breakout. The full method, a worked trade and its weak spots are in [Darvas boxes](learn-strat-darvas.md).

## 7. The family side by side

| Indicator | Question it answers | Defaults | Known when? | Typical use |
|---|---|---|---|---|
| Traditional pivots | Where are this period's balance point and extremes? | Prior period's H, L, C; monthly on a daily chart | At the start of the period | Bias above/below P; targets at R1/S1 |
| Fibonacci pivots | The same, spaced by range ratios | 0.382 / 0.618 / 1.0 × range | At the start of the period | As above |
| Camarilla pivots | Tight levels around the last close | 1.1 × range ÷ 12, 6, 4 | At the start of the period | Short-term fades and breakouts |
| Swing pivots | Where did the price turn? | 5 or 10 bars each side | n bars later | Structure; stops under swing lows |
| Zig Zag | What were the swings above a size? | 5% | Last leg: never final | Labelling history only |
| Fibonacci retracements | How much of the swing has been given back? | 38.2 / 50 / 61.8% | Once the swing is known | Rough map of a normal pullback |
| Darvas boxes | What range is held after a new high? | 3-session top and bottom | 3 sessions after each edge | Breakout entry and stop |

## 8. What the evidence says

**No overlap measurement.** The other family guides correlate each indicator with RSI and five other readings. A price level has no daily reading to correlate, so this family was not part of that measurement.

**Published research is thin.** Carol Osler (2000) studied the support and resistance levels that several firms published for currency traders. Intraday trends paused at those levels more often than at arbitrary levels, though the effect was modest and varied between firms. Osler (2003) found that currency stop and take-profit orders cluster at round numbers. That is a mechanism: a level many people watch attracts orders, which can make it mildly self-fulfilling.

We know of no careful published test of floor-trader pivot points on stocks. Fibonacci retracements have been tested, and the evidence is against special ratios. Darvas's own account is one trader's memoir, not a test.

**Measured here.** Pullback depths in US and Indian stocks formed a smooth hump with no Fibonacci spikes ([Retracements and measured moves](learn-strat-retracements.md)). Zones drawn by fixed rules held no more often than chance ([Support and resistance](learn-support-resistance.md)). The Zig Zag and swing-pivot tables above show how much depends on the setting and on the day you look.

**Limits.** The worked examples were chosen to show the tools, so they are not typical. Hindsight flatters every level indicator: the turns that lined up are memorable, the ones that did not are forgotten.

**Good practice.** Treat a level as a place to watch, not a forecast. Act on what happens there: a close back above it, volume, a reversal bar. Put stops beyond a level, not on it, because many stops sit exactly on the obvious prices.

## 9. Checklist

- [ ] Is this level one I would have drawn anyway, such as last month's high, or does it only come from a formula?
- [ ] Which period are my pivots from, and was that period's range unusual?
- [ ] Am I reading a swing pivot or a Zig Zag point that is not yet confirmed?
- [ ] Is my Zig Zag deviation large enough for this stock's ATR %?
- [ ] Did I draw the Fibonacci levels before the pullback ended, or after?
- [ ] What would the price have to do at the level for me to act?
- [ ] Is my stop beyond the level, rather than on it?

## Further reading

- Nicolas Darvas, *How I Made $2,000,000 in the Stock Market* (1960) — the box method in the author's words.
- Carol Osler, "Support for Resistance: Technical Analysis and Intraday Exchange Rates" (*Federal Reserve Bank of New York Economic Policy Review*, 2000).
- Carol Osler, "Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis" (*Journal of Finance*, 2003).
