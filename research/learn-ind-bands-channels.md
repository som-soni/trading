# Bands and channels — Bollinger, Keltner, Donchian, envelopes and ATR bands

**In short**

- A band is a centre line with a line above and below it. The designs differ only in how they set the width: a fixed %, the spread of closes, the average daily range, or the highest high and lowest low.
- A fixed % envelope ignores how volatile a stock is. A 2.5% envelope had the close outside it on about 55% of sessions; the volatility-based bands, on about 12–22%.
- Where the close sits inside a band is a momentum reading in disguise. Its position in a Keltner channel correlated 0.98 with RSI14.
- The band's width is a volatility reading. It repeats ATR % or the standard deviation, which have their own guide.
- Use a band as a picture of "far from normal for this stock", or as a breakout level (Donchian). Do not count two bands as two opinions.

Bands are drawn on the price chart, so they feel different from an oscillator in a lower panel. This guide shows they carry the same two numbers as other families: how far the price has run, and how much it usually moves.

Bollinger Bands are explained in [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md). The volatility side, including the squeeze, is in [Volatility indicators — ATR, standard deviation, BandWidth, historical volatility, Mass Index, Ulcer Index, TTM Squeeze](learn-ind-volatility.md). Donchian breakouts as a strategy are in [Channel breakout trend following](learn-strat-channel-breakout.md). For the whole set of families, see [Indicators — the map](learn-ind-map.md).

---

## 1. What this family measures

On 3 September 2025 Apple closed at $238.47, up 3.8% on the day. Five common bands, each with its usual settings, gave five different verdicts.

| Band (settings) | Lower | Upper | Close is… | Position (0 = lower, 1 = upper) | Width, % of centre |
|---|---|---|---|---|---|
| Bollinger (20, 2) | $218.62 | $239.09 | Just inside | 0.97 | 8.9% |
| Keltner (20, 2, 10) | $217.93 | $236.76 | Above | 1.09 | 8.3% |
| ATR bands (20, 14, 2) | $219.50 | $238.21 | Just above | 1.01 | 8.2% |
| Donchian (20) | $205.59 | $238.85 | At the top: a new 20-day high | 0.99 | 15.0% |
| Envelope (20, 2.5%) | $223.14 | $234.58 | Well above | 1.34 | 5.0% |

The same close was inside two bands and outside three. RSI14 that day was 69.9, near the usual "overbought" line. Every band was saying the same thing in its own units: Apple had run up fast for a stock of its usual volatility.

A band answers one question: **is the price far from its normal range?** "Normal" is set by the width. There are four ways to set it:

| Width set by | Bands | What makes the band wider |
|---|---|---|
| A fixed % of the average | Envelopes | Nothing: it is always the same % |
| The spread of closes (standard deviation) | Bollinger Bands | Closes scattered far from their average |
| The average daily range (ATR) | Keltner Channels, ATR bands | Bigger daily bars, including gaps |
| The highest high and lowest low | Donchian Channels | A larger move inside the window |

**ATR** (average true range) is the average size of a day's move, gaps included; see [Indicators — trend and volatility: moving averages, ATR and ADX](learn-price-indicators.md). **Standard deviation** measures how spread out the closes are around their average.

## 2. Bollinger Bands — width from the spread of closes

Bollinger Bands are a 20-day SMA with lines 2 standard deviations above and below. Their two readings are **%B** (where the close sits, 0 to 1) and **BandWidth** (the width as a % of the middle). Both are explained with worked numbers in [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md).

One property sets them apart from the ATR-based bands. The width depends on how far the closes have strayed from their average. A strong one-way move therefore widens the bands by itself. So a trend stretches Bollinger Bands faster than it stretches a Keltner channel.

```series
title: Apple, 2025 — Bollinger Bands and the Keltner Channel through a crash and a recovery
from: 2025-01-01
to: 2025-10-31
line: us:AAPL | Apple
line: us:AAPL@bb.upper | Bollinger upper (20, 2)
line: us:AAPL@bb.lower | Bollinger lower (20, 2)
line: us:AAPL@kc.upper | Keltner upper (20, 2, 10)
line: us:AAPL@kc.lower | Keltner lower (20, 2, 10)
mark: 2025-04-08 | Close $172.42
caption: In the April fall the Bollinger Bands blew out to about 27% wide, well outside the Keltner Channel. In the quiet weeks of June and late July they shrank inside it. Bollinger inside Keltner is the "squeeze" described in the volatility guide.
```

