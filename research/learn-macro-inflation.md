# Inflation — how rising prices reach rates, margins and sector leadership

Learning material: what inflation is and how the US and India measure it, why
it is the variable central banks react to, the three ways it reaches a stock
price (valuation, margins, sector leadership), and how the 1970s, 2021–22 and
the 2023 disinflation played out on the stored data. Read it beside
[the interest-rates guide](learn-macro-rates.md) — inflation is the *cause*,
rates are the *response* — and [the commodities guide](learn-macro-commodities.md)
for oil and metals in their own right.

**Where this shows in the app.** No CPI series is stored, but its footprints
are: the macro strip on **Markets → Breadth** shows the 10-year and 5-year
yields, WTI, gold and copper (US) and Brent, USD/INR and the US 10-year
(India), each with a one-line *why*. **Markets → Sectors** is where an
inflation regime shows up — energy and materials climbing the RS table.

---

## 1. What inflation is, in one paragraph

Inflation is the rate at which the general price level rises — the same
basket costing more each year. A little is normal — the Fed and the RBI both
target a positive rate. The trouble starts when inflation is **high, rising,
or unpredictable**: savers demand higher yields, the central bank raises its
policy rate, and the price investors pay for *future* profit falls. **For a
trader, inflation's direction and surprises matter more than its level** —
markets price the expected path and move on the gap between forecast and print.

## 2. How it is measured

### United States

| Measure | What it is | Why traders care |
|---|---|---|
| **CPI** (Consumer Price Index, BLS) | Monthly price of a consumer basket; shelter is the biggest piece | The headline number; released mid-month, moves markets on the day |
| **Core CPI** | CPI excluding food and energy | Strips the volatile parts; shows the *trend* the Fed worries about |
| **PPI** (Producer Price Index) | Prices received by producers | Pipeline pressure — input costs that may reach consumers later |
| **PCE price index** (BEA) | Broader consumer spending measure, different weights | **The Fed's 2% target is defined on PCE**, and it watches core PCE most |

CPI usually runs a few tenths above PCE (shelter weighs more in CPI). The
market trades CPI, which comes first each month; the Fed sets policy on PCE.

### India

| Measure | What it is | Why traders care |
|---|---|---|
| **CPI (combined)** (MoSPI) | Consumer prices, rural + urban | **The RBI's target: 4%, with a band of 2–6%**, under the inflation-targeting framework adopted in 2016 |
| **Core CPI** | CPI excluding food and fuel (not officially published; analysts compute it) | The underlying trend once vegetables and fuel are set aside |
| **WPI** (Wholesale Price Index) | Wholesale prices, heavy in manufactured goods and commodities | Input-cost pressure for manufacturers; it swings much more than CPI |

The big structural difference: **food is close to half of India's CPI
basket** (food and beverages, about 46% on the 2012 base; the rebasing of the
series to 2024 lowers that share, but food still weighs far more than in the US,
where it is roughly a seventh).
So India's headline is driven by the monsoon, vegetables and pulses — a single
crop (tomatoes, onions) can move it by tenths of a percent in a month. WPI can run far above or below CPI: in 2022 WPI was in the
mid-teens while CPI was around 7%, because commodity and fuel prices hit
wholesale prices first and hardest.

## 3. Why inflation drives rates

A central bank's main lever is its policy rate, and inflation is what it is
mandated to control (the RBI by law; the Fed under its dual mandate). The chain:

1. Inflation runs above target → the central bank raises its policy rate, or
   signals it will.
2. Bond investors demand a yield above expected inflation (a positive *real*
   yield), so **long yields rise** too — the US 10-year in the strip.
3. Every asset priced off future cash flows is now discounted at a higher
   rate; growth stocks most of all.

The transmission is detailed in [the interest-rates guide](learn-macro-rates.md).
The order is what matters: **inflation surprises move the expected path of
rates, and the expected path of rates moves stocks.**

## 4. How inflation hits stocks — three channels

### 4.1 Valuations: multiples compress

