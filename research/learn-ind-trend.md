# Trend indicators — DMI and ADX, Aroon, Vortex, Parabolic SAR, Supertrend, Chandelier Exit, Ichimoku

**In short**

- Trend indicators come in two kinds. Some turn direction and strength into a number (DMI and ADX, Aroon, Vortex). Others draw a trailing line that flips the trend between up and down (Parabolic SAR, Supertrend, Chandelier Exit, the Ichimoku cloud).
- ADX is the one reading here that repeats nothing directional. Its median correlation with RSI was about 0.1, because it measures how steady a move is, up or down.
- The directional readings are mostly momentum. +DI minus −DI moved with RSI14 at 0.94, and the Vortex spread with the 14-day % change at 0.88.
- The trailing lines are slower, yes/no versions of the same momentum: their up/down state correlated 0.58–0.70 with RSI14. A "trend" label does not make a reading independent.
- Use one of them as a filter or a stop, not several as a vote. Each flips far more often than a trend really turns.

This guide covers the indicators most charting packages file under "Trend". ADX itself is explained in depth in [Indicators — trend and volatility: moving averages, ATR and ADX](learn-price-indicators.md); here it gets a summary. Momentum readings are in [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md) and [Momentum II — how fast the price is changing](learn-ind-momentum-rate.md). How all the families fit together is in [Indicators — the map](learn-ind-map.md). For ATR trailing stops measured as exits, see [Stops and exits — where a trade is wrong, and how it ends](learn-risk-stops-exits.md).

---

## 1. What this family measures

Microsoft rose from a close of $354.56 on 8 April 2025 to a high of $555 at the end of July. By the end of March 2026 it had fallen to $370. Here is what every trend indicator in this guide said on two days, one in each move.

| Microsoft (MSFT) | 31 Jul 2025 | 31 Mar 2026 |
|---|---|---|
| Close | $533.50 | $370.17 |
| RSI14 (for comparison) | 81.7 | 36.1 |
| ADX14 | 47.8 | 32.8 |
| +DI / −DI (14) | 52.2 / 8.5 | 17.8 / 36.1 |
| Aroon Up / Down (14) | 100 / 0 | 0 / 92.9 |
| Vortex VI+ / VI− (14) | 1.12 / 0.69 | 0.62 / 1.21 |
| Parabolic SAR | $502.1, below the price | $385.8, above the price |
| Supertrend (10, 3) | Up; line at $513.8 | Down; line at $384.8 |
| Chandelier long exit (22, 3) | $530.3; close above | $384.8; close below |
| Ichimoku cloud | $422.5–475.5; close above | $418.4–437.7; close below |

Every indicator agreed: up in July, down in March. In a clean trend they always do. That is the first lesson of this family: **in a clear trend you do not need them, and in a messy market they disagree**.

On 27 October 2026 Microsoft closed at $531.33 after a choppy month. The Aroon Oscillator read −57 (down), Parabolic SAR sat above the price (down), Supertrend was up, and +DI was above −DI (up). Four indicators, two answers.

The family answers two questions. **Which way, and how strongly?** DMI, ADX, Aroon and Vortex give a number every day. **Is the trend intact, and where would I get out?** Parabolic SAR, Supertrend, the Chandelier Exit and the Ichimoku cloud draw a line beside the price; the trend "flips" when the price crosses it.

```series
title: Microsoft, 2025–2026 — Supertrend (10, 3) flipping between up and down
from: 2025-01-01
to: 2026-10-27
tf: D
line: us:MSFT | Microsoft
line: us:MSFT@st.up | Supertrend, up
line: us:MSFT@st.down | Supertrend, down
mark: 2025-07-31 | up: line at $513.8
mark: 2026-01-29 | results gap: flips down
mark: 2026-03-31 | down: line at $384.8
caption: The line sits under the price in an uptrend and over it in a downtrend. It caught the April–August 2025 rise and the 2026 fall, and flipped 11 times in under two years. Most of those flips came in the sideways stretches.
```

## 2. DMI and ADX — direction and steadiness

**The question.** +DI and −DI ask which way the recent range has been stretching: up or down. ADX asks how one-sided that has been, whichever way it was.

