# Bond yields and the yield curve — the discount rate for everything

**In short**

- When bond yields rise, bond prices fall. The longer the bond, the bigger the fall: long Treasuries lost about 29% in 2022.
- Bond yields set what everyone pays to borrow and what future profits are worth today, so they move stocks. The yield curve compares short and long yields; when the 3-month yield rises above the 10-year, the curve is inverted.
- An inversion has come before every US recession since the late 1960s, but with a lead of months to more than a year. The 2022–24 inversion has not (yet) been followed by one.
- The re-steepening after an inversion, often driven by emergency rate cuts, has tended to come closer to the trouble.
- For stocks, a fast rise in the 10-year yield hurts more than a high level reached slowly.

This guide starts from the basics: what a bond yield is, and why it matters to the economy and to stocks. It then covers the shape of the yield curve. It covers inversions and their record as a recession signal: good, slow and not infallible. It then turns to the re-steepening that follows, to real yields, and to why the speed of a yield move matters. It is a companion to [the rates guide](learn-macro-rates.md) and [the business cycle guide](learn-macro-cycle.md).

"The curve" in this guide means the **10-year Treasury yield minus the 3-month T-bill yield**.

**Key words**

| Word | Meaning |
|---|---|
| Bond | A loan to a government or company, with fixed payments and a date when the money comes back |
| Maturity | How long until the loan is repaid: 3 months, 2 years, 10 years, 30 years |
| Bill / note / bond | US government debt by maturity: bills up to a year, notes up to ten years, bonds beyond |
| Yield | The yearly return a buyer locks in at today's price |
| Policy rate | The overnight rate the central bank sets: the Fed funds rate in the US, the repo rate in India |
| Spread | One yield minus another, in percentage points. "The spread" here is the 10-year minus the 3-month |
| Basis point (bp) | One hundredth of a percentage point: 50bp is half a point |
| Inverted | Short-term yields above long-term ones; the spread below zero |

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

2022 was the worst year for bonds in generations:

| 2022 | Change |
|---|---|
| 7–10 year Treasuries (IEF) | about −14% |
| 20 year+ Treasuries (TLT) | about −29% |
| S&P 500 | about −20% |

The classic "60/40" portfolio holds 60% in stocks and the rest in bonds. In
2022 it lost on both parts. That is duration risk. It is the same arithmetic that hits long-duration growth stocks
([the rates guide](learn-macro-rates.md), §3).

## 2. Why yields matter to the economy and to stocks

Bond yields can look like a world of their own. They are not. The US government's borrowing rate is the starting point for almost every other price of money, and money is what both companies and investors run on. Four links connect yields to stocks.

**1. They set what everyone else pays to borrow.** A bank prices a mortgage or a company loan from the government's yield, plus a margin for risk. US 30-year mortgages follow the 10-year yield, because most are repaid early. When the 10-year rises a point, borrowing gets dearer for households and companies at once. They spend and invest less, and profits grow more slowly.

**2. Bonds compete with stocks for money.** Suppose a stock index pays 1.5% a year in dividends. When a safe government bill pays 0.1%, as in 2021, stocks look generous. When the bill pays 5%, as in 2023, a saver can earn that without any risk. Some money leaves stocks for bonds, and stocks need faster profit growth to stay attractive.

**3. They set what future profits are worth today.** A stock's price is what investors will pay now for profits that arrive over many years. A dollar promised later is worth less than a dollar today, and how much less depends on interest rates:

| $100 of profit, ten years away | Worth today |
|---|---|
| Discounted at 2% a year | about $82 |
| Discounted at 5% a year | about $61 |

The same future profit is worth about a quarter less today when rates rise from 2% to 5%. Companies whose profits lie furthest in the future, young growth companies above all, feel this most. That is why rising yields hurt high-valuation stocks first ([the rates guide](learn-macro-rates.md), §3).

**4. They carry a message about the future.** Bond investors are betting on growth, inflation and central bank policy. The yield on each maturity is their collective forecast, with real money behind it. Long yields falling below short ones, as section 5 explains, is the market saying it expects the economy to weaken.

The US 10-year matters beyond America too. Investors everywhere, India included, compare what they can earn at home with the US 10-year, treated as the world's risk-free rate. When it moves a full point, the price of almost everything set from it changes.

