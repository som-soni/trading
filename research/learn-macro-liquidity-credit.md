# Liquidity and credit — the tide under every chart

Learning material: what "liquidity" means, how QE and QT add and drain it,
the 2020 flood and the 2021 speculative peak, why credit often warns before
stocks, the VIX and funding stress, bank scares, India's system liquidity and
its 2018 NBFC crisis — and how a trader reads it all to set exposure. Companion to
[the interest-rates guide](learn-macro-rates.md) (the *price* of money; this is
its quantity) and [the currencies guide](learn-macro-currencies.md).

**Where this shows in the app.** The US macro strip on Markets → Breadth
(`scripts/swing_screener/marketdata/macro.py`) ends with **HY credit (HYG)**:
1-day and 1-month change, a 3-month sparkline, and the hover line *"Credit risk
appetite: HYG falling while stocks rise is an early warning."* The VIX is not
on the strip; the same page's **"Options: expected vs actual?"** card compares it
(India VIX for India) with how much the index has actually been moving. The
screener uses it too: above 25 (US) or India VIX above 20,
the regime is flagged high-volatility and sizing halves risk per trade from 1%
to 0.5% (`core/regime.py`, `core/sizing.py`, each market's config).

---

## 1. What "liquidity" means

Three different things, which move together in a crisis:

| Meaning | What it is | How you see it |
|---|---|---|
| **Market liquidity** | Can you trade size without moving the price? | Bid-ask spreads, gaps, how fast a stock falls on modest selling |
| **Funding liquidity** | Can banks, funds and companies borrow and roll over debt? | Money-market rates, credit spreads, the dollar |
| **Monetary liquidity** | How much money the central bank and banks have created | The Fed's and RBI's balance sheets, bank reserves, system surplus/deficit |

**The trader's version: liquidity is how much money is looking for a home,
and how easily it can be borrowed.** When it is abundant, almost any story
gets bought and dips are shallow. When it drains, the weakest stories go
first, then everything else is sold to raise cash.

## 2. Central-bank balance sheets: QE and QT

### 2.1 The mechanics

**Quantitative easing (QE):** the central bank buys government (and in the US,
mortgage) bonds with newly created reserves — yields fall, the sellers move
into riskier assets, and banks fill with cash. **Quantitative tightening (QT)**
reverses it: bonds mature without replacement, draining reserves.

### 2.2 The US record (approximate; not stored in the app)

| Period | What the Fed did | Balance sheet, roughly |
|---|---|---|
| 2008–2014 | QE1 (2008–10), QE2 (2010–11), QE3 (2012–14) | about $0.9 trillion → about $4.5 trillion |
| 2017–2019 | First QT, ended in 2019 after the September repo-market spike | about $4.5 trillion → under $4 trillion |
| 2020–2022 | Pandemic QE, "unlimited" from 23 March 2020, tapered from late 2021, ended March 2022 | about $4 trillion → about $9 trillion |
| 2022– | Second QT from June 2022, slowed in 2024–25 | drifting down |

The Fed publishes it weekly (H.4.1; FRED `WALCL`). The RBI also trades
government bonds (open-market operations), never on the Fed's scale.

### 2.3 "Don't fight the Fed"

Martin Zweig's line: when the Fed is easing, stay long; when it tightens hard,
be careful. It describes the **wind**, not the weather — QE years were mostly
good for stocks, 2022 was not. But the Fed eases *because* something is
breaking: in 2008 and 2020 stocks kept falling after the first emergency cuts. **Easing into a crash is not a buy signal; easing after
the crash has been absorbed usually is.**

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

The Fed bought bonds, the government sent cheques, rates sat at zero, and the
riskiest corners went furthest: small caps, unprofitable tech, SPACs, meme
stocks, crypto. Two lessons:

- **The most speculative assets peak first.** The Russell 2000 peaked on
  8 November 2021, about seven weeks before the Nasdaq 100 (27 December),
  and the most speculative growth stocks peaked well before both. When the
  froth starts failing while the indexes still rise, liquidity is leaving.
- **Watch participation.** Late 2021's index highs were widely noted to rest
  on fewer and fewer stocks — the kind of divergence Markets → Breadth shows.

## 4. Credit — why bonds often warn before stocks

### 4.1 The credit spread

A **credit spread** is the extra yield a risky borrower pays over the
government. High-yield ("junk") spreads are the most sensitive: nervous lenders
demand more, spreads widen, junk-bond prices fall. The ICE BofA US High Yield
spread (on FRED) has ranged from around 3 percentage points in calm years to
near 20 at the end of 2008 and above 10 in March 2020 (approximate).

### 4.2 Why credit leads

- **Bondholders only worry about the downside** — at best they get their money
  back — so they notice weakening balance sheets first.
- **Credit is funding.** Wider spreads stop weaker companies refinancing, so
  they cause the trouble they predict.
- **Institutions reprice gradually**, so the move starts earlier and quieter
  than in stocks.

### 4.3 HYG — the stored proxy

The app stores **HYG** (the iShares high-yield bond ETF) as a raw daily close
since 2007. Two cautions. The raw close leaves out the coupons paid, so HYG
(and any ratio built on it) drifts down over years — **read it over weeks and
months**. And HYG also falls when Treasury yields rise, which is not credit
stress. Dividing by a Treasury fund strips most of that out: `us:HYG / us:BONDS`
(IEF, 7–10 year Treasuries) is a rough **credit risk-appetite gauge**.

```series
title: Credit rolled over months before stocks, 2007–2009
from: 2007-04-11
to: 2009-12-31
line: us:SP500_TR | S&P 500 total return | log
line: us:HYG | High-yield bonds (HYG) | right
line: us:HYG / us:BONDS | HYG / Treasuries (IEF) | pane2
band: 2007-06-07 2007-10-09 | Credit falling, stocks still rising
mark: 2007-10-09 | S&P peak
caption: HYG against Treasuries peaked on 7 June 2007; the S&P 500 kept rising until 9 October. Peak to the March 2009 low the ratio fell about 53%, HYG about 42% and the S&P 500 about 55%.
```

The same warning came in **2014–16**: HYG/IEF peaked in June 2014 as oil
began to collapse and energy borrowers struggled, and fell about 29% by
February 2016. The S&P 500 kept rising for another year, peaked in July 2015,
then dropped about 13% into February 2016 — the same day the credit ratio
bottomed. And in **2021**, HYG's price peaked on 15 September while the S&P
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
at once; the ratio did not lead. It turned when the Fed announced, on 23
March 2020, that it would buy corporate bonds — later including high-yield
ETFs. Credit and stocks bottomed together, that same day.

**2022 is the honest counter-example.** HYG's *price* fell about 18% to
September, which looked alarming, but most of that was rising Treasury yields.
Against Treasuries the ratio dipped about 9% from April to July and ended
the year only about 1% lower. The S&P 500's 25% fall was driven by rates and valuations, and
credit stress never spread. **When stocks fall but credit holds, the damage is
usually more contained** than in a true credit bear market like 2008.

## 5. The VIX and funding stress

The VIX prices 30-day S&P 500 options — what protection costs. It spikes when
everyone wants insurance at once, just as dealers and leveraged funds cut risk.

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

- **Short spikes from calm are positioning, not a regime.** On 5 August 2024
  the VIX closed at 38.6 (much higher intraday) as a crowded yen-funded carry
  trade unwound; two weeks later it was down about 60%. February 2018 was
  similar: the collapse of short-volatility products, not of the economy.
- **A VIX that stays high is a regime.** After March 2020 it did not close
  below 20 for the rest of the year. In 2022 it peaked only at 36.5 but closed
  above 20 in 47 of 52 weeks — a grinding bear market, not a panic.
- **India VIX** behaves the same way: its stored high is 83.6 on 24 March
  2020; the June 2024 election-result day took it to 26.8.

**Trader's read:** after a spike from calm, stop buying breakouts for a few
days and let the market show whether it was positioning or something real. A
VIX holding above the threshold (25 for the US) is when the app halves risk.

## 6. Bank stress — March 2023

On 10 March 2023 Silicon Valley Bank failed, Signature Bank two days later, and
depositors fled small US banks. The Fed opened an emergency lending facility,
UBS rescued Credit Suisse within the fortnight, and First Republic failed in May.

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
**a sector scare with calm credit stays in its sector** — stepping aside from
financials while trading the leading groups worked; 2023 became a strong year
for large-cap tech.

## 7. India: system liquidity, the CRR and the NBFC crisis

### 7.1 How the RBI manages liquidity

The RBI's **Liquidity Adjustment Facility (LAF)** sets a corridor around the
repo rate: banks with surplus cash park it at the **Standing Deposit Facility**
(the floor), banks short of cash borrow at the **Marginal Standing Facility**
(the ceiling), and the RBI runs repo and reverse-repo auctions in between. The
RBI publishes the system's net position daily — a **surplus** (banks lending
money back to the RBI) or a **deficit** (banks borrowing from it).

