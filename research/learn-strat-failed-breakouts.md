# Failed breakouts and bull traps — when a breakout turns into a sell signal

**In short**

- A breakout fails when the price closes back inside the base it just left. Buyers who paid up at the breakout are now holding a loss, and many of them sell.
- For a long position, a failed breakout is an exit signal. Get out on the close back in the base; do not wait for the full stop.
- For a short, the failure is a setup: sell on the close back in the base, with a stop just above the breakout's high.
- Failures are common. In our study of liquid stocks, more than half of all volume breakouts closed back below the breakout level within ten sessions. After a failure the stock lagged its index only slightly on average, so the short needs a weak market or a weak stock to pay.
- In India a swing short must be held through stock futures or options (see the Futures & options section). In the cash market you can only short intraday.

## 1. The idea

On 10 January 2025, HCL Technologies closed at ₹1,995, above the highest close of the previous three months (₹1,972). Volume was about twice its 50-day average. It looked like a clean breakout. The next day it held. On 14 January, after its quarterly results, it opened lower and closed at ₹1,814, back inside the old range, on six times normal volume.

```series
title: HCL Technologies — a breakout that failed within three sessions, January 2025
from: 2024-10-01
to: 2025-05-30
tf: D
line: india:HCLTECH.NS | HCL Technologies | log
line: india:HCLTECH.NS@sma50 | 50-day average
line: india:HCLTECH.NS@vol | Volume | pane2 bars
mark: 2025-01-10 | breakout close ₹1,995
mark: 2025-01-14 | back in the base, 6× volume
mark: 2025-04-09 | ₹1,380
caption: The close on 14 January was 9% below the breakout close. By 9 April the stock was 31% below it.
```

That is a **failed breakout**, also called a **bull trap**. The breakout pulled in buyers: traders who buy new highs, and holders who had waited for a sign before adding. When the price falls back into the range, every one of them is holding a loss.

Some sell at once. Others sell on the next rally, near what they paid. That selling is the reason a failed breakout can lead to a fall.

Who is on the other side? On the way up, the sellers were holders who used the breakout's demand to get out. On the way down, the short seller sells to the trapped buyers when they give up. The short is betting that the supply above the base is larger than the demand. The breakout tested that, and demand lost.

Richard Wyckoff, writing in the 1930s, called this move an **upthrust**: a push above resistance that quickly reverses. He read it as a sign that large holders were selling into the strength. The same idea appears in most chart-reading traditions. [The chart patterns guide](learn-chart-patterns.md) shows what a breakout should look like, and [the supply and demand guide](learn-supply-demand.md) explains why old highs hold sellers.

## 2. When it works and when it doesn't

**It works best when the market is weak.** A failed breakout in a falling market has the wind behind it. Most stocks follow the index, and a stock that could not hold a breakout in a weak market often has no buyers left. In a strong uptrend, failures are common too, but many of them are just shakeouts. The stock dips into the base, then breaks out again a few weeks later.

**It works best on a stock that has already had a long run.** A breakout late in an advance — the third or fourth base — attracts the last buyers. A failure there can mark the top. A failure from a first base after a long decline means less. The stock may still be building a bottom.

**It works best with a reason.** A failure on bad results, as with HCL Technologies, tells you something changed. A failure on a quiet day with low volume may be noise. A heavy-volume close back in the base is the stronger signal.

**It works badly in a sharp market rally.** When the whole market jumps, shorts get squeezed regardless of their chart. [The squeezes and bear-market rallies guide](learn-strat-squeezes-bear-rallies.md) covers that risk.

**India.** Retail traders cannot hold a short in the cash market overnight. A short sale in cash must be bought back the same day, or the shares go to auction with a penalty. For a swing short you need stock futures or put options, which exist only for the roughly two hundred stocks in the derivatives segment (see the Futures & options section). For a long position, the exit side of this guide applies to any stock. Circuit limits matter too: a stock with a 5% or 10% daily band can lock at its limit, and then you cannot exit at all that day.

**US.** Any stock you can borrow can be shorted in a cash account with margin. Borrowing is easy for large stocks and costly or impossible for small, heavily shorted ones. After a stock falls 10% in a day, US rules allow new short sales only at a price above the best bid, for the rest of that day and the next.

## 3. The rules

These rules define the trade for a short, and the exit for a long. Every number is a parameter, listed in §4.

