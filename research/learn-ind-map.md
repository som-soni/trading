# Indicators — the map: eight families, and which ones say the same thing

**In short**

- An indicator turns past prices and volume into a number that answers one question. There are dozens of indicators, but only about eight questions.
- Group indicators by what they measure: moving averages, bands and channels, trend, momentum (two kinds), volatility, volume and price levels. "Oscillator" and "trading signal" describe how a study is drawn or used, not what it measures.
- Measured on stored prices, many indicators are one number under different names. RSI and the close's place in a Keltner channel moved together at 0.98; so did CCI and Bollinger %B.
- A few say something genuinely different: ADX, relative volume, the swing-size measures and the long-horizon momentum readings.
- Pick one indicator per question. Two from the same cluster look like confirmation but are one opinion counted twice.

This guide is the entry point to the Indicators section. It sorts every common indicator into its family, measures which ones repeat each other, and suggests one indicator per question. Each family then has its own guide, with formulas, default settings, worked examples and the evidence.

Start with the two core guides if you are new to indicators: [Indicators — trend and volatility](learn-price-indicators.md) covers moving averages, ATR and ADX, and [Momentum indicators](learn-price-oscillators.md) covers RSI, MACD and Bollinger Bands.

---

## 1. Two indicators, one opinion

Here are two momentum readings for Apple through 2025. One is the distance of the close from its 50-day average, in %. The other is the Percentage Price Oscillator (PPO), the gap between a 12-day and a 26-day exponential average, also in %.

```series
title: Apple, 2025 — distance from the 50-day average against the PPO
from: 2025-01-01
to: 2025-12-31
tf: D
line: us:AAPL@distma.d | Distance from 50-day (%), left scale | zero
line: us:AAPL@ppo.ppo | PPO 12/26 (%), right scale | right
caption: Different names, different formulas, one shape. Each line has its own scale: the PPO swings about a quarter as far, because its two averages are both short. Across 300 US stocks the two readings correlated at 0.96.
```

The two lines rise and fall together and turn at much the same places. One is built from a simple average, the other from two exponential ones. They still answer the same question: how far has the price run ahead of where it has recently been?

That is the most useful fact about indicators. **What matters is the question an indicator answers, not its name.** A chart with four indicators that answer one question holds one opinion, shown four times.

## 2. The eight families

Each family answers one kind of question. The table lists every indicator covered in these guides.

| Family | The question it answers | Indicators | Guide |
|---|---|---|---|
| Moving averages | Which way is the price going, once the noise is smoothed out? | Simple, exponential, weighted and Wilder's averages; DEMA; Hull; KAMA; Williams Alligator; ribbons | [Moving averages](learn-ind-moving-averages.md) |
| Bands and channels | How far is the price from its average, measured against its normal swing? | Bollinger Bands, Keltner Channels, Donchian Channels, moving-average envelopes, ATR bands | [Bands and channels](learn-ind-bands-channels.md) |
| Trend | Is there a trend, how steady is it, and where would it end? | DMI and ADX, Aroon and the Aroon Oscillator, Vortex, Parabolic SAR, Supertrend, Chandelier Exit, Ichimoku, Chande Trend Meter, RS line | [Trend indicators](learn-ind-trend.md) |
| Momentum I — range | Where does the close sit in its recent range? | RSI, Stochastic, Stochastic RSI, Williams %R, CCI, Bollinger %B, Ultimate Oscillator, Connors RSI, Balance of Power | [Momentum I](learn-ind-momentum-range.md) |
| Momentum II — rate | How fast is the price changing? | Rate of change, Momentum, distance from an average, MACD, PPO, TRIX, TSI, KST and Pring's Special K, PMO, DPO | [Momentum II](learn-ind-momentum-rate.md) |
| Volatility | How big are the swings, and are they growing or shrinking? | ATR and ATR %, standard deviation, Bollinger BandWidth, historical volatility, Mass Index, Ulcer Index, TTM Squeeze | [Volatility indicators](learn-ind-volatility.md) |
| Volume | Is trading heavier than usual, and on rising or falling days? | Relative volume, OBV, A/D line, Chaikin Money Flow and Oscillator, Money Flow Index, Force Index, Ease of Movement, VWAP, volume by price | [Volume indicators](learn-ind-volume.md) |
| Levels | Which prices might matter? | Pivot points, swing pivots, Fibonacci retracements, Zig Zag, Darvas boxes | [Level indicators](learn-ind-levels.md) |

Two words often used as families are not families. An **oscillator** is any reading that swings around a centre line or between fixed bounds. Most momentum indicators are drawn that way, and so are some volume and trend ones. A **trading signal** is a use: Parabolic SAR, Supertrend and the Chandelier Exit are trailing stops built on trend and volatility.

Momentum has two families because there are two ways to measure it. **Range** readings place today's close inside a recent high–low range or band, so they are bounded, often 0 to 100. **Rate** readings measure change over time, so they swing freely around zero.

## 3. Which indicators say the same thing — measured

> **Method.** 300 randomly chosen US stocks and all 147 qualifying Indian stocks, each with at least 1,500 sessions since 2015 and a median daily traded value of at least $10 million (US) or ₹50 crore (India). Every indicator was computed on daily bars with its usual default settings. For each stock, the correlation between two indicators was measured day by day from 2015 to October 2026. The tables show the median across stocks. A correlation of 1 means two readings move together exactly; 0 means no relation.

The readings fall into clusters. Inside a cluster, the indicators are close to interchangeable. The figures are US medians; India's were within 0.05 of every one.

