# Momentum I — where the close sits in its range

**In short**

- These indicators place today's close inside a recent range or band. Near the top of the range reads high; near the bottom reads low. Most are bounded, for example 0 to 100.
- Stochastic, Williams %R, CCI and Bollinger %B are close to the same number. Measured across hundreds of stocks, CCI and %B correlated at 0.98, and Williams %R and Stochastic at 0.92.
- The fast versions (Stochastic RSI, Connors RSI) repeat RSI less, but mostly because they react to one or two days. They swing from one extreme to the other within a week.
- "Overbought" is not rare: Stochastic sat above 80 on about a quarter of all sessions. In a strong stock it is what the advance looks like, not a reason to sell.
- Pick one range reading, learn how often it sits at its extremes on the stock you trade, and take entries and stops from price levels.

This guide covers the bounded momentum readings: Stochastic, Stochastic RSI, Williams %R, CCI, Bollinger %B, the Ultimate Oscillator, Connors RSI and Balance of Power. RSI itself is explained in depth in [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md). The unbounded readings, which measure how fast the price is changing, are in [Momentum II — how fast the price is changing](learn-ind-momentum-rate.md). For how the families fit together, see [Indicators — the map](learn-ind-map.md). The bands themselves are in [Bands and channels](learn-ind-bands-channels.md).

---

## 1. What this family measures

On 8 April 2025 Apple closed at $172.42. Four sessions earlier it had closed at $223.89, so it had lost 23% in four days. Its lowest price of the last 14 sessions was $169.21, touched that same day. The close sat almost on the floor of its recent range.

Every indicator in this guide said so, each in its own units:

| Apple, 8 April 2025 | Reading | Its usual "oversold" line |
|---|---|---|
| RSI (14) | 20.0 | 30 |
| Stochastic %K (14, 3) | 7.3 | 20 |
| Stochastic RSI (14, 14, 3) | 0.0 | 20 |
| Williams %R (14) | −94.3 | −80 |
| CCI (20) | −250 | −100 |
| Bollinger %B (20, 2) | −0.19 | 0 |
| Ultimate Oscillator (7, 14, 28) | 30.9 | 30 |
| Connors RSI (3, 2, 100) | 3.6 | 10 |
| Balance of Power (14) | +0.12 | 0 |

Eight of the nine were at or near their low lines. The ninth, Balance of Power, said the opposite; section 11 explains why. The next day Apple rose 15.3%, and several of these readings jumped to the middle of their scales.

```series
title: Apple, February–June 2025 — Stochastic and Stochastic RSI
from: 2025-02-01
to: 2025-06-30
line: us:AAPL | Apple
line: us:AAPL@stoch.k | Stochastic %K (14, 3) | pane2
line: us:AAPL@stochrsi.k | Stochastic RSI (14, 14, 3) | pane2
mark: 2025-04-08 | Close $172.42
caption: Both lines hit the floor on 8 April 2025. Stochastic RSI (the faster line) then went from 100 on 1 May to 9.2 on 7 May, while the stock moved only about 8%.
```

This family answers one question: where is today's close inside its recent range? The range can be the high and low of the last 14 days, a band around an average, or the range of RSI itself. Because the answer is a position, most of these readings are bounded. That makes fixed lines such as 80 and 20 possible, and it is where the words "overbought" and "oversold" come from.

A position in a range is a description, not a forecast. A close near the top of its range means buyers were in control lately, not that they will stay in control.

## 2. RSI — the reference reading

RSI compares the size of recent up-days with recent down-days, smoothed over 14 days. It runs from 0 to 100. Readings above 70 are called overbought and below 30 oversold. How it is computed, and why a high RSI in a leader means strength, is in [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md).

RSI belongs in this guide because it behaves like a range position. Its closest twin in the measurement below is the close's position inside a Keltner Channel, at 0.98. Every other reading here is compared with it.

## 3. Stochastic %K and %D

**The question:** how close is today's close to the top of the last 14 days' high-low range?

