# Distribution days and the follow-through day — reading index volume

**In short**

- A distribution day is the index closing down 0.2% or more on higher volume than the day before. Several in a few weeks, near a high, suggest big funds are selling.
- A follow-through day is a strong gain on higher volume, on day 4 or later of a rebound. It says a new uptrend may be starting.
- On ETF volume, five or six distribution days in 25 sessions is close to normal. Eight or more is the unusual reading.
- Distribution counts catch tops built by slow selling, not sudden shocks: in February 2020 the count was low at the top. Your stops have to handle shocks.
- Roughly a third of follow-through days failed within five weeks. Treat one as permission to buy small, not as a prediction.

William O'Neil used two volume signals to read the general market. The **distribution day** is heavy selling by institutions (funds, banks, pension plans) that warns of a top. The **follow-through day** is heavy institutional buying that confirms a new uptrend. This guide covers how they are defined, how they looked at real turns, and how often they mislead. Companion to [the trend guide](learn-health-trend.md) (where the index sits against its averages) and [the breadth guide](learn-health-breadth.md).

---

## 1. The idea: big money cannot hide

Suppose a fund holds 2% of a large company and decides to sell. Selling it all in one day would push the price down hard. So it sells over weeks, a slice each day.

On the index, many funds doing this at once shows up as **down days on rising volume**. One such day means nothing. **Several clustered in a few weeks, near a high, mean the largest holders are leaving.** That is why O'Neil made it part of the "M" (market direction) in CAN SLIM, his stock-picking checklist.

The mirror image is the **follow-through day**: a strong gain on rising volume a few days into a rebound.

## 2. Counting distribution days

The usual definition comes from O'Neil and *Investor's Business Daily* (IBD):

| Rule | Value |
|---|---|
| A distribution day | The index closes **down 0.2% or more** on volume **higher than the previous session** |
| The window | The last **25 sessions** (about five weeks) |
| A day drops off | After 25 sessions — **or** once the index closes about **5% above** that day's close |
| Pressure | About **5–6** in the window is the classic warning; more is a market under steady selling |

IBD counts on the Nasdaq Composite and the S&P 500 / NYSE, using the volume of the whole exchange. The counts in this guide use **the volume of the ETFs that track those indices**: SPY for the S&P 500 and QQQ for the Nasdaq. They also skip the 5% rule, so a day drops off only after 25 sessions. After a strong rally they therefore read a little higher than IBD's count.

### 2.1 What is "normal" on this count

Since 2000 about **23% of all sessions** qualified as distribution days on SPY, QQQ and IWM (Russell 2000) alike. So on an ordinary day a 25-session window holds about five or six:

| SPY, 25-session count | 2000–09 | 2010–19 | 2020–26 |
|---|---|---|---|
| Median | 6 | 5 | 6 |
| Top tenth of days | 8+ | 8+ | 9+ |

**On a raw ETF count, "5–6" is close to normal; 8 or more is the unusual reading.** The count also depends on the trend:

| SPY since 2010 | Median count |
|---|---|
| While SPY was above its 200-day | 5 |
| While SPY was below its 200-day | 7 |

Adjust the rule of thumb to the data you are counting on.

### 2.2 Stalling days

O'Neil also counted **stalling** days. Near a high, the index closes flat or barely up on higher volume, often in the lower half of the day's range. There is heavy trading but no progress. Spotting one is a judgement call. Treat a stalling day as extra evidence beside a cluster of distribution days, never on its own.

The same counting works on a single stock. Over 25 sessions, count up days on higher volume (accumulation) and down days on higher volume (distribution). More of one than the other suggests whether demand or supply is in control. See [learn-price-volume](learn-price-volume.md).

## 3. Distribution at real tops

### 3.1 Late 2021 — the Nasdaq first

```series
title: QQQ and its distribution days, October 2021 – February 2022
from: 2021-10-01
to: 2022-02-28
tf: D
line: us:QQQ | QQQ
line: us:QQQ@dist25 | QQQ distribution days (25 sessions) | pane2
line: us:SPY@dist25 | SPY distribution days | pane2
mark: 2021-11-19 | QQQ peak
mark: 2022-01-03 | S&P 500 record
caption: QQQ peaked on 19 November with only 3 distribution days; within three weeks it had 9. SPY made its record on 3 January with 7 already in its window.
```

