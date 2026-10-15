# Kullamägi's momentum breakouts — buying the fastest stocks as they set off again

**In short**

- Kristjan Kullamägi trades the strongest stocks in the market: ones up 30–100% or more in a few months that then rest in a tight, orderly range.
- He buys the breakout from that range early in the day, with the stop at the day's low, and sizes the position so the stop costs only a fraction of a percent.
- After three to five days he sells a third to a half and moves the stop to breakeven. The rest rides until the first close below the 10-day or 20-day average.
- Most trades lose a little. A few gain ten times the risk or more, and those few pay for everything.
- On stored daily data, an end-of-day version roughly broke even in India before costs and lost slightly in the US. The edge, if there is one, depends on intraday entries and on catching the rare big winner.

## 1. The idea

In late July 2023, BSE Ltd, the Mumbai stock exchange company, traded near ₹242. By 19 October it had more than doubled, to ₹516. The stock had spent the previous week resting between about ₹479 and ₹506. Volume in that week fell to between a quarter and half of its 50-day average.

```series
title: BSE Ltd — a doubling, a quiet week, and the next leg (prices adjusted for later bonus issues)
from: 2023-07-01
to: 2023-12-29
tf: D
line: india:BSE.NS | BSE Ltd | log
line: india:BSE.NS@sma10 | 10-day average
line: india:BSE.NS@sma20 | 20-day average
line: india:BSE.NS@vol | Volume | pane2 bars
mark: 2023-07-24 | low ₹242
mark: 2023-10-12 | tight range begins
mark: 2023-10-20 | breakout, entry ₹529
mark: 2023-11-21 | first close below the 10-day
caption: The stock rested above its rising 10-day and 20-day averages, then broke out. The exit came a month later, about 35% higher.
```

On 20 October the stock closed at ₹529, above the top of its range. A Kullamägi-style trade bought there with the stop at that day's low, ₹513: a risk of about 3%. A month later it sold the rest at ₹716.

That is the whole method in one chart. **Find the stocks that have moved most. Wait for them to rest. Buy when they start moving again, with a stop so close that being wrong is cheap.**

Who is on the other side? Mainly holders taking profit after a big run. While they sell, the stock drifts sideways. When their selling dries up, buyers who missed the first move push it out of the range.

Kullamägi is a Swedish trader who has shared his methods on his blog and in long live streams. He trades three setups:

| Setup | What it is | Where it is covered |
|---|---|---|
| **Breakout** | A big mover rests in a tight range, then breaks out | This guide |
| **Episodic pivot** | A neglected stock gaps up on news, usually results, on huge volume | [Earnings gaps and episodic pivots](learn-strat-earnings-gaps.md) |
| **Parabolic short** | Shorting a stock after a vertical, unsustainable run | Not covered here; see [Stage 4 shorts](learn-strat-stage4-shorts.md) for the short side |

The breakout is his main setup and the one he teaches most. The other two use the same entry and the same management.

## 2. When it works and when it doesn't

It works best in a strong, broad market where many stocks are making big moves. In those periods, breakouts follow through and the big winners appear. Kullamägi trades less, and smaller, when the indices fall below their short averages.

It works poorly in:

- **Corrections and bear markets.** Breakouts fail one after another. Each failure is small, but they add up.
- **Slow, quiet stocks.** The method needs stocks that move several percent a day. A stock that moves 1% a day rarely gives a ten-times-risk winner.
- **Choppy, sideways markets.** Stops set at the day's low get hit by ordinary noise.

It is close to Minervini's method (see [SEPA and the VCP](learn-strat-vcp-sepa.md)), with three differences. Kullamägi cares less about earnings. He wants faster, more volatile stocks. And his consolidations are shorter, often two to six weeks rather than months.

**India.** Many of the fastest Indian stocks are small caps with daily price bands of 5%, 10% or 20%. A breakout can lock at the upper band, so you cannot buy. A failure can lock at the lower band, so the stop cannot fill. Prefer stocks without a band (most stocks in the derivatives segment) or with a wide band and a deep order book.

**US.** Liquidity is deep, and intraday entries are easy to place. The risk is the opposite: so many fast stocks that it is tempting to trade too many at once.

## 3. The rules

Each rule below is a condition a program can check. Section 4 gives the ranges.

### Universe and filters