George Lane popularised it. Its idea is that in an uptrend closes tend to gather near the top of the recent range, and in a downtrend near the bottom.

```
fast %K = 100 × (close − lowest low of N days) ÷ (highest high of N days − lowest low of N days)
%K      = 3-day average of fast %K          ("slow" stochastic, the usual default)
%D      = 3-day average of %K               (the signal line)
Defaults: N = 14, smoothing 3 and 3; lines at 80 and 20
```

**Worked example.** Bharat Electronics (BEL) on 4 December 2023, in the middle of a long advance:

| BEL, 4 December 2023 | Value |
|---|---|
| Close | ₹153.55 |
| Highest high, last 14 days | ₹157.50 |
| Lowest low, last 14 days | ₹137.35 |
| Fast %K = 100 × 16.20 ÷ 20.15 | 80.4 |
| %K (3-day average) | 83.4 |
| %D (3-day average of %K) | 70.9 |

The close sat 80% of the way up its 14-day range. %K was above %D, so the position had been rising.

**What it repeats.** Stochastic %K correlated at 0.83 with RSI14 and at 0.92 with Williams %R. It is RSI's information measured a different way.

**How traders use it.** The common signals are %K crossing %D, and %K leaving the zone above 80 or below 20. Lane himself stressed divergences: a new price high that the stochastic does not confirm. The pitfall is frequency. In a trend the line sits pinned near one end for weeks, and the crossings come every few days.

## 4. Why "overbought" in a strong stock is strength

```series
title: Bharat Electronics, 2023 to mid-2024 — Stochastic %K in a long advance
from: 2023-01-01
to: 2024-06-30
line: india:BEL.NS | Bharat Electronics | log
line: india:BEL.NS@stoch.k | Stochastic %K (14, 3) | pane2
caption: BEL rose from ₹100 to ₹306 over these 365 sessions. Stochastic %K was above 80 on 144 of them (39%) and below 20 on only 9.
```

A trader who sold each time BEL's stochastic rose above 80 would have sold 16 times in this run. Three months after those 16 crossings, the stock was higher 14 times.

The reason is in the formula. A reading above 80 means the close is near the top of its recent range. In a stock that keeps rising, the close is near the top of its range most of the time. **A high reading describes the advance; it does not predict its end.**

Across all stocks, the evidence agrees. [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md) measured what followed RSI above 70 over the next month: no fall on average, in the US or in India. The reading is more useful the other way round. In a leader, a pullback that never takes the stochastic below 50 is a shallow pullback. A leader whose readings can no longer reach the top of the range is losing speed.

## 5. Williams %R

**The question:** how far is today's close below the highest high of the last 14 days, as a share of the range?

Larry Williams designed it. It is the fast (unsmoothed) stochastic turned upside down: %R = fast %K − 100. It runs from 0 at the top of the range to −100 at the bottom.

```
%R = −100 × (highest high of N days − close) ÷ (highest high of N days − lowest low of N days)
Default: N = 14; lines at −20 (overbought) and −80 (oversold)
```

**Worked example.** The same BEL bar as in section 3:

| BEL, 4 December 2023 | Value |
|---|---|
| %R = −100 × (157.50 − 153.55) ÷ (157.50 − 137.35) | −19.6 |
| Fast %K from section 3 | 80.4 (= −19.6 + 100) |

**What it repeats.** Williams %R correlated at 0.92 with Stochastic %K. It correlated at 0.94 with the close's position in a Donchian channel, the range between the highest high and lowest low of 20 days. It is a range position and nothing else.

**How traders use it.** Because it is not smoothed, it reaches its extremes sooner and leaves them sooner. Traders use it to time short swings, or as a short-term filter inside a longer trend. The pitfall is the same as for the stochastic, and larger: it is pinned near 0 through most of a strong advance.

## 6. Stochastic RSI

**The question:** is RSI near the top or the bottom of its own range over the last 14 days?

Tushar Chande and Stanley Kroll described it. It applies the stochastic formula to RSI instead of to price. That makes an indicator of an indicator, and a very fast one.

