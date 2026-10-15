# Expectancy — what a trade is worth on average, measured in R

**In short**

- Measure every trade in R, the amount you planned to lose. Buy at $50 with a stop at $47, and 1R is $3 a share.
- Expectancy is the average result per trade in R. It needs both halves: how often you win, and how big the wins are next to the losses.
- In trend-following, the typical trade is a small loss. A few large winners pay for everything, so cutting them short destroys the edge.
- At a 30% win rate, ten losses in a row within 100 trades is typical. Real streaks run longer still, because losses bunch together in weak markets.
- A small edge needs thousands of trades to prove, and a modest cost can erase it.

This is the first of four guides on risk. Next come [position sizing](learn-risk-sizing.md), [stops and exits](learn-risk-stops-exits.md) and [portfolio risk](learn-risk-portfolio.md).

> **The illustrative trades used in this guide.** To show what real results look like, we applied a simple textbook rule to stored daily prices. Entry: a stock closes above its highest high of the prior 55 sessions (the Turtle traders' long-term breakout); buy at the next open. Stop: 2 × ATR(14) below the entry. Exit: the first close below the lowest low of the prior 20 sessions, sold at the next open (a "trend exit"). Variants replace that exit with a fixed target at +2R or +3R. Signals from January 2010 to December 2025, at most one per stock per 20 sessions, on today's listed US and NSE companies with a close of at least $5 / ₹20 and 50-day average turnover of at least $20m / ₹10 crore. About 60,500 US and 17,600 Indian trades. No costs. Funds and ETFs were left out. So were 19 trades whose "loss" was an unadjusted corporate action, such as a special dividend, spin-off or demerger. These trades illustrate how results are shaped. They are not a test of a trading system: the stock lists contain only companies that survived, which flatters every average.

---

## 1. R — one unit of risk

Buy at $50 with a stop at $47. The risk is $3 a share, and that $3 is 1R. Sell at $56 and the trade made +2R. Get stopped at $47 and it lost −1R. Sell at $48.50 and it lost −0.5R.

The same works in rupees. Buy at ₹1,200 with a stop at ₹1,128. Then 1R is ₹72. Sell at ₹1,416 and the result is +3R.

Measuring in R removes position size and currency. A +2R trade is +2R whether you bought ten shares or a thousand, in dollars or in rupees. It also ties the result to the decision made at entry.

So always keep the **initial** stop for measuring R. A trailing stop later raised above the entry would make the risk look zero or negative, and R would mean nothing. Subtract costs (charges and slippage) from the profit before dividing by the initial risk, so R is net of costs.

## 2. Expectancy — the formula

Three traders keep records for a year:

| Win rate | Avg win | Avg loss | Expectancy | Verdict |
|---|---|---|---|---|
| 60% | +1.0R | −1.0R | 0.6 − 0.4 = **+0.20R** | Fine: high hit rate, small payoff |
| 40% | +2.5R | −1.0R | 1.0 − 0.6 = **+0.40R** | Better, despite losing more often |
| 70% | +0.5R | −1.5R | 0.35 − 0.45 = **−0.10R** | Loses money while "usually right" |

The rule behind the table:

> **Expectancy = (win % × average win) − (loss % × average loss)**, in R.

It is simply the average R per trade. The third row is the classic trap. Taking small profits quickly and letting losers run gives a high win rate and a negative expectancy.

### Why a 30–40% win rate can be profitable

The win rate you need to break even depends only on the **payoff ratio**: the average win divided by the average loss.

| Payoff ratio | Break-even win rate |
|---|---|
| 1 : 1 | 50% |
| 1.5 : 1 | 40% |
| 2 : 1 | 33% |
| 3 : 1 | 25% |
| 4 : 1 | 20% |

The formula is: break-even win rate = 1 ÷ (1 + payoff ratio). Trend-following and breakout methods live in the bottom rows. They lose small amounts often and win large amounts rarely.

The illustrative breakout trades show it. With the trend exit, they won 29% of the time in the US and 28% in India. With a fixed target at +2R, the win rate rose to about 36%, but the average win shrank to about 2R. Whether a method makes money depends on the payoff ratio as much as the win rate.

## 3. The distribution of R — a fat right tail

An average hides the shape of the results. Here are the illustrative breakout trades, closed trades only, before costs:

| Illustrative trades | US, trend exit | India, trend exit | US, +2R target | India, +2R target |
|---|---|---|---|---|
| Trades | 60,470 | 17,592 | 60,473 | 17,597 |
| Win rate | 29.0% | 28.3% | 36.1% | 35.6% |
| Median trade | −1.00R | −1.00R | −1.00R | −1.00R |
| Trades ending near −1R (−0.8 to −1.2R) | 56% | 59% | 60% | 63% |
| Sum of the best 10% of trades | +35,587R | +13,825R | +13,464R | +3,646R |
| Sum of all other trades | −28,749R | −7,673R | −9,129R | −2,529R |
| Share of all winning R from the best 10% | 75% | 78% | 30% | 29% |
| Best single trade | +123.7R | +84.3R | +14.4R | +4.7R |

Read down a column and the pattern is plain:

- **The median trade is a full −1R loss.** The typical trade in a trend-following method loses.
- **The best tenth of the trades makes more than the whole net profit.** Without them, every column loses money. Skipping a setup "because it looked tired" can throw away the year.
- **The exit decides how big the big wins get.** With the trend exit, the best 10% of trades held three-quarters of all winning R. With a +2R target, they held under a third. A fixed target cuts off the largest wins ([stops and exits](learn-risk-stops-exits.md)).
- **A target can still be overshot.** The US best trade under the +2R target was +14.4R, because the stock opened far above the target after news.

The large wins also took time. With the trend exit, the median winner was held about three months (91 days in the US). The median loser lasted about two weeks.

### The left tail exists too

```series
title: Relmada (RLMD), autumn 2022 — a stop that could not protect
from: 2022-08-01
to: 2022-12-30
tf: D
line: us:RLMD | Relmada (RLMD) | log
mark: 2022-10-06 | a buyer near $34.6, stop $30.83
mark: 2022-10-13 | opened at $6.66
caption: The close went from $31.69 to $6.47 in one session, on a clinical-trial result. A trader with that entry and stop would have sold at the open: a loss of about 7.4R. At 1% risk, that one trade cost 7.4% of the account.
```

Relmada, a drug developer, closed at $31.69 on 12 October 2022. The next morning it opened at $6.66 after a failed trial. A trader who bought near $34.60 with a stop at $30.83 risked $3.77 a share. The sale at the open lost about $28, or 7.4R.

A stop is an order, not a guarantee. When a stock opens below the stop, you are filled at the open, and the loss is larger than 1R. In the illustrative US trades, 9.3% of stop-outs filled more than 0.5% below the stop. They averaged −1.57R. In India the share was 4.6%, averaging −1.38R.

Expectancy already includes such trades, provided you record them honestly. Many of the worst gaps come on results days ([the calendar guide](learn-macro-calendar.md)).

## 4. Losing streaks are normal

Picture a method that wins 30% of the time. It loses 70% of its trades, so long runs of losses are simple arithmetic. They are not a sign that something broke.

We simulated it. Each trade is an independent coin flip at the given win rate. For each win rate we ran 20,000 sequences of 100 trades and recorded the longest run of losses in each:

| Win rate | Longest losing streak in 100 trades (median) | 1 in 10 sequences at least | Chance of 8+ in a row |
|---|---|---|---|
| 30% | 10 | 15 | 85% |
| 35% | 9 | 13 | 69% |
| 40% | 7 | 11 | 49% |
| 45% | 6 | 10 | 30% |
| 50% | 6 | 8 | 17% |

Real trades are worse than coin flips, because losses bunch together. To see it, we took the illustrative trades through a small portfolio. It held at most ten positions; when several stocks broke out on the same day, it picked among them at random. We ran 40 such portfolios per market, and compared each one's longest losing streak with shuffles of its own trades:

| Illustrative 10-position portfolio | Trades (median) | Win rate | Longest actual streak (median of 40) | Same trades shuffled: median (10th–90th pct) |
|---|---|---|---|---|
| US | 1,294 | 29% | 29 (range 21–38) | 18 (14–23) |
| India | 1,138 | 28% | 27 (range 23–34) | 18 (15–24) |

Two lessons. First, **20–30 losses in a row is ordinary** for a method like this over 16 years. Second, the actual streaks were about ten trades longer than shuffling predicts. In 38 of the 40 US portfolios, the actual streak was longer than nine shuffles in ten.

Losses cluster because trades taken in the same weak market fail together. That is correlation, the subject of [portfolio risk](learn-risk-portfolio.md). It is also why [the trend guide](learn-health-trend.md) and [regime filters](learn-strat-regime-filters.md) try to keep you out of weak markets.

What a streak costs depends on position size, which is why [position sizing](learn-risk-sizing.md) comes next. Twenty losses at 1% each leave the account about 18% down. At 5% each, they leave it about 64% down.

## 5. Sample size — when does expectancy mean anything?

Suppose your first 30 trades averaged +0.3R. The spread of results was wide, with a standard deviation of 3R: some −1R losses, a few +10R wins. How sure can you be that the edge is real?

The uncertainty of an average is its **standard error**: the standard deviation of R divided by the square root of the number of trades. Here that is 3 ÷ √30, about 0.55R. Roughly, the true expectancy lies within two standard errors of the measured one: anywhere from −0.8R to +1.4R. Thirty trades told you almost nothing.

The table shows how many trades it takes before the measured edge is at least twice its standard error. The formula is (2 × standard deviation ÷ expectancy)².

| Kind of method | Expectancy | Std dev of R | Trades needed |
|---|---|---|---|
| Fixed +2R target, thin edge | +0.05R | 1.5R | 3,600 |
| Fixed +2R target, decent edge | +0.15R | 1.5R | 400 |
| Trend exit, thin edge | +0.10R | 2.75R | about 3,000 |
| Trend exit, good edge | +0.30R | 3.0R | 400 |
| Trend exit, large edge | +0.50R | 3.0R | 144 |

The standard deviations come from the illustrative trades. They were about 1.5R with a fixed target, and 2.75–3.4R with the trend exit.

- **A small edge needs thousands of trades to prove.** At +0.05R, even ten years of trading cannot tell it apart from zero.
- **Rare huge wins widen the error.** A trend exit's big winners raise the standard deviation. Its edge must be larger to be detected in the same number of trades.
- **For a person** taking 50 trades a year, only a large edge can ever be confirmed. Judge your record by R per setup over 100 or more trades, not by last month.

## 6. Per trade versus per unit of time

Two methods each risk 1% a trade. Method A averages +0.5R and holds trades for 100 days. Method B averages +0.2R and holds for 20 days. With the same money, B can take five trades for each one of A's: +1.0R against +0.5R.

Expectancy is per trade, but money is made per year. Capital tied up in a slow trade cannot be used for the next one. Two more numbers matter: how many trades a year the method finds, and how long each one keeps the money busy.

The illustrative trades show the effect. "R per 100 position-days" is the total R divided by the total days held, times 100:

| Illustrative trades | Expectancy | Mean days held | R per 100 position-days |
|---|---|---|---|
| US, trend exit | +0.11R | 45 | 0.25 |
| US, +3R target | +0.12R | 38 | 0.31 |
| US, +2R target | +0.07R | 26 | 0.28 |
| India, trend exit | +0.35R | 47 | 0.74 |
| India, +3R target | +0.15R | 34 | 0.44 |
| India, +2R target | +0.06R | 23 | 0.27 |

Days are calendar days. In the US sample, the +2R target earned less per trade than the trend exit but more per day of capital used. In India the trend exit won on both counts. Neither is a general law; the point is to measure both.

The general rule: returns come from **expectancy × trades per year × risk per trade**. Drawdowns then slow the compounding. A lower expectancy with many more independent chances can beat a higher one that trades twice a year. But only if the edge is real (§5).

## 7. Costs and slippage eat a thin edge

Suppose a round trip costs 0.3% of the position: charges on the buy and the sell, plus slippage. With a 5% stop, 1R is 5% of the position. So the cost is 0.3 ÷ 5 = 0.06R on every trade.

Costs are charged as a share of the position, while R is a share of the risk. The tighter the stop, the bigger the same cost is in R:

| Round-trip cost | 3% stop | 5% stop | 8% stop |
|---|---|---|---|
| 0.1% | 0.033R | 0.020R | 0.013R |
| 0.3% | 0.100R | 0.060R | 0.038R |
| 0.5% | 0.167R | 0.100R | 0.063R |

Now apply it to two methods with 5% stops and a 0.3% round trip:

| Method | Expectancy before costs | After 0.06R of costs |
|---|---|---|
| Thin edge | +0.05R | −0.01R |
| Large edge | +0.40R | +0.34R |

A small edge can vanish with one realistic cost assumption. A large one barely notices. In the illustrative trades, the median stop was 4.6% below the entry in the US and 6.8% in India. So a 0.1% round trip costs about 0.02R per US trade. A 0.3% round trip costs about 0.05R per Indian trade.

Indian delivery trades carry real charges. STT (securities transaction tax) is 0.1% on each side, plus stamp duty, exchange fees, GST and depository charges. That comes to roughly 0.25–0.35% a round trip before slippage. Illiquid stocks cost more again, because the gap between bid and ask is wider.

## 8. What the trader does

1. **Write the stop before the entry.** R does not exist without it. Record entry, initial stop and exit for every trade.
2. **Compute R for every closed trade**, including the scratches and the gaps, net of costs.
3. **Review by setup, not in total.** Tag each trade with its setup (breakout, pullback, VCP pivot…). After 30–50 trades per setup, compare win rate, average win, average loss and expectancy. Drop or fix the setup that drags the results down.
4. **Watch the average loss.** If it creeps past −1R, either stops are being moved or positions are being held through gaps. Fix that before anything else.
5. **Never cut your biggest winners short on purpose.** Taking profits early to "lock in" gains raises the win rate and lowers expectancy (§2, row three).
6. **Expect the streak.** Decide in advance that 15 losses in a row is normal. Decide too what size you will be trading when it comes.

## 9. What the evidence says

- **Robust:** expectancy is just an average, and the arithmetic of payoff ratio and break-even win rate is exact.
- **Robust:** trend-following returns depend on a few very large winners. The managed-futures literature documents it, as do Covel's and Faith's accounts of the Turtles. The illustrative trades show it in both markets.
- **Robust:** losing streaks of 10–20 trades at 25–35% win rates follow from probability alone. Trades that move together make them longer.
- **Folklore:** that a high win rate signals a good method, or that a 3:1 target "guarantees" profit. Neither says anything without the other half of the formula.
- **Often missed:** small samples. Expectancy from a few dozen trades has an error bar wider than the number itself.
- **Failure mode:** an edge that exists before costs and not after.
- **Limits of the illustrations:** the trades come from one textbook rule on today's listed companies. Companies that failed and were delisted are missing, so the averages are flattered. There are no costs, fills use daily bars, and many trades overlap in time. Use them for the shape of the results, not for how much the rule earns.

## 10. Checklist

- [ ] Every trade has an initial stop (so a 1R value) and, once closed, its R net of costs
- [ ] Expectancy per setup recalculated monthly; sample size noted next to it
- [ ] Average loss no worse than about −1.1R (if worse, find out why)
- [ ] Biggest winners held to the exit rule, not cut early
- [ ] Current losing streak compared with what the win rate predicts (§4); costs in R checked

## Further reading

- Van K. Tharp, *Trade Your Way to Financial Freedom* — R-multiples and expectancy as a trader's core numbers.
- Curtis Faith, *Way of the Turtle* — the Turtles' rules, sizing by volatility (their "N") and what streaks and drawdowns felt like.
- Michael Covel, *Trend Following* — the right tail and why trend followers lose more often than they win.
- Robert Carver, *Systematic Trading* — sample size, costs and over-fitting in backtests.
