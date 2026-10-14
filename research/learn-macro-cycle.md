# Growth and the business cycle — where the economy is, and which stocks it favours

Learning material: how growth is measured (GDP, jobs, PMIs), which indicators
lead and which lag, the four phases of the business cycle and the sectors
that have tended to lead in each, why the stock market turns before the
economy does, and how to read the cycle live from ratios of stored prices —
in the US and in India. Pairs with [the yield curve guide](learn-macro-yield-curve.md)
(the classic recession warning) and [the liquidity and credit guide](learn-macro-liquidity-credit.md).

**Where this shows in the app.** No GDP, jobs or PMI series are stored, so the
app reads the cycle through prices. **Markets → Sectors** ranks sectors,
industry groups and sub-industries by RS on a rotation chart (Leading,
Weakening, Lagging, Improving); **Markets → Post-market** lists the day's
rotation changes. **Markets → Breadth** carries the macro strip (copper, the
10-year, HY credit) and the breadth measures.

---

## 1. The cycle in one paragraph

Credit expands, firms hire and invest, demand outruns capacity, inflation
and rates rise, spending slows, firms cut, and a recession clears the
excesses until falling rates start the next expansion. Lengths vary wildly —
US expansions have lasted from one year to more than ten. **The cycle
matters to a trader because earnings follow it, and the market prices the
next phase months before the data confirms it** — the skill is noticing what
the market is already pricing, not forecasting GDP.

## 2. Measuring growth

### 2.1 GDP — the scorecard, and the slowest

GDP is quarterly, published a month (US) or two (India) after the quarter,
and revised. **By the time GDP confirms a recession, the market has usually
priced it**; the NBER dates US recessions only months after they begin.

### 2.2 Jobs

- **Non-farm payrolls** (US, BLS, usually the first Friday): a big mover, revised.
- **Unemployment rate**: lags the cycle — it keeps rising after a recession
  ends, and peaks after stocks have bottomed.
- **The Sahm rule** (Claudia Sahm): a recession signal when the three-month
  average of the unemployment rate rises 0.5 percentage points above its low
  of the previous twelve months. Applied to history, it flagged every US recession since 1970
  early on (the rule dates from 2019), yet triggered in mid-2024 without a recession following (none had been declared through 2025).
- **Initial jobless claims** (weekly): the timeliest labour data.

India has no monthly payroll release; traders use the Periodic Labour Force
Survey and, more usefully, proxies — auto sales, GST collections, credit growth.

### 2.3 PMIs — the 50 line

Purchasing Managers' Indexes survey firms on orders, output, employment and
prices. **Above 50 means expansion, below 50 contraction**, versus the prior
month. They are timely (first business days of the month) and rarely revised.

- US: the **ISM** manufacturing and services indexes; S&P Global's PMIs.
- India: the **HSBC India** manufacturing and services PMIs (S&P Global
  compiles them).

The new-orders component leads the headline. A PMI falling from 58 to 52 is
still expansion, but the direction is what stocks trade.

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
| **Mid-cycle** | Steady growth, profits rising | Rates normalising | Technology, industrials, communication — broad participation |
| **Late cycle** | Capacity tight, inflation rising | Central bank tightening, curve flattening | Energy, materials, then defensives start to gain |
| **Recession** | Output and profits falling | Rates being cut, curve steepening from inversion | Staples, health care, utilities — the least-bad, and cash |

This is the classic sector-rotation map (it appears in Fidelity's and others'
published business-cycle frameworks). **Treat it as a tendency, not a
timetable.** Phases are only clear in hindsight; a single dominant theme
(technology in the 2010s and 2020s) can override it; and markets move to the
next phase's leaders before the phase arrives. Section 8 has the honest
caveats.

## 4. Markets lead the economy

The single most useful fact about the cycle for a trader: **stocks bottom
before earnings, and long before jobs.**

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
on **9 March 2009**. The NBER dates the recession's end to June 2009; the
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

