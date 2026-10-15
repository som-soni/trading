# Commodities — oil, gold and copper as context for stocks

Learning material on the three commodities a stock trader should watch. For each one: what
moves it, how it feeds into inflation, currencies and sector profits,
and how the effects differ between the US and India. The aim is not to trade
commodities. It is to know when oil, gold or copper is telling you which
**sectors** to favour, and how much risk the market carries. Companions:
[the inflation guide](learn-macro-inflation.md),
[the currencies guide](learn-macro-currencies.md) and
[the rates guide](learn-macro-rates.md).

**Where this shows in the app.** The macro strip (a row of market tiles) on **Markets → Breadth**
(`scripts/swing_screener/marketdata/macro.py`) shows WTI crude, gold and
copper for the US, and Brent crude, USD/INR and gold for India. Each tile has its
1-day and 1-month change and a one-line note on *why* it matters. Sector strength — energy,
materials, metals, oil marketers — is on **Markets → Sectors**. The charts
below are drawn from the same stored price data.

---

## 1. Context, not signals

Commodities are the raw costs and raw revenues of whole industries. When
crude doubles, an oil producer's profit jumps and an airline's disappears. Stock prices
adjust to this quickly. That is why **commodities are context, not
signals**. You do not buy an energy stock because oil rose yesterday. Instead, you
notice that oil has trended up for months, that energy is the strongest sector on the Sectors
page, and that your screens keep turning up oil stocks. Then you stop betting against it.

| Commodity | Mostly reflects | Helps | Hurts |
|---|---|---|---|
| **Oil** (WTI, Brent) | Supply politics, global demand | Producers, India's oil and gas producers | Airlines, chemicals, paints, tyres, oil importers, consumers |
| **Gold** | Fear, real rates, the dollar, central-bank buying | Miners, jewellers, gold financiers | Little directly; strong gold often means weak risk appetite |
| **Copper** | Industrial demand, China | Miners, materials | Wire, cable, appliance makers |

## 2. Oil — supply, demand and shocks

**Supply** comes from a few big producers, and politics shapes it. **OPEC+** (OPEC plus Russia and a
few others) sets production targets for a large share of world output. It
changes them to defend the price or its market share. Since
about 2010 the other producer that can quickly change its output is **US shale**. Shale wells start producing within months, so a high price
brings new supply and a low price shuts it off. Wars, sanctions and shipping
disruptions add sudden shocks. **Demand** follows the world economy, with
China and India growing fastest. In the short run, neither supply nor demand **responds much to price**
(you cannot quickly drive less or drill more). So a small gap between them produces
big price moves.

```series
title: WTI crude, 2007–2024 — the big shocks
from: 2007-01-01
to: 2024-12-31
tf: W
line: us:WTI | WTI crude ($/bbl) | zero
band: 2014-06-20 2016-02-11 | 2014–16 glut
mark: 2008-07-03 | $145 peak
mark: 2020-04-20 | negative settle
mark: 2022-03-08 | 2022 spike
caption: Three crashes and two spikes in 17 years. The weekly line hides the worst day: on 20 April 2020 front-month WTI settled at −$37.63.
```

- **2008.** WTI closed at about **$145 on 3 July 2008** and about **$34 on
  19 December**. That is down roughly three quarters in under six months, as the
  financial crisis wiped out demand.
- **2014–16.** Shale output surged, and OPEC chose to keep its market share instead of
  cutting production. WTI fell from about **$107 (June 2014)** to about **$26 (February
  2016)**, again about −75%. Brent went from about $115 to $28.
- **April 2020.** Lockdowns cut demand faster than wells could be shut. Storage at Cushing —
  where oil is physically handed over when WTI futures expire — filled up. On **20
  April 2020 the expiring contract settled at −$37.63**. Holders paid buyers to take
  barrels they had nowhere to store. It was one contract on one day (Brent
  never went negative; its low that week was about $19). The lesson is
  that a futures price is not simply "the price of oil".
- **2022.** Russia's invasion of Ukraine took WTI from about $92 the day
  before to about **$124 on 8 March**, and Brent to about $128. Both had fallen
  back about 40% by December.

The data also shows a spike in early 2026: Brent ended March 2026 near $118,
up from about $61 at the end of 2025.

**How oil reaches everything else:**