## 3. Keltner Channels — width from the average daily range

A Keltner channel asks: how far is the close from its average, measured in typical days' moves? A close above the upper line has moved more than two average days' ranges above the trend line.

```
Middle = EMA(close, 20)
Upper  = Middle + 2 × ATR(10)
Lower  = Middle − 2 × ATR(10)
Defaults: 20, 2, 10. Packages differ in the multiplier and the ATR length.
```

The name comes from Chester Keltner, whose 1960 book described a channel round a 10-day average of the typical price, (high + low + close) ÷ 3. His width was a 10-day average of the high-minus-low range. Today's version, with an EMA and ATR, came later. It keeps the idea and only changes the parts.

**Worked example (TCS).** On 28 February 2025 Tata Consultancy Services closed at ₹3,483.25, down 3.6% on the day.

| Reading | Value |
|---|---|
| Keltner middle (20-day EMA) | ₹3,836.61 |
| Keltner lower | ₹3,681.16 |
| ATR(10) | ₹77.72 |
| Close below the lower line by | ₹197.91, about 2.5 ATR |
| Position in the channel | −0.64 |
| RSI14 | 15.7 |

TCS was falling hard: about 4.5 ATR below its 20-day EMA. The very low RSI says the same thing. That is the main point of this guide: the two readings agree because they measure the same thing.

**Pitfalls.** Settings differ between charting packages, so "outside the Keltner channel" is not one fixed event. And because ATR reacts to gaps, a single results-day gap can widen the channel for weeks.

## 4. ATR bands — Keltner's width round a simple average

ATR bands ask the same question as Keltner. The usual form puts 2 ATR(14) either side of a 20-day SMA.

```
Middle = SMA(close, 20)
Upper / Lower = Middle ± 2 × ATR(14)
```

On Apple on 3 September 2025 they were $219.50 to $238.21, almost the same as the Keltner channel. The main difference is the centre. After a sharp move the EMA catches up faster than the SMA, so the close stays outside an SMA-based band for longer. That is one reason ATR bands were breached more often than Keltner (section 10).

ATR bands are mostly used for exits and stops rather than signals. A trailing stop set at "2 ATR below the average" is an ATR band's lower line. See [Stops and exits — where a trade is wrong, and how it ends](learn-risk-stops-exits.md).

## 5. Donchian Channels — the highest high and lowest low

A Donchian channel asks: is today's price beyond the range of the last n days? It has no average and no volatility formula. The upper line is the highest high of the last 20 bars; the lower line is the lowest low.

```
Upper  = highest high of the last 20 bars
Lower  = lowest low of the last 20 bars
Middle = (Upper + Lower) ÷ 2
Default: 20 bars. A breakout compares today's close with the PREVIOUS 20 bars' extreme.
```

It is named after Richard Donchian, an early manager of trend-following futures funds. Breakout rules on it were the core of the Turtle traders' system; the rules and their record are in [Channel breakout trend following](learn-strat-channel-breakout.md).

**Worked example (Apple, 3 September 2025).** The previous 20 bars' highest high was $235.12. Apple closed at $238.47, a new 20-day closing high, so a breakout rule would buy. The upper line then moved up to that day's high, $238.85.

```series
title: Tata Consultancy Services, Sep 2024 – Sep 2025 — a downtrend inside a Donchian channel
from: 2024-09-01
to: 2025-09-30
line: india:TCS.NS | TCS
line: india:TCS.NS@dc.upper | Donchian upper (20)
line: india:TCS.NS@dc.lower | Donchian lower (20)
line: india:TCS.NS@kc.lower | Keltner lower (20, 2, 10)
mark: 2025-02-28 | ₹3,483.25
caption: TCS fell about 36% over these 13 months. It closed below the previous 20 bars' low on 12% of sessions, and above their high on under 3%. The lower lines kept stepping down; the upper line flattened out between rallies.
```

