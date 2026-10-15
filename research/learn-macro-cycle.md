# Growth and the business cycle — where the economy is, and which stocks it favours

**In short**

- The economy moves through four phases: early recovery, mid-cycle, late cycle and recession. Profits follow it.
- Stocks turn first. In 2009 and 2020 the market bottomed before the recession ended and long before unemployment peaked.
- GDP and jobs data confirm a turn too late to trade on. Surveys of firms (PMIs) and market prices turn earlier.
- Ratios of prices show what the market expects: discretionary vs staples, copper vs gold, small caps vs large caps, and in India banks and mid caps vs the Nifty.
- The sector map for each phase is a tendency, not a timetable. Several famous signals have failed since 2022.

This guide covers how growth is measured (GDP, jobs, PMIs) and which indicators lead or lag. It describes the four phases of the business cycle and the sectors that have tended to lead in each. It shows why the stock market turns before the economy does. Finally, it shows how to read the cycle as it happens from ratios of prices, in the US and in India.

It pairs with [the yield curve guide](learn-macro-yield-curve.md) (the classic recession warning) and [the liquidity and credit guide](learn-macro-liquidity-credit.md).

---

## 1. The cycle in one paragraph

Credit expands, and firms hire and invest. Demand grows faster than the
economy can produce, so inflation and rates rise. Spending slows, and firms
cut back. A recession clears out the excesses, until falling rates start the
next expansion. Lengths vary wildly: US expansions have lasted from one year
to more than ten.

**The cycle matters to a trader because earnings follow it.** And the market
moves to the next phase months before the data confirms it. The skill is
noticing what the market already expects, not forecasting GDP.

## 2. Measuring growth

### 2.1 GDP — the scorecard, and the slowest

GDP is quarterly. It is published a month (US) or two (India) after the
quarter ends, and revised later. **By the time GDP confirms a recession, the
market has usually already fallen on it.** The NBER, which officially dates US
recessions, does so only months after they begin.

### 2.2 Jobs

- **Non-farm payrolls** (US, from the BLS, usually the first Friday): the
  monthly count of jobs added. It moves markets a lot, and is revised later.
- **Unemployment rate**: lags the cycle. It keeps rising after a recession
  ends, and peaks after stocks have bottomed.
- **The Sahm rule** (Claudia Sahm): a recession signal. It fires when the
  three-month average of the unemployment rate rises 0.5 percentage points
  above its low of the previous twelve months. The rule dates from 2019.
  Applied to history, it flagged every US recession since 1970 early on. Yet
  it triggered in mid-2024 without a recession following (none had been
  declared through 2025).
- **Initial jobless claims** (weekly new claims for unemployment benefit):
  the most up-to-date labour data.

India has no monthly payroll release. Traders use the Periodic Labour Force
Survey and, more usefully, stand-ins: auto sales, GST collections, credit
growth.

### 2.3 PMIs — the 50 line

Purchasing Managers' Indexes survey firms on orders, output, employment and
prices. **Above 50 means things grew compared with the month before; below 50
means they shrank.** PMIs come out quickly (in the first business days of the
month) and are rarely revised.

- US: the **ISM** manufacturing and services indexes; S&P Global's PMIs.
- India: the **HSBC India** manufacturing and services PMIs (S&P Global
  compiles them).

The new-orders part of the survey turns before the headline number. A PMI
falling from 58 to 52 still shows growth, but stocks react to the direction.

### 2.4 Leading versus lagging

| Leading (turn before the economy) | Coincident | Lagging (turn after) |
|---|---|---|
| Stock prices, the yield curve, credit spreads | Industrial production | Unemployment rate |
| PMI new orders, jobless claims | Payrolls, real income | Core inflation |
| Building permits, housing starts | GDP (in the quarter) | Corporate loan delinquencies |
| Copper, cyclical-vs-defensive ratios | Retail sales | Bank credit growth (India especially) |

Note the first row: **the stock market is itself one of the best leading
indicators** — which is why waiting for the economy to confirm is too slow.

## 3. The four phases, and who tends to lead

