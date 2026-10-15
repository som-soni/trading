# App notes moved out of learn-price-rs (verbatim)

## Intro (app framing)
Learning material on relative strength: how a stock is doing compared with the
market and with other stocks. The phrase has two meanings, the RS line and the
RS rank, and this guide covers both. It shows exactly how this app computes
them. It tests the classic claim that leaders show strength first, on real
stocks and on every liquid stock in three recent sell-offs. And it sets out
what the research and the app's own studies say about momentum, including when
it fails. For basic words, start with [learn-start-here.md](learn-start-here.md).

## "Where this shows in the app" and the code
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

## §1 table row "Where in the app"
| | **The RS line** | **The RS rank (or RS rating)** |
|---|---|---|
| What it is | The stock's price divided by an index's level, drawn as a line | A score from 1 to 99: where the stock's recent return ranks among all stocks |
| Compares the stock with | One index | Every other stock |
| Answers | "Is it beating the market right now, and since when?" | "How strong is it compared with everything else, over the past year?" |
| Speed | Shows a change the day it happens | Slow: most of its weight is on 6–12 months |
| Where in the app | Chart page study; the charts in this guide | Screens, company page, the Stage 2 rule |

## §2.2 Reading it well (app chart study, stored prices, Sectors page)
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

## §3 The RS rank: how this app computes it (3.1 formula wording, 3.2 which stocks are ranked, 3.3 thresholds, 3.4 other RS numbers)
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

## §5.2 The app's study (method line)
### 5.2 The app's study: forward returns by RS rank

The same method as the Study tab on each screen (`screens/study.py`): on each
of the 62 month-ends from August 2021 to September 2026, tradable stocks were
grouped by their RS rank that day. The table shows each group's average
return over the next 1, 3 and 6 months minus the average tradable stock's.

## §5.3 Group RS (app study reference)
### 5.3 Group RS

The group's strength adds to the stock's. In the app's group-strength study
([the study](group-strength-study.md)), tradable stocks in groups rated 80+
beat those in groups rated below 50 by 0.67% a month in the US (t 1.5) and
1.36% in India (t 2.9). Being the strongest stock *within* its group added
nothing. Details and the group charts are in [the sectors
guide](learn-sectors-groups.md).

## §5.4 Backtests (owner's backtests — removed from the guide)
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

## §6 (momentum research log figure — removed)
in [the stages guide](learn-price-stages.md). In the momentum research log, a
US portfolio ranked on 3-month returns alone (top 20) lost 5.9% a year, with
a worst drawdown of −89.5% (measured before the cost fix mentioned in §5.4). Ranking on the short window is the most exposed
to this.

## §6 India universe note
**India's smaller universe.** About 300 tradable stocks means one sector's
run can fill the top of the list. Check the group column before you treat
"ten stocks rated 95" as ten separate ideas.

## §8 evidence bullets referring to the app's data/backtests
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