### Universe and filters

- Liquid stocks only. The median daily traded value over the last 50 sessions is at least ₹10 crore in India or $10 million in the US.
- Price at least ₹50 or $5.
- For a short in India: the stock has futures or options, and it is not in the derivatives ban period (no new positions are allowed while open interest is above 95% of the market-wide limit).
- For a short in the US: shares are available to borrow at a fee you accept.
- Optional market filter for shorts: the index closes below its 50-day average.

### Setup

The setup has two parts: a breakout, then a failure.

1. **The breakout.** The stock closes above the highest close of the prior 60 sessions. That highest close is the **breakout level**. The previous close was at or below the level.
2. **Breakout volume.** Volume on the breakout day is at least 1.5 times the average of the previous 50 sessions.
3. **The trend.** On the breakout day the close is above the 50-day average. This keeps the study to real breakouts, not bounces in a downtrend.
4. **The failure.** Within 10 sessions after the breakout, the stock closes below the breakout level. A stricter version requires a close at least 3% below the level, or below the low of the breakout day.

### Entry

- **Short:** sell at the close of the failure day, or at the next open. With daily data, the next open is the honest choice for a test, because the close is only known once the session ends.
- **Long exit:** sell the long at the same moment. Do not wait for the original stop.

### Initial stop

- Place the buy-stop for the short just above the highest high from the breakout day to the failure day.
- Add a small buffer: 0.1 times the 14-day ATR.
- If the stop is more than 12% above the entry, skip the trade or size it down. A gap like HCL Technologies' can make the stop very wide.

### Exits

- **Trailing stop:** from the 20th session after entry, move the buy-stop down to the highest high of the last 20 sessions. Never move it up.
- **Target (optional):** cover half at 2R, the rest on the trailing stop.
- **Time stop:** if the trade is not at least 1R in profit after 20 sessions, cover.
- **Invalidation:** cover at once on a close back above the breakout level plus one ATR. The breakout has been repaired.

### Position size

Risk a fixed share of your account on each trade: 0.5% is a sensible start for shorts, half of a typical long. Shares (or lots) = account risk ÷ (stop − entry). In India, futures come in fixed lots, so round down to whole lots. If one lot is more risk than your rule allows, skip the trade. [The position sizing guide](learn-risk-sizing.md) shows the arithmetic.

### Managing the trade

- Check the stock and the index at each close. A sharp index rally is the main danger.
- Know the stock's next results date. A short held through results can gap either way.
- In India, roll a futures short before expiry if you want to keep it. Stock futures settle by delivery, so a short held to expiry means delivering shares.
- Do not add to a losing short.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Base length (lookback for the breakout level) | 60 sessions (40–120) | How big a range the breakout must clear | Longer bases give fewer, stronger signals |
| Breakout volume | 1.5× the 50-day average (1.3–2×) | Whether the breakout drew real buying | Higher thresholds cut signals sharply |
| Trend filter | Close above the 50-day average | Real breakouts only | Dropping it adds bounces in downtrends |
| Failure window | 10 sessions (3–15) | How soon the failure must come | Most failures came in the first three sessions |
| Failure depth | Any close below the level; or 3% below; or below the breakout-day low | How clear the failure must be | Stricter depth means fewer, cleaner trades |
| Stop buffer | 0.1 × ATR(14) | Room above the breakout high | Small; it only avoids a stop at a round high |
| Maximum stop distance | 12% of entry | Skips trades after big gaps | 8–15% is reasonable |
| Trailing stop lookback | 20 sessions (10–40) | How closely the short is trailed | Shorter locks in more, cuts more winners |
| Partial target | 2R (1.5–3R) | When to take half off | Optional |
| Time stop | 20 sessions | Frees money from dead trades | 10–30 |
| Risk per trade | 0.5% of account (0.25–1%) | Size | Lower than for longs, because of gaps |
| Liquidity | ₹10 crore / $10 million median daily value | Can you trade it | Raise for futures-only India shorts |
| Market filter | Index below its 50-day average | Shorts only in weak markets | Test with and without |

## 5. Variations

**Turtle Soup (Connors and Raschke).** In *Street Smarts* (1995), Laurence Connors and Linda Bradford Raschke describe trading false breaks of 20-day highs and lows. Their version needs the previous 20-day extreme to be at least four sessions old, and it enters as soon as the price comes back through it. It is a short-term trade, held for a few days. Their "Turtle Soup Plus One" waits for a second day.

