# Relative strength — which stocks are beating the market, and what that is worth

Learning material on relative strength: how a stock is doing compared with the
market and with other stocks. The phrase has two meanings, the RS line and the
RS rank, and this guide covers both. It shows exactly how this app computes
them. It tests the classic claim that leaders show strength first, on real
stocks and on every liquid stock in three recent sell-offs. And it sets out
what the research and the app's own studies say about momentum, including when
it fails. For basic words, start with [learn-start-here.md](learn-start-here.md).
For a stock's trend, see [the stages guide](learn-price-stages.md); for the
strength of whole groups, [the sectors guide](learn-sectors-groups.md).

**Where this shows in the app.**

- **Screens**: the field **RS rank** (1–99) can be used in any screen, and
  screen results are sorted by it unless you choose otherwise. **Stage 2 —
  Trend Template** requires an RS rank of 70 or more (criterion C8). The preset
  **Strong stocks in leading groups** asks for RS rank 70+ in a peer group
  rated 80+.
- **Chart page**: add the study **Relative Strength vs index** (under Trend).
  It draws the RS line against SPY for US stocks and the Nifty 50 for Indian
  stocks, restated to 100 at the first bar, with a 50-bar average.
- **The company (Fundamentals) page** shows the stock's RS rank beside its
  ratios.
- **Screener reports**: the columns **RS vs index** and **RS vs sector**.
- **Markets → Sectors**: the RS rating of each group (see the sectors guide).

The code: the RS rank is computed in `scripts/swing_screener/screens/snapshot.py`
(`_rs_raw`, then ranked in `_finish`); the thresholds are in
`screens/criteria.py`; the backtest's version is `rs_ratings` in
`backtesting/spec.py`.

---

## 1. Two meanings of "relative strength"

| | **The RS line** | **The RS rank (or RS rating)** |
|---|---|---|
| What it is | The stock's price divided by an index's level, drawn as a line | A score from 1 to 99: where the stock's recent return ranks among all stocks |
| Compares the stock with | One index | Every other stock |
| Answers | "Is it beating the market right now, and since when?" | "How strong is it compared with everything else, over the past year?" |
| Speed | Shows a change the day it happens | Slow: most of its weight is on 6–12 months |
| Where in the app | Chart page study; the charts in this guide | Screens, company page, the Stage 2 rule |

Neither is the **RSI** (relative strength index). The RSI compares a stock's
recent up days with its own recent down days. It never looks at the market or
at other stocks. Despite the similar name it measures something different: how
fast the stock itself has moved lately. It is covered in [the momentum
indicators guide](learn-price-oscillators.md).

## 2. The RS line

### 2.1 What it shows

The RS line is the stock's closing price divided by the index's close, each
day. The level means nothing on its own. **Only the direction matters.**

- **Rising line**: the stock is doing better than the index. That is true
  even when both are falling. If the index falls 20% and the stock falls 5%,
  the RS line rises.
- **Falling line**: the stock is doing worse than the index, even if the
  stock is rising.
- **A new high in the RS line**: the stock has done better than the index
  over the whole period shown.

```series
title: Eli Lilly against the S&P 500, 2021–2024 — a rising RS line through a bear market
from: 2021-06-01
to: 2024-12-31
tf: W
line: us:LLY | Eli Lilly | log
line: us:LLY / us:SPX | RS line: Lilly ÷ S&P 500 | pane2
band: 2022-01-03 2022-10-12 | S&P 500 −25%
caption: From 3 January to 12 October 2022 the S&P 500 fell 25.4% while Lilly rose 19.4%; its RS line rose 60%. In the next twelve months Lilly rose 88%, the index 22%. The RS line peaked on 3 September 2024.
```

Lilly is the textbook case. Through the whole 2022 bear market its RS line
climbed. Its RS rank was 91 at the end of September 2022. It kept leading for
almost two more years: from 12 October 2022 to 3 September 2024 the price went
from 324.6 to 956.5. Section 4 shows that the textbook case is not the typical
case.

### 2.2 Reading it well

- **Use a log scale for the price** and look at the RS line's slope, not its
  level.
- **Pick the right index.** The app's Chart study uses SPY or the Nifty 50.
  For a small Indian company, the Nifty 500 or a midcap index is a fairer
  yardstick. The charts in this guide use the Nifty 500.
