# Indicators — trend and volatility: moving averages, ATR and ADX

Learning material on the indicators that describe a stock's **trend** and how
much it **moves**: moving averages, ATR and ADX. For each one: what it
computes, what question it answers, what it adds to the price chart and what it
only repeats, the usual settings, and how this app computes and uses it. The
momentum indicators — RSI, MACD and Bollinger Bands — are in [the momentum
indicators guide](learn-price-oscillators.md), together with the Chart page's
full list of studies, a measurement of how much indicators overlap, and a table
of which indicator answers which question. For basic words, see [Start
here](learn-start-here.md). For stages and trend in a stock, see [the stages
guide](learn-price-stages.md); for volume, [the volume
guide](learn-price-volume.md); for relative strength against the index, [the
relative strength guide](learn-price-rs.md).

**Where this shows in the app.** The Chart page has an **Indicators** button
that opens a picker of studies, computed in your browser from the chart's own
bars (`web/static/studies.js`; the full list is in [the momentum indicators
guide](learn-price-oscillators.md)). The screening code computes a smaller
fixed set for every stock each day (`core/indicators.py`, `enrich_daily`): the
20-, 50-, 100-, 150- and 200-day simple averages, a 20-day EMA, RSI14, ATR14,
ATR as a % of the close, ADX14, a 50-day volume average, the 52-week high and
low, and 12-1 month momentum. The **Screens** builder offers several of them
as fields (SMA 20/50/150/200, EMA 20, ATR %, ADX 14, RSI 14). The rules that
use them are on each strategy's **Strategies** page.

**The data in this guide.** Charts are drawn from the app's stored daily
prices.

---


## 1. What an indicator is

An indicator is a formula applied to a stock's past prices, and sometimes its
volume. The inputs are the open, high, low, close and volume of each bar.
**No indicator knows anything that the bars do not already contain.** What an
indicator does is turn something you could judge by eye into a number. "The
stock has risen a lot lately" becomes "RSI 78". "It moves a lot each day"
becomes "ATR is 4% of the price".

That has two uses. A number can be put in a screen and checked on 5,000 stocks
at once. And a number can be written into a rule, so the rule is applied the
same way every time. It also has a cost. Each indicator throws some
information away, and many of them throw away the same things, so two
indicators can look different and say the same thing ([the overlap measurement in the momentum indicators guide](learn-price-oscillators.md)).

The useful question for any indicator is: **which question does it answer
that the price chart alone does not answer clearly?**

## 2. Moving averages

### 2.1 What they compute

A **simple moving average (SMA)** of N days is the average of the last N
closes. Worked example: closes of 10, 11, 12, 11 and 13 give a 5-day SMA of
57 ÷ 5 = 11.4. Tomorrow the oldest close (10) drops out and the new one is
added. Every close in the window counts equally.

An **EMA** also averages past closes, but gives the newest close the most
weight. Each day: new EMA = old EMA + α × (close − old EMA), with
α = 2 ÷ (N + 1). For a 21-day EMA, α = 2 ÷ 22 ≈ 0.091. Worked example: the
21-day EMA is 100 and today closes at 110. The new EMA is
100 + 0.091 × 10 = 100.9. In a 21-day SMA, the same new close has a weight of
1 ÷ 21 ≈ 0.048.

So an EMA turns sooner when the price turns. Two plain facts limit that
advantage:

- **The average age of the data is the same.** With α = 2 ÷ (N + 1), an EMA
  and an SMA of the same N both use data that is, on average, (N − 1) ÷ 2
  days old. The EMA reacts faster to the last few bars, but it still carries
  old prices.
- **Faster also means more false turns.** A line that reacts sooner also
  reacts to moves that reverse the next week.

### 2.2 The usual lengths

| Length | Usual use |
|---|---|
| 10-day EMA | The path of a fast-moving leader; a tight trailing exit |
| 20/21-day (SMA or EMA) | Short-term trend; where a strong stock usually pulls back to |
| 50-day SMA | Intermediate trend; the line institutions are said to defend |
| 150-day SMA (≈ 30 weeks) | Weinstein's stage line on a daily chart |
| 200-day SMA | Long-term trend; the most common trend filter |
| 30-week average | The same idea on a weekly chart (see [the stages guide](learn-price-stages.md)) |

