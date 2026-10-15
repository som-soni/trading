# Channel breakout trend following — buy the new high, sell the new low

**In short**
- Buy when the price breaks above its highest high of the last 55 sessions. Sell when it breaks below its lowest low of the last 20.
- This is the Donchian channel rule that the Turtle traders made famous in the 1980s, with every position sized by the market's daily range.
- Most breakouts fail. The system wins because a few breakouts turn into long trends that pay many times the risk.
- It suits liquid stocks, index futures and ETFs that make long moves. It suffers in sideways markets and on overnight gaps.
- Expect a win rate around 35%–45%, long losing streaks and results that depend on a handful of trades.

## 1. The idea

On 10 November 2023, Hindustan Aeronautics (HAL) traded above ₹2,085. That was its highest price of the previous 55 sessions. A channel-breakout rule bought there. The stop sat two "average daily ranges" lower, at about ₹2,003. Four months later the stock was near ₹3,000 and the rule sold on 20 March 2024, when the price broke its 20-session low.

```series
title: HAL, 2023–2024 — breakouts to 55-day highs, exits at 20-day lows
from: 2023-01-01
to: 2024-12-31
line: india:HAL.NS | HAL | log
line: india:HAL.NS@sma50 | 50-day average (for reference)
line: india:HAL.NS@vol | Volume | pane2 bars
mark: 2023-04-28 | entry
mark: 2023-08-03 | exit
mark: 2023-11-10 | entry
mark: 2024-03-20 | exit
mark: 2024-04-01 | entry
mark: 2024-07-18 | exit
caption: Three winning trades between April 2023 and July 2024, separated by small losses (see the table in §6).
```

A **Donchian channel** is two lines on a chart: the highest high and the lowest low of the last N sessions. Richard Donchian, a futures fund manager from the 1950s on, traded breakouts of such channels. The rule asks nothing about value or news. A new 55-day high means buyers are paying more than anyone paid for about three months. That is the definition of an uptrend starting or continuing.

Why can it work? A stock at a multi-month high has no recent buyers sitting on losses and waiting to sell. Investors are slow to raise their estimates after good news, so prices tend to keep drifting. Research on the 52-week high finds that stocks near their highs tend to keep outperforming (George and Hwang, 2004).

Who is on the other side? The seller who thinks a three-month high is "too high", and the short seller who bets on a pullback. Usually they are right: most breakouts stall. The trend follower accepts many small losses to be on board for the one that does not stall.

The **Turtles** were trainees taught by the traders Richard Dennis and William Eckhardt in 1983–84. Their rules were later published by former Turtles. They combined channel entries and exits with sizing by volatility. Section 3 follows their System 2, adapted to stocks.

## 2. When it works and when it doesn't

It works when a market makes a long one-way move: a sector re-rating, a commodity boom, a multi-year bull market in an index. The defence stocks in India in 2023–24 and Nvidia in 2023 are examples. It also works for short futures positions in long bear markets, which is where the Turtles made much of their money.

It fails in ranges. A stock that oscillates inside a wide band touches the top often enough to trigger entries, then falls back to the bottom. Each round trip costs about one unit of risk. It also fails when news gaps the price through the stop, as in the HAL loss of March 2023 (§6).

| Market condition | What the system does | What to expect |
|---|---|---|
| Long one-way trend | Enters early in the move and holds for months | A few trades of 5R to 15R |
| Wide sideways range | Buys near the top of the range, sells near the bottom | A run of 1R losses |
| Narrow sideways range | Breakouts are small and the 2N stop is close | Many small losses and small wins |
| Sharp V-shaped reversal | Exits after the fall, re-enters after the rise | One loss, then a late entry |
| Slow grind higher | The 20-day low is rarely hit | Long holds with modest gains |

**Stock types.** It suits liquid stocks with high volatility and a reason to trend: earnings growth, a sector in favour, a commodity cycle. It suits slow utilities and staples less well. On those a 55-day high is often just noise.

**India notes.** Indian stocks with price bands of 5% or 10% can lock at the upper circuit on a breakout. Then a buy stop does not fill at all.

On the way down they can lock at the lower circuit and the stop does not fill either. Shorting a breakdown is possible in cash only for the day. A swing short needs stock futures or options (see the Futures & options section). Index versions run on Nifty futures or Nifty ETFs.