The same is true in India: the Nifty 50's 2020 low was also on 23 March
(down about 38% from its January high), and Bank Nifty's 2009 low was on
9 March 2009.

## 5. Reading the cycle live — ratios of stored prices

Instead of forecasting GDP, watch what the market prefers. A **ratio** of a
cyclical group to a defensive one rises when the market expects growth, and
falls when it expects slowdown.

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
buy versus what they *must* buy. On the stored data it rose from about 0.90
at the March 2020 low to a peak near 1.47 in November 2021, fell to about
0.85 at the end of 2022, and was back above 1.2 by the end of 2023. A caveat:
XLY is dominated by Amazon and Tesla, so the ratio partly tracks two stocks.
`us:XLI / us:XLU` (industrials versus utilities) is a broader cross-check: it
hit its low on 2 March 2009, a week before the market, and its 2020 low on 18
March.

### 5.2 Copper versus gold

```series
title: Copper/gold and the 10-year yield, 2006–2026
from: 2006-01-01
line: us:COPPER / us:GOLD_FUT | Copper / gold
line: us:US10Y | US 10-year yield (%) | right
caption: For fifteen years the two moved together; since 2023 gold's surge has broken the link.
```

Copper is bought by factories and builders; gold is bought for safety. Their
ratio has been a well-known growth gauge that tracked the 10-year yield
closely — both collapsed in 2008, both rose from 2020 to 2021. **But it has
since diverged**: gold rose from about $1,800 at the start of 2022 to over
$4,000, outpacing copper, so the ratio made its lowest level in the stored
history (since 2000) in February 2026 while the 10-year was around 4%. Central
bank gold buying, more than a recession, drove that. **A ratio that worked for
years can stop working** — use it as one input among several.

### 5.3 Small caps and the cycle

```series
title: Small caps vs the S&P 500, 2000–2026
from: 2000-06-01
line: us:RUSSELL2000 / us:SP500_TR | Russell 2000 / S&P 500 (both total return)
mark: 2009-03-09 | 2009 low
mark: 2020-03-23 | 2020 low
caption: Small caps outran large caps out of both recession lows, then lost ground for most of the 2010s and 2020s.
```

Small companies borrow more at floating rates, depend more on the domestic
economy and have less pricing power, so they are hit harder in slowdowns and
recover harder in early recoveries. From the March 2020 low to mid-March 2021,
the Russell 2000 (IWM) rose about 138% against about 80% for the S&P 500 total
return. But the ratio peaked in April 2011 and roughly halved by its April 2025
low: **"small caps lead the recovery" is a phase, not a permanent edge**, and
since 2011 the mega-caps have dominated.

## 6. India's cycle

India's cycle is driven by different engines, and its data is slower:

- **Credit growth.** Bank credit growth (RBI, fortnightly) is the backbone:
  when banks lend freely, consumption and capex follow. It lags at turns —
  banks lend most just before the cycle peaks — but its *trend* defines the
  phase.
- **Capex.** The private investment cycle (order books of capital-goods
  companies, capacity utilisation in the RBI's OBICUS survey) and government
  capex, set in the **Union Budget** each February.
- **Rural demand and the monsoon.** A good monsoon lifts farm incomes,
  tractor and two-wheeler sales, and rural FMCG volumes. A bad one does the
  reverse, and also feeds food inflation (see
  [the inflation guide](learn-macro-inflation.md)).
- **Government spending.** Central and state spending, especially before
  elections, can carry demand when private capex is weak.
- **Global links.** IT services earn in dollars and follow the US cycle;
  foreign flows follow the dollar and US yields
  ([the currencies guide](learn-macro-currencies.md)).

### Banks as the bellwether

Bank Nifty (`^NSEBANK`) is India's cyclical bellwether: banks are the credit
cycle. It falls harder than the index in a slowdown and leads the recovery
when credit picks up. On the stored data it fell about 69% from January 2008
to March 2009, and about 48% from January to March 2020, against about 38%
for the Nifty 50. The `india:^NSEBANK / india:NIFTY50` ratio peaked in July 2019, before the
2020 shock, and fell about 29% to September 2020.

### Mid caps versus the Nifty

```series
title: Nifty Midcap 50 vs the Nifty 50, 2008–2026
from: 2008-01-01
line: india:NIFTY50 | Nifty 50 | log
line: india:MIDCAP / india:NIFTY50 | Midcap 50 / Nifty 50 | pane2
caption: Mid caps lost half their relative value from 2008 to 2013, and have about doubled against the Nifty since 2019.
```

India's mid caps are the domestic-cycle amplifier. On the stored data (both
price indices) the Midcap 50 / Nifty 50 ratio fell from about 0.62 in January
2008 to about 0.31 in August 2013 — the years of high inflation, rate hikes
and stalled capex — rose into a January 2018 peak, fell again to an April 2020
low, and has since roughly doubled, to about 0.75. **A rising ratio says the
domestic cycle — credit, capex, retail inflows — is doing the work**; a
falling one says money is hiding in the large caps.