```
StochRSI = 100 × (RSI − lowest RSI of N days) ÷ (highest RSI of N days − lowest RSI of N days)
K = 3-day average of StochRSI; D = 3-day average of K
Defaults: RSI 14, N = 14, smoothing 3 and 3; lines at 80 and 20
```

**Worked example.** Apple in early May 2025:

| Apple | RSI (14) | Stochastic RSI K | Stochastic %K |
|---|---|---|---|
| 1 May 2025 | 54.8 | 100.0 | 96.0 |
| 7 May 2025 | 41.5 | 9.2 | 32.6 |

RSI moved 13 points, from slightly above its middle to slightly below. Stochastic RSI moved 91 points, from the top of its scale to the bottom. On 1 May, RSI was only 54.8, yet Stochastic RSI read "overbought": RSI was at its highest of the last 14 days, which is all the formula asks.

**What it repeats.** It correlated only 0.54 with RSI14. That looks like new information. Mostly it is speed: its closest twin was Stochastic %K, at 0.79.

**How traders use it.** It is used for short-term timing, for example buying when it turns up from below 20 inside an uptrend. The pitfall is noise. Across the sample, it sat above 80 on about 27% of sessions. It sat below 20 on about 24%. In BEL's advance, which tripled the price, it was below 20 on one session in five.

## 7. CCI — the Commodity Channel Index

**The question:** how far is today's typical price from its 20-day average, measured in units of its usual distance?

Donald Lambert introduced it in 1980, for commodities. The typical price is the average of the high, low and close.

```
typical price (TP) = (high + low + close) ÷ 3
CCI = (TP − 20-day average of TP) ÷ (0.015 × mean deviation of TP over 20 days)
mean deviation = the average distance of each TP from the 20-day average
Default: 20 days; lines at +100 and −100
```

**Worked example.** Apple on 8 April 2025:

| Apple, 8 April 2025 | Value |
|---|---|
| Typical price, (190.34 + 169.21 + 172.42) ÷ 3 | 177.32 |
| 20-day average of the typical price | 212.30 |
| Mean deviation | 9.33 |
| CCI = (177.32 − 212.30) ÷ (0.015 × 9.33) | −250 |

The constant 0.015 only sets the scale. It is usually said to put most readings between −100 and +100. On the sample here, about 58% of sessions were inside that band; CCI was above +100 on 23% of them.

**What it repeats.** CCI and Bollinger %B correlated at 0.98, in both markets. They are the same number on different scales. Both ask how far the close is from its 20-day average, measured in its own recent spread. CCI uses the mean deviation; %B uses the standard deviation.

**How traders use it.** Lambert's own use was to buy when CCI rose above +100, as the start of a strong move. Many traders now use it the other way, buying below −100. Those are opposite rules on the same reading, which says something about how firm either one is. CCI is unbounded, so a reading of ±300 is possible on a gap.

## 8. Bollinger %B

**The question:** where is the close between the lower and upper Bollinger Bands?

```
%B = (close − lower band) ÷ (upper band − lower band)
Bands: 20-day average ± 2 standard deviations
0 = on the lower band, 0.5 = on the average, 1 = on the upper band
```

On 8 April 2025 Apple's lower band was $183.3 and it closed at $172.42, so %B was −0.19: below the band. On 4 December 2023 BEL's %B was 1.22: above the upper band. The bands are explained in [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md). A trade built on low %B readings is tested in [Bollinger band reversion](learn-strat-bollinger-reversion.md).

**What it repeats.** CCI, at 0.98, and RSI14, at 0.89. Use %B or CCI, not both.

## 9. Ultimate Oscillator

**The question:** over three lengths at once, how much of each day's range was buying pressure?

Larry Williams designed it to reduce the false signals of one-length oscillators. Each day's **buying pressure** is the close minus the lower of today's low and yesterday's close. The **true range** runs from that same low to the higher of today's high and yesterday's close.

