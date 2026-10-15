# Moving-average trend following — own it while it is above the line

**In short**
- Buy when the price is above a rising long average, sell when it closes back below a shorter one. You never predict a top or a bottom.
- On an index, the classic version is Faber's rule: hold while the month-end close is above the 10-month average, hold cash otherwise.
- The rule does not pick winners. It cuts losers early and lets a few big trends pay for many small losses.
- Its cost is the whipsaw: in a sideways market it buys high and sells low, again and again.
- Use it on liquid stocks and indices that trend, with fixed rules, small risk per trade and costs counted.

## 1. The idea

In May 2023 Trent, the Tata group retailer, was trading above its 50-day and 200-day averages. On 16 May the 50-day rose above the 200-day, which was itself rising. A simple rule said buy. Apart from one short gap in October 2023, the same rule kept the stock until October 2024. By then the price had risen from about ₹1,500 to more than ₹7,000.

```series
title: Trent, 2023–2024 — above a rising average for most of two years
from: 2023-01-01
to: 2025-03-31
line: india:TRENT.NS | Trent | log
line: india:TRENT.NS@sma50 | 50-day average
line: india:TRENT.NS@sma200 | 200-day average
mark: 2023-05-16 | trend filter turns on
mark: 2023-10-27 | back in after a short exit
mark: 2024-10-28 | second close below the 50-day
caption: The rule bought in May 2023, stepped out for four sessions in October 2023 and sold in late October 2024.
```

That is the whole strategy. A **moving-average trend rule** holds a stock or index while its price is above an average of recent prices. It exits when the price falls back below. The average is a slow, smoothed version of the price. When the price stays above it, buyers have been paying more over time.

Why can it work? Prices tend to move in persistent runs, not just random steps. Research calls this **time-series momentum**: an asset that has risen over the past months tends to keep rising a little longer. Big investors build positions over weeks and months. Good news is absorbed slowly, as analysts revise forecasts one quarter at a time.

On the other side, early in a trend, it is the holder who sells into the first rise, glad to break even. Late in a trend it is the buyer who arrives after the story is famous. In a falling market it is the investor who buys the dip and keeps buying. The trend follower is not smarter than them. It simply refuses to argue with the price.

The edge is in the exits, not the entries. The rule loses small and often when the price chops around the line. It wins big and rarely when a trend runs for a year. [The expectancy guide](learn-risk-expectancy.md) explains why that payoff can still be positive with a low win rate.

## 2. When it works and when it doesn't

It works in markets that make long, one-way moves. Examples are the Indian midcap rally after the 2020 crash and the defence and railway stocks of 2023–24. The US large-cap rally of 2023 is another. It also works in long bear markets on an index. The rule steps aside early and avoids most of the fall, as in 2008.

It fails in sideways markets. The price crosses the average back and forth and each cross costs a small loss. The Nifty in 2015–16 is an example (§6). The Nifty in late 2018 is another.

It also struggles with sharp V-shaped reversals. In March 2020 the rule sold after the fall and bought back after the rebound.

**Stock types.** It suits stocks with a story that unfolds over quarters: growing earnings, a sector in favour, broad institutional buying. It suits slow, defensive large caps less well. They often drift sideways for years. It needs liquid stocks, because a trend exit can mean selling on a down day.

**India notes.** Indian stocks trend strongly but also gap. Results, block deals and policy news can move a stock 10% overnight. A daily-close rule cannot avoid a gap, so size for it.

Stocks in a narrow price band (2% or 5% circuit limits) can lock at the limit for days. Then the exit may not fill at all. Holding periods of months bring Indian capital-gains tax into play (§9).

**US notes.** US large caps are deep and cheap to trade. The main risk is crowding: when many funds use the same 200-day line, moves through it can be fast. Index versions of the rule are widely published, so do not expect a hidden edge there.

## 3. The rules

Two versions follow. The **index version** is Faber's monthly rule. The **stock version** adds a trend filter, an entry trigger and a trailing exit. Each rule is a condition you can test on daily data.

### Universe and filters

- **Index version:** a broad index you can buy through an ETF or futures, such as the Nifty 50, Nifty 500 or S&P 500.
- **Stock version:** stocks with a median daily turnover of at least ₹10 crore in India or $10 million in the US over the last 50 sessions.
- Price at least ₹50 or $5, so the tick size and circuit bands do not distort fills.
- At least 250 sessions of history, so the 200-day average exists and has a slope.
- Optional: only when the market itself is in an uptrend (see [regime filters](learn-strat-regime-filters.md)).

