# Backtesting honestly — how a test on past data can fool you

**In short**

- A backtest shows what a set of rules would have done in the one history that happened. It cannot show what they will do next.
- Try enough variants and one will look good by luck. On simulated prices with no pattern at all, the best of 100 settings beat the typical one by about 4 points a year in-sample — and by nothing afterwards.
- Look-ahead bias, survivorship bias, bad data, missing costs and optimistic fills all make a test look better than live trading will.
- Small samples and results that depend on a few years are the norm. Even a rule with a real, constant edge has losing years.
- The defences: state the idea before testing, count every variant, hold data back, and check that the result survives other periods and other markets.

This guide covers what a backtest is and the main ways it misleads. It covers trying too many variants, using information from the future, and testing only the companies that survived. It also covers bad data, costs, fills and gaps, results from one kind of market, and samples too small to mean anything. Then come the defences: holding data back, robustness checks, and a checklist to run before a test.

The demonstrations here use simulated prices, index data and one simple textbook rule. They illustrate the traps; they are not a verdict on any strategy.

---

## 1. What a backtest is — and what it is not

A **backtest** applies a fixed set of trading rules to past prices, day by day, as if you had traded them. It records each trade it would have taken, and the account value over time.

A backtest **can** show whether the rules do what you think (a bug check). It can show the *shape* of the results: win rate, size of losses, length of losing streaks. And it can show whether the rules made money in the one history that actually happened.

It **cannot** show that the rules will make money from now on. Every choice you made while looking at that history leaks into the result. The rest of this guide is about those leaks. **Treat a backtest as an upper limit**: live trading adds missed fills, hesitation and broken rules.

## 2. The assumptions inside every backtest

A portfolio backtest walks the calendar one session at a time, across all stocks together, with one pool of money. Each day it should see only data up to that day. It closes positions that hit an exit, fills waiting orders if a slot and the cash are free, and turns today's signals into orders for later days. Each detail is an assumption, and each has a cautious choice:

| Item | A cautious choice |
|---|---|
| Entry | A buy-stop order at the trigger, filled only on a **later** day whose high reaches it — never on the signal day itself |
| Gap up at entry | Filled at the open if the stock opens above the trigger (a worse price) |
| Unfilled orders | Cancelled after a set number of days, such as ten |
| Stop | Filled at the stop price, or at the open if the stock opens below it |
| Stop and target on the same day | Counted as a stop: daily bars cannot show which came first |
| Costs | Slippage on every fill (for example 0.05% per side in the US, 0.1% in India), plus commissions and taxes |
| Position size | A fixed share of equity at risk per trade, a cap per stock, and a maximum number of positions |

A **basis point** (bp) is a hundredth of a percent: 5 bp = 0.05%.

Tests also commonly leave out things a live trader does:

- **Earnings dates.** A history of past report dates is often missing, so the test holds trades through results that a live trader would avoid.
- **Changing size with volatility.** Live traders often cut risk in a volatile market; a simple test risks the same every time.
- **Sector limits.** Without one, a test can hold ten stocks from one industry.

## 3. Trying too many variants

**Overfitting** means tuning rules until they fit the past, including its random noise. Try enough variants and one will look good by luck alone. Its result then fails on new data, because the luck does not repeat.

### 3.1 A demonstration on prices with no pattern

Here is a test where the right answer is known. Simulate 300 price histories of 20 years each, as random walks: each day's change is drawn at random, with a small upward drift. No trading rule can have a real edge on such prices.

On each history, test 100 random settings of a textbook rule: own the market when a fast moving average is above a slow one, otherwise hold cash. Pick the setting that did best in the first 10 years. Then run that same setting on the next 10.

| Return against buy-and-hold, median over 300 histories | First 10 years (in-sample) | Next 10 years (out-of-sample) |
|---|---|---|
| The setting that was best in the first 10 years | +0.4% a year | −2.7% a year |
| The typical (median) setting | −3.4% a year | −2.6% a year |

In-sample, the best setting looked about 4 points a year better than the typical one, and it beat buy-and-hold. Out of sample its lead vanished: it did no better than a setting picked at random. Only 18% of the "best" settings beat buy-and-hold in the second half. (Holding cash earns nothing here, which is why the typical setting lags.)

The method: daily changes drawn from a normal distribution with a mean of 0.03% and a standard deviation of 1%. The fast average's length is drawn from 5–100 days. The slow one's is drawn from 20–300 days. Each switch costs 0.1%.

