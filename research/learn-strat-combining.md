# Choosing and combining strategies — what to run, when, and with how much

**In short**

- Each strategy has market conditions it suits. Trend and breakout strategies need rising markets; mean reversion does better in choppy ones; shorts need falling ones. No single strategy works in all of them.
- Two strategies help each other only if their results are not closely correlated. Many that look different are the same bet: several long-only momentum strategies all lose together in a sell-off.
- Correlations rise in a crash. In early 2020, US sector funds that normally moved partly apart moved almost as one.
- Split capital by risk, not by rupees or dollars, and set a total risk limit for all strategies together.
- Start with one strategy, add a second only once the first runs smoothly, and pick the second because it does well when the first does badly.

## 1. The idea

In 2019 the nine main US sector funds (technology, financials, energy and so on) had an average daily correlation with each other of 0.54. They moved together, but only partly. From 20 February to 30 April 2020 the average was 0.88. A portfolio of ten long positions in ten sectors behaved almost like one position. Indian large caps did the same: the average correlation among twenty of the largest went from 0.23 in 2019 to 0.61 in the crash.

```series
title: Nifty 50 and India VIX — the regime changes of 2020
from: 2019-10-01
to: 2021-03-31
tf: D
line: india:NIFTY50 | Nifty 50 | log
line: india:NIFTY50@sma200 | 200-day average
line: india:INDIAVIX | India VIX | pane2
mark: 2020-03-12 | downtrend regime
mark: 2020-03-23 | low 7,610
mark: 2020-11-19 | uptrend regime again
caption: The index fell below a falling 200-day average on 12 March. It became an uptrend again only on 19 November, 68% above the March low.
```

That is the core problem of combining strategies. Diversification is what you get when your positions do not all lose at once. It is easy to have in calm markets and hard to keep in a crash, which is exactly when you need it. [The portfolio risk guide](learn-risk-portfolio.md) shows the same effect for single positions.

The answer is not to run every strategy at once. Choose a few strategies whose results differ for a reason. Size them so that no one of them can sink the account. Decide in advance what each does in each kind of market.

## 2. When it works and when it doesn't — matching strategies to regimes

A **regime** is a simple label for the state of the market. One common definition uses the index and its 200-day average:

- **Uptrend:** the index is above its 200-day average, and the average is higher than 20 sessions ago.
- **Downtrend:** the index is below its 200-day average, and the average is lower than 20 sessions ago.
- **Mixed:** anything else.

[The regime filters guide](learn-strat-regime-filters.md) covers other definitions, using breadth and volatility.

| Strategy family | Uptrend | Mixed | Downtrend | Why |
|---|---|---|---|---|
| Trend following, moving-average trend | Best | Whipsaws | Out, or short | Needs persistent moves |
| Breakouts from a base | Best | Many failures | Rarely fires; most fail | Needs buyers chasing new highs |
| Pullbacks in an uptrend | Good | Fair | Out | Needs an uptrend to pull back into |
| Momentum, relative strength | Good | Fair | Crashes in sharp rebounds | Daniel and Moskowitz (2016) |
| Mean reversion (short-term oversold) | Fair | Good | Good, with small size | Sharp drops overshoot more often when volatility is high |
| Event-driven (results gaps, drift) | Fair to good | Fair | Fair | Depends on the stock's news more than the market |
| Shorts (failed breakouts, Stage 4) | Poor | Fair | Best | Need a falling market |
| Cash | Wastes time | Fine | Often the best choice | — |

These ratings come from the logic of each strategy and from the published research cited in §8, not from a test. Treat them as starting hypotheses to test.

**What our regime study found.** The regime predicted *volatility* much better than *direction*. In the Nifty 50, daily volatility in the downtrend regime was more than twice that in the uptrend regime. But returns over the next 20 sessions were not worse in downtrends; they were slightly better, because sharp falls are often followed by sharp rebounds. The full table is in §8. Use regimes mainly to set *size* and to switch strategies whose logic needs a trend, not to forecast the market.

