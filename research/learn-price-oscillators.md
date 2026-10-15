# Momentum indicators — RSI, MACD and Bollinger Bands, and how much they overlap

Learning material on the indicators that describe **how fast a stock has moved
lately**: RSI, MACD and Bollinger Bands. For each one: what it computes, what
question it answers, what it adds to the price chart and what it only repeats,
the usual settings, and how this app computes and uses it. Then the Chart
page's full list of studies, a measurement of how much these indicators
overlap on the app's own stored prices, what the evidence says, and a table of
which indicator answers which question. Moving averages, ATR and ADX — the
trend and volatility indicators — are in [the trend and volatility indicators
guide](learn-price-indicators.md), which also explains what an indicator is.
For basic words, see [Start here](learn-start-here.md).

**Where this shows in the app.** The Chart page has an **Indicators** button.
It opens a picker of 35 studies (listed in §4), computed in your browser from
the chart's own bars (`web/static/studies.js`). The screening code computes
RSI14 for every stock each day (`core/indicators.py`); MACD and Bollinger Bands
are computed only on the Chart page and in these guides' charts. Each
strategy's **Setups today** table has an RSI column, and the **Screens**
builder offers RSI 14 as a field.

**The data in this guide.** Charts are drawn from the app's stored daily
prices. The overlap measurements in §5 use 300 randomly chosen US stocks and
145 Indian stocks, 2015 to October 2026 (method in §5).

---


## 1. RSI — the speed of recent moves

### 1.1 What it computes

RSI compares the size of recent up-days with the size of recent down-days.
Each day, the gain is the rise from the previous close (0 on a down-day) and
the loss is the fall (0 on an up-day). Both are averaged with Wilder's
smoothing over 14 days. Then RS = average gain ÷ average loss, and
RSI = 100 − 100 ÷ (1 + RS).

Worked example: the average gain is 1.0 and the average loss is 0.5. RS is 2,
and RSI = 100 − 100 ÷ 3 = 66.7. If there were no losses at all, RSI would be
100. Equal gains and losses give 50.

Wilder's 14-day smoothing uses α = 1/14. That is the same as an ordinary EMA of
about 27 days, so RSI14 remembers more than the "14" suggests.

### 1.2 Overbought and oversold — and why a leader stays "overbought"

The usual readings: above 70 is called **overbought**, below 30 **oversold**.
The words suggest the price must come back. It need not. RSI above 70 means
only that **the recent up-days have been much bigger than the down-days**.
That is exactly what a strong uptrend looks like.

```series
title: Nvidia's RSI14 during its 2023–24 advance
from: 2023-01-01
to: 2024-06-30
line: us:NVDA | Nvidia | log
line: us:NVDA@rsi14 | RSI 14 | pane2
caption: RSI was above 70 on 95 of 374 sessions (25%) and above 50 on 83% of them. It never reached 30: the low was 31.4 on 21 September 2023. The first reading above 70 came on 25 January 2023, at $19.32 split-adjusted; the stock ended June 2024 at $123.5.
```

A trader who sold every time RSI crossed 70 would have sold Nvidia about 20
times in this run. In India, Trent (TRENT.NS) rose about 458% from April 2023
to September 2024. Its RSI14 was above 70 on 47% of those sessions and never
fell below 40.5. **In a leader, a high RSI is a description of strength, not a
signal to sell.** RSI is more useful in the other direction: a leader whose
RSI cannot get back above 50 or 60 after a pullback is losing speed.

What does a high or low RSI say about the next month across all stocks? On the
§5 sample (overlapping 21-session windows, pooled across stocks, no costs):

| Next 21 sessions | US: all days | US: RSI > 70 | US: RSI < 30 | India: all days | India: RSI > 70 | India: RSI < 30 |
|---|---|---|---|---|---|---|
| Share of days | 100% | 6.4% | 4.0% | 100% | 7.1% | 3.8% |
| Mean return | +1.2% | +0.8% | +2.2% | +1.4% | +2.3% | +1.7% |
| Share of rises | 53.9% | 51.5% | 56.9% | 54.6% | 57.7% | 55.6% |

The differences are small and point in **opposite directions** in the two
markets. In the US, oversold stocks did a little better and overbought a
little worse. In India it was the other way round. Neither result is a
trading rule. "Overbought" was not, on average, followed by a fall in either
market.

### 1.3 RSI is not relative strength

The names are confusing. **RSI** compares a stock with **its own** recent
past. **Relative strength** compares a stock's performance **with the index or
with other stocks**. A stock can have RSI 75 (it rose fast this fortnight)
and a weak RS rank (it is still far behind the market over a year). The app's
RS rank is a different calculation. See [the relative strength
guide](learn-price-rs.md).

### 1.4 How the app uses RSI

