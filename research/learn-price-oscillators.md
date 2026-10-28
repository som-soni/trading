# Momentum indicators — RSI, MACD and Bollinger Bands, and how much they overlap

**In short**

- RSI, MACD and Bollinger Bands all describe how fast a stock has moved lately, measured against its own recent past.
- "Overbought" (RSI above 70) is what a strong uptrend looks like, not a reason to sell. Across thousands of stocks it was not followed by a fall on average.
- A Bollinger squeeze (very narrow bands) was not followed by a bigger move than usual. It describes a tight range; something else has to make it a trade.
- Measured on stored prices, RSI, Bollinger %B and the distance from the 50-day average are nearly the same number. Three momentum indicators on one chart give one opinion three times.
- Choose indicators that answer different questions: trend, swing size, trend steadiness, volume and comparison with the market.

Moving averages, ATR and ADX — the trend and volatility indicators — are in [the trend and volatility indicators guide](learn-price-indicators.md), which also explains what an indicator is. Every other indicator has a family guide, listed in [Indicators — the map](learn-ind-map.md). For basic words, see [Start here](learn-start-here.md).

---

## 1. RSI — the speed of recent moves

### 1.1 What it computes

Say a stock's average gain on up-days is 1.0 and its average loss on down-days is 0.5. The ratio of the two (RS) is 2. Then:

> RSI = 100 − 100 ÷ (1 + RS) = 100 − 100 ÷ 3 = 66.7

If there were no losses at all, RSI would be 100. Equal gains and losses give 50.

RSI (the relative strength index) compares the size of recent up-days with the size of recent down-days. Each day, the gain is the rise from the previous close (0 on a down-day). The loss is the fall (0 on an up-day). Both are averaged with Wilder's smoothing over 14 days.

Wilder's 14-day smoothing uses α = 1/14. That is the same as an ordinary EMA of about 27 days, so RSI14 remembers more than the "14" suggests.

### 1.2 Overbought and oversold — and why a leader stays "overbought"

```series
title: Nvidia's RSI14 during its 2023–24 advance
from: 2023-01-01
to: 2024-06-30
line: us:NVDA | Nvidia | log
line: us:NVDA@rsi14 | RSI 14 | pane2
caption: RSI was above 70 on 95 of 374 sessions (25%) and above 50 on 83% of them. It never reached 30: the low was 31.4 on 21 September 2023. The first reading above 70 came on 25 January 2023, at $19.32 split-adjusted; the stock ended June 2024 at $123.5.
```

A trader who sold every time RSI crossed 70 would have sold Nvidia about 20 times in this run. In India, Trent rose about 458% from April 2023 to September 2024. Its RSI14 was above 70 on 47% of those sessions and never fell below 40.5.

The usual readings: above 70 is called **overbought**, below 30 **oversold**. The words suggest the price must come back. It need not. RSI above 70 means only that **the recent up-days have been much bigger than the down-days**. That is exactly what a strong uptrend looks like.

**In a leader, a high RSI is a description of strength, not a signal to sell.** RSI is more useful in the other direction. A leader whose RSI cannot get back above 50 or 60 after a pullback is losing speed.

What does a high or low RSI say about the next month across all stocks? We measured it on the sample described in section 5.

> **Method note.** The section 5 sample of US and Indian stocks, 2015 to October 2026. Returns over the next 21 sessions, from overlapping windows, pooled across stocks. No costs.

| Next 21 sessions | US: all days | US: RSI > 70 | US: RSI < 30 | India: all days | India: RSI > 70 | India: RSI < 30 |
|---|---|---|---|---|---|---|
| Share of days | 100% | 6.4% | 4.0% | 100% | 7.1% | 3.8% |
| Mean return | +1.2% | +0.8% | +2.2% | +1.4% | +2.3% | +1.7% |
| Share of rises | 53.9% | 51.5% | 56.9% | 54.6% | 57.7% | 55.6% |

The differences are small and point in **opposite directions** in the two markets. In the US, oversold stocks did a little better and overbought a little worse. In India it was the other way round. Neither result is a trading rule. "Overbought" was not, on average, followed by a fall in either market.

### 1.3 RSI is not relative strength

