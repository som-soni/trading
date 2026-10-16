# Zanger's chart breakouts — trendlines, volume and the market's leaders

**In short**

- Dan Zanger buys big, liquid leading stocks as they break out of classic chart patterns: flat tops, cups with handles, flags, wedges and falling trendlines.
- The breakout must come on heavy volume. He gets out fast if the stock falls back below the line it broke, and sells into the wild, high-volume run-ups that often end a move.
- The method is concentrated: a few large positions in the hottest stocks, so a quick loss rule matters more than anything else.
- On stored data, breakouts in big, liquid stocks roughly broke even in the US and made a small profit in India, before judgement. The fast "back below the line" exit cut winners as often as losers.

## 1. The idea

In late November 2019, Tesla stalled just above 24. It fell back about 9%, then returned to the same level by 13 December, with a high of 24.35. (Prices here are adjusted for later splits.)

On 16 December the stock broke through. It closed at 25.43, on 2.1 times its usual volume. It never closed back below the old ceiling. Seven weeks later it had more than doubled.

```series
title: Tesla — a flat-top breakout on heavy volume, and the climax that ended it (split-adjusted)
from: 2019-10-01
to: 2020-03-31
tf: D
line: us:TSLA | Tesla | log
line: us:TSLA@sma20 | 20-day average
line: us:TSLA@sma50 | 50-day average
line: us:TSLA@vol | Volume | pane2 bars
mark: 2019-11-20 | high
mark: 2019-12-16 | breakout
mark: 2020-02-04 | climax
mark: 2020-02-26 | exit
caption: Highs of 24.08 in November and 24.35 on 13 December formed the flat top. The breakout came on 2.1× normal volume. The climax: a gap up on 4.2× volume, after which the stock fell 17% in a day. Exit: the first close below the 20-day.
```

That is Zanger's method. **Find the strongest, most traded stocks. Draw the line that has held them back. Buy when they cross it on heavy volume. Get out fast if the break fails, and sell into the frenzy if it succeeds.**

Why would a line matter? Many traders watch the same obvious levels. Sellers who bought near the ceiling, or who think the stock is "high enough", keep supplying shares there. When volume surges through the ceiling, it shows that a large buyer has absorbed that supply.

Zanger is an American trader who became known in the late 1990s technology boom. He has published a newsletter on chart patterns for many years. His approach is close to O'Neil's (see [CAN SLIM breakouts](learn-strat-canslim-breakout.md)). But it leans more on drawn trendlines and on the biggest, most liquid names.

## 2. When it works and when it doesn't

It works best in strong markets with clear leadership: a hot group of large stocks that institutions are buying. In those periods breakouts follow through and the climax runs appear.

It works poorly in:

- **Corrections.** Breakouts fail and reverse. A string of quick losses is the signal to stop.
- **Markets driven by news shocks.** A single headline can gap a whole group through its stops, as the Broadcom example in section 6 shows.
- **Thin stocks.** The method depends on reading volume. In a thinly traded stock, a few orders can fake a breakout.

**Concentration cuts both ways.** Zanger is known for holding a few large positions, at times with borrowed money (margin). That magnifies the big winners. It also magnifies every gap and every failed breakout. The rules on losses are what make it survivable.

**India.** The method suits the large, liquid stocks in the derivatives segment, which have no daily price band. Many mid and small caps have bands of 5–20%. A breakout can lock at the upper band, and a failure can lock at the lower band. Settlement is T+1.

**US.** Liquidity is deep in the large leaders the method favours. Pre-market news and results move these stocks before the open, so gaps are the main risk.

## 3. The rules

Each rule below is a condition a program can check. Section 4 gives the ranges.

### Universe and filters

- **Big and liquid.** 50-day average daily turnover of at least ₹50 crore or $100 million. Price at least ₹100 or $20.
- **Uptrend.** The close is above the 50-day average, and the 50-day is above the 200-day.
- **Leadership.** The stock is among the strongest in the market and in a leading industry group. See [Relative strength](learn-price-rs.md) and [Sectors and groups](learn-sectors-groups.md).
- **Market.** Leaders are breaking out and holding their gains. When several breakouts fail in a row, trade less.

### Setup

Zanger trades the classic shapes. Each one gives a line to draw.

```pattern
ascending-triangle
```