A P/E multiple falls when the return investors demand rises — and inflation
and higher yields raise it, even if earnings do not move. The effect is
largest for **long-duration stocks**, whose value sits in profits many years
away (high-multiple growth), for the same reason a 30-year bond falls more
than a 2-year one.

### 4.2 Margins: input costs versus pricing power

Inflation is a cost to some companies and revenue to others. **Commodity
producers** sell the thing whose price is rising. **Companies with pricing
power** (strong brands, few competitors) pass costs on, with a lag. Companies
**squeezed in the middle** — buying commodities, selling into a competitive
market (paints, tyres, FMCG in India; airlines, restaurants in the US) — see
gross margins fall before they can reprice.

### 4.3 Sector leadership: who wins and who loses

| Tends to hold up or lead | Tends to lag |
|---|---|
| Energy (XLE; India: upstream oil & gas) | Long-duration growth, software, unprofitable tech (XLK, the Nasdaq 100) |
| Materials, metals, miners (XLB) | Consumer discretionary (XLY) — real incomes squeezed |
| Commodity-linked industrials | Rate-sensitive real estate |
| Banks, *if* rates rise without recession | Commodity *users*: paints, tyres, aviation, oil marketers in India |

A **tendency, not a law**: materials held up only until April 2022, then
fell with everything else. The robust part is energy versus long-duration growth.

## 5. The worked example: 2021–22

US CPI inflation climbed through 2021 and peaked at about 9% in June 2022,
a four-decade high. The Fed began raising rates in March 2022, at its fastest
pace since the early 1980s.

```series
title: Energy vs technology, rebased, 2021–2022
from: 2021-01-01
to: 2022-12-31
rebase: 100
line: us:XLE | Energy (XLE)
line: us:XLK | Technology (XLK)
line: us:SPY | S&P 500 (SPY)
caption: Energy more than doubled over the two years while technology ended slightly below where it began — the inflation trade in one picture.
```

On the stored data: **XLE rose about 130%** from the start of 2021 to the end
of 2022 (about +53% in 2022 alone), while **XLK ended 2022 roughly 3% below
its January 2021 level** — it fell about a third from its December 2021 peak
to its October 2022 low. SPY lost about 19% in calendar 2022, with a
peak-to-trough fall of about a quarter. Consumer discretionary (XLY) fell
about 39% in 2022; staples (XLP) only about 3%.

```series
title: Oil and the 10-year yield, 2020–2023
from: 2020-01-01
to: 2023-12-31
line: us:WTI | WTI crude ($/bbl)
line: us:US10Y | US 10-year yield (%) | right
mark: 2022-03-08 | WTI peak
band: 2022-03-16 2023-07-26 | Fed raising rates
caption: Oil spiked first; the 10-year followed the inflation prints, from under 1% to about 5%.
```

WTI went from about $48 at the start of 2021 to a closing high near $124 on
8 March 2022, after Russia's invasion of Ukraine. The 10-year yield rose from
about 0.9% in January 2021 to about 3.9% at the end of 2022, and peaked near
5.0% in October 2023. **Note the order: oil peaked in March 2022, while yields
kept rising for another year and a half** — because what the Fed responds to
is core inflation (services, wages, shelter), which turns far slower than oil.

## 6. The 1970s — what a long inflation does

```series
title: The S&P 500 and the 10-year yield, 1965–1985
from: 1965-01-01
to: 1985-12-31
line: us:SP500_PRICE_LONG | S&P 500 (price) | log
line: us:US10Y | US 10-year yield (%) | right
mark: 1974-10-03 | 1974 low
caption: Fourteen years of going nowhere in nominal terms, while yields climbed to almost 16%.
```

From the late-1968 high (about 108) to August 1982 (about 102), **the S&P 500
price index went nowhere for almost fourteen years**, with a fall of nearly
half from January 1973 to the October 1974 low on the way. Dividends added a
few percent a year, but consumer prices nearly tripled over the same span —
so **in real terms stock holders lost a large part of their purchasing
power**. The 10-year yield rose from about 4% in 1965 to a peak near 15.8%
in September 1981, when the Fed under Paul Volcker held rates high enough to
break inflation. The great bull market began in August 1982, as inflation
and yields started a forty-year decline.