```
average(n) = sum of buying pressure over n days ÷ sum of true range over n days
UO = 100 × (4 × average(7) + 2 × average(14) + average(28)) ÷ 7
Defaults: 7, 14 and 28 days, weighted 4 : 2 : 1; lines at 70 and 30
```

**Worked example.** Apple on 8 April 2025:

| Apple, 8 April 2025 | Value |
|---|---|
| Average, 7 days | 0.268 |
| Average, 14 days | 0.344 |
| Average, 28 days | 0.403 |
| UO = 100 × (4 × 0.268 + 2 × 0.344 + 0.403) ÷ 7 | 30.9 |

The 28-day term still held weeks of normal trading, so it pulled the reading up. On the same day RSI was 20.0 and Stochastic 7.3. The Ultimate Oscillator was the least extreme reading in the table in section 1.

**What it repeats.** It correlated 0.75 with RSI14 in the US and 0.71 in India. Its closest twins were the Keltner position and Williams %R, near 0.79. Blending three lengths makes it slower and less extreme. It reached 70 on only about 2.5% of US sessions.

**How traders use it.** Williams' rules were built on divergence. A buy needs a new price low that the oscillator does not confirm, with the oscillator below 30, and then a rise above its high between the two lows. Signals are rare by design.

## 10. Connors RSI

**The question:** after a short burst of selling or buying, how stretched is the stock over the next few days?

Larry Connors built it for short-term mean reversion: buying sharp dips and selling sharp pops. It averages three readings, each from 0 to 100.

```
Connors RSI = (RSI(3) of the close + RSI(2) of the up/down streak + percent rank of today's 1-day change) ÷ 3
streak       = consecutive up closes (+1, +2 …) or down closes (−1, −2 …)
percent rank = share of the last 100 one-day changes smaller than today's
Defaults: 3, 2, 100; lines at 90 and 10
```

**Worked example.** Apple across one day:

| Apple | 3-day RSI | Streak | Streak RSI (2) | Rank of 1-day change | Connors RSI |
|---|---|---|---|---|---|
| 8 April 2025 (−5.0%) | 3.1 | 4 down | 5.6 | 2 | 3.6 |
| 9 April 2025 (+15.3%) | 60.2 | 1 up | 81.7 | 100 | 80.6 |

One day moved it from 3.6 to 80.6. The percent-rank term alone jumped from 2 to 100, because the gain was the biggest of the last 100 days.

**What it repeats.** It correlated only 0.46 with RSI14; its closest twin was Williams %R, at 0.58. It is the least redundant reading in this family. That is because it measures the last two or three days, which RSI14 barely sees.

**How traders use it.** It is a short-term trade signal, usually combined with a long-term trend filter such as the 200-day average. Readings below 10 are bought; readings above 90 are sold. How that kind of trade behaves is in [RSI(2) mean reversion](learn-strat-rsi2.md). The pitfall: a reading that changes completely in one day suits holding periods of days, not weeks.

## 11. Balance of Power

**The question:** inside each bar, did the close finish above or below the open, as a share of the bar's range?

Igor Livshin described it. A bar that opens on its low and closes on its high scores +1. One that opens on its high and closes on its low scores −1.

```
BOP (one bar) = (close − open) ÷ (high − low)
BOP           = 14-day average of that
Default: 14; line at 0
```

**Worked example.** Apple's four-day fall in April 2025:

| Apple | Opening gap | Close − open | High − low | BOP for the bar |
|---|---|---|---|---|
| 3 April 2025 | −8.2% | −2.35 | 6.24 | −0.38 |
| 4 April 2025 | −4.6% | −5.51 | 12.54 | −0.44 |
| 7 April 2025 | −5.9% | +4.26 | 19.53 | +0.22 |
| 8 April 2025 | +2.9% | −14.28 | 21.13 | −0.68 |

On 8 April 2025, after a 23% fall, the average was still positive (+0.12). Most of the loss came in overnight gaps, and BOP ignores gaps. It sees only what happened between the open and the close.

