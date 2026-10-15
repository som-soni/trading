# Expectancy — what a trade is worth on average, measured in R

Learning material. This guide covers:

- R as the unit for every trade, and the expectancy formula;
- why a strategy that loses most of the time can still make money;
- what results really look like: a few big winners, many small losers;
- losing streaks;
- how many trades it takes before a backtest means anything;
- expectancy per trade against per unit of time;
- how costs eat a small edge.

The worked data is this app's own backtest trades, not textbook examples. This
is the first of four guides on risk. Next is [position sizing](learn-risk-sizing.md),
then [stops and exits](learn-risk-stops-exits.md) and
[portfolio risk](learn-risk-portfolio.md).

**Where this shows in the app.** Every backtest's trade list has an `R` column
(`r_multiple`) and a `Days held` column. Open a run from Strategies → (a
strategy) → **Backtests**, or from System → Reports archive. The **Trades** tab
shows the tiles *Trades*, *Win rate* and *Avg R* above the list. Avg R is the
run's expectancy (open trades count as zero there). The figures in this guide
come from those stored trade tables (`report_tables`, name `trades`).

---

## 1. R — one unit of risk

Before entering, you know two prices: the entry and the stop. The distance
between them is the risk per share, and **that distance is 1R**. Every result
is then expressed as a multiple of it:

- Buy at $50, stop $47: 1R = $3 a share. Sell at $56 → **+2R**. Stopped at
  $47 → **−1R**. Sold at $48.50 → **−0.5R**.
- Buy at ₹1,200, stop ₹1,128: 1R = ₹72. Sell at ₹1,416 → **+3R**.

Measuring in R **removes position size and currency**. A +2R trade is +2R
whether you bought 10 shares or 1,000, in dollars or rupees. It also **ties the
result to the decision made at entry**. That is why the app keeps the initial
stop. Otherwise a trailing stop later raised above the entry would make R
meaningless: the risk would seem to be zero or negative.

In the app's backtests, R is **net of modelled costs**. The slippage is built
into the fill prices. The charges are subtracted from the profit or loss
before it is divided by the initial risk.

## 2. Expectancy — the formula

> **Expectancy = (win % × average win) − (loss % × average loss)**, in R.

It is simply the average R per trade. Three worked cases:

| Win rate | Avg win | Avg loss | Expectancy | Verdict |
|---|---|---|---|---|
| 60% | +1.0R | −1.0R | 0.6 − 0.4 = **+0.20R** | Fine: high hit rate, small payoff |
| 40% | +2.5R | −1.0R | 1.0 − 0.6 = **+0.40R** | Better, despite losing more often |
| 70% | +0.5R | −1.5R | 0.35 − 0.45 = **−0.10R** | Loses money while "usually right" |

The third row is the classic trap. Taking small profits quickly and letting
losers run gives a high win rate — and a negative expectancy.

### Why a 35–45% win rate can be profitable

The win rate you need to break even depends only on the **payoff ratio**
(average win ÷ average loss):

| Payoff ratio | Break-even win rate |
|---|---|
| 1 : 1 | 50% |
| 1.5 : 1 | 40% |
| 2 : 1 | 33% |
| 3 : 1 | 25% |
| 4 : 1 | 20% |

(Break-even win rate = 1 ÷ (1 + payoff ratio).) Trend-following and breakout
methods belong in the bottom rows. They lose small amounts often, and win big
amounts rarely. **Every strategy backtested in this app wins between 20% and
34% of the time** (table in §8). So whether they make money depends entirely
on the payoff ratio.

## 3. The distribution of R — a fat right tail

An average hides the shape. In a trend-following system, most trades are small
losses. A fair number are scratches (closed near breakeven). A handful are very
large wins. Those rare, very large wins are the "fat right tail" of the results.
Three measurements on the app's trades, closed trades only:

| Run (closed trades) | Median trade | Trades ending near −1R (−0.8 to −1.2R) | Best 10% of trades | All other trades | Net |
|---|---|---|---|---|---|
| Minervini SEPA, US (551) | −0.42R | 33% | +213R | −189R | +24R |
| Donchian channel, US (496) | −1.00R | 57% | +480R | −240R | +241R |
| Donchian channel, India (437) | −1.01R | 58% | +389R | −206R | +183R |
| Volume breakout, US (703) | −1.01R | 61% | +187R | −158R | +30R |
| Chart patterns, India (515) | −1.01R | 65% | +198R | −126R | +73R |

Read across a row and the point is plain:

- **The median trade is a loss.** In four of the five runs it is a full −1R.
  The typical trade in a working strategy loses.
