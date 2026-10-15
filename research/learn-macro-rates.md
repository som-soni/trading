# Interest rates and central banks — why the price of money moves every stock

Learning material: what the Fed and the RBI do, policy rates vs market
yields, why higher rates lower what any stock is worth, which sectors feel it
first, past hiking and cutting cycles, and reading a central-bank meeting.
Companion to [the yield curve guide](learn-macro-yield-curve.md) and
[the inflation guide](learn-macro-inflation.md).

**Where this shows in the app.** Markets → Breadth has a strip of macro tiles
for each market (built by `scripts/swing_screener/marketdata/macro.py`). The
US strip shows the 10-year and 5-year Treasury yields and the dollar. India's
shows USD/INR and Brent crude, plus the US 10-year and the dollar, because
those two drive foreign money into and out of India. Hover a tile to see *why*
it matters. Markets → Sectors is where rotations caused by rates show up first.

---

## 1. What a central bank does

A central bank sets **the price of overnight money**. Every other rate —
deposits, loans, mortgages, bond yields — starts from that rate as a floor. On
top of it comes extra pay for lending for longer and for the risk of not being
repaid.

### What "overnight money" actually means

It is literally a loan that lasts one night.

Banks keep accounts at the central bank, holding what are called **reserves**.
Every day, payments move between banks across those accounts: your salary
leaves your employer's bank and arrives at yours, a loan is drawn down, a
share trade settles. By the end of the day some banks are short of reserves
and others have a surplus, and each one has to end the day square.

So the short banks borrow from the surplus banks, overnight, and repay in the
morning. **The interest rate on that one-night loan is the price of overnight
money.** Money is the thing being rented; the interest is the rent. It is
quoted as an annual rate, which makes one night's cost small:

```
₹1,00,00,000 borrowed overnight at 6.00%  →  1,00,00,000 × 6% ÷ 365 ≈ ₹1,644
```

**Why the central bank gets to set it.** It is the only place reserves come
from — it can create or drain them at will — and it runs two standing
facilities that fence the market in. No bank lends below the floor, because it
could deposit at the central bank instead; none borrows above the ceiling,
because it could borrow from the central bank instead. The traded rate is
pinned inside that corridor:

| | US | India |
|---|---|---|
| The rate announced | Fed funds target range | Repo rate |
| What actually trades | EFFR (unsecured), SOFR (repo) | WACR — weighted average call rate |
| Floor | Interest on reserve balances | SDF — standing deposit facility |
| Ceiling | Discount window | MSF — marginal standing facility |

Note that the announced rate and the traded rate are not the same thing. The
RBI sets the repo rate but *targets* the WACR, which is why Indian commentary
watches WACR drifting inside the corridor even in months when the repo rate
does not move.

**Why every other rate is built on it.** Because a longer loan can be
replicated by rolling overnight loans — lending for a year is approximately
lending overnight 365 times in a row. So:

```
1-year rate ≈ expected average overnight rate over the year
            + term premium       (you are locked in; rates may move)
            + credit premium     (the borrower may not repay)
            + liquidity premium  (you cannot get out early)
```

Arbitrage keeps that roughly true: if a one-year loan paid far more than
rolling overnight, lenders would crowd into the one-year and close the gap.
That is the "floor plus a premium for time and risk" above — and it is why
§2's point holds. The overnight rate anchors the near end tightly, while the
10-year is mostly a vote on where the overnight rate is *heading*, so the two
can move in opposite directions without either being wrong.

| | Federal Reserve (US) | Reserve Bank of India |
|---|---|---|
| Decision body | FOMC — 12 voting members | Monetary Policy Committee — 6 members (3 RBI, 3 external) |
| Policy rate | Fed funds target *range* (e.g. 5.25–5.50%) | **Repo rate** (one number), inside a corridor |
| Mandate | Dual: maximum employment and stable prices (2% inflation) | Flexible inflation target: CPI 4%, band 2–6%, mindful of growth |
| Scheduled meetings | 8 a year, about every six weeks | Bi-monthly — 6 a year |
| Other tools | Balance sheet (QE/QT), forward guidance | CRR, liquidity operations, bond purchases, FX intervention |
| Projections | "Dot plot" at 4 of the 8 meetings | Inflation and GDP forecasts with each policy |