Welles Wilder published the Directional Movement Index in 1978; the full construction is in [the core indicators guide](learn-price-indicators.md).

```
+DM = today's high − yesterday's high   (if larger than the down move and > 0, else 0)
−DM = yesterday's low − today's low     (if larger than the up move and > 0, else 0)
+DI = 100 × Wilder average of +DM ÷ ATR,   −DI the same with −DM      (14 bars)
DX  = 100 × |+DI − −DI| ÷ (+DI + −DI)
ADX = Wilder average of DX                                           (14 bars)
```

Defaults: 14 bars. ADX below about 20 is read as no trend, above 25 as a trend, above 40 as a strong and often late one.

**Worked example.** TCS, India's largest IT services company, fell from about ₹3,225 in early February 2026 to ₹2,409 by mid-March. ADX rose as it fell.

| TCS (TCS.NS) | 3 Feb 2026 | 16 Mar 2026 |
|---|---|---|
| Close | ₹3,225.30 | ₹2,409.20 |
| +DI | 37.7 | 10.8 |
| −DI | 19.9 | 43.1 |
| ADX | 14.4 | 40.7 |
| RSI14 | 54.4 | 18.4 |

An ADX of 40.7 in a fall reads exactly like an ADX of 40.7 in a rise. The direction is in the DI lines: −DI far above +DI.

```series
title: TCS, 2026 — ADX rises in a fall just as it does in a rise
from: 2025-12-01
to: 2026-10-27
tf: D
line: india:TCS.NS | TCS
line: india:TCS.NS@adx.adx | ADX (14) | pane2
line: india:TCS.NS@adx.pdi | +DI | pane2
line: india:TCS.NS@adx.mdi | −DI | pane2
mark: 2026-02-03 | ADX 14
mark: 2026-03-16 | ADX 41
caption: Through February and March −DI stayed far above +DI, and ADX climbed past 40. ADX says "one-sided"; only the DI lines say which side. By mid-April, with the fall paused, ADX was back near 27.
```

**What it repeats.** ADX repeats almost nothing directional. Its median correlation with RSI14 was 0.07 in the US and 0.13 in India. Its closest twin was Bollinger BandWidth, at about 0.4: both rise when the price moves far in one direction.

Within one stock, ADX can still look directional. Since 2025, Microsoft's ADX correlated +0.44 with its RSI, because its steadiest trend was up. TCS's correlated −0.34, because its steadiest trend was down. Across many stocks the two cancel out.

The spread +DI − −DI is another matter. It correlated **0.94 with RSI14** in both markets. A "+DI crosses above −DI" signal is close to "RSI crosses 50".

**How traders use it.** ADX is a filter: trend-following setups wait for ADX above 20 or 25, and range trades want it low. Its pitfall is lag. Two rounds of 14-bar smoothing make it rise well after a trend starts, and peak after the move is mature.

## 3. Aroon and the Aroon Oscillator — how recent was the high?

**The question.** How many bars ago did the stock make its highest high, and its lowest low, of the window? A trend makes fresh highs often; a range does not.

Tushar Chande introduced Aroon in 1995.

```
Aroon Up   = 100 × (N − bars since the highest high of the last N+1 bars) ÷ N
Aroon Down = 100 × (N − bars since the lowest low  of the last N+1 bars) ÷ N
Aroon Oscillator = Aroon Up − Aroon Down        (range −100 to +100)
```

Usual settings are 14 or 25 bars. Aroon Up 100 means today made the high of the window. Up above 70 with Down below 30 is the usual reading of an uptrend.

**Worked example.** On 31 July 2025 Microsoft made its 14-bar high that day and its 14-bar low exactly 14 bars before. Aroon Up was 100, Down 0, and the Oscillator +100. On 31 March 2026 the high was 14 bars old and the low a day old. Aroon Up was 0 and Down 92.9, so the Oscillator read −92.9.

**What it repeats.** The Aroon Oscillator correlated **0.85 with the Vortex spread** and 0.73 with RSI14 in the US. It is momentum counted in bars rather than in price.

