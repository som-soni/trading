# Commodities — oil, gold and copper as context for stocks

Learning material: the three commodities a stock trader should watch — what
moves each one, how it feeds into inflation, currencies and sector profits,
and how the effects differ between the US and India. The aim is not to trade
commodities; it is to know when oil, gold or copper is telling you which
**sectors** to favour and how much risk the market carries. Companions:
[the inflation guide](learn-macro-inflation.md),
[the currencies guide](learn-macro-currencies.md) and
[the rates guide](learn-macro-rates.md).

**Where this shows in the app.** The macro strip on **Markets → Breadth**
(`scripts/swing_screener/marketdata/macro.py`) shows WTI crude, gold and
copper for the US, and Brent crude, USD/INR and gold for India, each with its
1-day and 1-month change and a one-line *why*. Sector strength — energy,
materials, metals, oil marketers — is on **Markets → Sectors**. The charts
below are drawn from the same stored series.

---

## 1. Context, not signals

Commodities are the raw costs and raw revenues of whole industries. When
crude doubles, a producer's profit jumps and an airline's evaporates. The
market prices this quickly — which is why **commodities are context, not
signals**. You do not buy an energy stock because oil rose yesterday. You
notice that oil has trended up for months, that energy leads on the Sectors
page, that your screens keep throwing up oil names — and you stop fighting it.

| Commodity | Mostly reflects | Helps | Hurts |
|---|---|---|---|
| **Oil** (WTI, Brent) | Supply politics, global demand | Producers, upstream India | Airlines, chemicals, paints, tyres, oil importers, consumers |
| **Gold** | Fear, real rates, the dollar, central-bank buying | Miners, jewellers, gold financiers | Little directly; strong gold often means weak risk appetite |
| **Copper** | Industrial demand, China | Miners, materials | Wire, cable, appliance makers |

## 2. Oil — supply, demand and shocks

**Supply** is concentrated and political. **OPEC+** (OPEC plus Russia and a
few others) sets production targets for a large share of world output, and
changes them to defend price or market share. The other swing producer since
about 2010 is **US shale**: wells that come on within months, so a high price
invites new supply and a low price shuts it off. Wars, sanctions and shipping
disruptions add sudden shocks. **Demand** follows the world economy, with
China and India the growth engines. Both are **inelastic in the short run**
(you cannot quickly drive less or drill more), so small imbalances produce
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
  19 December** — down roughly three quarters in under six months as the
  financial crisis destroyed demand.
- **2014–16.** Shale output surged and OPEC defended market share instead of
  cutting. WTI fell from about **$107 (June 2014)** to about **$26 (February
  2016)**, again about −75%; Brent went from about $115 to $28.
- **April 2020.** Lockdowns removed demand faster than wells could shut, and
  storage at Cushing — where WTI futures are delivered — filled. On **20
  April 2020 the expiring contract settled at −$37.63**: holders paid to be
  rid of barrels they could not store. It was one contract on one day (Brent
  never went negative; its low that week was about $19), and the lesson is
  that a futures price is not "the price of oil" in the abstract.
- **2022.** Russia's invasion of Ukraine took WTI from about $92 the day
  before to about **$124 on 8 March**, Brent to about $128. Both had given
  back about 40% by December.

The data also shows a spike in early 2026: Brent ended March 2026 near $118,
from about $61 at the end of 2025.

**How oil reaches everything else:** (1) **inflation** — fuel is in every CPI
basket and in the cost of everything transported, so a spike lifts headline
inflation within a month or two and keeps central banks tight; (2) **consumer
spending** — a sustained spike works like a tax, and several US recessions
followed one; (3) **profits** — revenue for producers, cost for airlines,
chemicals, paints, tyres and logistics.

## 3. Energy stocks versus oil

Energy stocks (US: **XLE**) track oil, but with their own timing — and the
gaps matter.

```series
title: Energy stocks (XLE) against WTI crude, 2019–2024
from: 2019-01-01
to: 2024-12-31
tf: W
line: us:XLE | Energy sector (XLE)
line: us:WTI | WTI crude ($/bbl) | right
band: 2022-03-08 2022-11-15 | oil falls, XLE keeps rising
caption: Oil peaked in March 2022, but energy stocks made new highs into November — the market priced cash flows and buybacks, not the spot price.
```

- **Down together.** June 2014 to January 2016: XLE about −49%, WTI −75%.
- **Up together.** End of October 2020 to 8 June 2022: XLE up about **220%**
  (adjusted prices) while WTI went from about $36 to $122.
