# Retracements and measured moves — Fibonacci levels, honestly

**In short**
- A retracement measures how much of a prior rise a pullback gives back: a third, a half, 61.8%.
- Fibonacci levels are widely watched, so they work as common reference points. There is no good evidence that prices respect them more than other levels.
- In our data, pullback depths form a smooth hump with no real spikes at the Fibonacci ratios. The "typical" depth even shifts with how you measure the swings.
- Use retracement levels as a rough map of where a healthy pullback usually ends (between about a third and two thirds), and let structure decide the trade: an old breakout level, a rising average, a reversal bar.
- A measured-move target (the next leg equals the last) was reached only about a third of the time in our data. Treat it as a stretch target, not a forecast.

## 1. The idea

Start with a real case. Nvidia rose from 76.20 on 19 April 2024 to 135.58 on 18 June 2024 (closing prices, split-adjusted). Then it fell. On 7 August 2024 it closed at 98.91. That pullback gave back 61.8% of the rise, to within a cent of the most famous Fibonacci level.

```series
title: Nvidia, a 61.8% retracement in 2024 (split-adjusted)
from: 2024-03-15
to: 2024-11-30
line: us:NVDA | Nvidia | log
line: us:NVDA@sma50 | 50-day average
line: us:NVDA@vol | Volume | pane2 bars
mark: 2024-04-19 | Swing low 76.20
mark: 2024-06-18 | Swing high 135.58
mark: 2024-08-07 | Close 98.91: a 61.8% retracement
caption: The August 2024 low closed almost exactly on the 61.8% retracement of the April–June rise. The stock made a new high in October.
```

Cases like this are why Fibonacci retracements are popular. They are also memorable for the wrong reason. Nobody keeps a list of the pullbacks that stopped at 44% or 71%. Section 8 shows what happens when you count all of them.

**How the levels are drawn.** Take a swing low L and the swing high H that followed. The rise is H − L. A retracement level at ratio r is H − r × (H − L). For Nvidia, the rise was 59.38, so the levels were:

| Ratio | Level | Where the ratio comes from |
|---|---|---|
| 23.6% | 121.57 | 0.618 cubed |
| 38.2% | 112.90 | 0.618 squared |
| 50% | 105.89 | Not a Fibonacci number; from Dow Theory and W. D. Gann |
| 61.8% | 98.88 | 1 ÷ 1.618, the "golden ratio" |
| 78.6% | 88.91 | The square root of 0.618 |

In the Fibonacci sequence, each number is the sum of the two before it. Divide any number in it by the next one, and the result gets ever closer to 0.618. Traders took these ratios from Ralph Elliott's wave theory in the 1930s and 1940s. There is no known reason why a market should care about them, except that traders do.

**Why it can still be useful.** The idea underneath is sound. After a strong rise, a pullback that gives back a third to two thirds of it is normal. A pullback that gives back nearly all of it says the rise has failed.

A retracement grid turns that into numbers. It also gives everyone the same reference points, so orders cluster there. That makes levels partly self-fulfilling, the way round numbers are.

**Who is on the other side?** The same as for any pullback buy: short-term holders taking profit, and traders who think the trend is over. You are betting that the original buyers return before the rise is undone.

## 2. When it works and when it doesn't

**It works as a filter, not as a signal.** A retracement level on its own picks a price, not a reason. It is most useful when it lines up with something structural: a prior breakout level, a demand zone, a rising 50-day average or a gap. See [Pullback to support](learn-strat-pullback-support.md) and [Pullback to a moving average](learn-strat-pullback-ma.md).

**It works in a clear trend with clean swings.** You need an obvious swing low and swing high. In choppy, sideways stocks, every analyst draws a different grid.

**It fails when the swing points are a matter of taste.** Move the swing low by a week and every level moves. If you cannot say in advance which swing you are measuring, the level means little.

**It fails in a market decline.** Retracements of a stock's rise get overrun when the whole market is falling. Trent in late 2024 is an example (section 6).

