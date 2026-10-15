# Regime filters — when to trade at all

**In short**
- A regime filter is a rule on top of a strategy that says whether to take its signals: on, off, or at reduced size.
- The common ones read the market's trend (the index against its 200-day average), its breadth (how many stocks are rising) or its volatility (VIX and India VIX).
- On index data the clearest effect is on risk: below the 200-day line, the index has been about twice as volatile and most of its worst days happened there.
- The cost is whipsaw. A raw 200-day rule on the Nifty switched about 8 times a year; a 2% band cut that to about 2.
- Whether a filter helps your strategy is an empirical question. Test it on your own signals, through more than one bear market.

## 1. The idea

On 26 February 2020 the Nifty 50 closed at 11,678.5. That was just below its 200-day average of 11,683.8. A trader with a simple regime filter stopped taking new long trades that day. Over the next four weeks the index fell to 7,610.2. The filter turned back on only on 17 July 2020, with the Nifty at 10,901.7.

```series
title: Nifty 50 and its 200-day average, 2019–2020
from: 2019-07-01
to: 2020-12-31
line: india:NIFTY50 | Nifty 50
line: india:NIFTY50@sma200 | 200-day average
band: 2020-02-26 2020-07-17 | filter off
mark: 2020-03-23 | low, 7,610.2
caption: The filter was off for the whole crash and the first half of the rebound.
```

A **regime** is the market's broad condition: trending up, trending down, or moving sideways; calm or volatile. A **regime filter** is a rule that reads it and switches a strategy on or off. It does not choose stocks. It decides whether the stock strategy should be trading at all, and how much.

Why can it work? Most stocks move with the market. When the index is falling, even good breakouts tend to fail, and losses arrive together. A filter tries to keep the strategy out of those periods. It also keeps the trader out when volatility is high, which is when losses are largest and gaps most common.

Who is on the other side? When the filter turns off, the buyers are the dip buyers and long-term investors who hold through declines. Sometimes they are right and the market rebounds fast, as in 2020. The filter then costs the rebound. When the decline is long, as in 2008 or 2022, the filter saves most of it.

## 2. When it works and when it doesn't

A filter helps most in long, deep bear markets. Examples are the 2000–02 bear market and 2008 in both countries. Another is 2022 in the US. The index stays below its average for months and the filter is off for the whole decline.

It hurts in two cases. First, in sideways markets the index crosses its average many times. Each cross turns the strategy off and on, often near the worst moments. Second, in sharp V-shaped falls the filter turns off near the bottom and back on well above it. March 2020 is the clearest example.

**Which strategies need one.** Long-only breakout and trend strategies benefit most, because their losers cluster in falling markets. Mean-reversion strategies often do the opposite: they find more and better setups when the market is weak. A short-side strategy wants the filter reversed. Do not copy one filter onto every strategy.

**India notes.** The Nifty 50 is dominated by a few large banks, IT and energy companies. A midcap or smallcap strategy should read a broader index such as the Nifty 500 or a midcap index, or breadth. In 2018 the Nifty made a record while midcaps were in a bear market (Example 4). India VIX reacts strongly to scheduled events such as elections and the Union Budget, so a VIX filter turns off around them by design.

**US notes.** The S&P 500 is also concentrated, in its largest technology companies. The Russell 2000 or an equal-weighted index gives a broader read for small-cap strategies. VIX data is deep and widely used, and its spikes are usually short.

## 3. The rules

A regime filter has its own rules: what it reads, when it turns off and on, and what "off" means. Each rule below is a testable condition. Pick one filter, or combine two, and fix it before the test.

### Universe and filters (what to read)

- **Large-cap strategy:** Nifty 50 or S&P 500.
- **Mid- and small-cap strategy:** Nifty 500 or a midcap index; Russell 2000 or the S&P 500 equal-weight index.
- **Breadth:** the share of stocks in your own universe above their 50-day average.
- **Volatility:** India VIX or VIX, both measures of the options market's expected volatility over the next 30 days.

### Setup (the filter conditions)

1. **Trend filter:** the index close is above its 200-day simple average.
2. **Trend filter with slope:** as rule 1, and the 200-day average is higher than 20 sessions ago.
3. **Trend filter with a band:** turn off only when the close is more than 2% below the 200-day average. Turn back on only when it is more than 2% above.
4. **Breadth filter:** at least 40% of the stocks in your universe are above their 50-day average.
5. **Volatility filter:** VIX below 30, or India VIX below 25.
6. **Combined:** on when at least two of the trend, breadth and volatility filters are on.

### Entry (what "on" allows)

- New trades from the strategy are taken at normal size.
- The filter is checked once a day after the close. A change applies from the next session.