**US notes.** US stocks trade without circuit bands, and stop orders fill in deep markets. Pre-market and after-hours moves on earnings still produce gaps through stops. Short selling a 20-day low breakdown is simple in a margin account, subject to borrow.

## 3. The rules

### Universe and filters

- Liquid stocks: median daily turnover over 50 sessions of at least ₹10 crore in India or $10 million in the US.
- Price at least ₹50 or $5.
- At least 75 sessions of history, so both channels and the volatility estimate exist.
- Index version: Nifty 50 or Bank Nifty futures, or index ETFs; S&P 500 and Nasdaq 100 futures or ETFs in the US.
- Optional: the stock is above its rising 200-day average, or the market is in an uptrend (see [regime filters](learn-strat-regime-filters.md)).

### Setup

- The **entry level** is the highest high of the previous 55 sessions, not including today.
- The **exit level** is the lowest low of the previous 20 sessions, not including today.
- **N** is the 20-day average true range. The true range of a day is its high minus its low, widened to include any gap from the previous close.
- No setup is needed beyond the channel. The breakout itself is the signal.

### Entry

- Place a buy stop order at the entry level, one tick above it.
- If the stock opens above the level, the fill is the open, not the level.
- Recompute the levels after every close and move the order.

### Initial stop

- The stop is the entry price minus 2 × N, using N on the day before entry.
- With the Turtle sizing below, a 2N stop risks about 2% of the account per full unit. Stock traders usually halve that (see Position size).

### Exits

- **Trailing exit:** a sell stop at the 20-session low. Raise it every day as the low rises; never lower it.
- The **stop in force** is the higher of the 2N stop and the 20-session low.
- **No profit target and no time stop** in the original rules.
- **Faster variant (Turtle System 1):** enter on a 20-session high, exit on a 10-session low.

### Position size

- The Turtle **unit**: the number of shares whose daily move of N equals 1% of the account. Shares = (1% × account) ÷ N.
- Example: a ₹10 lakh account and N of ₹41 give 243 shares. At ₹2,085 that position is worth about ₹5 lakh, half the account.
- That is why stock traders cap positions. Use 0.5% instead of 1% per unit, and cap any position at 20% of the account.
- See [position sizing](learn-risk-sizing.md) for the general formula.

The same rule sizes a calm stock and a volatile one very differently. In this illustrative table the account is ₹10 lakh and the risk is 0.5% per N.

| Stock | Price | N | Shares (₹5,000 ÷ N) | Position value | Share of account |
|---|---|---|---|---|---|
| Calm large cap | ₹1,600 | ₹20 | 250 | ₹4,00,000 | 40%, so the 20% cap binds |
| Volatile midcap | ₹800 | ₹40 | 125 | ₹1,00,000 | 10% |
| Very volatile smallcap | ₹300 | ₹30 | 166 | ₹49,800 | 5% |

### Managing the trade

- **Adding (pyramiding):** the Turtles added a unit every ½N of favourable move, up to 4 units. Each new unit got its own 2N stop, and older stops were raised to match.
- **Portfolio limits** in the original rules: 4 units per market, 6 in closely related markets, 10 in loosely related ones and 12 in one direction.
- For stocks, count a sector as "closely related". Five breakouts in five bank stocks are one bet on banks.
- Check levels after each close. Do not cancel the exit order because the stock "will bounce".

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Entry channel | 55 sessions; range 20–100 | How strong a move must be to enter | Shorter means more trades and more false breakouts |
| Exit channel | 20 sessions; range 10–50 | How much profit is given back | The most sensitive choice for the payoff shape |
| N (volatility) length | 20 sessions; range 14–30 | The daily range used for stop and size | Low sensitivity |
| Initial stop | 2 × N; range 1.5–3 N | Loss on a failed breakout | Tighter means more stop-outs |
| Risk per unit | 1% of the account per N; stocks 0.25%–0.5% | Size and drawdown | Scale down if positions are correlated |
| Pyramid step | ½ N; range ½–1 N | When to add | Adding raises both the payoff and the drawdown |
| Maximum units per position | 4; range 1–4 | Concentration | Many stock traders use 1 |
| Units per related group | 6 | Sector concentration | Define the groups before testing |
| Units in one direction | 12 | Total exposure | Lower it for a stock-only portfolio |
| Position cap | 20% of the account; range 10%–25% | Damage from a gap | Binds for low-volatility stocks |
| Liquidity floor | ₹10 crore or $10 million median turnover | What you can trade | Lower floors add slippage |
| History needed | 75 sessions | Valid channels | No effect on signals once met |