**India and the US.** The arithmetic is the same. In India, larger overnight gaps mean the price often opens straight through a level, so a limit order at an exact Fibonacci price may fill far below it. Use zones, not single prices, and use stop orders that survive overnight (GTT orders at many brokers).

## 3. The rules

These rules use retracements inside a structure-first pullback trade. Names in backticks are parameters in section 4.

### Universe and filters

- Price at least `min price`, average daily traded value at least `min liquidity`.
- The 50-day average is above the 200-day average, and the close is above the 200-day.
- The market index closes above its 50-day average.
- No results within the next `earnings gap` sessions.

### Setup

1. **The swing.** Find swing points with a fixed rule, decided in advance. For example: a swing high is a close that is the highest close of the surrounding `swing window` sessions on each side. A swing low is defined the same way.
2. **A real rise.** The rise from swing low L to swing high H is at least `min rise` and at least `min rise ATR` × ATR(14).
3. **The retracement zone.** Zone top = H − `zone shallow` × (H − L). Zone bottom = H − `zone deep` × (H − L). With the usual values, that is the band from 38.2% to 61.8%.
4. **Confluence.** At least one structural level lies inside the zone: a prior breakout level, the top of a prior base, or the 50-day average. This is required, not optional.
5. **No breakdown.** No close below H − `fail ratio` × (H − L) since the swing high.

### Entry

- Wait for a **reversal bar**: a session whose low is inside the zone and whose close is in the top third of its range.
- Place a buy-stop one tick above its high for the next session.
- If the stock gaps over the trigger, you are filled at the open. Record that price.
- Cancel if the price closes below the zone bottom, or if no reversal bar appears within `entry window` sessions of first entering the zone.

### Initial stop

- Stop = the lower of the reversal bar's low and the zone bottom, minus `stop buffer` × ATR(14).
- If the risk is more than `max risk` of the entry price, skip the trade. Deep retracements in volatile stocks often fail this test.

### Exits

- **First target.** Sell half at the swing high H, or at `target R`, whichever is nearer. **1R** is the distance from entry to the initial stop.
- **Stretch target.** For the rest, the measured move: the new swing low plus the size of the prior rise (H − L). Or the 127.2% or 161.8% extension of the pullback.
- **Trail.** Once the price is above H, trail under the 21-day EMA or under the latest higher swing low.
- **Time stop.** If the price has not reached +1R within `time stop` sessions, exit.
- **Invalidation.** A close below H − `fail ratio` × (H − L) ends the trade. Gaps below the stop are exited at the open.

### Position size

- Shares = (account × `risk %`) ÷ (entry − stop). Stops in this setup are often wide, so positions are smaller.
- Cap any position at `max position` of the account. See [Position sizing](learn-risk-sizing.md).

### Managing the trade

- Do not move the zone after the fact to make a level "work". Write down L and H before the trade.
- Results inside the trade are a gap risk larger than the stop. Exit or reduce size before them.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| `swing window` | 5–20 sessions each side | Which highs and lows count as swings | Changes every level; fix it before testing |
| `min rise` | 20–30% | Only measure meaningful rises | Smaller rises give noisy grids |
| `min rise ATR` | 5–8 × ATR(14) | Same, scaled to volatility | |
| `zone shallow` | 0.382 (range 0.33–0.40) | Top of the buy zone | Shallower catches more strong-trend pullbacks |
| `zone deep` | 0.618 (range 0.60–0.67) | Bottom of the buy zone | Dow Theory's band is one third to two thirds |
| `fail ratio` | 0.786–0.85 | Where the rise counts as failed | Beyond this, it is no longer a pullback |
| `entry window` | 5–10 sessions | How long to wait for a reversal bar | |
| `stop buffer` | 0–0.5 × ATR(14) | Room under the zone or bar | Very sensitive |
| `max risk` | 8–12% of entry | Skips trades whose stop is too far | Retracement stops run wider than MA pullback stops |
| `target R` | 2R | First profit-take if H is far away | |
| Extensions | 127.2%, 161.8%, 100% measured move | Stretch targets | Reached far less often than drawn |
| `time stop` | 10–20 sessions | Exits dead trades | |
| `earnings gap` | 5–15 sessions | Avoids results inside the trade | |
| `min price` / `min liquidity` | ₹50 / ₹10 crore; $10 / $20 million | Tradability | |
| `risk %` / `max position` | 0.5–1% / 15–25% | Risk and concentration | |

