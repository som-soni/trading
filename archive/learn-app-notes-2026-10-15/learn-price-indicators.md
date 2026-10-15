# App notes moved out of learn-price-indicators (verbatim)

## Intro (app framing)
Learning material on the indicators that describe a stock's **trend** and how
much it **moves**: moving averages, ATR and ADX. For each one: what it
computes, what question it answers, what it adds to the price chart and what it
only repeats, the usual settings, and how this app computes and uses it. The
momentum indicators — RSI, MACD and Bollinger Bands — are in [the momentum
indicators guide](learn-price-oscillators.md), together with the Chart page's
full list of studies, a measurement of how much indicators overlap, and a table
of which indicator answers which question. For basic words, see [Start

## "Where this shows in the app" and data note
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

## §2.2 The usual lengths (app note)
None of these numbers is special. They are conventions. The 10-day and
21-day EMAs are popular among momentum traders, but **this app does not
compute a 10- or 21-day line in its screening code**. Its short line is the
20-day (SMA and EMA). You can draw any length on the Chart page.

## §2.3 As trend filters — the app's screens
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

## §2.4 As pullback levels — the trend-pullback strategy (rules, and its backtest status — removed)
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
Be careful about evidence. The trend-pullback strategy's own **status** line
says it has no demonstrated edge: its portfolio backtest from 2013 returned
1.75% a year in the US (SPY 12.8%) and 2.30% in India (index 11.7%). Buying
pullbacks to an average is a common method, not a proven one.

## §3.3 How the app uses ATR
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

## §4.3 How the app uses ADX
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

## §5 evidence bullet on the app's rules
- **The app's own rules use indicators as filters and flags**, not as entry
  signals. Entries come from price levels: a pivot, a recent high, a channel
  high. Stops come from a pullback low or a base low, limited in ATR. No
  strategy in the app uses an indicator crossing as its entry.

## §6 Checklist (app thresholds)
- [ ] Extension: how many ATR is the close above the 20- and 50-day? (Trend
  pullback flags 2.5 above the 20-day; breakout rejects 4.)