QQQ topped on 19 November 2021 with just **3** distribution days in the window. The count describes selling that has happened, and at the very top there had been little yet. Then it climbed:

| Date | QQQ distribution days |
|---|---|
| 19 November 2021 (peak) | 3 |
| 3 December 2021 | 7 |
| 14 December 2021 | 9 |
| 21 January 2022 | 10 |

SPY went on to a record on 3 January 2022 with **7** already counted. They included two heavy days in late November, of −2.2% and −2.0%. The Nasdaq 100 fell about 36% to December 2022.

Here the missing 5% rule matters. SPY closed 5% above its 3 December distribution day on 30 December. So IBD's method would have dropped that day, and its count would have been a little lower at the record.

### 3.2 September 2018 — the warning on one index only

```series
title: September 2018 — QQQ under distribution while SPY was quiet
from: 2018-07-02
to: 2018-12-31
tf: D
line: us:SPY | SPY
line: us:QQQ@dist25 | QQQ distribution days | pane2
line: us:SPY@dist25 | SPY distribution days | pane2
mark: 2018-09-20 | S&P 500 record
mark: 2018-10-10 | −3.2% day
caption: SPY set its record on 20 September with 2 distribution days; QQQ had 6–8 through September and 10 by 5 October. The S&P 500 then fell almost 20% by 24 December.
```

SPY closed at a record on 20 September 2018 with only **2** distribution days, and 3 the day after. QQQ had **8** by 21 September 2018. It had **10** by 5 October. On 10 October SPY fell 3.2% on nearly three times the previous day's volume.

Note that 21 September was a quarterly options-expiry day and an index-rebalance day. On expiry days, traders close out expiring options or replace them with later ones. On rebalance days, index funds buy and sell to match changes in an index. Both inflate volume for mechanical reasons, not because anyone has changed their view. **So expiry days produce false distribution days**; give them less weight.

### 3.3 February 2020 — no warning at all

```series
title: SPY from the February 2020 record to the April follow-through
from: 2019-12-02
to: 2020-06-30
tf: D
line: us:SPY | SPY
line: us:SPY@dist25 | SPY distribution days | pane2
mark: 2020-02-19 | record, 3 distribution days
mark: 2020-03-23 | low
mark: 2020-04-06 | SPY follow-through
caption: At the 19 February record SPY had 3 distribution days in its window; seven sessions later it had 9. The count described the crash; it did not foresee it.
```

On 19 February 2020 SPY's count was **3** (QQQ's 5). The fall was an outside shock. The count only rose once the selling had begun: 9 by 28 February, after four days of heavy losses.

**Distribution counts catch tops that are built by gradual selling; they cannot catch a sudden shock.** Your stops have to do that.

## 4. The follow-through day

In March 2020 SPY made its lowest close on 23 March. The next day it jumped 9.1%. That was not yet the signal. The signal came on 6 April, the tenth day of the rebound, with a 6.7% gain on higher volume (§4.1).

After a decline, the index eventually stops making new lows and bounces. That first up day is **day 1 of a rally attempt**. O'Neil's rule:

1. Count from day 1. If the index closes below the low of the attempt, the attempt has failed. Wait for a new day 1.
2. A **follow-through day** comes on **day 4 or later** (most often days 4–7). It is a **strong gain on volume higher than the previous session**.
3. What counts as "strong" has changed over the years. It was about 1% in O'Neil's early books, higher (1.5–1.7%) in the 2000s, and lower again since. **There is no single official number**; about 1.25% to 1.7% is the range to keep in mind.
4. Days 1–3 do not count, however big. An early jump can come from short sellers buying back to close their bets. That is not institutions committing new money.

A follow-through day says **the market has earned a trial**, not "buy everything". Buy the best setups in small size, and add only if they work.

### 4.1 March–April 2020

SPY's lowest close was on 23 March 2020. Day 1 was 24 March, a 9.1% gain. It came on *lower* volume than the day before, but it still counts as day 1.

