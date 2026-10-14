# Currencies and capital flows — the dollar, the rupee and who gets paid

Learning material: what moves a currency, the US Dollar Index and why a
strong dollar squeezes US multinationals and emerging markets, the rupee's long
drift and what speeds it up, how foreign and domestic money push Indian stocks
around, and what a swing trader does with it. Companion to [the interest-rates guide](learn-macro-rates.md) (rate
differentials drive currencies), [the commodities guide](learn-macro-commodities.md)
(oil and the rupee are joined at the hip) and
[the liquidity and credit guide](learn-macro-liquidity-credit.md).

**Where this shows in the app.** Markets → Breadth carries a macro strip
(`scripts/swing_screener/marketdata/macro.py`, `STRIP`). The US strip shows the
**Dollar index** beside yields, oil, gold, copper and credit; India's shows
**USD/INR**, Brent, the US 10-year, the **Dollar index** and gold — US series on
purpose, since they drive foreign flows into India. Each tile has the last close,
1-day and 1-month change and a 3-month sparkline; hover for the *why*. The Fundamentals page
(Chart → Fundamentals) shows each Indian company's FII and DII holdings from its
quarterly shareholding filings.

---

## 1. What moves a currency

A currency is a price like any other: the rate at which the world wants to
swap into or out of a country's assets. Four forces do most of the work.

| Force | Pushes the currency up when… | Typical horizon |
|---|---|---|
| **Rate differential** | Its interest rates rise relative to other countries' — holding it pays more | Months to years |
| **Growth** | Its economy and earnings look stronger than elsewhere — capital comes to buy its stocks and companies | Quarters to years |
| **Risk appetite** | It is a "safe haven" (USD, JPY, CHF) and the world is scared; or a risk currency (INR, AUD) and the world is calm | Days to months |
| **Trade / current account** | It earns more foreign currency than it spends (exports, remittances) — less need to borrow abroad | Years |

**The short version: money flows to where it is paid best and treated
safest.** Rate differentials dominate most of the time; risk appetite takes
over in a panic. Trade balances set the slow background drift.

A currency move is rarely good or bad for a whole market — it moves money
*between* sectors, which is why a sector trader cares.

## 2. The US Dollar Index (DXY)

### 2.1 What is in it

The DXY is the dollar against a fixed basket of six currencies, set in 1973
(base 100): the euro about 58%, the yen about 14%, the pound about 12%, the
Canadian dollar about 9%, the Swedish krona and Swiss franc about 4% each. So the DXY is really **"the dollar against Europe, plus the yen."** It holds no
Chinese yuan, no rupee, no Mexican peso. It is still the number the market
watches, because the euro and yen dominate global funding — but an emerging
market currency can fall while the DXY is flat (see §4.4).

### 2.2 The dollar smile