| Phase | Economy | Rates and inflation | Sectors that have tended to lead |
|---|---|---|---|
| **Early recovery** | Output turns up from recession; unemployment still high | Policy rates low, curve steep | Consumer discretionary, financials, industrials, small caps, materials |
| **Mid-cycle** | Steady growth, profits rising | Rates moving back to normal | Technology, industrials, communication — most stocks taking part |
| **Late cycle** | Factories near full capacity, inflation rising | Central bank tightening, curve flattening | Energy, materials, then defensives start to gain |
| **Recession** | Output and profits falling | Rates being cut, curve steepening from inversion | Staples, health care, utilities — the least bad — and cash |

This is the classic sector-rotation map (it appears in Fidelity's and others'
published business-cycle frameworks). **Treat it as a tendency, not a
timetable.** Phases are only clear in hindsight. A single dominant theme
(technology in the 2010s and 2020s) can override the map. And markets move to
the next phase's leaders before the phase arrives. Section 8 has the honest
caveats.

## 4. Markets lead the economy

The single most useful fact about the cycle for a trader: **stocks bottom
before earnings do, and long before jobs do.**

### 2008–09

```series
title: The S&P 500 through the 2008–09 recession
from: 2007-06-01
to: 2010-12-31
line: us:SP500_TR | S&P 500 total return | log
band: 2007-12-01 2009-06-30 | Recession (NBER)
mark: 2009-03-09 | Market low
caption: Stocks bottomed in March 2009, three months before the recession ended and seven before unemployment peaked.
```

The S&P 500 total return fell about 55% from its October 2007 high to the low
on **9 March 2009**. The NBER dates the recession's end to June 2009. The
unemployment rate did not peak (at about 10%) until October 2009. Anyone
waiting for jobs to improve bought far higher.

### 2020

```series
title: The S&P 500 through the 2020 recession
from: 2019-10-01
to: 2021-06-30
line: us:SP500_TR | S&P 500 total return | log
band: 2020-02-01 2020-04-30 | Recession (NBER)
mark: 2020-03-23 | Market low
caption: The fastest bear market on record ended on 23 March 2020, while the job losses were still to be reported.
```

The S&P 500 total return fell about 34% from 19 February to **23 March
2020**. The April jobs report showed unemployment at about 14.7% — after the
low. By mid-August 2020 the index was back above its February high, while
unemployment was still above 8%.

The same is true in India. The Nifty 50's 2020 low also came on 23 March. It
was down about 38% from its January high. Bank Nifty's 2009 low was on 9 March 2009.

## 5. Reading the cycle live — ratios of prices

Instead of forecasting GDP, watch what the market prefers. Divide the price of
a cyclical group (one whose profits swing with the economy) by the price of a
defensive one. That **ratio** rises when the market expects growth, and falls
when it expects a slowdown.

### 5.1 Discretionary versus staples

```series
title: Consumer discretionary vs staples, 2018–2024
from: 2018-01-01
to: 2024-12-31
line: us:SP500_TR | S&P 500 total return | log
line: us:XLY / us:XLP | Discretionary / staples (XLY/XLP) | pane2
mark: 2020-03-23 | 2020 low
caption: The ratio fell about 35% in 2022 as rates rose and the market priced a slowdown, then recovered most of it in 2023.
```

XLY/XLP is the purest US "consumer confidence" ratio: what people *want* to
buy versus what they *must* buy.

| Date | XLY/XLP |
|---|---|
| March 2020 low | about 0.90 |
| November 2021 peak | near 1.47 |
| End of 2022 | about 0.85 |
| End of 2023 | above 1.2 |

Amazon and Tesla make up much of XLY, so the ratio partly tracks two stocks.
Industrials versus utilities (XLI/XLU) is a broader cross-check. It hit its
low on 2 March 2009, a week before the market. Its 2020 low came on 18 March.

### 5.2 Copper versus gold

```series
title: Copper/gold and the 10-year yield, 2006–2026
from: 2006-01-01
line: us:COPPER / us:GOLD_FUT | Copper / gold
line: us:US10Y | US 10-year yield (%) | right
caption: For fifteen years the two moved together; since 2023 gold's surge has broken the link.
```

Copper is bought by factories and builders; gold is bought for safety. Their
ratio has been a well-known gauge of growth. It tracked the 10-year yield
closely. Both collapsed in 2008, and both rose from 2020 to 2021.

