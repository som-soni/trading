# Swing trading — what it is, and seven ways to find a swing

**In short**
- A swing trade holds for days to a few weeks to catch one identifiable move. It can be long or short, in any liquid instrument.
- There are many ways to define "a move": a percentage swing chart, a three-day swing chart, Renko bricks, flags, an N-day breakout, trends that agree across timeframes, and the strongest stock in the strongest group.
- On their own, the entry signals measured here barely beat the average stock. Taken only when the daily, weekly and monthly trends agree, they did better.
- Most of the edge comes from where you trade (a rising market, a leading group, an aligned trend) and how you exit, not from the trigger.
- Trail the stop instead of setting a target, keep a fixed number of positions, and size every trade from its stop.

## 1. The idea

On 15 December 2025, Phoenix Mills closed at ₹1,789. That was above its last swing high of ₹1,773. The fall before it had been only about 5%. Its trend was up on the daily, weekly and monthly charts.

A swing trader bought at the close. The stock rose to ₹1,951 by 6 January. On 16 January it closed below its 21-day exponential average, at ₹1,859, and the trader sold. The gain was about 4%. Two months later the stock was below ₹1,480.

```series
title: Phoenix Mills, 2024–2026 — swing buys and a 21-day average exit
from: 2024-06-01
to: 2026-04-30
line: india:PHOENIXLTD.NS | Phoenix Mills | log
line: india:PHOENIXLTD.NS@ema21 | 21-day exponential average
line: india:PHOENIXLTD.NS@vol | Volume | pane2 bars
mark: 2024-11-22 | buy
mark: 2024-12-18 | exit
mark: 2025-12-15 | buy
mark: 2026-01-16 | exit
caption: Two buys on a close above the last swing high, each sold at the first close under the 21-day average (illustrative textbook-rule trades, see §6).
```

That is a swing trade. It aims at one leg of a move, not the whole trend. It does not predict where the leg ends. It holds while the leg lasts and leaves when it ends.

**Where the word comes from.** No dictionary defines swing trading, and traders use the term loosely. Charles Dow, writing around 1900, spoke of short swings and medium swings to describe how long a move lasts. W. D. Gann drew swing charts in the 1930s. Richard Wyckoff described small waves building into larger waves, and those into bull and bear markets.

Jesse Livermore used "swing" for a whole primary trend. He argued against trading the short ones at all. Today the word usually means the middle wave: longer than a day trade, shorter than a position held for many months.

**Why it can work.** Prices move in legs because news, earnings and fund flows arrive in bursts. Investors adjust their views slowly, so a move that starts tends to run for a while. Research finds that returns over three to twelve months tend to continue (Jegadeesh and Titman, 1993; Moskowitz, Ooi and Pedersen, 2012). Returns over one week to one month tend to reverse instead (Jegadeesh, 1990; Lehmann, 1990).

So a swing trader sits between two effects. The trade is short, but it should lean on the slower trend, not on last week's jump.

**Who is on the other side?** On a breakout, it is the holder who is glad to sell at a new high and the trader betting on a pullback. On a pullback entry, it is the seller who fears the trend is over. Each is often right. The swing trader accepts many small losses to be in the legs that keep going.

## 2. When it works and when it doesn't

It works when trends exist at the scale of weeks: a rising market, a sector in favour, a stock re-rated by earnings. It fails in choppy markets that reverse every few days. There, each entry is followed by a stop.

| Market condition | What a swing trader sees | What to expect |
|---|---|---|
| Steady uptrend in the index and the group | Entries work and trails are hit late | A run of winners, some much larger than the risk |
| Sideways, choppy index | Breakouts reverse within days | Many small losses |
| Sharp sell-off | Stops hit together; gaps through stops | A cluster of losses in one week |
| Narrow leadership (a few stocks carry the index) | Most setups fail outside the leaders | Few good trades; patience pays |
| Early recovery after a fall | Leaders break out first | The best entries of the cycle, if the filters allow them |