### 3.2 The same search on real indexes

Now the same search on two real indexes: 200 random settings each, chosen on one period and tested on the next. The measure is the Sharpe ratio, with cash earning nothing and the price index without dividends.

| | S&P 500 | Sensex |
|---|---|---|
| In-sample period | 1950–1987 | 1998–2011 |
| Out-of-sample period | 1988–2026 | 2012–2026 |
| Top 10 settings: Sharpe in-sample | 0.77 | 0.79 |
| Same 10 settings: Sharpe out-of-sample | 0.60 | 0.56 |
| All settings, median Sharpe out-of-sample | 0.61 | 0.49 |
| Buy-and-hold Sharpe out-of-sample | 0.59 | 0.75 |
| Out-of-sample rank of the in-sample best (of 200) | 99 | 25 |

On the S&P 500, the ten best in-sample settings ended out of sample at the median of all settings. The single best setting finished 99th of 200. On the Sensex, the top ten kept part of their lead over other settings. But 87% of all settings beat holding the index in-sample, a period that included the 2008 crash. Out of sample only 1% did.

The in-sample and out-of-sample rankings were not random: the rank correlation was about 0.4 to 0.5. Some of a setting's character carries over, such as how often it trades. But the size of the best result did not carry over.

### 3.3 What published research found

- **Bailey, Borwein, López de Prado and Zhu (2014)** showed that the best of many backtests is expected to look good even when every variant is worthless. The more variants tried, the higher the best in-sample result, so a backtest should report how many were tried.
- **Harvey, Liu and Zhu (2016)** counted hundreds of published return "factors". They argued that, given so much searching, a new one needs a t-statistic of about 3 rather than the usual 2.
- **Sullivan, Timmermann and White (1999)** tested thousands of technical trading rules on the Dow Jones index. The best rule's in-sample result survived their correction for data mining. In the following ten years it did not.
- **McLean and Pontiff (2016)** re-tested 97 published stock-return patterns. Returns were lower out of sample, and lower still after publication, as traders acted on them.

### 3.4 Count the tries, and state the reason first

The danger grows with the number of tries, so count them honestly — including the ones you threw away. Changing a liquidity floor, an exit, a filter and a sizing rule, one after another, is dozens of looks at the same years.

Adopt a variant only for a reason stated before the test, with an effect in the direction that reason predicts. A market filter, for example, is meant to cut drawdowns. If it does, that is evidence. If it instead raises the win rate a little and leaves drawdowns alone, that is probably noise.

## 4. Look-ahead bias

**Look-ahead bias** means the test uses information that did not exist yet on the day of the decision. It is the most common cause of a backtest that looks too good. Common forms:

- **Choosing stocks by today's data.** Picking the stocks to test by whether they pass a filter *today* drops every stock that trended for years but is resting now. The fix: include any stock that passed on at least one day of the test period.
- **Knowing the close at the moment of a touch.** Some rules need the day to *close* above a level. Filling such an order at the intraday touch uses information that did not exist yet. Fill at the close, or at the next open.
- **Today's industry for past dates.** Group strength rebuilt from past prices but with today's industry labels carries a small error. Companies rarely change industry, so the error is small, not zero.
- **Fundamentals as they are now.** Use each quarter's results only from its filing date. Analysts' estimates are a harder case: a stored estimate is often today's record, not what was known then.
- **Exits at the signal close.** An exit triggered by a close and filled *at that close* is slightly optimistic. In practice you would sell near the close or at the next open.

## 5. Survivorship bias

**Survivorship bias** means testing only on companies that still exist. The ones that went bankrupt, were taken over or were delisted during the test are missing. The missing ones include many of the worst losers, so the results look better than reality.

**A simulation.** Take 5,000 imaginary stocks over 10 years. Each has an expected return of 8% a year and high volatility (45% a year). A stock that falls below a tenth of its starting price is delisted, and its holders lose what is left. About 11% are delisted.

| 5,000 simulated stocks, 10 years | Average annual return |
|---|---|
| All stocks, delisted ones counted | 7.6% |
| Survivors only | 8.9% |

Testing on the survivors adds about 1.3 points a year, with no rule at all. Real studies agree. Shumway (1997) found that the main US price database was missing the final returns of many stocks delisted for poor performance. Those returns averaged about −30%. Brown, Goetzmann, Ibbotson and Ross (1992) showed how survivorship alone can create the look of skill.