**What it repeats.** It correlated 0.68 with RSI14 in the US and 0.70 in India. Its closest twin was the Vortex indicator, at 0.77. It is a bar-by-bar reading of buying pressure, not a position in a range.

**How traders use it.** As a confirmation: an advance in which most bars close above their opens is being bought during the session. The pitfalls are gaps, as above, and bars with a tiny range, where a small move gives an extreme score.

## 12. The family side by side

| Indicator | Question it answers | Defaults | Mostly repeats | Typical use |
|---|---|---|---|---|
| RSI | Size of up-days against down-days | 14; 70/30 | Keltner position (0.98) | Warning flags; see the core guide |
| Stochastic %K/%D | Close's position in the 14-day high-low range | 14, 3, 3; 80/20 | Williams %R (0.92) | %K/%D crossings; pullback depth in a trend |
| Williams %R | The same, unsmoothed, upside down | 14; −20/−80 | Donchian position (0.94) | Short-swing timing |
| Stochastic RSI | RSI's position in its own 14-day range | 14, 14, 3, 3; 80/20 | Stochastic %K (0.79) | Very short-term timing |
| CCI | Typical price's distance from its average, in mean deviations | 20; ±100 | Bollinger %B (0.98) | Breakouts above +100, or dips below −100 |
| Bollinger %B | Close's position between the bands | 20, 2; 1/0 | CCI (0.98) | Band touches; reversion trades |
| Ultimate Oscillator | Buying pressure over three lengths | 7, 14, 28; 70/30 | Keltner position, Williams %R (≈0.79) | Divergence signals, rarely |
| Connors RSI | Stretch after a 1–3 day burst | 3, 2, 100; 90/10 | Williams %R (0.58) | Short-term mean reversion |
| Balance of Power | Close against open within each bar | 14; 0 | Vortex (0.77) | Confirming intraday buying |

## 13. What the evidence says

### Most of these are one number

> **Method.** US: 300 stocks picked at random; India: all 147 that qualify. Each had at least 1,500 sessions since 2015 and a high median daily traded value. Every indicator used its default settings on daily bars. Correlations were measured day by day within each stock over 2015 to October 2026; the table shows the median across stocks. The stocks are ones listed today, so survivorship bias is possible.

| Median correlation (US / India) | RSI14 | 14-day % change | Distance from 50-day | Closest twin |
|---|---|---|---|---|
| Stochastic %K | 0.83 / 0.83 | 0.78 / 0.79 | 0.64 / 0.64 | Williams %R (0.92) |
| Williams %R | 0.84 / 0.83 | 0.74 / 0.74 | 0.61 / 0.61 | Donchian position (0.94 / 0.93) |
| CCI | 0.87 / 0.87 | 0.75 / 0.77 | 0.66 / 0.67 | Bollinger %B (0.98) |
| Bollinger %B | 0.89 / 0.89 | 0.77 / 0.78 | 0.67 / 0.68 | CCI (0.98) |
| Ultimate Oscillator | 0.75 / 0.71 | 0.65 / 0.61 | 0.58 / 0.53 | Keltner position (0.79) / Williams %R (0.78) |
| Stochastic RSI | 0.54 / 0.53 | 0.55 / 0.54 | 0.26 / 0.25 | Stochastic %K (0.79) |
| Connors RSI | 0.46 / 0.46 | 0.32 / 0.32 | 0.28 / 0.28 | Williams %R (0.58) |
| Balance of Power | 0.68 / 0.70 | 0.68 / 0.72 | 0.53 / 0.56 | Vortex (0.77) |

```series
title: Apple, 2025 — CCI and Bollinger %B
from: 2025-01-01
to: 2025-12-31
line: us:AAPL@cci.cci | CCI (20)
line: us:AAPL@bbpct.pb | Bollinger %B (20, 2) | right
caption: Two indicators, one line. For Apple in 2025 the two correlated at 0.99. Both measure the close's distance from its 20-day average in units of its recent spread.
```

