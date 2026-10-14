# Distribution days and the follow-through day — reading index volume

Learning material: William O'Neil's two volume signals for the general market —
the **distribution day**, institutional selling that warns of a top, and the
**follow-through day**, institutional buying that confirms a new uptrend —
how they are defined, how they looked at real turns in the stored data, how
often they mislead, and what the app does and does not compute. Companion to
[the trend guide](learn-health-trend.md) (where the index sits against its
averages) and [the breadth guide](learn-health-breadth.md).

**Where this shows in the app.** The app does **not** count distribution days
or flag follow-through days for an index: no job, page or strategy computes
them, and the market regime (`core/regime.py`) does not use index volume. Two
related pieces exist. The charts in these guides can draw a running count with
the `@dist25` transform on any stored series that has volume (SPY, QQQ, IWM;
`^NSEI` for India). And the **Trend pullback** strategy's demand/supply note
(`core/demand_supply.py`) counts accumulation and distribution days over 25
sessions for each *stock* — the same ±0.2%-on-higher-volume rule — and scores
"Demand in control" / "Supply in control" from them.

---

## 1. The idea: big money cannot hide

A fund selling a large position cannot do it in a day without crushing the
price, so it sells over weeks — on the index, **down days on rising volume**.
One means nothing; **several clustered in a few weeks, near a high, mean the
largest holders are leaving**. That is why O'Neil made it part of the "M"
(market direction) in CAN SLIM. The mirror image is the **follow-through
day**: a strong gain on rising volume a few days into a rebound.

## 2. Counting distribution days

The usual definition (O'Neil / *Investor's Business Daily*):

| Rule | Value |
|---|---|
| A distribution day | The index closes **down 0.2% or more** on volume **higher than the previous session** |
| The window | The last **25 sessions** (about five weeks) |
| A day drops off | After 25 sessions — **or** once the index closes about **5% above** that day's close |
| Pressure | About **5–6** in the window is the classic warning; more is a market under steady selling |

IBD counts on the Nasdaq Composite and the S&P 500 / NYSE using exchange
volume. **The app's `@dist25` and the numbers below use ETF volume (SPY, QQQ)
and do not apply the 5% rule** — a day only drops off after 25 sessions. They
therefore read a little higher than IBD's count after a strong rally.

### 2.1 What is "normal" on this count

Measured on stored prices since 2000, about **23% of all sessions** qualify as
distribution days on SPY, QQQ and IWM alike. So a 25-session window holds about
five or six on an ordinary day:

| SPY, 25-session count | 2000–09 | 2010–19 | 2020–26 |
|---|---|---|---|
| Median | 6 | 5 | 6 |
| Top tenth of days | 8+ | 8+ | 9+ |

**On a raw ETF count, "5–6" is close to normal; 8 or more is the unusual
reading.** Since 2010 the median has been 5 while SPY was above its 200-day
and 7 below it. Calibrate the rule of thumb to the data you are counting on.

### 2.2 Stalling days

O'Neil also counted **stalling**: near a high, the index closes flat or barely
up on higher volume, often in the lower half of its range — heavy trade, no
progress. It is a judgement call, not in the app's count; treat it as extra
evidence beside a cluster, never alone.

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

QQQ topped on 19 November 2021 with just **3** distribution days in the window
— the count is a description of selling, and at the very top there was little
yet. By 3 December it had 7, by 14 December 9, and 10 on 21 January 2022. SPY
went on to a record on 3 January 2022 with **7** already counted, including
heavy days on 26 November (−2.2%) and 30 November (−2.0%). The Nasdaq 100 fell
about 36% to December 2022.

Here the missing 5% rule matters: SPY closed 5% above its 3 December
distribution day on 30 December, so IBD's method would have dropped that day
(and its count would have been a little lower at the record).

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

SPY closed at a record on 20 September 2018 with only **2** distribution days,
3 the day after. QQQ had **8** by 21 September and **10** by 5 October; on 10
October SPY fell 3.2% on nearly three times the previous day's volume. Note
that 21 September was a quarterly options-expiry and index-rebalance day,
whose volume is inflated for mechanical reasons — **expiry days produce false
distribution days**; give them less weight.

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