A **surplus** keeps overnight rates near the floor and credit easy; a
**deficit** pushes them toward the ceiling, and banks get choosier.

When the RBI sells dollars to support the rupee
([currencies guide](learn-macro-currencies.md)) it absorbs rupees — **draining
liquidity**. Heavy rupee defence around the turn of 2024–25 left banks in a
large deficit; the RBI injected cash via bond purchases, longer repo auctions
and dollar-rupee swaps.

### 7.2 The CRR

The **cash reserve ratio** is the share of deposits banks must hold with the
RBI, earning nothing. Cutting it frees cash for lending at once. Approximate
recent history: cut from 4% to 3% in March 2020; restored to 4% in 2021;
raised to 4.5% in May 2022 (with the first rate hike); cut back to 4% in
December 2024 and to 3% in stages through 2025. **A CRR cut is the RBI's
loudest liquidity signal** — banks and NBFCs usually react first.

### 7.3 The 2018 NBFC crisis (IL&FS)

IL&FS, a large, highly rated infrastructure lender, began defaulting in
September 2018. Mutual funds stopped lending to non-bank lenders (NBFCs and
housing-finance companies) that funded long loans with short-term borrowing;
several NBFC shares collapsed within days, and the squeeze lasted into 2019.

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

**A credit event sorts the market by balance-sheet strength:** money fled to
large private banks and index heavyweights. Midcaps kept falling into August
2019, about 28% below their January 2018 high.

