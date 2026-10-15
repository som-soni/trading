# Stages and trend in a stock — where a stock is in its life, and whether to own it

Learning material on the trend of a single stock. It covers Stan Weinstein's
four stages, read off the 30-week (about 150-day) moving average. It covers
Mark Minervini's Trend Template exactly as this app checks it, and how often
stocks pass it. It walks through three real charts: a Stage 2 start, a full
four-stage cycle, and a stretched late Stage 2 that turned into a fast
decline. Then it measures how long Stage 2 lasts and what the app's own
studies and backtests say. [The index trend guide](learn-health-trend.md) does
the same for the whole market; this guide is about one stock. For the basic
words (moving average, 52-week high), start with
[learn-start-here.md](learn-start-here.md).

**Where this shows in the app.** **Screens → Stage 2 — Trend Template** lists
the stocks that pass Minervini's eight conditions today. Its **Study** tab
shows how those stocks did over the following months. Three looser trend
screens sit beside it: **Established uptrend**, **Near highs, rising 200-day**
and **Above the 200-day**. The rules are in
`scripts/swing_screener/screens/criteria.py` (criteria C1–C8 — the Minervini strategy and some other guides call the same
eight checks M1–M8), and the screen
conditions in `screens/definitions.py`. The Minervini SEPA strategy draws its
candidates from the Stage 2 screen. On the Chart page you can add a **Moving
Average** study (set the length to 150 or 200). You can also add **Pivot Points
High Low (swing pivots)** with the labels set to *Structure (HH/HL/LH/LL)*,
which marks higher highs and higher lows for you.

---

## 1. A stock's life in four stages

Weinstein noticed that most stocks move through the same four phases, over and
over. He read them off one line: the **30-week moving average** of weekly
closes. On a daily chart the nearest equivalent is the **150-day** average
(30 weeks × 5 sessions).

| Stage | What the price does | The 30-week line | Who is in control |
|---|---|---|---|
| **1 — Basing** | Moves sideways after a long fall; crosses the line back and forth | Stops falling, goes flat | Neither side. Sellers are running out |
| **2 — Advancing** | Makes higher highs and higher lows, stays above the line | Rising | Buyers. Demand is larger than supply |
| **3 — Topping** | Moves sideways after a long rise; swings get wider; crosses the line | Stops rising, goes flat | Neither side. Big holders are selling into strength |
| **4 — Declining** | Makes lower highs and lower lows, stays below the line | Falling | Sellers. Supply is larger than demand |

**Weinstein's rule is short: buy in Stage 2, own nothing in Stage 4.** Stage 1
can last for years and pays nothing while you wait. Stage 3 often looks like a
base, but the buyers are now the late ones. A stock can also skip from Stage 2
straight to Stage 4 when bad news hits.

Why do stages exist at all? Because large investors cannot buy or sell a big
position in a day. A fund that wants to own a stock buys for months, and that
steady buying is Stage 2. When funds decide to leave, they sell for months, and
that is Stage 4. [The supply and demand guide](learn-supply-demand.md) explains
the mechanism at the level of single price zones.

## 2. Reading the stage: position, slope and swings

Three questions tell you the stage. Ask them in this order.

### 2.1 Is the price above or below the average?

Above the 150-day (or 200-day) average, the buyers of the last several months
are, on average, in profit. Below it they are, on average, holding a loss, and
many will sell when they get back to what they paid. In a strong Stage 2 the
price can stay above the 150-day for more than a year: in Trent's 2023–24
advance (§4) it did not close below it once in 358 sessions.

### 2.2 Which way is the average sloping?

**A price above a falling average is a bounce, not an uptrend.** The slope is
what separates Stage 1 from Stage 2, and Stage 3 from Stage 4. The app uses
simple, fixed definitions, so a screen gives the same answer every time:

| Test | The app's rule | Where it is used |
|---|---|---|
| 200-day **rising** (Trend Template) | Higher than it was 21 sessions ago | Stage 2 screen, C5 |
| 200-day **falling** | More than 0.5% below its value 20 sessions ago | Near highs screen, H2 |
| 50-day **falling** | More than 1% below its value 10 sessions ago | Established uptrend screen, U4 |
| 30-week line rising (weekly) | The 30-week exponential average is above last week's value, and the weekly close is above it | Established uptrend screen, U1 |

