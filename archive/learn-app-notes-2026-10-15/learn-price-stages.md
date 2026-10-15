# App notes moved out of learn-price-stages (verbatim)

## From the intro: "Where this shows in the app"
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

## From §2.2 Which way is the average sloping? (the app's rule table)
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


## From §2.3 Are the swings rising or falling? (U5)
Swings turn before averages do, because an average needs months of prices to
change direction. So read swings for the early warning and the average for
confirmation. The Established uptrend screen checks this directly (U5): the
last two confirmed swing lows of the past ~50 sessions must be rising. A swing
low counts as confirmed when its low is the lowest of the seven bars centred on
it (three on each side).

## From §6 Minervini's Trend Template, exactly as the app checks it
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


## From §6.1 How often stocks pass (data source line)
Counted on the app's stored month-end snapshots (August 2021 to September
2026, 62 month-ends), among tradable stocks:


## From §8 (method framing)
To put a number on it, the app's stored daily prices were scanned for **fresh
Trend Template passes**: the first day a stock passed all eight rules after six
months (126 sessions) without passing. The RS rule used the single-stock
stand-in (12-1 month return of 10%+). The stock had to clear today's tradable
floor that day. Qualification dates run from 2005 to the end of 2024. Each
case was followed until the stock **stopped being above a rising 200-day**:
the first close below the 200-day, or the first day the 200-day was no higher
than 21 sessions earlier. This was run for this guide on stored data; it is
not a backtest, and it has no costs.

## From §9 What the app's own evidence says (9.1 screen study framing and 9.2 backtests — backtests removed from the guide)
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


## From §10 and §11 (app references)
1. **Check the market's stage first** ([learn-health-trend.md](learn-health-trend.md)).
   Most stocks move with the market. Traders hold that breakouts fail more
   often while the index falls; that guide explains why, and that the app has
   not measured it.
2. **Fish in the Stage 2 list.** Start from the Stage 2 screen. When it is
   short, look at the names that stay on it: they are the leaders.
3. **Prefer early Stage 2.** The 30-week line just turned up, a first or
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

## From §12 Checklist
- [ ] Stage 2 pass rate on the screen this week: rising or falling?