- **A small drift.** The app stores stock prices as traded: they are not
  raised for dividends paid. The S&P 500 and Nifty levels here are price
  indices, which also leave dividends out. So a stock that pays a much bigger
  dividend than the index looks slightly weaker on its RS line than it really
  was. Over a year the drift is about the difference in dividend yields:
  usually a point or two.
- **Compare the stock with its group too.** A stock can beat the market only
  because its whole group is moving. The group's own RS line is on its
  Sectors page.

## 3. The RS rank: how this app computes it

### 3.1 The formula

For each stock with at least a year (252 sessions) of history, the app adds up
four returns, all ending today:

**score = 2 × (3-month return) + 6-month return + 9-month return + 12-month return**

The months are 63, 126, 189 and 252 sessions. The 3-month return counts
twice, so the latest quarter has 40% of the weight and each earlier quarter
20%. That is the weighting usually described for IBD's RS rating (Investor's
Business Daily, the newspaper O'Neil founded). The app then sorts all the scores and
turns each into a number from 1 to 99: its **percentile**. **An RS rank of 80
means the stock's score beat about 80% of the stocks ranked that day.**

The score uses raw returns, not returns minus the index. That makes no
difference to the rank: subtracting the same index return from every stock
does not change their order.

### 3.2 Which stocks are ranked

- **In the daily snapshot** (what the Screens page reads), every stock in the
  snapshot with a year of history is ranked, tradable or not.
- **In a backtest** (`rs_ratings` in `backtesting/spec.py`), only stocks
  that clear a floor that day are ranked: a price of at least $10 (₹50), at
  least $5 million (₹10 crore) traded per day over 50 days, and about a
  year (260 sessions) of history. So a backtest's RS 70 and the screen's RS 70 are close but not
  identical numbers.

One effect of ranking every stock: weak stocks often fall below the
tradable floor. Among tradable US stocks on the average month-end since 2021,
about 644 had an RS rank of 70+ and only about 287 had 30 or less (India:
about 123 and 56).

### 3.3 The thresholds, by name

| Constant | Value | Where it is used |
|---|---|---|
| `RS_MIN_RANK` (`screens/criteria.py`) | 70 | Stage 2 screen, C8, when a whole market is screened |
| `RS_MIN_MOM` (`screens/criteria.py`) | 0.10 | C8 stand-in when one stock is checked alone: the 12-1 month return must be at least 10% |
| `LEADER_MIN_RS` (`screens/definitions.py`) | 70 | "Strong stocks in leading groups": the stock's own RS rank |
| `LEADER_GROUP_RS` (`screens/definitions.py`) | 80 | Same screen: the peer group's RS rating |
| `--min-rs` (backtest; `--spec` sets 70) | 70 | Minervini spec backtest: skip signals from stocks rated below 70 |

**The 12-1 month return** is the return from a year ago to a month ago. It
skips the latest month on purpose, for the reason in §5.1. The app uses it in
three places: as the single-stock stand-in for RS (C8 in the screen, M8 in the
Minervini strategy), as the "positive momentum" rule of the Established
uptrend screen (U6), and as the ranking of the momentum baseline portfolio.

### 3.4 The other RS numbers in the app

- **RS vs index** in a screener report is the stock's 3-month return minus
  the benchmark's 3-month return, in percentage points. The benchmark is SPY
  for the US and the Nifty 500 for India. **RS vs sector** is the same against
  the stock's sector index.
- **The Chart study** draws close ÷ benchmark close, restated to 100 at the
  first bar, with a 50-bar average (setting **MA length**).
- **Group RS rating** (Sectors page) uses the same 40/20/20/20 weights. But
  it measures each group against the typical stock, and ranks groups against
  each other. [The sectors guide](learn-sectors-groups.md) covers it.

### 3.5 What the rank is not

**It is a rank, not a return.** In a falling market a stock rated 90 can be
falling; everything else is just falling faster.

**It is slow.** Palantir's RS line fell 33% from 18 February to 10 March
2025, during that spring's sell-off. Its RS rank was still 97 at the end of
both February and March, because the 6–12-month returns were huge. The rank
tells you what the past year was like. The line tells you what is happening
now.

## 4. "Leaders show strength first" — tested

The classic claim, from O'Neil and Minervini, has two parts. First, a future
leader's RS line reaches a new high before its price does. Second, during a
market correction the future leaders hold up best, so the stocks with the
strongest RS lines at the market's low lead the next advance.