On 19 February 2020 SPY's count was **3** (QQQ's 5). The fall was an outside
shock, and the count only rose once the selling had begun — 9 by 28 February,
after four days of heavy losses. **Distribution counts catch tops that are
built by selling; they cannot catch a shock.** Your stops have to do that.

## 4. The follow-through day

After a decline, the index eventually stops making new lows and bounces. That
first up day is **day 1 of a rally attempt**. O'Neil's rule:

1. Count from day 1. If the index closes below the low of the attempt, it has
   failed — wait for a new day 1.
2. A **follow-through day** comes on **day 4 or later** (most often days 4–7):
   a **strong gain on volume higher than the previous session**.
3. "Strong" has changed over the years — about 1% in O'Neil's early books,
   higher (1.5–1.7%) in the 2000s, lower again since. **There is no single
   official number**; about 1.25% to 1.7% is the range to keep in mind.
4. Days 1–3 do not count, however big: a short-covering burst is not
   institutions committing.

A follow-through day says **the market has earned a trial**, not "buy
everything": buy the best setups small, add only if they work.

### 4.1 March–April 2020

SPY's lowest close was on 23 March 2020. Day 1 was 24 March, a 9.1% gain —
on *lower* volume than the day before, and day 1 anyway. In the ETF data, QQQ
qualified on 2 April (day 8, +2.0% on higher volume) and **SPY on 6 April (day
10, +6.7% on 188 million shares against 136 million)**. Three months later SPY
was about 18% higher.

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

- **June 2022.** SPY's lowest close was 17 June; day 1 was 21 June (+2.5%) and
  **day 4, 24 June, rose 3.2% on 98 million shares against 79 million** — a
  textbook follow-through (QQQ also qualified, +3.4% on barely higher volume).
  SPY rallied about 17% to 16 August, then rolled over, **closed below the
  June low on 26 September** and bottomed on 12 October. The signal "worked"
  for two months, then failed.