The names are confusing. **RSI** compares a stock with **its own** recent past. **Relative strength** compares a stock's performance **with the index or with other stocks**. A stock can have RSI 75 (it rose fast this fortnight) and a weak RS rank (it is still far behind the market over a year). See [the relative strength guide](learn-price-rs.md).

### 1.4 How traders use RSI

Many systematic traders use RSI only as a **warning flag**, never as a buy signal on its own. Typical flags in trend-following setups:

- **Extended:** RSI14 above 75 to 80. Wait for a pullback before buying.
- **Weak momentum:** RSI14 below 40 while the close is still above the 50-day. Wait for a trigger, such as a close above a recent high.

Some traders also smooth RSI with a 14-day average to reduce its day-to-day noise. Short-term mean-reversion traders use RSI the other way, buying very low readings; that method is in [RSI(2) mean reversion](learn-strat-rsi2.md).

## 2. MACD — the gap between a fast and a slow average

### 2.1 What it computes

Take a stock whose fast and slow averages have drifted apart:

> 12-day EMA 105 − 26-day EMA 100 = MACD 5; MACD 5 − signal line 4 = histogram +1

The histogram is positive. The gap between the averages is wider than its own recent average, so it has been widening.

The **MACD line** is the 12-day EMA minus the 26-day EMA. When the short average is above the long one, the line is positive: recent prices are above older ones. The **signal line** is a 9-day EMA of the MACD line. The **histogram** is the MACD line minus the signal line.

A MACD "buy" is the MACD line crossing above the signal line; a "sell" is crossing below. MACD is in price units, like ATR. A MACD of 5 means something different on a $50 stock and a $500 stock.

### 2.2 Lag, and crossings in a falling stock

```series
title: Meta and its MACD, July 2021 – February 2022
from: 2021-07-01
to: 2022-02-28
line: us:META | Meta
line: us:META@macd | MACD (12-26) | pane2 zero
line: us:META@macdsig | Signal (9) | pane2
mark: 2021-09-07 | Peak close $382
caption: Meta peaked on 7 September 2021 and fell 48% to 23 February 2022. MACD crossed below its signal four sessions after the peak, at $376.5. It then crossed back above it four times before the low, the last time on 2 February 2022, the day before the stock fell 26% on its results.
```

Here the first sell came quickly. The cost came afterwards: four buy signals in a falling stock. Over these eight months the two lines crossed 14 times.

MACD is built from averages of averages, so it is late by design. It is also crossed often when a stock moves sideways or falls in steps.

### 2.3 What it adds and what it repeats

The MACD line is close to "how far is the price above its recent average". In section 5 its correlation with the distance from the 50-day is 0.94. The histogram is close to "how much did the price change in the last two or three weeks" (0.77 with the 14-day % change).

**MACD repeats the moving averages.** It adds a single number for "the short-term trend is speeding up or slowing down".

## 3. Bollinger Bands — volatility envelopes and the squeeze

### 3.1 What they compute

Take a stock whose recent closes average 100 and are fairly spread out:

> 20-day SMA 100, standard deviation 2 → bands at 100 ± 2 × 2, so 96 and 104

The bands sit two standard deviations either side of the average. Standard deviation measures how spread out the closes are.

So the middle band is the 20-day SMA, and the upper and lower bands are 2 standard deviations above and below it. Two numbers come from the bands:

- **%B**: where the close sits between the bands (0 = on the lower band, 1 = on the upper).
- **Bandwidth**: (upper − lower) ÷ middle. In the example, 8 ÷ 100 = 8%.

### 3.2 The squeeze

```series
title: Amazon — a Bollinger squeeze, then a gap up, autumn 2024
from: 2024-07-01
to: 2024-12-31
line: us:AMZN | Amazon
line: us:AMZN@bbup20 | Upper band (20, 2)
line: us:AMZN@bblo20 | Lower band (20, 2)
mark: 2024-11-01 | Results gap
caption: On 25 October 2024 the bands were $181.4 and $191.1, a bandwidth of about 5%, the narrowest of the half-year. After results Amazon closed at $197.9 on 1 November and reached $232.9 on 16 December. This example was picked to show the idea; the measurement below shows it is not typical.
```

A **squeeze** is when the bands come unusually close together: the stock has been very quiet. Many traders read a squeeze as the calm before a large move. That idea comes from Bollinger himself. The bands do not say which way the move will go.