**Raising rates** slows spending, hiring and — a year or more later —
inflation; **cutting** does the reverse. Stocks show the effect first, because
they price the future. QE/QT: see [liquidity and credit](learn-macro-liquidity-credit.md).

## 2. Policy rate vs market yields

The central bank controls **only one interest rate**, a very short-term one:
in the US the federal funds rate (what banks charge each other overnight), in
India the repo rate. Every other rate is set by buyers and sellers in the bond
market.

The market rate closest to the policy rate is the **3-month Treasury bill** — a
three-month loan to the US government. Because it is so short, it simply tracks
the Fed's rate: when the Fed's rate is 5%, a 3-month bill pays about 5%. It is,
in effect, what you earn on cash, which is why the app stores it as
`CASH_YIELD` and the charts here call it the cash yield.

Longer bonds are different. The yield on a **5-year** or **10-year** bond is
the market's combined bet on three things:

- where the Fed's rate will be, on average, over those years;
- how much inflation there will be over that time;
- a little extra pay for tying money up for longer (the **term premium**).

So long yields can move against the Fed. After the Fed's first cut in
September 2024, the 10-year *rose* from about 3.6% to 4.8% in four months.
And from October to December 2023 the 10-year *fell* from about 5.0% to 3.9%
while the Fed did nothing. **For stocks the long yield usually matters more
than the policy rate.** It is the rate investors use to discount future
profits when they value a stock
([the yield curve guide](learn-macro-yield-curve.md)).

```series
title: The price of cash — the 3-month T-bill and the 10-year, 2000–today
from: 2000-01-01
line: us:CASH_YIELD | 3-month T-bill yield (%)
line: us:US10Y | US 10-year yield (%)
band: 2004-06-30 2006-06-29 | Fed hiking
band: 2015-12-16 2018-12-19 | Fed hiking
band: 2022-03-16 2023-07-26 | Fed hiking
caption: The T-bill moves in step with the Fed's rate — near zero in 2009–15 and 2020–21, then from 0.03% at the end of 2021 to above 5.3% in October 2023. The 10-year moves on its own and often turns first.
```

## 3. Why higher rates lower stock valuations

A share is a claim on **all of a company's future profits**. A dollar of
profit ten years from now is worth less than a dollar today. How much less
depends on the discount rate. Raise that rate and the same profits are worth
less today — **with no change at all in the business**.

### A worked example

A company earns $10 a year, forever. Its value is 10 ÷ the rate:

| Discount rate | Value | P/E implied |
|---|---|---|
| 2% | $500 | 50× |
| 5% | $200 | 20× |

Same earnings, **60% less value**. Real valuations are more complicated: they
allow for growth, and they add extra return for risk on top of the bond yield.
But two things still hold. Higher rates mean lower values. And the effect is
uneven: **a rise from a low level does the most damage**. Going from 2% to 3%
cuts the value by a third; going from 5% to 6% cuts it by a sixth.

### Near profits vs distant profits

What is $100 worth today, at 2% vs 5%?

| $100 received in | at 2% | at 5% | Loss from the rise |
|---|---|---|---|
| 1 year | $98 | $95 | about 3% |
| 10 years | $82 | $61 | about 25% |
| 20 years | $67 | $38 | about 44% |

This is **duration**: the further away the cash, the more its price today
reacts to rates. A utility that pays dividends now is short-duration. A
software company whose profits are a decade away is long-duration. That is
why growth stocks react most to yields (§4).

### Competition from cash, and the economy

**Stocks compete with safe assets.** At the end of 2021 T-bills paid 0.03%, so
almost anything beat cash. In 2023 they paid over 5%, so a stock had to earn
enough to be worth its risk. A rough gauge is the **equity risk premium** —
the extra return stocks offer over safe bonds. One simple version is the
earnings yield (earnings ÷ price, the P/E turned upside down) minus the
10-year yield. At a P/E of 20 the earnings yield is 5%. With a 1.5% 10-year
that leaves a 3.5-point cushion (5% − 1.5%). With a 5% 10-year it leaves none.
That is not a sign the market has topped, but it means **no cushion** if
earnings disappoint.

Rates hit stocks twice. First, quickly, through the multiple — the P/E
investors will pay. Then, slowly, through **earnings**, as the economy slows.
So the worst damage often comes late.