- **Not in lockstep.** WTI peaked on 8 March 2022, yet XLE made its high of
  the year on 15 November and finished 2022 up about **53%** — in a year the
  S&P 500 fell about **20%**. Selling energy because crude fell after March
  was early.

**The reading:** decide on the *sector's own trend* (Sectors page, the XLE
chart) and use oil as the explanation. When the two disagree for months, the
stocks are usually right about earnings.

## 4. Oil and India

India imports most of the crude it refines, so oil is a **macro variable**
for India in a way it is not for the US (now a net petroleum exporter).

```series
title: Brent crude and the rupee, 2012 to today
from: 2012-01-01
tf: W
line: india:BRENT | Brent crude ($/bbl)
line: india:USDINR | USD/INR (₹ per $) | right
band: 2013-05-22 2013-09-04 | 2013 rupee crisis
band: 2022-02-24 2022-10-20 | 2022: oil spike, rupee to 83
caption: A rising USD/INR line is a weaker rupee. Oil is one driver among several — the dollar and foreign flows matter as much — but the rupee's bad stretches (2013, autumn 2018, 2022) came with dear oil.
```

1. **Import bill.** Dearer crude widens the trade and current-account
   deficits — more dollars needed for the same barrels.
2. **The rupee.** USD/INR went from about 54 to about 69 between May and
   early September 2013; from about 63 to 75 in 2018 as Brent climbed to $86
   in October; from about 74 to 83 through 2022. Over the record it has gone
   from about 45 (2003) to about 95 now.
3. **Inflation.** Fuel, freight and fertiliser feed CPI and especially WPI
   (see [the inflation guide](learn-macro-inflation.md)), which can keep the
   RBI from cutting.
4. **Fuel-tax policy.** Pump prices are formally market-linked but in
   practice managed. When crude falls the government has often **raised
   excise duty** and kept the gain; when crude spikes it may cut duty, or the
   state-owned oil marketers hold pump prices and absorb losses for months.

| When crude rises — hurt | Why |
|---|---|
| **Oil marketing companies** (OMCs) | Pump prices lag crude; marketing margins go negative |
| **Paints** | Many raw materials are crude derivatives |
| **Aviation** | Jet fuel is the largest single cost |
| **Tyres** | Synthetic rubber and carbon black come from crude |
| Chemicals, plastics, logistics | Input and freight costs |
| **Helped** | |
| **Upstream producers** | Higher realisations — partly clawed back by windfall taxes, as in 2022 |
| IT exporters (indirectly) | A weaker rupee lifts rupee revenue |

Falling crude reverses the table: OMCs, paints and aviation were classic
beneficiaries of the 2014–16 collapse. **For an India trader:** a sustained
Brent uptrend with a weakening rupee is the combination in which foreign
investors tend to sell Indian equities — be more selective, keep the book
smaller, and steer away from the oil consumers however good their charts look.

## 5. Gold — fear, real rates and the dollar

Gold pays no interest and has no earnings. Its price is set by what holding
it costs and what it insures against:

- **Real yields.** Holding gold means giving up the real yield on a safe
  bond: real yields up, gold usually down. The nominal 10-year is the stored
  proxy (real/TIPS yields are not stored).
- **The dollar.** Gold is priced in dollars; a stronger dollar tends to push
  its dollar price down.
- **Fear.** A hedge against the system — though in the acute phase of a crash
  it is often *sold* for cash: from March to late October 2008 gold fell
  about 27%.
- **Official buying.** Central banks are large, price-insensitive buyers who
  can override the rest for years.

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
2012) to about 3.0% on the Fed's "taper" talk, and gold fell from about
$1,675 to $1,200 over the year (about −28%); from its August 2011 high near
$1,889 to its December 2015 low near $1,051 it lost about 44%. In 2022 the
10-year went from about 1.6% to over 4%, the dollar index hit about 114 on 27
September, and gold fell about 20% from March to about $1,631 on 3 November.

**When it broke — be honest about this.** From late 2022 gold rose while the
10-year sat near or above 4% (peaking near 5.0% in October 2023). Gold went
from about $1,630 to about **$2,640 at the end of 2024**, rose about 60% more
in 2025 (to about $4,340), and the stored series peaked near **$5,300 in late
January 2026**. The widely cited reason is **central-bank buying** —
emerging-market central banks diversifying reserves away from the dollar
after Russia's reserves were frozen in 2022 — plus geopolitical demand. (In
2025 the textbook drivers lined up too: the dollar index fell about 10%.)
The lesson: **a relationship that held for a decade can stop working for
years** — use it as a question, not a model.