## 8. How a trader reads credit to set exposure

| Credit (HYG/IEF, HY spreads) | Stocks | Reading | Exposure |
|---|---|---|---|
| Rising / spreads tight | Rising | Healthy risk appetite | Full size on good setups |
| Falling | Still rising | **Divergence — the early warning** | Tighten stops, fewer new entries, favour quality |
| Falling | Falling | Credit stress confirmed | Mostly cash; only the very strongest setups |
| Steady | Falling | Rates or valuation correction | Reduce size, but less likely to become 2008 |
| Turning up first | Still falling | Repair starting | Build a watchlist; start small as breadth improves |

Practical habits:

1. **Read the HYG tile weekly** — its 1-month change against the index's; a
   falling HYG while the index makes highs deserves a closer look, and the
   HYG/IEF ratio (charted above) is the cleaner test of it.
2. **For India** there is no stored credit gauge: watch the RBI's daily
   liquidity position, CRR and repo decisions, and NBFC and housing-finance
   stocks against the Nifty — they are the canaries.
3. **Combine with breadth.** Credit divergence plus narrowing breadth is a far
   stronger warning than either alone.

## 9. What the evidence says

- **Robust:** credit spreads carry information about future economic activity
  — the best-known modern statement is Gilchrist and Zakrajšek (2012) — and
  wide spreads coincide with poor stock returns. Abundant central-bank
  liquidity has coincided with rising asset prices (2009–14, 2020–21).
- **Mostly true:** credit warns before stocks *in slow-building credit
  cycles* (2007, 2014–16). It does **not** lead in sudden funding panics
  (2020) and stays quiet in rate-driven bear markets (2022).
- **Lags are long and uneven:** four months in 2007, over a year in
  2014–15. A falling HYG ratio is a reason to tighten, not a timing tool.
- **Folklore:** that the Fed balance sheet maps week by week onto the S&P 500.
  The direction matters over months; week to week the link is loose.
- **Proxy limits:** HYG is an ETF, not the spread; in a panic it can trade
  below its bonds' value, and its raw price drifts down with coupons paid.

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
