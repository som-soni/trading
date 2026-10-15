# Reading the market's trend — is the index in an uptrend?

**In short**

- Most stocks move with the market, so check the index's trend before you look at any single stock.
- The simplest read is the index against its 50-day and 200-day moving averages, and which way those averages slope.
- Below its 200-day the S&P 500 has not reliably fallen further, but its days have been about twice as wild. Wild days are what hit a swing trader's stop.
- A 200-day rule has roughly halved the worst losses in history, at the cost of some return and many false signals (whipsaws).
- In India, read a midcap index as well as the Nifty 50: the large-company index can hide a bear market in the stocks you actually trade.

This guide covers how to read the index's direction. It uses the 50- and 200-day averages and their slope, Weinstein's stages, and how far the index is below its high. It also covers how the US and India differ. Companion guides cover [breadth](learn-health-breadth.md) (how many stocks take part), [volatility](learn-health-volatility.md) and [distribution days](learn-health-distribution.md) (heavy selling on the index).

---

## 1. Why the index comes first

Look at the S&P 500's daily history since 1950, split by where the index closed the day before. It closed above its 200-day average about 72% of the time.

| S&P 500, 1950–2026 (daily) | Prior close above its 200-day | Prior close below it |
|---|---|---|
| Share of days | about 72% | about 28% |
| Next-day return, annualised | about 11% | about 5% |
| Volatility, annualised | about 12% | about 22% |
| Days moving more than 2% | about 2 in 100 | about 10 in 100 |

Since 2000 the gap is even larger. On days below the 200-day line, volatility was about 30% and one day in five moved more than 2%. Yet the average return was *higher*. The biggest up days cluster in bear markets (24 March 2020, for one).

**Below the 200-day you are not sure to lose; you are sure of a rougher ride.** Big daily swings are exactly what knock a swing trade out at its stop.

The reason is simple. When investors pull money out of funds, the funds sell what they own, good companies included. William O'Neil's rule of thumb is that **about three in four stocks move with the general market**. That is a rule of thumb, not a measured constant.

### 1.1 Breakouts in up and down markets

Traders often say that **breakouts fail more often when the market is falling**. A breakout needs buyers to keep coming after the price clears its old high. In a falling market, every rally meets holders who want to sell as soon as they are back to what they paid.

We can test this on stored prices with a simple textbook rule. A breakout is a stock closing above its highest close of the prior 55 sessions. Each one gets a stop two ATRs below the close and a target four ATRs above, so the target is worth 2R (twice the risk).

| 55-day breakouts, 2010–2026 | US: index above 200-day | US: index below | India: index above 200-day | India: index below |
|---|---|---|---|---|
| Breakouts | 108,194 | 11,156 | 27,917 | 4,568 |
| Stop hit first | 59.7% | 56.4% | 57.4% | 52.8% |
| Target hit first | 30.8% | 26.4% | 34.0% | 33.2% |
| Average result, in R | +0.07 | +0.06 | +0.14 | +0.19 |
| Median 20-day return | +0.4% | +0.8% | +0.4% | +0.7% |

> **Method note.** Daily prices for today's US and NSE stock lists, 2010 to July 2026. One breakout per stock per 20 sessions. Liquidity: close at least $5 or ₹20, 20-day average turnover at least $5 million or ₹5 crore. The market is "up" when SPY (US) or the Nifty 50 (India) closed above its 200-day that day. A trade that hits neither level within 40 sessions is valued at its 40th close. Caveats: survivorship (today's lists leave out delisted stocks), no costs, overlapping market periods. This illustrates the market's effect on breakouts. It is not a test of any strategy.

The result does not support the saying. Breakouts in a falling market hit their stop *no more* often than breakouts in a rising one. The average result per trade was about the same in each market.

Three things explain it. First, the stop here is set in ATRs, so it is already wider when the market is wild. Second, many breakouts below the index's 200-day come late in a decline, when the strongest stocks are turning up first. Third, there were far fewer of them: about one breakout in ten in the US came with the index below its 200-day.

So the case for trading less in a downtrend rests on the rougher ride and the larger gaps, not on a lower hit rate. A rough ride means wider stops and smaller positions for the same risk.

## 2. The index against its 50- and 200-day averages

Here is the S&P 500 through three breaks of its 200-day average.