## 3. The curve and its shape

Start with five real days. Each row is the US Treasury curve on that date, read left to right from the shortest loan to the longest:

| Date | 3-month | 2-year | 5-year | 10-year | 30-year | Shape |
|---|---|---|---|---|---|---|
| 26 Feb 2010 | 0.13% | 0.81% | 2.28% | 3.60% | 4.55% | Steep |
| 30 Jun 2014 | 0.04% | 0.47% | 1.62% | 2.52% | 3.34% | Normal, upward |
| 31 Dec 2018 | 2.45% | 2.48% | 2.51% | 2.69% | 3.02% | Flat |
| 28 Aug 2019 | 1.99% | 1.50% | 1.37% | 1.47% | 1.94% | U-shaped |
| 31 Jul 2023 | 5.55% | 4.88% | 4.18% | 3.96% | 4.02% | Inverted |

That is all a **yield curve** is: the yield on each maturity, for a single day. Plot the row as a line and you get its shape. In 2010 the line climbs steeply. By the end of 2018 it is almost level. In mid-2023 it slopes *down*: lending to the government for three months paid more than lending for ten years.

### What each point tells you

| Point | What drives it | What it tells you |
|---|---|---|
| 3-month bill | The policy rate, almost one for one | Where the central bank's rate is now |
| 2-year | Expected policy over the next two years | The market's best single guess at the coming cuts or hikes |
| 5-year | Policy over the medium term, plus some inflation risk | Where the rate cycle is expected to settle |
| 10-year | Long-run growth and inflation, plus a term premium | The benchmark for mortgages, company borrowing and stock valuations |
| 30-year | The same long-run forces, with the most term premium | How much investors want for very long inflation and deficit risk |

**The short end follows the policy rate.** In July 2023 the Fed's rate sat between 5.25% and 5.5%. The 3-month bill yielded 5.55%, just above it. A 3-month bill is a bet on where that rate will be over the next three months. It moves when the Fed moves, or when the market becomes sure the Fed will.

**The 2-year moves first.** It reacts to what the market expects the central bank to do over the next two years. In 2023 it stood well below the 3-month bill: the market was already pricing cuts. Watch it when a central bank meeting or an inflation report changes the outlook.

**The long end is expectations plus a premium.** A 10-year yield is roughly the average short rate the market expects over the next ten years, plus a **term premium**. That premium is extra pay for locking money up for a decade without knowing what inflation, deficits and the supply of new bonds will do.

A worked example. Suppose investors expect the policy rate to average 3.5% over the next decade. They also want 0.75 points of extra pay for the risk. The 10-year then trades near 4.25%. If inflation fears grow, the premium rises and the 10-year climbs, even with no change in expected policy.

The premium is not fixed, and it can turn negative. In the late 2010s, Fed staff estimates put it below zero for long stretches. Central banks were buying bonds, and investors paid up for the safety of long Treasuries. Its rise since 2022 is part of why long yields stayed high even as cuts came into view.

### Why the curve usually slopes up

Lending for longer carries more risk: more time for inflation to surprise and for prices to swing. So in normal times investors demand a higher yield for longer loans, and the curve slopes up. Since 1982, the 10-year yield has topped the bill yield on about 89% of trading days. A curve that slopes the other way is the exception, which is why it gets so much attention.

### The shapes, and what they usually mean

| Shape | What it looks like | What it usually means | Example |
|---|---|---|---|
| **Normal / upward** | Long yields above short, rising steadily | Money tied up longer earns more | June 2014 |
| **Steep** | A wide gap from short to long | Policy loose now; growth and inflation expected later | Right after recessions: 2003, 2010 |
| **Flat** | Almost the same yield at every maturity | Policy tight compared with the long-run outlook | Late in hiking cycles: end of 2018 |
| **U-shaped** | Short and long ends high, the middle low | The market expects cuts soon, but still wants a premium for the long run | August 2019, December 2000 |
| **Inverted** | Short yields above long | The market expects rates to fall, usually because growth will weaken | Mid-2023; before most US recessions |

```series
title: The short end and the long end, 1982 to today
from: 1982-01-01
line: us:US_TBILL_3M | 3-month bill (%)
line: us:US_UST_2Y | 2-year (%)
line: us:US10Y | 10-year (%)
caption: The 3-month bill tracks the policy rate; the 10-year moves more slowly. Where the 3-month line sits above the 10-year, the curve is inverted.
```