**Wyckoff's upthrust.** Wyckoff traders look for a push above a trading range on high volume that closes back inside, late in a topping range. The short is taken on a weak rally after the upthrust, with the stop above its high.

**Bulkowski's busted patterns.** Thomas Bulkowski catalogues how often chart patterns fail. He treats a pattern whose breakout reverses as a "busted" pattern and trades the reversal in the other direction.

**The growth-stock sell rule.** William O'Neil and Mark Minervini both treat a breakout that falls back into the base as a reason to sell a long. Minervini stresses getting out quickly rather than waiting for the full stop. That is the long-side use of this guide.

**A tighter stop.** Some traders put the stop above the failure day's high, not the breakout's high. Risk per share is smaller, so the position is bigger, but the stop is hit more often. Test both.

A failed breakout to a new high often leaves a **double top** — two peaks at about the same level, with a dip between them.

```pattern
double-top
```

## 6. Worked examples

All prices are split-adjusted closes from daily data. R is the profit or loss divided by the initial risk per share.

### NVIDIA, October 2018 — a failure that led to a 50% fall (US)

```series
title: NVIDIA — a failed breakout to a new high, October 2018
from: 2018-07-01
to: 2019-02-28
tf: D
line: us:NVDA | NVIDIA (split-adjusted) | log
line: us:NVDA@sma50 | 50-day average
line: us:NVDA@vol | Volume | pane2 bars
mark: 2018-10-01 | breakout 7.23
mark: 2018-10-04 | back below 7.09
mark: 2018-11-16 | results gap
caption: The close fell back below the breakout level three sessions after the breakout. By 19 November the stock had halved.
```

| Step | Date | What happened |
|---|---|---|
| Breakout level | 1 Oct 2018 | Highest close of the prior 60 sessions: 7.09 |
| Breakout | 1 Oct 2018 | Close 7.23, volume 1.58× average, above the 50-day |
| Failure | 4 Oct 2018 | Close 6.98, below the level |
| Entry (short) | 4 Oct 2018 | 6.98 at the close |
| Initial stop | — | Highest high since the breakout, 7.32, plus buffer: 7.34. Risk 0.36 (5%) |
| What happened | Oct–Nov 2018 | The market sold off in October. After results on 15 November, the stock fell 19% the next day |
| Exit | 15 Jan 2019 | The 20-session trailing stop was hit at 3.79 |
| Result | — | +46% on the short, about +8.9R |

This is the trade at its best: a failure in a weakening market, at the end of a long run, followed by bad news. The prices are split-adjusted; the actual price at the time was 40 times higher.

### HCL Technologies, January 2025 — a failure on results (India)

The chart is in §1. A swing short here would have been through stock futures.

| Step | Date | What happened |
|---|---|---|
| Breakout level | 10 Jan 2025 | Highest close of the prior 60 sessions: ₹1,972 |
| Breakout | 10 Jan 2025 | Close ₹1,995, volume 1.98× average |
| Failure | 14 Jan 2025 | Close ₹1,814 after results, 6.2× volume |
| Entry (short) | 14 Jan 2025 | ₹1,814 |
| Initial stop | — | Highest high since the breakout, ₹2,012, plus buffer: ₹2,017. Risk ₹203 (11%) |
| What happened | Jan–Apr 2025 | The stock drifted lower and fell to ₹1,380 by 9 April |
| Exit | 12 May 2025 | The trailing stop was hit at ₹1,618 |
| Result | — | +11% on the price, about +1R |

The stock fell 31% from the breakout close, but the trade made only about 1R. The gap made the stop wide, so the risk per share was large. A long holder, though, gained a lot by selling on 14 January instead of waiting.

### Bharat Electronics, March 2024 — the failure that failed (India)

```series
title: Bharat Electronics — a failed breakout that recovered, 2024
from: 2024-01-01
to: 2024-06-28
tf: D
line: india:BEL.NS | Bharat Electronics | log
line: india:BEL.NS@sma50 | 50-day average
line: india:BEL.NS@vol | Volume | pane2 bars
mark: 2024-03-04 | breakout ₹209.6
mark: 2024-03-12 | back below ₹205.7
mark: 2024-04-02 | short stopped
caption: The breakout failed and the stock fell 12% in five sessions. Then it recovered, took out the high and rose 45% from the failure close by late May.
```

