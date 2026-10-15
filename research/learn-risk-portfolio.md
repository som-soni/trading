# Portfolio risk — what all your positions can lose at once

**In short**

- Open risk, or "heat", is what you would lose if every stop were hit today: the sum over all positions, as a share of the account. Ten positions at 1% each is 10% heat.
- Heat is a snapshot. It ignores open profit, gaps through stops, and the new trades you keep buying while a market falls. Real losses in a sharp decline can be several times the heat.
- Stocks in the same industry move together. In a crash, nearly all stocks do: diversification across sectors fades exactly when you need it.
- Losses need larger gains to undo. The S&P 500 took seven years to regain its 2000 high and five and a half to regain its 2007 high.
- Practical limits: total heat around 6%, two or three positions per industry, and a rule that cuts risk after a drawdown or in a weak market.

This is the last of four risk guides, after [Expectancy](learn-risk-expectancy.md), [Position sizing](learn-risk-sizing.md) and [Stops and exits](learn-risk-stops-exits.md).

---

## 1. Open risk — the "heat" of the portfolio

Take a ₹20 lakh account with four positions:

| Position | Shares | Price | Stop | At risk | % of account |
|---|---|---|---|---|---|
| A | 400 | ₹1,000 | ₹950 | ₹20,000 | 1.0% |
| B | 250 | ₹1,600 | ₹1,520 | ₹20,000 | 1.0% |
| C (stop raised to cost) | 300 | ₹1,500 | ₹1,520 | ₹0 | 0.0% |
| D | 1,000 | ₹480 | ₹460 | ₹20,000 | 1.0% |
| **Heat** | | | | **₹60,000** | **3.0%** |

For one position, the risk is (price − stop) × shares. Once the position is in profit, count from your cost instead of the price, since only your own capital is then at risk. **Open risk, or heat, is that summed over every position**, as a share of the account.

A stop at or above cost puts **zero** capital at risk, like position C. Heat is measured to where the stop is *now*, so raising stops lowers the portfolio's heat.

Heat ignores **open profit**. Position C can still give back everything above ₹1,520. Section 4 shows how much that can matter.

## 2. Why 1% per trade is not 1% total

Each trade risks 1%. With ten open, up to **10% of the account is at risk at once**. Four things push the real figure higher:

- **Equity falls, heat rises.** Each position was sized on the account's value at its entry. After a losing stretch, the same stops are a bigger share of a smaller account.
- **Gaps.** About one stop in ten fills worse than −1R, averaging around −1.5R ([stops and exits](learn-risk-stops-exits.md)). When the whole market gaps down, many stops fill worse at the same time.
- **Re-entry.** Heat is a snapshot of one day. A trader who keeps buying new breakouts during a decline keeps adding fresh risk (§4).
- **Correlation.** Ten positions that fall together behave like a few large ones (§5).

Losing streaks compound too. Ten 1% losses in a row cost 9.6% of the account. Ten 2% losses cost 18.3% ([Expectancy](learn-risk-expectancy.md) covers how often streaks happen).

## 3. How many positions at once

A trader who buys every qualifying breakout fills ten slots quickly. To see how that plays out, we ran the illustrative 55-day breakouts from the [expectancy guide](learn-risk-expectancy.md) through a portfolio of at most ten positions. When several stocks broke out on the same day, it picked among them at random.

That portfolio was full on 92% of days in the US and 76% in India. On a typical day it held three positions in its largest sector. On more than a quarter of days it held four or more in one sector. At its most concentrated it held eight US positions, or nine Indian ones, in a single sector.

Breakouts come in waves from the strongest groups ([sector and group strength](learn-sectors-groups.md)). So a portfolio that simply buys leaders becomes concentrated when one theme is popular. With only 11 broad sectors, ten positions also share sectors by chance alone.

A selective method that waits for rare setups rarely fills all its slots, and runs with low heat. A method that is always in the market runs near its maximum heat most of the time. Know which kind you are running before you set the limits.