## 7. What a trader does with it

1. **Let leadership tell you the phase.** On Markets → Sectors, early
   cyclicals (homebuilders, banks, retailers, industrials) moving from
   Improving into Leading after a decline is the early-recovery footprint;
   utilities, staples and health care leading while the index stalls is the
   late-cycle one.
2. **Do not wait for the economy.** By the time payrolls and GDP confirm a
   recovery, the leaders have usually run.
3. **Check the ratios weekly.** Rising together: risk on, favour cyclical
   breakouts. Falling together: smaller positions, tighter selection, more cash.
4. **Fit the setups to the phase.** Breakouts tend to work best when many
   groups are rising; late in the cycle leadership narrows and more fail —
   demand more from each setup. The Breadth page and the strategies' market
   regime already encode "is the tape healthy"; the cycle explains them.
5. **India:** track credit growth, the monsoon, the Budget's capex number and
   Bank Nifty's relative strength; lean towards mid-cap breakouts while the
   Midcap/Nifty ratio rises, and away from them when it falls.

## 8. What the evidence says

- **Robust:** stocks lead the economy. In the US, the market has bottomed
  before the end of most recessions, often months before, and unemployment
  peaks later still. The 2009 and 2020 lows are the textbook cases.
- **Robust:** cyclicals are more sensitive to the economy than defensives,
  and lose relative ground in slowdowns.
- **Noisy:** the four-phase sector rotation map. Academic tests of
  business-cycle sector rotation find that the gains are small once you
  account for not knowing the phase in real time; most of the "edge" in
  textbook charts comes from dating the phases with hindsight.
- **Noisy:** single indicators. The ISM manufacturing PMI stayed below 50
  for most of 2023 and 2024, the Sahm rule triggered in 2024, and the
  10-year/3-month curve was inverted from late 2022 to late 2024 — with no
  recession following within the usual lag. Each had worked for decades.
- **Structural shifts override the cycle.** US mega-cap technology dominated
  through two cycles; small caps lost ground for over a decade; the
  copper/gold ratio broke away from yields. Ratios are best read for their
  *change*, not their level.
- **India:** data arrives later with larger revisions; Bank Nifty, the
  mid-cap ratio and the Sectors page are more timely than GDP.

## 9. Checklist

- [ ] Latest ISM / India PMI: above or below 50, and which way is it moving?
- [ ] Jobless claims trend (US); any Sahm-rule talk?
- [ ] XLY/XLP and XLI/XLU: rising or falling over the past three months?
- [ ] Copper/gold and the 10-year: moving together, or diverging?
- [ ] Russell 2000 / S&P 500: are small caps leading or lagging?
- [ ] India: Bank Nifty vs Nifty; Midcap 50 vs Nifty 50
- [ ] Sectors page: which groups moved into Leading or Improving this week
      (Post-market's rotation changes)? Cyclical or defensive?
- [ ] Breadth page: is participation broad (mid-cycle) or narrowing (late)?
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