| Step | Date | What happened |
|---|---|---|
| Breakout level | 4 Mar 2024 | Highest close of the prior 60 sessions: ₹205.65 |
| Breakout | 4 Mar 2024 | Close ₹209.60, volume 1.51× average |
| New high | 7 Mar 2024 | Close ₹215.20, high ₹216.80 |
| Failure | 12 Mar 2024 | Close ₹204.25, below the level |
| Entry (short) | 12 Mar 2024 | ₹204.25. Stop ₹217.47 (risk ₹13.2, 6.5%) |
| What happened | 15 Mar 2024 | Intraday low ₹179.10 on 3.7× volume. Then a steady recovery |
| Exit | 2 Apr 2024 | Stop hit at ₹217.47 |
| Result | — | −1R |

Nothing was wrong with the setup. The market was strong and defence stocks were in demand. The stock closed at ₹297.20 on 24 May. This is why a short needs a stop, and why the market filter in §3 is worth testing.

## 7. Common mistakes

- **Shorting the breakout before it fails.** A stock at a new high is strong until it proves otherwise. Wait for the close back in the base.
- **Treating every dip as a failure.** An intraday dip below the level that closes above it is not a failure. Use closes.
- **Ignoring the market.** A failed breakout in a strong market is often a shakeout. Most of the losers in a test come from strong markets.
- **A stop too far away.** After a gap, the breakout high may be 10% or more above the entry. Size down or skip.
- **Holding a long "until the stop".** If you are long and the breakout fails, the reason you bought is gone. Sell or cut the position.
- **Shorting a small, crowded stock.** Heavily shorted, thinly traded stocks can jump 30% in a day. See [the squeezes guide](learn-strat-squeezes-bear-rallies.md).
- **In India, forgetting the expiry.** A futures short must be rolled before expiry, or it ends in delivery.

## 8. What the evidence says

**Published research.** There is little academic work on failed breakouts as such. Practitioner books — Wyckoff's writing, Connors and Raschke, Bulkowski — describe the pattern and its trade, but their figures come from their own samples and are hard to check.

Work on short selling is more solid. Boehmer, Jones and Zhang (2008) found that stocks heavily shorted by institutions did worse than lightly shorted ones in the following weeks. That suggests short sellers, as a group, are informed. It does not test this setup.

**Our event study.** We looked at every volume breakout in liquid Indian and US stocks from 2012 to mid-2025.

*Method.* A breakout is a close above the highest close of the prior 60 sessions. Volume had to be at least 1.5 times its 50-day average, and the close above the 50-day average.

 Liquid means a median daily traded value of at least ₹10 crore or $10 million. The price had to be at least ₹50 or $5. We took at most one breakout per stock in any 60 sessions. A breakout failed if the stock closed below the breakout level within 10 sessions. Returns after a failure are measured from the failure close. The index is the Nifty 500 for India and the S&P 500 total return for the US.

| | India | US |
|---|---|---|
| Breakouts studied | 7,050 | 22,971 |
| Closed back below the level within 10 sessions | 57% | 53% |
| Closed more than 3% below the level | 33% | 27% |
| Closed below the breakout day's low | 39% | 41% |
| Failures that came on the first session after the breakout | 31% | 37% |
| Failures within the first three sessions | 63% | 66% |

| Median return over 60 sessions, from the breakout close | India | US |
|---|---|---|
| Breakouts that held | +7.4% | +4.5% |
| Breakouts that failed | −1.5% | −1.5% |

| After a failure more than 3% below the level | India | US |
|---|---|---|
| Median return over the next 20 sessions | +0.4% | +0.4% |
| Median return over 60 sessions, minus the index | −1.6% | −2.7% |
| Share that lagged the index over 60 sessions | 53% | 58% |

*What it shows.* First, failure is normal. More than half of all volume breakouts dipped back below their level within two weeks, most of them within three days. Second, the failure matters for a long: held breakouts went on to gain, failed ones did not. Third, a failure on its own is a weak short signal. The typical failed stock still edged up in price, and it lagged the index by only a few percent.