### Two ways to measure the slope

Traders boil the curve down to one number, a spread between a long and a short yield. The two common ones can tell different stories:

| Date | 10-year minus 3-month | 10-year minus 2-year |
|---|---|---|
| 29 Dec 2000 | −0.78 points | 0.00 points |
| 28 Aug 2019 | −0.52 points | −0.03 points |
| 31 Jul 2023 | −1.59 points | −0.92 points |

The 10-year minus 3-month spread compares the long rate with the policy rate itself. The 10-year minus 2-year spread compares it with where policy is *expected* to go. In 2000 and 2019 the first was clearly inverted while the second was only flat. This guide uses the 10-year minus 3-month spread: it has the longer record as a recession signal.

### The extremes

The slope has swung widely. The 10-year minus 3-month spread peaked at about 5.2 points in August 1982, as rates came down from their peak. It hit its deepest inversion, about −1.9 points, in May 2023. The 10-year yield itself peaked near 15.8% in September 1981 and bottomed near 0.5% in March 2020.

### India's curve today

India's government curve on 15 October 2026, with the repo rate at 5.5%:

| 91-day bill | 182-day bill | 364-day bill | 5-year | 10-year | 30-year |
|---|---|---|---|---|---|
| 5.73% | 6.29% | 6.49% | 7.17% | 7.39% | 7.78% |

It slopes up the whole way: a normal curve. The 91-day bill sits close to the repo rate, just as the US 3-month bill tracks the Fed's rate. Section 9 covers the G-sec in more detail.

## 4. Steepening and flattening — bull and bear

The curve does not sit still; its two ends move at different speeds. 2022 shows how.

| Date | 3-month | 10-year | Spread (10-year minus 3-month) |
|---|---|---|---|
| 31 Dec 2021 | 0.06% | 1.51% | +1.45 points |
| 30 Jun 2022 | 1.72% | 2.97% | +1.25 points |
| 31 Oct 2022 | 4.22% | 4.08% | −0.14 points |

The Fed raised its rate fast through 2022 to fight inflation. The 3-month bill, tied to that rate, jumped about four points. The 10-year rose too, but by much less. So the gap between them shrank, and by October it had turned negative.

When the gap narrows like this, the curve **flattens**. When it widens, the curve **steepens**. Traders name each move by which end does most of the moving, and which way.

The names borrow from bond traders' slang. A **bull** market in bonds means bond prices are rising, which means yields are *falling*. A **bear** market in bonds means yields are rising. So 2022 was a **bear flattener**: yields rising, the short end fastest.

| Move | What happens | Usual story | Stocks |
|---|---|---|---|
| **Bull steepener** | Short yields fall faster than long | The central bank is cutting — often because growth is breaking down | Dangerous if these are cuts into a recession (2001, 2007) |
| **Bear steepener** | Long yields rise faster than short | Optimism about growth or inflation — or worry about deficits and the term premium | Good if it is growth; bad if investors are refusing to buy bonds |
| **Bear flattener** | Short yields rise faster than long | The central bank is hiking | Usually fine early, harder late |
| **Bull flattener** | Long yields fall faster than short | Fear for growth; money moving to safe assets | Defensive stocks lead |

So a steepening is *good* news when long yields rise because growth is
strong. It is *bad* news when short yields collapse because of emergency cuts.

## 5. Inversion as a recession signal

**What inverts?** Normally a 10-year loan to the government pays more than a 3-month one. The curve is **inverted** when that flips: the 3-month yield rises *above* the 10-year. The spread, 10-year minus 3-month, drops below zero.

| 31 July 2023 | Yield |
|---|---|
| 3-month bill | 5.55% |
| 10-year note | 3.96% |
| Spread | −1.59 points: inverted |

**Why would anyone lend for ten years at less than they could get for three months?** Because they expect short rates to fall. A buyer of the 10-year locks in 3.96% for a decade. If the Fed cuts its rate to 3% within a year or two, rolling over 3-month bills will soon pay far less than that. Buying the long bond now, before the cuts, is the better deal. Enough buyers thinking this way push long yields down below short ones.