The lesson is not "the 1970s will repeat" but that **a high, unstable
inflation regime is hostile to valuations for years** — the index buyer's
usual tailwind is missing, and leadership rotates to commodities.

## 7. Disinflation and its rally (late 2022–2023)

When inflation is high but *falling*, the market prices the end of rate
rises, and the inflation phase's losers lead.

```series
title: The Nasdaq 100 and the 10-year as inflation came down, 2022–2023
from: 2022-08-01
to: 2023-12-31
line: us:NASDAQ100 | Nasdaq 100 (QQQ) | log
line: us:US10Y | US 10-year yield (%) | right
mark: 2022-11-10 | Soft October CPI
mark: 2023-10-19 | 10-year near 5%
caption: The soft CPI print of November 2022 started the turn; the late-2023 fall in yields powered the year-end rally.
```

From early October 2022 to the end of 2023, **the Nasdaq 100 (QQQ) rose about
50%** and the S&P 500 total return about 32%. XLK rose about 56% in 2023 alone,
while XLE was flat — a full reversal of 2022's leadership. Yields did not fall
straight away: the 10-year rose to almost 5% in October 2023 before dropping
to about 3.9% by year end, and that final drop fuelled a sharp
November–December rally.

**The bottom came while inflation was still far above target** — markets
trade "is it getting better?" long before the level is comfortable.

## 8. CPI day — the inflation surprise

US CPI is released at 8:30 a.m. New York time, before the open, and the
market reacts to the gap between the print and the consensus forecast —
especially core CPI.

```series
title: Two CPI days in autumn 2022 (S&P 500 ETF)
from: 2022-08-01
to: 2022-11-30
line: us:SPY | S&P 500 (SPY)
line: us:US10Y | US 10-year yield (%) | right
mark: 2022-09-13 | Hot August CPI
mark: 2022-11-10 | Soft October CPI
caption: A hot core print knocked about 4% off the index in a day; a soft one two months later added about 5½%.
```

- **13 September 2022:** August CPI came in hot, core re-accelerating.
  **SPY fell about 4.3%** (about 389 to 372), the Nasdaq 100 about 5.5%.
- **10 November 2022:** October CPI came in soft. **SPY rose about 5.5%**, the
  Nasdaq 100 about 7.4%, and the 10-year fell about 0.3 points in a day.

CPI day is a **scheduled volatility event**: a breakout bought the day before
is a coin flip on the print, and a tight stop can be gapped through at the
open ([the macro calendar guide](learn-macro-calendar.md)). India's CPI comes
around the 12th, after the close, so the reaction is in the next open — mostly
in rate-sensitive banks, NBFCs and real estate.

## 9. India: food, monsoon, fuel and Brent

- **Food and the monsoon.** A weak or uneven monsoon cuts kharif output and
  lifts food prices months later. The IMD's forecasts and the progress of the
  rains (June–September) are inflation news.
- **Vegetable spikes.** Tomato and onion prices can multiply within weeks on
  a crop failure, as tomatoes did in mid-2023; the government answers with
  export bans, stock limits and subsidised sales.
- **Fuel taxes.** Pump prices are set largely by excise and state VAT. Excise
  was cut in late 2021 and May 2022, and the oil marketers held pump prices
  for long stretches — so dear crude often lands in **their margins** rather
  than in CPI.
- **Brent and the rupee.** Dearer Brent widens the trade deficit and weakens
  the rupee, which makes every import dearer — a loop
  ([the currencies guide](learn-macro-currencies.md)).

```series
title: Nifty 50 and Brent crude, 2021–2023
from: 2021-01-01
to: 2023-12-31
line: india:NIFTY50 | Nifty 50
line: india:BRENT | Brent ($/bbl) | right
mark: 2022-06-17 | Nifty 2022 low
caption: While Brent spiked to about $128, the Nifty fell about 16% from its January high; it recovered as crude eased.
```