```series
title: The S&P 500 and its 200-day average, 2017–2023
from: 2017-01-01
to: 2023-12-31
line: us:SPX | S&P 500 | log
line: us:SPX@sma200 | 200-day average
line: us:SPX / us:SPX@sma200 | S&P 500 ÷ its 200-day | pane2
band: 2018-10-11 2019-02-12 | Q4 2018
band: 2020-02-27 2020-05-27 | Covid crash
band: 2022-04-08 2022-11-30 | 2022 bear market
caption: Three breaks of the 200-day. The lower pane shows how far below it the index went: about 15% in December 2018, 26% in March 2020, 17% in June 2022.
```

- **2018.** The first close below came on 11 October. The index went back and forth until early December. The low on 24 December was −19.8% from the high.
- **2020.** The break came on 27 February, when the index was already 12% off the high. In a fast crash the signal came late. The low was on 23 March (−34%), and the index was back above on 27 May.
- **2022.** The first close below came on 21 January, 8% off the 3 January record. The index then stayed below without a break from 8 April to 30 November. It closed above the line on only about 15% of 2022's sessions.

From cases like these comes the simplest read: where the index closes against its averages.

| Reading | What it says |
|---|---|
| Above a rising 50-day and a rising 200-day | Uptrend — buy breakouts, full size |
| Below the 50-day, above the 200-day | Pullback inside an uptrend — be selective, smaller |
| Below a flattening 200-day | Trend in doubt — mostly watch |
| Below a falling 200-day, 50-day under the 200-day | Downtrend — preserve capital |

### 2.1 Whipsaws — the price of a simple rule

```series
title: Whipsaw versus trend — the S&P 500 and its averages, 2015–2017
from: 2015-01-01
to: 2017-12-31
tf: D
line: us:SPX | S&P 500
line: us:SPX@sma50 | 50-day
line: us:SPX@sma200 | 200-day
caption: In 2015–16 the index crossed its 200-day 20 times and the 50-day crossed the 200-day four times. In 2017 it never touched the 200-day.
```

On daily closes the index crossed this line **20 times in 2015–16**. It crossed **not once in 2017** (nor in 2021 or 2024). A whipsaw is a signal that reverses soon after it is given. In a sideways year a 200-day rule flips every few weeks, and each flip costs a small loss.

What protection does the rule buy? Here is a crude test on the S&P 500 *price* index. It ignores dividends, interest on cash and costs. It is invested whenever the previous close was above the 200-day, and in cash otherwise.

| 1950–2026 | Buy and hold | 200-day rule |
|---|---|---|
| Annual growth (price only) | about 8.4% | about 7.6% |
| Worst drawdown | about −57% | about −28% |
| Switches | — | 452 (about six a year) |

| From 2000 | Buy and hold | 200-day rule |
|---|---|---|
| Annual growth (price only) | about 6.5% | about 4.9% |
| Worst drawdown | about −57% | about −25% |

**The 200-day is a risk filter, not a way to earn more.** It halved the worst loss, and the whipsaws cost some return.

### 2.2 Slope matters as much as position

A price above a *falling* average is a bounce, not an uptrend. The slope is today's value of the average against its value 20 sessions earlier.

The S&P 500's 200-day slope turned down on 5 May 2022. By then the index was already about 14% off its high. The slope turned up again on 5 April 2023.

A second slope signal is the cross of the two averages. The 50-day crossing below the 200-day is called a "death cross"; crossing above is a "golden cross". Here are the recent ones:

| Cross | Date | Index below its high |
|---|---|---|
| Death cross | 7 December 2018 | 10% |
| Death cross | 30 March 2020 (*a week after the low*) | 22% |
| Death cross | 14 March 2022 | 13% |
| Golden cross | 1 April 2019 | — |
| Golden cross | 9 July 2020 | — |
| Golden cross | 2 February 2023 | 13% |

**Crosses confirm a trend after the fact; they do not predict it.**

## 3. Weinstein's stages applied to the index

```series
title: Stages on the index — the S&P 500 and its 30-week line, 2021–2023
from: 2021-01-01
to: 2023-12-31
tf: W
line: us:SPX | S&P 500
line: us:SPX@sma150 | 150-day average (≈ 30 weeks)
mark: 2022-01-03 | record close
mark: 2022-10-12 | 2022 low
caption: 2021: Stage 2, not one weekly close below the line. Early 2022: Stage 3, the line flattening. Most of 2022: Stage 4. Early 2023: Stage 1 turning into 2.
```

In 2021 the index closed below its 30-week line in **none of its 53 weeks**. In 2022 it closed below in **41 of 52**. In 2023 it closed below in 4 weeks. The line here is a 30-week simple average of weekly closes.

Stan Weinstein described four stages in a stock's life, read off this 30-week moving average. He wrote them for stocks ([Bases](learn-bases.md), [Stages and trend in a stock](learn-price-stages.md)), but they work just as well on an index:

| Stage | Index above its 30-week line? | 30-week line | Trader's posture |
|---|---|---|---|
| 1 Basing | Crossing back and forth | Flat after a decline | Build the watchlist |
| 2 Advancing | Above | Rising | Full exposure |
| 3 Topping | Crossing back and forth | Flattening after an advance | Tighten, take profits, fewer new buys |
| 4 Declining | Below | Falling | Cash or very small |

Some traders use a 30-week *exponential* average instead, which weights recent weeks more. It turns a little sooner.

## 4. Higher highs and higher lows

In 2022 the S&P 500's summer rally stopped on 16 August, below the January high. That lower high was the warning. In October the index broke below the June low.

Before any average, a trend is a sequence of swings. An uptrend makes **higher highs and higher lows; a downtrend makes lower highs and lower lows.** After a sharp fall, a rally that stalls below the previous high is the first sign of Stage 4.

The reverse is the first sign of a new uptrend: a higher low, followed by a close above the last swing high. It often comes weeks before the 200-day turns. Use swings for the early read and averages for confirmation.

## 5. Drawdown depth as a regime read

```series
title: The S&P 500's distance below its record, 1928–2026
from: 1928-01-01
tf: M
line: us:SP500_PRICE_LONG@dd | % below the running record | zero
band: 1929-09-17 1954-09-22 | 25 years to regain the 1929 high
band: 2000-03-27 2013-03-28 | 2000 high regained in 2013
caption: −86% in 1932, −48% in 1974, −49% in 2002, −57% in 2009, −34% in 2020, −25% in 2022. Most of the time the index is within a few percent of a record.
```

How far the index is below its high is a blunt but honest read of the market's condition. By convention **a correction is a 10–20% fall; a bear market is a fall of 20% or more**. These are round numbers, not laws.

Counting declines between record closes gives this table. A fall inside a longer decline, such as 2011's, is not counted separately.

| Since | Corrections (10–20%) | Bear markets (20%+) |
|---|---|---|
| 1928 | 14 | 12 |
| 1950 | 13 | 11 |
| 1980 | 10 | 6 |

That is **a 10%+ decline roughly every three years since 1950**. About one in two of them went on to 20%. Four stopped just short of 20% on closing prices:

| Year | Decline (closing prices) |
|---|---|
| 1990 | −19.9% |
| 1998 | −19.3% |
| 2018 | −19.8% |
| 2025 | −18.9% |

That is why "is it officially a bear market?" is the wrong question.

| Since 1980, share of trading days | |
|---|---|
| Within 5% of a record | about half |
| At least 10% below one | about a third |
| 20% or more below one | about a sixth |

**The deeper the drawdown, the more of your watchlist is broken.** In a 10% correction, leading stocks often hold up. In a 20%+ decline they break too, and the next uptrend is usually led by *new* names.

## 6. India: the Nifty is not the market

```series
title: 2018 — the Nifty at a record while midcaps were in a bear market
from: 2017-10-01
to: 2020-01-31
line: india:NIFTY50@dd | Nifty 50, % below high | zero
line: india:MIDCAP@dd | Nifty Midcap 50, % below high
mark: 2018-08-28 | Nifty record
caption: The Nifty 50 set a record on 28 August 2018. The Midcap 50 fell 23% from January to October 2018 and 28% by August 2019.
```

The Nifty Midcap 50 peaked on 8 January 2018. While it fell, the Nifty 50 closed at a record on 28 August; its worst fall that year was about 15%. The Midcap 50 / Nifty 50 ratio lost about 30% by October 2019. The IL&FS shock (the default of a large Indian lender) is in [the liquidity guide](learn-macro-liquidity-credit.md), the midcap cycle in [the cycle guide](learn-macro-cycle.md).

The large-company index is also choppier around its line. Since 2010:

| Index | Share of days above its 200-day | Crosses of the line per year |
|---|---|---|
| Nifty 50 | about 73% | about eight |
| Nifty Midcap 50 | about 69% | — |
| S&P 500 | about 83% | about six |

**A breakout trader mostly trades mid and small companies, so read the Nifty 500 and a midcap index.** Suppose the Nifty makes highs while midcaps sit under falling 200-day lines. Then the market you actually trade is in a downtrend.

## 7. Turning the readings into a rule

A trend check can be written as a few yes/no readings for each broad index:

- close above the 50-day;
- close above the 200-day;
- **50-day rising** (above its value 10 sessions ago);
- **weekly close above a rising 30-week average**.