Most free and low-cost data sets are lists of *today's* listed stocks. The effect is largest in small caps, where most failures happen. If you cannot get past listings, state the bias and discount the result.

**A related trap: split-adjusted prices.** Stored prices are adjusted for later splits. NVIDIA traded around $15 in 2013. After later splits, its stored price for 2013 is about $0.30–0.40. A rule of "price at least $10", read against that history, kept NVIDIA out until July 2020. Use traded value (price × volume) instead, which splits do not change.

## 6. Bad data

A backtest believes every number it is given. A few wrong prices can produce trades that never could have happened.

**A fake crash.** HEG (HEGAM.NS) closed at ₹728 on 4 September 2026. The next session it opened at ₹260 and closed at ₹272. Volume that day was about 1.6 times its 50-day average — not the heavy volume of a real collapse. It looks like a corporate action that the price source did not adjust.

```series
title: HEG (HEGAM.NS), 2026 — a 63% overnight drop on modest volume
from: 2026-07-01
to: 2026-10-13
tf: D
line: india:HEGAM.NS | HEG | log
line: india:HEGAM.NS@vol | Volume | pane2 bars
mark: 2026-09-07 | ₹728 → ₹272 overnight
caption: Volume on the day was about 1.6 times normal, not the flood a real collapse brings. A test holding the stock with a stop 8% below ₹728 would record a loss of about 8 times its planned risk.
```

The arithmetic: a stop 8% below ₹728 risks about ₹58 a share. A fill at the ₹260 open loses ₹468, about 8R. One such trade can wipe out a large share of a test's profit.

**An unadjusted special dividend.** Dr Pepper Snapple merged with Keurig in July 2018 and paid a large special cash dividend. In the stored prices, the stock (now KDP) closed at $123.66 on 9 July 2018 and opened at $20.50 the next day. Run a textbook breakout rule over US stocks and this is its worst "loss" of all: about −37R, a trade that never happened.

**Earnings per share (EPS) errors.** Some stored US EPS figures are not adjusted for splits, so the P/E (price ÷ trailing EPS) is wrong. Apple's P/E reads as low as 1.3 in April 2013. Alphabet's reads 0.95 in July 2022. Trent's sales growth for one quarter, filed in April 2023, reads about 16,300%. Any test that filters on P/E, EPS growth or sales growth would treat these as real.

Automatic checks help but miss things. A common check looks for split-shaped gaps: a one-day move close to a split ratio such as one for two. It would not catch HEG, whose ratio is about 2.7.

**What to do:** look at the worst and best trades of any test by hand. A single trade beyond −3R or +20R deserves a chart before you believe it.

## 7. Costs and slippage

Costs are small per trade and large in total. The key is to measure them in R, the trade's planned risk. Cost in R = the round-trip cost ÷ the stop distance.

| Stop distance | US, about 0.10% per round trip | India, about 0.24% per round trip |
|---|---|---|
| 2% | 0.05R | 0.12R |
| 5% | 0.02R | 0.05R |
| 8% | 0.01R | 0.03R |

The India figure includes securities transaction tax (STT), stamp duty, exchange fees and GST on brokerage, but not slippage. A rule with tight stops and a small edge can lose most of that edge to costs. Suppose a rule earns +0.10R a trade with 2% stops: Indian costs alone would take more than all of it. The full arithmetic is in [Expectancy](learn-risk-expectancy.md) §7. Taxes on gains come on top.

A second lesson: in a portfolio test, a small change in costs changes which later signals the account can afford. The trade list reshuffles, and the result can move in either direction. So re-run a test after any change to its assumptions, and do not compare runs made under different ones.

## 8. Fills and gaps

Daily bars show four prices a day. A backtest has to guess the rest. Cautious guesses — a stop and target on the same day count as a stop, and a gap fills at the open — help, but gaps still matter.

**An illustration with a textbook rule.** The rule: buy at the close when a stock first closes above its highest close of the previous 55 sessions. Place a stop two ATRs (average true range over 14 days) below the entry. Exit at the stop, or at the open if the stock opens below it, or after 60 sessions.

The sample is liquid stocks from 2010 to October 2026. In the US that means a close of at least $10 and $20 million of daily turnover. In India it means ₹100 and ₹10 crore.