| ETF | Follow-through day | Day of the attempt | Gain | Volume against the day before |
|---|---|---|---|---|
| QQQ | 2 April 2020 | 8 | +2.0% | higher |
| SPY | 6 April 2020 | 10 | +6.7% | 188 million against 136 million shares |

Three months later SPY was about 18% higher.

### 4.2 June and October 2022 — one that faded, one that held

```series
title: 2022 — two follow-through days, two different endings
from: 2022-06-01
to: 2022-12-30
tf: D
rebase: 100
line: us:SPY | SPY
line: us:QQQ | QQQ
mark: 2022-06-24 | follow-through
mark: 2022-08-16 | rally peaks
mark: 2022-10-12 | new low
mark: 2022-10-21 | follow-through
mark: 2022-11-10 | CPI day
caption: The June follow-through led a 17% rally that failed in August; SPY then broke the June low. The October one marked the bear-market low for the S&P 500, though QQQ dipped below its October closes twice more.
```

**June 2022.** SPY's lowest close was on 17 June 2022. Day 1 was 21 June 2022 (+2.5%). Day 4, 24 June 2022, rose 3.2% on higher volume.

About 98 million shares traded, against 79 million the day before. That was a textbook follow-through; QQQ also qualified, +3.4% on barely higher volume. SPY rallied about 17% to 16 August, then turned down. It **closed below the June low on 26 September** and bottomed on 12 October.

So the June signal "worked" for two months, then failed.

**October 2022.** SPY's lowest close was 12 October. Day 1 was 13 October (+2.6%), the day of the September CPI report: the market fell early, then reversed and closed higher. On 14 October it fell 2.3% but held above the low.

Day 7, 21 October 2022, rose 2.4% on higher volume. About 131 million shares traded, against 88 million the day before. That low held.

QQQ is the cautionary tale. It closed below its low on 14 October, which reset its count. It followed through on 21 October.

Then it closed below that attempt's low on 3 November, a failure on closing prices. It followed through again on 10 November 2022, with a 7.4% gain on the soft CPI report. It dipped marginally below once more on 28 December, before the 2023 rally.

### 4.3 April 2025 — the big day was day 1

SPY's lowest close was 8 April 2025. The next day it rose 10.5% on heavy volume, but that was **day 1**. In this data the follow-through came on 22 April: day 9, +2.6% on higher volume. Three months later SPY was about 20% higher.

## 5. How often follow-through days fail

O'Neil's followers often say that **no sustained rally has begun without a follow-through day, but many follow-through days fail**. The second half can be measured on market data. Here is the method, so you can judge it:

- **Data:** SPY since 1993 and QQQ since 1999 (ETF closes and volume).
- **Setting:** the ETF has closed at least 10% below its high since the last confirmed uptrend. A new lowest close resets the attempt. Day 1 is the first up close after it.
- **Follow-through:** day 4 or later, a gain of at least 1.25% (or 1.7%) on volume above the previous session.
- **Failure:** a close below the attempt's low within the next 25 sessions (about five weeks), or 63 (about three months).

| Ticker | Threshold | Follow-throughs | Undercut within 25 sessions | Within 63 sessions |
|---|---|---|---|---|
| SPY | 1.25% | 43 | 15 (35%) | about half |
| SPY | 1.7% | 38 | 11 (29%) | — |
| QQQ | 1.25% | 75 | 29 (39%) | about half |
| QQQ | 1.7% | 68 | 23 (34%) | — |

**Roughly a third failed within five weeks, and about half within three months.** A higher threshold filtered out a few failures, but also some good signals. The failures cluster in long bear markets. On SPY, the 2000–02 bear market produced a run of them. So did the 2008–09 one.

The conclusion is the one O'Neil drew. The follow-through day is a **permission to test the market with small buys, not a prediction**.

The distribution count gives a similar, softer result. From 2000, compare days with many distribution days in the window against days with few:

| Chance of a 10%+ fall within three months, since 2000 | SPY | QQQ |
|---|---|---|
| After days with 6 or more distribution days | about 20% | about 30% |
| After days with 3 or fewer | about 13% | about 16% |