Add the share of stocks above their 20- and 50-day averages (see [the breadth guide](learn-health-breadth.md)). Add a volatility reading: VIX for the US, India VIX for India.

Few of these readings need to change a decision directly. Two common uses:

1. **Sizing.** Halve the risk per trade when the volatility index is high. For example, risk 1% of the account per trade normally and 0.5% when VIX is above 25 (India VIX above 20).
2. **A downgrade.** When the two main indices both close below their 50-day average, lower the grade of every new setup by one step. Keep the watchlist: a weak market is exactly when you want to know which stocks are building setups.

The downgrade switches on and off quickly. Take SPY (the S&P 500 fund) and QQQ (the Nasdaq 100 fund). Since 2010 both were below their 50-day on about 23% of sessions. That happened in seven or eight spells a year, with a median length of three sessions. **Read it as "be pickier today", not as a change in the market's condition.**

A slower filter blocks new buys while the index is below its 200-day, or while its 50-day is below its 200-day. Open positions are left alone. Some versions wait a few sessions after the index recovers before buying again. [Regime filters](learn-strat-regime-filters.md) covers these filters as part of a strategy.

## 8. What a trader does with it

### 8.1 An exposure ladder

Decide in advance how much you will have at risk in each state:

| State | Typical evidence | Exposure |
|---|---|---|
| **Full** | Index above rising 50- and 200-day, Stage 2, within ~10% of high | Normal size, normal number of positions |
| **Reduced** | Below the 50-day, or a 10% correction, 200-day still rising | Half size or half the positions; only the strongest setups |
| **Cash / minimal** | Below a falling 200-day, Stage 4, 20%+ drawdown | No new breakouts; manage exits; keep the watchlist |

Move one rung at a time. Step back up as the evidence improves. After a low, the first leading stocks to break out of sound bases are often the cycle's best trades.

### 8.2 Combine trend, breadth and volatility

- **Trend** (this guide): the index against its averages; the drawdown.
- **Breadth** ([the breadth guide](learn-health-breadth.md)): an index at highs while fewer stocks make new highs, and fewer sit above their 50-day, is a fragile trend.
- **Volatility** ([the volatility guide](learn-health-volatility.md)): when VIX or India VIX stays high, trade smaller.
- **Selling** ([the distribution-day guide](learn-health-distribution.md)): heavy-volume down days clustering near a high.

Two or three warnings together justify a rung down; one alone usually does not.

## 9. What the evidence says

- **Robust:** index trend filters have cut the worst drawdowns roughly in half, by staying out during long bear markets (Faber 2007; §2.1 agrees). Volatility below the 200-day is about double.
- **Weaker:** the case for higher returns. After whipsaws, a simple rule has usually lagged buy-and-hold.
- **Lags are built in.** In 2020 the death cross came after the low. In V-shaped markets (a sharp fall followed by a sharp recovery) the trend reads are wrong twice: late out, then late back in.
- **Breakouts and the market.** On a simple 55-day breakout rule, breakouts with the index below its 200-day did not fail more often than others (§1.1). The saying that "breakouts fail in downtrends" is not supported by this test, though it used ATR stops that widen with volatility.
- **Folklore:** that the golden or death cross predicts on its own, or that "−20%" marks a real change in the market's nature.
- **Limits of the numbers here.** The S&P 500 tests use the price index, without dividends or costs. The breakout study uses today's stock lists, so it leaves out companies that later failed and were delisted.

## 10. Checklist

- [ ] S&P 500 / Nifty 50 against rising 50- and 200-day lines? India: Nifty 500 and midcaps agree?
- [ ] 30-week line: which stage — and has it changed since last week?
- [ ] Swings: last high and last low higher or lower than the previous ones?
- [ ] Drawdown from the high: under 10%, a correction, or a bear market?
- [ ] Both main indices below their 50-day? Is VIX (or India VIX) high?
- [ ] Breadth and distribution days agree, or disagree, with the trend?
- [ ] Exposure rung for next week decided — full, reduced or cash?

## Further reading

- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — the four
  stages and the 30-week moving average.
- William O'Neil, *How to Make Money in Stocks* — the "M" in CAN SLIM: market
  direction first.
- Mark Minervini, *Trade Like a Stock Market Wizard* — why leaders and the
  market are read together, and trading smaller when the market is weak.
- Mebane Faber, "A Quantitative Approach to Tactical Asset Allocation"
  (Journal of Wealth Management, 2007) — the 10-month moving-average rule.
- [Regime filters](learn-strat-regime-filters.md) — market filters inside a trading strategy.