- **October 2022.** SPY's lowest close was 12 October. Day 1 was 13 October
  (+2.6%, the day of the September CPI report's intraday reversal); 14 October
  fell 2.3% but held above the low; **day 7, 21 October, rose 2.4% on 131
  million shares against 88 million**. That low held. QQQ is the cautionary
  tale: it closed below its low on 14 October (resetting its count), followed
  through on 21 October, closed below that attempt's low on 3 November —
  a failure on closes — followed through again on 10 November (+7.4% on the
  soft CPI report), and dipped marginally below once more on 28 December
  before the 2023 rally.

### 4.3 April 2025 — the big day was day 1

SPY's lowest close was 8 April 2025. The next day it rose 10.5% on heavy
volume — but that was **day 1**. The follow-through, in this data, came on 22
April (day 9, +2.6% on higher volume). Three months later SPY was about 20%
higher.

## 5. How often follow-through days fail

It is well known among O'Neil's followers that **no sustained rally has begun
without a follow-through day, but many follow-through days fail**. The second
half can be measured on the stored data; the method, so you can judge it:

- **Data:** SPY since 1993 and QQQ since 1999 (ETF closes and volume).
- **Setting:** the ETF has closed at least 10% below its high since the last
  confirmed uptrend. A new lowest close resets the attempt; day 1 is the first
  up close after it.
- **Follow-through:** day 4 or later, a gain of at least 1.25% (or 1.7%) on
  volume above the previous session.
- **Failure:** a close below the attempt's low within the next 25 sessions
  (about five weeks), or 63 (about three months). IBD uses intraday lows and
  index volume, so this is an approximation.

| Ticker | Threshold | Follow-throughs | Undercut within 25 sessions | Within 63 sessions |
|---|---|---|---|---|
| SPY | 1.25% | 43 | 15 (35%) | about half |
| SPY | 1.7% | 38 | 11 (29%) | — |
| QQQ | 1.25% | 75 | 29 (39%) | about half |
| QQQ | 1.7% | 68 | 23 (34%) | — |

**Roughly a third failed within five weeks and about half within three
months.** A higher threshold filtered out a few failures but also some good
signals. The failures cluster in long bear markets — 2000–02 and 2008–09
each produced several in a row on SPY. The conclusion is the one O'Neil drew: the
follow-through day is a **permission to test the market with small buys, not
a prediction**.

The distribution count gives a similar, softer result. From 2000, after a day
with **6 or more** distribution days in SPY's window, the index fell 10% or
more at some point in the next three months about **20%** of the time, against
about **13%** after a day with 3 or fewer (QQQ: about 30% against 16%). The
average one-month return was not lower — the count measures **risk, not
direction**.

## 6. India

O'Neil's method is mostly applied to US indices, where index volume is
published and widely used. On the stored data, `^NSEI` (Nifty 50) has **no
volume before 2013** and a few gaps after (about a dozen zero-volume days in
2018); the volume figure comes from the data provider, not NSE's official
turnover, so read it as approximate. Nifty ETFs (such as NIFTYBEES) are not
stored.

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

At the Nifty's record on 26 September 2024 the count was **3**; it rose to 8
by 22 November and 9 on 13 January 2025, while the index fell about 16% to 4
March. As in 2020, it described the decline rather than foreseeing it. For
Indian traders, breadth ([the breadth guide](learn-health-breadth.md)) and the
midcap index against its averages ([the trend guide](learn-health-trend.md))
are more reliable reads; FII selling ([the currencies guide](learn-macro-currencies.md))
is often the institutional seller behind the volume.

## 7. What a trader does

- **Count weekly, on more than one index.** In 2018 QQQ warned while SPY was
  quiet; in 2021 QQQ warned weeks before SPY's record.
- **Act on clusters near highs, not on single days.** Eight or more on the raw
  ETF count, while the index is still near its high and breadth is narrowing,
  is the setting in which to stop adding, tighten stops on extended winners
  and take partial profits.
- **Discount mechanical volume:** expiry, rebalance and holiday sessions.
- **After a decline, wait for the follow-through, then buy small.** Start with
  the leaders breaking out of sound bases ([learn-bases.md](learn-bases.md));
  add only as they work. If the index undercuts the attempt's low, cut back and
  wait for the next one.
- **Never let a count override a stop.** In February 2020 the count was low at
  the top.

## 8. What the evidence says

- **Robust:** heavy-volume selling clusters around many tops, and the major
  rallies in this data (March 2009, April 2020, October 2022) began with a
  follow-through — but so did many false starts. IBD's own studies of past
  markets are descriptive and chosen with hindsight.
- **Measured here:** a high count raised the chance of a 10% fall over the
  next three months from about one in eight to about one in five (SPY), and
  roughly a third of follow-through days failed within five weeks.
- **Weak points:** thresholds (0.2%, 25 sessions, 1.25–1.7%) are conventions;
  ETF volume differs from exchange volume; volume is inflated on expiry and
  rebalance days; and a shock like February 2020 gives no warning.
- **Folklore:** that a specific count (say, exactly 5) "calls" a top, or that a
  follow-through day guarantees a bull market.

## 9. Checklist

- [ ] SPY and QQQ: distribution days in the last 25 sessions? Rising or falling?
- [ ] Count high (8+) while the index is still near its high? Breadth narrowing too?
- [ ] Any of this week's "distribution days" on an expiry or rebalance day?
- [ ] In a correction: which day of the rally attempt is it? Has the low held?
- [ ] Follow-through today? Gain size, volume vs yesterday, day number.
- [ ] After a follow-through: first buys small, only the strongest bases.
- [ ] India: midcap index and breadth before trusting `^NSEI` volume.

## Further reading

- William O'Neil, *How to Make Money in Stocks* — the "M" in CAN SLIM,
  distribution days and the follow-through day.
- William O'Neil, *The Successful Investor* — selling rules and reading the
  general market.
- *Investor's Business Daily* (investors.com) — "The Big Picture" column and
  its market-pulse outlook, where the counts are published daily.