### What "off" means

Decide one of these before testing:

- **No new trades;** existing positions keep their own stops and exits. This is the most common version.
- **No new trades, and tighten stops** on existing positions, for example to the 10-day low.
- **Close everything** at the next open. Only sensible for an index strategy, where the filter is the strategy.

### Exits

- The filter does not exit stock trades by itself, unless you choose "close everything".
- It turns back on only when its own "on" condition is met. With a band, that is 2% above the average, not just above it.

### Position size (an exposure ladder)

Instead of on and off, many traders scale size with the number of filters that are on.

| Filters on (of trend, breadth, volatility) | Risk per new trade | Maximum total exposure |
|---|---|---|
| 3 | 1% | 100% |
| 2 | 0.5% | 60% |
| 1 | 0.25% | 30% |
| 0 | No new trades | Existing positions only |

The numbers are an illustration. Test your own ladder.

### Managing the filter

- Write the filter down and never override it during a test.
- In live trading, log every day it is off and what the strategy would have done. That is how you learn its real cost.
- Do not add a new filter after one bad month. Every filter fits the last loss.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Index | Nifty 50, Nifty 500, S&P 500, Russell 2000 | What "the market" means | Match it to the strategy's stocks |
| Average length | 200 days; range 100–250 (or 10 months) | Trend speed | Shorter averages switch much more often |
| Slope lookback | 20 sessions; range 10–60 | Whether the average is rising | Adds lag; removes some false "on" signals |
| Band | 2%; range 0–3% | Whipsaws | The biggest effect on switches (§8) |
| Confirmation | 1 close; range 1–5 | Whipsaws | Similar effect to a band, with more lag |
| Breadth threshold | 40% above the 50-day; range 30%–50% | Participation | Breadth is noisy; smooth it over 5–10 days |
| VIX threshold | 30; range 25–35 | Volatility | Spikes are short; often off for days only |
| India VIX threshold | 25; range 20–30 | Volatility | Event-driven spikes (elections, Budget) |
| Check frequency | Daily; or weekly, monthly | Reaction speed | Monthly checks cut switches further |
| Ladder steps | 4 levels | Size changes | More levels mean more rules to test |

## 5. Variations

- **The 200-day rule.** Long-only investors and many trend followers treat the index's 200-day average as the line between bull and bear. It is the simplest and most watched filter.
- **Faber's 10-month rule.** A monthly version: index above its 10-month average. It switches less often. See [moving-average trend following](learn-strat-ma-trend.md).
- **O'Neil's market direction (the "M" in CANSLIM).** William O'Neil judged the market by distribution days (heavy-volume down days) and follow-through days. See [distribution days](learn-health-distribution.md).
- **Zweig's breadth thrust.** Martin Zweig treated a fast rise in the share of advancing stocks, within about ten days, as the start of a new uptrend. See [breadth](learn-health-breadth.md).
- **Volatility targeting.** Moreira and Muir (2017) scaled exposure down when recent volatility was high and found better risk-adjusted returns. This is a continuous version of the volatility filter.
- **Elder's triple screen.** Alexander Elder used a longer timeframe's trend as a filter for trades on a shorter one. The weekly trend decides the direction; the daily chart gives the entry.
- **Stage of the index.** Stan Weinstein read the index's stage from its 30-week line before buying any stock. See [stage analysis](learn-strat-stage-analysis.md).

## 6. Worked examples

### Example 1 — the Nifty 50 in 2020 (India: success with a cost)

The chart in §1 shows it.

| Event | Date | Nifty 50 | Note |
|---|---|---|---|
| Filter off | 26 Feb 2020 | 11,678.5 | First close below the 200-day |
| Low | 23 Mar 2020 | 7,610.2 | 35% below the filter-off level |
| Filter on | 17 Jul 2020 | 10,901.7 | First close above the 200-day |

The filter kept a long strategy out of a 38% fall from the January peak. The cost: it turned back on 7% below where it turned off, after the index had already risen more than 40% from its low. A strategy that buys rebounds would have missed its best setups.

### Example 2 — the S&P 500 in 2022 (US: success after a messy start)

```series
title: S&P 500 and its 200-day average, 2022
from: 2021-10-01
to: 2023-03-31
line: us:SPX | S&P 500
line: us:SPX@sma200 | 200-day average
band: 2022-04-08 2022-11-30 | below the 200-day
mark: 2022-10-12 | low
caption: Eleven crosses between 21 January and 8 April 2022, then nearly eight months below the line.
```