Is a squeeze followed by a bigger move? On the section 5 sample, we marked each day when the 20-day bandwidth was the lowest of the last 125 sessions. Then we measured the next 21 sessions:

| Next 21 sessions | US: all days | US: after a squeeze | India: all days | India: after a squeeze |
|---|---|---|---|---|
| Median size of the move (up or down) | 5.7% | 5.3% | 5.7% | 5.7% |
| Share moving more than 10% | 27.7% | 24.9% | 26.0% | 24.7% |
| Share of rises | 53.9% | 51.9% | 54.5% | 52.1% |

**After a squeeze, the next month's move was no larger than usual.** A quiet stock tends to stay fairly quiet. A squeeze is a description of a tight range. It needs something else, such as a breakout on volume or a results date, to become a trade. Base and VCP methods use tightness that way: together with a pivot and volume (see [the VCP guide](learn-vcp.md) and [Short squeezes and bear-market rallies](learn-strat-squeezes-bear-rallies.md)).

### 3.3 What they add and what they repeat

%B repeats RSI (section 5: correlation 0.89). The bandwidth repeats ATR % in a different form. Bollinger Bands are useful mainly as **a picture**. They show on one chart how far the price is from its average, measured in its own volatility.

Charting tools differ in one detail. Some use the population standard deviation (dividing by 20), others the sample one (dividing by 19). For 20 days the bands' distance from the middle differs by about 2.6%.

## 4. The wider family of indicators

Most charting packages offer dozens of studies. Nearly all of them fall into a few families, and members of one family mostly repeat each other (section 5). The usual default settings are in brackets. Each family has its own guide, and [Indicators — the map](learn-ind-map.md) measures the overlap across all of them.

| Family | Common studies (default settings) |
|---|---|
| Moving averages | Simple (20); exponential (20); weighted (20); a ribbon of several lengths (20/50/100/200); double exponential, DEMA (20); Hull (9); Kaufman adaptive, KAMA (10/2/30); Williams Alligator (three smoothed averages, 13/8/5) |
| Bands & channels | Bollinger Bands (20, 2); Keltner Channels (20-day EMA ± 2 × 10-day ATR); Donchian Channels (20); moving-average envelopes (20-day average ± a fixed %); ATR bands (an average ± a multiple of ATR) |
| Support & resistance | Swing pivots high/low (10 bars each side); floor-trader pivot points (Traditional, Fibonacci or Camarilla); swing support and resistance levels; Fibonacci retracements (38.2/50/61.8% of a swing); Zig Zag (swings of at least 5%; it redraws its last leg); Darvas boxes (the range a stock holds after a new high); volume by price |
| Trend | Parabolic SAR (0.02/0.02/0.2); Supertrend (10, 3); Chandelier Exit (22, 3 × ATR); Ichimoku Cloud (9/26/52); Directional Movement Index (ADX 14); Aroon and the Aroon Oscillator (14); Vortex (14); Chande Trend Meter; an RS line against an index |
| Momentum | RSI (14; lines at 70/50/30); MACD (12/26/9); Stochastic (14/3/3); Stochastic RSI (14/14/3/3); Commodity Channel Index (20); Williams %R (14); Rate of Change (9); Momentum (10); distance from a moving average; Bollinger %B (20, 2); PPO (12/26/9); TRIX (15); True Strength Index (25/13); Ultimate Oscillator (7/14/28); Pring's Special K; Price Momentum Oscillator (35/20/10); Connors RSI (3/2/100); Detrended Price Oscillator (20); Balance of Power |
| Volatility | Average True Range (14); ATR % of price (14); Bollinger BandWidth (20, 2); standard deviation (20); Mass Index (25); Ulcer Index (14); TTM Squeeze (Bollinger Bands inside Keltner Channels) |
| Volume | Volume with a 20-bar average; rolling VWAP (20); Money Flow Index (14); On Balance Volume; Chaikin Money Flow (20); Accumulation/Distribution line; Chaikin Oscillator (3/10, a MACD of the A/D line); Force Index (13); Ease of Movement (14) |

