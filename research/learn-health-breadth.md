# Breadth — how many stocks are taking part

**In short**

- An index is a weighted average, so it can rise while most stocks fall. Breadth counts how many stocks are actually going up.
- Breadth measures risk more than direction. It tells you how many of your own trades are likely to work, not where the index goes next.
- The most useful single number is the share of stocks above their 50-day average. Below 30% is a washout; above 70% is a strong, broad market.
- An index making new highs while fewer stocks take part (a divergence) has come before many tops, but it can run for months. It is a reason to trade smaller, not to sell everything.
- Deep washouts (under 15% of stocks above their 50-day) have tended to come near important lows. The selling is well advanced, but not always over.

This guide covers what breadth is and the common ways to measure it. It shows what divergences, washouts and breadth thrusts looked like in the US and India since 2015. It ends with how a trader turns breadth into a decision about how much to have at risk. Companion guides cover [the index's trend](learn-health-trend.md) and [volatility](learn-health-volatility.md).

---

## 1. What breadth is — and what it is not

On 6 October 2026 the S&P 500 closed at a record. On the same day only about a third of US stocks were above their 50-day average. The index was rising; the typical stock was not.

That can happen because an index is a weighted average. The S&P 500 gives its biggest companies a large share of the weight, and the Nifty 50 holds only fifty stocks. A trader who owns ten mid-sized breakouts does not own the index. **Breadth asks: how many stocks are actually going up?**

Breadth helps judge how risky the market is, **not** which way it will go. Weak breadth means only a few stocks are pushing the index up, and few other breakouts are working alongside yours. Strong breadth means many setups work at once. **The index tells you the market's overall direction; breadth tells you how many of your own trades are likely to work.**

## 2. How the breadth data here is built

A breadth count depends on which stocks you count. The figures in this guide use, for each market and each trading day since **2015**, the **1,000 most-traded stocks**. They are ranked by 20-day average turnover (the money value traded per day). So the set changes over time as trading shifts between stocks. For those stocks the data counts:

| Measure | Definition |
|---|---|
| Rising / falling | close above / below the previous close |
| Up / down 4%+ | the day's big movers |
| 52-week highs / lows | today's high (low) is the extreme of the last 252 sessions; needs about 200 sessions of history |
| Above the 5 / 50 DMA | close above its 5- / 50-day simple average |
| Month ±25% | up / down 25%+ over the last 21 sessions |

**Only common stocks count.** Exchange-traded funds and closed-end funds (funds that trade like a stock) are left out. Two consequences follow.

- **The two "1,000s" differ.** In the US the 1,000 most-traded are mostly large and mid-sized companies. In India the same count reaches well into small companies. So India's breadth is closer to a gauge of small and mid-sized stocks (§8).
- **The stock list is today's.** Stocks delisted since 2015 are probably missing. Missing them likely leaves out some losers, so old readings may lean slightly strong.

**Read every reading against its own history.** A good habit is to rank today's value against all days since 2015, and to compare it with one week, one month and three months ago. Slow changes matter most: markets rarely turn in a day.

## 3. The common breadth views

Most breadth dashboards show some version of these:

| View | What it shows | How to read it |
|---|---|---|
| The index against its 50-day | The index's % distance from its 50-day | The index's own short-term trend — the context |
| New 52-week highs and lows | Highs, lows, and their two-week average | Leadership against damage; read the 10-day average of highs − lows |
| Stocks above their 5- and 50-day | % above each average | 50-day: the average stock's trend; 5-day: short-term stretch |
| Stocks rising or falling | Advancers and decliners | Participation; read the 10-day average of rising − falling |
| Leading sectors | Best and worst sectors, and the share of each sector above its 50-day | Where the strength is, and how widely shared |
| Expected against actual volatility | VIX / India VIX against the index's realised volatility | See [the volatility guide](learn-health-volatility.md) |

Useful lines on a chart of the share above the 50-day: **30% (washout)** and **70% (strong)**. Watch for crossings of those lines, new 90-day extremes, and the index crossing its own 50-day.

## 4. The measures

### 4.1 % above the 50-day — and the 5-day

```series
title: US stocks above their 50-day average, and the S&P 500, since 2015
from: 2015-01-01
to: 2026-10-13
line: us:SPX | S&P 500 | log
line: us:breadth.pct50 | % of the 1,000 most-traded above their 50-day | pane2
mark: 2018-12-24 | 2% above
mark: 2020-03-12 | 2% above
mark: 2022-06-17 | 4.5% above
mark: 2025-04-08 | 4.9% above
caption: The lower pane swings from near 0% to over 90%. The deepest readings (2% in Dec 2018 and Mar 2020, under 5% in June and Sept 2022 and Apr 2025) came at or near the index's lows, not its highs.
```

This is the most useful single number: *for how many stocks is the trend up?* It swings from near zero to over 90%. Its deepest readings came at or near the index's lows.

| Since 2015 | US | India |
|---|---|---|
| Median % above 50-day | 59% | 56% |
| 10th–90th percentile | 29–77% | 21–82% |
| Days below 30% ("washout") | 11% | 19% |
| Days below 15% | 3.5% | 4.8% |
| Days above 70% ("strong") | 23% | 27% |

The **5-day** version is a short-term gauge of whether stocks have run up or sold off too far, too fast.

| US, % above the 5-day, since 2015 | |
|---|---|
| Median | 54% |
| Days under 20% | about 8% |
| Days over 80% | about 10% |

Under 20% in an uptrend is a stretched pullback. Over 80% is a poor moment to chase.

### 4.2 New 52-week highs and lows

On 12 March 2020, **660** of the 1,000 US stocks made a new 52-week low. The next day **692** Indian stocks did. On a typical day since 2015 there were far fewer:

| Typical day since 2015 | New highs | New lows |
|---|---|---|
| US | about 46 | about 7 |
| India | about 31 | about 5 |

Highs show **leadership**. A stock at a new high has no overhead supply: no earlier buyers sitting at a loss and waiting to sell. That is where breakout and trend strategies find candidates. Lows show **damage**. Read the **net** (highs minus lows) and its 10-day average.

### 4.3 Advancers, decliners and the A/D line

Take rising stocks minus falling stocks each day, and add the result to a running total. That running total is the **advance-decline line**. Its level means nothing; what matters is its direction compared with the index.

Suppose the index makes a new high but the A/D line does not. Then fewer stocks took part in the last leg up. The common NYSE version counts every issue listed, including thinly traded micro caps and bond funds. The version here counts only the 1,000 most-traded common stocks.

### 4.4 Big movers: ±4% days and ±25% months

| Stocks moving 4%+ in a day | US | India |
|---|---|---|
| Median day, up | 24 | 62 |
| Median day, down | 23 | 24 |
| Record day, down | 944 (12 March 2020) | 943 (23 March 2020) |

India is lopsided: more stocks make big up moves on a normal day, until a panic. Many stocks up 25% in a month means a hot market. Many down 25% means forced selling.

## 5. Divergences — the index at a high, fewer stocks with it

Here a **divergence** means the index makes a higher high while breadth makes a lower one.

### 5.1 The US, 2021

```series
title: The S&P 500 rose through 2021 while its new-high count faded
from: 2020-11-01
to: 2022-03-31
line: us:SPX | S&P 500
line: us:breadth.adline | A/D line, 1,000 most-traded | right
line: us:breadth.hl@sma10 | highs − lows, 10-day average | pane2 zero
mark: 2021-05-10 | breadth peak
mark: 2022-01-03 | index peak
caption: Highs − lows (10-day average) peaked at 164 on 10 May 2021 and was 53 when the S&P 500 made its high on 3 Jan 2022. The A/D line topped on 16 Nov 2021. By late January 2022 the net was negative.
```

The S&P 500 gained about **30%** from the start of 2021 to its high on **3 January 2022**. Meanwhile breadth weakened for months. Net highs (10-day average) peaked at **164** in May and were **53** on the final high. Only **33** stocks made new highs that day.

The share above the 50-day (10-day average) fell in steps:

| Date | % above the 50-day (10-day average) |
|---|---|
| Early January 2021 | about 83% |
| End of April 2021 | 73% |
| End of October 2021 | 61% |
| End of December 2021 | 47% |

On **10 December 2021** the index closed at a record while net highs were *negative* (about −10). The Russell 2000 (an index of small US companies) had peaked on **8 November 2021**.

The divergence did not time the top: it ran for half a year. What it said was that risk was rising.

### 5.2 2024–2026: narrow highs come and go

```series
title: S&P 500 records with fewer stocks above their 50-day, 2023–2026
from: 2023-10-01
to: 2026-10-13
line: us:SPX | S&P 500 | log
line: us:breadth.pct50@sma10 | % above 50-day, 10-day average | pane2
mark: 2024-06-18 | 48% above
mark: 2025-02-19 | 57% above
mark: 2026-10-06 | 34% above
caption: Broad records (early and late 2024) were followed by more records; narrow ones (June 2024, Feb 2025) by a stall or a fall. The record of 6 Oct 2026 came with 34% above the 50-day.
```

Periods when a handful of giant companies led the index show up in the data in bursts.

| S&P 500 high | % above the 50-day | Net highs (10-day average) | What followed |
|---|---|---|---|
| March 2024 | — | 104 | More records |
| June 2024 | about 48% | 28 | A stall |
| Late 2024 (record days) | median 69% | — | More records |
| 19 February 2025 | 57% | 37 | A 19% fall to 8 April |

At the time of writing, the **6 October 2026** record had net highs (10-day average) near **−24**. That is the lowest participation on any S&P 500 record day since 2015. What follows is unknown. It is the situation in which breadth says *size down*, not *sell everything*.

## 6. Washouts — when almost nothing is above its 50-day

On 17 December 2018 fewer than 15% of US stocks were above their 50-day average. A week later, on Christmas Eve, only 2% were. Three months after that first day, the S&P 500 was 10.9% higher.

A reading below 30% is a washout. The deep version is **below 10–15%**, which happens on under 5% of days in either market. It has tended to come near important lows.

The table below lists each first close under 15% after a recovery above 40%. It shows how the index changed over the next one, two and three months (21, 42 and 63 sessions).

| US — first day < 15% | Low (date) | +1m | +2m | +3m |
|---|---|---|---|---|
| 24 Aug 2015 | 4.7% (25 Aug) | +2.4% | +8.4% | +10.4% |
| 7 Jan 2016 | 6.9% (20 Jan) | −4.6% | +2.4% | +5.4% |
| 11 Oct 2018 | 8.8% (26 Oct) | +1.9% | −2.8% | −5.3% |
| 17 Dec 2018 | 2.0% (24 Dec) | +3.5% | +9.2% | +10.9% |
| 27 Feb 2020 | 2.2% (12 Mar) | −14.7% | −3.9% | +1.7% |
| 9 May 2022 | 11.1% (11 May) | +3.1% | −3.4% | +3.3% |
| 13 Jun 2022 | 4.5% (17 Jun) | +1.1% | +14.1% | +4.9% |
| 22 Sep 2022 | 4.5% (26 Sep) | −0.1% | +5.1% | +3.2% |
| 3 Oct 2023 | 12.7% (27 Oct) | +0.2% | +8.6% | +11.2% |
| 4 Apr 2025 | 4.9% (8 Apr) | +10.5% | +17.1% | +22.7% |

| After a US washout | Higher | Median |
|---|---|---|
| One month on | 7 of 10 | — |
| Three months on | 9 of 10 | +5% |
| Any day since 2015, three months on | 75% of the time | — |

The first washout day of February 2020 was followed by a further **15%** fall. **A washout says the selling is well advanced, not that it is over.**

**India** had **13** such episodes. The Nifty 50 was higher three months later after **11**, with a median of **+6.4%**. The exceptions:

- the small-company bear market of 2018: first day 28 September, low **3.9%** on 8 October, Nifty **−2.4%** three months on;
- March 2020: low **0.6%** on 23 March; Nifty **−6.1%** from the first day, 9 March.

Two US washouts had **no Indian twin**. India's lowest reading was **43%** in September 2022 and **32%** in October 2023.

## 7. Breadth thrusts — the other end of a washout

In a **breadth thrust**, the market goes from deeply oversold (most stocks beaten down) to most stocks rising, within days. Martin Zweig's version takes the share of advancing stocks, advancers ÷ (advancers + decliners), and averages it over 10 days. A thrust is that average rising from below **0.40** to above **0.615** within 10 sessions.

A simple version of this can be built from the daily counts of rising and falling stocks, using a 10-day exponential average. Here is how it did since 2015:

| Breadth thrust, since 2015 | US | India |
|---|---|---|
| Times it fired | 11 | 7 |
| Index higher three months later | 7 of 11 | 7 of 7 |
| Index higher a year later | 9 of 10 (with a full year) | 4 of 6 |

Two US thrusts fired inside the 2022 bear market (March and September). Three months on, the index was **18%** and **4%** lower.

**Read a thrust as "the washout is probably over", not "the bear market is over".** Let the index's trend ([trend guide](learn-health-trend.md)) confirm it.

## 8. India against the US

```series
title: India's breadth faded before the Nifty peaked, then washed out, 2024–2025
from: 2024-01-01
to: 2025-06-30
line: india:NIFTY50 | Nifty 50
line: india:breadth.pct50@sma10 | % above 50-day, 10-day average | pane2
mark: 2024-09-26 | Nifty peak, 64% above
mark: 2025-03-03 | 9% above
band: 2025-01-27 2025-03-21 | below 15%, until back above 40%
caption: About 82% of Indian stocks were above their 50-day in early July 2024 and 64% at the Nifty's high on 26 Sept. On 3 March 2025 under 7% were (the 10-day average shown here: 9%).
```

The 2024 top in India was a divergence of its own. Net highs (10-day average) peaked near **153** in February 2024. They were about **72** at the Nifty 50's record on **26 September 2024**.

The washout that followed was India's deepest since 2020: **6.6%** above the 50-day on 3 March 2025. Yet the Nifty 50 was down only about **16%** from its peak. Holders of small and mid-sized stocks did far worse than the index suggested. That is the reason to watch India's breadth, not just the Nifty.

India's breadth runs **broader in rallies and deeper in sell-offs**:

| | Median % above the 50-day on record days |
|---|---|
| Nifty 50 record days, 2023 | 80–85% |
| S&P 500 record days, 2024–25 | mostly 50–70% |

The 2023–24 rally was a boom in small and mid-sized companies. From the March 2023 low to late September 2024, the Nifty Midcap 50 rose about **106%**. The Nifty 50 rose about **54%**.

## 9. How a trader uses breadth

Breadth does not pick stocks; it **sets how much risk to take**.

| Breadth state | Usually means | Exposure |
|---|---|---|
| > 70% above the 50-day, highs ≫ lows | Broad uptrend, setups working | Full size and position count; buy breakouts |
| 50–70%, net highs positive | Normal | Normal size; favour the leading sectors |
| Index at highs, % above 50-day and net highs falling | Narrowing | Fewer new positions; tighten stops on laggards; strongest groups only |
| < 30% (washout) | Correction | Few or no new longs; protect open profits |
| < 15%, then a fast recovery or thrust | Selling exhausted | Start small with the first leaders to make new highs; add as the index trend repairs |

**Which signals to trust:**

- **Most:** the % above the 50-day at its extremes, and new lows expanding (damage is hard to fake).
- **Noisy:** daily advancers and decliners. Use the 10-day average.
- **Least, on their own:** divergences used for *timing* (2021's ran six months), and thrusts inside a bear market (2022).

**Combine** breadth with the index trend, credit and volatility ([liquidity and credit](learn-macro-liquidity-credit.md), [volatility](learn-health-volatility.md)). Two warnings together matter far more than one.

Many trading systems check only the index itself: for example, whether the main indices are below their 50-day average. They compute breadth but do not act on it. If yours is one of them, breadth is a filter you apply yourself. [learn-strat-regime-filters](learn-strat-regime-filters.md) covers market filters inside a strategy.

## 10. What the evidence says

- **Robust:** deep washouts cluster near major lows, and returns afterwards have been better than average. That holds in this data and in long NYSE studies (Zweig; Desmond on 90% down days).
- **Mostly true:** narrowing breadth comes before many tops (2021 US, 2024 India). But the lead runs from weeks to many months, and narrow markets can keep rising (the stretches of 2023–24 led by a few giant companies).
- **Folklore:** that one divergence or one thrust times the market.
- **Measurement matters:** a different set of stocks gives other dates and levels. Compare a reading with its own history.
- **Sample:** 2015 onwards holds about ten real washouts per market. §6–7 describe what happened, not probabilities. No threshold here is a buy signal.
- **Survivorship:** the stock lists are today's, so delisted losers are probably missing and old readings may lean slightly strong.

## 11. Checklist

- [ ] % above the 50-day: rising or falling over a month? Above 70%, below 30%?
- [ ] Net new highs (10-day): positive and expanding, or shrinking?
- [ ] New lows expanding while the index holds up?
- [ ] Index at a high with fewer stocks above the 50-day than at the last high?
- [ ] After a washout: a fast recovery or thrust, and the index back over its 50-day?
- [ ] India: is the Nifty hiding weakness in small and mid-sized stocks?
- [ ] In the last five sessions: any crossing of 30% or 70%?
- [ ] Set this week's position count and size from the table in §9

## Further reading

- Martin Zweig, *Winning on Wall Street* — the breadth thrust.
- Gregory L. Morris, *The Complete Guide to Market Breadth Indicators*.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — breadth and stages.
- Paul Desmond, "Identifying Bear Market Bottoms and New Bull Markets" (2002) — 90% days.
- William J. O'Neil, *How to Make Money in Stocks* — leadership and the general market.
- [learn-strat-regime-filters](learn-strat-regime-filters.md) — using market conditions as a filter in a strategy.