## 5. Variations

- **Turtle System 1 with a filter.** Enter on a 20-day breakout, exit on a 10-day low. The Turtles skipped a System 1 signal if the previous breakout in that market would have been a winner. They took the 55-day breakout as a failsafe so they could not miss a big trend.
- **Donchian's four-week rule.** Buy a new four-week high, sell a new four-week low, always in the market. It is the simplest form of the idea and is usually credited to Donchian.
- **Close-only channels.** Use closing prices instead of highs and lows and act at the next open. Fewer false intraday breaks, slightly later entries.
- **Breakouts to 52-week highs.** Some stock traders use the 250-session high as the entry. It fires rarely and catches stocks at the start of a new leg.
- **ATR channels.** Some traders replace the 20-day low exit with a chandelier stop: the highest close since entry minus 3 ATR. Andreas Clenow uses volatility-based stops of this kind in his futures books.
- **Breakouts from a base.** Chart traders add a requirement that the price has moved sideways in a tight range before the breakout. That is the subject of the base-breakout guides, starting with [CANSLIM breakouts](learn-strat-canslim-breakout.md).

## 6. Worked examples

Prices are adjusted for splits and bonuses. Costs are not included.

### Example 1 — HAL, 2022–2024 (India: the losers and the winners)

The 55/20 rules with a 2N stop produced nine trades in HAL from June 2022 to December 2024.

| Entry date | Entry price | N | Stop | Exit date | Exit price | Return | Result in R |
|---|---|---|---|---|---|---|---|
| 1 Jun 2022 | 936.0 | 33.4 | 869.1 | 20 Jun 2022 | 869.1 | −7.1% | −1.0 |
| 28 Jul 2022 | 986.3 | 23.1 | 940.0 | 28 Sep 2022 | 1,130.0 | +14.6% | +3.1 |
| 16 Nov 2022 | 1,319.2 | 38.6 | 1,242.0 | 16 Dec 2022 | 1,292.6 | −2.0% | −0.3 |
| 3 Mar 2023 | 1,374.0 | 39.8 | 1,294.3 | 23 Mar 2023 | 1,246.5 | −9.3% | −1.6 |
| 28 Apr 2023 | 1,457.0 | 29.4 | 1,398.2 | 3 Aug 2023 | 1,853.5 | +27.2% | +6.7 |
| 23 Aug 2023 | 1,999.4 | 42.0 | 1,915.4 | 22 Sep 2023 | 1,937.6 | −3.1% | −0.7 |
| 10 Nov 2023 | 2,085.0 | 41.1 | 2,002.8 | 20 Mar 2024 | 2,935.1 | +40.8% | +10.3 |
| 1 Apr 2024 | 3,428.0 | 119.9 | 3,188.1 | 18 Jul 2024 | 5,114.6 | +49.2% | +7.0 |
| 12 Dec 2024 | 4,676.6 | 126.9 | 4,422.9 | 19 Dec 2024 | 4,399.5 | −5.9% | −1.1 |

Four trades won and five lost. The losers cost 4.7R in total; the winners made 27.1R. That is the typical shape of a trend system.

Look at the trade of 3 March 2023. The stop was ₹1,294.3. On 23 March the stock opened at ₹1,246.5, about 5% below the previous close and below the stop. The loss was 1.6R, not 1R. Gaps make the stop a hope, not a guarantee, so size for them.

### Example 2 — Nvidia, November 2022 to August 2023 (US)

| Entry date | Entry ($) | N | Stop | Exit date | Exit ($) | Return | Result in R |
|---|---|---|---|---|---|---|---|
| 15 Nov 2022 | 16.72 | 0.78 | 15.16 | 18 Nov 2022 | 15.16 | −9.3% | −1.0 |
| 1 Dec 2022 | 17.00 | 0.79 | 15.42 | 22 Dec 2022 | 15.52 | −8.7% | −0.9 |
| 23 Jan 2023 | 18.79 | 0.77 | 17.24 | 9 Aug 2023 | 42.78 | +127.7% | +15.5 |