1. **Inflation.** Fuel is in every CPI
   basket and in the cost of everything transported. So a spike lifts headline
   inflation within a month or two, and keeps central banks from cutting rates.
2. **Consumer spending.** A lasting spike works like a tax on consumers. Several US recessions
   followed one.
3. **Profits.** Higher oil is extra revenue for producers and an extra cost for airlines,
   chemicals, paints, tyres and logistics.

## 3. Energy stocks versus oil

Energy stocks (US: **XLE**) follow oil, but on their own timing. The
differences matter.

```series
title: Energy stocks (XLE) against WTI crude, 2019–2024
from: 2019-01-01
to: 2024-12-31
tf: W
line: us:XLE | Energy sector (XLE)
line: us:WTI | WTI crude ($/bbl) | right
band: 2022-03-08 2022-11-15 | oil falls, XLE keeps rising
caption: Oil peaked in March 2022, but energy stocks made new highs into November. Investors valued the companies' cash flows and share buybacks, not that day's oil price.
```

- **Down together.** June 2014 to January 2016: XLE about −49%, WTI −75%.
- **Up together.** End of October 2020 to 8 June 2022: XLE up about **220%**
  (adjusted prices) while WTI went from about $36 to $122.
- **Not always together.** WTI peaked on 8 March 2022. Yet XLE made its high of
  the year on 15 November and finished 2022 up about **53%**, in a year the
  S&P 500 fell about **20%**. Selling energy stocks because crude fell after March
  was too early.

**The reading:** decide based on the *sector's own trend* (Sectors page, the XLE
chart), and use oil as the explanation. When the two disagree for months, the
stocks are usually right about earnings.

## 4. Oil and India

India imports most of the crude it refines. So oil affects India's whole economy
in a way it does not for the US (now a net petroleum exporter).

```series
title: Brent crude and the rupee, 2012 to today
from: 2012-01-01
tf: W
line: india:BRENT | Brent crude ($/bbl)
line: india:USDINR | USD/INR (₹ per $) | right
band: 2013-05-22 2013-09-04 | 2013 rupee crisis
band: 2022-02-24 2022-10-20 | 2022: oil spike, rupee to 83
caption: A rising USD/INR line means a weaker rupee. Oil is one driver among several — the dollar and foreign money flows matter as much. But the rupee's bad stretches (2013, autumn 2018, 2022) all came with expensive oil.
```

1. **Import bill.** More expensive crude widens the trade and current-account
   deficits (India pays out more than it earns abroad). More dollars are needed for the same barrels.
2. **The rupee.** USD/INR went from about 54 to about 69 between May and
   early September 2013. It went from about 63 to 75 in 2018, as Brent climbed to $86
   in October, and from about 74 to 83 through 2022. Over the full record it has gone
   from about 45 (2003) to about 95 now.
3. **Inflation.** Fuel, freight and fertiliser prices feed into CPI and especially WPI, India's wholesale price index
   (see [the inflation guide](learn-macro-inflation.md)). That can stop the
   RBI from cutting rates.
4. **Fuel-tax policy.** Officially, pump prices follow the market. In
   practice the government manages them. When crude falls, the government has often **raised
   excise duty** (the fuel tax) and kept the gain. When crude spikes, it may cut the duty, or the
   state-owned oil marketing companies hold pump prices down and take losses for months.

| When crude rises — hurt | Why |
|---|---|
| **Oil marketing companies** (OMCs) | Pump prices lag crude; marketing margins go negative |
| **Paints** | Many raw materials are crude derivatives |
| **Aviation** | Jet fuel is the largest single cost |
| **Tyres** | Synthetic rubber and carbon black come from crude |
| Chemicals, plastics, logistics | Input and freight costs |
| **Helped** | |
| **Upstream producers** (companies that find and pump oil and gas) | They get higher prices for what they sell — partly taken back by windfall taxes, as in 2022 |
| IT exporters (indirectly) | A weaker rupee lifts rupee revenue |

Falling crude reverses the table. OMCs, paints and aviation were classic
winners from the 2014–16 collapse. **For an India trader:** a lasting
Brent uptrend together with a weakening rupee is when foreign
investors tend to sell Indian shares. Be more selective, hold fewer and smaller
positions, and stay away from companies that use a lot of oil, however good their charts look.