**And why would the Fed cut?** Usually because its own hikes are slowing the economy. Inversions tend to follow the same chain:

1. Inflation rises, and the central bank raises its rate to cool it. Short yields climb with it.
2. Bond investors start to believe the higher rate will slow the economy, so they expect cuts later. Long yields stop rising, or fall.
3. Short yields end up above long ones: the curve inverts.
4. Banks feel it directly. They borrow short-term (deposits) and lend long-term (loans). When short rates top long ones, lending earns less, so banks lend less. Less credit slows the economy further.

So an inversion is the bond market betting that the economy will weaken enough to force rate cuts. It is not a cause of recession by itself. It is a forecast, made with real money, that has often been right.

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
caption: The lower pane is the spread, 10-year minus 3-month. Below the dashed zero line, the curve is inverted. Every shaded recession since 1969 came after one; the lead time ranged from a few months to well over a year. The 2022–24 inversion, the deepest since the early 1980s, has not (as of this data) been followed by one.
```

The record, using month-end values of the 10-year minus 3-month spread
(approximate):

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

## 6. The re-steepening often matters more

An inversion ends when the spread climbs back above zero: the curve **re-steepens**. How it gets there matters.

Usually it is not long yields rising. It is short yields *falling*, because the central bank has started cutting. And it cuts fast when something has broken: jobs are being lost, credit is freezing, or a market is in trouble. The 3-month bill drops with each cut, the spread turns positive, and that is often when the slowdown the inversion warned of finally arrives.

So the inversion is the early warning, and the re-steepening has often come close to the trouble itself. In the terms of section 4, it is usually a *bull steepener*: yields falling, the short end fastest.

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
caption: About two years inverted — longer without a break than any earlier episode since 1962 — with the S&P 500 up about 47% across it. In mid-October 2026 the spread is positive at about +1.2 points, with the 10-year near 5.2%.
```

## 7. Real yields — and gold and growth stocks

A bond's yield is paid in money, but inflation eats into what that money buys. What a lender really earns is the yield *after* inflation, the **real yield**. Take a 10-year paying 4.5% when inflation is expected at 2.5%. Its real yield is about 2%: the nominal yield minus expected inflation.

The market's
own measure is the yield on inflation-protected Treasuries (TIPS — bonds whose
payments rise with inflation). FRED, the St. Louis Fed's free data site,
publishes it. You can also estimate it from the 10-year and the inflation
expectations discussed in [the inflation guide](learn-macro-inflation.md).

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

## 8. Speed matters more than level

Why should speed matter? When yields rise slowly, companies have time to grow their profits, and investors have time to adjust what they will pay. When yields jump, the discounting from section 2 hits all at once, before profits can catch up. Investors who borrowed to buy are forced to sell.

Stocks can live with almost any **level** of yields if it arrives slowly and
growth comes with it. The S&P 500 rose through the 2004–06 hikes. In the 1990s
bull market the long yield ranged from about 4% to 9%. What hurts is a
**fast** move. Valuations do not have time to adjust, and investors who
borrowed to hold must sell:

| Episode | 10-year move | S&P 500 |
|---|---|---|
| Taper tantrum, May–Sept 2013 | about 1.6% → 3.0% in four months | Shallow dip (about 6%) — growth was improving |
| Jan–Feb 2018 | about 2.4% → 2.9% in seven weeks | About −10% in two weeks, as bets on calm markets blew up |
| 2022 | about 1.6% → 4.2% by October | Bear market, about −25% peak to trough |
| July–Oct 2023 | about 3.7% → 5.0% in three months | About −10%, until yields turned |

Here is a working rule of thumb, not a tested rule. **A 10-year rise of half a
point (50bp) or more in a month** is a cue to tighten stops on high-P/E stocks.

## 9. India: the G-sec

India's government also borrows by selling bonds, called **government securities (G-secs)**. The RBI's policy rate is the **repo rate**: the rate at which it lends overnight to banks, India's version of the Fed funds rate. The benchmark long yield is the **10-year G-sec**:

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

For a stock trader in India, a practical quick check is the **US 10-year and
USD/INR**. When both are rising fast, foreign selling in India is likely
([the currencies guide](learn-macro-currencies.md)).

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

- [ ] US 10-year: level and 1-month change — fast or slow?
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