The families group studies by **what they measure**: direction, speed, swing size, volume or price levels. Some lists add columns such as "oscillators" or "trading signals". Those describe how a study is drawn or used, so most studies would fit two or three columns. Most momentum studies are drawn as oscillators, and Parabolic SAR, Supertrend and the Chandelier Exit are trailing-stop rules built on trend and ATR.

Some names mislead. **%B** sits with momentum, not volatility: it is the price's position inside the bands, and it tracks RSI closely (section 5). **TRIX** is the rate of change of a smoothed average, so it is momentum too. Ichimoku draws several studies at once, so it appears in many lists; its cloud is a trend filter.

Packages also differ in small details. Most follow Wilder's smoothing for RSI, ATR and ADX. Some start an EMA from the average of its first N bars, others from the first close. The two agree after the first few dozen bars. Support and resistance levels are covered in [the chart patterns guide](learn-chart-patterns.md).

## 5. How much they overlap — measured

Take Apple in 2024. Its RSI14 and its plain 14-day % change had a correlation of 0.89: two indicators, one story. We measured the same thing across many stocks.

> **Method.** Stocks with at least 1,500 sessions since 2015 and a median daily traded value of at least $10 million (US) or ₹50 crore (India). A random 300 in the US; all 145 that qualify in India. For each stock, each indicator was computed over 2015–2026, and the correlations were measured day by day within that stock. The table shows the median across stocks. A correlation of 1 means two numbers move together exactly; 0 means no relation. The stocks are ones listed today, so some survivorship bias is possible.

| Median correlation (US / India) | RSI14 | MACD histogram | 14-day % change | Distance from 50-day | Bollinger %B |
|---|---|---|---|---|---|
| RSI14 | 1 | 0.58 / 0.60 | 0.81 / 0.84 | 0.88 / 0.89 | 0.89 / 0.89 |
| MACD line (÷ price) | 0.78 / 0.80 | 0.36 / 0.34 | 0.73 / 0.75 | 0.94 / 0.95 | 0.54 / 0.56 |
| MACD histogram | 0.58 / 0.60 | 1 | 0.77 / 0.77 | 0.40 / 0.39 | 0.69 / 0.71 |
| ADX14 | 0.07 / 0.14 | −0.04 / 0.00 | 0.00 / 0.08 | 0.03 / 0.12 | 0.02 / 0.06 |
| ATR % | −0.28 / −0.23 | −0.09 / −0.12 | −0.23 / −0.20 | −0.40 / −0.29 | −0.18 / −0.17 |

What it shows:

- **RSI14, %B and the distance from the 50-day are nearly the same number** (0.88–0.89). The **MACD line** is almost exactly the distance from an average (0.94–0.95). The **MACD histogram** is mostly the recent % change (0.77).
- **RSI14 and the plain 14-day % change** correlate at 0.81 in the US and 0.84 in India. Ranked correlations, which ignore outliers, give 0.85 and 0.86.
- **ADX and ATR % measure something else**: trend steadiness and swing size. ADX's correlations with the direction indicators are near zero. ATR %'s are weak and negative (about −0.1 to −0.5): within a stock, volatility tends to be higher when the price is below its averages.
- The two markets give almost the same table.

```series
title: Apple in 2024 — RSI14 against the plain 14-day % change
from: 2024-01-01
to: 2024-12-31
line: us:AAPL@rsi14 | RSI 14
line: us:AAPL@chg14 | 14-day % change | right
caption: Two indicators, one story. In 2024 the two lines had a correlation of 0.89 for Apple. They differ mainly at the extremes: RSI's low was on 7 March; the 14-day change's low was on 5 August.
```

**So what?** Putting RSI, MACD and Stochastic on one chart does not give three opinions. It gives one opinion three times. A useful set of indicators covers **different questions**. Use one for trend (a moving average), one for swing size (ATR), and perhaps one for trend steadiness (ADX). Add volume (see [the volume guide](learn-price-volume.md)) and comparison with the market (see [the relative strength guide](learn-price-rs.md)).

## 6. What the evidence says

