# Strategies — the map

**In short**
- A trading strategy is a complete set of rules you can test: what to trade, when to enter, how much to buy, and when to get out.
- The guides group strategies into nine families, from slow trend following to intraday trading, plus a family on building and combining them.
- The two big ideas are opposites. Trend and momentum strategies bet that moves continue; mean-reversion strategies bet that stretched moves snap back.
- Choose by timeframe, temperament, the market you are in, your capital and, in India, costs and tax.
- Every strategy guide uses the same ten sections, so you can compare them and build your own version from any of them.

## 1. What a strategy is

Here is one strategy, written out in full.

| Question | Rule |
|---|---|
| What? | Indian stocks with a median daily turnover of at least ₹10 crore and a price of at least ₹50 |
| When in? | The day the close is above the 50-day average, the 50-day is above the 200-day, and the 200-day is rising; buy at the next open |
| How much? | Risk 1% of the account; shares = 1% of the account ÷ (entry − stop), capped at 20% of the account |
| Where is it wrong? | Initial stop at the entry minus 3 times the 20-day average true range |
| When out? | After two closes below the 50-day average; sell at the next open |

Every line is a condition a computer could check. Two traders given this table would take the same trades. That is the test of a strategy: **if two people can read your rules and disagree about a trade, you do not have a strategy yet.**

A view ("banks look cheap"), a pattern ("a cup with handle") or an indicator ("RSI is oversold") is not a strategy. Each is at most one part of one: a reason to look, or a setup. A strategy must also say how much to buy and when to leave. Those two answers usually matter more for the result than the entry.

```series
title: Trent, 2023–2024 — one stock, three ways in
from: 2023-01-01
to: 2024-12-31
line: india:TRENT.NS | Trent | log
line: india:TRENT.NS@sma50 | 50-day average
line: india:TRENT.NS@vol | Volume | pane2 bars
mark: 2023-05-16 | trend filter turns on
mark: 2023-06-02 | breakout to a new high
mark: 2023-10-26 | pullback to the 50-day
mark: 2024-10-28 | trend exit
caption: A trend follower, a breakout trader and a pullback buyer could all own this advance, each entering at a different point.
```

The chart shows why families overlap. The same advance in Trent could be bought by a trend rule in May 2023, by a breakout rule in June, or on a pullback to the 50-day in October. The families differ in **where** they enter and **how** they exit, and so in how often they win and how much.

The parts of a strategy, in the order a trade meets them:

1. **Universe** — which instruments it may trade, and the liquidity and price floors.
2. **Regime** — whether the market's condition allows trading at all.
3. **Setup** — the condition that makes a stock a candidate.
4. **Entry** — the exact trigger and order type.
5. **Initial stop** — the price that proves the idea wrong.
6. **Size** — how many shares, decided by the stop and the risk per trade.
7. **Exits** — the target, the trailing stop, the time stop, the invalidation.
8. **Management** — what you do while the trade is open, and what you never do.

[Expectancy](learn-risk-expectancy.md), [position sizing](learn-risk-sizing.md) and [stops and exits](learn-risk-stops-exits.md) cover steps 5 to 7 in general. The strategy guides apply them to each method.

## 2. The families

### A. Trend following

Trend followers buy what is already rising and hold until the trend breaks. They do not try to buy low. They win rarely, maybe one trade in three, but their winners are many times their losers. They need patience through long losing streaks and a market that makes long moves.

- [Moving-average trend following](learn-strat-ma-trend.md) — hold while the price is above a rising average; Faber's 10-month rule on indices.
- [Channel breakout](learn-strat-channel-breakout.md) — the Donchian and Turtle rules: buy a 55-day high, sell a 20-day low.
- [Stage analysis](learn-strat-stage-analysis.md) — Weinstein's Stage 2 breakouts above a rising 30-week line.

### B. Breakouts from a base

These strategies buy a stock as it leaves a period of tight, sideways trading, usually near a new high. The base is where sellers have been absorbed; the breakout is the moment demand wins. Entries are precise and stops are close, so the risk per trade is small. Most attempts fail quickly, and the method depends on cutting those failures at once.