- **Liquidity.** Close at least ₹20 or $5. The 50-day average daily turnover is at least ₹5 crore or $5 million. Kullamägi wants more for large accounts.
- **Speed.** The **average daily range** (ADR) is at least 4%, ideally 5% or more. ADR is the average, over 20 days, of each day's high divided by its low, minus one. It measures how far the stock moves in a typical day.
- **A big prior move.** The stock has risen 30% or more within the last one to three months. Kullamägi finds these by ranking every stock by its 1-month, 3-month and 6-month gain and looking at the top 1–2%. See [Relative strength](learn-price-rs.md).
- **Market.** The main index (the Nasdaq in the US, a broad index in India) is above its 20-day average, and its 10-day average is above its 20-day.

### Setup

```pattern
bull-flag
```

- **Orderly rest.** After the move, the stock goes sideways or drifts slightly down for 2 to 8 weeks.
- **Higher lows.** The range narrows from left to right. The lows hold or rise.
- **Riding the averages.** The lows stay near or above the rising 10-day and 20-day averages. Kullamägi calls this "surfing" the averages.
- **Quiet volume.** Volume shrinks during the rest. (On stored data, this made no clear difference — see section 8.)
- **Pivot.** The high of the range, or of its last few tight days.

### Entry

- **Opening-range breakout (his way).** On the day the price trades above the pivot, buy when it breaks above the high of the first 1, 5 or 60 minutes. See [Opening range breakouts](learn-strat-orb.md).
- **Don't chase.** Skip the trade if the price is already well above the pivot by the time you can buy. A practical limit is about one ADR above the pivot.
- **Daily-data version.** For testing on daily bars, buy at the close of the day that closes above the pivot.

### Initial stop

- The low of the day at the moment you buy. With an opening-range entry, that is the low of the opening range.
- If the stop is further away than one ADR, skip the trade or wait for a tighter entry.
- In the daily-data version, the stop is the low of the breakout day.

### Exits

- **Partial sale.** After 3 to 5 sessions, sell a third to a half if the trade is in profit. Move the stop on the rest to the entry price.
- **Trailing exit.** Sell the rest on the first close below the 10-day average. For slower stocks, use the 20-day average instead.
- **Failed breakout.** The stop handles it. Do not move the stop down to give the trade "room".

### Position size

- Risk a small, fixed share of capital per trade. Kullamägi has described risking well under 1% per trade, rising only during strong periods.
- Shares = (capital × risk %) ÷ (entry − stop). A 3% stop and 0.5% risk give a position of about 17% of capital.
- Cap any one position, for example at 20–25% of capital, so a gap through the stop cannot do serious damage. See [Position sizing](learn-risk-sizing.md).

### Managing the trade

- Never add to a loser.
- When trades work, add new positions; when several fail in a row, stop and wait for the market to improve.
- A stock that stops you out can be bought again if it builds a new range. Many of the biggest winners take two or three tries.
- Sell before results unless the trade is already well in profit and the stop is at breakeven or higher.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Minimum price / turnover | ₹20 / $5; ₹5 crore / $5m | Tradeability | Raise for bigger accounts |
| ADR (20-day) | ≥ 4% (ideal ≥ 5%) | How fast the stock moves | Lower = fewer big winners |
| Prior move | ≥ 30% in 1–3 months | Leadership | 30–100%+ |
| Momentum rank | Top 1–2% by 1, 3 or 6-month gain | Leadership | Top 5% gives many more setups |
| Rest length | 2–8 weeks | Base maturity | Shorter is riskier |
| Range of the rest | ≤ 20% high to low | Tightness | Tighter = closer stop |
| Lows vs 20-day average | ≥ 97% of it | Trend intact | Some allow a brief undercut |
| Entry | Break of the opening-range high | Timing | 1, 5 or 60 minutes |
| Maximum stop distance | 1 × ADR | Biggest allowed risk | Most stops are well inside it |
| Partial sale | 1/3 to 1/2 after 3–5 sessions | Locking gains | Earlier = smaller winners |
| Trailing average | 10-day (fast) or 20-day (slower) | When the rest is sold | 20-day holds longer |
| Risk per trade | 0.25–1% | Position size | Start low |
| Position cap | 20–25% of capital | Gap risk | Lower for small caps |
| Market filter | Index above 20-day; 10-day above 20-day | When to trade | Optional; see section 8 |

## 5. Variations

- **Kullamägi's own teaching**, on his blog and in recorded streams, is the source of the rules above. He gives ranges and examples rather than one fixed rule set, so any coded version is an interpretation.
- **Minervini's SEPA** uses the same idea with earnings filters, longer bases and a VCP shape. See [SEPA and the VCP](learn-strat-vcp-sepa.md).
- **O'Neil's CAN SLIM** buys breakouts from longer bases with wider stops. See [CAN SLIM breakouts](learn-strat-canslim-breakout.md).
- **Flags and high tight flags** are the chart-pattern view of the same setup. See [Flags, pennants and high tight flags](learn-strat-flags.md).
- **Episodic pivots** start the move with a news gap. The breakout setup often follows a few weeks later, as in the Vertiv example below.
- **Cross-sectional momentum** holds the top-ranked stocks for months with no chart setup at all. See [Cross-sectional momentum](learn-strat-xs-momentum.md).