| Cluster | Members, with their median correlation to the first | What they all measure |
|---|---|---|
| Stretch over 2–3 weeks | RSI 14; close's place in a Keltner channel 0.98; in ATR bands 0.95; +DI minus −DI 0.94; in a Donchian channel 0.90; %B 0.89; CCI 0.87; Williams %R 0.84; Stochastic 0.83 | Where the close sits after the last few weeks |
| Change over 2–3 weeks | 14-day % change; close's place in a 2.5% envelope 0.93; distance from the 20-day VWAP 0.92; Vortex spread 0.88; Rate of change (9) 0.78; Money Flow Index 0.76 | How far the price has moved lately |
| Distance from a slower average | Distance from the 50-day; PPO 0.96; PMO 0.92; TSI 0.90; MACD line 0.89; TRIX 0.88; KST 0.88 | How far the price has run from where it has been for months |
| Swing size | ATR %; historical volatility 0.88; standard deviation ÷ price 0.73; Bollinger BandWidth 0.70 | How much the price moves, in either direction |

Inside the third cluster, TRIX, KST and PMO correlated 0.96–0.98 with each other. BandWidth and standard deviation ÷ price correlated 0.98: one is the other times a constant.

The clusters also overlap. RSI correlated 0.81 with the recent % change and 0.88 with the distance from the slower average. **Most of the indicator catalogue is one family of momentum readings, at a few speeds.**

Some readings stood apart:

| Reading | Its strongest link to any other reading | Why it differs |
|---|---|---|
| ADX | 0.41 (Bollinger BandWidth) | It measures how steady a move is, not its direction |
| Relative volume | 0.17 (Mass Index) | It measures participation, not price |
| Mass Index | 0.35 (historical volatility) | It measures whether ranges are widening fast |
| Pring's Special K | 0.27 with any momentum reading | Most of its weight is on moves of six months to two years |
| Stochastic RSI | 0.79 with Stochastic, 0.54 with RSI | It is a very fast, noisy version of RSI |
| Connors RSI | 0.58 (Williams %R), 0.46 with RSI | It mixes a 3-day RSI, a streak count and a percentile |
| Detrended Price Oscillator | −0.64 with Momentum (10) | It compares an old price with today's average, so it leans the other way |

A low correlation means an indicator is *different*. It does not mean it is useful. Each family guide reports what is known about usefulness.

## 4. One indicator per question

A practical rule follows: choose the question first, then one indicator for it.

| Question | Use one of | They repeat |
|---|---|---|
| Is the stock in an uptrend? | The 50- and 200-day averages and their slope | Close vs the Ichimoku cloud (0.76 with the distance from the 50-day), Supertrend's direction (0.66) |
| Is the move steady in one direction? | ADX | Nothing else measured |
| Has it run up or down a lot in the last few weeks? | RSI 14 | Stochastic, Williams %R, CCI, %B, a channel position |
| How far has it run from its slower average? | Distance from the 50-day, in % or in ATRs | MACD, PPO, TSI, PMO, TRIX, KST |
| How much does it move per day? | ATR % | Historical volatility, standard deviation |
| Has it gone unusually quiet? | Bollinger BandWidth, or ATR % against its own past | TTM Squeeze |
| Is trading heavier than usual? | Relative volume | Nothing else measured |
| Is it beating the market? | A relative strength line or rank | Not RSI — see [relative strength](learn-price-rs.md) |
| Where might it stop or turn? | Swing highs and lows, then pivot points | Fibonacci levels, Zig Zag |

A sensible chart holds three to five indicators, each answering a different row. Adding a second indicator from the same row adds lag or noise, not information.

## 5. Reading order

The two core guides come first. They explain what an indicator is and measure the most-used ones in depth.

1. [Indicators — trend and volatility](learn-price-indicators.md): moving averages, ATR and ADX.
2. [Momentum indicators](learn-price-oscillators.md): RSI, MACD and Bollinger Bands.

The family guides can then be read in any order. Each one gives every indicator its formula, default settings, a worked example on a real stock, the question it answers and what it repeats.

3. [Moving averages](learn-ind-moving-averages.md)
4. [Bands and channels](learn-ind-bands-channels.md)
5. [Trend indicators](learn-ind-trend.md)
6. [Momentum I — where the close sits in its range](learn-ind-momentum-range.md)
7. [Momentum II — how fast the price is changing](learn-ind-momentum-rate.md)
8. [Volatility indicators](learn-ind-volatility.md)
9. [Volume indicators](learn-ind-volume.md)
10. [Level indicators](learn-ind-levels.md)

## 6. What the evidence says

- **Robust:** many popular indicators measure the same thing. The clusters above held in both markets, with India's correlations within 0.05 of the US figures.
- **Robust:** ADX, relative volume and the swing-size measures carry information the momentum readings do not.
- **Limits:** correlation shows that two readings are alike, not that either one predicts anything. The measurement used daily bars and default settings; other settings shift the numbers. The stocks are today's listed companies, so failed ones are missing. Education, not advice.

## 7. Checklist

- [ ] For each indicator on my chart, can I name the question it answers?
- [ ] Do any two of them answer the same question? If so, keep one.
- [ ] Is there one reading for trend, one for stretch, one for swing size and one for volume?
- [ ] Am I treating a "trend" indicator's direction as separate evidence, when it mostly repeats momentum?
- [ ] Have I read the family guide for any indicator I rely on, including what it repeats?

## Further reading

- J. Welles Wilder Jr., *New Concepts in Technical Trading Systems* (1978) — RSI, ATR, ADX and Parabolic SAR, from their author.
- John Bollinger, *Bollinger on Bollinger Bands* (2001) — bands, %B and BandWidth, and why indicators that measure the same thing should not be stacked.
- John J. Murphy, *Technical Analysis of the Financial Markets* (1999) — a standard reference for most of the indicators here.
- Perry J. Kaufman, *Trading Systems and Methods* — formulas and tests for a wide range of indicators.