- **Robust: moving-average trend filters reduce the deepest drawdowns** on indices, by keeping you out during long bear markets. They usually do not raise returns after whipsaws and costs. This is shown for the index in [the trend guide](learn-health-trend.md).
- **Robust: medium-term momentum** (the past 3–12 months' return, ranked across stocks) has predicted the next months' return in many markets and decades (Jegadeesh and Titman, 1993, and many studies since). That is a **cross-sectional** comparison between stocks. It is what an RS rank and 12-1 momentum measure. It is not RSI.
- **Mixed: rules based on a single indicator.** Brock, Lakonishok and LeBaron (1992) found that simple moving-average and range-breakout rules on the Dow had predictive power in data up to 1986. Sullivan, Timmermann and White (1999) showed that, once you allow for how many rules had been tried, the best rule's results did not hold in the following years. Park and Irwin's survey (2007) found many positive studies, and also widespread problems: testing many rules on the same data, ignoring costs, and choosing rules after the fact.
- **Folklore: "overbought means sell"** and **"a squeeze means a big move is coming"**. On the stored prices measured here, neither held on average (sections 1.2 and 3.2).
- **Built in: lag.** Every indicator here uses past bars. Smoothing reduces false signals and adds delay. You cannot have both fewer false signals and less delay from the same data.
- **Measured here: overlap.** Most momentum indicators are close to the same number (section 5). Adding more of them adds confidence without adding information.
- **Limits:** the studies here use today's listed stocks, overlapping windows and no costs.
- **Good practice:** use indicators as filters and flags, not as entry signals. Take entries from price levels: a pivot, a recent high, a channel high. Take stops from a pullback low or a base low, limited in ATR.

## 7. Which indicator answers which question

| Question | Indicator | What it repeats | Typical use |
|---|---|---|---|
| Is the stock in an uptrend? | 50/150/200-day SMA, and its slope | The price over months | Trend filters such as the Trend Template |
| Where might a pullback stop? | 20/21-day or 50-day average | Recent average price | Pullback entries: within about 1 ATR of a rising 50-day, then a close back above the 20-day |
| How much does it move per day? | ATR14 | Candle height | Stops, extension, volatility limits |
| Is it more volatile than another stock? | ATR % | — | Skip stocks below about 1.5% or above about 8–10% |
| How fast has it risen lately? | RSI14, 14-day % change | Each other | Warning flags: extended above 75–80, weak below 40 |
| Is short-term momentum speeding up? | MACD histogram | The recent % change | Mostly a chart aid |
| Is it far from its average for its volatility? | Bollinger %B, ATR distance from an average | RSI | Extension checks, usually in ATR |
| Has it gone unusually quiet? | Bollinger bandwidth, ATR % against its own past | ATR | Base and VCP tightness tests |
| Is the move steady in one direction? | ADX14 | — | A minimum trend strength (about 15–20); above 40 is late |
| Is it beating the market? | Relative strength line or RS rank | Not RSI | Choosing leaders (see [relative strength](learn-price-rs.md)) |

## 8. Checklist

- [ ] For each indicator on my chart: which question does it answer? Do two of them answer the same one?
- [ ] Trend: is the stock above a rising 50- and 200-day, or is the line flat and being crossed every few days?
- [ ] Volatility: what is its ATR %? Is my stop at least about one ATR away?
- [ ] Extension: how many ATR is the close above the 20- and 50-day? (About 2.5 above the 20-day is stretched; 4 is a reason to pass.)
- [ ] RSI above 70 in a leader: am I reading strength as a sell signal?
- [ ] RSI below 40–50 after a pullback in a leader: is momentum fading?
- [ ] A squeeze: what will make it move — a pivot, volume, a results date?
- [ ] Am I acting on an indicator alone, without a price level for entry and stop?

## Further reading

- J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) — the original RSI, ATR, ADX and Parabolic SAR.
- Gerald Appel, *Technical Analysis: Power Tools for Active Investors* (2005) — MACD from its author.
- John Bollinger, *Bollinger on Bollinger Bands* (2001) — the bands, %B, bandwidth and the squeeze.
- Brock, Lakonishok and LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns" (*Journal of Finance*, 1992).
- Sullivan, Timmermann and White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap" (*Journal of Finance*, 1999).
- Park and Irwin, "What Do We Know About the Profitability of Technical Analysis?" (*Journal of Economic Surveys*, 2007).
- Jegadeesh and Titman, "Returns to Buying Winners and Selling Losers" (*Journal of Finance*, 1993) — momentum across stocks.
