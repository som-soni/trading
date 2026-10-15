# App notes moved out of learn-price-oscillators (verbatim)

## Intro (app framing)
Learning material on the indicators that describe **how fast a stock has moved
lately**: RSI, MACD and Bollinger Bands. For each one: what it computes, what
question it answers, what it adds to the price chart and what it only repeats,
the usual settings, and how this app computes and uses it. Then the Chart
page's full list of studies, a measurement of how much these indicators
overlap on the app's own stored prices, what the evidence says, and a table of
which indicator answers which question. Moving averages, ATR and ADX — the

## "Where this shows in the app" and data note
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

## §1.3 (app RS rank note)
and a weak RS rank (it is still far behind the market over a year). The app's
RS rank is a different calculation. See [the relative strength
guide](learn-price-rs.md).

## §1.4 How the app uses RSI
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

## §2.3 (MACD not in screening code)
**The app's screening code does not compute MACD.** It is available as a study
on the Chart page and as a chart line in these guides.

## §3.2 (app base/VCP rules)
It needs something else, such as a breakout on volume or a results date, to
become a trade. That is how the app's own base and VCP rules use tightness:
together with a pivot and volume (see [the VCP guide](learn-vcp.md)).

## §3.3 (Bollinger Bands on the Chart page; population vs sample std dev)
**The app's screening code does not compute Bollinger Bands.** They are on the
Chart page (Bollinger Bands, Bollinger BandWidth). One small difference: the
Chart page uses the population standard deviation (as TradingView does), and
the charts in these guides use the sample standard deviation. For 20 days the
bands' distance from the middle differs by about 2.6%.

## §4 The Chart page's studies (whole section)
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

## §5 Method (app price table)
**Method.** Stocks in the app's price table with at least 1,500 sessions since
2015 and a median daily traded value above the market's liquidity floor ($10m
in the US, ₹50 crore in India). A random 300 in the US; all 145 that qualify
in India. For each stock, each indicator was computed over 2015–2026 and the
correlations were measured day by day within that stock. The table shows the
median across stocks. A correlation of 1 means two numbers move together
exactly; 0 means no relation. The stocks are ones stored today, so some
survivorship bias is possible.

## §6 evidence bullets referring to the app
- **Robust: medium-term momentum** (the past 3–12 months' return, ranked
  across stocks) has predicted the next months' return in many markets and
  decades (Jegadeesh and Titman, 1993, and many studies since). That is a
  **cross-sectional** comparison between stocks. It is what the app's RS rank
  and 12-1 momentum measure. It is not RSI.
- **Folklore: "overbought means sell"** and **"a squeeze means a big move is
  coming"**. On this app's stored prices, neither held on average (§1.2, §3.2).
- **The app's own rules use indicators as filters and flags**, not as entry
  signals. Entries come from price levels: a pivot, a recent high, a channel
  high. Stops come from a pullback low or a base low, limited in ATR. No
  strategy in the app uses an indicator crossing as its entry.

## §7 Which indicator answers which question (with the "In the app" column)
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

## §8 Checklist (app thresholds)
- [ ] Extension: how many ATR is the close above the 20- and 50-day? (Trend
  pullback flags 2.5 above the 20-day; breakout rejects 4.)
