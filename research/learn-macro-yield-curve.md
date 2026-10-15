# Bond yields and the yield curve — the discount rate for everything

Learning material: bond yields and prices, the shape of the curve,
inversions and their record as a recession signal (good, slow, not
infallible), the re-steepening that follows, real yields, and why the speed
of a yield move matters. Companion to [the rates guide](learn-macro-rates.md)
and [the business cycle guide](learn-macro-cycle.md).

**Where this shows in the app.** The macro strip on Markets → Breadth (built
by `scripts/swing_screener/marketdata/macro.py`) shows the US 10-year and
5-year yields. Each tile shows the change over 1 day and over 1 month, in basis
points. The India strip shows the US 10-year too. The charts below use the
yields stored in the app. "The curve" in this guide means the **10-year yield
minus the 3-month T-bill yield**.

---

## 1. What a bond yield is

A bond is a loan with fixed payments. You lend the US Treasury $1,000 for ten
years, collect a fixed coupon each year, and get the $1,000 back at the end.
The **yield** is the annual return you lock in if you buy at today's price.
The payments never change, so only the **price** can move. Say new bonds pay
5% and an old one pays 2%. Nobody will pay full price for the old one, so its
price falls until it too yields about 5%. Hence the rule:

**Bond prices and yields move in opposite directions.** The longer the bond,
the bigger the price swing for the same change in yield (its *duration*):

| | Maturity | Roughly, price change for a 1-point yield rise |
|---|---|---|
| 3-month T-bill | 0.25 years | about −0.25% |
| 7–10y Treasuries (IEF) | ~8 years | about −7 to −8% |
| 20y+ Treasuries (TLT) | ~17 years | about −15 to −17% |

```series
title: Price and yield move opposite — long Treasuries and the 10-year, 2020–2024
from: 2020-01-01
to: 2024-12-31
line: us:BONDS_LONG | 20y+ Treasuries (TLT)
line: us:US10Y | US 10-year yield (%) | right
mark: 2020-08-04 | TLT peak
caption: As the 10-year rose from about 0.5% in 2020 to about 5% in October 2023, TLT lost about 48% of its price. "Safe" bonds had a worse drawdown than the S&P 500.
```

2022 was the worst year for bonds in generations. **IEF (7–10 year) fell about
14% and TLT (20 year+) about 29%** — in a year the S&P 500 fell 20%. The
classic "60/40" portfolio (60% stocks, 40% bonds) lost on both parts. That is
duration risk. It is the same arithmetic that hits long-duration growth stocks
([the rates guide](learn-macro-rates.md), §3).

## 2. The curve and its shape

The **yield curve** shows, for a single day, the yield on each maturity: 3
months, 2, 5, 10 and 30 years. The two ends tell you different things:

- **The short end follows the policy rate.** A 3-month bill is a bet on where
  the Fed's rate will be over the next three months. It moves when the Fed
  moves, or when the market becomes sure the Fed will. The 2-year (not stored
  in the app) is the market's best single guess at Fed policy over the next
  two years. The **5-year**, which the app does store, looks a little further
  out.
- **The long end reflects what the market expects over the long run**:
  growth plus inflation, plus a **term premium**. Lenders want that extra pay
  for locking money up for a decade without knowing what inflation, government
  deficits and the supply of new bonds will be.

| Shape | What it means | Typical when |
|---|---|---|
| **Normal / upward** (long > short) | Money tied up longer earns more | Most of the time; early and middle of an expansion |
| **Steep** | Policy loose now; growth and inflation expected later | Right after recessions (2003, 2009–10) |
| **Flat** | Policy tight compared with the long-run outlook | Late in hiking cycles |
| **Inverted** (short > long) | Market expects rates to *fall* — usually because growth will weaken | Late in the cycle, before most US recessions |

In the history stored in the app, the 10-year peaked near 15.8% in September
1981. Its low was near 0.5% in March 2020.

## 3. Steepening and flattening — bull and bear

The curve **steepens** when the gap between long and short yields widens, and
**flattens** when it narrows. Each move is named by **which end moves** and
**which way**. "Bull" means yields are falling (so bond prices are rising);
"bear" means yields are rising.

| Move | What happens | Usual story | Stocks |
|---|---|---|---|
| **Bull steepener** | Short yields fall faster than long | The central bank is cutting — often because growth is breaking down | Dangerous if these are cuts into a recession (2001, 2007) |
| **Bear steepener** | Long yields rise faster than short | Optimism about growth or inflation — or worry about deficits and the term premium | Good if it is growth; bad if investors are refusing to buy bonds |
| **Bear flattener** | Short yields rise faster than long | The central bank is hiking | Usually fine early, harder late |
| **Bull flattener** | Long yields fall faster than short | Fear for growth; money moving to safe assets | Defensive stocks lead |