### 4.1 RS line new highs before price new highs

```series
title: Broadcom, 2021–2023 — the RS line made a new high four months before the price
from: 2021-10-01
to: 2023-12-31
tf: W
line: us:AVGO | Broadcom (split-adjusted) | log
line: us:AVGO / us:SPX | RS line: Broadcom ÷ S&P 500 | pane2
mark: 2023-01-06 | RS line above its May 2022 high
mark: 2023-05-18 | price above its December 2021 record
caption: On 6 January 2023 the RS line passed its May 2022 peak while the price was still 13% below its record. The price passed the record on 18 May. From 6 January to the end of 2023 Broadcom rose 90%, the S&P 500 22.5%.
```

Other cases from the stored data (each date is the first close above the
earlier high):

| Stock | RS line at a new high | Price at a new high | Lead |
|---|---|---|---|
| Broadcom (AVGO) | 6 January 2023 | 18 May 2023 | about four months |
| Nvidia (NVDA) | 17 May 2023 | 25 May 2023 | six sessions |
| Netflix (NFLX) | 8 April 2025 | 24 April 2025 | 11 sessions |
| Palantir (PLTR) | 25 April 2025 | 13 May 2025 | 12 sessions |

The pattern is real in these examples. It also follows from arithmetic. When
the market is below its own high, a stock can only reach its price high after
beating the market by a wide margin. So the RS line usually gets there first.
That makes it an early warning to look at the chart, not proof of a future
leader. §4.4 measures it across all stocks.

### 4.2 Strength during a correction: two stocks in 2025

```series
title: Two RS lines through the 2025 sell-off — Netflix and Palantir against the S&P 500
from: 2025-01-02
to: 2025-10-31
rebase: 100
line: us:NFLX / us:SPX | Netflix ÷ S&P 500
line: us:PLTR / us:SPX | Palantir ÷ S&P 500
band: 2025-02-19 2025-04-08 | S&P 500 −18.9%
caption: Both lines restated to 100 on 2 January. Netflix's RS line rose through the sell-off and made a new high on the low day; Palantir's fell 15%. Over the next six months Palantir rose 137%, Netflix about 40%.
```

From 19 February to 8 April 2025 the S&P 500 fell 18.9%.

- **Netflix** fell 16.6%: a little less than the index. Its RS line rose
  2.9% and made a new high on 8 April, the day of the low. The stock then rose
  54% to 30 June, against 24.5% for the index. That is the textbook pattern.
  Its RS line also peaked on 30 June 2025. By early October 2026 the stock
  was half its peak price and its RS rank had fallen from 92 (end of June
  2025) to 32 (end of December).
- **Palantir** fell 31%, much more than the index. Its RS line fell 15%. Then
  it rose 137% in six months (8 April to 8 October), against 35.5% for the
  index. **The next leader was one of the stocks that fell hardest.**

India had its own sell-off. The Nifty 500 fell 18.8% from 26 September 2024
to 28 February 2025.

```series
title: Muthoot Finance against the Nifty 500, 2024–2026
from: 2024-06-01
to: 2026-06-30
tf: W
line: india:MUTHOOTFIN.NS | Muthoot Finance | log
line: india:MUTHOOTFIN.NS / india:NIFTY500 | RS line: Muthoot ÷ Nifty 500 | pane2
band: 2024-09-26 2025-02-28 | Nifty 500 −18.8%
caption: The stock rose 4% while the index fell 19%; its RS line rose 28%. In the next twelve months it rose 57%, the Nifty 500 16.5%. Its RS line peaked on 29 January 2026.
```

Muthoot Finance (a gold-loan lender) rose 4.2% through the fall. Its RS rank
was 94 at the end of February 2025. From 28 February 2025 to 29 January 2026
the price went from 2,133 to 4,092.

### 4.3 Strength during a correction: every liquid stock

Single examples are chosen after the fact. So the same test was run on every
liquid stock in three sell-offs. The method:

- **Stocks**: price at least $10 (₹50) and at least $20 million (₹20 crore)
  traded per day over the 50 days before the market's peak, with a full year
  of history. A few ETFs are included.
- **Strength during the fall**: the change in each stock's RS line from the
  index's peak to its closing low. Stocks are split into fifths by it.
- **Afterwards**: each stock's return from the low, and the share of each
  fifth that beat the index. Medians, no costs, today's listed stocks only.