Between "rising" and "falling" the app calls an average **flat**. A flat
200-day after a long rise is the first sign of Stage 3. A flat one after a long
fall is the first sign of Stage 1.

### 2.3 Are the swings rising or falling?

A trend is, before anything else, a sequence of swings: swing highs, and swing
lows (troughs with higher prices on both sides). **An uptrend makes
higher highs and higher lows. A downtrend makes lower highs and lower lows.**

Swings turn before averages do, because an average needs months of prices to
change direction. So read swings for the early warning and the average for
confirmation. The Established uptrend screen checks this directly (U5): the
last two confirmed swing lows of the past ~50 sessions must be rising. A swing
low counts as confirmed when its low is the lowest of the seven bars centred on
it (three on each side).

## 3. Worked example: Nvidia, 2021–2023 — from Stage 4 to an early Stage 2

```series
title: Nvidia and its 150-day average, 2021–2023
from: 2021-06-01
to: 2023-12-31
tf: W
line: us:NVDA | Nvidia (split-adjusted) | log
line: us:NVDA@sma150 | 150-day average (≈ 30 weeks)
band: 2021-11-29 2022-10-14 | Stages 3 and 4
band: 2022-10-14 2023-01-31 | Stage 1
mark: 2022-10-14 | 2022 low
mark: 2023-04-14 | passes the Trend Template
caption: Lower highs all through 2022, a higher low in late December, the average turning up in February 2023 — and the Trend Template only passing in April, 138% off the low.
```

Prices here are adjusted for later stock splits, so they are lower than the
prices quoted at the time.

- **Stage 3 to 4.** Nvidia closed at a record 33.38 on 29 November 2021. Its
  200-day average stopped rising on 11 May 2022.
- **Stage 4.** Each rally stopped lower than the one before: swing highs of
  28.7 (29 March), 19.6 (2 June), 19.2 (4 August) and 18.1 (13 December 2022).
  The lows fell too, to 11.23 on 14 October 2022: 66% below the record.
- **Stage 1.** The price first closed back above its 150-day on 11 November
  2022 and above its 200-day on 12 December. On 28 December it made a low of
  14.0, **above** the October low. That higher low is the first swing that
  points up.
- **Stage 2.** The 150-day stopped falling in mid-January 2023 and was rising
  by 1 February. The 50-day crossed above the 200-day on 24 January. The 200-day
  itself was rising again by 22 February.
- **The Trend Template passed on 14 April 2023**, at 26.76. By then the stock
  was already 138% above its October low. It then rose another 88% to 50.41 on
  20 November 2023.

**The lesson: the Trend Template confirms Stage 2; it does not find its first
day.** Its 200-day test needs months of rising prices. A trader who reads the
swings and the 30-week line sees Stage 2 forming earlier, at a lower price, but
with less certainty. Many Stage 1 bases fail and sink again.

## 4. Worked example: Trent, 2022–2025 — a full four-stage cycle

```series
title: Trent and its 150-day average, 2022–2025
from: 2022-01-01
to: 2025-12-31
tf: W
line: india:TRENT.NS | Trent | log
line: india:TRENT.NS@sma150 | 150-day average (≈ 30 weeks)
band: 2022-01-01 2023-05-29 | Stage 1
band: 2023-05-30 2024-10-11 | Stage 2
band: 2024-10-11 2025-01-17 | Stage 3
band: 2025-01-20 2025-12-31 | Stage 4
mark: 2023-05-30 | breaks out of the range
mark: 2024-10-11 | peak
caption: Eighteen months sideways, sixteen months up (+428% from the breakout), three months of churning at the top, then a decline of half.
```