**India notes.** Only about two hundred stocks have futures and options, and fewer are liquid enough to short. A swing short is a futures or options trade, not a cash trade (see the guide on futures). Price bands of 5% or 10% can stop a fill on a breakout or a stop.

**US notes.** Short selling is open to any stock that can be borrowed. Earnings reports come before the open or after the close, so a stop can be gapped. ETFs on gold, bonds, sectors and foreign markets are deep and cheap to trade.

## 3. Seven ways to find a swing

Each method answers one question: has a new leg started? They differ in how they define "a leg".

### 3.1 The percentage swing chart

Record only moves of at least a set percentage, such as 5%. Ignore smaller wiggles. A rise of 5% or more from the last low is an up-swing; a fall of 5% or more from the last high is a down-swing.

A buy signal is a close above the last swing high. A sell signal is a close below the last swing low. Perry Kaufman calls this one of the oldest trading systems. It ignores time: a stock flat for two months still signals the day it breaks out.

| Choice | Effect |
|---|---|
| Smaller threshold (2%–3%) | More swings, earlier signals, more false starts |
| Larger threshold (8%–10%) | Fewer swings, later signals, fewer whipsaws |
| Closes only | Simpler; ignores intraday spikes |
| Highs and lows | Earlier signals; more noise |

Point-and-figure charts work the same way, with a fixed box size instead of a percentage.

### 3.2 The three-day swing chart

Gann's swing chart counts days instead of percent. While prices rise, the line follows each day's high. It turns down only after the market makes lower highs for a set number of days, usually three. On the way down it follows the lows until three days of higher lows turn it up.

The count filters out one- and two-day pullbacks. Marc Rivalland adapted the count so the line turns sooner. A swing high or low on this chart becomes the level to beat, as in §3.1.

### 3.3 Taylor's three-day cycle

George Taylor described a rhythm of three days in 1950: a buying day, a selling day and a short-sale day, in turn. The idea is that markets rise for a while, stall, then fall back, and that the pattern repeats at larger scales.

It is worth knowing as history. There is little published evidence that a fixed three-day cycle exists in stock prices. Treat it as a way of thinking about pullbacks, not as a timing rule.

### 3.4 Flags and pennants

A sharp move up (the pole) is followed by a brief, tight pause. A flag drifts slightly against the move; a pennant narrows into a small triangle. The entry is a break out of the pause in the direction of the pole.

These are easy to see and hard to define. The rules and their evidence are in [Flags, pennants and high tight flags](learn-strat-flags.md).

### 3.5 The N-day breakout

Ask whether today's close is above the highest high of the last N days. Short look-backs of 7 to 21 days suit swing trades. Longer ones of 55 days and more suit trend following.

It is the time-based twin of the percentage swing chart. It is simple to test and to automate. The long version is covered in [Channel breakout trend following](learn-strat-channel-breakout.md).

### 3.6 Trends that agree across timeframes

A trend can be up on one chart and down on another. A stock can be in a monthly uptrend and a daily pullback, or the reverse. This method takes a trade only when the daily, weekly and monthly trends agree.

One simple version, used in §8:

| Timeframe | Condition |
|---|---|
| Daily | The 50-day average is above the 200-day, and both are higher than 20 sessions ago |
| Weekly | The close is above the 30-week average, and that average is higher than four weeks ago |
| Monthly | The close is above the 10-month average, and that average is higher than three months ago |

Count the current week and month as they stand that day. Waiting for the month to close looks ahead.

### 3.7 The strongest stock in the strongest group

Look one level up before looking at the chart. Which sector, industry or size segment is leading? Money tends to flow into groups, not single stocks. A good chart in a weak group fails more often than an average chart in a strong one.

Judge groups on **equal-weight** baskets. A cap-weighted sector index can be lifted by one or two giants while most of its members fall. In an equal-weight basket, each member counts the same, so a rise means most of the group is rising.

Then compare each member with its basket since a fixed date. Is the group's gain broad, or carried by two or three stocks? The method is described in [Sectors and groups](learn-sectors-groups.md) and [Relative-strength leaders](learn-strat-rs-leaders.md).

### Renko bricks