## 4. Growth vs value: who reacts most

```series
title: 2022 — the year rates left zero: tech, energy and banks
from: 2021-12-31
to: 2022-12-30
rebase: 100
line: us:XLK | Technology (XLK)
line: us:XLE | Energy (XLE)
line: us:XLF | Financials (XLF)
band: 2022-03-16 2022-12-30 | Fed hiking
caption: All three start at 100. Technology lost about 29% over the year, financials about 14%; energy gained about half. The tech/energy ratio more than halved.
```

In 2022 the Fed took its rate from near zero to above 4%. The 10-year went
from about 1.6% to above 4%. And stocks sorted themselves by duration:

- **Technology (XLK) −29%, Nasdaq 100 (QQQ) −34%** — profits far in the
  future and high P/Es, so the biggest hit from a higher discount rate.
- **Energy (XLE) +53%** — cash coming in now; the oil price rise *was* the
  inflation.
- **Financials −14%, utilities flat, staples −3%** — banks' wider lending
  margins, or earnings that hold up in a slowdown, offset the rate hit.

Small companies carry more floating-rate debt (loans whose interest rate
resets as rates rise). Yet in 2022 **small caps (IWM) fell less than the
Nasdaq 100 (QQQ): −23% vs −34%**. The duration effect on valuations mattered
more. In 2023 it flipped (QQQ +54%, IWM +15%). By then high rates had reached
small companies' interest bills.

**For a momentum trader:** a change in the rate trend changes *which* stocks
lead. Markets → Sectors shows the rotation. The macro picture tells you *why*,
and how long it may last.

## 5. The rate-sensitive sectors

| Sector | Why rates matter | Rising rates | Falling rates |
|---|---|---|---|
| **Banks** (XLF; Nifty Bank) | Borrow short-term, lend longer-term; they earn the gap (net interest margin) | Wider margins, until loan losses or deposits leave | Margin squeeze, more loan demand |
| **Real estate** (XLRE) | Heavy borrowers; income investors compare their payouts to bond yields | Hit twice: costlier borrowing and lower valuations | Among the first to recover |
| **Utilities** (XLU) | "Bond proxies" — bought like bonds, for steady dividends; high debt | Lose appeal as T-bills pay more | Bought as yields fall |
| **Homebuilders, autos** | Customers buy on credit | Demand falls | Demand returns early |
| **Long-duration growth** | Profits far in the future | P/Es cut hardest | P/Es rise fastest |

Real estate is the textbook case. **XLRE fell about 38%** from the end of 2021
to October 2023, when the 10-year neared 5%. Utilities held up in 2022. But
they **fell about 15%** in the first ten months of 2023, once T-bills paying
above 5% made their dividends look thin.

Banks do not simply rise when rates rise. In March 2023 depositors moved cash
out of banks into money market funds, which paid far more interest. Silicon Valley Bank failed because of
losses in its bond portfolio. XLF fell about 14% in under two weeks.
**Fast rate rises break something, and the weakest balance sheet goes
first.**

## 6. Hiking and cutting cycles — what stocks did

"Hikes bad, cuts good" is wrong often enough to be dangerous. What matters is
**why** the central bank is moving.

| Cycle | Fed move (approx.) | S&P 500, first hike to last |
|---|---|---|
| June 2004 – June 2006 | 1% → 5.25%, a quarter point a meeting | **+12%**, worst drawdown about 8% |
| Dec 2015 – Dec 2018 | 0–0.25% → 2.25–2.50% | **+21%**, including a 20% drop Sept–Dec 2018 |
| March 2022 – July 2023 | near zero → 5.25–5.50%, fastest in 40 years | **+6%**, but a 23% drawdown to Oct 2022 |

Slow hikes, signalled well in advance, into a growing economy are usually
fine: earnings grow faster than the P/E shrinks. **Speed and surprise** hurt,
as in 2022. So do hikes into slowing growth, as in late 2018; that sell-off
ended when the Fed paused.