## 5. Gold — fear, real rates and the dollar

Gold pays no interest and has no earnings. Its price depends on what holding
it costs you and what it protects you against:

- **Real yields.** If you hold gold, you give up the real yield you could earn on a safe
  bond. So when real yields rise, gold usually falls. The app does not store real (TIPS) yields, so it uses the ordinary 10-year
  yield as a stand-in.
- **The dollar.** Gold is priced in dollars. A stronger dollar tends to push
  its dollar price down.
- **Fear.** Gold is a hedge against the financial system failing. But in the worst phase of a crash
  it is often *sold* to raise cash: from March to late October 2008 gold fell
  about 27%.
- **Official buying.** Central banks are large buyers who do not care much about the price. Their buying
  can outweigh everything else for years.

```series
title: Gold against the 10-year yield and the dollar, 2011–2025
from: 2011-01-01
to: 2025-12-31
tf: W
line: us:GOLD_FUT | Gold ($/oz) | log
line: us:US10Y | US 10-year yield (%) | right
line: us:DXY | Dollar index (DXY) | pane2
band: 2013-01-01 2013-12-31 | taper tantrum
band: 2023-01-01 2024-12-31 | yields 4–5%, gold rises anyway
caption: The textbook link held in 2013 and 2022 — yields and the dollar up, gold down. From 2023 it broke: gold rose with the 10-year near 4–5% and a firm dollar.
```

**When the link worked.** In 2013 the 10-year rose from about 1.4% (July
2012) to about 3.0% after the Fed talked of "tapering" (slowing its bond buying). Gold fell from about
$1,675 to $1,200 over the year (about −28%). From its August 2011 high near
$1,889 to its December 2015 low near $1,051, it lost about 44%. In 2022 the
10-year went from about 1.6% to over 4%, and the dollar index hit about 114 on 27
September. Gold fell about 20%, from March to about $1,631 on 3 November.

**When it broke — be honest about this.** From late 2022 gold rose while the
10-year stayed near or above 4% (peaking near 5.0% in October 2023). Gold went
from about $1,630 to about **$2,640 at the end of 2024**. It rose about 60% more
in 2025 (to about $4,340), and the stored series peaked near **$5,300 in late
January 2026**. The reason most often given is **central-bank buying**.
Emerging-market central banks moved part of their reserves out of the dollar
after Russia's reserves were frozen in 2022. Buying driven by wars and political tension added to it. (In
2025 the textbook drivers also pointed up: the dollar index fell about 10%.)
The lesson: **a relationship that held for a decade can stop working for
years.** Use it to prompt a question, not as a model.

### Gold in India

In India gold is a **cultural asset and a way households save** — for weddings,
festivals (Akshaya Tritiya, Dhanteras), and rural savings. India is one of the
two largest consumers and imports almost all of its gold, so:

- **The rupee price matters.** In 2022 gold priced in dollars ended flat, while the
  rupee fell about 11%. The stored Indian gold series rose about 13%.
- **Import duty** is a tool the government uses. It raises the duty to cut imports when the current
  account is under strain, and cuts it to reduce smuggling (the July 2024 Budget cut it
  sharply). Duty changes move jewellers, gold-loan companies and gold ETFs.

**For a trader:** gold up with stocks down means investors are running from risk. Gold up with stocks
also up (2024–25) more likely reflects central-bank reserve buying or currency moves. The effect you can trade
is in gold miners (US) or jewellers and gold-loan companies (India). Their own
charts decide.

## 6. Copper — "Dr. Copper" and the copper/gold ratio

Copper goes into wiring, buildings, motors and power grids. So its price is a rough,
up-to-date reading of **industrial demand** — hence the joke "Dr. Copper, the metal with a PhD
in economics". China uses about half the world's copper. Electrification
(grids, EVs, data centres) has added a lasting source of extra demand since 2020.

In 2008 copper fell about **69%** from July to December. From the March 2020
low to May 2021 it rose about **125%**, and materials (**XLB**) about 127%.

Copper tracks growth and gold tracks fear. Divide copper by gold and you get one line for **growth
versus fear**. For most of 2005–2022 this **copper/gold ratio** moved with the
10-year yield, because both follow what investors expect for growth.