```series
title: Nvidia, Oct 2022 – Sep 2023 — two failed breakouts, then the big one
from: 2022-10-01
to: 2023-09-30
line: us:NVDA | Nvidia | log
line: us:NVDA@vol | Volume | pane2 bars
mark: 2022-11-15 | entry 1 (stopped)
mark: 2022-12-01 | entry 2 (stopped)
mark: 2023-01-23 | entry 3
mark: 2023-08-09 | exit at the 20-day low
caption: Prices are adjusted for the 2024 ten-for-one split. The third breakout held for more than six months.
```

The first two breakouts failed within weeks. A trader who gave up after them missed the third, which made 15.5R. The 2023 run included the May results gap, which a 20-day exit simply rode. The exit in August gave back about 11% from the high of $48.09.

### Example 3 — Nifty 50 around the 2024 election (India, index)

Index series have no intraday highs and lows here, so this example uses closes: enter on a close above the highest close of 55 sessions, exit on a close below the lowest close of 20.

| Signal | Date | Nifty close | What happened |
|---|---|---|---|
| Entry | 23 May 2024 | 22,967.7 | New 55-session closing high before the election result |
| Exit | 4 Jun 2024 | 21,884.5 | Result day: the index fell below its 20-session low; −4.7% |
| Entry | 7 Jun 2024 | 23,290.2 | Three sessions later, a new high again |
| Exit | 5 Aug 2024 | 24,055.6 | +3.3% |

One news day produced a full-size loss and a re-entry above the exit price. On an index, which moves less than a stock, channel systems trade often for small gains. Futures make index trading cheap, but the costs of many round trips still add up.

## 7. Common mistakes

- **Stopping after a losing streak.** Example 2 shows why. The big trend is often the next trade.
- **Taking every breakout in one sector.** Five bank breakouts are one bet. Apply the related-markets limit.
- **Sizing by money, not by N.** A ₹5 lakh position in a calm stock and in a volatile one carry very different risk.
- **Chasing a gap.** If the stock opens 8% above the level, the 2N stop may be only slightly below the open. Decide in advance whether to skip opens more than 1N above the level.
- **Using short channels with high costs.** A 20/10 system trades several times as often as 55/20. In India, STT and slippage can absorb the edge.
- **Moving the exit further away.** The 20-session low only rises. Lowering it turns a trend system into a hope system.

- **Ignoring results dates.** A breakout two days before quarterly results is a bet on the results. Either skip it or size it for the gap.
- **Testing on intraday-perfect fills.** A daily backtest that fills exactly at the channel level on a gap day overstates returns. Fill at the open when the open is beyond the level.
- **Judging the system on one stock.** A trend system's result depends on a few trades. Judge it on a portfolio of many stocks over many years.

## 8. What the evidence says

**Published research.** Trend-following futures funds, many using channel breakouts, have long track records. Hurst, Ooi and Pedersen (2017) found trend returns positive in each decade they studied, on diversified futures. Moskowitz, Ooi and Pedersen (2012) documented time-series momentum across 58 futures markets.

On individual stocks, George and Hwang (2004) found that nearness to the 52-week high predicted returns. Evidence on simple channel breakouts in single stocks, after costs, is much thinner. Results there depend strongly on the universe and period.

**Event study: what happens after a 55-day high?** Method: take every stock in the stored universe meeting the liquidity and price floors in §3. Find each first close above the previous 55-session high, with no such close in the prior 20 sessions. Measure the price change over the next 20 and 60 sessions. Compare with all liquid stock-days. Period 2010 to mid-2026.

| Market | Events | Median 60-day change, breakouts | Median 60-day change, all days | Breakouts closing back below the level within 10 sessions | Breakouts up more than 30% after 60 sessions | Breakouts down more than 20% |
|---|---|---|---|---|---|---|
| India | 10,666 | +1.6% | +1.4% | 65% | 9% | 8% |
| US | 55,025 | +1.7% | +2.0% | 65% | 5% | 8% |

Three findings follow.