| | US | India |
|---|---|---|
| Trades | 59,405 | 18,145 |
| Exits at the stop | 40,484 | 11,990 |
| … where the stock opened below the stop | 15.6% | 8.2% |
| … filled more than 1% below the stop | 7.1% | 4.5% |
| … filled more than 5% below the stop | 1.9% | 0.9% |
| … losing more than 2R | 1.6% | 0.6% |

About one stop in fourteen in the US filled more than 1% worse than planned. The worst cases were the data errors of §6. Indian stocks gapped less in this sample.

Some things daily bars still cannot show. In India a stock can lock at its lower circuit limit, with no buyers at any price. Small stocks have thin order books. And a bar cannot tell whether you would really have been at the screen. The [stops and exits guide](learn-risk-stops-exits.md) has real gap examples.

## 9. Results that come from one kind of market

**Luck alone makes lumpy years.** Simulate a rule with a real, constant edge of 40 trades a year. It wins 35% of the time. Wins are +2.5R and losses −1R, an expectancy of +0.225R a trade. Run it for 14 years, 20,000 times.

| Constant edge, 14 years, 20,000 simulations | Median result |
|---|---|
| Losing years | 3 of 14 |
| Share of the total R made in the best two years | 39% |
| A bad year (5th percentile) | −8.5R |
| A typical year | +9.0R |
| A good year (95th percentile) | +26.5R |

So even a steady edge has losing years, and two years can carry well over a third of the total.

**Real markets add regimes.** Trend-following rules earn in long, broad advances and give some back in between. The Sensex test of §3.2 shows the effect at its sharpest. Most moving-average settings beat the index in 1998–2011, a period that contained the 2008 crash. Almost none did in 2012–2026. A result that depends on one kind of market depends on whether that kind of market returns.

Check which kinds your test covers. A test that starts after 2009 contains no long bear market like the dot-com bust or the 2008 crisis. The market-level guides describe how to recognise the kind of market you are in ([the trend guide](learn-health-trend.md)).

## 10. Samples too small to mean anything

The error of an average shrinks only with the square root of the number of trades. The full treatment is in [Expectancy](learn-risk-expectancy.md) §5.

Take the same constant-edge rule, with a true expectancy of +0.225R a trade. How often does a sample of trades show a loss anyway?

| Trades in the sample | Chance the sample's average is below zero | Middle 90% of sample averages |
|---|---|---|
| 25 | 31% | −0.30R to +0.82R |
| 50 | 19% | −0.16R to +0.61R |
| 100 | 9% | −0.06R to +0.51R |
| 200 | 3% | +0.03R to +0.42R |
| 400 | 0.3% | +0.09R to +0.36R |

With 50 trades, a rule with a genuine edge shows a loss almost one time in five. With 25 trades, a sample average of +0.8R is as easy to get as −0.3R. A filter that leaves a few dozen trades cannot show a difference smaller than several tenths of an R.

Small samples hide in other places too. A test on a 500-stock sample can rank differently from the full universe. With more stocks competing for the same slots, the tie-breaking rule decides which trades are taken.

## 11. Holding data back: in-sample and out-of-sample

The basic defence against overfitting is to **hold data back**. Develop and tune the rules on one period (**in-sample**). Then test them once on a period you did not look at (**out-of-sample**). If the result holds, the rules probably found something real. If it collapses, they fitted noise.

§3 showed both outcomes. On random walks the in-sample winner's lead vanished entirely. On the indexes, part of the ranking carried over but most of the best result did not.

Three rules make a hold-out honest:

- **Decide the split before you start**, and do not look at the held-back period until the end.
- **Use it once.** If you go back and tune after seeing it, it has become in-sample data.
- **Compare like with like.** Judge the held-back result against the same rule's in-sample result and against a simple benchmark over the same dates.

**Walk-forward testing** repeats the split. Tune on, say, five years, test on the next year, move forward a year, and repeat. The joined-up test years form an out-of-sample record. Note that a backtest in which "each day sees only earlier data" is not walk-forward testing in this sense unless the rules are re-tuned on a rolling window.

## 12. Robustness checks

A real edge should survive small changes. Three checks:

**Parameter neighbourhoods.** Move each setting one step either way. A real edge fades gradually. An edge that vanishes after a small change was probably fitted.

**Sub-periods.** Split by halves, by year (§9) or by market regime. Ask whether the result needs one particular stretch.