The "dollar smile" (Stephen Jen's framing) says the dollar tends to rise at
**both ends** of the world economy:

- **Left side — fear.** In a global panic everyone rushes into dollars
  (Treasuries, cash, repaying dollar loans), even when the trouble began in America.
- **Right side — US outperformance.** Faster US growth and a Fed paying more
  than other central banks pull capital into US assets.
- **The bottom — synchronised global growth.** Money leaves the dollar for
  better returns abroad, and the dollar falls.

```series
title: The dollar in the 2008 crisis — a flight to safety
from: 2007-06-01
to: 2009-12-31
line: us:DXY | Dollar index (DXY)
line: us:SP500_TR | S&P 500 total return | right
band: 2008-09-15 2009-03-09 | Panic: Lehman to the low
mark: 2008-04-22 | Dollar low
caption: A US-born crisis, and still the dollar rose about 25% — from 71.3 in April 2008 to 89.1 in March 2009 — as the world scrambled for dollars. That is the left side of the smile.
```

March 2020 was the same, faster: the DXY hit 102.8 on 20 March, then fell
about 13% into early 2021 once the Fed flooded the system with dollars (see
[the liquidity guide](learn-macro-liquidity-credit.md)). **A rising dollar in a
sell-off is a stress signal; a falling one after it means relief.**

### 2.3 Why a strong dollar hurts US multinationals

Roughly 40% of S&P 500 revenue is earned abroad (more in tech and materials).
When the dollar rises, each euro or yen of foreign sales becomes fewer dollars,
so **reported** earnings shrink even if the business did not — the "currency
headwind" of 2022's earnings calls. Regional banks, utilities, US-focused
retailers and small caps are largely insulated.

### 2.4 Why a strong dollar hurts emerging markets

- **Dollar debt** borrowed by emerging-market governments and companies gets
  heavier in local terms.
- **Outflows:** US cash and bonds pay more, so foreign funds trim emerging-market stocks.
- **Imported inflation:** oil and most commodities are priced in dollars, so
  central banks may have to raise rates into a slowdown.

```series
title: The 2022 dollar spike and non-US stocks
from: 2021-01-01
to: 2023-12-31
line: us:INTL | Developed ex-US stocks (EFA) | log
line: us:DXY | Dollar index | right
line: us:INTL / us:SP500_TR | EFA relative to the S&P 500 | pane2
band: 2021-06-01 2022-09-27 | Dollar rally
mark: 2022-09-27 | Dollar peak 114
caption: The DXY rose from about 90 to 114.1 on 27 September 2022 — the same day EFA bottomed, about 30% below its 2021 high. EFA's ratio to the S&P 500 also bottomed that month, then rose sharply into January 2023 as the dollar fell back.
```

**When the dollar turns down after a big run, non-US stocks and multinationals
tend to lead:** from 27 September 2022 to July 2023 EFA rose about 37% to the
S&P 500's 28%; in 2025 the DXY fell about 11% and EFA gained about 12% on the S&P.

## 3. USD/INR — the rupee's long drift

### 3.1 The trend

```series
title: Rupees per US dollar since 2003
from: 2003-12-01
tf: M
line: india:USDINR | USD/INR (rupees per dollar)
band: 2008-01-01 2009-03-31 | Global crisis
band: 2013-05-22 2013-09-04 | Taper tantrum
band: 2022-01-01 2022-10-20 | Fed hikes, oil spike
caption: The rupee has gone from about 46 per dollar in December 2003 to about 95 now — a weakening of roughly 3.3% a year. The drift is steady; the damage comes in bursts.
```

Up means a **weaker** rupee. The slow drift mirrors India's higher inflation
than America's and is unremarkable; what matters to a trader are the **bursts**:

| Episode | USD/INR (stored closes) | What happened |
|---|---|---|
| 2008 crisis | 39.2 (Jan 2008) → 51.9 (Mar 2009) | Global deleveraging; foreign money left all emerging markets |
| 2013 taper tantrum | 55.4 (22 May) → 68.6 (4 Sep) | The Fed hinted at slowing QE; India had a large current-account deficit and was named one of the "Fragile Five" |
| 2018 | 63.3 (Jan) → 74.6 (11 Oct) | Brent above $86, rising US rates, the IL&FS credit scare at home |
| 2022 | 74.5 (Jan) → 83.0 (20 Oct) | Fed hiking fast, Brent to $128 in March, heavy foreign selling |
| 2025–26 | 85.8 (Jan 2025) → 96.9 (24 Jul 2026) | Rupee weakness even while the DXY fell — the pressure was India-specific |

### 3.2 What weakens the rupee

- **Oil.** India imports most of its crude (around 85% is the widely quoted
  figure), paid in dollars — which is why Brent is on the India strip.
- **US yields and the dollar.** Higher US rates narrow the gap with Indian
  yields, and foreign money goes home.
- **FII selling.** Foreigners who sell Indian shares convert the rupees back to
  dollars; that sale itself pushes the rupee down.
- **The current-account deficit.** India's goods imports (oil, gold,
  electronics) usually exceed exports, part-offset by services and remittances.
  When the gap widens — near 5% of GDP around 2012–13 — the rupee becomes
  hostage to foreign capital.

### 3.3 The RBI smooths it, it does not fix it

The RBI holds large foreign-exchange reserves (well above $600 billion in
recent years). It **sells dollars** when the rupee falls fast and **buys** when
inflows push it up; the stated aim is to curb volatility, not defend a level.
In 2022 reserves fell roughly $100 billion from their late-2021 peak (part of
it valuation). The result is a rupee that usually moves in small steps,
punctuated by sharp moves when the pressure overwhelms the smoothing.