- **Stochastic, Williams %R, CCI and %B form one cluster** with RSI. Two of them on one chart give one opinion twice. The two markets give almost the same table.
- **The faster readings repeat less, but they are noisier.** Stochastic RSI and Connors RSI react to the last few days. Their lower correlation is mostly a different time scale, not a different question.
- **Balance of Power is the one different idea**: it reads each bar's close against its open. It still correlated 0.68 with RSI, because days that close above their open tend to be up days.

### "Overbought" is common, and its frequency depends on the indicator

The same line means very different things on different indicators. Here is how often each reading sat beyond its usual lines, on the same sample:

| Share of sessions (median stock, US / India) | Above the high line | Below the low line |
|---|---|---|
| RSI (70 / 30) | 6.2% / 6.8% | 3.7% / 3.7% |
| Bollinger %B (1 / 0) | 6.5% / 7.0% | 5.6% / 5.2% |
| Stochastic %K (80 / 20) | 23.9% / 21.0% | 17.4% / 17.1% |
| Williams %R (−20 / −80) | 25.9% / 23.1% | 19.6% / 19.0% |
| CCI (+100 / −100) | 23.4% / 23.4% | 18.5% / 18.3% |
| Stochastic RSI (80 / 20) | 26.9% / 26.1% | 24.3% / 25.2% |
| Ultimate Oscillator (70 / 30) | 2.5% / 0.7% | 1.8% / 1.9% |
| Connors RSI (90 / 10) | 2.4% / 2.6% | 2.5% / 2.6% |

A Stochastic above 80 happens about one day in four. An RSI above 70 happens about one day in sixteen. Treating both as the same "overbought" signal mixes a common event with a rare one.

### Published research

- **Nearness to the high has been a sign of strength.** George and Hwang (2004) found that US stocks trading close to their 52-week high went on to do better than stocks far from it. That is a range position over a year, compared across stocks. It points the opposite way to "near the top means sell".
- **Very short-term moves have tended to reverse.** Jegadeesh (1990) found that individual US stocks' returns over one month tended to reverse the next month. Lehmann (1990) found the same for weekly returns. This is the effect that short-term readings such as Connors RSI try to use.
- **No study is cited here for Stochastic, %R, CCI or the Ultimate Oscillator as a stand-alone rule.** Tests of single-indicator rules have mostly not survived once costs and the number of rules tried are allowed for; see [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md).

**Limits.** The sample holds today's listed stocks only, so stocks that collapsed and were delisted are missing. A correlation measures overlap, not predictive power: two readings can be identical and both useless. No costs are counted, and the fast readings change their verdict often.

## 14. Checklist

- [ ] Do I have more than one of Stochastic, Williams %R, CCI, %B and RSI on my chart? Keep one.
- [ ] Do I know how often my reading sits above its "overbought" line on this stock? About a quarter of the time is normal for Stochastic.
- [ ] Is the stock in a strong uptrend? Then a high reading is the trend, not a sell signal.
- [ ] In a leader's pullback, how low did the reading go? A shallow dip that holds above the middle is strength.
- [ ] Am I using a fast reading (Stochastic RSI, Connors RSI) for a trade I plan to hold for weeks? Its verdict changes in a day or two.
- [ ] Is my entry and stop tied to a price level, not just to the oscillator?

## Further reading

- Tushar Chande and Stanley Kroll, *The New Technical Trader* (1994) — Stochastic RSI from its authors.
- John Bollinger, *Bollinger on Bollinger Bands* (2001) — the bands and %B.
- Larry Connors and Cesar Alvarez, *Short Term Trading Strategies That Work* — short-term RSI and mean reversion.
- George and Hwang, "The 52-Week High and Momentum Investing" (*Journal of Finance*, 2004).
- Jegadeesh, "Evidence of Predictable Behavior of Security Returns" (*Journal of Finance*, 1990).
- Lehmann, "Fads, Martingales, and Market Efficiency" (*Quarterly Journal of Economics*, 1990).