### Gold in India

In India gold is a **cultural and household savings asset** — weddings,
festivals (Akshaya Tritiya, Dhanteras), rural savings. India is one of the
two largest consumers and imports almost all of it, so:

- **The rupee price matters.** In 2022 dollar gold ended flat while the
  rupee fell about 11%; the stored Indian gold series rose about 13%.
- **Import duty** is a policy lever, raised to curb imports when the current
  account is strained and cut to curb smuggling (the July 2024 Budget cut it
  sharply). Duty changes move jewellers, gold-loan companies and gold ETFs.

**For a trader:** gold up with stocks down is risk-off; gold up with stocks
up (2024–25) is more likely a reserve or currency story. The tradeable effect
is in gold miners (US) or jewellers and gold financiers (India) — whose own
charts decide.

## 6. Copper — "Dr. Copper" and the copper/gold ratio

Copper goes into wiring, buildings, motors and grids, so its price is a rough
real-time read on **industrial demand** — "Dr. Copper, the metal with a PhD
in economics". China uses about half the world's copper, and electrification
(grids, EVs, data centres) has added a structural demand story since 2020.

In 2008 copper fell about **69%** from July to December; from the March 2020
low to May 2021 it rose about **125%**, and materials (**XLB**) about 127%.

Divide the growth metal by the fear metal and you get one line for **growth
versus fear**. For most of 2005–2022 the **copper/gold ratio** moved with the
10-year yield, because both follow growth expectations.

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
- **2020–21:** from April 2020 to October 2021 the ratio about doubled and
  the 10-year rose from about 0.5% to 1.7% — the reflation trade.
- **2022–25, broken:** the ratio fell about 55% from February 2022 to
  October 2025, yet copper itself made **records** (about $5.60/lb at the
  end of 2025, about $6.80 in September 2026). Gold simply rose faster. When
  one half of a ratio is driven by something else, it stops meaning "growth".

**Materials stocks.** XLB is heavy in chemicals, whose costs *rise* with
oil, so it is not a pure copper play — for metals use the industry groups on
the Sectors page. Metal stocks often top while the metal is still rising.

**For a trader:** rising copper with materials and metals leading is the
cyclical-recovery backdrop in which industrials, materials and small caps do
well. Copper collapsing with yields falling is a growth scare: favour
defensives and cut size.

## 7. What a trader does with this

1. **Sector context.** A commodity trending for months (not days) tells you
   which sector moves are likely to persist. The Sectors page and the stocks'
   own charts still pick the trades.
2. **Not standalone signals.** A one-day oil jump is noise for a swing
   trader; the stock-level effect is already in the stock's price.
3. **Know your exposure.** Five positions in oil consumers with Brent breaking
   out is one big bet, not five small ones.
4. **Breaks are questions.** When a textbook link stops working (gold vs
   yields since 2023), find out why before trusting it again.

## 8. What the evidence says

- **Robust:** oil drives energy-sector earnings and, over months, energy-stock
  returns; oil shocks lift headline inflation quickly; India's current account
  and rupee are sensitive to crude; copper is pro-cyclical.
- **Robust but unstable:** gold's inverse link to real yields and the dollar
  held for long stretches, then broke from 2022–23 as official buying took
  over.
- **Folklore-leaning:** "Dr. Copper predicts recessions" — copper falls *in*
  recessions but also gives false alarms (China slowdowns that stayed local)
  and moves on supply news such as mine strikes. The copper/gold fit to
  yields describes; it does not forecast.
- **Lags:** oil to CPI is quick (a month or two); to consumer spending and
  policy slower, depending on how long the move lasts. Stocks usually move
  *before* the commodity data confirms.
- **Measurement:** stored oil, gold and copper are front-month futures that
  roll and can misbehave near expiry — use them for trend, not exact levels.

## 9. Checklist

- Oil: trending over 1–3 months? New high or low for the year? Do the
  energy groups on the Sectors page agree?
- India: Brent and USD/INR together — both rising is the warning; check your
  OMC, paint, aviation and tyre exposure.
- Gold: rising with stocks falling (fear) or rising (reserves/currency)? In
  line with the 10-year and the dollar, or breaking from them?
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