| Sell-off | Index fall | RS line rose for | Next period | Index | Strongest fifth: median | Beat the index | Weakest fifth: median | Beat the index |
|---|---|---|---|---|---|---|---|---|
| US, 3 Jan – 12 Oct 2022 (1,384 stocks) | −25.4% | 46% of stocks | 6 months | +15.7% | +5.7% | 26% | +6.0% | 41% |
| | | | 12 months | +21.0% | +4.2% | 25% | −3.3% | 28% |
| US, 19 Feb – 8 Apr 2025 (1,548) | −18.9% | 43% | 3 months | +26.0% | +7.3% | 14% | +46.0% | 78% |
| | | | 12 months | +36.8% | +12.7% | 21% | +58.3% | 57% |
| India, 26 Sep 2024 – 28 Feb 2025 (651) | −18.8% | 31% | 3 months | +15.4% | +12.6% | 46% | +25.6% | 73% |
| | | | 12 months | +10.9% | +2.8% | 38% | −2.7% | 31% |

**In all three sell-offs, the stocks that held up best did worse than the
typical stock afterwards** (in India over the first months; after a year they
were level with it). In 2025 the weakest fifth led the recovery by a wide margin. In
2022 the middle three fifths did best over twelve months; in India, the
second-strongest fifth did (+12.0%).

A stricter test: count only "leaders at the low", stocks whose RS line was
within 5% of its 52-week high *and* whose price was within 15% of its own
52-week high on the low day. Over the next six months, their median return
was +6.3% against +13.4% for the rest (US 2022, 157 stocks). It was +11.3%
against +27.0% (US 2025, 165), and +9.8% against +17.5% (India, 33).

**Who held up?** Mostly stocks that hold up in any sell-off:

- **2022**: energy (PBF Energy, Marathon Petroleum, ConocoPhillips, Exxon),
  plus drug makers and drug distributors (Lilly, McKesson, Vertex).
- **2025**: gold miners (Harmony, Kinross, Agnico Eagle), utilities (Con
  Edison, Duke, American Water) and insurers. Only 6 of the 165 had a
  beta of 1 or more over the year before the sell-off.

Much of their strength most likely came from the kind of business they are
(energy during an oil spike, defensive stocks in a fall), not from anything
new about the company. When the market turned up, money went back into the stocks that
had fallen most.

A last check: stocks that closed above their 52-week high within 30 sessions
of the low. That was 11% of US stocks after October 2022, 12% after April
2025 and 5% in India. Measured from the 30th session, they did no better than the
other stocks. In the US after 2022 the median was −7.7% over six months
against −3.2% for the rest. In India it was +2.8% against +5.8%. In the US
after April 2025 the two were about even over six months (+4.1% against
+3.1%), and the early-high stocks lagged over twelve (+6.2% against +13.4%).

**What this does and does not show.** It does not show that RS is useless:
§5 shows that the strongest stocks by RS rank did beat the weak ones on
average. It shows that **"held up in the sell-off" is not, by itself, a buy
signal at the low.** The holding up was mostly low beta and sector, and it
reversed when the market turned. Three episodes are a small sample. They are
also the most recent falls of close to 20% in each market, so they are not
cherry-picked.

### 4.4 RS line at a high, with and without the price

On every month-end from 2012 to 2026 (same liquidity floor), stocks were
sorted by whether the RS line and the price closed at a 52-week high that day.
The table shows their average return minus the average liquid stock's (the
**excess return**). The "t" figure is a t-statistic on the 1-month excess:
roughly, how far a result stands out from chance. About 2 or more is usually
taken as meaningful.

| Month-end group | Stocks per month | 1 month | 3 months | 6 months | Months it won (6M) |
|---|---|---|---|---|---|
| US: RS line and price at a 52-week high | about 24 | −0.02% (t −0.1) | +0.17% | +1.84% | 57% |
| US: RS line at a high, price 5%+ below its high | about 15 (in 25 months) | −0.39% (t −0.5) | +0.74% | +3.37% | 64% |
| US: price at a high, RS line not | about 45 | 0.00% (t 0.0) | +0.39% | +0.76% | 57% |
| India: RS line and price at a high | about 10 | +0.37% (t 0.9) | +1.67% | +5.59% | 72% |
| India: price at a high, RS line not | about 14 | +0.22% (t 0.5) | +1.16% | +1.32% | 58% |