**Pitfalls.** Aroon moves in steps of 100 ÷ N, and jumps when an old extreme leaves the window. One spike high can hold Aroon Up near 100 for days even after the price slips. It ignores how far the price moved: a new high by one cent counts the same as a new high by 10%.

## 4. Vortex — upward reach against downward reach

**The question.** Over the last N bars, did the highs reach further above the previous lows than the lows reached below the previous highs?

Etienne Botes and Douglas Siepman published the Vortex Indicator in 2010.

```
VM+ = |today's high − yesterday's low|
VM− = |today's low − yesterday's high|
VI+ = sum of VM+ over N bars ÷ sum of true range over N bars
VI− = sum of VM− over N bars ÷ sum of true range over N bars      (N = 14)
```

The usual signal is a crossing: VI+ above VI− reads as up, below as down. The spread VI+ − VI− summarises it in one number.

**Worked example.** On 31 July 2025 Microsoft's VI+ was 1.12 and VI− 0.69. On 31 March 2026 they were 0.62 and 1.21.

**What it repeats.** The Vortex spread correlated **0.88 with the 14-day % change** in the US and 0.91 in India. It is a 14-day price change, measured in ranges. It also crossed very often: 49 times on Microsoft between January 2025 and October 2026.

```series
title: Microsoft, 2025–2026 — RSI14 and +DI minus −DI tell one story
from: 2025-01-01
to: 2026-10-27
tf: D
line: us:MSFT | Microsoft
line: us:MSFT@rsi14 | RSI 14 | pane2
line: us:MSFT@adx.pdi - us:MSFT@adx.mdi | +DI − −DI | pane2 zero
caption: For Microsoft since 2025 the two lines correlated at 0.97. A "trend" label on the second does not make it a second opinion.
```

## 5. Trailing lines — Parabolic SAR, Supertrend, Chandelier Exit and the Ichimoku cloud

These four draw a line beside the price. While the price stays on one side, the trend is "up" (or "down"). They were designed as stops: the line is where you would get out.

How often did each one change its mind? Counted on Microsoft over the same 22 months:

| Microsoft, Jan 2025 – Oct 2026 | Times the up/down state changed |
|---|---|
| Parabolic SAR (0.02, 0.02, 0.2) | 38 |
| +DI above or below −DI (14) | 35 |
| Close against the Ichimoku cloud (above, inside, below) | 36 |
| Close above or below the Chandelier long exit (22, 3) | 29 |
| Aroon Oscillator above or below 0 (14) | 29 |
| Vortex VI+ above or below VI− (14) | 49 |
| Supertrend (10, 3) | 11 |

Microsoft had only a handful of real trends in that time. Only Supertrend, the widest of these lines, came close to that count.

### 5.1 Parabolic SAR

**The question.** If I am in this trend, where is my stop today? SAR stands for "stop and reverse": when the price hits it, the system reverses from long to short.

Wilder published it in the same 1978 book as ADX.

```
SAR(tomorrow) = SAR(today) + AF × (EP − SAR(today))
EP = extreme point: the highest high of the current up move (lowest low in a down move)
AF = acceleration factor: starts at 0.02, +0.02 at each new extreme, at most 0.20
In an up move the SAR may not rise above the previous two lows.
When the price trades through the SAR, it flips: SAR = the old EP, AF back to 0.02.
```

**Worked example.** On 31 July 2025 Microsoft's SAR was $502.1, under a close of $533.50. On 31 March 2026 it was $385.8, over a close of $370.17.

**What it repeats.** Its up/down state correlated 0.58 with RSI14, and most closely with the Stochastic (0.73). It is a fast, short-term reading.

**Pitfalls.** The SAR speeds up every time the trend makes a new extreme, so in a long trend it closes in on the price. It is always in the market, long or short, so in a range it flips back and forth. It works best in a steady trend and worst in a range.

### 5.2 Supertrend

**The question.** Has the price moved against the trend by more than a few ATRs? ATR, the average true range, is a stock's typical daily move (see [the core indicators guide](learn-price-indicators.md)).