**Pitfalls.** The width is set by one high and one low, so it jumps when an old extreme leaves the window. A single spike can hold the channel wide for 20 bars. Note also that the upper line, drawn with today's bar included, can never be beaten by today's close. Breakout rules compare with yesterday's line.

## 6. Moving-average envelopes — a fixed % either side

An envelope asks: is the close more than x% from its average? It draws the 20-day SMA and lines a fixed % above and below. A common default is 2.5%; traders also use 1% to 10%, set by eye for each stock.

```
Upper / Lower = SMA(close, 20) × (1 ± 2.5%)
```

**Worked example (Apple, 8 April 2025).** The close was $172.42 and the 20-day SMA $211.84. The 2.5% envelope ran from $206.55 to $217.14. The close was more than three envelope-widths below the lower line. The Bollinger Bands that day were about 27% wide; the envelope stayed at 5%.

The fixed % is the envelope's problem. A 2.5% move is a big day for Coca-Cola and an ordinary one for Super Micro. Here is the share of sessions with the close outside a 2.5% envelope, 2015 to October 2026:

| Stock | Outside the envelope | Outside Bollinger (20, 2) | Median Bollinger width |
|---|---|---|---|
| Coca-Cola (KO) | 26% | 12% | 5.4% |
| HDFC Bank (HDFCBANK.NS) | 38% | 12% | 7.1% |
| Apple (AAPL) | 56% | 13% | 10.4% |
| Nvidia (NVDA) | 70% | 12% | 16.6% |
| Super Micro (SMCI) | 71% | 12% | 20.5% |

The Bollinger breach rate stayed near 12% for all five, because its width scales with each stock. The envelope's rate ran from 26% to 71%. An envelope only works when its % is set for the one stock it is drawn on.

## 7. Two readings in every band: position and width

Every band gives two numbers. **Position** is where the close sits between the lines. **Width** is how far apart the lines are. Measured on hundreds of stocks, both repeat readings from other families.

| Band reading | Closest measured twin (US / India) | Also close to |
|---|---|---|
| Keltner position | RSI14 (0.98 / 0.98) | ATR-band position (0.98) |
| ATR-band position | Keltner position (0.98 / 0.98) | RSI14 (0.95) |
| Bollinger %B | CCI (0.98 / 0.98) | RSI14 (0.89) |
| Donchian position | Bollinger %B (0.94 / 0.94) | Williams %R (0.94 / 0.93) |
| Envelope position | Distance from 20-day VWAP (0.99 / 0.98) | 14-day % change (0.93 / 0.94) |
| Bollinger BandWidth | Standard deviation ÷ close (0.98 / 0.98) | ATR % (0.70 / 0.65) |

**Position is momentum.** A close high in a Keltner channel is a close well above its 20-day EMA, measured in ATR. That is close to what RSI measures. An envelope's position is just the % distance from the 20-day average, rescaled. The range-position readings — Stochastic, Williams %R, CCI — are in [Momentum I — where the close sits in its range](learn-ind-momentum-range.md).

**Width is volatility.** A Keltner channel's width is four ATRs, so it *is* ATR, drawn on the chart. Bollinger width is the standard deviation. Neither adds anything that ATR % or BandWidth do not already say; see [Volatility indicators — ATR, standard deviation, BandWidth, historical volatility, Mass Index, Ulcer Index, TTM Squeeze](learn-ind-volatility.md).

So a chart with Bollinger Bands, a Keltner channel and RSI shows one momentum opinion three times. What a band adds is a **picture**: the stretch drawn at the price, in the stock's own units.

## 8. The squeeze: Bollinger inside Keltner

When the Bollinger Bands contract inside the Keltner channel, closes have been unusually tightly bunched compared with the daily range. Traders call this a squeeze, and some read it as the calm before a large move. The idea and its test are in [Volatility indicators — ATR, standard deviation, BandWidth, historical volatility, Mass Index, Ulcer Index, TTM Squeeze](learn-ind-volatility.md). In short, on stored prices, the move after a squeeze ended was no larger than usual.

## 9. The family side by side