- **The best tenth of the trades makes more than all the profit.** Without
  them, every one of these runs loses money. Skipping a single setup "because
  it looked tired" can throw away the year.
- **The size of the big wins depends on the exit.** Donchian has no profit
  target, and its best 10% of trades hold 82% of all winning R. The volume
  breakout exits at a fixed target, and its best 10% hold only 36%. A fixed
  target cuts off the biggest wins ([stops and exits](learn-risk-stops-exits.md)).
- **Minervini's losses are smaller than −1R on average** (−0.68R). Its exits
  often sell *before* the stop is hit: on a close below the 50-day, at a
  breakeven stop, or when the breakout fails. So only a third of trades lose
  the full 1R.

### The left tail exists too

A stop is an order, not a guarantee. When a stock opens below the stop, you are
filled at the open, and the loss is larger than 1R. About 3–7% of the stop-outs
in these runs lost more than 1.2R. The worst single trade in the US Donchian
run lost 7.4R:

```series
title: Relmada (RLMD), autumn 2022 — a −7.4R loss through a stop
from: 2022-08-01
to: 2022-12-30
tf: D
line: us:RLMD | Relmada (RLMD) | log
mark: 2022-10-06 | Donchian entry about $34.6, stop $30.83
mark: 2022-10-13 | Gap: filled about $6.7
caption: The close went from $31.7 to $6.5 in one session, on a clinical-trial result. The backtest exits at the open, at −7.4R. At 1% risk that one trade cost 7.4% of the account.
```

Expectancy already includes such trades. The backtester does not block trades
before earnings, so earnings gaps are in the record
([the calendar guide](learn-macro-calendar.md)).

## 4. Losing streaks are normal

With a 30% win rate, 70% of trades lose. Long runs of losses are not a sign
that something broke. They are simple arithmetic. Below are simulated streaks.
Each trade is an independent coin flip at the given win rate. There are 20,000
sequences, and we record the longest run of losses in each:

| Win rate | Longest losing streak in 100 trades (median) | 1 in 10 sequences at least | Chance of 8+ in a row |
|---|---|---|---|
| 30% | 10 | 15 | 85% |
| 35% | 9 | 13 | 69% |
| 40% | 7 | 11 | 49% |
| 45% | 6 | 9–10 | 30% |
| 50% | 6 | 8 | 17% |

And here are the app's runs. Each run's actual longest streak is compared with
a simulation at that run's own win rate and number of trades:

| Run | Win rate | Trades | Longest actual streak | Simulated median (10th–90th pct) |
|---|---|---|---|---|
| Minervini SEPA, US | 27.8% | 551 | 16 | 16 (13–22) |
| Volume breakout, US | 34.3% | 703 | 20 | 13 (11–18) |
| Donchian channel, US | 28.6% | 496 | 20 | 15 (12–21) |
| Donchian channel, India | 27.2% | 437 | 29 | 16 (12–21) |
| Trend pullback, India | 29.7% | 347 | 21 | 14 (10–19) |

Two lessons. First, **15–20 losses in a row is ordinary** for these systems
over a decade. Second, most actual streaks are *longer* than a coin flip
predicts. Losses come in clusters, because trades taken in the same weak market
fail together. The India Donchian run's 29-loss streak is far outside the
simulation. That is correlation, the subject of
[portfolio risk](learn-risk-portfolio.md). It is also why [the trend
guide](learn-health-trend.md) has filters that keep you out of weak markets.

What a streak costs depends on position size. That is why [position
sizing](learn-risk-sizing.md) comes next. 20 losses at 1% each leave the
account about 18% down. At 5% each, they leave it about 64% down.

## 5. Sample size — when does expectancy mean anything?

Expectancy from 30 trades is a guess. The uncertainty of an average is
measured by its **standard error**: the standard deviation of R divided by
√(number of trades). (The standard deviation measures how widely the R values
are spread.) Roughly, the true expectancy lies within ±2 standard errors of the
measured one.

| Run | Trades | Expectancy | Std dev of R | Std error | ±2 SE range | Trades needed for E = 2 SE |
|---|---|---|---|---|---|---|
| Minervini SEPA, US | 551 | +0.04R | 1.53 | 0.065 | −0.09 to +0.17 | ~5,000 |
| Volume breakout, US | 703 | +0.04R | 1.56 | 0.059 | −0.08 to +0.16 | ~5,500 |
| Chart patterns, India | 515 | +0.14R | 1.86 | 0.082 | −0.02 to +0.30 | ~700 |
| Donchian channel, US | 496 | +0.49R | 4.83 | 0.217 | +0.05 to +0.92 | ~400 |
| Donchian channel, India | 437 | +0.42R | 3.86 | 0.184 | +0.05 to +0.79 | ~340 |