```
upper band = (high + low) ÷ 2 + 3 × ATR(10)
lower band = (high + low) ÷ 2 − 3 × ATR(10)
In an uptrend the lower band can only rise; the trend flips down when the close falls below it.
In a downtrend the upper band can only fall; the trend flips up when the close rises above it.
```

Defaults: ATR of 10 bars, a multiple of 3. Its author is not well documented.

**Worked example.** Taking every Supertrend "up" period on Microsoft as a long trade, close to close, gives this. It is an illustration of how the line behaves, not a test.

| Supertrend up | Turned down | Result |
|---|---|---|
| 22 Jan 2025, $446.20 | 30 Jan 2025, $415.00 | −7.0% |
| 29 Apr 2025, $394.00 | 19 Aug 2025, $509.80 | +29.4% |
| 6 Oct 2025, $528.60 | 31 Oct 2025, $517.80 | −2.0% |
| 27 Jan 2026, $480.60 | 29 Jan 2026, $433.50 | −9.8% |
| 14 Apr 2026, $393.10 | 5 Jun 2026, $416.70 | +6.0% |
| 15 Jul 2026, $395.60 | still up on 27 Oct 2026, $531.33 | +34.3% |

Two big trends paid for three losses. The worst loss, −9.8%, came from a results gap two days after the flip up: no line drawn in ATRs protects against a gap.

**What it repeats.** Its state correlated 0.69 with RSI14 in the US and 0.67 in India. Its closest twin was the True Strength Index (0.72), a smoothed momentum reading.

### 5.3 Chandelier Exit

**The question.** How far below the highest high can the price fall before the trend is over? The stop hangs from the high like a chandelier from the ceiling.

Chuck LeBeau designed it as a trailing exit.

```
long exit  = highest high of the last 22 bars − 3 × ATR(22)
short exit = lowest low of the last 22 bars + 3 × ATR(22)
```

**Worked example.** On 31 July 2025 Microsoft gapped up to a high of $555.45 after results, then closed at $533.50.

| Microsoft, 31 Jul 2025 | Value |
|---|---|
| Highest high of 22 bars | $555.45 |
| ATR (22) | $8.38 |
| Long exit = 555.45 − 3 × 8.38 | $530.30 |
| Close | $533.50, just $3.20 above the exit |

The close sat only 0.4 ATR above the stop, on a day the stock was up 4%. A wide-ranging gap day lifts the 22-bar high at once, and the exit with it. As drawn, the line can also fall when ATR widens or an old high leaves the window; used as a stop, traders only ever raise it.

**What it repeats.** "Close above the long exit" correlated 0.70 with RSI14. Its closest twin was the close's position in its 20-day Donchian channel (0.74). In [Stops and exits](learn-risk-stops-exits.md), a trailing stop 3 ATRs under the highest close sold many trades on ordinary pullbacks. It did worse than a wider trend exit on the same entries.

### 5.4 Ichimoku Kinko Hyo — the cloud

**The question.** Is the price above or below the middle of its recent ranges, and is that middle rising? "Ichimoku kinko hyo" means roughly "a one-glance equilibrium chart".

Goichi Hosoda, a Japanese newspaper writer, developed it over many years and published it in the 1960s. It draws five lines.

```
conversion line (tenkan-sen) = (9-bar high + 9-bar low) ÷ 2
base line (kijun-sen)        = (26-bar high + 26-bar low) ÷ 2
leading span A               = (conversion + base) ÷ 2,           drawn 26 bars ahead
leading span B               = (52-bar high + 52-bar low) ÷ 2,    drawn 26 bars ahead
lagging span (chikou)        = today's close,                     drawn 26 bars back
cloud (kumo)                 = the area between span A and span B
```

The settings 9, 26 and 52 are often explained by the six-day Japanese trading week of the time: a week and a half, a month, two months.

**Worked example.** Because the spans are drawn 26 bars ahead, the cloud under today's bar was computed 26 sessions earlier.

| Microsoft | 31 Jul 2025 | 31 Mar 2026 |
|---|---|---|
| Cloud computed on | 24 Jun 2025 | 23 Feb 2026 |
| Span A / span B | $475.5 / $422.5 | $418.4 / $437.7 |
| Close | $533.50, above the cloud | $370.17, below the cloud |
| Conversion / base line | $528.1 / $522.1 | $374.4 / $384.7 |