| Stage | Dates | What happened |
|---|---|---|
| 1 | Late 2021 – May 2023 | A range between about 998 (December 2021) and 1,558 (1 November 2022). The 150-day went flat; it was rising again from 1 March 2023 |
| 2 | 30 May 2023 – 11 Oct 2024 | First close above the 2022 high on 30 May 2023. Trend Template passed from 1 August 2023 at 1,708. Peak close 8,235 on 11 October 2024 |
| 3 | Oct 2024 – Jan 2025 | Closes between about 6,160 and 8,190. Last Trend Template pass on 6 January 2025 |
| 4 | Jan 2025 onward | First close below the 150-day on 10 January, below the 200-day on 20 January; the 150-day was falling from 18 February. Low of 4,018 on 10 December 2025, 51% below the peak |

**Stage 2 was a staircase.** The swing lows rose from 1,666 (July 2023) to
1,992 (October 2023), 3,027 (February 2024) and 5,166 (July 2024). The swing
highs rose with them. The stock closed below its 50-day on only 5 of 358
sessions, and below its 150-day on none.

**Stage 3 showed in the swings before the averages.** After the 11 October
peak the stock fell 6.5% on 7 November 2024, on 4.5 times its average volume.
It held a low of 6,299 the next day. A second low on 20 December (6,832) was
higher, so the structure was still intact. But the rally that followed stopped
at 7,321 on 2 January 2025 — a **lower high**. On 14 January the price closed
at 6,161, below the November low. That was the first lower low. The price had
closed below its 150-day four days earlier, on 10 January, and closed below its
200-day on 20 January. The 150-day itself only turned down a month later.

## 5. Worked example: Super Micro, 2022–2024 — late Stage 2, and a fast Stage 4

```series
title: Super Micro Computer and its 150-day average, 2022–2025
from: 2022-07-01
to: 2025-06-30
tf: W
line: us:SMCI | Super Micro (split-adjusted) | log
line: us:SMCI@sma150 | 150-day average (≈ 30 weeks)
line: us:SMCI / us:SMCI@sma200 | Price ÷ its 200-day | pane2
band: 2024-03-13 2024-08-01 | Stage 3
mark: 2024-03-13 | peak
caption: The lower pane shows how stretched the price was: 3.2 times its 200-day at the March 2024 peak. Five months of lower highs followed, then a fall of 85%.
```

Super Micro rose from a low of 3.90 on 5 July 2022 (split-adjusted) to 118.8 on
13 March 2024. That is about thirty-fold in 20 months. It passed the Trend
Template on and off through 2022, and on most days of November and December,
while the S&P 500 was in a bear market.

**The late stage was easy to see in one number: distance from the average.**
In February 2024 the price stood at 3.4 times its 200-day average. At the peak
it was 3.2 times. A stock that far above its long-term average has run far
ahead of what most holders paid. Any selling then has a long way to fall before
it reaches buyers.

Stage 3 then lasted about five months:

- **Lower highs:** 118.8 (13 March), 95.2 (15 May), 92.0 (18 June), 91.0
  (12 July).
- **The averages held for a while:** first close below the 50-day on 12 April;
  last Trend Template pass on 15 May; first close below the 150-day on 24 July.
- **The break:** on 7 August 2024 the stock fell 20% in a day, on 2.7 times its
  average volume. That took it below the April low of 71.4 — the first lower
  low. It had closed below the 200-day on 2 August.
- **Stage 4:** on 28 August it fell another 19% on 4.7 times average volume.
  That followed a short-seller's report (a published case that the stock will
  fall) and a delay to the company's annual filing. The
  150-day was falling from 16 September. The low was 18.01 on 14 November 2024,
  85% below the peak.

**Extension alone does not mark the top.** Trent was 64% above its 150-day in
February 2024 and still had eight months of rise ahead. Extension tells you
the risk is high. The lower highs and the first lower low tell you the stage
has changed.

## 6. Minervini's Trend Template, exactly as the app checks it

Minervini turned Stage 2 into eight yes/no rules. A stock must pass **all** of
them. The app's version (screen **Stage 2 — Trend Template**):

