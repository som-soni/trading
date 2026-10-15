# Liquidity and credit — the money underneath every chart

Learning material. This guide covers what "liquidity" means and how QE and QT add and remove it.
It covers the 2020 flood of money and the 2021 speculative peak, and why credit (the market for
company debt) often warns before stocks. It also covers the VIX and stress in borrowing markets, bank scares,
India's system liquidity and its 2018 NBFC crisis. Finally, it shows how a trader reads all of it to decide how much to have invested. Companion to
[the interest-rates guide](learn-macro-rates.md) (which covers the *price* of money; this guide covers
its quantity) and [the currencies guide](learn-macro-currencies.md).

**Where this shows in the app.** The US macro strip (the row of market tiles) on Markets → Breadth
(`scripts/swing_screener/marketdata/macro.py`) ends with **HY credit (HYG)**, a high-yield bond fund.
The tile shows the 1-day and 1-month change, a 3-month sparkline, and the hover line *"Credit risk
appetite: HYG falling while stocks rise is an early warning."* The VIX is not
on the strip. Instead, the same page's **"Options: expected vs actual?"** card compares the VIX
(India VIX for India) with how much the index has actually been moving. The
screener uses it too. When the VIX is above 25 (US) or India VIX is above 20,
the app's market-regime check flags the market as high-volatility, and position sizing halves risk per trade from 1%
to 0.5% (`core/regime.py`, `core/sizing.py`, each market's config).

---

## 1. What "liquidity" means

The word means three different things. In a crisis, all three dry up together:

| Meaning | What it is | How you see it |
|---|---|---|
| **Market liquidity** | Can you trade in large size without moving the price? | Bid-ask spreads, gaps, how fast a stock falls on modest selling |
| **Funding liquidity** | Can banks, funds and companies borrow, and take out new loans to repay old ones as they come due? | Money-market rates (rates on very short-term loans), credit spreads, the dollar |
| **Monetary liquidity** | How much money the central bank and banks have created | The Fed's and RBI's balance sheets (what each central bank owns), bank reserves, whether the banking system as a whole has spare cash (surplus) or is short (deficit) |

**The trader's version: liquidity is how much money is looking for something to buy,
and how easily money can be borrowed.** When there is plenty, investors buy almost any story,
and dips are shallow. When it shrinks, the weakest stories are sold
first. Then everything else is sold to raise cash.

## 2. Central-bank balance sheets: QE and QT

### 2.1 The mechanics

**Quantitative easing (QE):** the central bank buys government bonds (and, in the US,
mortgage bonds), paying with newly created reserves. Yields fall. The investors who sold the bonds
buy riskier assets with the money, and banks fill up with cash. **Quantitative tightening (QT)**
is the reverse. The central bank lets its bonds mature without buying new ones, which removes reserves.

### 2.2 The US record (approximate; not stored in the app)

| Period | What the Fed did | Balance sheet, roughly |
|---|---|---|
| 2008–2014 | QE1 (2008–10), QE2 (2010–11), QE3 (2012–14) | about $0.9 trillion → about $4.5 trillion |
| 2017–2019 | First QT, ended in 2019 after the September spike in repo rates (the rate on overnight loans backed by bonds) | about $4.5 trillion → under $4 trillion |
| 2020–2022 | Pandemic QE, "unlimited" from 23 March 2020, purchases reduced step by step from late 2021, ended March 2022 | about $4 trillion → about $9 trillion |
| 2022– | Second QT from June 2022, slowed in 2024–25 | drifting down |

The Fed publishes its balance sheet weekly (the H.4.1 release; on FRED the series is `WALCL`). The RBI also buys and sells
government bonds (called open-market operations), but never on the Fed's scale.

### 2.3 "Don't fight the Fed"

This is Martin Zweig's line: when the Fed is easing, stay invested; when it tightens hard,
be careful. It describes the **general background**, not what happens on any given day or month. QE years were mostly
good for stocks; 2022 was not. But the Fed eases *because* something is
going wrong. In 2008 and 2020 stocks kept falling after the first emergency cuts. **Easing in the middle of a crash is not a buy signal. Easing after
the market has stopped falling and steadied usually is.**

## 3. The 2020 flood and the 2021 speculative peak

```series
title: The 2020 liquidity flood — small caps and the Nasdaq 100
from: 2019-06-01
to: 2022-12-31
rebase: 100
line: us:RUSSELL2000 | Russell 2000 (IWM)
line: us:NASDAQ100 | Nasdaq 100 (QQQ)
band: 2020-03-23 2022-03-09 | Fed QE
mark: 2021-11-08 | Small-cap peak
caption: From the 23 March 2020 low the Russell 2000 rose about 150% to its November 2021 peak and the Nasdaq 100 about 140% to its December peak. Both then fell about a third as QE ended and rates rose.
```

The Fed bought bonds, the government sent cheques, and rates stayed at zero. The
riskiest parts of the market rose the most: small caps, unprofitable tech, SPACs (shell companies listed
to buy a private business), meme stocks, crypto. Two lessons:

- **The most speculative assets peak first.** The Russell 2000 peaked on
  8 November 2021, about seven weeks before the Nasdaq 100 (27 December).
  The most speculative growth stocks peaked well before both. When the
  most speculative stocks start falling while the indexes still rise, money is leaving the market.
- **Watch how many stocks are taking part.** Late 2021's index highs were widely noted to depend
  on fewer and fewer stocks. That is the kind of divergence Markets → Breadth shows.

## 4. Credit — why bonds often warn before stocks

### 4.1 The credit spread

A **credit spread** is the extra yield a risky borrower pays over the
government. Spreads on high-yield ("junk") bonds, from riskier companies, react the most. When lenders get nervous they
demand more, spreads widen, and junk-bond prices fall. The ICE BofA US High Yield
spread (on FRED) has ranged from around 3 percentage points in calm years to
near 20 at the end of 2008 and above 10 in March 2020 (approximate).

### 4.2 Why credit leads

- **Bondholders only worry about the downside.** At best they get their money
  back, so they are the first to notice when a company's finances weaken.
- **Credit is funding.** When spreads widen, weaker companies cannot take out new loans to repay old ones. So
  wider spreads help cause the trouble they predict.
- **Big investors change what they will pay for bonds gradually.** So the move starts earlier, and more quietly,
  than in stocks.

### 4.3 HYG — the series the app stores instead

The app stores **HYG** (the iShares high-yield bond ETF) as a raw daily close
since 2007. Two cautions. First, the raw close leaves out the coupons the fund pays out, so HYG
(and any ratio built on it) drifts down over the years. **Read it over weeks and
months.** Second, HYG also falls when Treasury yields rise, which is not credit
stress. Dividing HYG by a Treasury fund removes most of that effect. HYG divided by IEF
(a fund of 7–10 year Treasuries) is a rough **gauge of how willing lenders are to take credit risk**.

```series
title: Credit turned down months before stocks, 2007–2009
from: 2007-04-11
to: 2009-12-31
line: us:SP500_TR | S&P 500 total return | log
line: us:HYG | High-yield bonds (HYG) | right
line: us:HYG / us:BONDS | HYG / Treasuries (IEF) | pane2
band: 2007-06-07 2007-10-09 | Credit falling, stocks still rising
mark: 2007-10-09 | S&P peak
caption: HYG against Treasuries peaked on 7 June 2007; the S&P 500 kept rising until 9 October. Peak to the March 2009 low the ratio fell about 53%, HYG about 42% and the S&P 500 about 55%.
```

The same warning came in **2014–16**. HYG/IEF peaked in June 2014, as oil
began to collapse and energy companies struggled to pay their debts. It fell about 29% by
February 2016. The S&P 500 kept rising for another year and peaked in July 2015.
It then dropped about 13% into February 2016, bottoming the same day as the credit ratio.
And in **2021**, HYG's price peaked on 15 September, while the S&P
500 rose about another 7% to its 3 January 2022 high.

```series
title: Credit in 2020 and 2022 — a crash and a rates shock
from: 2019-06-01
to: 2023-12-31
line: us:SP500_TR | S&P 500 total return
line: us:HYG / us:BONDS | HYG / Treasuries (IEF) | pane2
band: 2020-02-19 2020-03-23 | Covid crash
band: 2022-01-03 2022-10-12 | 2022 bear market
caption: In 2020 credit crashed with stocks (the ratio fell about 29% to 23 March) and recovered with them once the Fed said it would buy corporate bonds. In 2022 the ratio barely moved for the year — that was a rates bear market, not a credit one.
```

**2020 was a funding panic, not a slow credit warning.** Everything was sold
at once, and the ratio did not move first. It turned when the Fed announced, on 23
March 2020, that it would buy corporate bonds (later including high-yield
ETFs). Credit and stocks bottomed together, that same day.

**2022 is the honest counter-example.** HYG's *price* fell about 18% to
September. That looked alarming, but most of it came from rising Treasury yields.
Measured against Treasuries, the ratio dipped about 9% from April to July and ended
the year only about 1% lower. The S&P 500's 25% fall was driven by rates and valuations, and
credit stress never spread. **When stocks fall but credit holds steady, the damage is
usually more limited** than in a true credit bear market like 2008.

## 5. The VIX and funding stress

The VIX is calculated from the prices of 30-day S&P 500 options. It shows what protection against a fall costs. It spikes when
everyone wants insurance at once. That tends to happen just as dealers and funds that trade with borrowed money are cutting their risk.

```series
title: The VIX since 2010 — spikes and the calm between
from: 2010-01-01
tf: W
line: us:VIX | VIX
mark: 2011-08-08 | US downgrade
mark: 2015-08-24 | China devaluation
mark: 2018-02-05 | Volmageddon
mark: 2020-03-16 | Covid 82.7
mark: 2022-03-07 | 2022 high
mark: 2024-08-05 | Yen carry unwind
mark: 2025-04-08 | Tariff shock
caption: Daily closes: 48 (Aug 2011), 40.7 (Aug 2015), 37.3 (Feb 2018), 82.7 (Mar 2020), 36.5 (Mar 2022), 38.6 (Aug 2024), 52.3 (Apr 2025). Calm years sit mostly between 10 and 20; weekly bars show less than the daily peaks.
```

- **A short spike after a calm period usually comes from traders unwinding crowded bets, not a lasting change.** On 5 August 2024
  the VIX closed at 38.6 (much higher during the day). A popular carry
  trade funded by borrowing in yen was being closed out all at once by many traders. Two weeks later the VIX was down about 60%. February 2018 was
  similar: products that bet on low volatility collapsed, not the economy.
- **A VIX that stays high signals a lasting change in the market.** After March 2020 it did not close
  below 20 for the rest of the year. In 2022 it peaked at only 36.5, but it closed
  above 20 in 47 of 52 weeks. That was a slow, grinding bear market, not a panic.
- **India VIX** behaves the same way. Its highest stored value is 83.6, on 24 March
  2020. The June 2024 election-result day took it to 26.8.

**Trader's read:** after a spike from calm, stop buying breakouts for a few
days. Let the market show whether it was crowded bets being unwound or something real. A
VIX holding above the threshold (25 for the US) is when the app halves risk.

## 6. Bank stress — March 2023

On 10 March 2023 Silicon Valley Bank failed. Signature Bank failed two days later, and
depositors pulled money out of small US banks. The Fed opened an emergency lending programme for banks.
UBS rescued Credit Suisse within two weeks, and First Republic failed in May.

```series
title: March 2023 — banks broke, credit held
from: 2023-01-01
to: 2023-06-30
rebase: 100
line: us:XLF | Financials (XLF)
line: us:SP500_TR | S&P 500 total return
line: us:HYG | High-yield bonds (HYG)
band: 2023-03-08 2023-03-17 | SVB, Signature, Credit Suisse
caption: XLF fell about 11% between 8 and 17 March; the S&P 500's worst point was only 3.4% down and HYG's about 1%. Financials kept lagging — XLF against the S&P 500 fell about 18% from January to late June.
```

The regional-bank ETF (KRE, not stored) fell much harder than XLF. The lesson:
**when one sector panics but credit stays calm, the damage stays in that sector.** Avoiding
financials while trading the leading groups worked. 2023 became a strong year
for large-cap tech.

## 7. India: system liquidity, the CRR and the NBFC crisis

### 7.1 How the RBI manages liquidity

The RBI's **Liquidity Adjustment Facility (LAF)** sets a band of rates around the
repo rate (the RBI's policy rate). Banks with spare cash deposit it with the RBI at the **Standing Deposit Facility**
rate, the bottom of the band. Banks short of cash borrow from the RBI at the **Marginal Standing Facility**
rate, the top of the band. In between, the RBI runs auctions to lend cash (repo) or take it in (reverse repo). Every day the
RBI publishes the banking system's net position. It is either a **surplus** (banks lending
money back to the RBI) or a **deficit** (banks borrowing from it).

A **surplus** keeps overnight rates near the bottom of the band, and loans are easy to get. A
**deficit** pushes overnight rates toward the top, and banks become more careful about whom they lend to.

When the RBI sells dollars to support the rupee
([currencies guide](learn-macro-currencies.md)), it takes rupees in exchange. That **removes cash from
the banking system**. Heavy selling of dollars to support the rupee around the turn of 2024–25 left banks in a
large deficit. The RBI then put cash back in by buying bonds, holding longer repo auctions,
and doing dollar-rupee swaps (buying dollars now and agreeing to sell them back later).

### 7.2 The CRR

The **cash reserve ratio** (CRR) is the share of deposits banks must keep with the
RBI, earning nothing. Cutting it immediately frees cash for banks to lend. Approximate
recent history: cut from 4% to 3% in March 2020; restored to 4% in 2021;
raised to 4.5% in May 2022 (with the first rate hike); cut back to 4% in
December 2024, and to 3% in stages through 2025. **A CRR cut is the RBI's
clearest signal that it wants more cash in the system.** Bank and NBFC shares usually react first.

### 7.3 The 2018 NBFC crisis (IL&FS)

IL&FS, a large, highly rated lender to infrastructure projects, began defaulting in
September 2018. Mutual funds then stopped lending to non-bank lenders — NBFCs (non-bank finance companies) and
housing-finance companies — that had funded long loans with short-term borrowing.
Several NBFC shares collapsed within days, and the shortage of funding lasted into 2019.

```series
title: India's 2018 credit event — midcaps lagged for a year
from: 2018-06-01
to: 2019-06-28
rebase: 100
line: india:MIDCAP | Nifty Midcap
line: india:NIFTY50 | Nifty 50
line: india:^NSEBANK | Bank Nifty
band: 2018-09-01 2018-10-26 | IL&FS defaults
caption: Midcaps fell about 18% from 31 August to 8 October 2018 and were still below their June 2018 level a year later, while the Nifty 50 and Bank Nifty (dominated by large private banks) made new highs by June 2019.
```

**A credit event sorts stocks by how strong each company's finances are.** Money moved into
large private banks and the biggest index stocks. Midcaps kept falling into August
2019, ending about 28% below their January 2018 high.

## 8. How a trader reads credit to set exposure

| Credit (HYG/IEF, HY spreads) | Stocks | Reading | Exposure |
|---|---|---|---|
| Rising / spreads tight | Rising | Healthy risk appetite | Full size on good setups |
| Falling | Still rising | **Divergence — the early warning** | Tighten stops, fewer new entries, favour quality |
| Falling | Falling | Credit stress confirmed | Mostly cash; only the very strongest setups |
| Steady | Falling | Rates or valuation correction | Reduce size, but less likely to become 2008 |
| Turning up first | Still falling | Repair starting | Build a watchlist; start small as breadth improves |

Practical habits:

1. **Read the HYG tile weekly.** Compare its 1-month change with the index's. A
   falling HYG while the index makes new highs deserves a closer look. The
   HYG/IEF ratio (charted above) is the cleaner test of it.
2. **For India** the app stores no credit gauge. Instead, watch the RBI's daily
   liquidity position, its CRR and repo decisions, and how NBFC and housing-finance
   stocks are doing against the Nifty. They are usually the first to show trouble.
3. **Combine with breadth.** Credit falling while stocks rise, together with breadth narrowing, is a far
   stronger warning than either alone.

## 9. What the evidence says

- **Robust:** credit spreads help predict future economic activity.
  The best-known modern statement is Gilchrist and Zakrajšek (2012). Wide
  spreads also coincide with poor stock returns. Plenty of central-bank
  money has coincided with rising asset prices (2009–14, 2020–21).
- **Mostly true:** credit warns before stocks *when credit problems build slowly*
  (2007, 2014–16). It does **not** move first in sudden funding panics
  (2020), and it stays quiet in bear markets caused by rising rates (2022).
- **The delays are long and uneven:** four months in 2007, over a year in
  2014–15. A falling HYG ratio is a reason to tighten up, not a tool for timing the top.
- **Folklore:** that the Fed balance sheet tracks the S&P 500 week by week.
  The direction matters over months; week to week the link is loose.
- **Limits of HYG as a stand-in:** HYG is an ETF, not the spread itself. In a panic it can trade
  below the value of the bonds it holds, and its raw price drifts down as coupons are paid out.

## 10. Checklist

- [ ] Fed: easing, on hold or tightening? Balance sheet growing or shrinking?
- [ ] RBI: system liquidity in surplus or deficit? Any CRR change?
- [ ] HYG tile: 1-month change — falling while the S&P rises?
- [ ] HYG / IEF ratio: making lower highs?
- [ ] VIX / India VIX: a short spike from calm, or holding above 20–25?
- [ ] Speculative corners (small caps, recent IPOs) leading or lagging the index?
- [ ] Banks and NBFCs: acting like a sector scare, or spreading?
- [ ] Breadth narrowing at the same time? Two warnings together → cut new risk

## Further reading

- **FRED** — `WALCL` (Fed total assets) and `BAMLH0A0HYM2` (US high-yield spread).
- **Federal Reserve**, the H.4.1 release — the weekly balance sheet.
- **Reserve Bank of India** — the daily money-market operations press release
  (system liquidity) and the monetary policy statements (repo, CRR).
- Martin Zweig, *Winning on Wall Street* — "don't fight the Fed" and its indicators.
- Simon Gilchrist and Egon Zakrajšek, "Credit Spreads and Business Cycle
  Fluctuations", *American Economic Review* (2012).