RSI14 is stored for every stock and day. Strategies use it only as a **watch
flag**, never as a buy signal:

- Trend pullback: **X1** when RSI14 is above 75 (extended; caps at WATCH -
  WAIT), and **X8** when RSI14 is below 40 while the close is above the 50-day
  (weak momentum; caps at TRADE ON TRIGGER).
- Breakout: **XB3** when RSI14 is above 80 (caps at TRADE ON TRIGGER).
- Chart patterns: **XS3** when RSI14 is above `OVERBOUGHT_RSI` = 80 (caps at
  TRADE ON TRIGGER).

A 14-day SMA of RSI (`rsi_ma`) is also computed and stored. No current rule
reads it. The Quality page shows RSI beside each company's valuation.

## 2. MACD — the gap between a fast and a slow average

### 2.1 What it computes

The **MACD line** is the 12-day EMA minus the 26-day EMA. When the short
average is above the long one, the line is positive: recent prices are above
older ones. The **signal line** is a 9-day EMA of the MACD line. The
**histogram** is the MACD line minus the signal line.

Worked example: the 12-day EMA is 105 and the 26-day EMA is 100, so MACD is 5.
If the signal line is 4, the histogram is +1: the gap between the averages is
wider than its own recent average, so it has been widening. A MACD "buy" is the MACD line crossing above the signal line;
a "sell" is crossing below.

MACD is in price units, like ATR. A MACD of 5 means something different on a
$50 stock and a $500 stock.

### 2.2 Lag, and crossings in a falling stock

MACD is built from averages of averages, so it is late by design. It is also
crossed often when a stock moves sideways or falls in steps.

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

Here the first sell came quickly. The cost came afterwards: four buy signals
in a falling stock. Over these eight months the two lines crossed 14 times.

### 2.3 What it adds and what it repeats

The MACD line is close to "how far is the price above its recent average"
(§5: correlation 0.94 with the distance from the 50-day). The histogram is
close to "how much did the price change in the last two or three weeks"
(0.77 with the 14-day % change). **MACD repeats the moving averages.** It adds
a single number for "the short-term trend is speeding up or slowing down".

**The app's screening code does not compute MACD.** It is available as a study
on the Chart page and as a chart line in these guides.

## 3. Bollinger Bands — volatility envelopes and the squeeze

### 3.1 What they compute

The middle band is the 20-day SMA. The upper and lower bands are 2 standard
deviations of the last 20 closes above and below it. Standard deviation
measures how spread out the closes are. Worked example: the 20-day SMA is 100
and the standard deviation is 2. The bands are at 96 and 104.

Two numbers come from the bands:

- **%B**: where the close sits between the bands (0 = on the lower band, 1 =
  on the upper).
- **Bandwidth**: (upper − lower) ÷ middle. In the example, 8 ÷ 100 = 8%.

### 3.2 The squeeze

A **squeeze** is when the bands come unusually close together: the stock has
been very quiet. Many traders read a squeeze as the calm before a large move.
That idea comes from Bollinger himself. The bands do not say which way the
move will go.

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

Is a squeeze followed by a bigger move? On the §5 sample, we marked each day
when the 20-day bandwidth was the lowest of the last 125 sessions, and
measured the next 21 sessions:

| Next 21 sessions | US: all days | US: after a squeeze | India: all days | India: after a squeeze |
|---|---|---|---|---|
| Median size of the move (up or down) | 5.7% | 5.3% | 5.7% | 5.7% |
| Share moving more than 10% | 27.7% | 24.9% | 26.0% | 24.7% |
| Share of rises | 53.9% | 51.9% | 54.5% | 52.1% |

**After a squeeze, the next month's move was no larger than usual.** A quiet
stock tends to stay fairly quiet. A squeeze is a description of a tight range.
It needs something else, such as a breakout on volume or a results date, to
become a trade. That is how the app's own base and VCP rules use tightness:
together with a pivot and volume (see [the VCP guide](learn-vcp.md)).

### 3.3 What they add and what they repeat

%B repeats RSI (§5: correlation 0.89). The bandwidth repeats ATR % in a
different form. Bollinger Bands are useful mainly as **a picture**: they show
on one chart how far the price is from its average, measured in its own
volatility.

**The app's screening code does not compute Bollinger Bands.** They are on the
Chart page (Bollinger Bands, Bollinger BandWidth). One small difference: the
Chart page uses the population standard deviation (as TradingView does), and
the charts in these guides use the sample standard deviation. For 20 days the
bands' distance from the middle differs by about 2.6%.

## 4. The Chart page's studies

Indicators → a searchable picker. The studies are computed in the browser from
the bars on screen, so they work on daily, weekly and monthly charts. The
chosen list is saved in your browser and applies to every symbol. On first use
the chart starts with the 20-, 50- and 200-day SMA, Volume and RSI.