**In India, the RS line and the price at a high together was clearly the
best combination over six months.** In the US every group was close to the
average. In both markets a price high without an RS high did less well than
both at a high. The "RS leads price" case was rare: only 25 of about 160 US
month-ends had three or more such stocks, and India too few to measure (9–10
months). Its US six-month figure is the largest in the table, but it rests on
too few months to trust (t −0.5 at one month).

## 5. The momentum evidence

"Momentum" in research means the same thing as a high RS rank: stocks that
rose most over the past months, compared with other stocks.

### 5.1 What the research found

- **Jegadeesh and Titman (1993)** sorted US stocks by their return over the
  past 3 to 12 months. Buying the past winners and selling the past losers
  earned about 1% a month over 1965–1989, before costs. The effect lasted
  for up to about a year; part of it reversed over the following years.
- **The one-month reversal.** Over a single month the effect runs the other
  way: last month's biggest winners tend to lag next month, and the biggest
  losers bounce (Jegadeesh 1990; Lehmann 1990). That is why the standard
  momentum measure is **12-1**: it skips the latest month.
- **Momentum works in many markets.** Asness, Moskowitz and Pedersen (2013)
  found it in stock markets around the world and in other asset classes.
- **Momentum crashes.** Daniel and Moskowitz (2016) showed that momentum's
  worst losses come in a specific situation: after a long market fall, when
  the market rebounds sharply. Past losers are then mostly high-beta stocks
  that have been beaten down, and they jump the most. Two of the worst cases
  in US history were the 1932 rebound and the March–May 2009 rebound. In each,
  a winners-minus-losers portfolio lost a large part of its value within
  months. §4.3 above is the same effect, seen in 2025.

### 5.2 The app's study: forward returns by RS rank

The same method as the Study tab on each screen (`screens/study.py`): on each
of the 62 month-ends from August 2021 to September 2026, tradable stocks were
grouped by their RS rank that day. The table shows each group's average
return over the next 1, 3 and 6 months minus the average tradable stock's.

| RS rank | US 1 month | US 3 months | US 6 months | India 1 month | India 3 months | India 6 months |
|---|---|---|---|---|---|---|
| 91–99 | −0.03% (t 0.0) | +0.16% | +2.82% | **+1.43% (t 2.1)** | +2.70% | +4.68% |
| 81–90 | +0.46% (t 1.8) | +1.20% | +2.56% | +0.54% (t 1.5) | +1.57% | +2.74% |
| 71–80 | +0.36% (t 2.4) | +0.80% | +1.32% | +0.11% (t 0.4) | +0.83% | +1.37% |
| 51–70 | +0.31% (t 2.3) | +0.76% | +0.90% | −0.32% (t −2.1) | −0.84% | −1.27% |
| 31–50 | +0.23% (t 1.2) | +0.33% | −0.26% | −0.24% (t −1.2) | −0.32% | −0.97% |
| 11–30 | −0.59% (t −1.6) | −1.50% | −3.17% | −0.35% (t −0.9) | −1.09% | −1.72% |
| 1–10 | **−5.59% (t −6.2)** | −12.55% | −18.56% | +0.17% (t 0.3) | −1.17% | −3.74% |

- **India**: the higher the rank, the better, almost step by step. The top
  group beat the average by about 1.4% a month.
- **US**: the clearest result is at the bottom. Stocks ranked 1–10 lagged by
  5.6% a month. Above the middle, the ranks 71–90 did best over one and three
  months. **The very top (91–99) gained nothing over the next month** and only
  caught up over six months. That fits the one-month reversal: the most
  extended stocks pause first.
- Taken as a screen, **RS 70+ alone** beat the average tradable stock by
  +0.28% a month in the US (t 1.2) and +0.52% in India (t 1.8). Over six
  months the excess was +2.0% and +2.6%.

Caveats: five years, one kind of market, no costs, equal weight. It uses
today's listed stocks only (**survivorship bias**: companies that failed and
were delisted are missing). That flatters the weakest groups most, so the
real gap at the bottom is probably wider. The 3- and 6-month windows overlap,
so only the 1-month t-figures are given.

**The one-month reversal, in the same data.** Sorted by last month's return
instead, the US top tenth lagged the next month by 0.68% (t −1.5) and the
bottom tenth by 1.20% (t −3.1). India showed no reversal (top tenth +0.32%,
t 0.7). So the textbook reversal is weak here. The useful part is the US
top-tenth result: **last month's biggest winners did not keep winning next
month.**