## 6. Worked examples

These use the daily-data version: entry at the breakout close, stop at that day's low. Prices are adjusted for later splits and bonus issues.

### BSE Ltd, October 2023 — a doubling, a pause, and another 35%

This is the chart in section 1.

- **Prior move.** From ₹241.88 on 24 July to ₹516 on 19 October: +113% in under three months. ADR was about 4.5%.
- **Rest.** From 12 to 18 October the range was ₹479–₹506, above a rising 10-day average. Volume was 0.25–0.52 times average.
- **Entry.** Close of 20 October, ₹529.27. Stop at the day's low, ₹512.60: a risk of 3.1%, or ₹16.67 per share (1R).
- **Partial sale.** On 26 October, the third session, the close was ₹599.73. That is +4.2R. Sell a third and move the stop to ₹529.27.
- **Exit.** The first close below the 10-day average came on 21 November, at ₹716.48. The rest gained 35.4%, or 11.2R.
- **Whole trade.** About +8.9R. Breakout volume was only 0.74 times average, so a strict volume rule would have skipped it.

### Vertiv, May 2023 — an episodic pivot, a flag, then the run

```series
title: Vertiv — a results gap, three weeks of rest, then a breakout
from: 2023-03-15
to: 2023-08-31
tf: D
line: us:VRT | Vertiv | log
line: us:VRT@sma10 | 10-day average
line: us:VRT@sma20 | 20-day average
line: us:VRT@vol | Volume | pane2 bars
mark: 2023-04-26 | results gap, 4.8× volume
mark: 2023-05-17 | breakout, entry 15.63
mark: 2023-07-21 | first close below the 10-day
caption: The results-day gap started the move. The breakout from the rest that followed was the trade.
```

- **The episodic pivot.** On 26 April 2023, Vertiv opened 17% higher after its results, on 4.8 times its usual volume. It closed at 13.59.
- **Rest.** From 28 April to 16 May the stock held between 14.28 and 15.58. Volume faded to under half its average by mid-May.
- **Entry.** Close of 17 May, 15.63, above the 15.575 high. Stop at the day's low, 15.175: a risk of 2.9%.
- **Partial sale.** On 22 May the close was 16.51, or +1.9R. Sell a third; stop to breakeven.
- **Exit.** The 10-day average held for two months. The first close below it came on 21 July, at 25.68. The rest gained 64.3%, or 22.1R.
- **Whole trade.** About +15.4R. This is the kind of trade the method lives on: rare, and large enough to cover many small losses.

### Coinbase, November 2021 — a breakout at the top of the market

```series
title: Coinbase — a breakout that failed the next day, at the top of a speculative market
from: 2021-09-01
to: 2022-02-28
tf: D
line: us:COIN | Coinbase | log
line: us:COIN@sma10 | 10-day average
line: us:COIN@sma20 | 20-day average
line: us:COIN@vol | Volume | pane2 bars
mark: 2021-11-08 | breakout, entry 353.92
mark: 2021-11-09 | stop hit, results that evening
caption: The stop at the breakout day's low was hit the next day by fifty cents. Three months later the stock was about half the entry price.
```

- **Prior move.** From 224.51 on 4 October to 345.85 on 4 November: +54% in a month.
- **Rest.** Two weeks between about 305 and 346, above the 10-day and 20-day averages. The Nasdaq was still in an uptrend, so the market filter passed.
- **Entry.** Close of 8 November, 353.92, on 1.8 times average volume. Stop at the day's low, 345.56: a risk of 2.4%.
- **What happened.** The next day the stock first rose to 368.90 (+1.8R), then fell to 345.06. The stop sold at 345.56: −1R.
- **Then.** Results came out that evening. The stock opened at 327.22 the next morning. A trade still open would have lost about 3R on the gap.
- **Three months later.** It closed near 170 in late January 2022, about half the entry price.
- **Lesson.** The method's losses are meant to look like this: small and quick. It also shows why holding into results with a tight stop is a bad bet.

## 7. Common mistakes

