# Currencies and capital flows — the dollar, the rupee and who gets paid

Learning material. This guide covers:

- what moves a currency;
- the US Dollar Index, and why a strong dollar squeezes US multinationals and emerging markets;
- the rupee's slow, long-run fall and what speeds it up;
- how foreign and domestic money push Indian stocks around;
- what a swing trader does with all of it.

Companion guides: [the interest-rates guide](learn-macro-rates.md) (the gap
between countries' interest rates drives currencies), [the commodities guide](learn-macro-commodities.md)
(oil and the rupee move closely together, because India buys its oil in dollars) and
[the liquidity and credit guide](learn-macro-liquidity-credit.md).

**Where this shows in the app.** Markets → Breadth carries a macro strip: a row
of small tiles for key market series (defined in
`scripts/swing_screener/marketdata/macro.py`, `STRIP`). The US strip shows the
**Dollar index** beside yields, oil, gold, copper and credit. India's strip shows
**USD/INR**, Brent, the US 10-year, the **Dollar index** and gold. The US series
are there on purpose, because they drive foreign money into and out of India. Each tile shows the last close,
the 1-day and 1-month change, and a 3-month sparkline (a tiny line chart). Hover over a tile to see why it matters. The Fundamentals page
(Chart → Fundamentals) shows how much of each Indian company is held by FIIs and DIIs, taken from its
quarterly shareholding filings.

---

## 1. What moves a currency

A currency is a price like any other. It is the rate at which people around the world exchange
money to buy or sell a country's assets. Four forces do most of the work.

| Force | Pushes the currency up when… | Typical horizon |
|---|---|---|
| **Rate differential** (the gap between its interest rates and other countries') | Its interest rates rise relative to other countries' — holding it pays more | Months to years |
| **Growth** | Its economy and earnings look stronger than elsewhere — investors bring money in to buy its stocks and companies | Quarters to years |
| **Risk appetite** (how willing investors are to take risk) | It is a "safe haven" that investors buy when scared (USD, JPY, CHF) and the world is scared; or a risk currency that investors buy when confident (INR, AUD) and the world is calm | Days to months |
| **Trade / current account** (all the money a country earns from abroad minus all it pays abroad) | It earns more foreign currency than it spends (exports, remittances) — less need to borrow abroad | Years |

**The short version: money goes where it earns the most and is safest.**
Usually, rate differentials matter most. In a panic, risk appetite
matters more. Trade balances cause the slow movement in the background.

A currency move is rarely good or bad for a whole market. Instead it helps some sectors
and hurts others, which is why a sector trader cares.

## 2. The US Dollar Index (DXY)

### 2.1 What is in it

The DXY measures the dollar against a fixed basket of six currencies. The basket was set in 1973,
when the index started at 100. The weights are: the euro about 58%, the yen about 14%, the pound about 12%, the
Canadian dollar about 9%, the Swedish krona and Swiss franc about 4% each. So the DXY is really **"the dollar against Europe, plus the yen."** It holds no
Chinese yuan, no rupee, no Mexican peso. It is still the number the market
watches, because the euro and yen dominate global funding (the borrowing and lending that moves money between countries). But an emerging
market currency can fall while the DXY is flat (see §4.4).

### 2.2 The dollar smile

The "dollar smile" is a way of describing the dollar suggested by the economist Stephen Jen. It says the dollar tends to rise in
**two opposite situations**, the two ends of the "smile":

- **Left side — fear.** In a global panic everyone rushes to hold dollars: they buy
  Treasuries, hold cash, and repay loans taken in dollars. This happens even when the trouble began in America.
- **Right side — the US doing better than everyone else.** Faster US growth, and a Fed paying higher rates
  than other central banks, draw money into US assets.
- **The bottom — the whole world growing together.** Money leaves the dollar for
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

March 2020 was the same, only faster. The DXY hit 102.8 on 20 March. It then fell
about 13% into early 2021, once the Fed had pumped huge amounts of new dollars into the financial system (see
[the liquidity guide](learn-macro-liquidity-credit.md)). **A dollar that rises while stocks are falling is a sign of stress.
A dollar that falls afterwards is a sign the stress is easing.**

### 2.3 Why a strong dollar hurts US multinationals

Roughly 40% of S&P 500 revenue is earned abroad (more in tech and materials).
When the dollar rises, each euro or yen of foreign sales converts into fewer dollars.
So **reported** earnings shrink even if the business itself did not. Companies called this the "currency
headwind" on their 2022 earnings calls. Regional banks, utilities, US-focused
retailers and small caps earn mostly at home, so they are largely unaffected.

### 2.4 Why a strong dollar hurts emerging markets

- **Dollar debt.** Emerging-market governments and companies that borrowed in dollars
  need more of their own currency to repay it.
- **Outflows.** US cash and bonds pay more, so foreign funds sell some of their emerging-market stocks.
- **Imported inflation.** Oil and most commodities are priced in dollars, so they cost more in local currency.
  Central banks may then have to raise rates even while the economy is slowing.

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

**When the dollar turns down after a big rise, non-US stocks and multinationals
tend to do best.** From 27 September 2022 to July 2023, EFA (an ETF of developed-market stocks outside the US) rose about 37% against the
S&P 500's 28%. In 2025 the DXY fell about 11%, and EFA beat the S&P by about 12%.

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

Up on this chart means a **weaker** rupee (more rupees per dollar). The slow drift reflects India's inflation being higher
than America's, and it is nothing unusual. What matters to a trader are the **bursts** of sudden weakness:

| Episode | USD/INR (stored closes) | What happened |
|---|---|---|
| 2008 crisis | 39.2 (Jan 2008) → 51.9 (Mar 2009) | Investors worldwide sold assets to pay down debt; foreign money left all emerging markets |
| 2013 taper tantrum | 55.4 (22 May) → 68.6 (4 Sep) | The Fed hinted at slowing QE; India had a large current-account deficit and was named one of the "Fragile Five" (five economies seen as most dependent on foreign money) |
| 2018 | 63.3 (Jan) → 74.6 (11 Oct) | Brent above $86, rising US rates, the IL&FS credit scare at home |
| 2022 | 74.5 (Jan) → 83.0 (20 Oct) | Fed hiking fast, Brent to $128 in March, heavy foreign selling |
| 2025–26 | 85.8 (Jan 2025) → 96.9 (24 Jul 2026) | Rupee weakness even while the DXY fell — the pressure was India-specific |

### 3.2 What weakens the rupee

- **Oil.** India imports most of its crude oil (around 85% is the widely quoted
  figure), and pays for it in dollars. That is why Brent (the main global oil price) is on the India strip.
- **US yields and the dollar.** Higher US rates shrink the extra return Indian
  bonds pay over US bonds, so foreign money goes home.
- **FII selling.** Foreigners who sell Indian shares convert the rupees back to
  dollars. Selling those rupees itself pushes the rupee down.
- **The current-account deficit** (India paying out more foreign currency than it earns). India usually imports more goods (oil, gold,
  electronics) than it exports. Services exports and money sent home by Indians abroad cover part of the gap.
  When the gap widens — it was near 5% of GDP around 2012–13 — the rupee depends on foreign investors
  continuing to bring money in, and falls when they stop.

### 3.3 The RBI smooths it, it does not fix it

The RBI (Reserve Bank of India) holds large foreign-exchange reserves (well above $600 billion in
recent years). It **sells dollars** when the rupee falls fast. It **buys dollars** when
money flowing in pushes the rupee up. Its stated aim is to reduce sharp swings, not to hold the rupee at a particular level.
In 2022 reserves fell roughly $100 billion from their late-2021 peak. Part of
that fall was not selling but the changing value of the assets held. The result is a rupee that usually moves in small steps,
with occasional sharp moves when the selling pressure is too big for the RBI to smooth out.

**Trader's read:** a quiet USD/INR means the RBI is doing its job. A USD/INR that
jumps higher day after day means money leaving India is overwhelming the RBI. That usually comes
with weak Indian stocks.

## 4. Who moves Indian stocks: FIIs and DIIs

### 4.1 Two big buyers

- **FIIs / FPIs** (foreign portfolio investors — the newer official name for FIIs). They react to the dollar, US
  yields, how much global funds decide to put into emerging markets, and how expensive India looks.
- **DIIs** (mutual funds, insurers, pension funds). They are fed largely by **SIPs**
  from millions of savers. That money arrives every month regardless of headlines.

The NSE publishes provisional FII/DII figures for cash-market (ordinary share) buying and selling after each session. They are not stored in this app.

### 4.2 2022: when domestic money absorbed the foreign selling

In 2022 foreigners sold well over ₹1 lakh crore of Indian shares in the cash
market. In the past, selling on that scale would have meant a deep bear market. This time domestic institutions
bought more than that. Their buying was carried by SIPs running above ₹12,000 crore a month by
late 2022 (figures approximate). The Nifty 50 fell 16.5% to the June low and then
**finished the year up about 3%**. The S&P 500 total return lost about 19%.

**The lesson: FII selling now hits the stocks foreigners own most
(large private banks, IT, the biggest index stocks) harder than the whole market.**
A stock's FII share on the Fundamentals page tells you how exposed it is.

### 4.3 Why the rupee and the Nifty move together for a foreigner

An investor who counts in dollars earns the Nifty's return *and* the rupee's change against the dollar. When both
fall at once, the two losses multiply. That pushes more foreigners to sell, which pushes both down further.

```series
title: The Nifty 50 in rupees and in dollars
from: 2007-09-17
rebase: 100
line: india:NIFTY50 | Nifty 50 in rupees
line: india:NIFTY50 / india:USDINR | Nifty 50 in US dollars
mark: 2024-09-26 | Dollar-terms peak
caption: Since September 2007 the Nifty is up about 400% in rupees but only about 115% in dollars. From the September 2024 peak it is down about 14% in rupees and about 24% in dollars.
```

The gap is widest during the sharp sell-offs. In 2008–09 the Nifty fell about 60% in
rupees and 69% in dollars, peak to trough. From May to late August 2013 it fell about
15% in rupees but 30% in dollars. A fund facing a 30% loss in three months
sells. In India that shows up as steady, heavy selling in large caps, day after day.

### 4.4 The rupee can fall while the DXY falls

In 2025 the DXY fell about 11% from its January high. Yet USD/INR rose from
about 86 to about 90 over the year. When the rupee weakens against a *falling* dollar, the
cause is something specific to India — money leaving, oil, a widening trade gap — not "the
strong dollar". Watch both tiles on the India strip. **DXY up and rupee down
is a global move. DXY flat or down and rupee down is a local one.** Local pressure is
usually worse for Indian stocks.

## 5. Who wins and who loses from a weak rupee

| Usually helped | Why | Usually hurt | Why |
|---|---|---|---|
| IT services (^CNXIT) | Revenue in dollars, costs in rupees — a weaker rupee widens margins | Oil marketing companies (OMCs: the fuel retailers) | Buy crude in dollars; pump prices are slow to rise |
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

**The caveat matters just as much.** In 2022 USD/INR rose about 11%, yet Nifty IT
fell about 27%. Investors were paying less for US tech earnings, and clients cut spending. The currency
helps margins a little. It does not outweigh the sector's own ups and downs. Check
the sector's relative strength on Markets → Sectors first.

## 6. For US traders: the dollar, commodities and gold

Most commodities are priced in dollars. A weaker dollar makes them cheaper
for buyers using other currencies, and that tends to lift their dollar price. A stronger dollar does the opposite.

```series
title: A falling dollar and rising gold, 2002–2008
from: 2002-01-01
to: 2008-06-30
line: us:GOLD_FUT | Gold ($/oz) | log
line: us:DXY | Dollar index | right
caption: The DXY fell about 40% from its January 2002 high (120) to April 2008 (71.3); gold went from under $280 to over $1,000 in March 2008.
```

The link is a tendency, not a law. In **2020–21** the DXY fell about 12% from
its March 2020 spike to May 2021, while copper rose about 80% from early March
2020. In **2022** the dollar's surge helped push gold down about 20% from March
to November, despite high inflation. But in **2024–26** gold roughly doubled
while the DXY ended where it started. Other buyers mattered more than the dollar.

**Trader's read:** if the dollar is breaking down, look at materials
(XLB), energy (XLE), gold miners and non-US stocks on the Sectors page. If the
dollar is breaking out, be pickier there.

## 7. What a trader does with it

1. **Check the strip weekly** (Markets → Breadth). Look at the 1-month change and the
   sparkline's direction, not the single day's move.
2. **US: a dollar in a strong uptrend** favours companies that earn mainly at home (small
   caps, regional banks, domestic retail) over multinationals and commodities.
   A dollar breaking down favours the opposite.
3. **India: a rupee falling fast** — USD/INR at new highs week after week, with
   Brent and US yields rising — is the classic sign that FIIs are pulling money out. In that case:
   expect large caps with high FII ownership to struggle; favour IT and pharma *if* their charts
   agree; go easy on sectors that suffer when oil rises.
4. **Size, don't predict.** Currency stress means smaller positions and
   only the cleanest setups. (The screener already halves risk per trade when the VIX or
   India VIX is above its threshold.)
5. **Never trade the currency story against the chart.** IT stocks outside
   Stage 2 and outside leading groups are not a buy because of the rupee.

## 8. What the evidence says

- **Robust:** the dollar jumps in panics as investors run to safety (2008, March 2020), and
  that hurts emerging markets in turn; the rupee's long drift roughly follows the
  gap between Indian and US inflation; a strong dollar reduces multinationals' reported earnings.
- **Mostly true, with exceptions:** a weak rupee helps exporters' margins, but
  the sector's own ups and downs can outweigh it (2022); dollar down, commodities up — until 2024.
- **Folklore:** that you can forecast currencies well enough to trade on them.
  Even simply forecasting "no change" is hard to beat (Meese and Rogoff, 1983). Use
  currencies as **context for which sectors to favour and how much risk to take**.
- **Lags:** a currency's effect on reported earnings shows up a quarter or
  two later. The effect through money flows (FII selling) is immediate.
- **FII/DII flows** jump around from day to day (one block deal — a single very large trade — can swing a day's figure).
  Read them as monthly totals.

## 9. Checklist

- [ ] Dollar index: 1–3 month trend; rising *in a sell-off* (stress) or on US growth?
- [ ] USD/INR: new highs, or quiet? Moving with the DXY (global) or against
      it (India-specific)?
- [ ] Brent and the US 10-year on the India strip — both rising is the rupee's worst mix
- [ ] Monthly FII/DII net flows (NSE) — is domestic buying still absorbing
      foreign selling?
- [ ] India positions: FII share of holdings (Fundamentals page) — high means outflow-exposed
- [ ] Sector leadership on Markets → Sectors: are exporters (IT, pharma) or
      commodities actually outperforming, or is it only a story?
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