**Trader's read:** a quiet USD/INR is the RBI doing its job; a USD/INR that
gaps higher day after day means outflows are winning, and that tends to come
with weak Indian stocks.

## 4. Who moves Indian stocks: FIIs and DIIs

### 4.1 Two big buyers

- **FIIs / FPIs** (foreign portfolio investors) react to the dollar, US
  yields, emerging-market allocations and India's valuation.
- **DIIs** (mutual funds, insurers, pension funds) are fed largely by **SIPs** —
  monthly investment plans from millions of savers that arrive regardless of headlines.

The NSE publishes provisional FII/DII cash figures after each session (not stored in this app).

### 4.2 2022: when domestic money absorbed the foreign selling

In 2022 foreigners sold well over ₹1 lakh crore of Indian shares in the cash
market — once a recipe for a deep bear market. This time domestic institutions
bought more than that, carried by SIPs running above ₹12,000 crore a month by
late 2022 (figures approximate). The Nifty 50 fell 16.5% to the June low and
**finished the year up about 3%**; the S&P 500 total return lost about 19%.

**The lesson: FII selling now hits harder in the stocks foreigners own most
(large private banks, IT, the index heavyweights) than in the whole market.**
A stock's FII share on the Fundamentals page tells you how exposed it is.

### 4.3 Why the rupee and the Nifty move together for a foreigner

A dollar-based investor earns the Nifty's return *and* the rupee's. When both
fall at once the loss compounds — which is why FII selling feeds itself.

```series
title: The Nifty 50 in rupees and in dollars
from: 2007-09-17
rebase: 100
line: india:NIFTY50 | Nifty 50 in rupees
line: india:NIFTY50 / india:USDINR | Nifty 50 in US dollars
mark: 2024-09-26 | Dollar-terms peak
caption: Since September 2007 the Nifty is up about 400% in rupees but only about 115% in dollars. From the September 2024 peak it is down about 14% in rupees and about 24% in dollars.
```

The gap is widest in the bursts: in 2008–09 the Nifty fell about 60% in
rupees and 69% in dollars, peak to trough; from May to late August 2013 about
15% in rupees but 30% in dollars. A fund staring at a 30% loss in three months
sells — felt in India as relentless distribution in large caps.

### 4.4 The rupee can fall while the DXY falls

In 2025 the DXY fell about 11% from its January high, yet USD/INR rose from
about 86 to about 90 over the year. When the rupee weakens against a *falling* dollar, the
cause is India-specific — outflows, oil, a widening trade gap — not "the
strong dollar". Watch both tiles on the India strip: **DXY up and rupee down
is global; DXY flat or down and rupee down is local**, and local pressure is
usually worse for Indian stocks.

## 5. Who wins and who loses from a weak rupee

| Usually helped | Why | Usually hurt | Why |
|---|---|---|---|
| IT services (^CNXIT) | Revenue in dollars, costs in rupees — a weaker rupee widens margins | Oil marketers (OMCs) | Buy crude in dollars; retail prices are sticky |
| Pharma exporters (^CNXPHARMA) | Large US generics business | Aviation | Fuel and aircraft leases in dollars |
| Textiles, specialty chemicals exporters | Dollar revenue | Paints, tyres | Crude-derived raw materials |
| | | Companies with dollar debt | Debt grows in rupee terms |
| | | Capital-goods and electronics importers | Imported components |

```series
title: 2013 — the taper tantrum split India's sectors
from: 2013-01-01
to: 2013-12-31
rebase: 100
line: india:^CNXIT | Nifty IT
line: india:^CNXPHARMA | Nifty Pharma
line: india:^NSEBANK | Bank Nifty
band: 2013-05-22 2013-09-04 | Rupee 55 → 69
caption: As the rupee lost about a fifth of its value, Nifty IT rose about 58% over 2013 and Pharma about 26%, while Bank Nifty fell about 34% from mid-May to late August. The Nifty 50 ended the year up only about 5%.
```

**The caveat matters as much:** in 2022 USD/INR rose about 11%, yet Nifty IT
fell about 27% as US tech was de-rated and clients cut spending. The currency
helps margins at the edge; it does not overrule the sector's own cycle — check
its relative strength on Markets → Sectors first.

