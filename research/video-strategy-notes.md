# Strategy notes from trading videos (November 2026)

What 16 trading videos (YouTube downloads, transcribed locally) contain that is worth keeping, and what
each idea becomes here. Every figure below is the speaker's own claim — none is verified. The six
Hindi/Hinglish videos were translated to English with a multilingual speech model (section 5).

## 1. Worth testing

| Idea | Source | Rules as stated | Becomes here |
|---|---|---|---|
| **Delivery % breakout** (India) | marketfeed | A day with unusually high delivery % *and* volume versus the stock's own recent days (example 48–50% → 86%; no threshold given). Buy when that day's high is crossed within 5 sessions — not on a gap through it. Stop below the signal day's low (example widened 2.85% → 3.5%). Target ≥ 1.5R (2R ideal), capped below a nearby 52-week high; book half at target, stop to breakeven. Risk ≤ 2% per trade, room for 5 positions. | New strategy `delivery_breakout` (1.0) on new data: NSE's security-wise delivery file (`MTO_*.DAT`), stored daily from December 2012 by the `delivery` job. Thresholds the video did not give are the strategy's choices, fixed before the first run. **Optimise 2013–2021, India: 106 trades, −0.02R a trade, profit factor 0.95, −0.28% CAGR at 37% exposure — no edge as stated** |
| **100 EMA trend** | Hitesh Somani (section 5) | Weekly close above the weekly 100 EMA, a 2-year-plus uptrend. After a dip, the daily close crosses back above the daily 100 EMA; buy-stop over that candle's high. No target: exit only when a close under the EMA is followed by a break of that candle's low. Nifty 500 only. Daily data only here (the 1-hour version is skipped). | New strategy `ema100_trend` (1.0) with a new exit mode, `--exit-mode ma_low`. Choices the video did not make, fixed before the first run: the stop goes under the dip's low, the trigger expires after 5 sessions, "Nifty 500" means the top 500 by traded value (both markets). **Optimise 2013–2021: India 361 trades, +0.15R a trade, profit factor 1.20, 3.5% CAGR vs 5.6% for the Nifty 500 at the same 73% exposure; US 535 trades, +0.35R, profit factor 1.41, 9.0% CAGR vs 11.0% for SPY at the same 94% exposure — positive per trade, but behind the index in both** |
| **Brandt classical breakouts** | Peter Brandt (Chat with Traders) | Weekly charts to find, daily to time. Horizontal patterns only (rectangle, right-angle triangle, H&S, cup and handle), 8–12 weeks long within ~15% of price. Compression: 14-day ADX under 12. Entry: buy-stop **0.5 × the 30-day ATR beyond the boundary**. Risk 60–70 bp per trade, all at once. Hold while above the 8-day average. | `chart_pattern` 1.18 research switches, off by default: `COMPRESSION_ADX_MAX` (gate G6) and `BUFFER_ATR` (with `BUFFER_ATR_BARS` = 30). Tested as `--const COMPRESSION_ADX_MAX=12` and `--const BUFFER_ATR=0.5` |
| **Weinstein + RS confirmation** | (Indian presenter) | Above the 50-week MA (Weinstein used 30); comparative RS line rising; buy only when *both* price and RS clear resistance. Reject a price breakout without an RS breakout. | Candidate filter for the stage-analysis / breakout strategies |
| **Kullamägi in his own words** | Chat with Traders ep. 212 | Top 2% by 1/3/6/12/18-month momentum, $150M+ daily dollar volume. Buy the opening-range high (5- or 60-minute beats 1-minute), stop at the day's low. Sell 20–25% into the first burst (days 3–5), trail the rest on a *close* below the 10- or 20-day. Best after a 5–15% index correction; no breakouts in a falling market. | Cross-check against the `kullamagi` strategy's rules |

## 2. Process rules several traders share

- Track every trade in R; anything worse than −1R means the stop was not honoured (Umar Ashraf).
- After 5 losses in 10 trades, stop and stay flat ("Doing the math wrong").
- Raise size only after months of results, never after a hot streak, in 20–30% steps held about two
  months (Freudberg, Ashraf).
- An edge needs 200–300 trades to judge; fixed rules for 100 trades, adjust a little, repeat — no
  optimisation (Brandt). Expectancy, not win rate: average win must exceed average loss.
- Decide the exit before entry, judged on a *close* through the level, not a wick (price-action video).

## 3. Lessons, not new strategies

- **Price action:** levels (2+ touches) → confirmation (hold, reclaim, break-and-retest) → invalidation
  decided in advance → context sets the size (index trend, extension, catalysts). Matches the Learn course.
- **Options income (Tom Sosnoff, two videos):** sell 16–25 delta, 35–50 DTE, only with high implied
  volatility; take 50% of the premium; short strangles are most of his profit. Belongs with options, not
  the stock strategies.
- **Valuation:** high US valuations are concentrated in the mega-caps; valuation timing rarely works (Ben
  Felix). The "Buffett method" — a multiple against its own 5-year average, adjusted for quality — is the
  presenter's reading, not Buffett's stated method.