## 4. Heat is a snapshot — the 2020 example

```series
title: The S&P 500 ETF, February–April 2020
from: 2020-01-02
to: 2020-04-30
tf: D
line: us:SPY | SPY
band: 2020-02-19 2020-03-23 | −34% in 23 sessions
caption: On 19 February 2020, 753 illustrative breakout trades were open in US stocks, on average 2.9R in profit. By 23 March, 747 of them had closed, averaging +0.07R. Almost every new breakout bought in between was stopped out.
```

On 19 February 2020 the S&P 500 closed at a record. In the illustrative breakout trades, 753 US positions were open that day. Most were winners: 88% were in profit, by an average of 2.9R.

By 23 March, 747 of them had closed. Half ended on their initial stop. On average they closed at +0.07R, so each had given back about 2.8R of open profit. A heat figure measured from cost to stop counted none of that profit as being at risk.

Meanwhile, 105 new breakouts triggered between 20 February and 23 March. Almost all of them (99%) were stopped out, averaging −1.06R. A trader who kept refilling empty slots kept adding fresh risk all the way down.

The lesson: **a heat limit bounds what current positions can lose from their cost.** It does not protect open profit. Nor does it stop you buying new positions as old ones are stopped out in a falling market. That needs a rule about *new* risk (§8).

## 5. Correlation — positions that move together

Coca-Cola and PepsiCo share customers, costs and shareholders, so their prices tend to move together. A bank and a software company share far less. **Correlation** measures how closely two return series move together: 1 means in lockstep, 0 means no relation.

We measured it on market data. At each quarter-end from 2012 to 2025, we took the liquid stocks in each market and measured every pair's correlation of daily returns over the prior 60 sessions:

| Average correlation of daily returns | US | India |
|---|---|---|
| Same industry | 0.44 | 0.32 |
| Same sector, different industry | 0.34 | 0.25 |
| Different sectors | 0.25 | 0.21 |
| Different sectors, calm market (60 sessions to Dec 2017) | 0.07 | 0.11 |
| Different sectors, crash (60 sessions to Mar 2020) | 0.56 | 0.47 |

> **Method.** Stocks with a close of at least $5 / ₹20 and 50-day average turnover of at least $20m / ₹10 crore, with a full 60 sessions of prices; about 1,100 US and 280 Indian stocks per date. Sectors and industries use today's classification. Today's listed companies only.

Two stocks in the same industry moved more closely than two in different sectors: in the US, nearly twice as closely. Three positions in one industry are closer to one large position than to three independent ones.

The crash rows matter most. In the calm of late 2017, stocks in different sectors barely moved together. In the 60 sessions to March 2020, their average correlation jumped to 0.56 in the US. **Diversification across sectors fades exactly when markets fall hardest.**

## 6. Market-wide drops hit every long at once

The biggest correlation is with the market itself. A portfolio that only buys (never sells short) is one bet on the market, whatever its sectors.

Stop-outs bunch together when the market falls. In the illustrative breakout trades, a typical week saw 29 US stop-outs and 8 Indian ones. The busiest weeks saw more than ten times as many:

| Weeks with the most illustrative stop-outs | US | India |
|---|---|---|
| 1st | Week of 8 Jun 2020 (378) | Week of 11 Sep 2023 (144) |
| 2nd | Week of 24 Feb 2020 (370) | Week of 3 Jun 2024 (139) |
| 3rd | Week of 5 Feb 2018 (311) | Week of 23 Oct 2023 (125) |
| 4th | Week of 25 Jan 2021 (305) | Week of 11 Mar 2024 (113) |

The Indian list leans to recent years, because many more Indian stocks have become liquid since 2020.

Weak markets are also more violent. Both indexes spent about two-thirds of their days above the 200-day average. The other third produced most of the large falls:

| Days that started… | S&P 500 above its 200-day | S&P 500 below | Nifty 50 above its 200-day | Nifty 50 below |
|---|---|---|---|---|
| Share of days | 68% | 32% | 71% | 29% |
| Annualised volatility | 14.7% | 25.7% | 15.3% | 27.3% |
| Days down more than 2% | 2.0% | 6.9% | 2.0% | 8.1% |
| Share of all days down more than 2% | 38% | 62% | 38% | 62% |

> **Method.** Daily closes; S&P 500 price index from October 1928, Nifty 50 from July 2008, both to October 2026. "Above" means the previous close was above its 200-day simple average.

So when the index falls, spreading across sectors helps less than it looks. The defence is **less exposure when the market is weak**. The market's trend ([the trend guide](learn-health-trend.md)) and breadth ([breadth](learn-health-breadth.md)) tell you when; [regime filters](learn-strat-regime-filters.md) turn that into rules.

## 7. Drawdowns and the arithmetic of recovery

A loss needs a larger gain to undo:

| Drawdown | Gain needed | Years to recover at 10% a year |
|---|---|---|
| −10% | +11% | 1.1 |
| −20% | +25% | 2.3 |
| −30% | +43% | 3.7 |
| −40% | +67% | 5.4 |
| −50% | +100% | 7.3 |
| −60% | +150% | 9.6 |

```series
title: The S&P 500 and its distance below its record, 2000–2014
from: 2000-01-01
to: 2014-12-31
tf: W
line: us:SP500_PRICE_LONG | S&P 500 (price) | log
line: us:SP500_PRICE_LONG@dd | % below its record | pane2 zero
band: 2000-03-24 2007-05-30 | 7 years to regain the 2000 high
band: 2007-10-09 2013-03-28 | 5½ years to regain the 2007 high
caption: −49% by October 2002 and −57% by March 2009 — each needed a doubling or more to recover. The index sat below its 2000 high for most of 13 years.
```

The long history is in [the trend guide](learn-health-trend.md): the 1929 high was not regained until 1954. In India, the Nifty 50 fell 60% from January to October 2008. It first closed back above its high in November 2010. The 38% fall of 2020 was regained in about ten months.

```series
title: The Nifty 50's distance below its record, 2008–2015
from: 2007-09-17
to: 2015-12-31
tf: W
line: india:NIFTY50@dd | Nifty 50, % below its record | zero
band: 2008-01-08 2010-11-09 | below the January 2008 high
caption: −60% at the October 2008 low. It took almost three years to get back, and the high did not hold for long.
```

**Years below the previous peak are normal**, for indexes and for traders. A drawdown rule (§10) is about staying able to follow your method through them.

## 8. Cutting exposure after losses or in weak markets

Three common rules manage exposure for the whole portfolio:

- **Progressive exposure** (Minervini's term): halve the risk per trade during a losing stretch, for example while the last ten closed trades are net negative, and restore it once they turn positive.
- **A market filter**: take no new trades while the index is below its 200-day average, or while its 50-day average is below its 200-day.
- **A drawdown rule**: cut risk when the account is a set distance below its peak, and stop opening trades if the fall deepens.

The [sizing guide](learn-risk-sizing.md) §9 simulates the first. Cutting size after losses made drawdowns shallower but cost some growth. The cost was smaller when results came in clusters, as they do in real markets.

Published research points the same way for the second:

- **Trend filters on an index.** Mebane Faber (2007) tested a simple rule: hold the S&P 500 only while it is above its 10-month average, otherwise hold cash. Over the twentieth century it gave returns similar to buy-and-hold with much smaller drawdowns.
- **Volatility scaling.** Moreira and Muir (2017) showed that cutting exposure when recent volatility is high, and raising it when volatility is low, improved risk-adjusted returns for the stock market and several factor portfolios.
- **Momentum crashes.** Daniel and Moskowitz (2016) found that momentum strategies suffer their worst losses in turbulent markets after a fall, when the market suddenly rebounds. Barroso and Santa-Clara (2015) showed that scaling momentum exposure down when its own volatility rises greatly reduced those crashes.

None of this says a filter improves each trade. On the illustrative breakouts, trades taken while the index was below its 200-day did about as well on average as the rest. The case for cutting exposure is about losses that arrive together (§4, §6), not about the average trade.

**Adding exposure after wins** is the mirror rule: risk somewhat more, or allow an extra position, while recent trades are working. It is common practitioner advice. Its danger is that a winning streak often ends in exactly the market turn that hits every position at once.

## 9. Cash is a position

Holding no stocks is a position too. It has a known return (the cash rate) and no drawdown.

A method that finds nothing to buy is telling you something. In a weak market, its rules are saying the odds are poor. Make each trade earn its way out of cash; do not buy something just to be invested.

## 10. What a trader does

1. **Set a heat limit**, for example **6%** of the account at risk across all positions. New trades wait while you are at the limit; raising stops frees room.
2. **Set a concentration limit**, for example no more than **two or three positions per industry group** and about **a third of the account in one sector**. Count industries, not just sectors: same-industry pairs moved much more closely than different-sector pairs.
3. **Set a drawdown rule**, for example: at **−10% from the equity peak, halve the risk per trade; at −20%, stop opening trades** and review. Restore size after wins, not after a calendar date.
4. **Let the market set exposure**: fewer and smaller positions below the 200-day or on weak breadth; no new risk the day before a big event.
5. **Recompute heat each week**: (lower of price and cost − stop) × shares, summed over positions, against today's equity.
6. **Watch open profit, not just heat.** When several winners are far above their stops, a sharp market fall can take back much more than the heat figure shows.

## 11. What the evidence says

- **Robust:** losses compound against you (the recovery table is arithmetic). Stocks in one industry are correlated. Market declines hit all long positions.
- **Robust:** correlations rise sharply in crashes. In the measurements here, the correlation between stocks in different sectors went from under 0.1 in a calm market to about 0.5 in March 2020.
- **Robust:** markets below their 200-day average have been far more volatile, and most large down days started there.
- **Published evidence:** trend filters and volatility scaling have reduced drawdowns on indexes and factor portfolios (Faber; Moreira and Muir; Barroso and Santa-Clara). They change the path more than the long-run return.
- **Not shown:** that a particular heat limit, sector cap or drawdown rule is best. The thresholds in §10 are common practice, not optimised.
- **Limits:** the illustrative trades and correlations use today's listed companies and today's sector classification. The breakout trades have no costs and overlap heavily in time.

## 12. Checklist

- [ ] Heat this week: Σ (lower of price and cost − stop) × shares ÷ equity — under the limit?
- [ ] Positions per industry group and per sector — any over the limit?
- [ ] Equity against its peak — has the drawdown rule changed my risk per trade?
- [ ] Market regime and breadth: is this a week for new risk at all?
- [ ] Any event (results, CPI, Fed, RBI, Budget) where several holdings gap together?
- [ ] Cash: am I holding it on purpose?

## Further reading

- Van K. Tharp, *Trade Your Way to Financial Freedom* — position sizing and total portfolio risk in R.
- Mark Minervini, *Think & Trade Like a Champion* — progressive exposure: smaller after losses, larger after wins.
- William O'Neil, *How to Make Money in Stocks* — moving to cash when the market turns.
- Mebane Faber, "A Quantitative Approach to Tactical Asset Allocation", *Journal of Wealth Management* (2007).
- Alan Moreira and Tyler Muir, "Volatility-Managed Portfolios", *Journal of Finance* (2017).
- Kent Daniel and Tobias Moskowitz, "Momentum Crashes", *Journal of Financial Economics* (2016).
- Pedro Barroso and Pedro Santa-Clara, "Momentum Has Its Moments", *Journal of Financial Economics* (2015).