**India.** India has a smaller toolkit for the downtrend regime. Swing shorts need futures or options (see the Futures & options section), which exist for only about two hundred stocks. Many Indian traders therefore run long strategies plus cash, and cut size in downtrends. Mid and small caps fall harder in Indian downtrends than large caps. Delivery costs (about 0.1% STT on each side) also make a high-turnover strategy more expensive in India than in the US.

**US.** Shorting and inverse funds are easier, so a long-and-short mix is practical. Treasury bills pay interest on idle cash, which makes "cash" a real position in the plan.

## 3. The rules

These rules build a plan of one or two strategies. Every number is a parameter in §4.

### Universe and filters — which strategies to consider

- Only strategies you have specified in writing and tested. [The specification guide](learn-strat-spec.md) shows how.
- Only strategies you can actually run: data, time of day, broker, instruments. An intraday strategy needs you at the screen during market hours.
- At most two strategies in the first year.

### Setup — choosing the pair

1. **Strategy 1** is the one that fits your time, temperament and market. For most swing traders this is a trend or breakout strategy on the long side.
2. **Strategy 2** must differ from strategy 1 in at least one of: direction (long against short), holding period (days against months), regime (works in mixed or down markets), or market (India against US).
3. Measure the correlation of their monthly results in your tests. If it is above 0.5, they are mostly the same bet; choose a different second strategy.
4. Check how both did in the worst months of strategy 1. Strategy 2 should not lose heavily in the same months.

### Entry — allocating capital

- Allocate **risk**, not money. Each strategy gets a risk budget: the most it may lose on all its open trades if every stop is hit.
- Start: strategy 1 gets 100% of the budget while you learn it. Once strategy 2 starts, give it 25% of the budget at first and raise it to 50% after it has run for six months as tested.
- Total open risk for the whole account: at most 6% (the sum of all distances to stops times position sizes).

### Initial stop — limits for each strategy

- **Strategy drawdown limit:** if a strategy loses more than 1.5 times its worst drawdown in testing, stop trading it and review.
- **Account drawdown limit:** if the account is 15% below its peak, halve the risk per trade in every strategy until it recovers half the loss.

### Exits — retiring or switching a strategy

- **Regime switch:** turn off any strategy whose rules require a trend when the regime is not "uptrend". Turn it back on when the regime returns.
- **Buffer:** require the index to close 1% beyond its 200-day average, or to stay on the new side for 5 sessions, before the regime changes. This cuts whipsaws.
- **Retirement:** retire a strategy if its last 50 trades show an expectancy below zero after costs and it has also broken its drawdown limit. One bad quarter is not enough.

### Position size

- Within each strategy, use its own sizing rule (for example, 1% risk per trade).
- Scale each strategy's risk per trade by its share of the budget. A strategy with 50% of the budget risks half as much per trade as it would alone.
- In the downtrend regime, halve the risk per trade for every long strategy that stays on.

### Managing the trade

- Review each strategy monthly against its tested numbers: win rate, average R, number of trades, drawdown.
- Rebalance the risk budget once a quarter, not after every win or loss.
- Keep one journal for each strategy, so that one's results do not hide the other's. [The journal guide](learn-process-journal.md) shows what to record.
- Do not add a third strategy because the first two are in a drawdown. That is when the urge is strongest and the judgement weakest.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Strategies in year one | 1–2 | Complexity | More is harder to run well |
| Correlation ceiling | 0.5 on monthly results (0.3–0.6) | Whether two strategies are really different | Measure on test results |
| Regime average | 200-day (150–250) | Trend regime | Widely used; robust |
| Slope lookback | 20 sessions (10–40) | "Rising" average | Small effect |
| Regime buffer | 1% beyond the average, or 5 sessions (0.5–3%, 3–10 sessions) | Fewer whipsaws | Trades responsiveness for stability |
| Starting share for strategy 2 | 25% of the risk budget | Learning cost | 10–30% |
| Full share for strategy 2 | 50% after 6 months | Long-run split | Split by risk, not money |
| Total open risk | 6% of account (4–10%) | Worst case if every stop is hit | Before gaps |
| Strategy drawdown limit | 1.5× its worst tested drawdown | When to stop a strategy | 1.25–2× |
| Account drawdown trigger | 15% below peak (10–20%) | When to cut all sizes | Halve risk until half recovered |
| Downtrend size cut | Half the risk per trade | Size in high volatility | Or scale by volatility |
| Retirement test | 50 trades below zero expectancy, and drawdown limit broken | When to drop a strategy | Needs both conditions |
| Review cadence | Monthly; rebalance quarterly | Process | — |