## 6. For US traders: the dollar, commodities and gold

Most commodities are priced in dollars, so a weaker dollar makes them cheaper
for everyone else and tends to lift their dollar price — and vice versa.

```series
title: A falling dollar and rising gold, 2002–2008
from: 2002-01-01
to: 2008-06-30
line: us:GOLD_FUT | Gold ($/oz) | log
line: us:DXY | Dollar index | right
caption: The DXY fell about 40% from its January 2002 high (120) to April 2008 (71.3); gold went from under $280 to over $1,000 in March 2008.
```

The link is a tendency, not a law. In **2020–21** the DXY fell about 12% from
its March 2020 spike to May 2021 while copper rose about 80% from early March
2020. In **2022** the dollar's surge helped push gold down about 20% from March
to November, despite high inflation. But in **2024–26** gold roughly doubled
while the DXY ended where it started — other buyers overrode the dollar.

**Trader's read:** a dollar breaking down is a reason to look at materials
(XLB), energy (XLE), gold miners and non-US stocks on the Sectors page; a
dollar breaking out, a reason to be pickier there.

## 7. What a trader does with it

1. **Check the strip weekly** (Markets → Breadth): the 1-month change and the
   sparkline's direction, not the day's tick.
2. **US: a dollar in a strong uptrend** favours domestic-revenue names (small
   caps, regional banks, domestic retail) over multinationals and commodities;
   a dollar breaking down favours the opposite.
3. **India: a rupee falling fast** — USD/INR at new highs week after week, with
   Brent and US yields rising — is the classic FII-outflow setup: expect
   high-FII large caps to struggle, favour IT and pharma *if* their charts
   agree, go easy on oil-sensitive sectors.
4. **Size, don't predict.** Currency stress means smaller positions and
   cleaner setups. (The screener already halves risk per trade when the VIX or
   India VIX is above its threshold — `core/sizing.py`.)
5. **Never trade the currency story against the chart.** IT stocks outside
   Stage 2 and outside leading groups are not a buy because of the rupee.

## 8. What the evidence says

- **Robust:** the dollar's safe-haven spike in panics (2008, March 2020) and
  its knock-on to emerging markets; the rupee's long drift roughly tracking the
  inflation gap; a strong dollar's dent in multinationals' reported earnings.
- **Mostly true, with exceptions:** a weak rupee helps exporters' margins, but
  sector cycles overwhelm it (2022); dollar down, commodities up — until 2024.
- **Folklore:** that you can forecast currencies well enough to trade on —
  even a "no change" forecast is hard to beat (Meese and Rogoff, 1983). Use
  them as **context for which sectors to favour and how much risk to take**.
- **Lags:** a currency's effect on reported earnings shows up a quarter or
  two later; the flow effect (FII selling) is immediate.
- **FII/DII flows** are noisy day to day (one block deal can swing a day);
  read them in monthly sums.

## 9. Checklist

- [ ] Dollar index: 1–3 month trend; rising *in a sell-off* (stress) or on US growth?
- [ ] USD/INR: new highs, or quiet? Moving with the DXY (global) or against
      it (India-specific)?
- [ ] Brent and the US 10-year on the India strip — both rising is the rupee's worst mix
- [ ] Monthly FII/DII net flows (NSE) — is domestic buying still absorbing
      foreign selling?
- [ ] India positions: FII share of holdings (Fundamentals page) — high means outflow-exposed
- [ ] Sector leadership on Markets → Sectors: are exporters (IT, pharma) or
      commodities actually leading, or is it only a story?
- [ ] If stress is building (fast rupee fall, DXY spike, VIX up): smaller
      positions, fewer new entries

## Further reading

- **FRED** (St. Louis Fed) — trade-weighted dollar indexes and the INR/USD rate.
- **Reserve Bank of India** (rbi.org.in) — the weekly statistical supplement
  (foreign-exchange reserves) and the annual report's external-sector chapter.
- **NSDL** FPI monitor and **NSE** daily FII/DII activity — the flows in §4.
- Richard Meese and Kenneth Rogoff, "Empirical exchange rate models of the
  seventies: Do they fit out of sample?", *Journal of International Economics*
  (1983) — why currency forecasting is humbling.