**When it went wrong.** The month-by-month gap between RS 91–99 and RS 1–10
had some very bad months. In the US, the worst was July 2026 (−23 points).
The second worst was January 2023, during the rebound that followed the
October 2022 low (−16 points). In India the worst was March 2025, the month straight after
the Nifty 500's 28 February low (−19 points). Two of the three worst months
came right after a market low. That is the momentum crash of §5.1.

### 5.3 Group RS

The group's strength adds to the stock's. In the app's group-strength study
([the study](group-strength-study.md)), tradable stocks in groups rated 80+
beat those in groups rated below 50 by 0.67% a month in the US (t 1.5) and
1.36% in India (t 2.9). Being the strongest stock *within* its group added
nothing. Details and the group charts are in [the sectors
guide](learn-sectors-groups.md).

### 5.4 Backtests

- **The momentum baseline** holds the strongest stocks by 12-1 momentum and
  rebalances monthly. In the app's research log
  ([momentum-trend-research.md](momentum-trend-research.md), 2013–2026), the
  top 50 Indian stocks above a ₹1 crore liquidity floor grew 29.0% a year
  against the Nifty 500's 11.7%, with a worst drawdown of −55%. The edge
  shrank as the floor rose: 2.6% a year for the top 20 with a ₹500 crore
  floor. In the US
  it did not beat SPY in eight of nine settings (top 50 with the 200-day
  filter: 9.3% a year against 12.8%). Those runs were measured before a cost
  fix that later moved re-measured results by up to about a point.
- **Ranking by momentum.** In the same log, the India Donchian strategy took
  the same signals ranked three ways. Ranked by 12-1 momentum it grew 13.8% a
  year; ranked at random, 6.1%. But its worst drawdown was deeper (−52.6%
  against −49.8%). Momentum ranking chose the same hot stocks at the same
  time.
- **Minervini SEPA.** Its backtest (`--spec`) skips any signal from a stock
  rated below 70, and fills free slots highest RS first. In the US run from
  2010 with the market filter (the current default), the RS rule skipped 874
  of 2,221 signals. No stored run switches the RS rule off, so this guide
  cannot say what the rule itself adds. Among the 490 trades it kept, a
  higher RS at entry did not mean better trades:

| RS at entry (Minervini SEPA backtest) | US trades | US average R | US win rate | India trades | India average R |
|---|---|---|---|---|---|
| 70–79 | 234 | +0.21R | 33% | 84 | +0.08R |
| 80–89 | 184 | −0.17R | 23% | 65 | +0.07R |
| 90–99 | 72 | +0.15R | 32% | 43 | −0.03R |

The US run is version 1.6 with `--market-filter`, entries 2010–2026, +0.06R
per trade overall. The India run is the latest full one (version 1.5, no
market filter, 192 trades, +0.05R). Both are backtests with modelled costs.
Once a stock clears 70, the exact rank told these backtests little.

## 6. Weaknesses

**RS ranks chase what has already moved.** By construction the rank is
highest after a big rise. That is when a stock is most stretched and has the
most holders sitting on gains.

```series
title: Super Micro, 2023–2024 — the 3-month gain peaked on the day of the top
from: 2023-07-01
to: 2024-12-31
line: us:SMCI | Super Micro (split-adjusted) | log
line: us:SMCI@chg63 | Super Micro, % change over 63 sessions | pane2 zero
line: us:SPX@chg63 | S&P 500, % change over 63 sessions | pane2
mark: 2024-03-13 | peak
caption: The 63-session change is the part the RS rank weights double. It peaked at +353% on 13 March 2024, the day of the price top (the S&P 500's was +12%). By 14 November the stock was 85% lower.
```

Super Micro's RS rank was 99 at the end of February, March and April 2024. At
the end of June it was still 98, with the price already 31% below its March
peak. It fell to 36 only at the end of August. The full story of that top is
in [the stages guide](learn-price-stages.md). In the momentum research log, a
US portfolio ranked on 3-month returns alone (top 20) lost 5.9% a year, with
a worst drawdown of −89.5% (measured before the cost fix mentioned in §5.4). Ranking on the short window is the most exposed
to this.

**Crashes after sharp market turns.** See §4.3 and §5.2. When a market
rebounds hard from a deep fall, the weakest stocks lead for weeks to months.
A high-RS list is then full of defensive stocks that lag.