| First cut | Why | S&P 500 afterwards |
|---|---|---|
| Jan 2001 | Recession, tech bust | **−40%** to the Oct 2002 low |
| Sept 2007 | Housing and credit crisis | **−54%** to the March 2009 low |
| July 2019 | "Insurance" against a slowdown | **+12%** to the Feb 2020 peak |
| March 2020 | Pandemic emergency, cut to zero | **+24%** a year later, after a plunge first |
| Sept 2024 | Inflation falling, "recalibration" | **+17%** a year later, with a 19% drop in spring 2025 |

**Cuts into a recession** (2001, 2007) came with the worst bear markets of
the era. In those cases the Fed cuts *because* earnings are collapsing.
**Insurance cuts** — cuts made to protect a still-growing economy against a
slowdown (1995, 1998, 2019, 2024) — were followed by gains: in 1995 and 1998,
about 20% over the next year. So the first cut is not a buy signal. **The
reason for the cut is the signal** — see the
[business cycle guide](learn-macro-cycle.md).

```series
title: Two cutting cycles that ended in bear markets, 2000–2010
from: 2000-01-01
to: 2010-12-31
line: us:SP500_PRICE_LONG | S&P 500 | log
line: us:CASH_YIELD | 3-month T-bill (%) | right
band: 2001-01-03 2003-06-25 | Fed cutting
band: 2007-09-18 2008-12-16 | Fed cutting
caption: Each time the T-bill fell from about 5–6% to below 1%, the S&P 500 fell by roughly 40–55% — the cuts were a response to recession, not a cure for the market.
```

## 7. Reading a central-bank meeting

| Part | What to look for |
|---|---|
| **Decision** | Usually known in advance — prices in the interest-rate futures market show the odds |
| **Statement** | Compared word by word with the last one; one changed phrase can matter more than the rate |
| **Guidance** | Hints at what comes next: "higher for longer", "data dependent" |
| **Dot plot** (Fed, 4×/yr) | Where each official expects rates to go, vs what futures imply |
| **Press conference** | Tone in the Q&A — many same-day reversals start here |

**Markets move on surprise, not news.** If futures put a hike at 95%, the hike
itself does nothing: traders had already bet on it. That is what "priced in"
means. A hold when a cut was expected, though, is a shock. Before a meeting,
ask: *what does the market expect?* (CME FedWatch shows it). After it, ask:
*was it more hawkish or dovish than that?* The 5-year on the macro strip gives
a quick answer. On meeting days and the session after, prices swing more
within the day and more breakouts fail. The
[calendar guide](learn-macro-calendar.md) covers planning around them.

## 8. India: the RBI, liquidity and the US connection

### The RBI's tools

- **Repo rate** — the policy rate. It sits inside a corridor: the Standing
  Deposit Facility below, the Marginal Standing Facility above.
- **CRR** (cash reserve ratio) — the share of deposits banks must park with
  the RBI at zero interest. A CRR cut releases cash for banks to lend. The Fed
  has no such lever.
- **Liquidity** — whether the banking system as a whole has spare cash
  (**surplus**) or is short of it (**deficit**). This can matter as much as
  the repo rate for short-term rates and bank stocks.

Recent cycles, approximately: the RBI raised the repo rate from **4.0% to
6.5%** between May 2022 and February 2023. The first hike, in May 2022, came
between scheduled meetings. The RBI then held for two years. It cut to **5.5%
by June 2025**, and alongside the June move announced a CRR cut in stages.

```series
title: India during the RBI's 2022–23 hikes: banks vs the Nifty
from: 2022-05-02
to: 2023-02-28
rebase: 100
line: india:^NSEBANK | Nifty Bank
line: india:^NSEI | Nifty 50
band: 2022-05-04 2023-02-08 | RBI hiking (4.0% → 6.5%)
caption: From the surprise May 2022 hike to the last one in February 2023, the Nifty Bank rose about 18% and the Nifty 50 about 7% — Indian banks led while US financials fell.
```

The difference from the US was the **credit cycle** — whether banks are
nursing bad loans or lending freely. Indian banks had cleaned up their bad
loans, and loan growth was speeding up. So wider margins went straight to
profit. **How rates act depends on the state of the borrower.** Other
rate-sensitive groups in India:

- **NBFCs** (non-bank lenders) — they borrow in the markets rather than taking
  deposits, so their costs rise faster than what they earn on loans. They
  usually suffer more from hikes and gain more from cuts.
- **Real estate**, **autos and two-wheelers**, and consumer stocks on high
  P/Es.