## 5. Variations

**Equal risk (risk parity).** Give each strategy the same expected volatility of results, not the same capital. A low-volatility mean-reversion strategy then gets more capital than a high-volatility breakout strategy. This is the idea behind risk-parity funds.

**Equal weights.** DeMiguel, Garlappi and Uppal (2009) found that a simple equal split often did as well, out of sample, as carefully optimised weights, because the optimisation fitted noise. For two or three strategies, a fixed split is fine.

**Volatility targeting.** Moreira and Muir (2017) found that cutting exposure when recent volatility is high, and raising it when volatility is low, improved risk-adjusted returns for several strategies. The "halve size in downtrends" rule is a crude version of this.

**Value with momentum.** Asness, Moskowitz and Pedersen (2013) found that value and momentum strategies had negatively correlated returns across many markets. Combining them gave smoother results than either alone. It is the classic example of a good second strategy: it does well when the first does badly, for a reason.

**Trend following as the diversifier.** Hurst, Ooi and Pedersen (2017) found that trend following across futures markets tended to do well in the worst stretches for stocks. A trend strategy on indices or commodities can serve as a second strategy for a stock trader.

**Core and satellite.** Many traders keep most of the account in a low-turnover holding (an index fund, a long-term portfolio) and trade one or two strategies with the rest. The core earns the market's return while the strategies are being proven.

## 6. Worked examples

### Nifty 50, 2020 — a trend strategy switched off, a mean-reversion strategy switched on (India)

The chart is in §1. Regime dates use the definitions in §2 without a buffer.

| Date | Nifty 50 close | 200-day average | Regime | What the plan does |
|---|---|---|---|---|
| 26 Feb 2020 | 11,679 | 11,684 | Mixed | Trend strategy stops taking new trades |
| 12 Mar 2020 | 9,590 | 11,663 | Downtrend | Trend strategy off; long sizes halved; mean-reversion strategy (if run) active at half size |
| 23 Mar 2020 | 7,610 | — | Downtrend | Low of the crash |
| 17 Jul 2020 | 10,902 | 10,869 | Mixed | Trend strategy may manage open trades; no full size yet |
| 19 Nov 2020 | 12,772 | 10,721 | Uptrend | Trend strategy fully on |

The trend strategy missed the 68% rise from the low to 19 November. That is the price of a regime filter: it avoids most of the fall and misses the first part of the rise. A second strategy that buys sharp, oversold drops is active exactly in that gap. That is the case for pairing the two.

### S&P 500, 2022 — whipsaws without a buffer (US, the failure)

```series
title: S&P 500 — a regime filter flipping in early 2022
from: 2021-10-01
to: 2022-12-30
tf: D
line: us:SP500_PRICE_LONG | S&P 500 | log
line: us:SP500_PRICE_LONG@sma200 | 200-day average
mark: 2022-01-21 | mixed
mark: 2022-05-05 | downtrend
caption: Between 21 January and 5 May the regime changed 12 times, as the index crossed back and forth over a flattening average.
```

| Date | S&P 500 close | 200-day | Regime |
|---|---|---|---|
| 21 Jan 2022 | 4,398 | 4,429 | Mixed |
| 31 Jan 2022 | 4,516 | 4,437 | Uptrend |
| 11 Feb 2022 | 4,419 | 4,452 | Mixed |
| 22 Mar 2022 | 4,512 | 4,473 | Uptrend |
| 8 Apr 2022 | 4,488 | 4,493 | Mixed |
| 5 May 2022 | 4,147 | 4,490 | Downtrend |

The table shows six of the twelve changes. A plan that switched strategies on each change would have bought and sold repeatedly as the index crossed the line. Each switch costs money and attention.

The buffered rule in the §9 pseudocode keeps the old label until the index closes 1% beyond its average. With it, the regime changed once in this period: to downtrend on 5 May. It also changed only once in the Nifty's 2015. This is common. In our count of regime changes without a buffer, the busiest years were these:

| Index | Year | Regime changes |
|---|---|---|
| Nifty 50 | 2015 | 20 |
| Nifty 50 | 2018, 2019, 2022 | 16 each |
| S&P 500 | 2015 | 18 |
| S&P 500 | 2022 | 14 |

### The crash correlation — what diversification across stocks is worth (US and India)

| Period | US sector funds: average correlation | Indian large caps: average correlation |
|---|---|---|
| 2017 | 0.32 | 0.12 |
| 2019 | 0.54 | 0.23 |
| Sep–Dec 2008 | 0.81 | 0.49 |
| 20 Feb – 30 Apr 2020 | 0.88 | 0.61 |
| 2022 | 0.64 | 0.34 |

A long-only breakout strategy holding eight stocks in 2017 was well diversified. The same eight stocks in March 2020 were close to one bet. A second long-only strategy in the same stocks adds little at that moment. A short strategy, cash or a strategy in a different asset does.

## 7. Common mistakes

- **Running everything at once.** Five half-learned strategies are worse than one learned well. Errors multiply, and you cannot tell which strategy caused a loss.
- **Two names for one bet.** A breakout strategy and a momentum strategy on the same stocks are mostly the same long, trend-following bet.
- **Splitting by money, not risk.** A strategy with wide stops and volatile stocks takes most of the risk even with half the money.
- **Switching strategies after a few losses.** Each strategy has losing runs. Judge it against its tested numbers, not your last month.
- **Regime filters with no buffer.** They flip on every crossing and cost more than they save.
- **Adding a strategy to escape a drawdown.** Decide additions on a calm weekend, with a test, not during a losing run.
- **Forgetting the total.** Every strategy within its limit can still add up to too much risk.

## 8. What the evidence says

**Published research.**
- **Correlations rise in falls.** Longin and Solnik (2001) found that the correlation between national markets rises in bear markets, not in bull markets. Ang and Chen (2002) found the same asymmetry among US stock portfolios.
- **Momentum crashes.** Daniel and Moskowitz (2016) found that momentum's worst losses come in sharp rebounds after market falls, when the short side (past losers) jumps.
- **Value and momentum.** Asness, Moskowitz and Pedersen (2013) found negatively correlated returns between the two, across asset classes and countries.
- **Trend following in bad times.** Hurst, Ooi and Pedersen (2017) found trend following did well, on average, in the worst periods for a stock and bond portfolio.
- **Simple splits.** DeMiguel, Garlappi and Uppal (2009) found that equal weights were hard to beat out of sample.
- **Volatility management.** Moreira and Muir (2017) found that scaling exposure down when volatility is high improved risk-adjusted returns.

**Our event study 1 — what regimes predict.** We labelled each day by the regime in §2 and measured the index's return over the next 20 sessions and its daily volatility within the regime.

| Regime | Nifty 50, share of days | Median 20-session return | Share of 20-session periods up | Volatility (annualised) |
|---|---|---|---|---|
| Uptrend | 64% | +0.8% | 59% | 13.8% |
| Mixed | 18% | +1.6% | 67% | 22.0% |
| Downtrend | 18% | +1.3% | 59% | 31.0% |

| Regime | S&P 500, share of days | Median 20-session return | Share of 20-session periods up | Volatility (annualised) |
|---|---|---|---|---|
| Uptrend | 66% | +1.1% | 63% | 12.3% |
| Mixed | 13% | +1.6% | 65% | 20.8% |
| Downtrend | 22% | +0.4% | 53% | 22.5% |

*Method.* The Nifty data start in 2008 and the S&P data (price index) in 1960. Both end in September 2026. Regimes as defined in §2, with no buffer. Returns overlap, so the periods are not independent.

*What it shows.* The downtrend regime was far more volatile: more than twice the uptrend's volatility in India, and nearly twice in the US. Its median return was not reliably worse. Regimes are a good guide to *how much* to risk and to *which kind* of strategy can work. They are a poor forecast of direction.

**Our event study 2 — correlations in calm and crisis.** We computed the average correlation of daily returns between each pair of nine US sector funds. We did the same for twenty large Indian stocks, in the periods shown in §6. Correlations were highest in the 2008 and 2020 crashes in both markets. The Indian stocks were less correlated than the US sector funds, partly because single stocks carry more company-specific news than sector funds.