## 5. Variations

**Dow Theory's thirds.** Robert Rhea's *The Dow Theory* (1932) described secondary reactions in a primary trend as usually retracing one third to two thirds of the prior move. That is close to the modern 38.2–61.8% band, decades before Fibonacci ratios became popular.

**W. D. Gann's halves and eighths.** Gann gave special weight to the 50% retracement and to divisions of a range into eighths. The 50% level that appears on every Fibonacci tool comes from this tradition, not from Fibonacci.

**Elliott Wave.** Ralph Nelson Elliott's wave principle, popularised by Frost and Prechter's *Elliott Wave Principle* (1978), is the source of most Fibonacci use in markets. In it, corrective waves often retrace 38.2%, 50% or 61.8% of the prior wave. Wave counts are notoriously subjective, which makes the method hard to test.

**Harmonic patterns.** Some traders combine several Fibonacci ratios into named shapes (the "Gartley", the "butterfly"). Each adds more ratios and more tolerance bands. More conditions do not mean more evidence; they mean more ways to fit the past.

**Measured moves and AB=CD.** Edwards and Magee described flags that "fly at half-mast": the move after the flag tends to equal the move before it. Thomas Bulkowski catalogues "measured move up" and "measured move down" patterns in *Encyclopedia of Chart Patterns*. The AB=CD pattern of harmonic traders is the same idea. Section 8 tests how often the second leg actually matches the first.

**Structure-only traders.** Many trend traders ignore Fibonacci entirely. They buy pullbacks to a rising average, a broken level or a demand zone, and simply note that most such pullbacks end between a third and two thirds of the prior rise.

## 6. Worked examples

All prices are split-adjusted daily prices. The rules are those of section 3. The zone runs from the 38.2% to the 61.8% level. The stop buffer is 0.25 ATR, and the maximum risk is 10%.

### Example 1 — Nvidia, August 2024 (US; the level that worked, and a stop that was too wide)

| Step | Date | Detail |
|---|---|---|
| Swing low L / high H | 19 Apr / 18 Jun 2024 | 76.20 / 135.58; rise 59.38 |
| Zone | | 112.90 (38.2%) down to 98.88 (61.8%) |
| Confluence | | The rising 200-day average was near 81, below the zone; none in the zone itself |
| First reversal bar | 5 Aug | Low 90.69, below the zone; close 100.45 in the top third. Stop would be about 88.70: risk about 15%, too wide. Skip |
| Second reversal bar | 8 Aug | Low 97.52, close 104.97, high 105.50 |
| Entry | 9 Aug | Opened at 105.64, above the trigger; filled at the open |
| Stop | | 97.52 − 0.25 × ATR (7.98) = about 95.53; risk 10.11, or 9.6% |
| First target 2R | 19 Aug | 2R = about 125.86; the high that day was 130.00 |

Strictly, the confluence rule was not met: no structural level sat inside the zone. A disciplined trader would have passed. It is included because it is the kind of case that makes Fibonacci famous. The first reversal bar also shows the practical problem: the stop under a deep retracement in a volatile stock can be very wide.

The measured move from the August low was 98.91 + 59.38 = 158.29. Nvidia's next high, on 7 November 2024, closed at 148.88. The stock first closed above 158.29 on 3 July 2025, almost a year later.

### Example 2 — Trent, November 2024 (India; the bounce that failed)