| Mistake | Why it hurts |
|---|---|
| Buying a stock that hasn't moved much | The method's big winners come from stocks that were already the fastest |
| Buying a loose, wide-swinging range | No close stop is possible; the risk is several times larger |
| Chasing a breakout already far above the pivot | The stop at the day's low is now far away |
| Widening the stop after entry | Turns a planned −1R into −3R or worse |
| Skipping the partial sale | Many trades that reach +2R fall back to the entry |
| Selling the rest too early | The method lives on the few trades that run for weeks |
| Trading full size after several stop-outs in a row | Strings of failures usually mean the market has turned |
| Holding into results with a tight stop | A gap jumps the stop; the loss is far bigger than planned |
| Judging the method on ten trades | Most trades lose; one big winner can change the whole picture |

## 8. What the evidence says

**Kullamägi's record.** He has shared account statements showing very large gains since the mid-2010s. They are self-reported and not audited. A trader's own record shows the method can be traded well. It does not show how often its rules work for others, or how much depends on his judgement and intraday execution.

**Published research behind the parts:**

- **Momentum.** Stocks that rose most over the prior 3–12 months tended to keep outperforming for months (Jegadeesh and Titman, 1993).
- **Nearness to the 52-week high.** Stocks close to their 52-week high outperformed those far below it (George and Hwang, 2004).
- **News versus no news.** Large price moves that came with public news tended to continue. Large moves without news tended to reverse (Chan, 2003). This is the case for episodic pivots.
- **Patterns in general.** An automated study of chart patterns found that some carry a little information about future returns, much less than practitioners claim (Lo, Mamaysky and Wang, 2000).

**An event study on stored data.** We coded the daily-data version and ran it on both markets.

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to October 2026. Liquidity on the day before: close ≥ ₹20 / $5, 50-day average turnover ≥ ₹5 crore / $5m. ADR (20-day) ≥ 4%. Prior move: the highest high of the last 20 sessions is at least 30% above the lowest low of the last 63. Rest: the last 10 sessions span at most 20% high to low, their lows stay at or above 97% of the 20-day average, and the prior close is above the 10-day average. Breakout: a close above the rest's high. Entry at that close; stop at that day's low, skipped if more than one ADR or less than 1% away. After 3 sessions, if the close is above entry, a third is sold there and the stop moves to entry. The rest exits on the first close below the 10-day average, at the stop (or the open, if it gaps through), or after 120 sessions. One event per stock per 20 sessions. Market filter: Nasdaq-100 (US) or Nifty 500 (India) above its 20-day exponential average, and its 10-day above its 20-day. Caveats: today's lists only (survivorship bias), daily bars instead of intraday entries, fills at the stop on non-gap days, no price-band locks.

| Momentum breakouts, daily-data version | India | US |
|---|---|---|
| Events | 2,489 (1,017 stocks) | 5,276 (1,917 stocks) |
| Median stop distance | 3.3% | 3.2% |
| Stopped out at the full −1R | 58.0% | 59.9% |
| Stopped out within two sessions | 40.8% | 44.4% |
| Winning trades | 37.8% | 36.1% |
| Average winner | +1.9R | +1.6R |
| Trades of +5R or more | 3.4% | 2.5% |
| Share of all gains from the best 5% of trades | 56% | 57% |
| Median holding period | 3 sessions | 3 sessions |
| **Average result, before costs** | **+0.09R** | **−0.10R** |
| Average result, after costs (0.3% / 0.1% a round trip) | −0.01R | −0.14R |
| Years with a positive average | 10 of 17 | 3 of 17 |

| Average result in R, before costs | India | US |
|---|---|---|
| As above (10-day trailing exit) | +0.09 | −0.10 |
| 20-day trailing exit instead | +0.09 | −0.11 |
| Market filter passed | +0.07 | −0.11 |
| Market filter failed | +0.24 | −0.06 |
| Other breakouts (prior move under 30%), same rules | +0.07 | −0.04 |
| Wider stop: under the rest's low, up to two ADRs | −0.06 | −0.04 |

**Where the stocks went next** (close 60 sessions after the breakout):

| | India: big movers | India: other breakouts | US: big movers | US: other breakouts |
|---|---|---|---|---|
| Median return | +1.8% | +0.9% | +2.6% | +1.4% |
| Average return | +5.7% | +2.5% | +4.3% | +1.1% |
| Spread (standard deviation) | 26.4% | 18.2% | 28.5% | 14.0% |
| Share up more than 50% | 5.3% | 1.4% | 5.3% | 0.3% |
| Share down more than 20% | 11.5% | 7.1% | 17.4% | 5.7% |

What this shows:

- **The stocks are special; the daily-bar trade is not.** Breakouts in big movers were about four times as likely to gain 50% in India, and over fifteen times as likely in the US. Part of that is simply because they are more volatile: big losses were also more common.
- **The tight daily stop is hit very often.** About four in ten trades were stopped within two sessions. The stop at the breakout day's low sits inside the stock's normal daily range.
- **The result rests on a few trades.** The best 5% of trades produced over half of all gains. Missing a few of them, or adding costs, turns a small edge into a small loss.
- **The market filter did not help** in this test, in either market. Volume on the breakout day (not shown) made no clear difference either.
- **A wider stop did not rescue it.** The partial sale and breakeven stop then cut many trades for a small gain.

**What is unknown.** This test uses daily bars. Kullamägi buys intraday, early in the breakout day, with the stop at the low of the opening range. That entry is cheaper on a strong day and avoids buying the close of a day that has already moved. It may be where much of the edge lies, and daily data cannot measure it.

His stock selection, his reading of the market and his willingness to press winners are not coded here at all. Treat the rules as a framework to test with intraday data, not as a proven edge.

## 9. Building and testing it yourself

**Data.** Adjusted daily OHLCV for the whole universe, to compute momentum ranks and ADR each day. Intraday bars (1- or 5-minute) for the entry and stop, if you want to test the method as it is traded. An index for the market filter. Results dates, to avoid holding through them.

**Look-ahead traps.**

- The day's low is only known at the close. A daily test that buys early in the day cannot use the day's low as its stop. Either buy at the close, or use intraday bars.
- The momentum rank must use only stocks and prices that existed on that day.
- The pivot must be set from bars before the breakout day.

**Survivorship.** Use lists that include delisted companies. Fast stocks are exactly the ones that collapse and disappear, and a today's-list test leaves them out.

**Costs.** In India a delivery round trip costs roughly 0.25–0.35%: securities transaction tax, stamp duty, exchange fees, GST and depository charges. With a 3% stop, that is about 0.1R per trade before slippage. Slippage on fast breakouts is often larger than the costs. Measure results in R after both.

**What to test.** Start with the ADR floor, the prior-move threshold, the stop rule and the trailing average. Change one at a time. Because a few trades decide the result, check how much the result changes when the best 1% of trades is removed. Report results by year, not only in total.

**What a good test reports.** Trades per year, win rate, average win and loss in R, and expectancy after costs. Also the share of gains from the best trades, the longest losing streak, drawdown, and results by market regime. See [Backtesting honestly](learn-test-backtesting.md).

```
each session t:
    if not market_ok(t): trade smaller or skip
    leaders = stocks with ADR(20) >= 4%, liquidity ok, and gain over 1-3 months in the top 1-2%
    for each stock in leaders:
        rest = last 2-8 weeks of bars up to t - 1
        if rest is not tight, or lows undercut the 20-day average: continue
        pivot = high of rest
        if high[t] > pivot:
            entry = break of the opening-range high (intraday) or close[t] (daily version)
            stop = low of the day so far (intraday) or low[t] (daily version)
            if entry - stop > ADR(20) * entry: continue
            shares = capital * risk_pct / (entry - stop)
manage daily:
    if low <= stop: sell at min(open, stop)
    if sessions_held in 3..5 and close > entry and not sold_part: sell a third; stop = entry
    if close < sma10: sell the rest
```

## 10. Checklist

- [ ] Market: indices above their 20-day averages; recent breakouts are working
- [ ] Stock up 30% or more in the last one to three months; among the top 1–2% by momentum
- [ ] ADR at least 4–5%; liquid enough for your size
- [ ] Rest of 2–8 weeks: higher lows, narrowing range, above the rising 10-day and 20-day
- [ ] Pivot marked; entry planned as an opening-range breakout above it
- [ ] Stop at the low of the day at entry, no more than one ADR away
- [ ] Position size from the stop; risk per trade under 1%; position under the cap
- [ ] No results due before the partial sale
- [ ] Plan written: sell a third to a half after 3–5 days, stop to breakeven, rest on a close below the 10-day
- [ ] In India: stock not locked at its price band, and the band is wide enough for the stop to fill

## Further reading

- Kristjan Kullamägi's blog and recorded streams — his own description of the breakout, episodic pivot and parabolic short setups.
- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and Selling Losers", *Journal of Finance* (1993).
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* (2004).
- Wesley Chan, "Stock Price Reaction to News and No-News: Drift and Reversal After Headlines", *Journal of Financial Economics* (2003).
- Andrew Lo, Harry Mamaysky and Jiang Wang, "Foundations of Technical Analysis", *Journal of Finance* (2000).
- [Earnings gaps and episodic pivots](learn-strat-earnings-gaps.md), [Flags, pennants and high tight flags](learn-strat-flags.md), [Opening range breakouts](learn-strat-orb.md), [Stops and exits](learn-risk-stops-exits.md).