- [CAN SLIM breakouts](learn-strat-canslim-breakout.md) — O'Neil's leaders with strong earnings, bought from named bases.
- [SEPA and the VCP](learn-strat-vcp-sepa.md) — Minervini's trend template and volatility contraction.
- [Darvas boxes](learn-strat-darvas.md) — buying the break of a box at new highs.
- [Flags and high tight flags](learn-strat-flags.md) — buying the short pause after a fast move.

### C. Pullbacks

Pullback traders also want an uptrend, but they buy a dip inside it instead of a new high. They get a better price and a closer stop, at the risk that the dip becomes a reversal. The win rate tends to be higher than for breakouts, and the winners smaller.

- [Pullback to a moving average](learn-strat-pullback-ma.md) — buying the 10-, 21- or 50-day line in a trend.
- [Pullback to support](learn-strat-pullback-support.md) — buying the retest of a broken level.
- [Retracements](learn-strat-retracements.md) — Fibonacci levels and measured moves, tested honestly.

### D. Momentum and relative strength

These strategies rank many stocks or assets and hold the strongest. They rebalance on a schedule, often monthly. Momentum is one of the best-documented effects in finance. It also has sharp crashes, usually when a falling market suddenly rebounds.

- [Cross-sectional momentum](learn-strat-xs-momentum.md) — rank the market, hold the top, rotate monthly.
- [Dual momentum](learn-strat-dual-momentum.md) — own the strongest asset, and step aside when nothing beats cash.
- [Sector rotation](learn-strat-sector-rotation.md) — hold the strongest sectors and move when leadership changes.
- [Relative-strength leaders](learn-strat-rs-leaders.md) — the strongest stocks in the strongest groups, bought after a correction.

### E. Event-driven

Event traders act on a known piece of news: quarterly results, an index change, a corporate action. The edge comes from how slowly or how strongly investors react. Results days in India can move a stock 10% or more, so event trades carry gap risk in both directions.

- [Earnings gaps](learn-strat-earnings-gaps.md) — buying the big results-day gap.
- [Post-earnings drift](learn-strat-pead.md) — trading the slow reaction to a results surprise.
- [Index changes and corporate news](learn-strat-index-news-events.md) — trading the event calendar.

### F. Mean reversion

Mean-reversion traders buy a short, sharp fall and sell the bounce. They bet that the move was overdone. They win often, perhaps two trades in three, but their losses can be large when the fall turns out to be news. They hold for days, not months, and work best on broad indices and large stocks.

- [RSI(2) mean reversion](learn-strat-rsi2.md) — buying a two- to five-day dip in an uptrend.
- [Bollinger band reversion](learn-strat-bollinger-reversion.md) — buying the lower band in a range.
- [Gap fills](learn-strat-gap-fills.md) — trading the price's return towards the previous close.

### G. Reversals and the short side

These strategies profit when a move fails, or when a stock falls. Shorting is harder than buying: losses are not capped, borrowing costs money, and in India a cash short must be closed the same day. Swing shorts in India need stock futures or options.

- [Failed breakouts](learn-strat-failed-breakouts.md) — when a breakout turns into a sell signal.
- [Shorting Stage 4](learn-strat-stage4-shorts.md) — selling a stock that is already falling.
- [Short squeezes and bear-market rallies](learn-strat-squeezes-bear-rallies.md) — the sharp rises inside a decline.

### H. Intraday

Intraday strategies open and close within one session. They need a live screen, fast execution and very low costs. Daily data cannot test them properly, so their guides use illustrative tables for the mechanics. Most retail intraday traders in India lose money, according to studies by SEBI, the Indian market regulator.

- [Opening-range breakout](learn-strat-orb.md) — trading the first decisive move of the day.
- [VWAP strategies](learn-strat-vwap.md) — trading around the day's volume-weighted average price.
- [Intraday momentum](learn-strat-intraday-momentum.md) — when the morning predicts the afternoon.