The last column is (2 × std dev ÷ expectancy)². What it says:

- **A small edge needs thousands of trades to prove.** At +0.04R with a
  standard deviation of 1.5R, even 700 trades over 13 years cannot tell the
  strategy apart from zero.
- **Rare huge wins widen the error.** Donchian's huge winners make its
  standard deviation three times larger. But its expectancy is ten times
  larger, so it clears the bar in a few hundred trades.
- **For a person** taking 50 trades a year, only a large edge can ever be
  confirmed. Judge your record by R per setup over 100+ trades, not by last
  month.

## 6. Per trade versus per unit of time

Expectancy is per trade. But money is made per year, and capital tied up in a
slow trade cannot be used for the next one. Two more numbers matter: how many
trades a year the method finds, and how long each one keeps the money tied up.

| Run | Expectancy | Trades a year | R a year | Mean days held | R per 100 position-days |
|---|---|---|---|---|---|
| Donchian channel, US | +0.49R | 36 | 17.5R | 97 | 0.50 |
| Donchian channel, India | +0.42R | 32 | 13.4R | 105 | 0.40 |
| Chart patterns, India | +0.14R | 37 | 5.3R | 43 | 0.33 |
| Volume breakout, US | +0.04R | 51 | 2.2R | 29 | 0.15 |
| Minervini SEPA, US | +0.04R | 33 | 1.4R | 32 | 0.13 |

(Days are calendar days. "R per 100 position-days" = total R ÷ total days
held × 100.) Donchian's winners take months: the median winner was held about
200 days, against 19 for the median loser. Yet it still earns the most per day
of capital used. The general rule: returns come from **expectancy × trades per
year × risk per trade**, before drawdowns slow the compounding. A slightly
lower expectancy with many more independent opportunities can beat a higher
one that trades twice a year. But only if the edge is real (§5).

## 7. Costs and slippage eat a thin edge

Costs are charged as a share of the position. R is a share of the risk. With a
5% stop, a 0.1% cost is 0.02R. The app's runs, with costs as modelled:

| Run | Modelled costs | Mean cost per trade | Expectancy net | Gross |
|---|---|---|---|---|
| Minervini SEPA, US | 1bp charges + 5bp slippage per side | 0.024R | +0.043R | +0.067R |
| Volume breakout, US | 5bp slippage per side | 0.022R | +0.042R | +0.064R |
| Donchian channel, US | 5bp slippage per side | 0.016R | +0.486R | +0.501R |
| Chart patterns, India | 10bp slippage per side | 0.033R | +0.141R | +0.174R |
| Minervini SEPA, India (v1.5) | 12bp charges + 15bp slippage per side | 0.091R | +0.053R | +0.144R |

Costs already take a third of the small US edges. And the India runs other than
Minervini model **slippage only — no STT, stamp duty or exchange charges**. The
Minervini runs add them, because they follow the app's written Minervini
backtest specification (`backtesting/spec.py` `COST_BPS`). Adding 0.24% per round trip (buy and sell) lowers the India
chart-pattern expectancy from +0.14R to about +0.10R. The same extra 0.24%
would take the US volume breakout (+0.04R) and Minervini (+0.04R) to zero or
just below. **A small edge can vanish with one more realistic cost
assumption.** Donchian barely notices. Costs take about the same small slice
of R from every trade, and a large expectancy has room for them.

Halve the stop distance and the same cost doubles in R. Illiquid stocks cost
more again: the Minervini specification doubles slippage for stocks trading
less than ₹25 crore / $25 million a day.

## 8. The app's strategies side by side

Each row is the strategy's most recent full-history run at its current version.
(For India Minervini, the latest run is the previous version, v1.5.) Closed
trades only. R is net of modelled costs. CAGR and drawdown come from the run's
equity curve.