Renko charts are a close cousin of the percentage swing chart. A brick is drawn only when the price moves a full brick size from the last brick, for example 5%. Up bricks are green and down bricks are red. Time drops out of the chart.

| Use | How |
|---|---|
| Spot a turn | Wait for one or two green bricks after a run of red ones |
| Spot a breakout | A green brick above all earlier bricks is a new high |
| Trail a stop | Exit on the first red brick, or on two |
| Filter noise | A larger brick ignores more of the day-to-day movement |

The chart compresses long sideways stretches. A stock still far below its old high stands out at once, and so does one that has just cleared it.

### Relative or absolute?

Stocks can be compared with their peers: IT against IT, midcaps against midcaps. That is relative momentum. Gold, crude oil or an index have no peer group. For them only absolute momentum works: is the price above where it was some months ago?

So the method depends on the instrument. See [Cross-sectional momentum](learn-strat-xs-momentum.md) and [Dual momentum](learn-strat-dual-momentum.md).

## 4. A complete swing system, step by step

The seven methods are triggers. A system needs a filter, a trigger, an exit, a size and a portfolio rule.

### Universe and filters

- Liquid stocks, or liquid ETFs. Many listed ETFs trade too little to use.
- Price above the 50-day or 200-day average.
- **Category filter:** the stock's own segment index above its 21-day or 50-day average. For a midcap, that is a midcap index; for a small cap, a small-cap index. If the segment is below its average, take no new trades in it.
- Optional: the trend aligned on daily, weekly and monthly bars (§3.6).

### Setup and entry

Pick one trigger and use it every time:

| Trigger | Entry |
|---|---|
| Percentage swing chart or Renko | Close above the last swing high, or after two green bricks |
| N-day breakout | Close above the highest high of the last 10 to 21 days |
| Flag or pennant | Close above the top of the pause |
| Supertrend | The first close above the Supertrend line |

**Supertrend** is a trailing line built from the average true range (ATR). The usual setting uses ten days of ATR and a multiple of three. In an uptrend the line sits three ATRs below the day's midpoint and only moves up. A close below it flips the line above the price, and the trend reads down.

### Exits

Trail the stop instead of setting a target. A strong leg can last for months, and nobody knows in advance when it ends. Pick one trail and keep it for the whole trade.

| Trail | Breathing room | Typical use |
|---|---|---|
| 21-day average (simple or exponential) | Wide | Lets a trend run through normal pullbacks |
| 7- to 9-day average | Tight | Short, fast legs |
| Supertrend (10 days, 3 ATR) | Adjusts to volatility | Volatile stocks |
| Fixed percentage under the highest high | Fixed | Simple; too tight for volatile stocks |

A fixed 3%–4% trail sits closer than one day's normal range for many stocks. It will sell good trades on ordinary pullbacks. [Stops and exits](learn-risk-stops-exits.md) compares trailing exits in detail.

### Position size

Two common ways:

- **Equal slots.** With five positions, each gets 20% of the account. Simple, and every position matters the same.
- **Risk-based.** Decide what one trade may lose, such as 1% of the account. Divide by the distance to the stop. On ₹10 lakh, risking ₹10,000 with a ₹20 stop gives 500 shares.

Risk-based sizing keeps every loss the same size. Equal slots let a trade with a wide stop lose more. See [Position sizing](learn-risk-sizing.md).

### Managing the portfolio

- Hold a fixed number of positions, such as five.
- **One in, one out.** When the portfolio is full, take nothing new. When a stop frees a slot, run the scan and fill it.
- Never add money to the system mid-stream because a week went well. Grow it in planned steps.
- Aim for winners several times the size of the losers. With a trailing exit, a few large winners pay for many small losses.

### ETFs instead of stocks

The same system can run on a basket of liquid ETFs: index, sector, gold, silver, bonds and foreign markets. There is no single-company risk, gaps are smaller and the basket spreads across asset classes. The trades are slower and smaller. Use absolute momentum (§3), since the basket has no peer group.

## 5. The parameters

