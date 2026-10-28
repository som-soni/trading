# Indicators — trend and volatility: moving averages, ATR and ADX

**In short**

- An indicator is a formula on past prices. It knows nothing the bars do not already contain; it turns a judgement by eye into a number you can screen and write into rules.
- Moving averages smooth the price so its direction is easy to see. They serve as trend filters ("above a rising 200-day") and as levels where pullbacks often stop.
- ATR measures how much a stock moves each day, ignoring direction. As a % of the price it compares stocks, and it scales stops and filters to each stock.
- ADX measures how strongly the price is trending, up or down. It repeats almost nothing the direction-based indicators say, but it is slow.
- Use indicators as filters and flags. Take entries and stops from price levels.

The momentum indicators — RSI, MACD and Bollinger Bands — are in [the momentum indicators guide](learn-price-oscillators.md). That guide also measures how much indicators overlap, and maps which indicator answers which question. Every other indicator, sorted by family with its own guide, is in [Indicators — the map](learn-ind-map.md). For basic words, see [Start here](learn-start-here.md). For stages and trend in a stock, see [the stages guide](learn-price-stages.md); for volume, [the volume guide](learn-price-volume.md); for relative strength against the index, [the relative strength guide](learn-price-rs.md).

---

## 1. What an indicator is

"The stock has risen a lot lately" becomes "RSI 78". "It moves a lot each day" becomes "ATR is 4% of the price". That is what an indicator does: it turns something you could judge by eye into a number.

An indicator is a formula applied to a stock's past prices, and sometimes its volume. The inputs are the open, high, low, close and volume of each bar. **No indicator knows anything that the bars do not already contain.**

That has two uses. A number can be put in a screen and checked on 5,000 stocks at once. And a number can be written into a rule, so the rule is applied the same way every time.

It also has a cost. Each indicator throws some information away, and many of them throw away the same things. So two indicators can look different and say the same thing ([the overlap measurement in the momentum indicators guide](learn-price-oscillators.md)).

The useful question for any indicator is: **which question does it answer that the price chart alone does not answer clearly?**

## 2. Moving averages

### 2.1 What they compute

Take five closes and average them:

> closes 10, 11, 12, 11, 13 → sum 57 → 5-day SMA = 57 ÷ 5 = 11.4

That is a 5-day **simple moving average (SMA)**. Tomorrow the oldest close drops out and the new one is added. An SMA of N days is the average of the last N closes, each counting equally.

An **EMA** (exponential moving average) also averages past closes, but gives the newest close the most weight. Say a 21-day EMA is 100 and today closes at 110:

> new EMA = 100 + 0.091 × (110 − 100) = 100.9

The general rule is new EMA = old EMA + α × (close − old EMA), with α = 2 ÷ (N + 1). For 21 days, α is about 0.091. In a 21-day SMA, the new close would weigh only about 0.048 (one part in 21).

So an EMA turns sooner when the price turns. Two plain facts limit that advantage:

- **The average age of the data is the same.** With α = 2 ÷ (N + 1), an EMA and an SMA of the same N both use data that is, on average, (N − 1) ÷ 2 days old. The EMA reacts faster to the last few bars, but it still carries old prices.
- **Faster also means more false turns.** A line that reacts sooner also reacts to moves that reverse the next week.

### 2.2 The usual lengths

| Length | Usual use |
|---|---|
| 10-day EMA | The path of a fast-moving leader; a tight trailing exit |
| 20/21-day (SMA or EMA) | Short-term trend; where a strong stock usually pulls back to |
| 50-day SMA | Intermediate trend; the line institutions are said to defend |
| 150-day SMA (≈ 30 weeks) | Weinstein's stage line on a daily chart |
| 200-day SMA | Long-term trend; the most common trend filter |
| 30-week average | The same idea on a weekly chart (see [the stages guide](learn-price-stages.md)) |

None of these numbers is special. They are conventions. The 10-day and 21-day EMAs are popular among momentum traders. The 20-day is just as common, and any length can be drawn on a chart.

### 2.3 As trend filters

A trend filter is a yes/no test: is the stock in an uptrend? Moving averages answer it in several common ways:

- **The Trend Template** (Minervini): the close is above the 50-, 150- and 200-day; the 50-day is above the 150-day, which is above the 200-day; the 200-day is higher than it was a month (21 sessions) ago. With them: at least 30% above the 52-week low, and at most 25% below the 52-week high. See [the stages guide](learn-price-stages.md).
- **A weekly-and-daily uptrend**: the weekly close is above a rising 30-week EMA, and the 20-week average is above the 50-week. On the daily chart the 50-day is above the 200-day. The price has not broken down through the 50-day: not more than 2 ATR below it, and not 5 closes in a row under it.
- **"Falling" needs a definition.** A typical one: the 50-day is falling when it is more than 1% below its value 10 sessions ago. The 200-day is falling when it is more than 0.5% below its value 20 sessions ago. Anything in between is "flat".