| Event | Date | S&P 500 |
|---|---|---|
| Record close | 3 Jan 2022 | 4,796.6 |
| First close below the 200-day | 21 Jan 2022 | 4,397.9 |
| Crosses back and forth | 31 Jan – 7 Apr 2022 | Nine more crosses |
| Last close below before the long stretch | 8 Apr 2022 | 4,488.3 |
| Low | 12 Oct 2022 | 3,577.0 |
| Back above | 30 Nov 2022 | 4,080.1 |

A raw filter flipped eleven times in under three months. A 2% band flipped five times in the same stretch and then stayed off from 12 April 2022 to 26 January 2023. Either way, the filter kept the strategy out of the fall from about 4,490 to 3,577, about 20%.

### Example 3 — the Nifty 50, September 2018 to March 2019 (India: whipsaw failure)

```series
title: Nifty 50 and its 200-day average, 2018–2019
from: 2018-06-01
to: 2019-06-30
line: india:NIFTY50 | Nifty 50
line: india:NIFTY50@sma200 | 200-day average
band: 2018-10-04 2019-03-01 | 18 switches of the raw filter
caption: The index wound around a nearly flat 200-day average for five months.
```

From October 2018 to March 2019 the raw filter switched 18 times. Many "on" signals lasted only a day or two. A trader who followed it took new positions on each "on" day and then stopped on the next "off" day.

| Filter | Switches, Oct 2018 – Mar 2019 | Last change |
|---|---|---|
| Raw 200-day | 18 | On, 1 Mar 2019 at 10,863.5 |
| 2% band | 4 | On, 11 Mar 2019 at 11,168.0 |

The band filter turned off on 5 October 2018 at 10,316.5 and stayed off until February. It cost about 3% of upside at the end, compared with the raw filter, and removed 14 switches.

### Example 4 — 2018: the Nifty filter was on while midcaps fell (India: wrong index)

```series
title: 2018 — Nifty 50 and the midcap index, % below their highs
from: 2017-10-01
to: 2019-06-30
line: india:NIFTY50@dd | Nifty 50, % below high | zero
line: india:MIDCAP@dd | Midcap index, % below high
mark: 2018-08-28 | Nifty record
caption: The Nifty made a record in August 2018 while the midcap index was well below its January high.
```

The midcap index peaked at 5,702.4 on 8 January 2018 and fell 23% by 8 October 2018. It closed below its own 200-day average on 18 May 2018 and stayed below for most of the next year. Meanwhile the Nifty 50 was above its 200-day from April to early October, and set a record on 28 August. A midcap breakout strategy filtered on the Nifty would have kept trading through a midcap bear market. The filter must read the market the strategy trades.

## 7. Common mistakes

- **Choosing the filter after seeing the losses.** A filter fitted to the last drawdown removes that drawdown in the backtest and nothing else.
- **Reading the wrong index.** Example 4.
- **No band or confirmation.** A raw 200-day rule switches several times a year in a sideways market.
- **Stacking filters until no trades are left.** Every filter removes good trades too. Three filters can turn a strategy off for a third of the time.
- **Testing only since 2010.** The Indian and US stock data since then contain mostly short, V-shaped declines. The filter's main case, a long bear market, is barely in the sample (§8).
- **Overriding it.** "This time is different" is how a filter becomes a mood.

## 8. What the evidence says

**Published research.** Faber (2007) and Zakamulin (2017) found that index trend filters mostly reduce volatility and drawdowns, with returns similar to holding. Moreira and Muir (2017) found that scaling exposure down when volatility is high improved risk-adjusted returns across many factors. Brock, Lakonishok and LeBaron (1992) reported that returns after buy signals of moving-average rules were less volatile than after sell signals. Daniel and Moskowitz (2016) showed that stock momentum strategies crash after bear markets, when the market rebounds sharply, which argues for care in exactly those regimes.

**Event study 1: the index above and below its 200-day.** Method: each day, compare the index close with its 200-day average. Measure the next day's change. Volatility is annualised.

| Index, period | Share of days above | Volatility above | Volatility below | Of the 20 worst days, below | Of the 20 best days, below |
|---|---|---|---|---|---|
| S&P 500, 1929–2026 | 68% | 14.7% | 25.7% | 13 | 15 |
| S&P 500, 1991–2026 | 76% | 13.2% | 28.4% | 17 | 19 |
| Sensex, 1998–2026 | 69% | 18.8% | 28.6% | 16 | 13 |
| Nifty 50, 2008–2026 | 71% | 15.3% | 27.3% | 17 | 17 |

Below the line, daily volatility was roughly double. Most of the worst days happened there, but so did most of the best days: big rebounds come in falling markets. The average daily return was not consistently lower below the line. So a trend filter is mainly a risk tool.

**Event study 2: how often it switches.** The same daily rule, with and without a band.