On the stored data, Brent went from about $51 at the start of 2021 to a
closing high of about $128 on 8 March 2022. The Nifty 50 fell about 16.5%
from its January 2022 high to its June 2022 low, and USD/INR moved from about
74.5 to above 82 over 2022 (the rupee lost about 11% against the dollar).
India's CPI ran above the RBI's 6% upper band for much of 2022, and the RBI
raised its repo rate from May 2022, after the Fed had begun.

Brent-sensitive in India: oil marketers (hurt when pump prices are held),
paints, tyres and aviation (crude-based costs); upstream producers gain.

## 10. What a trader does with it

1. **Know the regime.** Rising core inflation with rising yields punishes
   high-multiple growth; falling core rewards it.
2. **Mark CPI days.** Avoid new breakouts the day before a US CPI release;
   size down or tighten stops in rate-sensitive growth stocks (for India
   CPI, in financials).
3. **Read leadership on the Sectors page.** In an inflation regime energy
   and materials groups climb the RS table; let the screens find that
   leadership rather than fighting it with "cheap" tech.
4. **Watch the strip.** A sharp jump in oil or the 10-year on Markets →
   Breadth on a day of weak breadth is a reason to slow down. Inflation
   regimes are volatile: smaller and fewer positions.
5. **India:** a weak monsoon plus rising Brent and a falling rupee is the mix
   that pushes the RBI towards hikes and pulls foreign money out.

## 11. What the evidence says

- **Robust:** high and rising inflation has come with lower valuations (the
  P/E falls) — the 1970s and 2022 alike; the mechanism is mechanical.
- **Robust:** commodity producers outperform when inflation is
  commodity-driven; in 2022 the energy-versus-technology gap was enormous.
- **Weaker:** "stocks are an inflation hedge". Over decades earnings keep up
  with nominal growth, but over years-long inflationary stretches stocks have
  lost in real terms (the 1970s).
- **Weaker:** the sector map. Materials fell hard in late 2022; staples and
  utilities held up for defensive reasons, not inflation ones.
- **Lags:** headline inflation peaks when commodities peak; core inflation
  and policy rates lag by months; stocks usually bottom before inflation
  falls far (October 2022 in the US). Waiting for "inflation to be beaten" is
  usually waiting too long.
- **India:** the food-heavy CPI is noisy; the RBI looks through one-off
  vegetable spikes more than persistent core inflation.

## 12. Checklist

- [ ] Last US CPI and core CPI: rising or falling on a 3- and 6-month basis?
- [ ] Next US CPI date — which open positions are exposed to it?
- [ ] What did India's last CPI show, and is it inside the RBI's 2–6% band?
- [ ] WTI and Brent on the macro strip: trending, spiking or calm?
- [ ] US 10-year: rising or falling over the past month?
- [ ] Sectors page: are energy and materials groups rising in RS, and is
      technology falling? Which quadrant are they in?
- [ ] India: monsoon progress, vegetable prices, USD/INR trend

## Further reading

- U.S. Bureau of Labor Statistics — the CPI and PPI releases and schedule
  (bls.gov); Bureau of Economic Analysis — the PCE price index (bea.gov).
- Federal Reserve — the Statement on Longer-Run Goals and Monetary Policy
  Strategy (the 2% PCE target) and FOMC statements (federalreserve.gov).
- FRED, Federal Reserve Bank of St. Louis — CPIAUCSL, CPILFESL, PCEPI and
  the long history of US inflation (fred.stlouisfed.org).
- Reserve Bank of India — the Monetary Policy Statements and the Monetary
  Policy Report (rbi.org.in); MoSPI — the CPI release (mospi.gov.in).
- [The interest-rates guide](learn-macro-rates.md),
  [the commodities guide](learn-macro-commodities.md),
  [the macro calendar guide](learn-macro-calendar.md).