So a steepening is *good* news when long yields rise because growth is
strong. It is *bad* news when short yields collapse because of emergency cuts.

## 4. Inversion as a recession signal

An inverted curve says: **the market expects short rates to be lower in the
future than they are now.** Usually that is because policy is tight enough
to slow the economy, and the market expects cuts once it does. It also hurts
banks. They borrow short-term and lend long-term, so when short rates are
above long ones, lending pays less and banks lend less.

```series
title: The 10-year minus 3-month spread and the S&P 500, with US recessions
from: 1965-01-01
tf: M
line: us:SP500_PRICE_LONG | S&P 500 | log
line: us:US10Y - us:CASH_YIELD | 10y − 3m spread (points) | pane2 zero
band: 1969-12-01 1970-11-30 | Recession
band: 1973-11-01 1975-03-31 | Recession
band: 1980-01-01 1980-07-31 | Recession
band: 1981-07-01 1982-11-30 | Recession
band: 1990-07-01 1991-03-31 | Recession
band: 2001-03-01 2001-11-30 | Recession
band: 2007-12-01 2009-06-30 | Recession
band: 2020-02-01 2020-04-30 | Recession
caption: In the lower pane, below the dashed zero line is an inversion. Every shaded recession since 1969 came after one; the lead time ranged from a few months to well over a year. The 2022–24 inversion, the deepest since the early 1980s, has not (as of this data) been followed by one.
```

The record, using month-end values of the 10-year minus 3-month spread stored
in the app (approximate):

| Inversion began | Recession began (NBER) | Lead time |
|---|---|---|
| Dec 1968 | Dec 1969 | about 12 months |
| June 1973 | Nov 1973 | about 5 months |
| Nov 1978 | Jan 1980 | about 14 months |
| Oct 1980 | July 1981 | about 9 months |
| May 1989 (barely) | July 1990 | about 14 months |
| Aug 2000 | March 2001 | about 7 months |
| Aug 2006 | Dec 2007 | about 16 months |
| May 2019 | Feb 2020 | about 9 months — and the trigger was a pandemic |
| Nov 2022 | none so far | — |

Also note **1966**. The curve inverted (Sept–Dec 1966), and the US got a
slowdown but no recession. It is the classic early false alarm.

### What that record really says

- **Good, slow, and a small sample** (about eight recessions). A lead of 5–16
  months is useless for timing a swing trade. And stocks often *rose* after
  the inversion: the S&P 500 peaked in October 2007, fourteen months after it.
- **The 2022–24 inversion has (so far) not produced a US recession.** The
  spread went negative in November 2022. It reached about −1.7 points in May
  2023, the deepest since the early 1980s. It stayed inverted until
  mid-December 2024. The S&P 500 *rose* about 47% across it. Explanations
  offered:
  - borrowers had locked in low rates in 2020–21, so hikes took effect slowly;
  - pandemic savings and government spending;
  - a term premium held down by years of QE.

  Maybe the signal was early; maybe it failed. **Be honest about which you
  assume.**

## 5. The re-steepening often matters more

The inversion is the warning. The **re-steepening** — the spread climbing back
above zero — has often come close to the trouble itself. That is because it
is usually a *bull steepener*: the central bank starts cutting because
something has broken, and short yields collapse.

```series
title: 2006–2009 — the curve re-steepened just before the bear market
from: 2005-06-01
to: 2009-12-31
line: us:SP500_PRICE_LONG | S&P 500 | log
line: us:US10Y - us:CASH_YIELD | 10y − 3m spread (points) | pane2 zero
band: 2007-12-01 2009-06-30 | Recession
mark: 2007-10-09 | S&P 500 peak
caption: Inverted from August 2006 to mid-2007 while stocks kept rising. The spread was back above zero by the end of June 2007; the S&P 500 peaked in October 2007, and the spread widened past 2 points as the Fed cut and stocks fell more than half.
```

2000–01 was similar: the curve re-steepened as the Fed began cutting in
January 2001, and a long bear market followed. It did **not** hold in
2024–25. The curve re-steepened from December 2024, and stocks kept rising
after a sharp drop in spring 2025. So treat re-steepening as a sign that
**trouble may now be close**, not as a sell signal. And ask whether it is a
bull steepener (cuts into weakness) or a bear one.