What a filter adds: a clear answer you can apply to every stock the same way. What it repeats: the price itself. "Above a rising 200-day" is a way of saying "higher than its average of the last ten months, and that average is going up".

### 2.4 As pullback levels

```series
title: Nvidia with its 21-day EMA and 50-day average, 2023 to mid-2024
from: 2023-01-01
to: 2024-06-30
line: us:NVDA | Nvidia | log
line: us:NVDA@ema21 | 21-day EMA
line: us:NVDA@sma50 | 50-day average
caption: In this run of about +760%, Nvidia closed above its 50-day on 328 of 374 sessions. The dips to the 21-day and 50-day were where a pullback buyer looked. The sideways stretch from August to early November 2023 is where the price crossed the 50-day back and forth.
```

Over these 18 months Nvidia crossed its 50-day 15 times. Most crossings came in two sideways stretches: August–November 2023 and April–May 2024. In a trend, the average is a useful level. In a sideways stretch it is crossed every few days and tells you little.

In a strong uptrend, the price often dips back to a short average and then continues. Traders use the 20/21-day or the 50-day as the place to look for a low-risk entry. A typical mechanical version has four parts:

- **Near the average:** the close is within 1 ATR of a rising 50-day. That marks a pullback worth watching.
- **Not extended:** a close more than 2.5 ATR above the 20-day, or an RSI above 75, means wait for a pullback toward the 20-day.
- **The turn:** the entry needs a close back above the 20-day and above a recent high. You buy the turn back up, not the dip itself.
- **Warning:** a close below the 50-day while the longer trend still holds means wait for a trigger before buying.

Be careful about evidence. Brock, Lakonishok and LeBaron (1992) found that simple moving-average rules on the Dow Jones index had predictive power over 1897–1986. Sullivan, Timmermann and White (1999) then allowed for the many rules that had been tried. The best rule did not keep working after 1986. Buying pullbacks to an average is a common method, not a proven one; [Pullback to a moving average](learn-strat-pullback-ma.md) sets out how to trade and test it.

### 2.5 What moving averages add and what they repeat

They add **a smoothed line that makes the direction easy to see**, and a level to measure distance from. They repeat the price: every moving average is just past closes. Distance from the 50-day is one of the most overlapping numbers in [the overlap measurement](learn-price-oscillators.md). It moves with RSI almost one for one.

## 3. ATR — how much a stock moves

### 3.1 What it computes

Say the previous close is 100. Today the high is 104 and the low is 101. The day's range is 3, but the price moved 4 from the previous close. So the **true range** is 4.

The true range of a day is the largest of: high − low; |high − previous close|; |low − previous close|. The last two catch gaps. **ATR14** is a 14-day average of the true range, smoothed the way Wilder smoothed it:

> new ATR = old ATR + (true range − old ATR) ÷ 14

**ATR is in price units**: dollars or rupees per day. That makes it useful for one stock (where to put a stop) and useless for comparing two stocks. **ATR %** (ATR ÷ close × 100) fixes that.

| Stock (Oct 2025 – Oct 2026) | Median ATR14 | Median ATR % |
|---|---|---|
| Coca-Cola (KO) | $1.27 | 1.6% |
| Apple (AAPL) | $6.06 | 2.2% |
| Nvidia (NVDA) | $6.41 | 3.3% |
| Super Micro (SMCI) | $2.27 | 6.3% |
| Reliance (RELIANCE.NS) | ₹23.15 | 1.8% |
| HDFC Bank (HDFCBANK.NS) | ₹14.66 | 1.8% |

Apple and Nvidia have almost the same ATR in dollars. Nvidia moves half as much again as a share of its price. Super Micro has the smallest dollar ATR of the four US stocks and by far the largest ATR %.

```series
title: ATR as a % of the price — three very different stocks, 2022–2026
from: 2022-01-01
line: us:KO@atrp14 | Coca-Cola ATR %
line: us:NVDA@atrp14 | Nvidia ATR %
line: us:SMCI@atrp14 | Super Micro ATR %
caption: Median since 2022: Coca-Cola about 1.5%, Nvidia about 3.8%, Super Micro about 6.1%. Volatility also changes over time: Nvidia went from 8.4% in May 2022 to 2.1% in July 2025, and Super Micro reached 20% in November 2024.
```

### 3.2 What it adds and what it repeats

ATR adds something the closing-price indicators do not: **the size of the moves, ignoring their direction**. RSI, MACD and moving averages all ask "up or down, and how much?" ATR asks "how much does it swing?"