| Code | Rule | Setting in `screens/criteria.py` |
|---|---|---|
| C1 | Close above the 50-day average | — |
| C2 | Close above the 150-day average | — |
| C3 | Close above the 200-day average | — |
| C4 | 50-day above the 150-day, and 150-day above the 200-day | — |
| C5 | 200-day higher than it was 21 sessions ago (rising for at least a month) | `SMA200_RISING_BARS` = 21 |
| C6 | Close at least 30% above the 52-week low | `MIN_PCT_ABOVE_52W_LOW` = 30 |
| C7 | Close within 25% of the 52-week high | `MAX_PCT_BELOW_52W_HIGH` = 25 |
| C8 | RS rank of 70 or more | `RS_MIN_RANK` = 70 |

The 52-week high and low are the highest high and lowest low of the last 252
sessions. All averages are simple averages of daily closes.

**How RS rank is computed.** RS rank means relative strength rank: where the
stock's recent performance stands against every other stock. For each stock
with a year of history the app adds up four returns: twice the 3-month return,
plus the 6-month, 9-month and 12-month returns. The recent quarter therefore
counts double. It then ranks all stocks from 1 to 99. **An RS rank of 70 means
the stock did better than about 70% of the market.** When the app checks a
single stock, or runs a backtest, there is no whole market to rank against. It
then uses a stand-in: the 12-1 month return must be at least 10%
(`RS_MIN_MOM` = 0.10). That is the return from a year ago to a month ago,
skipping the latest month. [The relative strength guide](learn-price-rs.md)
covers RS in depth.

Before any of this, a stock must clear the market's **tradable floor**: in the
US a price of at least $10 and at least $10 million traded per day on average
over 20 days; in India at least ₹50 crore a day (no price floor). It also needs
a year of history.

Minervini's book is looser in two places. It asks for the 200-day to rise for
at least a month, preferably four to five. And it treats 70 as the minimum RS,
preferring 80–90. The app uses the minimums, so a stricter trader can add their
own conditions in the screen builder.

### 6.1 How often stocks pass

Counted on the app's stored month-end snapshots (August 2021 to September
2026, 62 month-ends), among tradable stocks:

| | US | India |
|---|---|---|
| Tradable stocks per month-end (average) | about 1,760 | about 305 |
| Passing all eight (average) | about 335 | about 72 |
| Share passing, median month | 19% | 22% |
| Lowest | 2.5% (40 stocks, 30 June 2022) | 2.8% (9 stocks, 28 February 2025) |
| Highest | 32% (540 stocks, 30 August 2024) | 43% (151 stocks, 31 May 2024) |
| Latest (30 September 2026) | 12% (260 of 2,131) | 28% (118 of 415) |

**The pass rate is a breadth reading in its own right.** In the US it fell to
2.5% at the end of June 2022, in the middle of that year's bear market. In
India it fell to 2.8% at the end of February 2025, when the Nifty Midcap 50 was
20% below its September 2024 high. When fewer
than one stock in twenty passes, the few that do are worth a close look: they
are the ones holding up while the market falls.

Which rule cuts the most? On the average month, these shares of tradable stocks
passed each condition on its own:

| Condition | US | India |
|---|---|---|
| Close above the 50-day | 52% | 59% |
| Close above the 200-day | 55% | 65% |
| 200-day rising | 58% | 68% |
| At least 30% above the 52-week low | 53% | 64% |
| Within 25% of the 52-week high | 67% | 74% |
| RS rank 70+ | 37% | 39% |

The RS rule is the hardest single test, by design. The others mostly ask the
same question — is the stock in an uptrend? — so they pass and fail together.
That is why all eight together still pass about one stock in five.

## 7. Early Stage 2, late Stage 2, Stage 3: telling them apart

| | Early Stage 2 | Late Stage 2 | Stage 3 |
|---|---|---|---|
| Distance above the 200-day | Modest: the price close to its rising averages | Large: the price far above its averages | Shrinking as the price churns |
| Base count | First or second base | Third, fourth or later | The "base" is the top |
| Swings | Higher highs and higher lows | Still higher, but the moves are steeper | First lower high, then a lower low |
| 150/200-day | Just turned up | Rising steeply | Flattening |
| Volume | Heavy on up days | Climax days: the biggest gains on the heaviest volume | Heavy on down days |
| What to do | Buy sound breakouts | Hold winners; new buys smaller, stops tighter | Sell into strength; no new buys |