```series
title: Trent, a 61.8% bounce that failed, 2024–25
from: 2024-06-15
to: 2025-03-31
line: india:TRENT.NS | Trent | log
line: india:TRENT.NS@sma50 | 50-day average
line: india:NIFTY500 | Nifty 500 | right
mark: 2024-07-19 | Swing low 5,166
mark: 2024-10-11 | Swing high 8,235
mark: 2024-11-22 | Reversal bar in the zone
mark: 2025-01-13 | Stop hit
caption: Trent bounced from near its 61.8% retracement in November, failed below its old high, and then gave back the whole rise as the Indian market fell.
```

| Step | Date | Detail |
|---|---|---|
| Swing low L / high H | 19 Jul / 11 Oct 2024 | 5166.35 / 8234.95; rise 3068.60 |
| Zone | | 7062.7 (38.2%) down to 6338.5 (61.8%) |
| Confluence | | None clear; the 50-day average was above the zone |
| Low of the pullback | 18 Nov | Low 6275.00, close 6301.65, just under 61.8% |
| Reversal bar | 22 Nov | Low 6430.00, close 6652.80, high 6678.00 |
| Entry | 25 Nov | Opened at 6799.00, above the trigger |
| Stop | | 6338.5 − 0.25 × ATR (261.2) = about 6273.2; risk about 525.8, or 7.7% |
| Best price | 3 Jan 2025 | High 7493.05, about +1.3R; 2R (about 7850.6) never reached |
| Exit | 13 Jan 2025 | Low 6155.00; stopped, −1R |

The "61.8% held" story was true for six weeks. Then the market decline took over. Trent closed below the 78.6% level on 21 January and below the original swing low in February. The structural confluence rule would have kept you out. So would the market filter: the Nifty 500 closed below its 50-day average throughout November 2024.

### Example 3 — Nifty 50, 2024–25 (India; the level that wasn't there)

```series
title: Nifty 50, a 45% retracement, 2023–25
from: 2023-01-01
to: 2025-12-31
line: india:NIFTY50 | Nifty 50
line: india:NIFTY50@sma50 | 50-day average
mark: 2023-03-24 | Swing low 16,945
mark: 2024-09-26 | Swing high 26,216
mark: 2025-03-04 | Low close 22,083
caption: The Nifty 50's 2024–25 correction ended near 45% of the prior rise, between the 38.2% and 50% levels. In November 2025 it was back at its old high.
```

The Nifty 50 rose from 16,945 on 24 March 2023 to 26,216 on 26 September 2024. It then fell to a closing low of 22,083 on 4 March 2025, and made a second, slightly higher low in April. That is a retracement of about 44.6%.

| Level | Price |
|---|---|
| 38.2% | 22,675 |
| 50% | 21,581 |
| 61.8% | 20,487 |
| Actual low close | 22,083 (44.6%) |

The low sat between two levels, about 500–600 points from each.

A trader with a limit order at 38.2% was filled too early and sat through a further 2.6% drop. A trader waiting for 50% or 61.8% never got filled. A trader using the band and a reversal rule did fine. The index was back at 26,216 by late November 2025. The lesson: treat the band as the map, not any single line.

## 7. Common mistakes

- **Choosing the swing points after seeing the bounce.** There is almost always some swing for which the turn "was a Fibonacci level".
- **Treating a line as a price.** Levels are zones. Orders cluster around them, not on them.
- **Buying a level with nothing else there.** Without structure, a retracement level is one guess among many.
- **Ignoring how deep 61.8% really is.** A stock that gives back nearly two thirds of its rise is weaker than one that gives back a third. The trade needs a wider stop and a smaller size.
- **Taking extension targets as forecasts.** A 161.8% extension is a drawing, not a prediction.
- **Adding ratios until something fits.** Five levels and their tolerance bands cover a large part of every pullback. Fit is guaranteed; evidence is not.

## 8. What the evidence says