| Strategy | Market | Version | Period | Trades | Win % | Avg win | Avg loss | Expectancy | CAGR (benchmark) | Max drawdown |
|---|---|---|---|---|---|---|---|---|---|---|
| Minervini SEPA | US | 1.6 | 2010–2026 | 551 | 27.8% | +1.94R | −0.68R | +0.04R | 0.7% (12.1%) | −43.5% |
| Minervini SEPA | India | 1.5 | 2010–2026 | 192 | 19.8% | +2.10R | −0.45R | +0.05R | 0.5% (10.1%) | −16.1% |
| Volume breakout | US | 1.1 | 2013–2026 | 703 | 34.3% | +2.14R | −1.05R | +0.04R | 2.2% (12.8%) | −29.7% |
| Trend pullback | US | 1.1 | 2013–2026 | 863 | 26.7% | +2.93R | −1.08R | −0.01R | 1.8% (12.8%) | −46.5% |
| Trend pullback | India | 1.1 | 2013–2026 | 347 | 29.7% | +2.92R | −1.07R | +0.12R | 2.3% (11.7%) | −32.1% |
| Donchian channel | US | 1.1 | 2013–2026 | 496 | 28.6% | +4.13R | −0.98R | +0.49R | 6.5% (12.8%) | −49.3% |
| Donchian channel | India | 1.1 | 2013–2026 | 437 | 27.2% | +4.02R | −0.93R | +0.42R | 7.7% (11.7%) | −44.2% |
| Chart patterns | India | 1.5 | 2013–2026 | 515 | 32.0% | +2.68R | −1.05R | +0.14R | 3.6% (11.7%) | −27.8% |

Read it honestly:

- **None of these runs beat simply holding the benchmark index.** Half had
  deeper drawdowns than it (US −34.1%, India −38.3% over the same years). A
  positive expectancy is necessary, not sufficient. It has to be large enough,
  come often enough and survive costs.
- **Only Donchian's expectancy is clearly above zero**, given its sample size
  (§5). The others are within two standard errors of zero.
- **These are backtests.** The universe is today's listed names, so
  survivorship bias flatters it. Earnings dates are not enforced. Fills come
  from daily bars. Costs are modelled, not paid (`backtesting/backtest.py`,
  `portfolio_sim.py`). Live trading adds hesitation, missed fills and bent
  rules, which usually lower the number. Treat a backtest as an upper limit on
  what the rules can do.
- The *Backtests* tab of each strategy's page groups runs by version. A run at
  an older version does not reflect the current rules.

## 9. What the trader does

1. **Write the stop before the entry.** R does not exist without it. Record
   entry, initial stop and exit for every trade.
2. **Compute R for every closed trade**, including the scratches and the
   gaps. The Notes page's *Trade plan* template has a "Size / risk" line. The
   *Trade review* template is the place for the R result.
3. **Review by setup, not in total.** Tag each trade with its setup
   (breakout, pullback, VCP pivot…). After 30–50 trades per setup, compare
   win rate, average win, average loss and expectancy. Drop or fix the setup
   that drags the results down.
4. **Watch the average loss.** If it creeps past −1R, either stops are being
   moved or positions are being held through gaps. Fix that before anything
   else.
5. **Never cut your biggest winners short on purpose.** Taking profits early
   to "lock in" gains raises the win rate and lowers expectancy (§2, row three).
6. **Expect the streak.** Decide in advance that 15 losses in a row is normal.
   Decide too what size you will be trading when it comes.

## 10. What the evidence says

- **Robust:** expectancy is just an average, and the arithmetic of payoff
  ratio and break-even win rate is exact. Trend-following returns are known to
  depend on a few very large winners (the "fat right tail"). This is well
  documented: the managed-futures literature, and Covel's and Faith's accounts
  of the Turtles. It shows in every run here.
- **Robust:** losing streaks of 10–20 trades at 25–35% win rates follow from
  probability alone. Trades that move together make them longer.
- **Folklore:** that a high win rate signals a good method, or that a 3:1
  target "guarantees" profit. Neither says anything without the other half of
  the formula. And a fixed target shrinks the big wins that pay for the rest.
- **Often missed:** small samples. Expectancy from a few dozen trades has an
  error bar wider than the number itself. A backtest of hundreds of trades can
  still fail to separate a small edge from zero (§5).
- **Failure mode:** an edge that exists before costs and not after. The small
  US edges here are the size of plausible extra costs.

## 11. Checklist

- [ ] Every trade has an initial stop (so a 1R value) and, once closed, its R net of costs
- [ ] Expectancy per setup recalculated monthly; sample size noted next to it
- [ ] Average loss no worse than about −1.1R (if worse, find out why)
- [ ] Biggest winners held to the exit rule, not cut early
- [ ] Current losing streak compared with what the win rate predicts (§4); costs in R checked

## Further reading

- Van K. Tharp, *Trade Your Way to Financial Freedom* — R-multiples and
  expectancy as a trader's core numbers.
- Curtis Faith, *Way of the Turtle* — the Turtles' rules, sizing by volatility (their "N") and
  what streaks and drawdowns felt like.
- Michael Covel, *Trend Following* — the right tail and why trend followers
  lose more often than they win.
- Robert Carver, *Systematic Trading* — sample size, costs and over-fitting
  in backtests.