### Setup

**Index version (Faber):** on the last trading day of the month, the index closes above its 10-month simple average of month-end closes.

**Stock version:** all four of these are true at today's close.

1. The close is above the 50-day simple average.
2. The 50-day average is above the 200-day average.
3. The close is above the 200-day average.
4. The 200-day average is higher than it was 20 sessions ago.

### Entry

- **Index:** buy at the next session's open after a month-end close above the line. Many traders buy at the month-end close itself, using a market-on-close order.
- **Stock:** buy at the next session's open on the first day all four setup conditions are true after at least one was false. This also re-enters after an exit, once the close is back above the 50-day.
- Use a limit order a little above the expected open (for example 0.5%) in thin stocks, so a gap does not fill you far away.

### Initial stop

- **Index:** none intraday. The month-end check is the stop. Size the position so that a 20% fall within a month is survivable.
- **Stock:** the entry price minus 3 × ATR(20), where ATR(20) is the 20-day average true range on the setup day. Exit at the next open after a close below it.

### Exits

- **Trailing exit (stock):** two consecutive closes below the 50-day average. Sell at the next open.
- **Slow alternative:** the 50-day crosses below the 200-day (the "death cross"). This gives back much more but whipsaws less.
- **Index:** a month-end close below the 10-month average. Sell at the next open and hold cash or a liquid fund.
- **No profit target.** A target caps the rare big trend that pays for all the losses.
- **No time stop** in the classic version. Some traders add one: exit if the trade is not 1R in profit after 60 sessions.

### Position size

- Risk a fixed share of the account per trade: 0.5% to 1%. The share count is that amount divided by (entry − stop). See [position sizing](learn-risk-sizing.md).
- Cap any one position at 10% to 20% of the account, because a gap can jump past the stop.
- **Index version:** all in or all out, or scale it. Some traders hold half when the index is between the 10-month line and a band 2% above it.

### Managing the trade

- Check the rules once a day after the close (stock) or once a month (index). Do not act on intraday crosses.
- Do not move the initial stop down. Raise nothing by hand: the 50-day exit does the trailing.
- Before results or big events, decide in advance whether you hold through them. The rule itself does not know about earnings dates.
- Keep a log of every signal taken and skipped. A trend system's result depends on taking the next signal after five losers.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Index average length | 10 months (about 200 days); range 8–12 months | How soon the index rule reacts | Shorter means earlier exits and more whipsaws |
| Index check frequency | Month-end; range weekly to monthly | How often a cross can trigger | Monthly checks cut noise a lot |
| Fast average (stock) | 50 days; range 20–100 | The trailing exit and re-entry line | The most sensitive choice: 20 trades often, 100 gives back a lot |
| Slow average (stock) | 200 days; range 150–250 | The trend filter | Fairly insensitive between 150 and 250 |
| Slope lookback | 20 sessions; range 10–60 | Whether the 200-day counts as rising | Short lookbacks flip often near a top |
| Exit confirmation | 2 closes; range 1–3 | Whipsaws on the exit | One close: more exits; three: later exits |
| Initial stop | 3 × ATR(20); range 2–4 ATR | Loss on a failed entry | Wider stops mean fewer shares per trade |
| ATR length | 20 sessions; range 14–20 | Volatility estimate for the stop | Low sensitivity |
| Liquidity floor | ₹10 crore or $10 million median turnover; range 5–50 | What you can trade | Lower floors add gap and slippage risk |
| Price floor | ₹50 or $5 | Excludes penny stocks | Low sensitivity |
| Entry limit buffer | 0.5% above the open; range 0–1% | Fill risk on a gap | Too tight and you miss strong opens |
| Risk per trade | 0.5%–1% of the account | Drawdown depth | Halve it in a losing streak if you must, but decide that rule in advance |
| Position cap | 10%–20% of the account | Damage from a gap | Binds for low-volatility stocks |
| Optional time stop | 60 sessions without 1R profit | Capital stuck in dead trades | Can cut a slow starter that later trends |

## 5. Variations