| Band | Question it answers | Defaults | Mostly repeats | Typical use |
|---|---|---|---|---|
| Bollinger Bands | Far from the average, in standard deviations? | 20, 2 | %B ≈ CCI, RSI; width ≈ standard deviation | Picture of stretch; mean reversion in ranges |
| Keltner Channel | Far from the average, in daily ranges? | 20 EMA, 2 × ATR(10) | Position ≈ RSI; width ≈ ATR | Extension checks; the squeeze |
| ATR bands | Same, round an SMA | 20 SMA, 2 × ATR(14) | Keltner | Stops and exits |
| Donchian Channel | Beyond the last n days' range? | 20 | Position ≈ %B, Williams %R | Breakout entries and exits |
| Envelope | More than x% from the average? | 20 SMA, 2.5% | Distance from the average | Only with a % set per stock |

## 10. What the evidence says

> **Method.** 300 US stocks (random, fixed seed) and 147 Indian stocks, each with at least 1,500 sessions since 2015 and high daily turnover. Daily bars, 2015 to October 2026, default settings. Breach rate: the share of sessions with the close above the upper or below the lower line. Overlap: correlation measured day by day within each stock (1 = move together exactly, 0 = no relation). Each figure is the median across stocks.

**How often the close was outside the band:**

| Band | US above | US below | India above | India below |
|---|---|---|---|---|
| Bollinger (20, 2) | 6.5% | 5.6% | 7.0% | 5.2% |
| Keltner (20, 2, 10) | 8.9% | 6.4% | 8.1% | 5.1% |
| Donchian (20, previous bars) | 7.2% | 5.4% | 6.4% | 4.8% |
| ATR bands (20, 14, 2) | 12.7% | 9.8% | 11.9% | 7.9% |
| Envelope (20, 2.5%) | 31.0% | 24.7% | 31.6% | 24.5% |

What it shows:

- **The volatility-based bands are breached about equally often.** Bollinger, Keltner and Donchian each had the close outside on about 11–15% of sessions. ATR bands, round a slower SMA, about 20–22%.
- **The fixed envelope was breached on more than half of all sessions.** For most stocks, 2.5% is less than an ordinary week's move.
- **Every band was breached more often on the upside.** Over 2015–2026 most of these stocks rose, and a rising stock sits above its average more often.
- **Position repeats momentum** (section 7). Keltner position and RSI14 correlated 0.98 in both markets.

Published research. John Bollinger's own rules for the bands say they do not give buy and sell signals on their own. Breakout rules of the Donchian kind were among the rules Brock, Lakonishok and LeBaron (1992) found useful on the Dow up to 1986. Sullivan, Timmermann and White (1999) found the best such rules did not keep working afterwards, once the number of rules tried was allowed for. How a lower-band entry performs in a range is in [Bollinger band mean reversion — buying the lower band in a range](learn-strat-bollinger-reversion.md).

**Limits.** The sample is today's listed stocks, so firms that failed are missing. A breach rate describes the band, not the return after a breach. High correlation means two readings move together day by day; it says nothing about predicting the next move. No costs are included.

## 11. Checklist

- [ ] Which width does this band use: fixed %, standard deviation, ATR, or the n-day extremes?
- [ ] If it is an envelope, is its % set for this stock's volatility?
- [ ] Am I reading the band's position as a separate opinion from RSI? It is the same one.
- [ ] Am I reading its width as separate from ATR % or BandWidth? It is the same one.
- [ ] For a breakout: am I comparing the close with the previous bars' extreme, not a line that includes today?
- [ ] Do my settings match the charting package someone else used? Keltner and Bollinger differ between packages.
- [ ] Is there a price level and a volume reason for the trade, beyond "outside the band"?

## Further reading

- John Bollinger, *Bollinger on Bollinger Bands* (2001) — the bands, %B and BandWidth from their author.
- Chester Keltner, *How to Make Money in Commodities* (1960) — the original channel.
- Curtis Faith, *Way of the Turtle* (2007) — Donchian breakouts in the Turtle traders' system.
- Brock, Lakonishok and LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns" (*Journal of Finance*, 1992).
- Sullivan, Timmermann and White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap" (*Journal of Finance*, 1999).