**But the two have since split apart.** Gold rose from about $1,800 at the
start of 2022 to over $4,000, outpacing copper. In February 2026 the ratio
hit its lowest level since 2000, while the 10-year was around 4%. Gold buying
by central banks, more than a recession, drove that. **A ratio that worked
for years can stop working**, so use it as one input among several.

### 5.3 Small caps and the cycle

```series
title: Small caps vs the S&P 500, 2000–2026
from: 2000-06-01
line: us:RUSSELL2000 / us:SP500_TR | Russell 2000 / S&P 500 (both total return)
mark: 2009-03-09 | 2009 low
mark: 2020-03-23 | 2020 low
caption: Small caps outran large caps out of both recession lows, then lost ground for most of the 2010s and 2020s.
```

Small companies borrow more at floating rates (rates that reset as market
rates move). They depend more on the home economy and have less pricing power.
So they are hit harder in slowdowns and bounce harder in early recoveries.
From the March 2020 low to mid-March 2021, the Russell 2000 (IWM) rose about
138%. The S&P 500 total return rose about 80%.

But the ratio peaked in April 2011 and roughly halved by its April 2025 low.
**"Small caps lead the recovery" is a phase, not a permanent edge.** Since
2011 the very largest companies (mega-caps) have dominated.

## 6. India's cycle

India's cycle is driven by different forces, and its data arrives more
slowly:

- **Credit growth.** Bank credit growth (published by the RBI every two
  weeks) is the backbone. When banks lend freely, consumer spending and
  business investment (capex) follow. At turning points it lags: banks lend
  most just before the cycle peaks. But its *trend* tells you the phase.
- **Capex.** Two parts. Private investment: order books of capital-goods
  companies, and how much of their capacity factories are using (the RBI's
  OBICUS survey). And government capex, set in the **Union Budget** each
  February.
- **Rural demand and the monsoon.** A good monsoon lifts farm incomes,
  tractor and two-wheeler sales, and rural sales of everyday consumer goods
  (FMCG). A bad one does the reverse, and also pushes up food inflation (see
  [the inflation guide](learn-macro-inflation.md)).
- **Government spending.** Central and state spending, especially before
  elections, can carry demand when private capex is weak.
- **Global links.** IT services earn in dollars and follow the US cycle;
  foreign flows follow the dollar and US yields
  ([the currencies guide](learn-macro-currencies.md)).

### Banks as the bellwether

Bank Nifty is India's cyclical bellwether — the index that signals where
the cycle is going. Banks *are* the credit cycle. Bank Nifty falls harder than
the broad index in a slowdown, and leads the recovery when lending picks up.

It fell about 69% from January 2008 to March 2009. From January to March 2020
it fell about 48%, against about 38% for the Nifty 50. The ratio of Bank Nifty to the Nifty 50 peaked in July 2019, before the
2020 shock, and fell about 29% to September 2020.

### Mid caps versus the Nifty

```series
title: Nifty Midcap 50 vs the Nifty 50, 2008–2026
from: 2008-01-01
line: india:NIFTY50 | Nifty 50 | log
line: india:MIDCAP / india:NIFTY50 | Midcap 50 / Nifty 50 | pane2
caption: Mid caps lost half their relative value from 2008 to 2013, and have about doubled against the Nifty since 2019.
```

India's mid caps magnify the home economy's cycle. Here is the ratio of the
Midcap 50 to the Nifty 50, both price indices:

| Date | Midcap 50 / Nifty 50 |
|---|---|
| January 2008 | about 0.62 |
| August 2013 | about 0.31 |
| January 2018 | a peak |
| April 2020 | a low |
| October 2026 | about 0.75, roughly double the 2020 low |

The years from 2008 to 2013 brought high inflation, rate hikes and stalled
capex. **A rising ratio says the home economy — credit, capex, money
from retail investors — is driving the market.** A falling one says investors
are moving to the large caps, which they see as safer.

## 7. What a trader does with it