- **Golden cross / death cross.** Buy when the 50-day crosses above the 200-day; sell on the reverse cross. It is slow and late at both ends, but it trades rarely. It is widely watched, so it is a common baseline.
- **Faber's 10-month rule.** Mebane Faber's 2007 paper applied it to US stocks, foreign stocks, bonds, commodities and property. Over the decades he tested, it gave returns similar to or better than buy-and-hold, with much smaller drawdowns. The test was on monthly data with no leverage.
- **Price against a single average with a band.** Brock, Lakonishok and LeBaron (1992) tested the Dow against its 50-, 150- and 200-day averages. Some variants required a 1% move through the line before acting. The band reduces whipsaws.
- **Exponential averages.** An EMA reacts faster to recent prices. Many traders use the 21-day EMA as a short trail, and the 10-week EMA on weekly charts.
- **Triple averages.** Richard Donchian, an early trend follower, used combinations of moving averages on commodities. Many modern futures funds blend several lengths (for example 20, 60 and 250 days) to avoid betting on one.
- **Volatility-scaled size.** Instead of a fixed stop, Andreas Clenow and the futures literature size every position so that each has the same expected daily swing.
- **Weekly stage version.** Stan Weinstein's 30-week line is the same idea on weekly bars, with a base breakout as the trigger. See [stage analysis](learn-strat-stage-analysis.md).

## 6. Worked examples

Prices are adjusted for splits and bonuses. Costs are not included in the returns below.

### Example 1 — Trent, 2023–2024 (India, success)

The chart in §1 shows it. Here is the second trade, step by step.

| Step | Date | Detail |
|---|---|---|
| Setup | 27 Oct 2023 | Close 2,122.1; 50-day 2,056.9; 200-day 1,615.1 and rising; ATR(20) 54.3 |
| Entry | 30 Oct 2023 | Bought at the open, 2,143.2 |
| Initial stop | — | 2,143.2 − 3 × 54.3 = 1,980.4, a risk of 162.8 per share |
| Highest close while held | 11 Oct 2024 | 8,235.0 |
| Exit signal | 28 Oct 2024 | Second close below the 50-day: 7,307.9 against 7,416.3 |
| Exit | 29 Oct 2024 | Sold at the open, 7,313.3 |

The trade gained 241% in a year. That is about 32R: the gain was 32 times the risk taken at entry. The rule gave back about 11% from the peak close, the price of waiting for proof that the trend had turned.

The first trade, from May to October 2023, made 34%. The rule then sold and bought back three sessions later, about 7% higher. Small costs like that are normal. The two trades that followed in December 2024 and January 2025 lost 2% and 5%.

### Example 2 — BEL, December 2021 to March 2022 (India, failure)

Bharat Electronics was in a long-term uptrend, but for four months it moved sideways around its 50-day average.

```series
title: BEL, Oct 2021 – Jun 2022 — a sideways stretch around the 50-day
from: 2021-10-01
to: 2022-06-30
line: india:BEL.NS | BEL
line: india:BEL.NS@sma50 | 50-day average
line: india:BEL.NS@sma200 | 200-day average
band: 2021-12-06 2022-03-29 | six entries, six exits
caption: The trend filter stayed on, but the close crossed the 50-day again and again.
```

| Entry (open) | Price | Exit (open) | Price | Return |
|---|---|---|---|---|
| 7 Dec 2021 | 69.8 | 20 Dec 2021 | 67.0 | −4.1% |
| 24 Dec 2021 | 69.4 | 28 Dec 2021 | 69.6 | +0.3% |
| 30 Dec 2021 | 69.9 | 20 Jan 2022 | 69.7 | −0.4% |
| 21 Jan 2022 | 70.5 | 25 Jan 2022 | 65.4 | −7.1% |
| 1 Feb 2022 | 70.6 | 8 Feb 2022 | 67.4 | −4.5% |
| 2 Mar 2022 | 69.2 | 29 Mar 2022 | 68.7 | −0.7% |

Six trades compounded to about −16% before costs, while the stock ended the period roughly where it started. Each loss was within the rules. Two lessons follow. First, a 50-day exit on a volatile stock trades too often; a wider exit or a 2% band would have kept the position. Second, a trade from July 2022 made 25%, so the trader who quit in March 2022 missed the payoff.

### Example 3 — the Nifty 50 and Faber's rule, 2020 (India, index)

```series
title: Nifty 50 and its 200-day average (≈ 10 months), 2019–2021
from: 2019-01-01
to: 2021-06-30
tf: M
line: india:NIFTY50 | Nifty 50
line: india:NIFTY50@sma200 | 200-day average (≈ 10-month line)
mark: 2020-02-28 | month-end below: sell
mark: 2020-07-31 | month-end above: buy
caption: The chart shows the 200-day; Faber's 10-month line of month-end closes is close to it.
```