| Index, period | No band | ±1% band | ±2% band | ±3% band |
|---|---|---|---|---|
| Nifty 50, mid-2008 to 2026: switches per year | 7.9 | 3.4 | 2.1 | 1.6 |
| S&P 500, 1990–2026: switches per year | 6.7 | 2.9 | 1.8 | 1.0 |

The share of time "on" barely changed with the band: 69%–71% for the Nifty. For the S&P 500 it was 75%–76%. A band removes most whipsaws at almost no cost in time invested.

**Event study 3: stock breakouts by regime.** Method: liquid stocks, using the floors of the breakout guide, from 2010 to mid-2026. An event is a stock's first close above its previous 55-session high. The outcome is the price change over the next 60 sessions. Events are split by whether the main index was above its 200-day average that day.

| Market | Index above its 200-day: events | Median 60-day change | Index below: events | Median 60-day change |
|---|---|---|---|---|
| India | 9,095 | +1.3% | 1,545 | +3.5% |
| US | 47,760 | +1.6% | 7,265 | +2.0% |

This result goes against the usual advice. Over this period, breakouts that happened with the index below its 200-day did as well or better. So did stocks in general on those days. The reason is the sample.

Most of its declines, such as 2015–16 and 2020, were followed by quick recoveries. Long bear markets like 2008 are not in it.

What to conclude: a regime filter is insurance against a long bear market, and its premium is paid in missed rebounds. Whether it is worth it depends on how much a deep drawdown would hurt you. Test it on your own strategy, and include at least one long bear market if your data allows.

Caveats: today's stock lists (survivorship bias, which favours rebounds), overlapping windows, no costs.

## 9. Building and testing it yourself

**Data.** The index you will filter on, with at least 200 sessions before the first test date. Breadth needs the full stock universe each day, including delisted stocks. VIX for the US; India VIX for India (published since 2008).

**Look-ahead traps.**

- The filter reads today's close and applies from the next session. Never apply it to today's trades.
- Breadth must be computed from the stocks that existed that day.
- A band filter has memory: store its state, do not recompute it from today's values alone.

**Testing a filter properly.**

1. Run the strategy without any filter. Save every trade with its entry date.
2. Tag each trade with the filter state on its signal day.
3. Compare the two groups: number of trades, win rate, average R, and the worst drawdown with and without the "off" trades.
4. Look at time: does the filter remove a few deep drawdowns, or many ordinary trades?
5. Repeat on the other market and in a period you did not use to design it.

**Parameters to test.**

- The index.
- The average length: 100, 150 and 200 days.
- The band: none, 1%, 2% and 3%.
- What "off" means.

 Keep the strategy itself fixed.

**Costs.** A filter changes how often you trade. Count the extra round trips from whipsaws at India's roughly 0.3%–0.6% per round trip.

**What a good test reports.** Return, maximum drawdown, the longest time underwater, time in the market, number of switches, and the trades removed: how many and their average R.

```
state = ON
each day t, after the close:
    if state == ON and close[t] < sma200[t] * (1 - band): state = OFF
    elif state == OFF and close[t] > sma200[t] * (1 + band): state = ON
    on day t+1: take new strategy signals only if state == ON
```

## 10. Checklist

- [ ] I have written down which index, breadth measure or volatility gauge the filter reads, and it matches the stocks the strategy trades.
- [ ] I know what "off" means: no new trades, tighter stops, or close everything.
- [ ] The filter has a band or confirmation to limit whipsaws.
- [ ] I tested the strategy with and without the filter, on trades tagged by filter state.
- [ ] The test includes at least one long bear market, or I know it does not.
- [ ] I counted the cost of the trades the filter removes, not just the losses it avoids.
- [ ] I will follow it without overriding it, and log what it costs.

## Further reading

- Mebane T. Faber, "A Quantitative Approach to Tactical Asset Allocation", *Journal of Wealth Management* (2007; updated 2013).
- Alan Moreira and Tyler Muir, "Volatility-Managed Portfolios", *Journal of Finance* (2017).
- Kent Daniel and Tobias Moskowitz, "Momentum Crashes", *Journal of Financial Economics* (2016).
- William Brock, Josef Lakonishok and Blake LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns", *Journal of Finance* (1992).
- Valeriy Zakamulin, *Market Timing with Moving Averages* (Palgrave Macmillan, 2017).
- Martin Zweig, *Winning on Wall Street* (Warner Books, 1986).
- Alexander Elder, *Trading for a Living* (Wiley, 1993).
- Related guides: [the index trend](learn-health-trend.md), [breadth](learn-health-breadth.md), [volatility](learn-health-volatility.md), [backtesting honestly](learn-test-backtesting.md).