1. **Let leadership tell you the phase.** A common tool is a rotation chart.
   It places each sector in one of four zones by its relative strength and
   the direction of that strength: Leading, Weakening, Lagging, Improving.
   Watch the groups that lead early in a recovery (homebuilders, banks,
   retailers, industrials). If they move from Improving into Leading after a
   decline, that is the sign of an early recovery. If utilities, staples and
   health care lead while the index stalls, that is the sign of a late cycle.
2. **Do not wait for the economy.** By the time payrolls and GDP confirm a
   recovery, the leading stocks have usually already made big gains.
3. **Check the ratios weekly.** If they are rising together, the market is
   willing to take risk: favour breakouts in cyclical stocks. If they are
   falling together: smaller positions, pickier selection, more cash.
4. **Fit the setups to the phase.** Breakouts tend to work best when many
   groups are rising. Late in the cycle fewer groups lead and more breakouts
   fail, so demand more from each setup. Breadth measures and a market-regime
   filter ask "is the market healthy?"; the cycle explains their answer
   ([regime filters](learn-strat-regime-filters.md)).
5. **India:** track credit growth, the monsoon, the Budget's capex number and
   Bank Nifty's relative strength. Lean towards mid-cap breakouts while the
   Midcap/Nifty ratio rises, and away from them when it falls.

## 8. What the evidence says

- **Robust:** stocks lead the economy. In the US, the market has bottomed
  before the end of most recessions, often months before. Unemployment peaks
  later still. The 2009 and 2020 lows are the textbook cases.
- **Robust:** cyclicals are more sensitive to the economy than defensives,
  and fall behind them in slowdowns.
- **Noisy:** the four-phase sector rotation map. Academic tests of
  business-cycle sector rotation find that the gains are small once you
  allow for not knowing the phase at the time. Most of the "edge" in
  textbook charts comes from dating the phases with hindsight.
- **Noisy:** single indicators. The ISM manufacturing PMI stayed below 50
  for most of 2023 and 2024. The Sahm rule triggered in 2024. The
  10-year/3-month curve was inverted from late 2022 to late 2024. Yet no
  recession followed within the usual delay. Each had worked for decades.
- **Lasting changes can override the cycle.** US mega-cap technology
  dominated through two cycles. Small caps lost ground for over a decade. The
  copper/gold ratio broke away from yields. Ratios are best read for their
  *change*, not their level.
- **India:** data arrives later and is revised more. Bank Nifty, the mid-cap
  ratio and sector relative strength are more up to date than GDP.

## 9. Checklist

- [ ] Latest ISM / India PMI: above or below 50, and which way is it moving?
- [ ] Jobless claims trend (US); any Sahm-rule talk?
- [ ] XLY/XLP and XLI/XLU: rising or falling over the past three months?
- [ ] Copper/gold and the 10-year: moving together, or diverging?
- [ ] Russell 2000 / S&P 500: are small caps leading or lagging?
- [ ] India: Bank Nifty vs Nifty; Midcap 50 vs Nifty 50
- [ ] Which groups moved into Leading or Improving this week? Cyclical or
      defensive?
- [ ] Breadth: is participation broad (mid-cycle) or narrowing (late)?
- [ ] Does the market's leadership agree with the economic story — and if
      not, trust the market's leadership.

## Further reading

- NBER, *US Business Cycle Expansions and Contractions* — the official
  recession dates (nber.org).
- FRED, Federal Reserve Bank of St. Louis — payrolls (PAYEMS), the
  unemployment rate (UNRATE), the Sahm rule indicator, GDP (fred.stlouisfed.org).
- Institute for Supply Management — the ISM Report On Business (ismworld.org).
- Claudia Sahm, "Direct Stimulus Payments to Individuals" (Hamilton Project,
  2019) — the paper that introduced the Sahm rule.
- Reserve Bank of India — sectoral deployment of bank credit, OBICUS survey,
  Monetary Policy Reports (rbi.org.in); MoSPI — GDP releases (mospi.gov.in).
- Martin Pring, *The All-Season Investor* — the business cycle and asset
  rotation.
- Sam Stovall, *Standard & Poor's Guide to Sector Investing* — the classic
  sector-rotation model.
- [The yield curve guide](learn-macro-yield-curve.md),
  [the liquidity and credit guide](learn-macro-liquidity-credit.md),
  [the inflation guide](learn-macro-inflation.md).