- **Sell:** the February 2020 month-end close was 11,201.8, below the 10-month average of 11,659.3.
- **Low:** the index bottomed at 7,610.2 on 23 March 2020, 38% below its January peak.
- **Buy:** the July 2020 month-end close was 11,073.5, above the average of 10,867.9.

The rule sold and bought back at almost the same level. It skipped the whole crash and the whole rebound. That is the rule working as designed: it avoided the risk, not the time.

### Example 4 — the Nifty 50, 2015–2016 (India, failure)

| Month-end | Nifty close | 10-month average | Signal |
|---|---|---|---|
| Apr 2015 | 8,181.5 | 8,316.0 | Sell |
| May 2015 | 8,433.7 | 8,387.2 | Buy |
| Jun 2015 | 8,368.5 | 8,428.6 | Sell |
| Jul 2015 | 8,532.8 | 8,485.4 | Buy |
| Aug 2015 | 7,971.3 | 8,450.3 | Sell |
| May 2016 | 8,160.1 | 7,816.6 | Buy |

Every buy was at a higher price than the sell before it. Over the 13 months the rule lost about 7% before costs. Simply holding lost less than 1%. A flat, choppy market is the trend follower's worst case.

## 7. Common mistakes

- **Changing the average after a loss.** Switching from 50 to 40 days because "the 50 was too slow last time" fits the last trade, not the next.
- **Skipping signals after a losing streak.** The big trend usually comes after several small losses. Skipping one is how a trend system ends up negative.
- **Adding a profit target.** It cuts off the few trades that make the year.
- **Acting on intraday crosses.** A price that dips through the 50-day at 11 a.m. and closes above it is not an exit.
- **Using it on illiquid stocks.** The rule will tell you to sell on a weak day. In a thin stock that is when the bids disappear.
- **Ignoring gaps.** A close-based stop is not a guaranteed price. Size so that a 10%–15% gap below the stop does not hurt badly.
- **Testing on today's index members.** Trend rules look much better on stocks that survived (§9).

## 8. What the evidence says

**Published research.** Moving-average rules are among the most studied trading rules.

- Brock, Lakonishok and LeBaron (1992) found that simple moving-average rules on the Dow from 1897 to 1986 separated higher-return days from lower-return days.
- Sullivan, Timmermann and White (1999) showed that, after allowing for the many rules tested, the best rule did not keep working after 1986.
- Faber (2007, updated 2013) reported similar returns and much smaller drawdowns for his 10-month rule, across several asset classes.
- Moskowitz, Ooi and Pedersen (2012) documented time-series momentum across 58 futures markets. Hurst, Ooi and Pedersen (2017) extended trend evidence back over a century.
- Zakamulin (2017) argued that much of the benefit on stock indices comes from avoiding deep bear markets, and that the gain over buy-and-hold varies a lot by period.

**An event study on stored index data.** Method: at each month-end, compare the close with its 10-month average of month-end closes. Then measure the next month's price change. The S&P 500 series is price only, without dividends.

| Index, period | Months above / below | Next-month mean, above | Next-month mean, below | Monthly st. dev., above | Monthly st. dev., below | Share of next months below −10%, above / below |
|---|---|---|---|---|---|---|
| S&P 500, 1928–2026 | 800 / 376 | +0.84% | +0.22% | 4.1% | 7.3% | 1.1% / 5.9% |
| S&P 500, 1990–2026 | 334 / 98 | +0.90% | +0.64% | 3.4% | 6.2% | 0.3% / 4.1% |
| Sensex, 1998–2026 | 237 / 105 | +1.37% | +0.33% | 5.7% | 7.4% | 3.0% / 6.7% |
| Nifty 50, 2008–2026 | 154 / 66 | +0.98% | +0.86% | 4.5% | 7.5% | 0.6% / 6.1% |

The clearest result is about risk, not return. Months that started below the line were far more volatile in every index. They contained most of the crashes: of the ten worst months, the signal was already "below" for six or seven in each index. Returns after "below" months were lower on average in three indices, and about equal on the Nifty.

The cost was also clear. On the S&P 500 the signal switched 146 times in 98 years. Of those switches, 40% reversed within two months. On the Nifty the rule switched 36 times in 18 years and 44% reversed within two months. Each reversal is a whipsaw like the one in Example 4.

Caveats: months overlap with the same crashes in each sample, so the counts are small. The Nifty sample has only a few bear markets. No costs or cash returns are included. This is evidence about conditional risk, not a strategy backtest.

