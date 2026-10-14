# Interest rates and central banks — why the price of money moves every stock

Learning material: what the Fed and the RBI do, policy rates vs market
yields, why higher rates lower what any stock is worth, which sectors feel it
first, past hiking and cutting cycles, and reading a central-bank meeting.
Companion to [the yield curve guide](learn-macro-yield-curve.md) and
[the inflation guide](learn-macro-inflation.md).

**Where this shows in the app.** Markets → Breadth has a macro strip per
market (`scripts/swing_screener/marketdata/macro.py`): the US 10-year and
5-year yields and the dollar; India's adds USD/INR and Brent to the US 10-year
and dollar, which drive foreign flows. Hover a tile for its *why*. Markets →
Sectors is where rate-driven rotations show up first.

---

## 1. What a central bank does

A central bank sets **the price of overnight money**. Every other rate —
deposits, loans, mortgages, bond yields — is built on that floor plus a
premium for time and risk.

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

The central bank sets **one short rate**; the market sets the rest. The
**3-month Treasury bill** hugs the policy rate (stored here as `CASH_YIELD`:
what cash earns). The **5-year** and **10-year** are the market's own vote:
the expected policy path, plus inflation expectations, plus a term premium.

So the Fed can cut while long yields *rise* — after the first cut in
September 2024 the 10-year went from about 3.6% to 4.8% in four months — and
hold while they *fall*: from October to December 2023 the 10-year dropped
from about 5.0% to 3.9% with no move by the Fed. **For stocks the long yield
usually matters more than the policy rate** — it is what valuations are
discounted at ([the yield curve guide](learn-macro-yield-curve.md)).

```series
title: The price of cash — the 3-month T-bill and the 10-year, 2000–today
from: 2000-01-01
line: us:CASH_YIELD | 3-month T-bill yield (%)
line: us:US10Y | US 10-year yield (%)
band: 2004-06-30 2006-06-29 | Fed hiking
band: 2015-12-16 2018-12-19 | Fed hiking
band: 2022-03-16 2023-07-26 | Fed hiking
caption: The T-bill follows the Fed step by step — near zero in 2009–15 and 2020–21, then from 0.03% at the end of 2021 to above 5.3% in October 2023. The 10-year moves on its own and often turns first.
```

## 3. Why higher rates lower stock valuations

A share is a claim on **all of a company's future profits**. A dollar of
profit in ten years is worth less than a dollar today, and how much less
depends on the discount rate. Raise the rate and the same profits are worth
less today — **with no change at all in the business**.

### A worked example

A company earns $10 a year, forever. Its value is 10 ÷ the rate:

| Discount rate | Value | P/E implied |
|---|---|---|
| 2% | $500 | 50× |
| 5% | $200 | 20× |

Same earnings, **60% less value**. Real valuation adds growth and a risk
premium on top of the bond yield, but the direction and the non-linearity
hold: **a rise from a low level does the most damage** (2% → 3% cuts the value
by a third; 5% → 6% by a sixth).

### Near profits vs distant profits

What is $100 worth today, at 2% vs 5%?

| $100 received in | at 2% | at 5% | Loss from the rise |
|---|---|---|---|
| 1 year | $98 | $95 | about 3% |
| 10 years | $82 | $61 | about 25% |
| 20 years | $67 | $38 | about 44% |

This is **duration**: the further away the cash, the more the price reacts.
A dividend-paying utility is short-duration; a software company whose profits
are a decade out is long-duration — why growth reacts most to yields (§4).

### Competition from cash, and the economy

**Stocks compete with safe assets.** At 0.03% on T-bills (end of 2021)
anything beat cash; at over 5% (2023) a stock had to earn its risk. A rough
gauge is the **equity risk premium**: the earnings yield (inverse of the P/E)
minus the 10-year. At a P/E of 20 that is 5% − 1.5% = a 3.5-point cushion with
a 1.5% 10-year, and none with a 5% one — no top signal, but **no cushion** if
earnings disappoint.

Rates hit stocks twice: through the multiple (fast) and, as the economy
slows, through **earnings** (slow) — so the worst damage often comes late.

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

In 2022 the Fed took its rate from near zero to above 4%, the 10-year went
from about 1.6% to above 4%, and the market sorted itself by duration:

- **Technology (XLK) −29%, Nasdaq 100 (QQQ) −34%** — distant profits, high
  multiples, the biggest discount-rate hit.
- **Energy (XLE) +53%** — near-term cash; oil *was* the inflation.
- **Financials −14%, utilities flat, staples −3%** — wider margins or
  defensive earnings offset the rate hit.

Small caps carry more floating-rate debt, yet in 2022 **IWM fell less than
QQQ (−23% vs −34%)** — valuation duration dominated. In 2023 it flipped (QQQ
+54%, IWM +15%) as high rates reached small companies' interest bills.

**For a momentum trader:** rate regimes change *which* stocks lead. Markets
→ Sectors catches the rotation; the macro read says *why* and how long.

## 5. The rate-sensitive sectors

| Sector | Why rates matter | Rising rates | Falling rates |
|---|---|---|---|
| **Banks** (XLF; Nifty Bank) | Borrow short, lend longer: net interest margin | Wider margins, until losses or deposit flight | Margin squeeze, more loan demand |
| **Real estate** (XLRE) | Heavy borrowers; yield buyers compare them to bonds | Hit twice: funding and valuation | Among the first to recover |
| **Utilities** (XLU) | "Bond proxies": steady dividends, high debt | Lose appeal as T-bills pay more | Bid as yields fall |
| **Homebuilders, autos** | Customers buy on credit | Demand falls | Demand returns early |
| **Long-duration growth** | Profits far in the future | De-rated hardest | Re-rated fastest |

Real estate is the textbook case: **XLRE fell about 38%** from the end of
2021 to October 2023, when the 10-year neared 5%. Utilities held up in 2022
but **fell about 15%** in the first ten months of 2023, once T-bills above 5%
made their dividends look thin.

Banks are not "rates up, banks up". In March 2023 deposits fled to money
funds and Silicon Valley Bank failed on losses in its bond portfolio; XLF
fell about 14% in under two weeks.
**Fast rate rises break something; the weakest balance sheet goes first.**

## 6. Hiking and cutting cycles — what stocks did

"Hikes bad, cuts good" is wrong often enough to be dangerous. What matters is
**why** the central bank is moving.

| Cycle | Fed move (approx.) | S&P 500, first hike to last |
|---|---|---|
| June 2004 – June 2006 | 1% → 5.25%, a quarter point a meeting | **+12%**, worst drawdown about 8% |
| Dec 2015 – Dec 2018 | 0–0.25% → 2.25–2.50% | **+21%**, including a 20% drop Sept–Dec 2018 |
| March 2022 – July 2023 | near zero → 5.25–5.50%, fastest in 40 years | **+6%**, but a 23% drawdown to Oct 2022 |

Slow, telegraphed hikes into a growing economy are usually fine — earnings
outgrow the shrinking multiple. **Speed and surprise** hurt (2022), as do hikes
into slowing growth (late 2018, which ended when the Fed paused).

| First cut | Why | S&P 500 afterwards |
|---|---|---|
| Jan 2001 | Recession, tech bust | **−40%** to the Oct 2002 low |
| Sept 2007 | Housing and credit crisis | **−54%** to the March 2009 low |
| July 2019 | "Insurance" against a slowdown | **+12%** to the Feb 2020 peak |
| March 2020 | Pandemic emergency, cut to zero | **+24%** a year later, after a plunge first |
| Sept 2024 | Inflation falling, "recalibration" | **+17%** a year later, with a 19% drop in spring 2025 |

**Cuts into a recession** (2001, 2007) came with the worst bear markets of
the era: the Fed cuts *because* earnings are collapsing. **Insurance cuts**
into a growing economy (1995, 1998, 2019, 2024) were followed by gains — in
1995 and 1998 about 20% over the next year. The first cut is not a buy
signal; **the reason for the cut is the signal** — see the
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
| **Decision** | Usually known in advance — futures price the odds |
| **Statement** | Diffed word by word; one changed phrase can outweigh the rate |
| **Guidance** | "Higher for longer", "data dependent": what comes next |
| **Dot plot** (Fed, 4×/yr) | Officials' projected path vs what futures price |
| **Press conference** | Tone in the Q&A — many intraday reversals start here |