```series
title: The 2022–24 inversion and the S&P 500
from: 2021-06-01
line: us:SP500_PRICE_LONG | S&P 500 | log
line: us:US10Y - us:CASH_YIELD | 10y − 3m spread (points) | pane2 zero
band: 2022-11-07 2024-12-13 | Curve inverted
caption: About two years inverted — longer without a break than any earlier episode in the stored data since 1962 — with the S&P 500 up about 47% across it. In the latest stored data (October 2026) the spread is positive at about +1.2 points, with the 10-year near 5.2%.
```

## 6. Real yields — and gold and growth stocks

A **real yield** is the nominal yield minus expected inflation. A 10-year
paying 4.5% when inflation is expected at 2.5% gives a real yield of about 2%.
The market's own measure is the yield on inflation-protected Treasuries
(TIPS — bonds whose payments rise with inflation). FRED, the St. Louis Fed's
free data site, publishes it. **It is not stored in this app.** Read it on
FRED, or estimate it from the 10-year and the inflation expectations discussed
in [the inflation guide](learn-macro-inflation.md).

Real yields matter more than nominal ones for two groups:

- **Long-duration growth stocks.** Their value rests on cash flows far in the
  future, after inflation, so those are discounted at a real rate. The 10-year
  TIPS yield went from roughly −1% at the end of 2021 to about +2.5% by
  October 2023, one of the fastest rises on record. That is a large part of
  why the Nasdaq 100 fell about 35% from its late-2021 high to its late-2022
  low.
- **Gold** pays no income. So what you give up by holding it is the real
  yield you could have earned instead. When real yields rose sharply in 2013,
  gold fell about a third from late 2012 to the end of 2013. **But the link is
  not a law.** From 2023 to the end of 2025 gold rose about 135% while real
  yields stayed high. The buying came from central banks moving some of their
  reserves out of the dollar. A relationship that holds for a decade can break
  when conditions change. See [the commodities guide](learn-macro-commodities.md).

```series
title: Gold and the 10-year yield, 2011–today
from: 2011-01-01
line: us:GOLD_FUT | Gold ($/oz) | log
line: us:US10Y | US 10-year yield (%) | right
band: 2013-05-01 2013-12-31 | Taper tantrum
caption: In 2013 rising yields came with a falling gold price, the textbook relationship. From 2023 gold more than doubled with the 10-year mostly between about 3.5% and 5% — the old link gave way to central-bank buying.
```

## 7. The 10-year as the discount rate for everything

The US 10-year is the benchmark that prices around the world are set from:

- **US mortgages** are priced from it. (A 30-year mortgage follows the 10-year
  because most 30-year loans are repaid early.)
- **Stock valuations** discount future profits at the 10-year plus a risk
  premium ([the rates guide](learn-macro-rates.md), §3).
- **Company borrowing costs** are the Treasury yield plus a credit spread
  ([the liquidity and credit guide](learn-macro-liquidity-credit.md)).
- **Investors everywhere**, India included, compare what they can earn with
  the US 10-year, treated as risk-free.

When it moves a full point, the price of everything set from it changes. That
is why it sits on both markets' macro strips.

## 8. Speed matters more than level

Stocks can live with almost any **level** of yields if it arrives slowly and
growth comes with it. The S&P 500 rose through the 2004–06 hikes. The 1990s
bull market lived with a 10-year between about 4% and 9%. What hurts is a
**fast** move. Valuations do not have time to adjust, and investors who
borrowed to hold must sell:

| Episode | 10-year move | S&P 500 |
|---|---|---|
| Taper tantrum, May–Sept 2013 | about 1.6% → 3.0% in four months | Shallow dip (about 6%) — growth was improving |
| Jan–Feb 2018 | about 2.4% → 2.9% in seven weeks | About −10% in two weeks, as bets on calm markets blew up |
| 2022 | about 1.6% → 4.2% by October | Bear market, about −25% peak to trough |
| July–Oct 2023 | about 3.7% → 5.0% in three months | About −10%, until yields turned |