A close above the cloud reads as an uptrend, below as a downtrend, inside as no trend. A thick cloud is read as strong support or resistance, a thin one as weak.

**What it repeats.** "Close against the cloud" correlated 0.76 with the distance from the 50-day average and 0.70 with RSI14. Every line is a midpoint of a high–low range, so the cloud is a slow moving average drawn differently.

**Pitfalls.** The forward shift makes the cloud look predictive. It is not: everything in it was known 26 bars ago. The many lines also invite reading crossings everywhere, which multiplies signals rather than information.

## 6. Two more: the Chande Trend Meter and the RS line

**The Chande Trend Meter** is a composite score from 0 to 100, attributed to Tushar Chande. It blends several trend readings over different lookbacks into one number. High readings describe a strong uptrend, low ones a weak or falling stock. Its exact formula has not been published, so it is described here, not computed. Since it is built from trend and momentum readings, expect it to repeat them.

**The RS line** divides a stock's price by an index. A rising line means the stock is beating the market, whatever the market does. It is a trend indicator of *relative* performance, and it answers something none of the others here can: is this stock a leader? It was not part of the overlap measurement below. The full treatment is in [Relative strength — which stocks are beating the market, and what that is worth](learn-price-rs.md).

## 7. The family side by side

| Indicator | Question it answers | Defaults | Mostly repeats | Typical use |
|---|---|---|---|---|
| ADX | Is the move one-sided, up or down? | 14 | Nothing directional; BandWidth (0.4) | Trend filter: above 20–25 |
| +DI / −DI | Which way has the range been stretching? | 14 | RSI14 (0.94) | Direction; crossings |
| Aroon / Aroon Oscillator | How recent are the high and the low? | 14 or 25 | Vortex spread (0.85) | Fresh highs = trend |
| Vortex | Is upward reach larger than downward? | 14 | 14-day % change (0.88) | Crossings |
| Parabolic SAR | Where is the stop, tightening with time? | 0.02 / 0.02 / 0.2 | Stochastic (0.73) | Trailing stop in trends |
| Supertrend | Has the price reversed by 3 ATRs? | 10, 3 | TSI (0.72) | Trend state; trailing stop |
| Chandelier Exit | Has it fallen 3 ATRs from the high? | 22, 3 | Donchian position (0.74) | Trailing stop |
| Ichimoku cloud | Above or below the middle of past ranges? | 9 / 26 / 52 | Distance from 50-day (0.76) | Trend filter; zones |
| Chande Trend Meter | All of the above in one score | Not published | Not measured | Ranking trend strength |
| RS line | Is it beating the index? | Price ÷ index | Not measured | Choosing leaders |

## 8. What the evidence says

**Measured here: overlap.** Each indicator was correlated, day by day within each stock, with six reference readings.

> **Method.** 300 random US stocks and all 147 qualifying Indian stocks, each with at least 1,500 sessions since 2015 and a median daily traded value of at least $10 million or ₹50 crore. Every indicator at its default settings on daily bars, 2015 to October 2026. Correlations measured within each stock; the table shows the median across stocks. Today's listed stocks only, so some survivorship bias.