**Little formal support.** We know of no peer-reviewed study showing that stock prices turn at Fibonacci ratios more often than chance. Batchelor and Ramyar, in a working paper titled "Magic numbers in the Dow", tested the ratios on swings in the Dow Jones index and found no evidence that they mattered. Osler's work on currency markets (2000, 2003) found that orders cluster at round numbers and published levels, which can make widely watched levels mildly self-fulfilling. That is the honest case for Fibonacci: it is a common reference point, not a law of nature.

**Our event study: how deep are pullbacks?** We found swings in liquid US and Indian stocks from 2010 onward with a fixed rule. A swing turns when the close reverses by 8% from its extreme. We kept every rise of at least 25% whose pullback was followed by a new high above the swing high. The depth of each pullback is the share of the rise it gave back.

| Depth of pullback | US share | India share |
|---|---|---|
| 10–20% | 2.3% | 2.9% |
| 20–30% | 14.6% | 17.3% |
| 30–40% | 24.9% | 25.4% |
| 40–50% | 21.4% | 21.0% |
| 50–60% | 14.1% | 13.5% |
| 60–70% | 9.3% | 8.6% |
| 70–80% | 6.7% | 5.4% |
| 80–90% | 4.1% | 3.7% |
| 90–100% | 2.7% | 2.1% |
| Pullbacks | 16,141 | 6,445 |
| Median depth | 43.2% | 41.7% |

The shape is a smooth hump. Most completed pullbacks gave back between a fifth and three fifths of the rise. That supports the old Dow Theory band of a third to two thirds as a description of normal pullbacks.

**Are the Fibonacci levels special?** We counted pullbacks within 1.5 points of each ratio. We compared that with what a smooth curve fitted to the rest of the distribution would predict.

| Level | US, 8% swings | US, 12% swings | India, 8% swings |
|---|---|---|---|
| 23.6% | 1.01 | 0.93 | 1.00 |
| 38.2% | 1.10 | 1.04 | 1.15 |
| 50% | 0.94 | 0.98 | 0.95 |
| 61.8% | 1.15 | 1.11 | 1.01 |
| 78.6% | 0.93 | 1.09 | 0.78 |

A ratio of 1.00 means "exactly as many as a smooth curve predicts". The values scatter between 0.78 and 1.15, with no level consistently above 1. The 50% level, the most quoted, is slightly below 1 in all three samples. The 38.2% level is the only one above 1 in all three samples, by a small margin. It also sits at the peak of the hump, where a smooth curve is hardest to fit, so we would not read much into it.

**The typical depth depends on how you measure.** With 8% swings, the US median depth was 43.2%. With 12% swings, it was 55.5% (13,015 pullbacks). The same stocks, measured differently, "retrace" to a different typical level. That is the strongest reason to distrust any single magic number.

**Confluence by chance.** About 32% of all pullbacks ended within 3 points of a main level. The three levels are 38.2%, 50% and 61.8%. In all three samples the share was between 31% and 33%. Those three bands cover the busiest part of the distribution. So "it bounced near a Fibonacci level" will be true of about one pullback in three, whether or not the levels matter.

**Measured moves.** For the same swings, we compared the next rise (from the pullback low to the next swing high) with the prior rise.

| | US | India |
|---|---|---|
| Cases | 17,135 | 6,722 |
| Median next rise ÷ prior rise | 0.74 | 0.73 |
| Next rise at least equal to the prior one | 31.1% | 31.9% |
| Next rise at least half the prior one | 76.2% | 75.1% |
| Middle half of outcomes | 0.51 to 1.12 | 0.50 to 1.14 |

A full measured move happened in about a third of cases. Half of it happened in about three quarters. If you use a measured-move target, take partial profits well before it.

Method notes: daily closes; US stocks priced at $10 or more, with at least $20 million average daily traded value at the swing high. Indian stocks priced at ₹50 or more, with at least ₹10 crore. The universe is today's list of stocks, so delisted stocks are missing. Keeping only pullbacks followed by a new high removes failed rises from the depth table. That is deliberate: we are describing pullbacks that turned out to be pullbacks.

## 9. Building and testing it yourself