| Parameter | Typical range | Tighter | Looser |
|---|---|---|---|
| Swing threshold or brick size | 3%–10% | More signals, more noise | Fewer, later signals |
| Breakout look-back | 7–21 days | Earlier, more false breaks | Later, more reliable |
| Category filter average | 21–50 days | Quicker on and off | Fewer switches |
| Trailing average | 7–21 days | Small gains locked in | Bigger winners, bigger give-backs |
| Supertrend multiple | 2–4 ATR | Flips often | Holds through noise |
| Number of positions | 5–10 | Concentrated | Smoother equity |

Choose before testing. Then change one at a time, and judge the change on years you did not use to choose it.

## 6. Worked example

### Phoenix Mills — the same rule, twice

These are illustrative textbook-rule trades: a close above the last 5% swing high, sold at the first close under the 21-day exponential average. Costs are ignored.

| | November 2024 | December 2025 |
|---|---|---|
| Buy (close) | ₹1,627 on 22 Nov | ₹1,789 on 15 Dec |
| Trend aligned on daily, weekly, monthly? | No — all three down | Yes |
| Highest close before the exit | ₹1,868 on 11 Dec | ₹1,951 on 6 Jan |
| Exit (close under the 21-day average) | ₹1,715 on 18 Dec | ₹1,859 on 16 Jan |
| Result | About +5% | About +4% |
| Low in the next three months | ₹1,458 | ₹1,477 |

Both trades made money, and both exits came before a fall of more than 15%. The trailing exit did the work. The 2024 buy came while all three trends pointed down, and it still worked.

One example proves nothing either way. The filter is a matter of averages over thousands of trades (§8). The lesson here is the exit: neither leg was held through the decline that followed.

## 7. Common mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Buying last week's biggest gainers | One-week winners tend to give back part of the gain | Rank on 3- to 12-month strength; use the week only to time the entry |
| Ignoring the market and the group | Most stocks follow their segment | Use a category filter |
| Switching trails mid-trade | Turns a rule into a feeling | Pick one trail per system |
| Too tight a trail | Sells good trades on noise | Size the trail to the stock's ATR |
| Fixed targets | Caps the few trades that pay for the rest | Trail instead |
| Too many positions for the time you have | Stops are missed | Five to ten positions |
| Adding capital after a hot streak | Risk rises just before a cold one | Grow in planned steps |

## 8. What the evidence says

**Published research.**

- Returns over one week to one month tend to reverse (Jegadeesh, 1990; Lehmann, 1990). Returns over 3 to 12 months tend to continue (Jegadeesh and Titman, 1993).
- Time-series momentum, the idea behind absolute trend filters, has worked across futures markets for decades (Moskowitz, Ooi and Pedersen, 2012).
- Simple moving-average and range-breakout rules showed forecasting power on the Dow Jones index from 1897 to 1986 (Brock, Lakonishok and LeBaron, 1992). After allowing for the many rules tried, much of it faded in later data (Sullivan, Timmermann and White, 1999).
- A 10-month moving-average filter on asset classes cut drawdowns with similar returns over long histories (Faber, 2007).
- A survey of studies found more positive than negative results for technical rules, with many caveats about testing (Park and Irwin, 2007).

**An event study on stored prices.** It covers liquid stocks from 2013 to 2025, and counts a signal on the day the close crosses its level.

| Filter | India | US |
|---|---|---|
| Average daily traded value, 50 days | ₹10 crore | $10 million |
| Price | ₹50 | $5 |

Each forward return is measured against the average of all eligible stocks on the same day. A positive number means the group beat the typical stock. Costs are ignored, and the stock list is today's, so delisted losers are missing.

| Signal | India: 20-day excess return | US: 20-day excess return |
|---|---|---|
| 20-day close breakout | +0.08% | −0.08% |
| 5% swing-chart buy | +0.14% | −0.25% |
| 20-day breakout, trend aligned | +0.62% | +0.18% |
| 20-day breakout, not aligned | −0.46% | −0.28% |
| 5% swing-chart buy, trend aligned | +0.69% | +0.11% |

On their own, both triggers did about as well as the average stock. The trend filter separated the better half from the worse half in both markets.