A working rule of thumb, not a tested rule: **a 10-year rise of half a point
or more in a month** (50bp or more on the macro strip's 1M change) is a cue to
tighten stops on high-P/E stocks.

## 9. India: the G-sec

India's benchmark is the **10-year government security (G-sec)**. It is not
stored in this app, so these points are text only:

- **It tracks the repo rate plus a spread.** It typically sits somewhat above
  the policy rate. It moves with expectations for RBI policy, for inflation
  and for the government's borrowing plan. That plan is announced with the
  Union Budget; a bigger fiscal deficit means more bonds for buyers to absorb.
- **It follows US yields, at a distance.** A jump in US yields pulls foreign
  money out of India and weakens the rupee. The G-sec yield then rises, unless
  the RBI steps in to hold it down. The link is loose because domestic banks,
  insurers and the RBI hold most G-secs.
- **Roughly:** the 10-year G-sec traded around 6% in 2020–21. It rose above
  7% in 2022 as the RBI hiked, and eased back toward the mid-6s as the RBI cut
  in 2025. Indian government bonds entered JPMorgan's emerging-market bond
  index from June 2024, which brought in a new source of foreign buying.
- **What reacts:** banks (they hold a lot of G-secs, so they book gains on
  them when yields fall and losses when yields rise), NBFCs and housing
  finance, real estate.

The app stores no Indian yield curve. So the practical stand-in here is the
**US 10-year and USD/INR on the India macro strip**. When both are rising
fast, foreign selling in India is likely ([the currencies guide](learn-macro-currencies.md)).

## 10. What a trader does with it

- **Check how fast the 10-year is moving, every week.** If it rises half a
  point or more in a month: favour short-duration leaders (energy, financials,
  value), tighten stops on breakouts in high-P/E stocks, and be pickier with
  new entries.
- **Treat inversion as background, not a trigger.** It raises the odds of a
  recession sometime in the next one to two years. It says nothing about next
  month. Keep trading the trend, and let breadth and price lead.
- **Watch for a bull steepener** — short yields collapsing on cuts into a
  weakening economy, with breadth and credit getting worse (2001, 2008). Then
  cut exposure.
- **Know what kind of steepener it is.** Long yields rising because growth is
  strong: fine for cyclical stocks and banks. Long yields rising on fear of
  deficits or inflation, with stocks falling: valuations are being squeezed,
  so reduce exposure to growth stocks.
- **Bonds do not always offset stock losses.** When inflation is the problem,
  stocks and bonds fall together (2022).
- **India:** watch the US 10-year and the rupee. A fast US move tends to hit
  large caps that FIIs own heavily, and rate-sensitive financials, first.

## 11. What the evidence says

- **Robust:** the inverted US yield curve has preceded every US recession
  since the late 1960s, with one early false positive (1966). The New York
  Fed's recession-probability model is built on the 10y−3m spread for this
  reason (Estrella and Mishkin, 1998).
- **Weak as timing:** leads of roughly 5–16 months, and stocks frequently
  rose after inversion. As a sell signal it has cost more than it saved.
- **Uncertain now:** the 2022–24 inversion was deep and two years long. As of
  this data it had not been followed by a US recession. Either it was early,
  or lasting changes in the economy weakened it: locked-in low borrowing
  costs, government spending, and a term premium kept artificially low by
  years of QE. Nobody knows yet.
- **Small sample:** eight or so episodes. Any statistic built on them has a
  wide margin of error. Treat precise "x months later" claims as folklore.
- **Context-dependent:** gold vs real yields, and stocks vs bonds, are strong
  relationships while conditions stay the same. They can break when
  conditions change.
- **Not universal:** the record is a US result; India's curve, shaped by RBI
  liquidity and government borrowing, has no comparable track record.

## 12. Checklist

- [ ] US 10-year: level and 1-month change (macro strip) — fast or slow?
- [ ] US 5-year: is the market pricing more hikes or more cuts?
- [ ] 10y−3m spread: inverted, flat, or re-steepening — and bull or bear?
- [ ] Leadership consistent with the yield trend? Bonds hedging, or falling too?
- [ ] India: the US 10-year and USD/INR; any change in RBI liquidity?

## Further reading

- FRED, Federal Reserve Bank of St. Louis (fred.stlouisfed.org) — Treasury
  yields, the 10y−3m and 10y−2y spreads (T10Y3M, T10Y2Y), 10-year TIPS yields,
  and NBER recession shading.
- Federal Reserve Bank of New York — "The Yield Curve as a Leading
  Indicator", its recession-probability model.
- Arturo Estrella and Frederic Mishkin, "Predicting U.S. Recessions:
  Financial Variables as Leading Indicators", *Review of Economics and
  Statistics*, 1998.
- NBER Business Cycle Dating Committee (nber.org) — the official US
  recession dates.
- Reserve Bank of India (rbi.org.in) — government securities market data and
  the Monetary Policy Report.