### How US rates reach India

- **FII flows.** When US yields rise, foreign investors can earn more at home,
  with no currency risk. So money leaves emerging markets. In 2022 FIIs sold
  heavily, but domestic institutions and SIP money bought what they sold. That
  is one reason the Nifty 50 ended 2022 up about 3% while the S&P 500 fell
  20%.
- **The rupee.** Higher US yields and a strong dollar push the rupee down:
  USD/INR rose about 11% in 2022. A weaker rupee makes India's oil imports
  cost more and pushes up inflation. That can force the RBI to keep rates high
  when growth alone would call for cuts. IT exporters gain; importers lose.
- **The 2013 taper tantrum** shows the pattern. The Fed talked of slowing QE.
  In four months the US 10-year rose from about 1.6% to about 3.0%. USD/INR
  jumped from about 54 to above 68. The Nifty fell about 15% peak to trough.

That is why the India macro strip shows the US 10-year and the dollar; see
[the currencies guide](learn-macro-currencies.md).

## 9. What a trader does with it

- **Name the current state — no forecast needed.** Is the central bank
  hiking, holding or cutting? Is the long yield rising or falling? A rising
  long yield favours short-duration stocks (energy, financials, value). A
  falling one favours long-duration growth stocks.
- **Check that the leading sectors agree** (Markets → Sectors). If they don't,
  go with what prices are doing.
- **Watch speed, not just level.** A 50bp jump in yields in a month hurts
  breakouts in high-P/E stocks more than a slow drift to the same level
  ([the yield curve guide](learn-macro-yield-curve.md)).
- **Know why cuts are coming.** Insurance cuts with healthy breadth: stay
  invested. Emergency cuts with collapsing breadth and wider credit spreads:
  cut exposure.
- **Trade smaller around Fed (FOMC) and RBI decision days.** Their big swings
  knock out tight stops.
- **India: watch the US too.** A jump in the US 10-year or the dollar hits
  stocks that FIIs own heavily. Banks and NBFCs react most to RBI liquidity
  and the repo rate.

## 10. What the evidence says

- **Robust:** valuations depend on discount rates, and long-duration stocks
  depend on them most. That is arithmetic, and 2022 showed it. Policy
  *surprises* move stocks. Bernanke and Kuttner (2005) estimate that a
  surprise 25bp cut lifts the US market about 1%. Expected moves do little.
- **Folklore:** "don't fight the Fed" and "the first cut is bullish" as
  timing rules. Both failed in 2001 and 2007–08, when the Fed cut for two
  years into falling markets. What follows a cut depends on whether a
  recession follows.
- **Fragile:** the stock–bond relationship. From about 2000 to 2021 bond
  prices mostly rose when stocks fell; in 2022, with inflation the problem,
  both fell together.
- **Long, variable lags.** Hikes take one to two years to work through the
  economy. Many calls that "the hikes will break it" were years early. And
  rates are only one input: 2022 was also about oil and the war in Ukraine.
  Use rates to read the background, not as a mechanical signal.

## 11. Checklist

- [ ] Next Fed / RBI meeting and any surprise risk; the US 10-year's level and pace?
- [ ] Cash yield vs the market's earnings yield: is there a cushion?
- [ ] Leadership consistent with the rate trend (Markets → Sectors)?
- [ ] Rate-sensitive groups turning? Cuts coming: insurance or recession?
- [ ] India: USD/INR, the US 10-year, RBI liquidity stance.
- [ ] New positions sized down around FOMC / RBI decision days.

## Further reading

- Federal Reserve Board (federalreserve.gov) — FOMC statements, minutes, the
  Summary of Economic Projections; CME FedWatch for market odds.
- Reserve Bank of India (rbi.org.in) — Monetary Policy Statements, MPC minutes.
- FRED, Federal Reserve Bank of St. Louis (fred.stlouisfed.org) — the Fed
  funds rate, Treasury yields and most US series discussed here.
- Ben Bernanke and Kenneth Kuttner, "What Explains the Stock Market's
  Reaction to Federal Reserve Policy?", *Journal of Finance*, 2005.
- Aswath Damodaran's equity risk premium updates (NYU Stern).
- Martin Zweig, *Winning on Wall Street* — the original "don't fight the Fed".