**The rank lags; the line is noisy.** The rank needs months to fall (Super
Micro). The line flips with every short move. Use them together.

**It says nothing about why.** A stock can rank high because of a takeover
bid, a one-off event or a squeeze (forced buying by short sellers). None of
that is a trend to follow. Check the chart and the news.

**India's smaller universe.** About 300 tradable stocks means one sector's
run can fill the top of the list. Check the group column before you treat
"ten stocks rated 95" as ten separate ideas.

## 7. What the trader does

- **Use RS to choose where to look, not when to buy.** RS 70+ (better, 80+)
  and a strong group narrow the list. The entry still comes from the chart: a
  base, a pivot, a stop ([the bases guide](learn-bases.md), [the VCP
  guide](learn-vcp.md)).
- **Prefer the RS line and the price at new highs together.** In §4.4 that
  combination did best in India, and a price high without an RS high did
  worse in both markets. An RS line at a new high while the price is still
  in its base is a reason to watch the stock closely, not to buy early.
- **Do not buy "the stocks that held up" at a market low just because they
  held up.** Check what they are. Gold miners, utilities and staples holding
  up in a sell-off is normal. A growth stock in a leading group holding up
  near its high is the rarer, more useful signal (Netflix in April 2025).
  After a sharp low, expect beaten-down stocks to lead the first weeks. Keep
  positions small until breakouts from sound bases appear.
- **Be wary of the most extended names.** An RS rank of 99 with a 3-month
  gain of several hundred percent is the Super Micro pattern. Size smaller or
  wait for a new base.
- **Watch the RS line of what you own.** A rising market with a falling RS
  line in your stock means money is going elsewhere. A break of the RS line's
  uptrend often comes before the price breaks (Netflix after June 2025).
- **In India, compare with the Nifty 500 or a midcap index**, not only the
  Nifty 50.

## 8. What the evidence says

- **Robust:** momentum over 3–12 months is one of the best-documented return
  patterns in finance, across many markets (Jegadeesh and Titman;
  Asness, Moskowitz and Pedersen). In this app's data, high-RS stocks beat
  low-RS stocks in both markets over 2021–2026. India's result was the more
  orderly one; the US result came mostly from the very weak stocks doing very
  badly.
- **Robust:** momentum has rare, severe crashes, and they come after sharp
  market rebounds (Daniel and Moskowitz). The app's data shows the same after
  October 2022 (US) and February 2025 (India).
- **Weaker:** that a *higher* rank above 70 is better. In the US screen
  study and in the Minervini backtest, the top ranks did not beat the 70s and
  80s.
- **Folklore, at least as usually stated:** that the stocks holding up best in
  a correction become the next leaders. In the three sell-offs measured here,
  they did worse than average afterwards. Single cases like Lilly in 2022 and
  Netflix in 2025 are real, but they are not the rule.
- **Not measured here:** what Minervini's RS 70 rule adds to his strategy's
  trades, since no stored backtest switches it off.

## 9. Checklist

- [ ] RS rank of the stock: 70+? Rising or falling over the last month?
- [ ] RS line: rising? At a new high together with the price?
- [ ] Group RS rating 80+? Is the stock's strength just its group's?
- [ ] Is the rank high because of a huge 3-month gain? How far above the 50-day is the price?
- [ ] Market just turned up from a deep fall? Expect laggards to lead for a while; size down.
- [ ] Holdings: any RS line breaking down while the market rises?
- [ ] India: compared against the Nifty 500 or midcaps, not only the Nifty 50?

## Further reading

- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and
  Selling Losers: Implications for Stock Market Efficiency" (Journal of
  Finance, 1993) — the founding momentum paper.
- Narasimhan Jegadeesh, "Evidence of Predictable Behavior of Security Returns"
  (Journal of Finance, 1990) — the one-month reversal.
- Kent Daniel and Tobias Moskowitz, "Momentum Crashes" (Journal of Financial
  Economics, 2016) — when and why momentum fails.
- Clifford Asness, Tobias Moskowitz and Lasse Pedersen, "Value and Momentum
  Everywhere" (Journal of Finance, 2013).
- William O'Neil, *How to Make Money in Stocks* — the "L" in CAN SLIM:
  leader or laggard, and the RS rating.
- Mark Minervini, *Trade Like a Stock Market Wizard* — the Trend Template's
  RS rule and the RS line in a correction.