In [the overlap measurement](learn-price-oscillators.md), ATR % has only a weak relation to the others. Its correlations ran between about −0.5 and 0.1. It does repeat what you can see from the height of the candles.

### 3.3 How traders use ATR

ATR turns fixed rules into rules scaled to each stock. A 3% stop is wide for Coca-Cola and inside the daily noise for Super Micro. Common uses, with typical values:

- **Too quiet:** skip stocks with ATR % at or below about 1.5. They rarely move far enough to pay for the trade.
- **Too wild:** skip stocks with ATR % above about 8 to 10. Their stops have to be very wide.
- **Extension:** a close more than about 2.5 ATR above the 20-day is stretched; more than 4 ATR is often a reason to pass.
- **Zones, not lines:** a breakout counts only when the close clears the base high by about 1 ATR. A level within 1 ATR of another is treated as the same zone.
- **Stops:** a stop about 2 ATR below entry is a common default. Many traders keep a stop between about 0.6 and 2 ATR from entry. A trailing stop might follow 3 ATR under the highest close.
- **Pattern detection:** what counts as a real swing can be scaled by ATR %. A fixed percentage is noise on one stock and a big move on another.

Position size comes from the distance between entry and stop, not from ATR directly. How ATR-based stops lead to equal risk per trade is in [the position sizing guide](learn-risk-sizing.md). How wide a stop should be is in [the stops guide](learn-risk-stops-exits.md).

## 4. ADX — trend strength without direction

### 4.1 What it computes

A stock falling steadily has a high ADX, just like one rising steadily. ADX was designed by Wilder to measure **how strongly the price is trending, up or down**. The steps:

1. **+DM** is today's high minus yesterday's high, if that is positive and larger than the move down; otherwise 0. **−DM** is the same for lows.
2. Each is smoothed over 14 days and divided by ATR14. That gives **+DI** and **−DI**: the share of the recent range that was upward and downward movement.
3. **DX** = |+DI − −DI| ÷ (+DI + −DI) × 100. **ADX** is DX smoothed over 14 days.

ADX under about 20 is usually read as no trend; above about 25 as a trend. Above 40 it reads as a strong, often late, trend. These are conventions.

### 4.2 What it adds and what it repeats

ADX is one of the few indicators here that does **not** repeat RSI or MACD. In [the overlap measurement](learn-price-oscillators.md), its correlation with every direction-based indicator is close to zero (−0.06 to 0.14). It answers a different question: is the price moving in one direction, or back and forth?

It does lag. Two rounds of 14-day smoothing make it slow to rise at the start of a trend and slow to fall at the end.

### 4.3 How traders use ADX

ADX is mostly used as a filter on a trend-following setup, not as a signal:

- **Minimum trend:** require ADX14 above about 15, or treat 15 to 20 as a weak trend — a base or a drift.
- **Fading:** ADX lower than it was five sessions ago is sometimes read as momentum fading.
- **Late move:** ADX above 40 while the price is far above its 20-day suggests a late, stretched move.

Most charting packages draw it as a "Directional Movement Index" study, which shows ADX, +DI and −DI together.

## 5. What the evidence says

- **Robust: moving-average trend filters reduce the deepest drawdowns** on indices, by keeping you out during long bear markets. They usually do not raise returns after whipsaws and costs. This is shown for the index in [the trend guide](learn-health-trend.md).
- **Weak: simple indicator rules as trading signals.** Early studies found moving-average rules on the Dow had predictive power (Brock, Lakonishok and LeBaron, 1992). After allowing for the many rules tried, the effect did not survive after 1986 (Sullivan, Timmermann and White, 1999).
- **Built in: lag.** Every indicator here uses past bars. Smoothing reduces false signals and adds delay. You cannot have both fewer false signals and less delay from the same data.
- **Good practice:** use indicators as filters and flags, not as entry signals. Take entries from price levels: a pivot, a recent high, a channel high. Take stops from a pullback low or a base low, limited in ATR.

For the momentum indicators, the research on single-indicator rules and the measured overlap, see [the momentum indicators guide](learn-price-oscillators.md).

## 6. Checklist

- [ ] For each indicator on my chart: which question does it answer? Do two of them answer the same one?
- [ ] Trend: is the stock above a rising 50- and 200-day, or is the line flat and being crossed every few days?
- [ ] Volatility: what is its ATR %? Is my stop at least about one ATR away?
- [ ] Extension: how many ATR is the close above the 20- and 50-day? (About 2.5 above the 20-day is stretched; 4 is a reason to pass.)
- [ ] Am I acting on an indicator alone, without a price level for entry and stop?

## Further reading

- J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) — the original RSI, ATR, ADX and Parabolic SAR.
- Brock, Lakonishok and LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns" (*Journal of Finance*, 1992).
- Sullivan, Timmermann and White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap" (*Journal of Finance*, 1999).