**Markets move on surprise, not news.** A hike that was 95% priced does
nothing; a hold when a cut was expected is a shock — that is "priced in". Ask
before: *what does the market expect?* (CME FedWatch shows it). Ask after:
*more hawkish or dovish than that?* — the 5-year on the macro strip is a quick
read. Meeting days and the next session bring wider ranges and false
breakouts; the [calendar guide](learn-macro-calendar.md) covers planning
around them.

## 8. India: the RBI, liquidity and the US connection

### The RBI's tools

- **Repo rate** — the policy rate, inside a corridor (Standing Deposit
  Facility below, Marginal Standing Facility above).
- **CRR** — deposits banks must park with the RBI at zero interest. A CRR cut
  releases cash to lend; the Fed has no such lever.
- **Liquidity** — whether the banking system is in **surplus or deficit**
  can matter as much as the repo rate for short rates and bank stocks.

Recent cycles, approximately: repo raised from **4.0% to 6.5%** between May
2022 (an off-cycle hike) and February 2023, held for two years, then cut to
**5.5% by June 2025**, with a phased CRR cut alongside the June move.

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

The difference from the US was the **credit cycle**: Indian banks had cleaned
up their bad loans and loan growth was accelerating, so wider margins went
straight to profit. **Rates act through the state of the borrower.** Other
rate-sensitive groups in India: **NBFCs** (market-funded, so their costs rise
faster than their loan yields — they usually suffer more from hikes and gain
more from cuts), **real estate**, **autos and two-wheelers**, and
high-multiple consumer names.

### How US rates reach India

- **FII flows.** Higher US yields pay foreign investors at home with no
  currency risk; emerging markets lose flows. Heavy FII selling in 2022 was
  absorbed by domestic institutions and SIP money — one reason the Nifty
  50 ended 2022 up about 3% while the S&P 500 fell 20%.
- **The rupee.** Higher US yields and a strong dollar pull the rupee down:
  USD/INR rose about 11% in 2022. That raises the oil import bill and
  inflation, which can force the RBI to stay tight when growth argues
  otherwise. IT exporters gain; importers lose.
- **The 2013 taper tantrum** is the template: the US 10-year rose from about
  1.6% to about 3.0% in four months on talk of slowing QE, USD/INR jumped
  from about 54 to above 68, and the Nifty fell about 15% peak to trough.

Hence the US 10-year and the dollar on the India macro strip; see
[the currencies guide](learn-macro-currencies.md).

## 9. What a trader does with it

- **Name the regime — no forecast needed.** Hiking, holding or cutting; long
  yield rising or falling? Rising favours short-duration stocks (energy,
  financials, value); falling favours long-duration growth.
- **Check that leadership agrees** (Markets → Sectors); if not, respect price.
- **Watch speed, not just level.** A 50bp jump in a month pressures
  high-multiple breakouts more than a slow drift to the same level
  ([the yield curve guide](learn-macro-yield-curve.md)).
- **Know why cuts are coming.** Insurance cuts with healthy breadth: stay
  invested. Emergency cuts with collapsing breadth and wider credit spreads:
  cut exposure.
- **Size down around FOMC and RBI days** — they shake out tight stops.
- **India: watch the US too.** A jump in the US 10-year or the dollar hits
  FII-heavy stocks; banks and NBFCs react most to RBI liquidity and repo.

## 10. What the evidence says

- **Robust:** valuations depend on discount rates, long-duration stocks most
  — it is arithmetic, and 2022 showed it. Policy *surprises* move stocks:
  Bernanke and Kuttner (2005) estimate a surprise 25bp cut lifts the US
  market about 1%; expected moves do little.
- **Folklore:** "don't fight the Fed" and "the first cut is bullish" as
  timing rules. Both failed in 2001 and 2007–08, when the Fed cut for two
  years into falling markets; outcomes split on whether a recession follows.
- **Fragile:** the stock–bond relationship. From about 2000 to 2021 bond
  prices mostly rose when stocks fell; in 2022, with inflation the problem,
  both fell together.
- **Long, variable lags.** Hikes reach the economy over one to two years;
  many "the hikes will break it" calls were early by years. And rates are one
  input — 2022 was also oil and the war in Ukraine. A regime lens, not a
  mechanical signal.

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