| Category | Studies (default settings) |
|---|---|
| Screener | Screener levels (entry / stop / target); Chart patterns (live detection) |
| Moving averages | Moving Average (SMA 20); Moving Average Exponential (EMA 20); Moving Average Weighted (20); Moving Average Ribbon, SMA and EMA versions (20/50/100/200) |
| Bands & channels | Bollinger Bands (20, 2); Keltner Channels (20-day EMA ± 2 × 10-day ATR); Donchian Channels (20) |
| Support & resistance | Pivot Points High Low (10/10); Pivot Points Standard (Traditional, Fibonacci or Camarilla); Support & Resistance swing levels (250-bar lookback) |
| Trend | Parabolic SAR (0.02/0.02/0.2); Supertrend (10, 3); Ichimoku Cloud lines (9/26/52); Directional Movement Index (ADX 14); Aroon (14); Relative Strength vs index (50-day MA) |
| Momentum | RSI (14; lines at 70/50/30); MACD (12/26/9); Stochastic (14/3/3); Stochastic RSI (14/14/3/3); Commodity Channel Index (20); Williams %R (14); Rate of Change (9); Momentum (10) |
| Volatility | Average True Range (14); ATR % of price (14); Bollinger BandWidth (20, 2) |
| Volume | Volume (with a 20-bar average); Rolling VWAP (20); Money Flow Index (14); On Balance Volume; Chaikin Money Flow (20) |

The Chart page's formulas follow TradingView's (Wilder smoothing for RSI, ATR
and ADX). Its EMAs start from an SMA of the first N bars, while the screening
code starts from the first close. The two agree after the first few dozen bars.
The two "Screener" studies are not indicators: they draw a strategy's levels
and its pattern detector's findings (see [the chart patterns
guide](learn-chart-patterns.md)).

## 5. How much they overlap — measured

**Method.** Stocks in the app's price table with at least 1,500 sessions since
2015 and a median daily traded value above the market's liquidity floor ($10m
in the US, ₹50 crore in India). A random 300 in the US; all 145 that qualify
in India. For each stock, each indicator was computed over 2015–2026 and the
correlations were measured day by day within that stock. The table shows the
median across stocks. A correlation of 1 means two numbers move together
exactly; 0 means no relation. The stocks are ones stored today, so some
survivorship bias is possible.

| Median correlation (US / India) | RSI14 | MACD histogram | 14-day % change | Distance from 50-day | Bollinger %B |
|---|---|---|---|---|---|
| RSI14 | 1 | 0.58 / 0.60 | 0.81 / 0.84 | 0.88 / 0.89 | 0.89 / 0.89 |
| MACD line (÷ price) | 0.78 / 0.80 | 0.36 / 0.34 | 0.73 / 0.75 | 0.94 / 0.95 | 0.54 / 0.56 |
| MACD histogram | 0.58 / 0.60 | 1 | 0.77 / 0.77 | 0.40 / 0.39 | 0.69 / 0.71 |
| ADX14 | 0.07 / 0.14 | −0.04 / 0.00 | 0.00 / 0.08 | 0.03 / 0.12 | 0.02 / 0.06 |
| ATR % | −0.28 / −0.23 | −0.09 / −0.12 | −0.23 / −0.20 | −0.40 / −0.29 | −0.18 / −0.17 |

What it shows:

- **RSI14, %B and the distance from the 50-day are nearly the same number**
  (0.88–0.89). The **MACD line** is almost exactly the distance from an average
  (0.94–0.95). The **MACD histogram** is mostly the recent % change (0.77).
- **RSI14 and the plain 14-day % change** correlate at 0.81 in the US and 0.84
  in India. Ranked correlations, which ignore outliers, give 0.85 and 0.86.
- **ADX and ATR % measure something else**: trend steadiness and swing size.
  ADX's correlations with the direction indicators are near zero. ATR %'s are
  weak and negative (about −0.1 to −0.5): within a stock, volatility tends to
  be higher when the price is below its averages.
- The two markets give almost the same table.

```series
title: Apple in 2024 — RSI14 against the plain 14-day % change
from: 2024-01-01
to: 2024-12-31
line: us:AAPL@rsi14 | RSI 14
line: us:AAPL@chg14 | 14-day % change | right
caption: Two indicators, one story. In 2024 the two lines had a correlation of 0.89 for Apple. They differ mainly at the extremes: RSI's low was on 7 March; the 14-day change's low was on 5 August.
```

**So what?** Putting RSI, MACD and Stochastic on one chart does not give three
opinions. It gives one opinion three times. A useful set of indicators covers
**different questions**: one for trend (a moving average), one for swing size
(ATR), perhaps one for trend steadiness (ADX), plus volume (see [the volume
guide](learn-price-volume.md)) and comparison with the market (see [the
relative strength guide](learn-price-rs.md)).