**Data.** Daily prices adjusted for splits and bonus issues, including delisted stocks. Results dates as known at the time.

**The swing rule is the whole test.** Fix it before you look at results. A swing high confirmed by "the highest close of 10 sessions on each side" is only known 10 sessions later. Your grid can only use swings already confirmed on the day of the trade. This is the most common look-ahead error in Fibonacci backtests.

**Other look-ahead traps:**
- Using the final swing high of a move before it is confirmed.
- Choosing L and H from a chart you have already seen.
- Treating "the pullback held" as a filter. It is only known afterwards.

**Costs (approximate).** US: 0.05–0.10% each way in spread and slippage. India, delivery: brokerage of zero to ₹20 per order, STT of 0.1% on each side, stamp duty of 0.015% on buys, plus exchange charges and GST. About 0.25–0.35% per round trip before slippage.

**What to test, one at a time:**
- The zone: 38.2–61.8% against one third to two thirds, and against a single level.
- The confluence rule on and off. If results do not change when you drop the Fibonacci zone and keep only the structural level, the ratios add nothing.
- A placebo: replace the Fibonacci ratios with 0.40 and 0.60, or 0.45 and 0.65. A real effect should beat its neighbours.
- The swing rule: 8% and 12% reversals, or 5 and 10 sessions each side.

```
swings = confirmed_swings(close, rule)          # only swings known by day t
for each day t with an up-leg (L, H) where H is confirmed by t:
    rise = H - L
    if rise / L < min_rise or not filters_pass(t): continue
    top, bot = H - zone_shallow * rise, H - zone_deep * rise
    if not has_structure_between(bot, top, t): continue
    if close[t] < H - fail_ratio * rise: discard leg
    if low[t] <= top and low[t] >= bot - buffer and close_in_top_third(t):
        if high[t+1] > high[t]:
            entry = max(open[t+1], high[t])
            stop  = min(low[t], bot) - stop_buffer * atr14[t]
            if (entry - stop) / entry <= max_risk: manage(entry, stop, H, L + ...)
```

**A good test reports:** trades per year; win rate and average win and loss in R; expectancy after costs; worst losing streak; results by year and market regime; and the placebo comparison. If the placebo ratios do as well, the Fibonacci part of the rule is decoration. See [Backtesting](learn-test-backtesting.md).

## 10. Checklist

- [ ] I chose the swing low and high with my fixed rule, before the pullback ended.
- [ ] The rise was large: at least my minimum, in an uptrend, with the market above its 50-day average.
- [ ] A structural level (breakout level, base top, 50-day average) sits inside the 38.2–61.8% zone.
- [ ] The price has not closed beyond my failure level.
- [ ] A reversal bar closed in the top third of its range inside the zone.
- [ ] Buy-stop above its high; stop under the zone with the buffer decided now.
- [ ] The risk is within my maximum; size from my risk %.
- [ ] First target at the old high or 2R; measured move only as a stretch target.
- [ ] No results inside my holding period.

## Further reading

- Robert Rhea, *The Dow Theory*, 1932.
- Robert Edwards and John Magee, *Technical Analysis of Stock Trends*.
- A. J. Frost and Robert Prechter, *Elliott Wave Principle*, 1978.
- Thomas Bulkowski, *Encyclopedia of Chart Patterns*.
- Roy Batchelor and Richard Ramyar, "Magic Numbers in the Dow", working paper, Cass Business School, 2006.
- Carol Osler, "Support for Resistance: Technical Analysis and Intraday Exchange Rates", *Federal Reserve Bank of New York Economic Policy Review*, 2000.
- Carol Osler, "Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis", *Journal of Finance*, 2003.
- Related guides: [Pullback to a moving average](learn-strat-pullback-ma.md), [Pullback to support](learn-strat-pullback-support.md), [Supply and demand](learn-supply-demand.md), [Chart patterns](learn-chart-patterns.md), [Stops and exits](learn-risk-stops-exits.md).