The same split holds without any trigger. Each Friday, stocks were sorted by whether all three trends agreed.

| Weekly sample | India | US |
|---|---|---|
| Share of stock-weeks aligned | 42% | 35% |
| Aligned: 20-day excess return | +0.43% | +0.24% |
| Not aligned: 20-day excess return | −0.31% | −0.13% |
| Aligned: 60-day excess return | +0.98% | +0.69% |
| Years in which aligned beat not aligned | 12 of 13 | 12 of 13 |

In both markets, 2016 was the only year in which aligned stocks did worse.

**The one-week scan.** Each Friday, stocks were also sorted by their return over the past week.

| Top tenth by one-week return | India | US |
|---|---|---|
| Next 5 days, excess return | −0.09% | −0.17% |
| Next 20 days, excess return | −0.02% | −0.25% |

Last week's best performers did not keep beating the market. In the US they lagged, as the reversal research predicts. A one-week scan finds stocks that are moving, but the ranking itself carries no edge.

**What the numbers mean.** These are averages of small effects, before costs, over overlapping periods. A 0.5% edge over a month is real money over many trades and nothing on a single trade. The pattern matches the research: the trend you trade with matters more than the trigger you enter on.

## 9. Building and testing it yourself

1. Write the rules down before testing: filter, trigger, exit, size and the number of positions.
2. Use closing prices for signals and fill at the next open, or at the close if you can trade it.
3. Charge costs: brokerage, taxes and slippage of at least 0.1% each way for liquid stocks.
4. Test a trigger with and without the trend filter and the category filter. Keep a filter only if it helps in most years.
5. Tune on one span of years and judge on a later span you have not looked at.
6. Count trades. Fewer than a hundred tell you little.
7. Look at the worst run of losses and the deepest drawdown, not only the average.
8. Paper trade for some months before using real money.

## 10. Checklist

- [ ] The stock's segment index is above its 21- or 50-day average
- [ ] The group is leading on an equal-weight basis, and the stock is ahead of its group
- [ ] The trend is up on daily, weekly and monthly bars
- [ ] One trigger, the same every time: swing high, Renko bricks, N-day breakout, flag or Supertrend
- [ ] Stop and trail decided before entry; no fixed target
- [ ] Size from the stop, or one equal slot; never more than the system's capital
- [ ] Portfolio not full; one in, one out
- [ ] No results due inside the expected holding period, unless you accept that risk

## Further reading

- Marc Rivalland, *Marc Rivalland on Swing Trading* (2003) — swing charts adapted from Gann.
- Perry Kaufman, *Trading Systems and Methods* (Wiley) — swing charts, breakouts and their testing.
- George Douglas Taylor, *The Taylor Trading Technique* (1950).
- Alan Farley, *The Master Swing Trader* (McGraw-Hill, 2001).
- Deron Wagner, *Trading ETFs* (Wiley) — timeframes and group strength.
- Edwin Lefèvre, *Reminiscences of a Stock Operator* (1923).
- Narasimhan Jegadeesh, "Evidence of Predictable Behavior of Security Returns", *Journal of Finance* (1990).
- Bruce Lehmann, "Fads, Martingales, and Market Efficiency", *Quarterly Journal of Economics* (1990).
- Tobias Moskowitz, Yao Hua Ooi and Lasse Pedersen, "Time Series Momentum", *Journal of Financial Economics* (2012).
- William Brock, Josef Lakonishok and Blake LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns", *Journal of Finance* (1992).
- Ryan Sullivan, Allan Timmermann and Halbert White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap", *Journal of Finance* (1999).
- Mebane Faber, "A Quantitative Approach to Tactical Asset Allocation" (2007).
- Cheol-Ho Park and Scott Irwin, "What Do We Know About the Profitability of Technical Analysis?", *Journal of Economic Surveys* (2007).
- [Regime filters](learn-strat-regime-filters.md), [Stops and exits](learn-risk-stops-exits.md), [Position sizing](learn-risk-sizing.md), [Sectors and groups](learn-sectors-groups.md).