Base counting is covered in [the bases guide](learn-bases.md). Volume patterns
are in [the volume guide](learn-price-volume.md).

## 8. How long does Stage 2 last?

To put a number on it, the app's stored daily prices were scanned for **fresh
Trend Template passes**: the first day a stock passed all eight rules after six
months (126 sessions) without passing. The RS rule used the single-stock
stand-in (12-1 month return of 10%+). The stock had to clear today's tradable
floor that day. Qualification dates run from 2005 to the end of 2024. Each
case was followed until the stock **stopped being above a rising 200-day**:
the first close below the 200-day, or the first day the 200-day was no higher
than 21 sessions earlier. This was run for this guide on stored data; it is
not a backtest, and it has no costs.

| After a fresh pass | US | India |
|---|---|---|
| Cases (stocks) | 8,455 (2,034) | 884 (354) |
| Median sessions above a rising 200-day | 107 (about five months) | 124 (about six months) |
| Middle half of cases | 57 to 175 sessions | 65 to 220 sessions |
| Ended within 3 months (63 sessions) | 28% | 24% |
| Lasted more than a year (252 sessions) | 11% | 19% |
| Median sessions to the first close below the 150-day | 79 | 91 |
| Median best gain before the end | +13% | +20% |
| Share that gained 50%+ at some point / doubled | 14% / 5% | 28% / 13% |
| Median return at the end (exit on the 200-day rule) | −3.8% | −2.5% |
| Average return at the end | +4.2% | +16% |

The picture is the same in both markets. **A typical Stage 2, measured from the
day it qualifies, lasts five to six months. The typical one makes little money
if you wait for the 200-day to break before selling.** Only 40% of US cases and
46% of Indian ones were up at that point. The average is pulled up by a
minority of long runs:

| | US | India |
|---|---|---|
| Runs that ended within 3 months: median return at the end | −11% | −14% |
| Runs that lasted more than a year: median return at the end | +43% | +66% |
| Runs that lasted more than a year: median best gain | +69% | +106% |

Two warnings. The sample uses only stocks still in the database, so companies
that went bust are under-counted. And the two sets differ: India's ₹50 crore
floor is in today's rupees, so most Indian cases come from 2020 onward, while
the US cases spread across 2005–2024. Read the shape, not the decimals.

## 9. What the app's own evidence says

### 9.1 The screen study

The **Study** tab on each screen applies the screen on every month-end
snapshot, then compares the qualifiers' returns over the next 1, 3 and 6 months
with the average tradable stock. Recomputed for this guide with the same method
(screens/study.py), on the 62 month-ends from August 2021:

| Stage 2 — Trend Template | US | India |
|---|---|---|
| 1-month excess return | +0.46% (t 1.5) | +0.93% (t 2.4) |
| 3-month excess | +0.63% | +1.84% |
| 6-month excess | +2.53% | +2.67% |
| Hit rate (share of qualifiers beating the median stock), 6 months | 53% | 52% |
| Month-ends on which qualifiers won, 6 months | 75% | 62% |

"Excess" is the qualifiers' average return minus the average tradable stock's.
The "t" figure is a t-statistic: roughly, how far the result stands out from
chance (about 2 or more is usually taken as meaningful). It is computed on
1-month returns only, because the 3- and 6-month windows overlap. The looser
screens, over six months, for comparison:

| 6-month excess | US | India |
|---|---|---|
| Established uptrend | +2.01% | +1.38% |
| Near highs, rising 200-day | +1.64% | +1.23% |
| Above the 200-day | +1.50% | +0.84% |

**The stricter the trend screen, the better its stocks did**, in both markets.
That is the order you would expect if the trend itself carries information.
But look at the hit rate: only just over half of Stage 2 stocks beat the
median stock. **The edge comes from a minority of big winners, not from most
qualifiers doing well.** That matches §8. The study covers five years, no
costs, and stocks that survived.

### 9.2 Backtests that rely on it

A screen only says which stocks to look at. The strategies built on Stage 2
have not shown an edge:

- **Minervini SEPA** (Stage 2 plus a volatility contraction pattern entry, see
  [the VCP guide](learn-vcp.md)). Its status on the Strategies page reports the
  US backtest from 2010 with the market filter on (no new buys while the
  benchmark index is below its 200-day). It made 490 trades at +0.06R each, for
  1.34% a year against the index's ~13%. In India, the version that buys with a
  stop order just above the base made 114 trades at −0.03R each. These are
  backtests with modelled costs.
- **The momentum baseline** holds the 50 strongest stocks by 12-1 month return.
  In the app's research log (US, 2013–2026), requiring each stock to be above
  its own 200-day cut the annual return from 15.6% to 9.3%. The worst drawdown
  did not improve (−50.3% with the filter, −45.7% without). Those runs were
  measured before a later cost fix that moved results by up to about a point.

So a stock-level trend filter **narrows the list to better-than-average
stocks** (§9.1). It does not, by itself, make a profitable trading system, and
selling a strong stock just because it dipped under its 200-day cost the
momentum portfolio money.

## 10. What the trader does

1. **Check the market's stage first** ([learn-health-trend.md](learn-health-trend.md)).
   Most stocks move with the market. Traders hold that breakouts fail more
   often while the index falls; that guide explains why, and that the app has
   not measured it.
2. **Fish in the Stage 2 list.** Start from the Stage 2 screen. When it is
   short, look at the names that stay on it: they are the leaders.
3. **Prefer early Stage 2.** The 30-week line just turned up, a first or
   second base, the price not far above its 200-day. A stock three times its
   200-day is late, however strong it looks.
4. **Buy a setup, not a stage.** Stage 2 says *which* stock. The entry comes
   from a base and a breakout ([learn-bases.md](learn-bases.md),
   [learn-vcp.md](learn-vcp.md)), with a stop under it
   ([learn-risk-stops-exits.md](learn-risk-stops-exits.md)).
5. **Watch the swings in the stocks you own.** The first lower high, then a
   lower low, is the Stage 3 warning. Sell into strength or tighten the stop.
   Do not wait for the 200-day: by then Trent was 26% off its peak and Super
   Micro 47%.
6. **Own nothing in Stage 4.** A stock below a falling 30-week line is not
   cheap; it is in a downtrend. Put it on a watchlist for the next Stage 1.

## 11. What the evidence says

- **Robust:** stocks in Stage 2 have, on average, done better than other
  stocks over the next months — in this app's five-year study in both markets,
  and in many published momentum studies. Stricter trend screens did better
  than looser ones here.
- **Robust:** the gain is concentrated. Only about half of Stage 2 stocks beat
  the median stock, and the typical Stage 2 run lasted five to six months.
- **Lags are built in.** The Trend Template passed Nvidia 138% off its low.
  The 200-day rule confirmed Trent's top more than three months late. Swings
  turn first; averages confirm.
- **Not shown here:** that the Trend Template plus a chart pattern beats the
  index. The app's Minervini backtests do not. Nor that selling a stock below
  its own 200-day protects a momentum portfolio; in the US test it hurt.
- **Folklore:** that a stage can be named exactly in real time. Stages are
  clear in hindsight. On the day, Stage 1 and Stage 3 look alike, and many
  Stage 1 bases fail.

## 12. Checklist

- [ ] Market stage: index above a rising 30-week line?
- [ ] Stock passes the Trend Template (or misses only on RS or the 200-day slope)?
- [ ] 150-day: rising, flat or falling? Has it changed this week?
- [ ] Swings: last high and last low higher than the ones before?
- [ ] How far above the 200-day? Early (modest) or late (stretched)?
- [ ] Base count: first or second base, or later?
- [ ] Open positions: any lower high followed by a lower low? Any stock now below a flattening 150-day?
- [ ] Stage 2 pass rate on the screen this week: rising or falling?

## Further reading

- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — the four
  stages and the 30-week moving average.
- Mark Minervini, *Trade Like a Stock Market Wizard* — the Trend Template and
  Stage 2 as the precondition for every buy.
- William O'Neil, *How to Make Money in Stocks* — leaders, relative strength
  and base counts.
- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and
  Selling Losers" (Journal of Finance, 1993) — the academic evidence that past
  winners keep winning for months.
