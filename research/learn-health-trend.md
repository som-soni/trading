# Reading the market's trend — is the index in an uptrend?

Learning material: why the direction of the index matters more to a stock
trader than almost anything else, how to read it from the 50- and 200-day
averages, their slope, Weinstein's stages and drawdown depth, how the US and
India differ, and exactly what this app's own market regime does. Companion
to [the breadth guide](learn-health-breadth.md) (how many stocks take part),
[the volatility guide](learn-health-volatility.md) and
[the distribution-day guide](learn-health-distribution.md) (index volume).

**Where this shows in the app.** Every screening run computes a market regime
(`scripts/swing_screener/core/regime.py`) from the broad indices in each
market's config — SPY, QQQ and IWM for the US; the Nifty 50 (`^NSEI`), Nifty 500
(`^CRSLDX`) and a Midcap 150 entry for India — and prints it at the top of the
run's report: VIX, `high_vol`, the share of stocks above their 20- and 50-day
averages, and **downgrade active** when it fires. The Strategies page shows the
rule as each strategy's regime note. Markets → Breadth opens with the card
**"S&P 500 against its 50 DMA?"** (Nifty 50 for India) and charts the index.

---

## 1. Why the index comes first

Most stocks follow the market: funds being redeemed sell what they own, good
companies included. O'Neil's rule of thumb is that **about three in four stocks
move with the general market** — a heuristic, not a measured constant. And
**breakouts fail far more often in downtrends** — a well-known practitioner
observation, not a statistic measured here: a breakout needs buyers after the
pivot, and in a falling market every rally meets sellers wanting out at
breakeven. What the stored S&P 500 history does show is **far wilder days**:

| S&P 500, 1950–2026 (daily) | Prior close above its 200-day | Prior close below it |
|---|---|---|
| Share of days | about 72% | about 28% |
| Next-day return, annualised | about 11% | about 5% |
| Volatility, annualised | about 12% | about 22% |
| Days moving more than 2% | about 2 in 100 | about 10 in 100 |

Since 2000, below the line, volatility was about 30% and one day in five moved
more than 2% — yet the average return was *higher*, because the biggest up days
cluster in bear markets (24 March 2020, for one). **Below the 200-day you are
not sure to lose; you are sure of a rougher ride** — exactly what breaks a
stop-based swing trade.

## 2. The index against its 50- and 200-day averages

The simplest read is where the index closes against its averages:

| Reading | What it says |
|---|---|
| Above a rising 50-day and a rising 200-day | Uptrend — buy breakouts, full size |
| Below the 50-day, above the 200-day | Pullback inside an uptrend — be selective, smaller |
| Below a flattening 200-day | Trend in doubt — mostly watch |
| Below a falling 200-day, 50-day under the 200-day | Downtrend — preserve capital |

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
caption: Three breaks of the 200-day. The lower pane shows how far: about 15% below it in December 2018, 26% in March 2020, 17% in June 2022.
```

- **2018.** First close below on 11 October, then back and forth until early
  December; the low on 24 December was −19.8% from the high.
- **2020.** The break came on 27 February, already 12% off the high — a late
  signal in a fast crash. Low on 23 March (−34%); back above on 27 May.
- **2022.** First close below on 21 January (8% off the 3 January record);
  below without a break from 8 April to 30 November, and above the line on
  only about 15% of 2022's sessions.

### 2.1 Whipsaws — the price of a simple rule

A line that the index crosses often is a line that will often be wrong. On the
stored daily closes the S&P 500 crossed its 200-day **20 times in 2015–16** and
**not once in 2017** (nor in 2021 or 2024). In a sideways year the rule
flips every few weeks, each flip a small loss.

```series
title: Whipsaw versus trend — the S&P 500 and its averages, 2015–2017
from: 2015-01-01
to: 2017-12-31
tf: D
line: us:SPX | S&P 500
line: us:SPX@sma50 | 50-day
line: us:SPX@sma200 | 200-day
caption: In 2015–16 the index crossed its 200-day 20 times and the 50-day crossed the 200-day four times; in 2017 it never touched the 200-day.
```

What protection does it buy? A crude test on the stored S&P 500 *price* index
(no dividends, cash interest or costs; invested while the previous close was
above the 200-day):

| 1950–2026 | Buy and hold | 200-day rule |
|---|---|---|
| Annual growth (price only) | about 8.4% | about 7.6% |
| Worst drawdown | about −57% | about −28% |
| Switches | — | 452 (about six a year) |

From 2000: about 4.9% a year against 6.5%, worst drawdown −25% against −57%.
**The 200-day is a risk filter, not a return engine**: it halved the worst loss
and cost some return in whipsaws.

### 2.2 Slope matters as much as position

A price above a *falling* average is a bounce, not an uptrend.

- **The 200-day's slope** (against 20 sessions earlier) turned down on 5 May
  2022, the index already about 14% off its high, and up on 5 April 2023.
- **The 50/200 cross** ("golden" / "death" cross). The 50-day fell below the
  200-day on 7 December 2018 (index 10% off its high), on 30 March 2020 —
  *a week after the low*, 22% off — and on 14 March 2022 (13% off). It crossed
  back up on 1 April 2019, 9 July 2020 and 2 February 2023 (still 13% below
  the high). **Crosses confirm; they do not anticipate.**

## 3. Weinstein's stages applied to the index

Stan Weinstein's four stages, read off the 30-week moving average, were written
for stocks ([learn-bases.md](learn-bases.md)) but read an index just as well:

| Stage | Index above its 30-week line? | 30-week line | Trader's posture |
|---|---|---|---|
| 1 Basing | Crossing back and forth | Flat after a decline | Build the watchlist |
| 2 Advancing | Above | Rising | Full exposure |
| 3 Topping | Crossing back and forth | Flattening after an advance | Tighten, take profits, fewer new buys |
| 4 Declining | Below | Falling | Cash or very small |

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

Against a 30-week simple average of weekly closes, the S&P 500 closed below
its line in **none of 2021's 53 weeks**, **41 of 2022's 52** and 4 in 2023.
The app's regime uses a 30-week *exponential* average (§7).

## 4. Higher highs and higher lows

Before any average, a trend is a sequence of swings: **higher highs and higher
lows, or lower highs and lower lows.** A rally that stalls below the previous
high after a sharp fall is the first sign of Stage 4 — in 2022 the summer rally
stopped at a lower high on 16 August and broke the June low in October. A higher
low followed by a close above the last swing high is the first sign of a new
uptrend, often weeks before the 200-day turns. Swings for the early read,
averages for confirmation.

## 5. Drawdown depth as a regime read

Distance below the high is a blunt, honest regime read. By convention **a
correction is a 10–20% fall; a bear market 20% or more** — round numbers, not laws.

```series
title: The S&P 500's distance below its record, 1928–2026
from: 1928-01-01
tf: M
line: us:SP500_PRICE_LONG@dd | % below the running record | zero
band: 1929-09-17 1954-09-22 | 25 years to regain the 1929 high
band: 2000-03-27 2013-03-28 | 2000 high regained in 2013
caption: −86% in 1932, −48% in 1974, −49% in 2002, −57% in 2009, −34% in 2020, −25% in 2022. Most of the time the index is within a few percent of a record.
```

Counting declines between record closes (a fall inside a longer decline, such
as 2011's, is not counted separately):

| Since | Corrections (10–20%) | Bear markets (20%+) |
|---|---|---|
| 1928 | 14 | 12 |
| 1950 | 13 | 11 |
| 1980 | 10 | 6 |

That is **a 10%+ decline roughly every three years since 1950**, and about one
in two of them went on to 20%. Four stopped just short of the line on closes —
1990 (−19.9%), 1998 (−19.3%), 2018 (−19.8%) and 2025 (−18.9%) — which is why
"is it officially a bear market?" is the wrong question. Since 1980 the index
has been within 5% of a record on about half of all trading days, at least 10%
below one on about a third, and 20% or more below on about a sixth.

**The deeper the drawdown, the more of your watchlist is broken**: in a 10%
correction leaders often hold up; in a 20%+ decline they break too, and the
next uptrend is usually led by *new* names.

## 6. India: the Nifty is not the market

Since 2010 the Nifty 50 closed above its 200-day about 73% of the time (Nifty
Midcap 50 about 69%, S&P 500 about 83%), crossing it about eight times a year
against the S&P 500's six. And the large-cap index can hide the typical stock.

```series
title: 2018 — the Nifty at a record while midcaps were in a bear market
from: 2017-10-01
to: 2020-01-31
line: india:NIFTY50@dd | Nifty 50, % below high | zero
line: india:MIDCAP@dd | Nifty Midcap 50, % below high
mark: 2018-08-28 | Nifty record
caption: The Nifty 50 set a record on 28 August 2018; the Midcap 50 fell 23% from January to October 2018 and 28% by August 2019.
```

The Midcap 50 peaked on 8 January 2018; while it fell, the Nifty 50 closed at
a record on 28 August (its worst fall that year was about 15%). The Midcap 50 /
Nifty 50 ratio lost about 30% by October 2019. The IL&FS shock is in [the
liquidity guide](learn-macro-liquidity-credit.md), the midcap cycle in [the
cycle guide](learn-macro-cycle.md). **A breakout trader lives in mid and small
caps: read the Nifty 500 and a midcap index** — when the Nifty makes highs while
midcaps sit under falling 200-day lines, your market is in a downtrend.

## 7. The app's own regime, exactly as coded

`core/regime.py` computes, per broad index, `IndexRegime`: close above the
50-day, above the 200-day, **50-day rising** (above its value 10 sessions ago),
and **weekly close above a rising 30-week EMA**. Across the whole loaded
universe it computes the share of stocks above their 20- and 50-day averages.
It reads the volatility index — VIX for the US, India VIX for India — and sets
`high_vol` when it is above the market's `vol_threshold` (**25** US, **20**
India, in `config/us.py` and `config/india.py`).

Only two of those readings change a decision:

1. **Sizing.** `core/sizing.py` risks `risk_pct` (1% of the account) per trade,
   or `risk_pct_high_vol` (0.5%) when `high_vol` is set. Position size is
   still capped at `max_position_pct` (25%) of the account.
2. **The downgrade.** The screening pipeline takes the *first two* broad
   indices — SPY and QQQ, or the Nifty 50 and Nifty 500 — and sets
   `downgrade_active` when **every one of them closes below its 50-day
   average**. Strategies then demote their decision:

| Strategy | What the downgrade does |
|---|---|
| Trend pullback, Volume breakout, Donchian channel, Chart patterns | Every label down one tier (HIGH CONFIDENCE → ON TRIGGER → WATCH → AVOID) |
| Minervini SEPA | TRADE tiers become WATCH ("market filter: no new buys"); the watchlist is kept |

The Strategies page's regime note describes the first group; Minervini keeps
the watchlist on purpose — a weak tape is when you want to know what is setting
up. The other readings (200-day, slope, 30-week EMA, breadth) are **reported,
not acted on**.

Two caveats. If a downgrade index has no data the rule cannot fire (`all()`
needs both present and below). And it is fast: since 2010 SPY and QQQ were both
below their 50-day on about 23% of sessions, in seven or eight spells a year,
median length three sessions — **the downgrade flickers**; read it as "be
pickier today", not as a regime change.

**In backtests** the downgrade is not applied (`backtesting/backtest.py` says
so). The Minervini spec backtest has an optional `--market-filter` (MKT-01 in
`backtesting/spec.py`): no new entries while the benchmark is below its 200-day
or its 50-day is below its 200-day; open positions are untouched, and
`--mkt-confirm` waits a few sessions before risk-on resumes. The momentum
baseline's trend filter is on each stock's own 200-day, not the market's.

## 8. What a trader does with it

### 8.1 An exposure ladder

Decide in advance how much you will have at risk in each state:

| State | Typical evidence | Exposure |
|---|---|---|
| **Full** | Index above rising 50- and 200-day, Stage 2, within ~10% of high | Normal size, normal number of positions |
| **Reduced** | Below the 50-day, or a 10% correction, 200-day still rising | Half size or half the positions; only the strongest setups |
| **Cash / minimal** | Below a falling 200-day, Stage 4, 20%+ drawdown | No new breakouts; manage exits; keep the watchlist |

Move one rung at a time, and step back up as evidence repairs — the first
leaders out of sound bases after a low are often the cycle's best trades.

### 8.2 Combine trend, breadth and volatility

- **Trend** (this guide): the index against its averages; the drawdown.
- **Breadth** ([the breadth guide](learn-health-breadth.md)): an index at highs
  with fewer new highs and fewer stocks above their 50-day is a fragile trend.
- **Volatility** ([the volatility guide](learn-health-volatility.md)): a VIX or
  India VIX holding above the threshold is when the app halves risk.
- **Selling** ([the distribution-day guide](learn-health-distribution.md)):
  heavy-volume down days clustering near a high.

Two or three warnings together justify a rung down; one alone usually does not.

## 9. What the evidence says

- **Robust:** index trend filters have cut the worst drawdowns roughly in half
  by sitting out long bear markets (Faber 2007; §2.1 agrees), and volatility
  below the 200-day is about double. **Weaker:** the return case — after
  whipsaws a simple rule has usually lagged buy-and-hold.
- **Lags are built in:** in 2020 the death cross came after the low; in
  V-shaped markets the trend reads are wrong twice.
- **Folklore:** that the golden/death cross predicts on its own, or that
  "−20%" marks a change in kind.
- **"Breakouts fail in downtrends"** fits the mechanism but is not measured
  here; the backtests do not apply the live downgrade.

## 10. Checklist

- [ ] S&P 500 / Nifty 50 against rising 50- and 200-day lines? India: Nifty 500 and midcaps agree?
- [ ] 30-week line: which stage — and has it changed since last week?
- [ ] Swings: last high and last low higher or lower than the previous ones?
- [ ] Drawdown from the high: under 10%, a correction, or a bear market?
- [ ] Did the screener report say **downgrade active**? Is VIX above the threshold?
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