### Futures and options

Strategies that use futures and options (hedging, selling premium, spreads, swing shorts in India) have their own section. See the Futures & options section.

### J. Building and combining

The last family is about turning ideas into a working system. It covers writing a strategy down precisely, running several at once, and deciding when to trade at all.

- [Writing a strategy specification](learn-strat-spec.md) — every rule as a testable condition.
- [Combining strategies](learn-strat-combining.md) — several methods in one account, and how they offset each other.
- [Regime filters](learn-strat-regime-filters.md) — trend, breadth and volatility filters on top of any strategy.

## 3. How the families relate

### Trend against mean reversion

The deepest split is about what a move means. A trend follower sees a new high as evidence that the move will continue. A mean-reversion trader sees a fall of three days as evidence that it will reverse. Both can be right, on different timeframes.

Over a few days, prices of large stocks and indices tend to reverse a little. Over months, they tend to continue.

| Feature | Trend, breakout, momentum (A, B, D) | Mean reversion (F) |
|---|---|---|
| Bet | The move continues | The move reverses |
| Typical holding period | Weeks to months | Days |
| Win rate | Low, often 30%–45% | High, often 60%–75% |
| Average win against average loss | Large wins, small losses | Small wins, occasional large losses |
| Worst market | Sideways, choppy | Strong one-way trend, or a crash |
| Main risk | Long losing streaks | A rare, very large loss |
| What breaks the trader | Boredom and doubt after many small losses | One large loss after many small wins |

Because their worst markets differ, the two styles can offset each other in one account. [Combining strategies](learn-strat-combining.md) covers how.

### Pullbacks and events sit in between

Pullback strategies (C) need a trend but buy a short reversal inside it. They mix both ideas. Event strategies (E) can go either way: drift after results is a continuation, a gap fill is a reversal.

### Long against short

Most of these guides are long-only, because stocks rise over time and buying is simpler. The short side (G) is a separate skill. Falling markets are faster and more volatile than rising ones, and rallies inside a decline are violent. In India the instruments are different too: a swing short needs futures or options.

### Timeframes nest

A weekly trend, a daily setup and an intraday entry can belong to one trade. Many traders read the trend on a weekly chart, find the setup on a daily one, and time the entry on the open. A regime filter (J) sits on top of all of them.

## 4. How to choose

### Timeframe

| Style | Holding period | Time needed | Families |
|---|---|---|---|
| Intraday | Minutes to hours | Market hours, every day | H |
| Swing | Days to a few weeks | An hour after the close | B, C, E, F |
| Position | Weeks to months | A few hours each week | A, D, B |
| Rotation | Months | A few hours each month | D |

Choose the timeframe your life allows. A swing strategy run by someone who checks prices only at weekends will not be run as tested.

### Temperament

Look at the win rate you can live with. Trend following may lose eight trades out of ten in a bad stretch. Mean reversion may win nine and then give it all back in one. Neither is better in principle.

The better one is the one you will follow on its worst day. [Trading biases](learn-process-biases.md) covers why this is harder than it sounds.

### Market regime

Some families need a trending market (A, B, D); some prefer a range (F). In a falling market, long breakouts fail more often, while short-side strategies (G) come into their own. Read the market first: [the index trend](learn-health-trend.md), [breadth](learn-health-breadth.md) and [volatility](learn-health-volatility.md). Then decide whether to trade, and at what size, with [regime filters](learn-strat-regime-filters.md).

### Capital

Small accounts face fixed costs and lot sizes. In India, a stock futures lot is often worth several lakh rupees, too large for a small account. A strategy that holds ten positions at 1% risk each needs enough capital for each position to be worth trading. Start with fewer positions and longer timeframes if the account is small.

### Costs and tax in India

Costs rise with turnover, and in India they are not small. Approximate costs per round trip, before slippage:

| Trade type | Main charges | Approximate cost per round trip |
|---|---|---|
| Delivery (swing and position) | STT 0.1% each side, stamp duty 0.015% on the buy, exchange charges, GST, DP charge | About 0.25% |
| Intraday equity | STT 0.025% on the sell, stamp duty 0.003% on the buy, exchange charges, brokerage | About 0.05%–0.1% |
| US stocks | Usually no commission; small regulatory fees on sales | Mostly slippage |

Slippage adds 0.1% to 0.3% per side on liquid stocks and more on gaps. The yearly drag depends on how often you trade:

| Round trips per position slot per year | Cost per round trip | Yearly drag on that slot |
|---|---|---|
| 2 (position trading) | 0.5% | About 1% |
| 12 (swing trading) | 0.5% | About 6% |
| 50 (short swing trading) | 0.5% | About 25% |

The table is illustrative. A short-term strategy needs a much larger edge per trade just to cover costs. Tax matters too. Equity gains on holdings of up to 12 months are short-term and taxed at a higher rate than long-term gains, and intraday profits are taxed as business income. Check the current rates before you build.

## 5. How to read the strategy guides

Every strategy guide has the same sections, in the same order:

| Section | What it gives you |
|---|---|
| In short | The 30-second version |
| 1. The idea | A real chart, why it can work, and who is on the other side |
| 2. When it works and when it doesn't | Market conditions, stock types, India and US notes |
| 3. The rules | Universe, setup, entry, initial stop, exits, size and management, each a testable condition |
| 4. The parameters | Every number in the rules, with a typical range and how sensitive it is |
| 5. Variations | How named practitioners and researchers do it differently |
| 6. Worked examples | Real cases, at least one Indian and at least one failure, step by step |
| 7. Common mistakes | What usually goes wrong in practice |
| 8. What the evidence says | Published research and event studies on stored data, with caveats |
| 9. Building and testing it yourself | Data, look-ahead traps, survivorship, costs, over-fitting, what to report |
| 10. Checklist | The pre-trade checklist |

Three habits make them more useful:

1. **Read the rules as a draft, not a recipe.** The parameters table tells you what you can change. The worked examples show what each rule does on a real chart.
2. **Read the failures as carefully as the successes.** Each guide includes at least one losing example. It shows the loss the strategy is designed to accept.
3. **Treat event studies as evidence about the idea, not a forecast of returns.** They measure what happened after a signal on average. They are not a backtest of the full strategy with costs. That test is yours to run, and [backtesting honestly](learn-test-backtesting.md) explains how.

## 6. A path through the guides

If you are new to systematic trading, a sensible order is:

1. [Moving-average trend following](learn-strat-ma-trend.md) — the simplest complete strategy.
2. [Regime filters](learn-strat-regime-filters.md) — when to trade at all.
3. One breakout guide and one pullback guide, such as [CAN SLIM](learn-strat-canslim-breakout.md) and [pullback to a moving average](learn-strat-pullback-ma.md).
4. [RSI(2) mean reversion](learn-strat-rsi2.md) — the opposite idea.
5. [Writing a strategy specification](learn-strat-spec.md) and [combining strategies](learn-strat-combining.md).

Before you trade any of them with real money:

- Write the rules down as in §1, with every number named.
- Test them on data you did not use to design them, with costs.
- Trade them at small size for a few months and keep a [trade journal](learn-process-journal.md).
- Decide in advance what result would make you stop.

## Further reading

- Robert Carver, *Systematic Trading* (Harriman House, 2015).
- Ernest Chan, *Quantitative Trading* (Wiley, 2008; second edition 2021).
- Van K. Tharp, *Trade Your Way to Financial Freedom* (McGraw-Hill, 1998).
- Jack Schwager, *Market Wizards* (New York Institute of Finance, 1989).
- Andreas Clenow, *Stocks on the Move* (2015).
- Larry Harris, *Trading and Exchanges* (Oxford University Press, 2003).
- Related guides: [your trading plan](learn-process-plan.md), [expectancy](learn-risk-expectancy.md), [portfolio risk](learn-risk-portfolio.md), [reading a backtest](learn-test-reading.md).
