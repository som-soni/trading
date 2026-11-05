# Momentum bursts — Bonde's 4% breakout, held for a few days

**In short**

- Pradeep Bonde (Stockbee) observed that stocks move in short bursts of three to five days, then rest. A burst often starts from a quiet stock with one decisive up day.
- His trigger is the "4% breakout": a close at least 4% above yesterday's, on more volume than yesterday. He buys it, puts the stop at the day's low and sells within a few days.
- The trade is short and mechanical. Most of the work is the daily scan and the discipline to sell on time.
- On stored daily data, a close-entry version made a small average gain in India (+0.05R a trade after costs) and roughly nothing in the US. The "quiet before" and volume rules added nothing.
- Treat it as a framework to test with intraday data, not a proven edge on daily bars.

## 1. The idea

On Friday 1 December 2023, Adani Ports closed at ₹827.80. It had moved less than 1.5% a day for three sessions. Volume that Friday was below its 50-day average.

```series
title: Adani Ports — a quiet week, a 6% day, then the burst
from: 2023-10-16
to: 2024-01-31
tf: D
line: india:ADANIPORTS.NS | Adani Ports
line: india:ADANIPORTS.NS@vol | Volume | pane2 bars
mark: 2023-12-04 | burst
mark: 2023-12-11 | sold
caption: The 4 December close was 6.1% above Friday's, on 3 times average volume, near the day's high. Five sessions later the stock was 17% higher.
```

On Monday 4 December it closed at ₹878.65, up 6.1%. Volume was three times its average, and the close was near the day's high. That is a momentum burst trigger.

A burst trade bought that close with a stop at the day's low, ₹858.50. The risk was ₹20.15 a share, about 2.3%. The next day the stock rose another 15%. Five sessions after the entry it closed at ₹1,031.90, and the trade sold there: +7.6 times the risk.

That is the whole method. **Watch for the first strong day out of a quiet stretch. Buy it. Keep the stop at that day's low. Sell after a few days, whatever happens.**

Why might it work? A burst usually has a cause: results, an order win, news about the sector. Not everyone acts on the first day. Some buyers need a second look, or a committee, or a day to read the report. Their buying can carry the move for a few more days.

Most bursts do not run like Adani Ports. Many stall, and some reverse the next day. The method accepts that: the stop keeps each failure small, and the short hold takes profits before the move fades.

## 2. When it works and when it doesn't

It works best when the market is rising and many stocks are breaking out. Bursts then follow through more often, and a trader finds several a day.

It works poorly in:

- **Falling markets.** Up days are often short-covering or relief rallies. They reverse quickly.
- **Event days that resolve the next day.** A burst on a rumour or a poll can reverse when the real news arrives. See the SBI example in section 6.
- **Thin stocks.** A 4% move on a few trades is not a burst. It is noise.