- **Flat top or ascending triangle.** Two or more highs at about the same level. The line is horizontal.
- **Cup with handle.** The line runs across the top of the handle. See [Bases](learn-bases.md).
- **Flag or pennant.** A short pause after a fast rise. The line runs along the top of the flag. See [Flags, pennants and high tight flags](learn-strat-flags.md).
- **Falling wedge or falling trendline.** A line through two or more falling highs.

```pattern
falling-wedge
```

- **Base depth.** The pattern is at most about 25% deep from high to low.
- **The line.** It touches at least two highs, and no close has been above it since the last one.

### Entry

- **On the break.** Buy as the price crosses the line during the day.
- **Volume pace.** The day's volume is on track to reach well above average. A common reading is at least 1.5 to 2 times the 50-day average.
- **Don't chase.** Skip a stock already more than about 3–5% above the line.
- **Daily-data version.** For testing, buy at the close of the first day that closes above the line.

### Initial stop

Zanger's rule is to cut a failed breakout quickly. There are two common ways to code it:

- **Tight.** Sell if the stock closes back below the breakout line.
- **Hard limit.** Sell if the loss reaches about 7–8%, whatever the chart says.

Many traders use both: the tight rule for most trades, the hard limit as a backstop.

### Exits

- **Sell into a climax.** A climax run is a burst of very large up-days, often with gaps and record volume, after a big gain. Sell a large part into it. The climax run is drawn in [Chart patterns](learn-chart-patterns.md).
- **Trend break.** Sell the rest on a close below the 20-day average, or below the stock's own uptrend line.
- **Slower version.** Some followers use the 50-day average, which holds longer.
- **Results.** Sell before results unless the gain is large enough to absorb a gap.

### Position size

- Risk a fixed share of capital per trade, for example 0.5–1%.
- Shares = (capital × risk %) ÷ (entry − stop). An 8% stop and 1% risk give a position of 12.5% of capital.
- Cap any one position. A gap through the stop costs more than the planned risk. See [Position sizing](learn-risk-sizing.md).
- Avoid margin until the method has a long record in your own hands.

### Managing the trade

- Never average down.
- Add only when the stock breaks out of a new, smaller pattern above your entry.
- Re-buy a stock that stops you out if it builds a new pattern and breaks out again.
- Keep the number of positions small enough to watch every one during the day.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Minimum turnover | ₹50 crore / $100m a day | Liquidity, gap risk | Zanger favours the most traded names |
| Minimum price | ₹100 / $20 | Quality of the stock | |
| Trend filter | Close > 50-day > 200-day | Stage 2 only | See [Stages and trend in a stock](learn-price-stages.md) |
| Base depth | ≤ 25% | Damage in the pattern | Deeper bases fail more |
| Line touches | ≥ 2 highs | Validity of the line | 3+ is a stronger line |
| Breakout volume | ≥ 1.5–2 × 50-day average | Evidence of demand | See section 8 |
| Buy limit | ≤ 3–5% above the line | Chasing | |
| Tight exit | Close back below the line | Failed breakout | Fast; see section 8 |
| Hard stop | 7–8% | Largest planned loss | Gaps can exceed it |
| Climax sale | Several huge up-days on record volume | Profit taking | Hard to code exactly |
| Trend exit | Close below the 20-day | When the rest is sold | 50-day holds longer |
| Risk per trade | 0.5–1% | Position size | |
| Positions | Few (for example 4–8) | Concentration | Fewer = larger swings |

## 5. Variations

