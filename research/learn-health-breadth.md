# Breadth — how many stocks are taking part

Learning material on market breadth: what it is, and why it measures **risk
more than direction**. It covers the measures this app stores, and what
divergences, washouts and breadth thrusts looked like in the stored data, in
the US and India. It ends with how a trader turns breadth into a decision about
how much to have at risk. Companion to [the trend guide](learn-health-trend.md)
and [the volatility guide](learn-health-volatility.md).

**Where this shows in the app.** Markets → **Breadth** ("How healthy is the
market — risk, not direction"). The page is built from the app's daily breadth
table, `breadth_daily` (computed by `scripts/swing_screener/analytics/breadth.py`
and served by `/api/breadth` in `web/server.py`). Every reading is ranked
against all trading days since 2015. Breadth also supplies three of the six
**market tone** signals on Markets → Post-market (`analytics/postmarket.py`):
*more stocks rose than fell*, *more new 52-week highs than lows*, *half or more
of stocks above their 50-day average*.

---

## 1. What breadth is — and what it is not

An index is a weighted average. The S&P 500 gives its biggest companies a large
share of the weight, and the Nifty 50 holds only fifty stocks. So an index can
rise while most stocks fall. A trader who owns ten mid-sized breakouts does not
own the index. **Breadth asks: how many stocks are actually going up?**

The page's framing is the right one: breadth *"helps judge how risky the
market is, **not** which way it will go."* Weak breadth means only a few stocks
are pushing the index up, and few other breakouts are working alongside yours.
Strong breadth means many setups work at once. **The index tells you the
market's overall direction; breadth tells you how many of your own trades are
likely to work.**

## 2. How this app builds breadth

Every trading day since **2015**, the app takes the **1,000 most-traded
stocks** in each market (`analytics/breadth.py`). They are ranked by 20-day
average turnover (the money value traded per day). So the set changes over
time as trading shifts between stocks. For those stocks it counts:

| Field | Definition in the code |
|---|---|
| Rising / falling (`adv`, `dec`) | close above / below the previous close |
| Up / down 4%+ (`up4`, `dn4`) | the day's big movers |
| 52-week highs / lows | today's high (low) is the extreme of the last 252 bars; needs ~200 bars of history |
| Above the 5 / 50 DMA | close above its 5- / 50-day simple average |
| Month ±25% (`up25m`, `dn25m`) | up / down 25%+ over the last 21 bars (±50% is stored too) |

**Only common stocks count.** The US list of stocks already excludes ETFs.
Closed-end funds (funds that trade like a stock) are also dropped when the
app's classification job flags them (`classify`). India's symbols are
classified as equity or fund, and funds are left out. Two consequences:

- **The two "1,000s" differ.** In the US the 1,000 most-traded are mostly
  large and mid-sized companies. In India the same count reaches well into
  small companies. So India's breadth is closer to a gauge of small and
  mid-sized stocks (§8).
- **The symbol list is today's** (a fixed ticker file). Stocks delisted since
  2015 are probably missing. Missing them likely leaves out some losers, so
  old readings may lean slightly strong.

## 3. The Breadth page, card by card

Each card shows today's value. A gauge ranks it against every day since 2015
("Only N in 100 days since 2015 were…"). A table compares it with one week, one
month and three months ago, because *"slow changes matter most: markets rarely
turn in a day."*

| Card (its real title) | What it shows | How to read it |
|---|---|---|
| **S&P 500 against its 50 DMA?** (Nifty 50 for India) | The index's % distance from its 50-day | The index's own short-term trend — the context |
| **Stocks at a 52w high or low?** | New highs and lows, and the typical day over two weeks | Leadership against damage; ranked on the 10-day average of highs − lows |
| **Stocks above their 5 & 50 DMA?** | % above the 5- and 50-day averages | 50-day: the average stock's trend; 5-day: short-term stretch |
| **Stocks rising or falling?** | Advancers and decliners, and the two-week typical day | Participation; ranked on the 10-day average of rising − falling |
| **Leading sectors, last 3 months?** | Best and worst sector against the average stock; sectors with most stocks above the 50-day | Where the strength is, and how widely shared |
| **Options: expected vs actual?** | VIX / India VIX against the index's realised volatility | See [the volatility guide](learn-health-volatility.md) |

Below the cards come:

- **What changed in the last 5 sessions**: 30% / 70% crossings, 90-day
  extremes, the index crossing its 50-day.
- Four **Charts**. The 50-day one has lines at **30% washout, 70% strong**.
- **Sectors: where the strength is?**
- **The last 30 days**, shaded where a reading is in its strongest or weakest
  fifth since 2015.

## 4. The measures

### 4.1 % above the 50-day — and the 5-day

The most useful single number: *for how many stocks is the trend up?*

| Since 2015 | US | India |
|---|---|---|
| Median % above 50-day | 59% | 56% |
| 10th–90th percentile | 29–77% | 21–82% |
| Days below 30% (the page's "washout") | 11% | 19% |
| Days below 15% | 3.5% | 4.8% |
| Days above 70% (the page's "strong") | 23% | 27% |

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

The **5-day** version is a short-term gauge of whether stocks have run up or
sold off too far, too fast. The US median is 54%. It is under 20% on about 8% of
days and over 80% on about 10%. Under 20% in an uptrend is a stretched
pullback. Over 80% is a poor moment to chase.

### 4.2 New 52-week highs and lows

Highs show **leadership**. A stock at a new high has no overhead supply: no
earlier buyers sitting at a loss and waiting to sell. That is where breakout and
trend strategies find candidates. Lows show **damage**. A typical US day since
2015 had about **46 highs and 7 lows** among the 1,000; India about **31 and
5**. In a panic the lows explode: **660** US lows on 12 March 2020 and **692**
in India the next day. Read the **net** (highs minus lows) and its 10-day
average, as the page does.

### 4.3 Advancers, decliners and the A/D line

Take rising stocks minus falling stocks each day, and add the result to a
running total. That running total is the **advance-decline line**. Its level
means nothing; what matters is its direction compared with the index. Suppose
the index makes a new high but the A/D line does not. Then fewer stocks took
part in the last leg up. The common NYSE version counts every issue listed.
The app's version has no thinly traded micro caps or bond funds in it.

### 4.4 Big movers: ±4% days and ±25% months

A median US day has **24** stocks up 4%+ and **23** down. The record is **944**
down on 12 March 2020. India is lopsided: **62** up and **24** down on a median
day, until a panic (**943** down on 23 March 2020). Many stocks up 25% in a
month means a hot market. Many down 25% means forced selling.

## 5. Divergences — the index at a high, fewer stocks with it

Here a **divergence** means the index makes a higher high while breadth makes a
lower one.

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

The S&P 500 gained about **30%** from the start of 2021 to its high on **3
January 2022**. Meanwhile breadth weakened for months. Net highs (10-day
average) peaked at **164** in May and were **53** on the final high. Only **33**
stocks made new highs that day.

The share above the 50-day (10-day average) fell in steps: about **83%** in
early January 2021, **73%** at the end of April, **61%** at the end of October,
**47%** at the end of December. On **10 December 2021** the index closed at a
record while net highs were *negative* (about −10). The Russell 2000 (an index
of small US companies) had peaked on **8 November 2021**.

The divergence did not time the top: it ran for half a year. What it said was
that risk was rising.

### 5.2 2024–2026: narrow highs come and go

Periods when a handful of giant companies led the index show up in the data in
bursts. At the **June 2024** highs only about **48%** of stocks were above their
50-day. Net highs averaged **28**, against **104** at the March 2024 highs. The
**19 February 2025** high had **57%** and a net of **37**. The index then fell
**19%** to 8 April. Late 2024 was broad again (median **69%** above the 50-day
on record days).

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

At the time of writing, the **6 October 2026** record had net highs (10-day
average) near **−24**. That is the lowest participation on any S&P 500 record
day since 2015. What follows is unknown. It is the situation in which breadth
says *size down*, not *sell everything*.

## 6. Washouts — when almost nothing is above its 50-day

The page calls **below 30%** a washout. The deep version is **below 10–15%**,
which happens on under 5% of days in either market. It has tended to come near
important lows. The table below lists each first close under 15% after a
recovery above 40%. It shows the S&P 500's change 21, 42 and 63 sessions later
(about one, two and three months).

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

Three months on, the S&P 500 was higher after **9 of 10** (median **+5%**).
Across all days since 2015 it was higher three months on **75%** of the time.
One month on, it was higher after only 7 of 10. The first washout day of
February 2020 was followed by a further **15%** fall. **A washout says the
selling is well advanced, not that it is over.**

**India** had **13** such episodes. The Nifty 50 was higher three months later
after **11** (median **+6.4%**). The exceptions:

- the small-company bear market of 2018: first day 28 September, low **3.9%**
  on 8 October, Nifty **−2.4%** three months on;
- March 2020: low **0.6%** on 23 March; Nifty **−6.1%** from the first day, 9
  March.

Two US washouts had **no Indian twin**. India's lowest reading was **43%** in
September 2022 and **32%** in October 2023.

**Small sample:** ten US and thirteen Indian episodes. No threshold here is a
buy signal.

## 7. Breadth thrusts — the other end of a washout

In a **breadth thrust**, the market goes from deeply oversold (most stocks
beaten down) to most stocks rising, within days. Martin Zweig's version takes
the share of advancing stocks, advancers ÷ (advancers + decliners), and
averages it over 10 days. A thrust is that average rising from below **0.40**
to above **0.615** within 10 sessions.

The app does not compute one. A simple version, built from the stored counts of
rising and falling stocks (`adv`, `dec`) with a 10-day exponential average,
fired **11** times in the US since 2015. Ten of them have a full year behind
them, and the S&P 500 was higher a year later after 9 of the 10. Three months
later it was higher after only **7 of 11**. Two fired inside the 2022 bear
market (March and September); the index was **18%** and **4%** lower three
months on. In India it fired 7 times. The Nifty was higher three months later
all 7 times, but a year later only 4 of 6.

**Read a thrust as "the washout is probably over", not "the bear market is
over".** Let the index's trend ([trend guide](learn-health-trend.md)) confirm
it.

## 8. India against the US

India's breadth runs **broader in rallies and deeper in sell-offs**. On Nifty
50 record days in 2023 the median share above the 50-day was **80–85%**. On
S&P 500 record days in 2024–25 it was mostly **50–70%**. The 2023–24 rally was
a boom in small and mid-sized companies. From the March 2023 low to late
September 2024 the Nifty Midcap 50 rose about **106%** and the Nifty 50 about
**54%**.

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

The 2024 top was a divergence of its own. Net highs (10-day average) peaked
near **153** in February 2024. They were about **72** at the Nifty 50's record
on **26 September 2024**. The washout that followed was India's deepest since
2020: **6.6%** above the 50-day on 3 March 2025. Yet the Nifty 50 was down only
about **16%** from its peak. Holders of small and mid-sized stocks did far worse
than the index suggested. That is the reason to watch India's breadth, not just
the Nifty.

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

- **Most:** the % above the 50-day at its extremes, and new lows expanding
  (damage is hard to fake).
- **Noisy:** daily advancers and decliners. Use the 10-day average.
- **Least, on their own:** divergences used for *timing* (2021's ran six
  months), and thrusts inside a bear market (2022).

**Combine** breadth with the index trend, credit and volatility
([liquidity and credit](learn-macro-liquidity-credit.md),
[volatility](learn-health-volatility.md)). Two warnings together matter far
more than one.

**What the app's strategies do with breadth.** The screener's market-regime
check (`core/regime.py`) computes the share of its stocks above the 20- and
50-day. But **no decision uses it**. The downgrade looks only at whether the
first two broad indices (SPY and QQQ; Nifty 50 and Nifty 500) are below their
50-day. Risk is halved only on the volatility index. Breadth is **your**
filter.

## 10. What the evidence says

- **Robust:** deep washouts cluster near major lows, and returns afterwards have
  been better than average. That holds in this data and in long NYSE studies
  (Zweig; Desmond on 90% down days).
- **Mostly true:** narrowing breadth comes before many tops (2021 US, 2024
  India). But the lead runs from weeks to many months, and narrow markets can
  keep rising (the stretches of 2023–24 led by a few giant companies).
- **Folklore:** that one divergence or one thrust times the market.
- **Measurement matters:** a different set of stocks gives other dates and
  levels. Compare a reading with its own history, as the page's ranks do.
- **Sample:** 2015 onwards holds about ten real washouts per market. §6–7
  describe what happened, not probabilities.

## 11. Checklist

- [ ] % above the 50-day: rising or falling over a month? Above 70%, below 30%?
- [ ] Net new highs (10-day): positive and expanding, or shrinking?
- [ ] New lows expanding while the index holds up?
- [ ] Index at a high with fewer stocks above the 50-day than at the last high?
- [ ] After a washout: a fast recovery or thrust, and the index back over its 50-day?
- [ ] India: is the Nifty hiding weakness in small and mid-sized stocks?
- [ ] "What changed in the last 5 sessions": any 30% / 70% crossing?
- [ ] Set this week's position count and size from the table in §9

## Further reading

- Martin Zweig, *Winning on Wall Street* — the breadth thrust.
- Gregory L. Morris, *The Complete Guide to Market Breadth Indicators*.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — breadth and stages.
- Paul Desmond, "Identifying Bear Market Bottoms and New Bull Markets" (2002) — 90% days.
- William J. O'Neil, *How to Make Money in Stocks* — leadership and the general market.