*Caveats.* The stock lists are today's lists, so companies that were delisted are partly missing (survivorship bias). Breakouts cluster in strong markets, so the years are not independent. The "held" group is defined using the next ten sessions, which you cannot know on the breakout day. These are raw medians, before costs, with no stop or exit rule.

**What is unknown.** Whether adding a market filter, a results trigger or a late-stage base turns this into a real edge. Practitioners say it does. Test it on your own data before you rely on it.

## 9. Building and testing it yourself

**Data.** Daily open, high, low, close and volume, adjusted for splits. Index closes for the market filter. Results dates if you test the "failure on news" idea. For India, the list of stocks with derivatives on each date, and the ban list.

**Look-ahead traps.**
- The breakout level must use closes *before* the breakout day.
- The failure is known only at the close. Enter at the next open in a test, or accept that a close entry needs you to act in the last minutes.
- The derivatives list changes. Use the list as it was on each date, not today's.

**Survivorship.** Stocks that collapsed and were delisted are the best shorts. A test on today's stocks leaves them out, so it understates the short side. Use data that includes delisted stocks if you can.

**Costs and slippage (approximate).**
- India, stock futures: brokerage about ₹20 per order; securities transaction tax (STT) 0.05% on the sell side (since April 2026); stamp duty about 0.002% on the buy side; exchange fees and GST on top. Allow about 0.05% per side for slippage in liquid names.
- India, intraday cash short: STT about 0.025% on the sell side; stamp duty about 0.003% on the buy side.
- US: commissions are near zero at most brokers. The cost is the bid-ask spread, the borrow fee (often under 1% a year for large stocks, much higher for crowded ones) and dividends, which a short must pay.
- Gaps: a short stop is often filled above the stop price when the stock gaps up. Fill at the open if the open is beyond the stop.

**Over-fitting.** Pick the parameters before you look at results. Vary each one in steps, such as a base length of 40, 60 or 90 sessions. Look for a plateau of good results, not a single peak. Keep the last few years out of the test and check them once at the end. [The backtesting guide](learn-test-backtesting.md) covers this in detail.

**What a good test reports.**

- Number of trades, win rate, and the average win and loss in R.
- Expectancy in R, and the worst run of losses.
- Results by year and by market regime.
- Results with and without the market filter, and the effect of costs.

```
for each stock, each day t:
    level = max(close[t-60 .. t-1])
    if close[t] > level and close[t-1] <= level
       and volume[t] >= 1.5 * mean(volume[t-50 .. t-1])
       and close[t] > sma50[t]:
        breakout_high = high[t]
        for k in 1 .. 10:
            breakout_high = max(breakout_high, high[t+k])
            if close[t+k] < level:
                entry = open[t+k+1]            # next open
                stop  = breakout_high + 0.1 * atr14[t+k]
                if (stop - entry) / entry <= 0.12:
                    open_short(entry, stop)
                break
manage: from day 20, stop = min(stop, max(high[last 20]));
        cover at stop (or at the open if it gaps above), or after 20 days if < 1R
```

## 10. Checklist

- [ ] The breakout was real: a close above the base's highest close, on at least 1.5× volume, above the 50-day.
- [ ] The failure is a **close** back below the breakout level, within 10 sessions.
- [ ] The market is weak, or I have a clear reason the stock is (results, a late-stage base).
- [ ] I can short it: futures or options in India and not in the ban period; borrow available in the US.
- [ ] The stop is above the breakout's high and no more than 12% away.
- [ ] Position size: risk is 0.5% of the account or less, in whole lots.
- [ ] I know the next results date and the futures expiry.
- [ ] If I am long this stock, I am selling now.

## Further reading

- Laurence A. Connors and Linda Bradford Raschke, *Street Smarts: High Probability Short-Term Trading Strategies* (1995).
- Thomas N. Bulkowski, *Encyclopedia of Chart Patterns* (2nd ed., 2005).
- Richard D. Wyckoff, *The Richard D. Wyckoff Method of Trading and Investing in Stocks* (course, 1931; later reprints).
- Mark Minervini, *Trade Like a Stock Market Wizard* (2013).
- William J. O'Neil, *How to Make Money in Stocks* (4th ed., 2009).
- Ekkehart Boehmer, Charles M. Jones and Xiaoyan Zhang, "Which Shorts Are Informed?", *Journal of Finance* 63 (2008).