**What is unknown.** Whether a stock-level 50/200 rule beats buy-and-hold on Indian stocks depends heavily on the universe, the costs and survivorship. No study settles it. Test it yourself (§9).

## 9. Building and testing it yourself

**Data.** Daily open, high, low, close and volume, adjusted for splits and bonuses. For index rules, use a total-return series when you can; a price-only index understates holding and overstates cash. Store delisted stocks too.

**Look-ahead traps.**

- Signals use today's close; fills use the next open. Never fill at the close that created the signal unless you trade a market-on-close order.
- A month-end rule must use only month-end closes known at that time.
- The 200-day average needs 200 sessions before the first signal; do not start the test earlier.

**Survivorship.** A universe built from today's index members leaves out the stocks that fell out of it. Those are exactly the failed trends. Use point-in-time index membership, or at least include delisted stocks.

**Costs in India (approximate; check current rates).**

| Item | Approximate rate | Applies to |
|---|---|---|
| STT | 0.1% | Buy and sell, delivery trades |
| Stamp duty | 0.015% | Buy |
| Exchange charges | about 0.003% | Both sides |
| GST | 18% | On brokerage and exchange charges |
| Brokerage | ₹0–20 per order at discount brokers | Both sides |
| DP charge | about ₹15 per stock sold | Sell |
| Slippage | 0.1%–0.3% per side for liquid stocks | Both sides; more on gaps |

A round trip costs roughly 0.3% to 0.6% with slippage. Holding periods under 12 months are taxed as short-term capital gains (20% at the time of writing). That changes the after-tax result of a rule that trades often.

**Parameters to test.** Vary one at a time, using the ranges in §4:

- the fast average: 20, 50 and 100 days;
- the exit confirmation: 1, 2 and 3 closes;
- the stop: 2, 3 and 4 ATR.

 Look for a broad plateau where nearby values give similar results. Distrust a single sharp peak.

**Avoiding over-fitting.** Fix the rules before looking at the test period. Keep the last few years out of the design and test on them once. Test the same rules on the other market (India and the US) and on different periods.

**What a good test reports.** The number of trades, win rate, average win and loss in R, expectancy, the largest drawdown and its length, time in the market, and turnover. Report results with costs, and show the share of profit from the top 5% of trades.

```
for each stock, each day t (after the close):
    setup = close > sma50 and sma50 > sma200 and close > sma200
            and sma200 > sma200[t-20]
    if not in_position and setup and not setup[t-1]:
        buy at open[t+1]; stop = open[t+1] - 3 * atr20[t]
    if in_position:
        if close < stop: sell at open[t+1]
        elif close < sma50 and close[t-1] < sma50[t-1]: sell at open[t+1]
```

## 10. Checklist

- [ ] The stock or index meets the liquidity and price floors.
- [ ] The close is above the 50-day and the 200-day; the 50-day is above the 200-day.
- [ ] The 200-day is higher than 20 sessions ago.
- [ ] This is the first day all conditions are true (or a re-entry after an exit).
- [ ] The initial stop is set at entry minus 3 × ATR(20), and the share count comes from it.
- [ ] The position is within the size cap, and a gap past the stop is survivable.
- [ ] I know when the next results or major event is, and whether I will hold through it.
- [ ] I will check the exit only on closes, and sell at the next open after two closes below the 50-day.
- [ ] I have no profit target, and I will take the next signal even after a losing streak.

## Further reading

- Mebane T. Faber, "A Quantitative Approach to Tactical Asset Allocation", *Journal of Wealth Management* (2007; updated 2013).
- William Brock, Josef Lakonishok and Blake LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns", *Journal of Finance* (1992).
- Ryan Sullivan, Allan Timmermann and Halbert White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap", *Journal of Finance* (1999).
- Tobias Moskowitz, Yao Hua Ooi and Lasse Pedersen, "Time Series Momentum", *Journal of Financial Economics* (2012).
- Brian Hurst, Yao Hua Ooi and Lasse Pedersen, "A Century of Evidence on Trend-Following Investing", *Journal of Portfolio Management* (2017).
- Valeriy Zakamulin, *Market Timing with Moving Averages* (Palgrave Macmillan, 2017).
- Andreas Clenow, *Following the Trend* (Wiley, 2013).
- Related guides: [stages in a stock](learn-price-stages.md), [the index trend](learn-health-trend.md), [stops and exits](learn-risk-stops-exits.md), [backtesting honestly](learn-test-backtesting.md).