1. **The breakout alone predicts almost nothing on average.** The median outcome is close to that of any liquid stock on any day. The entry is not the edge.
2. **Most breakouts are retested.** About two in three closed back below the old high within 10 sessions. A stop placed just under the breakout level would be hit often. That is why the Turtles placed it 2N away.
3. **The payoff is skewed.** In both markets, the best 10% of breakouts produced about half of all the positive 60-day returns. The edge of the system has to come from the exit: cutting the bad 8% early and staying with the good 5%–9%.

Caveats: the universe is today's stock list, so delisted failures are missing and results are biased upward. Events overlap in time. There are no costs, and fixed horizons are not the 20-day exit rule. A 20-session channel gave almost the same figures.

## 9. Building and testing it yourself

**Data.** Daily open, high, low, close and volume, adjusted for splits and bonuses, including delisted stocks. Futures need continuous contracts adjusted for rolls.

**Look-ahead traps.**

- The channel must exclude today: the highest high of the previous 55 sessions.
- If the stock opens above the level, fill at the open, not at the level.
- N must be computed from data before the entry day.
- An intraday stop and a breakout on the same day are ambiguous on daily bars. Assume the worse outcome.

**Survivorship.** The event study above shows how much depends on a few big winners. A universe without delisted stocks keeps the winners and drops many of the losers.

**Costs and slippage.** In India a delivery round trip costs roughly 0.3%–0.6% including STT (0.1% each side), stamp duty, exchange charges and slippage. Breakout fills are often worse than average, because you buy when everyone is buying. Model at least 0.2% slippage per side on liquid stocks, and gap fills at the open.

**Parameters to test.**

- Entry channel: 20, 55 and 100 sessions.
- Exit channel: 10, 20 and 50 sessions.
- Stop: 1.5, 2 and 3 N.
- Pyramiding on or off.

Look for a broad region where results are similar. If only one exact pair of channels works and its neighbours do not, the result is luck.

**Over-fitting.** Keep a held-out period. Test on both markets. Count how many variants you tried and report it; see [backtesting honestly](learn-test-backtesting.md).

**What a good test reports.** Trades, win rate, and average win and loss in R. The largest losing streak, the largest drawdown and how long it lasted. Exposure, and the share of profit from the top 10 trades. Run it with and without the three biggest winners.

```
each day t, after the close:
    hi55 = max(high[t-55 .. t-1]); lo20 = min(low[t-20 .. t-1]); N = atr20[t-1]
    if flat: place buy stop at hi55 for day t+1
        filled at max(hi55, open[t+1]); stop = fill - 2 * N
        shares = 0.005 * equity / N, capped at 20% of equity
    if long: sell stop at max(stop, lo20) for day t+1
        filled at min(level, open[t+1]) if low[t+1] <= level
```

## 10. Checklist

- [ ] The stock meets the liquidity and price floors, and I am not already holding its sector to the limit.
- [ ] The entry level is the highest high of the previous 55 sessions, and the buy stop is placed there.
- [ ] N is the 20-day average true range, and the initial stop is 2N below the fill.
- [ ] The share count comes from N and my risk per unit, and the position is under the cap.
- [ ] I know of any results date or event in the next weeks, and I have sized for a gap.
- [ ] The exit is a sell stop at the higher of the 2N stop and the 20-session low, raised daily.
- [ ] No profit target. I will take the next breakout even after several losers.

## Further reading

- Curtis Faith, *Way of the Turtle* (McGraw-Hill, 2007).
- Michael Covel, *The Complete TurtleTrader* (HarperCollins, 2007).
- Michael Covel, *Trend Following* (FT Press; first edition 2004).
- Andreas Clenow, *Following the Trend* (Wiley, 2013).
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* (2004).
- Tobias Moskowitz, Yao Hua Ooi and Lasse Pedersen, "Time Series Momentum", *Journal of Financial Economics* (2012).
- Brian Hurst, Yao Hua Ooi and Lasse Pedersen, "A Century of Evidence on Trend-Following Investing", *Journal of Portfolio Management* (2017).
- Related guides: [moving-average trend following](learn-strat-ma-trend.md), [stops and exits](learn-risk-stops-exits.md), [expectancy](learn-risk-expectancy.md).