**Both markets.** The same rule tested in the US and India is close to an independent test. Take the moving-average settings of §3.2 and run them over 1998–2026 in both markets. The rank correlation of their Sharpe ratios was 0.47. The five best settings on the S&P 500 ranked between 46th and 110th on the Sensex. A setting that is best in one market is rarely best in another.

Two more checks are covered elsewhere. Resampling the trade order shows the range of possible drawdowns ([Position sizing](learn-risk-sizing.md) §7). Chasing last year's best strategy is a bias of its own ([biases guide](learn-process-biases.md)).

## 13. Results go stale

A stored result belongs to the code and data that produced it. Both change.

- **Version your rules.** Give each set of rules a version number and a short log of what changed and why. Record the version with every result, so that two different rule sets never share a label.
- **Prove "no change".** Before tidying code that should not change behaviour, record its decisions on a fixed sample of stocks and dates. After the change it must reproduce them exactly.
- **Date every number.** Check the date and method of any stored result before quoting it. A figure measured before a bug fix is a different measurement.

## 14. What the evidence says

- **Robust:** the best of many backtests overstates the truth (Bailey et al.; Harvey, Liu and Zhu; McLean and Pontiff). In the random-walk demonstration, the best of 100 settings lost its whole lead out of sample.
- **Robust:** survivorship and look-ahead bias inflate results. A simple simulation of delistings added about 1.3 points a year.
- **Robust:** bad data creates trades that never happened. A single unadjusted corporate action produced a −37R "loss" in a textbook rule.
- **Measured here:** with tight stops, Indian trading costs alone can be 0.1R a trade or more. About one US stop in fourteen filled more than 1% worse than planned.
- **Folklore:** that a long backtest with hundreds of trades is "proven". A genuine +0.225R edge still shows a loss in 3% of 200-trade samples, and a small edge needs far more trades than that.
- **Limits of the demonstrations:** the random walks have no fat tails or volatility clusters; the index tests ignore dividends and interest on cash; the textbook rule uses today's stock lists and no costs.

## 15. Before you run a test — checklist

- [ ] Write the idea and the reason for it *before* testing. Predict the direction of the effect.
- [ ] Decide the test period, the out-of-sample period and the costs in advance. Do not look at the held-back period until the end.
- [ ] Count every variant you try, including the ones you throw away.
- [ ] Change one thing at a time, as a new version with its own result.
- [ ] Check that every input was known on the decision day: prices, industry, fundamentals (filing date), index membership.
- [ ] Use realistic costs. India: add STT, stamp duty and exchange charges.
- [ ] Open the five best and five worst trades on a chart. Look for data errors.
- [ ] Split the result by half, by year and by market. Note how much comes from the best two years.
- [ ] Compare the difference you care about with its standard error. Under two is noise.
- [ ] Compare with the benchmark and a simple baseline rule, over the same dates.
- [ ] Record the rules' version and the data date with the result. Re-run after any fix to the test code or the data.

## Further reading

- David Aronson, *Evidence-Based Technical Analysis* — data-mining bias and how
  to test trading rules properly.
- Marcos López de Prado, *Advances in Financial Machine Learning* — backtest
  overfitting, and why a backtest is not a research tool.
- David Bailey, Jonathan Borwein, Marcos López de Prado and Qiji Jim Zhu,
  "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest
  Overfitting on Out-of-Sample Performance", *Notices of the AMS* (2014).
- Campbell Harvey, Yan Liu and Heqing Zhu, "… and the Cross-Section of Expected
  Returns", *Review of Financial Studies* (2016).
- Ryan Sullivan, Allan Timmermann and Halbert White, "Data-Snooping, Technical Trading Rule
  Performance, and the Bootstrap", *Journal of Finance* (1999).
- R. David McLean and Jeffrey Pontiff, "Does Academic Research Destroy Stock Return
  Predictability?", *Journal of Finance* (2016).
- Tyler Shumway, "The Delisting Bias in CRSP Data", *Journal of Finance* (1997).
- Stephen Brown, William Goetzmann, Roger Ibbotson and Stephen Ross, "Survivorship Bias in
  Performance Studies", *Review of Financial Studies* (1992).
- Robert Pardo, *The Evaluation and Optimization of Trading Strategies* —
  walk-forward analysis.
- Robert Carver, *Systematic Trading* — costs, overfitting and how much a
  backtest can really tell you.