- **Research process (Richard Coffin):** screen → understand the business → 5/10/15-year finances and
  forensic checks → strategy and returns on capital → valuation last → written thesis.
- **Live algo trading:** an unattended bot needs trade limits, a daily loss cap and reconciled P&L first;
  grids add to losers.

## 4. Skipped

- **CRT (candle range theory):** the presenter's own backtest only worked after heavy tuning, once by
  inverting the signal; 46 trades in a year.
- **Agenda trading** (shorting diluting US small caps): needs SEC-filing data; exceptional claimed returns.
- **Scanner and liquidity "masterclass":** mostly promotion; what they teach is in section 5.

## 5. Hindi/Hinglish videos (translated)

| Video | What it teaches | Becomes here |
|---|---|---|
| **Delivery % swing** (marketfeed) | The clean translation confirms §1's rules: delivery data comes after the close, so the signal is acted on the next day; stop under the signal day's low, at least 1.5R (2R ideal), target below a nearby 52-week high, where "there is a high chance of rejection". | Already tested (§1) — no change |
| **Hitesh Somani — two swing setups** | (1) *Bollinger reversal:* after a squeeze, a daily hammer formed wholly outside the lower band; buy the next green close back inside (a red close: wait for the next green), stop under the hammer, 1:2, half off at 1:1 and the stop to cost. Bollinger Bands measure volatility, they are not buy/sell lines. (2) *100 EMA trend:* the weekly close above its 100 EMA (a 2-year-plus uptrend); buy when the daily close crosses back above the daily 100 EMA after a dip and its high breaks; exit only on a close under the EMA followed by a break of that candle's low. Faster version: weekly + daily as filters, the 1-hour chart as trigger. Nifty 500 only, for liquidity. | (2) became `ema100_trend` 1.0 (section 1): positive per trade, but behind the index at the same exposure in both markets (optimise 2013–2021). (1) is a reversal and fails the 200-day screen |
| **Dhananjay Pawar — 9/21 EMA** | Intraday index (Sensex, Nifty) on 3-minute bars. After a 9/21 crossover, wait for a pullback with no opposite crossover and enter only on a break of the pullback's extreme — the filter that keeps him out of sideways chop. Wait for the candle close unless one candle clearly dominates the recent range. Stop 150–180 index points at a swing; half at 1:1, stop to breakeven, the rest at 1:2–1:3. Claims ~75–80% reach 1:1, 60–65% win rate at 1:2 over 100 hand-tested crossovers. | Needs intraday data not stored. The pullback-break filter after a crossover is the transferable idea |
| **Stock scanner** (course pitch) | Plan entry, stop and target before the open. *Continuation:* above the 20/50/200-day, RSI under 70, quarterly EPS growth over 20%, then a breakout on high volume (claimed 50–60% wins). *Reversal:* above the 20-day but below the 50 and 200, RSI crossing up, a higher low, at least a 20% move off the low (35–45%). Skip any trade under 2:1. | Overlaps the Stage 2 / Near-highs screens and Minervini's fundamentals option — nothing new |
| **Real P&L — Kundan, options** | Weekly Nifty put ratio spread, entered Monday ~15:30 on the expiry after next: buy 1 put 200 below spot, sell 2 at 400 below, buy 1 at 800 below as the hedge. Target +1% of capital, stop −1%, out by Friday (no weekend gap). Skip the week when the spread costs more than 0.7%; in high volatility widen the strikes until it takes in about 0.6%. Claims 28 of 29 weeks profitable in 2026; a 5% lower circuit would cost about 10%. His own book shows a **35% win rate** with winners 2.15× losers — the edge is the asymmetry, not the hit rate; top traders sit at 35–45%. | An F&O strategy: testable later on the stored NSE F&O bhavcopy, not a stock strategy |
| **Arun & Sooraj — supply & demand** | A zone is a few narrow-range "base" candles followed by an "explosive" candle: the base is where an institution's unfilled orders wait. Mark it on a higher timeframe (monthly/weekly), refine it on a lower one (daily), and buy the first return to it. Stronger zones: a bigger explosive candle, fewer base candles, the higher timeframe agreeing. A fast, aggressive fall breaks a low-timeframe zone; a higher-timeframe one holds. Timeframes by style: swing = weekly → daily. | Close to the base-and-breakout family already tested; a "first return to the base" entry is a possible variant, not a priority |
| **Liquidity masterclass** (gold, intraday) | Trade only at important levels, on price action there. The best levels: previous day's high and low (by the wick), then the current day's high/low once the day has moved at least ATR minus 20–30%, the volume-profile value-area high/low, and 15-minute/1-hour order blocks. Trade the *sweep* of a level (a wick through it that closes back), never the first touch. | Intraday; the "sweep, not touch" rule is the lesson |

**What repeats across them:** wait for confirmation — a green close, a pullback break, a sweep that
closes back — rather than buy the first signal; book half at 1:1 and move the stop to breakeven
(Somani, Pawar, and the delivery video in its own way); and judge a system by the size of its winners
against its losers, not its win rate.