None of these numbers is special. They are conventions. The 10-day and
21-day EMAs are popular among momentum traders, but **this app does not
compute a 10- or 21-day line in its screening code**. Its short line is the
20-day (SMA and EMA). You can draw any length on the Chart page.

### 2.3 As trend filters

A trend filter is a yes/no test: is the stock in an uptrend? The app's screens
answer it with moving averages (`screens/criteria.py`):

- **Stage 2 / Trend Template** (the Minervini strategy's screen): the close is
  above the 50-, 150- and 200-day; the 50-day is above the 150-day, which is
  above the 200-day; the 200-day is higher than it was `SMA200_RISING_BARS` = 21
  sessions ago. With them: at least `MIN_PCT_ABOVE_52W_LOW` = 30% above the
  52-week low, and at most `MAX_PCT_BELOW_52W_HIGH` = 25% below the 52-week high.
- **Established uptrend** (the trend-pullback strategy's screen): the weekly
  close is above a rising 30-week EMA; the weekly 20-week average is above the
  50-week; the daily 50-day is above the 200-day, and the price has not broken
  down through the 50-day (more than 2 ATR below it, or 5 closes in a row under
  it).
- **"Falling" has a definition.** The 50-day is falling when it is more than
  `SMA50_FALLING_PCT` = 1% below its value `SMA50_SLOPE_BARS` = 10 sessions ago.
  The 200-day is falling when it is more than `SMA200_FALLING_PCT` = 0.5% below
  its value `SMA200_SLOPE_BARS` = 20 sessions ago. Anything in between is "flat".

What a filter adds: a clear answer you can apply to every stock the same way.
What it repeats: the price itself. "Above a rising 200-day" is a way of saying
"higher than its average of the last ten months, and that average is going up".

### 2.4 As pullback levels — the trend-pullback strategy

In a strong uptrend, the price often dips back to a short average and then
continues. Traders use the 20/21-day or the 50-day as the place to look for a
low-risk entry. The trend-pullback strategy (`strategies/trend_pullback.py`)
builds this in:

- **X3 (a positive flag):** the close is within 1 ATR of a rising 50-day. It
  adds 1.0 to the setup's quality score, which is used for ranking.
- **X1 (extended):** the close is more than 2.5 ATR above the 20-day SMA, or
  RSI14 is above 75. It caps the decision at WATCH - WAIT: wait for a pullback
  toward the 20-day.
- **The resumption signal:** the entry needs a close above the 20-day SMA and
  above a recent high. The strategy buys the turn back up, not the dip itself.
- **X2:** a close below the 50-day (while the trend gate still passes) caps the
  decision at TRADE ON TRIGGER.

```series
title: Nvidia with its 21-day EMA and 50-day average, 2023 to mid-2024
from: 2023-01-01
to: 2024-06-30
line: us:NVDA | Nvidia | log
line: us:NVDA@ema21 | 21-day EMA
line: us:NVDA@sma50 | 50-day average
caption: In this run of about +760%, Nvidia closed above its 50-day on 328 of 374 sessions. The dips to the 21-day and 50-day were where a pullback buyer looked. The sideways stretch from August to early November 2023 is where the price crossed the 50-day back and forth.
```

Over these 18 months Nvidia crossed its 50-day 15 times. Most crossings came
in two sideways stretches: August–November 2023 and April–May 2024. In a trend,
the average is a useful level. In a sideways stretch it is crossed every few
days and tells you little.

Be careful about evidence. The trend-pullback strategy's own **status** line
says it has no demonstrated edge: its portfolio backtest from 2013 returned
1.75% a year in the US (SPY 12.8%) and 2.30% in India (index 11.7%). Buying
pullbacks to an average is a common method, not a proven one.

### 2.5 What moving averages add and what they repeat

They add **a smoothed line that makes the direction easy to see**, and a level
to measure distance from. They repeat the price: every moving average is just
past closes. Distance from the 50-day is one of the most overlapping numbers
in [the overlap measurement in the momentum indicators guide](learn-price-oscillators.md) (it moves with RSI almost one for one).

## 3. ATR — how much a stock moves

### 3.1 What it computes

The **true range** of a day is the largest of: high − low; |high − previous
close|; |low − previous close|. The last two catch gaps. Worked example: the
previous close is 100. Today the high is 104 and the low is 101. The day's
range is 3, but the true range is 4, because the price moved 4 from the
previous close.

**ATR14** is a 14-day average of the true range, smoothed the way Wilder
smoothed it: each day, new ATR = old ATR + (true range − old ATR) ÷ 14.

**ATR is in price units**: dollars or rupees per day. That makes it useful for
one stock (where to put a stop) and useless for comparing two stocks.
**ATR %** (ATR ÷ close × 100) fixes that.

| Stock (Oct 2025 – Oct 2026) | Median ATR14 | Median ATR % |
|---|---|---|
| Coca-Cola (KO) | $1.27 | 1.6% |
| Apple (AAPL) | $6.06 | 2.2% |
| Nvidia (NVDA) | $6.41 | 3.3% |
| Super Micro (SMCI) | $2.27 | 6.3% |
| Reliance (RELIANCE.NS) | ₹23.15 | 1.8% |
| HDFC Bank (HDFCBANK.NS) | ₹14.66 | 1.8% |

Apple and Nvidia have almost the same ATR in dollars. Nvidia moves half as much
again as a share of its price. Super Micro has the smallest dollar ATR of the
four US stocks and by far the largest ATR %.

```series
title: ATR as a % of the price — three very different stocks, 2022–2026
from: 2022-01-01
line: us:KO@atrp14 | Coca-Cola ATR %
line: us:NVDA@atrp14 | Nvidia ATR %
line: us:SMCI@atrp14 | Super Micro ATR %
caption: Median since 2022: Coca-Cola about 1.5%, Nvidia about 3.8%, Super Micro about 6.1%. Volatility also changes over time: Nvidia went from 8.4% in May 2022 to 2.1% in July 2025, and Super Micro reached 20% in November 2024.
```

### 3.2 What it adds and what it repeats

ATR adds something the closing-price indicators do not: **the size of the
moves, ignoring their direction**. RSI, MACD and moving averages all ask "up
or down, and how much?" ATR asks "how much does it swing?" In [the overlap measurement in the momentum indicators guide](learn-price-oscillators.md), ATR % has
only a weak relation to the others (correlations between about −0.5 and
0.1). It does repeat what you can see from the height of the candles.

### 3.3 How the app uses ATR

ATR appears in many of the app's rules. It turns fixed rules into rules
scaled to each stock:

- **Floor:** every screen first requires a usable ATR14 (`screens/base.py`).
- **Too quiet:** the trend-pullback and breakout strategies skip stocks with
  ATR % at or below `atr_pct_min` = 1.5 (both markets' config).
- **Too wild:** trend pullback (D6) and breakout (B6) reject ATR % above 8; the
  chart-pattern strategy rejects ATR % above `MAX_ATR_PCT` = 10.
- **Extension:** breakout rejects a close more than 4 ATR above the 20-day
  (B5) and flags more than 2.5 ATR (XB1). Trend pullback flags more than
  2.5 ATR above the 20-day (X1).
- **Zones, not lines:** in the Minervini strategy, a close must clear the base
  high by `bh_break_atr` = 1 ATR to count as leaving the base, and overhead
  supply only caps the target when it sits at least `OVERHEAD_CLUSTER_ATR` = 1
  ATR above the base high.
- **Stops:** the Donchian strategy's stop is `stop_atr_mult` = 2 ATR below
  entry. Breakout's stop is never more than 2 ATR away. Chart patterns keeps
  the stop between `MIN_STOP_ATR` = 0.6 and `MAX_STOP_ATR` = 2 ATR. The
  backtester's `trail_atr` exit trails the stop 3 ATR under the highest close.
- **Pattern detection:** the VCP and chart-pattern detectors scale their
  "what counts as a real swing" thresholds by ATR %, because a fixed percentage
  is noise on one stock and a big move on another.

Position size in the app comes from the distance between entry and stop, not
from ATR directly (`core/sizing.py`). How ATR-based stops lead to equal risk
per trade is in [the position sizing guide](learn-risk-sizing.md); how wide a
stop should be is in [the stops guide](learn-risk-stops-exits.md).

## 4. ADX — trend strength without direction

### 4.1 What it computes

ADX was designed by Wilder to measure **how strongly the price is trending,
up or down**. The steps:

1. **+DM** is today's high minus yesterday's high, if that is positive and
   larger than the move down; otherwise 0. **−DM** is the same for lows.
2. Each is smoothed over 14 days and divided by ATR14. That gives **+DI** and
   **−DI**: the share of the recent range that was upward and downward
   movement.
3. **DX** = |+DI − −DI| ÷ (+DI + −DI) × 100. **ADX** is DX smoothed over 14
   days.

A stock falling steadily has a high ADX, just like one rising steadily. ADX
under about 20 is usually read as no trend; above about 25 as a trend; above
40 as a strong, often late, trend. These are conventions.

### 4.2 What it adds and what it repeats

ADX is one of the few indicators here that does **not** repeat RSI or MACD. In
[the overlap measurement in the momentum indicators guide](learn-price-oscillators.md), its correlation with every direction-based indicator is close to zero (−0.06
to 0.14). It answers a different question: is the price moving in one
direction, or back and forth? It does lag: two rounds of 14-day smoothing make
it slow to rise at the start of a trend and slow to fall at the end.

### 4.3 How the app uses ADX

ADX14 is stored for every stock. Only the trend-pullback strategy uses it:

- **Pre-screen:** ADX14 must be above `adx_min` = 15 (both markets).
- **X5:** ADX14 from 15 up to 20 (low trend strength); labelled base or drift.
  Drift subtracts 1.0 from setup quality.
- **X6:** ADX14 lower than 5 sessions ago. Sometimes noted as momentum fading.
- **X7:** ADX14 above 40 together with X1 (extended): a late move.

The Screens builder has an "ADX 14" field. The charts in these guides cannot
draw ADX; use the Chart page's "Directional Movement Index (ADX)" study, which
shows ADX, +DI and −DI.

## 5. What the evidence says

- **Robust: moving-average trend filters reduce the deepest drawdowns** on
  indices, by keeping you out during long bear markets. They usually do not
  raise returns after whipsaws and costs. This is shown for the index in [the
  trend guide](learn-health-trend.md).
- **Built in: lag.** Every indicator here uses past bars. Smoothing reduces
  false signals and adds delay. You cannot have both fewer false signals and
  less delay from the same data.
- **The app's own rules use indicators as filters and flags**, not as entry
  signals. Entries come from price levels: a pivot, a recent high, a channel
  high. Stops come from a pullback low or a base low, limited in ATR. No
  strategy in the app uses an indicator crossing as its entry.

For the momentum indicators, the research on single-indicator rules and the measured overlap, see [the momentum indicators guide](learn-price-oscillators.md).

## 6. Checklist

- [ ] For each indicator on my chart: which question does it answer? Do two of
  them answer the same one?
- [ ] Trend: is the stock above a rising 50- and 200-day, or is the line flat
  and being crossed every few days?
- [ ] Volatility: what is its ATR %? Is my stop at least about one ATR away?
- [ ] Extension: how many ATR is the close above the 20- and 50-day? (Trend
  pullback flags 2.5 above the 20-day; breakout rejects 4.)
- [ ] Am I acting on an indicator alone, without a price level for entry and
  stop?

## Further reading

- J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) — the
  original RSI, ATR, ADX and Parabolic SAR.
- Brock, Lakonishok and LeBaron, "Simple Technical Trading Rules and the
  Stochastic Properties of Stock Returns" (*Journal of Finance*, 1992).
- Sullivan, Timmermann and White, "Data-Snooping, Technical Trading Rule
  Performance, and the Bootstrap" (*Journal of Finance*, 1999).