It differs from the other breakout methods in its time frame. A base breakout (see [SEPA and the VCP](learn-strat-vcp-sepa.md) or [Kullamägi's momentum breakouts](learn-strat-kullamagi.md)) aims to hold for weeks. A burst trade aims to sell within a week, before the stock rests again.

**India.** Many smaller Indian stocks have daily price bands of 5%, 10% or 20%. A burst can lock at the upper band, so there is no close to buy. A failure can lock at the lower band, so the stop cannot fill. Prefer stocks without a band, or with a wide one.

**US.** Liquidity is deep and intraday entries are easy. But the market reacts fast, so much of a burst can be gone by the close.

## 3. The rules

Each rule below is a condition a program can check. Section 4 gives the ranges.

### Universe and trend

- **Liquidity.** Enough daily turnover to enter and leave at the close without moving the price.
- **Uptrend.** The close is above the 200-day average, and that average is not falling: it is no more than 0.5% below its value 20 sessions ago.
- **Near the highs.** The close is within 15% of the 52-week high. Bonde trades bursts more widely; this version stays with the trend.

### The quiet before

- **Not already moving.** Yesterday closed no more than 2% above the session before. A burst is the first strong day, not the second.
- **Narrow days.** A day's range is its high minus its low, as a share of its close. The average range of the 3 sessions before today is no wider than the average of the 20 sessions before today.

### The burst

- **Size.** Today's close is at least 4% above yesterday's close.
- **Volume.** Today's volume is higher than yesterday's. (Bonde's rule. A stricter version asks for more than the 50-day average.)
- **Strength into the close.** The close sits in the top 30% of the day's range: (close − low) ÷ (high − low) is at least 0.7.

### The market

- The broad index (the Nasdaq-100 in the US, the Nifty 500 in India) closes above its 20-day exponential average. Its 10-day exponential average is above its 20-day one.

### Entry

- **His way.** Bonde buys during the day, as the stock crosses +4% or breaks the high of its opening range. The stop is the day's low so far. See [Opening range breakouts](learn-strat-orb.md).
- **Daily-data version.** Buy at the close of the burst day.

### Stop

- The low of the burst day. In the daily version that is the whole day's low.
- If the stop is less than 1% below the entry, skip the trade. A tiny range leaves no room for ordinary noise.
- The stop never moves.

### Exit

- Sell at the close of the fifth session after the entry. Bonde often sells sooner, into a strong day.
- Sell at the stop if it is hit first, or at the open if the stock gaps below it.
- There is no profit target. The time limit is the exit.

### Position size

- Risk a small, fixed share of capital: shares = (capital × risk %) ÷ (entry − stop). See [Position sizing](learn-risk-sizing.md).
- Cap any one position. A gap through the stop can cost two or three times the planned risk (see the Microsoft example).

## 4. The parameters

| Parameter | Value used here | Range seen | What it controls |
|---|---|---|---|
| Burst size | 4% close to close | 4–5% | How decisive the day must be |
| Burst volume | Above yesterday's | Above yesterday's, or above the 50-day average | Participation |
| Close in range | Top 30% | Top 25–50% | Strength into the close |
| Yesterday's gain | At most 2% | 1–2% | That the burst is the first day |
| Quiet sessions | 3 | 2–5 | How long the quiet stretch is |
| Reference sessions | 20 | 10–50 | What "normal range" means |
| Trend | Above a rising 200-day; within 15% of the high | Optional for Bonde | Trading with the trend |
| Market | Index above its 20-day EMA; 10-day above 20-day | Optional | When to trade |
| Stop | The burst day's low | Low of the opening range (intraday) | The risk, 1R |
| Minimum stop | 1% | 0.5–1.5% | Skipping no-room trades |
| Hold | 5 sessions | 3–5 sessions | When to sell |

## 5. Variations

- **Bonde's own scans.** He runs several daily scans: the 4% breakout, a dollar-gain version for high-priced stocks, and breakouts from narrow-range days. He reads each result by eye before trading it.
- **The episodic pivot.** A burst caused by big news, usually results, on many times normal volume. It can lead to a move of months rather than days. See [Earnings gaps and episodic pivots](learn-strat-earnings-gaps.md).
- **Base breakouts.** The same first strong day, from a longer base, held for weeks. See [Kullamägi's momentum breakouts](learn-strat-kullamagi.md) and [Darvas boxes](learn-strat-darvas.md).
- **Selling into strength.** Instead of a fixed hold, sell part into the first big up day after the entry, and the rest at the time limit.
- **Opening range entry.** Buy the break of the first 5 or 15 minutes' high on the burst day. The stop is closer, so the same move is worth more R.

## 6. Worked examples

These use the daily-data version: buy the burst close, stop at that day's low, sell at the close of the fifth session after. Prices are adjusted for later splits and bonus issues.

### Adani Ports, December 2023 — the burst that ran

This is the chart in section 1.

| | |
|---|---|
| Quiet before | Ranges of about 2% or less for three sessions; Friday's volume 0.8 times average |
| Burst | 4 December: +6.1%, volume 3.0 times average, close near the high |
| Entry | ₹878.65 (the close) |
| Stop | ₹858.50 (the day's low): risk ₹20.15, about 2.3% |
| Next day | +15.3% on 10 times average volume |
| Exit | 11 December, the fifth session: ₹1,031.90 |
| Result | +17.4%, or +7.6R |

A result like this is rare. In the study in section 8, fewer than one trade in a hundred made more than 5R.

### SBI, June 2024 — a burst on a forecast, reversed by the facts

```series
title: SBI — a 9% burst on exit-poll day, then the election result
from: 2024-04-15
to: 2024-07-31
tf: D
line: india:SBIN.NS | State Bank of India
line: india:SBIN.NS@vol | Volume | pane2 bars
mark: 2024-06-03 | burst
mark: 2024-06-04 | stopped
caption: The exit polls lifted the whole market on 3 June. The election result the next day did not match them, and the stock fell through the burst day's low.
```

| | |
|---|---|
| Quiet before | Four sessions within about 1% of ₹830 |
| Burst | 3 June: +9.1%, volume 3.4 times average, close near the high |
| Entry | ₹905.65 |
| Stop | ₹856.75: risk 5.4% |
| Next day | Opened at ₹897, fell to ₹731.95 |
| Exit | Stopped at ₹856.75 |
| Result | −1R |

The burst was real, but its cause was a forecast. When the actual result came out, the forecast was wrong and the move reversed. On a day this violent, a real stop order may fill well below its price.

**Lesson.** Know what caused the burst. A burst on news that is still to be confirmed carries the risk of that confirmation.

### Microsoft, January 2025 — a gap through the stop

| | |
|---|---|
| Burst | 22 January: +4.1%, volume 1.3 times average |
| Entry | $446.20 |
| Stop | $436.00: risk 2.3% |
| Two sessions later | Still near $444 |
| 27 January | Opened at $424.01, below the stop, on a sell-off in AI stocks |
| Exit | At the open, $424.01 |
| Result | −2.2R |

The stop was never "hit" at its price. The stock opened below it. A tight stop protects against a slow decline, not against a gap.

**Lesson.** Size every position so a gap of two or three times the stop distance is survivable.

## 7. Common mistakes

| Mistake | Why it hurts |
|---|---|
| Buying the second or third day of a move | Most of the burst is gone, and the stop is far below |
| Holding past the time limit "because it might keep going" | The burst ends and the gain fades; the method's edge is in short holds |
| Moving the stop down | Turns a planned −1R into a much larger loss |
| Trading every 4% day in a falling market | Up days in a downtrend are often relief rallies that reverse |
| Ignoring what caused the burst | A burst on a rumour or a forecast can reverse on the facts |
| Holding through results with a tight stop | A gap jumps the stop |
| Buying a stock locked at its upper price band | There is no fill, or the fill comes at the worst price |
| Judging the method on a handful of trades | Results are spread wide; only hundreds of trades say anything |

## 8. What the evidence says

**Bonde's record.** He has taught the method for many years and reports trading it himself. His results are not audited. A trader's own success shows a method can be traded. It does not show how much depends on his scans, his judgement and his intraday entries.

**Published research behind the parts:**

- **Short-term reversal.** Stocks that rose most over the past week or month tended to do worse the next week or month (Jegadeesh, 1990; Lehmann, 1990). On average, a big up move partly reverses. A burst trader is betting that some bursts are exceptions.
- **Volume and continuation.** Stocks with unusually high trading volume over a day or a week tended to earn higher returns over the following month (Gervais, Kaniel and Mingelgrin, 2001).
- **Volume and reversal.** The short-term reversal was strongest in heavily traded stocks. Lightly traded stocks showed more continuation (Conrad, Hameed and Niden, 1994).
- **News versus no news.** Large moves that came with public news tended to continue. Large moves without news tended to reverse (Chan, 2003).
- **Nearness to the 52-week high.** Stocks close to their 52-week high outperformed those far below it (George and Hwang, 2004).

The research points both ways. Big moves tend to reverse, but moves with news and unusual volume tend to continue. A burst method lives in that gap.

**An event study on stored data.** We coded the daily-data version and ran it on both markets.

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to October 2026. Liquidity on the day before: close ≥ ₹20 / $5, 50-day average turnover ≥ ₹5 crore / $5m. Trend: close above the 200-day average, the 200-day no more than 0.5% below its value 20 sessions earlier, close within 15% of the 52-week high. Quiet: yesterday up at most 2%; the mean range of the 3 sessions before no wider than that of the 20 before. Burst: close at least 4% above yesterday's, volume above yesterday's, close in the top 30% of the day's range. Market: Nifty 500 (India) or Nasdaq-100 (US) above its 20-day exponential average, with its 10-day above its 20-day. Entry at the burst close; stop at that day's low, skipped if under 1% away. Exit at the stop (or the open, if it gaps through), else at the close of the fifth session after entry. One open trade per stock at a time. Costs: 0.3% (India) and 0.1% (US) a round trip. Caveats: today's lists only (survivorship bias), daily bars instead of intraday entries, fills at the stop on days that do not gap through it, no price-band locks.

| Momentum bursts, daily-data version | India | US |
|---|---|---|
| Trades | 11,335 (1,354 stocks) | 16,932 (2,657 stocks) |
| Median stop distance | 5.5% | 4.8% |
| Stopped out | 28.5% | 35.1% |
| Stopped out within two sessions | 11.1% | 17.7% |
| Winning trades | 45.4% | 45.0% |
| Average winner | +1.09R | +1.02R |
| Average loser | −0.71R | −0.80R |
| Median trade | −0.11R | −0.15R |
| Trades of +5R or more | 0.7% | 0.5% |
| Share of all gains from the best 5% of trades | 37% | 37% |
| **Average result, before costs** | **+0.11R** | **+0.02R** |
| Average result, after costs | +0.05R | −0.01R |
| Years with a positive average, before costs | 11 of 17 | 10 of 17 |

| Average result in R, before costs | India | US |
|---|---|---|
| The rules above (5-session hold) | +0.11 | +0.02 |
| 3-session hold | +0.09 | +0.01 |
| 10-session hold | +0.13 | +0.03 |
| Market filter failed | +0.09 | +0.03 |
| Bursts of 5% or more | +0.10 | +0.03 |
| Burst volume above its 50-day average | +0.11 | +0.01 |
| Burst volume below its 50-day average | +0.13 | +0.04 |
| Same bursts without the quiet before | +0.13 | +0.04 |

**Where the stocks went next.** The return from the burst close, minus the average return of every uptrend stock on the same day:

| Sessions after the burst | India: average | India: median | US: average | US: median |
|---|---|---|---|---|
| 1 | +0.24% | −0.29% | 0.00% | −0.11% |
| 5 | +0.15% | −0.88% | +0.05% | −0.22% |
| 20 | +0.17% | −1.74% | +0.18% | −0.54% |

What this shows:

- **There is little to no edge in the daily-bar version.** In India the average trade made about a twentieth of the risk after costs. In the US it lost slightly.
- **The typical burst does not continue.** The median stock did worse than the average uptrend stock after its burst. A few large continuations lift the average above zero.
- **The stop is what makes the trade.** Close-to-close, the edge over other uptrend stocks is a fraction of a percent. The trade's small profit comes from cutting the failures at the burst day's low.
- **The filters did not help.** The quiet stretch, above-average volume, a bigger burst and the market filter made no clear difference in either market.
- **Holding longer did not hurt.** A 10-session hold did slightly better than five. The short hold is Bonde's choice, not something these data demand.

**What is unknown.** Bonde buys intraday, as the stock crosses +4%, with the stop at the low so far. That entry is earlier and its stop closer, so the same move is worth more R. Daily bars cannot test it.

He also reads every chart and skips most of what his scans find. That judgement is not coded here at all. Treat the rules as a framework to test with intraday data, not as an edge.

## 9. Building and testing it yourself

**Data.** Adjusted daily OHLCV for the whole universe, for the scan and the trend filter. Intraday bars (1- or 5-minute) for the entry and stop, if you want to test the method as it is traded. An index for the market filter. Results dates, to know which bursts are news-driven.

**Look-ahead traps.**

- The day's low and close are known only at the close. A daily test cannot both buy early in the day and use the day's low as its stop.
- The "quiet before" must use only sessions before the burst day.
- The 50-day average volume must end the day before, if the rule compares the burst against it.

**Survivorship.** Use lists that include delisted companies. Stocks that burst and then collapsed into delisting are exactly the failures a today's-list test misses.

**Costs.** In India a delivery round trip costs roughly 0.25–0.35%: transaction tax, stamp duty, exchange fees, GST and depository charges. With a 5% stop that is about 0.06R a trade. With a 2% stop it is 0.15R. Slippage on a fast stock is often larger than the costs. Measure results in R after both.

**What to test.** The hold length, the minimum stop, the burst size and the entry (close versus intraday). Change one at a time. Report results by year and by market regime, not only in total. See [Backtesting honestly](learn-test-backtesting.md).

```
each session t, after the close:
    for each stock with enough liquidity:
        if not (close > sma200 and sma200 not falling and close >= 0.85 * high_52w): continue
        if close[t-1] / close[t-2] - 1 > 2%: continue                  # already moving
        if mean(range[t-3 .. t-1]) > mean(range[t-20 .. t-1]): continue  # not quiet
        if close[t] / close[t-1] - 1 >= 4% and volume[t] > volume[t-1]
           and (close[t] - low[t]) / (high[t] - low[t]) >= 0.7:
            entry = close[t]; stop = low[t]
            if (entry - stop) / entry < 1%: continue
            shares = capital * risk_pct / (entry - stop)
manage daily:
    if open <= stop: sell at open
    elif low <= stop: sell at stop
    elif sessions_held == 5: sell at close
```

## 10. Checklist

- [ ] Market: the index above its 20-day average; other breakouts are working
- [ ] Stock in an uptrend, near its 52-week high, liquid enough for the size
- [ ] Quiet before: yesterday up 2% or less; narrow ranges for the last few days
- [ ] Today: up 4% or more, on more volume than yesterday, closing near the high
- [ ] The cause known: results, an order, sector news, or a forecast still to be confirmed
- [ ] Stop at the day's low, at least 1% below the entry
- [ ] Position sized from the stop, and small enough to survive a gap through it
- [ ] No results or major event due before the planned exit
- [ ] Exit planned: the fifth session's close, or sooner into strength
- [ ] In India: the stock not locked at its price band

## Further reading

- Pradeep Bonde's Stockbee blog and courses — his own description of momentum bursts, the 4% breakout and episodic pivots.
- Narasimhan Jegadeesh, "Evidence of Predictable Behavior of Security Returns", *Journal of Finance* (1990).
- Bruce Lehmann, "Fads, Martingales, and Market Efficiency", *Quarterly Journal of Economics* (1990).
- Simon Gervais, Ron Kaniel and Dan Mingelgrin, "The High-Volume Return Premium", *Journal of Finance* (2001).
- Jennifer Conrad, Allaudeen Hameed and Cathy Niden, "Volume and Autocovariances in Short-Horizon Individual Security Returns", *Journal of Finance* (1994).
- Wesley Chan, "Stock Price Reaction to News and No-News: Drift and Reversal After Headlines", *Journal of Financial Economics* (2003).
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* (2004).
- [Kullamägi's momentum breakouts](learn-strat-kullamagi.md), [Earnings gaps and episodic pivots](learn-strat-earnings-gaps.md), [Opening range breakouts](learn-strat-orb.md), [Stops and exits](learn-risk-stops-exits.md).