## 6. What the evidence says

- **Robust: moving-average trend filters reduce the deepest drawdowns** on
  indices, by keeping you out during long bear markets. They usually do not
  raise returns after whipsaws and costs. This is shown for the index in [the
  trend guide](learn-health-trend.md).
- **Robust: medium-term momentum** (the past 3–12 months' return, ranked
  across stocks) has predicted the next months' return in many markets and
  decades (Jegadeesh and Titman, 1993, and many studies since). That is a
  **cross-sectional** comparison between stocks. It is what the app's RS rank
  and 12-1 momentum measure. It is not RSI.
- **Mixed: rules based on a single indicator.** Brock, Lakonishok and LeBaron
  (1992) found that simple moving-average and range-breakout rules on the Dow
  had predictive power in data up to 1986. Sullivan, Timmermann and White
  (1999) showed that, once you allow for how many rules had been tried, the
  best rule's results did not hold in the following years. Park and Irwin's
  survey (2007) found many positive studies, and also widespread problems:
  testing many rules on the same data, ignoring costs, and choosing rules
  after the fact.
- **Folklore: "overbought means sell"** and **"a squeeze means a big move is
  coming"**. On this app's stored prices, neither held on average (§1.2, §3.2).
- **Built in: lag.** Every indicator here uses past bars. Smoothing reduces
  false signals and adds delay. You cannot have both fewer false signals and
  less delay from the same data.
- **Measured here: overlap.** Most momentum indicators are close to the same
  number (§5). Adding more of them adds confidence without adding information.
- **The app's own rules use indicators as filters and flags**, not as entry
  signals. Entries come from price levels: a pivot, a recent high, a channel
  high. Stops come from a pullback low or a base low, limited in ATR. No
  strategy in the app uses an indicator crossing as its entry.

## 7. Which indicator answers which question

| Question | Indicator | What it repeats | In the app |
|---|---|---|---|
| Is the stock in an uptrend? | 50/150/200-day SMA, and its slope | The price over months | Stage 2 and uptrend screens |
| Where might a pullback stop? | 20/21-day or 50-day average | Recent average price | Trend pullback X3, resumption above the 20-day |
| How much does it move per day? | ATR14 | Candle height | Stops, extension, volatility limits |
| Is it more volatile than another stock? | ATR % | — | Pre-screen (1.5%), D6/B6 (8%), S4 (10%) |
| How fast has it risen lately? | RSI14, 14-day % change | Each other | Watch flags X1, X8, XB3, XS3 |
| Is short-term momentum speeding up? | MACD histogram | The recent % change | Chart page only |
| Is it far from its average for its volatility? | Bollinger %B, ATR distance from an average | RSI | Extension checks use ATR |
| Has it gone unusually quiet? | Bollinger bandwidth, ATR % against its own past | ATR | Base and VCP tightness rules |
| Is the move steady in one direction? | ADX14 | — | Trend pullback pre-screen, X5–X7 |
| Is it beating the market? | Relative strength line or RS rank | Not RSI | RS rank (see [relative strength](learn-price-rs.md)) |

## 8. Checklist

- [ ] For each indicator on my chart: which question does it answer? Do two of
  them answer the same one?
- [ ] Trend: is the stock above a rising 50- and 200-day, or is the line flat
  and being crossed every few days?
- [ ] Volatility: what is its ATR %? Is my stop at least about one ATR away?
- [ ] Extension: how many ATR is the close above the 20- and 50-day? (Trend
  pullback flags 2.5 above the 20-day; breakout rejects 4.)
- [ ] RSI above 70 in a leader: am I reading strength as a sell signal?
- [ ] RSI below 40–50 after a pullback in a leader: is momentum fading?
- [ ] A squeeze: what will make it move — a pivot, volume, a results date?
- [ ] Am I acting on an indicator alone, without a price level for entry and
  stop?

## Further reading

- J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) — the
  original RSI, ATR, ADX and Parabolic SAR.
- Gerald Appel, *Technical Analysis: Power Tools for Active Investors* (2005)
  — MACD from its author.
- John Bollinger, *Bollinger on Bollinger Bands* (2001) — the bands, %B,
  bandwidth and the squeeze.
- Brock, Lakonishok and LeBaron, "Simple Technical Trading Rules and the
  Stochastic Properties of Stock Returns" (*Journal of Finance*, 1992).
- Sullivan, Timmermann and White, "Data-Snooping, Technical Trading Rule
  Performance, and the Bootstrap" (*Journal of Finance*, 1999).
- Park and Irwin, "What Do We Know About the Profitability of Technical
  Analysis?" (*Journal of Economic Surveys*, 2007).
- Jegadeesh and Titman, "Returns to Buying Winners and Selling Losers"
  (*Journal of Finance*, 1993) — momentum across stocks.