```series
title: The copper/gold ratio and the 10-year yield, 2005 to today
from: 2005-01-01
tf: W
line: us:COPPER / us:GOLD_FUT | Copper / gold ratio
line: us:US10Y | US 10-year yield (%) | right
band: 2023-01-01 2025-12-31 | the link breaks
caption: The ratio's units mean nothing; watch its direction against the yield. They moved together for years. Since 2023 the ratio fell to record lows while the 10-year stayed near 4% — gold's rally, not weak copper.
```

- **2008:** the ratio more than halved over the year; yields followed it down.
- **2020–21:** from April 2020 to October 2021 the ratio about doubled, and
  the 10-year rose from about 0.5% to 1.7%. This was the "reflation trade": investors betting on the economy reviving.
- **2022–25, broken:** the ratio fell about 55% from February 2022 to
  October 2025. Yet copper itself made **records** (about $5.60/lb at the
  end of 2025, about $6.80 in September 2026). Gold simply rose faster. When
  one half of a ratio is driven by something else, the ratio stops meaning "growth".

**Materials stocks.** XLB holds a lot of chemical companies, whose costs *rise* with
oil. So it is not a pure bet on copper. For metals, use the industry groups on
the Sectors page. Metal stocks often peak while the metal is still rising.

**For a trader:** rising copper, with materials and metals the strongest groups, is the
early-recovery background in which industrials, materials and small caps do
well. Copper collapsing while yields fall is a scare about growth. Favour
defensive stocks and use smaller positions.

## 7. What a trader does with this

1. **Sector context.** A commodity trending for months (not days) tells you
   which sector moves are likely to last. The Sectors page and the stocks'
   own charts still pick the trades.
2. **Not standalone signals.** A one-day oil jump is noise for a swing
   trader. Its effect on individual stocks is already in their prices.
3. **Know your exposure.** Five positions in companies that use a lot of oil, while Brent is breaking
   out, is one big bet, not five small ones.
4. **Breaks are questions.** When a textbook link stops working (gold vs
   yields since 2023), find out why before trusting it again.

## 8. What the evidence says

- **Robust:** oil drives energy-sector earnings and, over months, energy-stock
  returns. Oil shocks lift headline inflation quickly. India's current account
  and rupee are sensitive to crude. Copper rises and falls with the economy.
- **Robust but unstable:** gold moved opposite to real yields and the dollar
  for long stretches. That link broke from 2022–23, when central-bank buying became the main driver.
- **Closer to folklore:** "Dr. Copper predicts recessions." Copper does fall *during*
  recessions. But it also gives false alarms (China slowdowns that did not spread),
  and it moves on supply news such as mine strikes. The way the copper/gold ratio has matched
  yields describes the past; it does not forecast.
- **Delays:** oil reaches CPI quickly (a month or two). It reaches consumer spending and
  central-bank decisions more slowly, depending on how long the move lasts. Stocks usually move
  *before* the commodity data confirms the trend.
- **Measurement:** the stored oil, gold and copper prices are front-month futures (the contract nearest expiry).
  The series switches to the next contract at each expiry and can behave oddly near expiry. Use them for trend, not exact levels.

## 9. Checklist

- Oil: trending over 1–3 months? New high or low for the year? Do the
  energy groups on the Sectors page agree?
- India: Brent and USD/INR together — both rising is the warning; check your
  OMC, paint, aviation and tyre exposure.
- Gold: rising while stocks fall (fear) or while they rise (reserve buying or currency)? Moving in
  line with the 10-year and the dollar, or breaking away from them?
- Copper and copper/gold: growth backdrop improving or fading? Materials and
  metals groups leading or lagging?
- Concentration: how many positions share one commodity exposure?
- Due this week: an OPEC+ meeting, an Indian excise or gold-duty change?

## Further reading

- U.S. Energy Information Administration (eia.gov) — the weekly petroleum
  status report and the short-term energy outlook.
- FRED, Federal Reserve Bank of St. Louis (fred.stlouisfed.org) — oil and
  real-yield (TIPS) series.
- World Gold Council (gold.org) — gold demand trends, central-bank buying,
  Indian jewellery demand.
- Reserve Bank of India (rbi.org.in) — policy statements and the
  balance-of-payments data behind the rupee.
- Daniel Yergin, *The Prize* — the history of oil, OPEC and price shocks.