- **O'Neil's CAN SLIM** uses the same patterns with earnings and ownership filters, and a strict 7–8% stop. See [CAN SLIM breakouts](learn-strat-canslim-breakout.md).
- **Minervini's SEPA** asks for a specific shape, the volatility contraction, and tighter stops. See [SEPA and the VCP](learn-strat-vcp-sepa.md).
- **Kullamägi's breakouts** trade faster, smaller stocks with a stop at the day's low. See [Kullamägi's momentum breakouts](learn-strat-kullamagi.md).
- **Classical charting** (Edwards and Magee) is the source of the patterns and trendlines. See [Chart patterns](learn-chart-patterns.md).
- **Failed-breakout traders** take the other side: they short the breakouts that fall back below the line. See [Failed breakouts](learn-strat-failed-breakouts.md).

## 6. Worked examples

These use the daily-data version: entry at the breakout close, an 8% hard stop, and the rest sold on a close below the 20-day average. Prices are adjusted for later splits.

### Tesla, December 2019 — a flat top, heavy volume, and a climax

This is the chart in section 1.

- **Pattern.** A flat top: highs of 24.08 on 20 November and 24.35 on 13 December. Between them the stock dipped 9%, to 21.81.
- **Entry.** Close of 16 December, 25.43, on 2.1 times average volume. That was 4.5% above the line, near the limit for chasing. Hard stop 8% lower, at 23.40.
- **The tight rule.** The stock never closed back below 24.35, so it never triggered.
- **The climax.** On 3 February 2020 the stock rose 19.9% on 3.5 times average volume. The next day it opened 13% higher and traded up to 64.60, on 4.2 times average volume.
- **Selling into it.** A sale at the 4 February close, 59.14, would have kept a gain of 133%. The next day the stock fell 17%.
- **The trend exit.** Without a climax sale, the first close below the 20-day came on 26 February, at 51.92. That is still +104%, but about 30 points less.

### Zydus Lifesciences, December 2023 — a shakeout below the line

```series
title: Zydus Lifesciences — a breakout on six times normal volume, a dip back below the line, and the run
from: 2023-10-01
to: 2024-04-30
tf: D
line: india:ZYDUSLIFE.NS | Zydus Lifesciences | log
line: india:ZYDUSLIFE.NS@sma20 | 20-day average
line: india:ZYDUSLIFE.NS@sma50 | 50-day average
line: india:ZYDUSLIFE.NS@vol | Volume | pane2 bars
mark: 2023-12-18 | breakout
mark: 2024-04-04 | exit
caption: The breakout above ₹664.95 came on 6.1× normal volume. Two days later the stock closed back below that ceiling: the tight rule sold, but the hard stop and the 20-day average held. Exit: the first close below the 20-day.
```

- **Pattern.** A ceiling at ₹664.95, set on 8 December 2023. The base was 16% deep.
- **Entry.** Close of 18 December, ₹680.60, on 6.1 times average volume. That is 2.4% above the line. Hard stop at ₹626.15.
- **The tight rule.** On 20 December the stock closed at ₹663.75, just below the line. The tight rule sold there, for −2.5%.
- **The hard stop.** It was never hit. The 20-day average held until 4 April 2024, when the close was ₹983.20: +44.5%.
- **Lesson.** A close back below the line is common and often harmless. Section 8 shows how often it happens.

### Broadcom, January 2025 — a trendline break, then a sector shock

```series
title: Broadcom — a falling-trendline breakout, and the gap that went through the stop
from: 2024-11-15
to: 2025-04-30
tf: D
line: us:AVGO | Broadcom | log
line: us:AVGO@sma20 | 20-day average
line: us:AVGO@sma50 | 50-day average
line: us:AVGO@vol | Volume | pane2 bars
mark: 2024-12-13 | results
mark: 2025-01-17 | breakout
mark: 2025-01-27 | gap
caption: A results-day gap, a high of 251.88 the next day, then a month under a falling trendline. The breakout held for a week. Then a shock to the whole chip group gapped the stock 13% lower, through the stop.
```

- **Setup.** Broadcom jumped 24% on its results on 13 December 2024 and peaked at 251.88 the next trading day. It then drifted down for a month under a falling trendline.
- **Entry.** On 17 January 2025 it closed at 237.44, above the trendline, on about average volume. A strict volume rule would have skipped it. Hard stop at 218.45.
- **What happened.** A week later the stock was at 249.59. On 27 January a new low-cost AI model from China hit chip stocks. Broadcom opened at 213.40, below the stop.
- **Result.** The stop filled at the open: −10.1%, not the planned −8%. By mid-April the stock was below 180.
- **Lesson.** A concentrated position in one hot group carries the group's news risk. Gaps go through stops; size for the gap, not the stop.

## 7. Common mistakes

| Mistake | Why it hurts |
|---|---|
| Drawing the line after the breakout | Any line can be drawn to fit; it must be fixed before |
| Buying on light volume because the chart looks good | No sign that a large buyer is present |
| Chasing a stock far above the line | The stop is far away; a normal pullback hits it |
| Treating every dip below the line as a failure | Most breakouts close below the line at least once |
| Ignoring the hard stop | Turns a failed breakout into a large loss |
| Holding through a climax run | The biggest gains can disappear in days |
| Concentrating in one group | One headline hits every position at once |
| Using margin early | Borrowed money magnifies mistakes faster than skill |

## 8. What the evidence says

**Zanger's record.** He has said he turned an account of about $11,000 into more than $18 million. That took under two years, during the late-1990s boom. The figure is self-reported and not audited. It was earned in one of the strongest speculative markets on record.

It shows that the method can be traded well in such a market. It does not show how it does for others, or in other markets.

**Published research behind the parts:**

- **Momentum.** Stocks that rose most over the prior 3–12 months tended to keep outperforming for months (Jegadeesh and Titman, 1993).
- **Nearness to the 52-week high.** Stocks near their 52-week high outperformed those far below it (George and Hwang, 2004).
- **Unusual volume.** Stocks with unusually high trading volume tended to rise over the following month (Gervais, Kaniel and Mingelgrin, 2001).
- **Chart patterns.** An automated study found that some patterns carry a little information about future returns, much less than practitioners claim (Lo, Mamaysky and Wang, 2000).
- **Pattern catalogues.** Thomas Bulkowski's large collection of pattern statistics reports that pullbacks to the breakout level are common after upward breakouts.

**An event study on stored data.** We coded the daily-data version and ran it on both markets.

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to October 2026. Liquidity on the day before: close ≥ ₹20 / $5 and 50-day average turnover ≥ ₹5 crore / $5m. "Big" stocks: turnover ≥ ₹50 crore / $100m. Uptrend: close above the 50-day, 50-day above the 200-day. Flat breakout: the first close above the highest high of the prior 30 sessions, from a range at most 25% deep. Trendline breakout: the first close above a falling line through the last two confirmed swing highs of the prior 60 sessions, with no close above it in between, from a pullback at most 25% deep. Entry at the breakout close. Exit on the first close below the 20-day average (from the second session), an 8% hard stop (gaps fill at the open), or after 120 sessions. One event per stock per 20 sessions. Caveats: today's lists only (survivorship bias), daily bars instead of intraday entries, no climax sale, no price-band locks.

| Breakouts in big, liquid stocks | India | US |
|---|---|---|
| Events | 7,413 (622 stocks) | 25,224 (1,065 stocks) |
| Winning trades | 34.9% | 35.5% |
| Average winner / average loser | +9.8% / −3.8% | +6.0% / −3.1% |
| Trades that gained 20% or more | 4.7% | 1.6% |
| Hard stop hit | 8.6% | 5.2% |
| Median holding period | 11 sessions | 12 sessions |
| **Average result, before costs** | **+1.0%** | **+0.1%** |
| Average result, after costs (0.3% / 0.1% a round trip) | +0.7% | 0.0% |
| Years with a positive average | 10 of 17 | 9 of 17 |

| Average result per trade, before costs | India | US |
|---|---|---|
| All big-stock breakouts (as above) | +1.0% | +0.1% |
| Smaller liquid stocks, same rules | +1.2% | +0.1% |
| Flat-top breakouts | +1.1% | +0.1% |
| Trendline breakouts | +0.8% | +0.1% |
| Breakout volume 2× average or more | +1.5% | +0.5% |
| Breakout volume 1–2× average | +0.7% | +0.1% |
| Breakout volume below average | +0.9% | +0.1% |
| Index below its 50-day average | +0.6% | +0.3% |
| Tight exit added (close back below the line, first 10 sessions) | +0.7% | +0.1% |
| 50-day average exit instead of the 20-day | +2.0% | +0.4% |

**How often breakouts dip back** (big stocks, first 10 sessions):

| | India | US |
|---|---|---|
| Closed back below the line at least once | 66.0% | 67.0% |
| Average result of those (20-day exit) | −1.9% | −1.8% |
| Average result of the rest | +6.7% | +4.0% |

What this shows:

- **The pattern alone is a thin edge.** Breakouts in big, liquid stocks made about 1% a trade in India and nothing in the US, before costs. Big stocks did no better than smaller liquid ones.
- **Heavy volume helped a little.** Breakouts on twice the usual volume did best in both markets, but the gap was small, and it was not consistent across bands of volume.
- **Trendline and flat-top breakouts behaved alike.** Drawing a falling line found as many trades and no better results.
- **The tight exit cut winners too.** Two in three breakouts closed back below the line within ten sessions. Those that did were, on average, losers. But selling all of them at once removed enough eventual winners that the average did not improve.
- **Holding longer helped.** The slower 50-day exit raised the average in both markets, with more hard stops hit on the trades that failed.
- **The best trades did most of the work.** The best 5% of trades produced about half of all gains.

**What is unknown.** Zanger buys intraday, using the day's volume pace, and sells into climax runs. Daily bars cannot test either. His choice of stocks — the few leaders of the hottest group — is judgement this test does not have. Treat the method as a framework, and the record as a description of one trader in one market.

## 9. Building and testing it yourself

**Data.** Adjusted daily OHLCV; intraday bars (5-minute or finer) if you want to test buying on the break with volume pace; an index; results dates; industry groups, to rank leaders.

**Look-ahead traps.**

- The line must use only swing highs that were confirmed before the breakout day. A swing high is only known a few sessions after it forms.
- The day's volume is only known at the close. An intraday entry must use the volume pace up to that minute, not the day's total.
- A climax can only be recognised after its biggest day. Test a rule you could have followed at the time, for example "sell after two days each up more than three ADRs on three times average volume".

**Survivorship.** Use lists that include delisted companies. Former leaders that collapsed and were delisted are exactly the trades a today's-list test leaves out.

**Costs.** In India a delivery round trip costs roughly 0.25–0.35%: securities transaction tax, stamp duty, exchange fees, GST and depository charges. With an average result near 1%, costs take a large share of the edge. Slippage on intraday breakout orders adds to that.

**What to test.** The exit rule matters more than the entry. Compare the 20-day, the 50-day and a climax sale. Test the volume rule as a filter, and check how many trades it removes. Report results with and without the best 1% of trades.

**What a good test reports.** Trades per year, win rate, average win and loss, and expectancy after costs. Also the share of gains from the best trades, the longest losing streak, drawdown, and results by market regime. See [Backtesting honestly](learn-test-backtesting.md).

```
each session t:
    leaders = stocks with turnover >= big floor, close > sma50 > sma200, strong relative strength
    for each stock in leaders:
        line = flat top of the base, or falling line through confirmed swing highs (both from bars up to t - 1)
        if close[t - 1] <= line(t - 1) and price crosses line(t):
            if volume pace < 1.5 * avg_volume_50: continue
            if price > 1.05 * line(t): continue
            entry = price at the cross (intraday) or close[t] (daily version)
            stop = entry * 0.92
            shares = capital * risk_pct / (entry - stop)
manage daily:
    if low <= stop: sell at min(open, stop)
    if tight_rule and sessions_held <= 10 and close < line: sell
    if climax(recent bars): sell most of the position
    if close < sma20: sell the rest
```

## 10. Checklist

- [ ] Market: leaders are breaking out and holding; recent breakouts are working
- [ ] Stock is big and liquid, in an uptrend, and a leader in a leading group
- [ ] Pattern named; line drawn through at least two highs before the breakout
- [ ] Base no more than about 25% deep
- [ ] Volume on pace for at least 1.5–2 times average
- [ ] Entry within 3–5% of the line
- [ ] Exit rule chosen: tight (close back below the line) or hard stop (7–8%), or both
- [ ] Position size from the stop; risk per trade 0.5–1%; size allows for a gap
- [ ] No results due, or a large cushion if holding through them
- [ ] Climax plan written: what you will sell, and on what kind of day
- [ ] Not too many positions in the same group
- [ ] In India: stock not in a price band that could lock

## Further reading

- Dan Zanger's interviews and newsletter commentary — his description of the patterns, volume and selling rules.
- Robert Edwards and John Magee, *Technical Analysis of Stock Trends* — the classical source for trendlines and chart patterns.
- Thomas Bulkowski, *Encyclopedia of Chart Patterns* — the largest public collection of pattern statistics.
- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and Selling Losers", *Journal of Finance* (1993).
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* (2004).
- Simon Gervais, Ron Kaniel and Dan Mingelgrin, "The High-Volume Return Premium", *Journal of Finance* (2001).
- Andrew Lo, Harry Mamaysky and Jiang Wang, "Foundations of Technical Analysis", *Journal of Finance* (2000).
- [CAN SLIM breakouts](learn-strat-canslim-breakout.md), [Kullamägi's momentum breakouts](learn-strat-kullamagi.md), [Stops and exits](learn-risk-stops-exits.md).