The average one-month return was not lower after a high count. The count measures **risk, not direction**.

## 6. India

```series
title: Nifty 50 and its distribution days, June 2024 – April 2025
from: 2024-06-03
to: 2025-04-30
tf: D
line: india:^NSEI | Nifty 50
line: india:^NSEI@dist25 | distribution days (25 sessions) | pane2
mark: 2024-09-26 | Nifty record
caption: At the 26 September 2024 record the count was 3; it reached 8 in November and 9 in January as the Nifty fell about 16% to March 2025.
```

At the Nifty's record on 26 September 2024 the count was **3**. It rose to 8 by 22 November and to 9 on 13 January 2025. Meanwhile the index fell about 16% to 4 March. As in 2020, the count described the decline rather than foreseeing it.

O'Neil's method is mostly applied to US indices, where index volume is published and widely used. Nifty 50 volume is patchier. In the data used here it is missing before 2013, with about a dozen zero-volume days in 2018. It comes from a data provider, not NSE's official turnover, so read it as approximate.

For Indian traders, two reads are more reliable: breadth ([the breadth guide](learn-health-breadth.md)), and the midcap index against its averages ([the trend guide](learn-health-trend.md)). FII selling ([the currencies guide](learn-macro-currencies.md)) is often the institutional seller behind the volume.

## 7. What a trader does

- **Count weekly, on more than one index.** In 2018 QQQ warned while SPY was quiet. In 2021 QQQ warned weeks before SPY's record.
- **Act on clusters near highs, not on single days.** Take eight or more on the raw ETF count, while the index is still near its high and breadth is narrowing. That is the setting in which to stop adding, tighten stops on winners that have run far above their buy point, and take partial profits.
- **Give less weight to mechanical volume:** expiry, rebalance and holiday sessions.
- **After a decline, wait for the follow-through, then buy small.** Start with the leading stocks breaking out of sound bases ([learn-bases.md](learn-bases.md)), and add only as they work. If the index closes below the attempt's low, cut back and wait for the next attempt.
- **Never let a count override a stop.** In February 2020 the count was low at the top.

Using market signals like these as a rule inside a trading strategy is covered in [learn-strat-regime-filters](learn-strat-regime-filters.md).

## 8. What the evidence says

- **Robust:** heavy-volume selling clusters around many tops. The major rallies in this data (March 2009, April 2020, October 2022) began with a follow-through, but so did many false starts.
- **Hindsight:** IBD's own studies of past markets describe what happened, and the examples were chosen with hindsight.
- **Measured here:** a high count raised the chance of a 10% fall over the next three months from about one in eight to about one in five (SPY). Roughly a third of follow-through days failed within five weeks.
- **Limits of the measurement:** the counts here use ETF closes and volume. IBD uses intraday lows (the lowest price during the day) and whole-exchange volume, so these results are an approximation.
- **Weak points:** the thresholds (0.2%, 25 sessions, 1.25–1.7%) are conventions. Volume is inflated on expiry and rebalance days. And a shock like February 2020 gives no warning.
- **Folklore:** that a specific count (say, exactly 5) "calls" a top, or that a follow-through day guarantees a bull market.

## 9. Checklist

- [ ] SPY and QQQ: distribution days in the last 25 sessions? Rising or falling?
- [ ] Count high (8+) while the index is still near its high? Breadth narrowing too?
- [ ] Any of this week's "distribution days" on an expiry or rebalance day?
- [ ] In a correction: which day of the rally attempt is it? Has the low held?
- [ ] Follow-through today? Gain size, volume vs yesterday, day number.
- [ ] After a follow-through: first buys small, only the strongest bases.
- [ ] India: check the midcap index and breadth before trusting Nifty 50 volume.

## Further reading

- William O'Neil, *How to Make Money in Stocks* — the "M" in CAN SLIM,
  distribution days and the follow-through day.
- William O'Neil, *The Successful Investor* — selling rules and reading the
  general market.
- *Investor's Business Daily* (investors.com) — "The Big Picture" column and
  its market-pulse outlook, where the counts are published daily.