*Caveats.* The Indian list is today's large caps, chosen with hindsight. Correlations over a few months are noisy.

**What is unknown.** How your own strategies correlate. That has to be measured from your own tests and, better, your own live trades.

## 9. Building and testing it yourself

**Data.** The daily or trade-by-trade results of each strategy from its own test, on the same dates and the same account size. The index for the regime label.

**Look-ahead traps.**
- The regime on day t uses closes up to day t, and a switch takes effect on day t+1.
- Do not pick the second strategy because it did well in the first strategy's worst months *in the same test you then report*. Choose on one period, check on another.

**Survivorship.** Each strategy's test should already use point-in-time stock lists. Combining two biased tests gives a biased combination.

**Costs.** Switching strategies on and off costs trades. Count the extra entries and exits the regime filter causes, at your market's costs (India delivery: roughly 0.25–0.3% for a round trip; US: the spread and slippage).

**What to test.**
1. Each strategy alone, by regime: expectancy, number of trades and drawdown in each.
2. The correlation of monthly results between them, overall and in the worst 10% of months for the market.
3. The combined account with a fixed risk split (for example 50/50), with and without the regime switch and its buffer.
4. Total open risk over time: its average and its maximum.

**What a good test reports.** Combined drawdown against each strategy's alone, the worst month, the share of months both lost, the number of regime switches a year, and the extra costs of switching.

```
regime[t] = up   if close[t] > sma200[t] * 1.01 and sma200[t] > sma200[t-20]
            down if close[t] < sma200[t] * 0.99 and sma200[t] < sma200[t-20]
            else regime[t-1]                       # buffer: keep the old label

budget = {"trend": 0.5, "meanrev": 0.5}            # share of the risk budget
for each day t:
    for each strategy k:
        on = k.allowed_in(regime[t-1])
        risk_per_trade = base_risk * budget[k] * (0.5 if regime[t-1] == "down" else 1)
        if on: k.take_signals(t, risk_per_trade)
        k.manage_open_trades(t)
    if total_open_risk(t) > 0.06 * account: skip new trades
    if account < 0.85 * peak: base_risk = base_risk / 2   # until half the loss is recovered
```

## 10. Checklist

- [ ] I run one strategy, or two at most, each specified and tested.
- [ ] The second strategy differs in direction, holding period, regime or market, and its monthly results correlate below 0.5 with the first.
- [ ] I know which regime each strategy needs, and the regime rule has a buffer.
- [ ] Capital is split by risk; each strategy has a risk budget.
- [ ] Total open risk across all strategies is capped at 6%.
- [ ] Each strategy has a drawdown limit; the account has a size-cut trigger.
- [ ] Each strategy has its own journal and a monthly review against its tested numbers.
- [ ] I will not add a strategy during a drawdown.

## Further reading

- Clifford S. Asness, Tobias J. Moskowitz and Lasse Heje Pedersen, "Value and Momentum Everywhere", *Journal of Finance* 68 (2013).
- Brian Hurst, Yao Hua Ooi and Lasse Heje Pedersen, "A Century of Evidence on Trend-Following Investing", *Journal of Portfolio Management* 44 (2017).
- Kent Daniel and Tobias J. Moskowitz, "Momentum Crashes", *Journal of Financial Economics* 122 (2016).
- Alan Moreira and Tyler Muir, "Volatility-Managed Portfolios", *Journal of Finance* 72 (2017).
- Victor DeMiguel, Lorenzo Garlappi and Raman Uppal, "Optimal Versus Naive Diversification: How Inefficient Is the 1/N Portfolio Strategy?", *Review of Financial Studies* 22 (2009).
- François Longin and Bruno Solnik, "Extreme Correlation of International Equity Markets", *Journal of Finance* 56 (2001).
- Andrew Ang and Joseph Chen, "Asymmetric Correlations of Equity Portfolios", *Journal of Financial Economics* 63 (2002).
- Mebane T. Faber, "A Quantitative Approach to Tactical Asset Allocation", *Journal of Wealth Management* 9 (2007).