| Median correlation (US / India) | RSI14 | 14-day % change | Distance from 50-day | ATR % | ADX | Closest twin (US) |
|---|---|---|---|---|---|---|
| ADX (14) | 0.07 / 0.13 | −0.01 / 0.08 | 0.02 / 0.12 | 0.11 / 0.20 | 1 | Bollinger BandWidth (0.41) |
| +DI − −DI (14) | 0.94 / 0.94 | 0.80 / 0.81 | 0.86 / 0.87 | −0.27 / −0.23 | 0.06 / 0.13 | RSI14 (0.94) |
| Aroon Oscillator (14) | 0.73 / 0.74 | 0.76 / 0.77 | 0.60 / 0.61 | −0.17 / −0.15 | 0.03 / 0.07 | Vortex spread (0.85) |
| VI+ − VI− (14) | 0.86 / 0.86 | 0.88 / 0.91 | 0.71 / 0.73 | −0.21 / −0.18 | 0.05 / 0.09 | ATR-band position (0.90) |
| Supertrend up/down (10, 3) | 0.69 / 0.67 | 0.57 / 0.56 | 0.66 / 0.67 | −0.21 / −0.17 | 0.04 / 0.07 | TSI (0.72) |
| Parabolic SAR up/down | 0.58 / 0.58 | 0.53 / 0.53 | 0.40 / 0.39 | −0.10 / −0.09 | 0.01 / 0.03 | Stochastic %K (0.73) |
| Close above Chandelier long exit | 0.70 / 0.68 | 0.62 / 0.61 | 0.59 / 0.58 | −0.23 / −0.21 | −0.15 / −0.11 | Donchian position (0.74) |
| Close against the Ichimoku cloud | 0.70 / 0.70 | 0.48 / 0.49 | 0.76 / 0.76 | −0.28 / −0.18 | 0.01 / 0.07 | TSI (0.80) |

What it shows:

- **ADX stands apart.** It is the only trend reading that is not a version of momentum. It pairs naturally with one momentum reading, because the two answer different questions.
- **The directional numbers are momentum.** +DI − −DI is nearly RSI. Vortex is nearly the 14-day change. Aroon sits between them.
- **The trailing lines are slow, yes/no momentum.** Their 0.58–0.70 with RSI14 understates the overlap. A yes/no reading cannot correlate perfectly with a smooth one; about 0.8 is the practical ceiling.
- **The two markets agree** closely: the largest gap in the table is about 0.1, and none changes the picture.

**Published research.** Wilder presented his indicators as rules with examples, not as statistical tests. Published tests of these exact indicators on stocks are few. The wider evidence on simple technical rules is mixed. Brock, Lakonishok and LeBaron (1992) found moving-average and breakout rules had predictive power on the Dow up to 1986. Sullivan, Timmermann and White (1999) showed the best rule did not hold up afterwards, once the number of rules tried was allowed for.

Park and Irwin's survey (2007) found many positive studies, along with common flaws: many rules tried on the same data, costs ignored, rules chosen after the fact. The strongest evidence for trend following is time-series momentum. Moskowitz, Ooi and Pedersen (2012) found that a market's own past-year return predicted its next month's across many futures markets. That is diversified futures over months, not one stock's ADX or Supertrend.

**Limits.** Correlation shows overlap, not predictive power: two readings can be the same number and both useless. The sample is today's listed stocks, and nothing here includes costs. The Microsoft and TCS examples were chosen to show the indicators clearly, so they are not typical.

## 9. Checklist

- [ ] Which question am I asking: which way, how steady, or where do I get out?
- [ ] Is ADX my only reading that is not momentum? Am I treating +DI/−DI, Aroon or Vortex as a second opinion beside RSI?
- [ ] Is ADX above about 20–25 before I rely on a trend-following signal?
- [ ] Is the trailing line wide enough for this stock? How often has it flipped in the last year?
- [ ] Do I have a results date ahead? No ATR line protects against a gap.
- [ ] Am I reading the Ichimoku cloud as a forecast, when it was computed 26 bars ago?
- [ ] Do I have one trend reading and one stop line, rather than five indicators voting?

## Further reading

- J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) — the Directional Movement Index, ADX and Parabolic SAR.
- Etienne Botes and Douglas Siepman, "The Vortex Indicator", *Technical Analysis of Stocks & Commodities* (2010).
- Chuck LeBeau and David Lucas, *Technical Traders Guide to Computer Analysis of the Futures Market* — the Chandelier Exit.
- Moskowitz, Ooi and Pedersen, "Time Series Momentum" (*Journal of Financial Economics*, 2012).
- Brock, Lakonishok and LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns" (*Journal of Finance*, 1992).
- Sullivan, Timmermann and White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap" (*Journal of Finance*, 1999).
- Park and Irwin, "What Do We Know About the Profitability of Technical Analysis?" (*Journal of Economic Surveys*, 2007).
