# Valuation for traders — why leaders look expensive, and when the price tag matters

Learning material. This guide covers:

- P/E (trailing against forward), earnings yield, PEG, EV/EBITDA, price/sales
  and price/book;
- why big winners look expensive when they start;
- the two sources of return — earnings growth and the multiple — measured on
  real cases;
- when valuation matters; sector norms; India's higher multiples.

It is the second of three Fundamentals guides. It comes after
[earnings that move stocks](learn-fund-earnings.md) and before
[quality and the growth checklist](learn-fund-quality.md).

**Where this shows in the app.** Chart → **Fundamentals** (built by
`fundamentals/company.py`) shows **Stock P/E**: the price ÷ the EPS of the last
twelve months. It is blank when that EPS is not positive. The page also shows
*Book value*, *Dividend yield*, *Market cap*, *Sales (TTM)* and a table of
peers with their P/E. Screens → **Quality** (`fundamentals/quality.py`) values
a company three ways: free-cash-flow yield, P/E against its own median, and
PEG. It also shows *Net debt/EBITDA*. **No screen, strategy or backtest uses
valuation as a filter.** (In backtest run names, `pe…` means *progressive
exposure*, not P/E.) The P/E lines on the charts here (`fund.SYMBOL.pe`) divide
each day's close by the trailing EPS known that day.

---

## 1. P/E — the price of one rupee or dollar of profit

**P/E = share price ÷ earnings per share.** At a P/E of 25, buyers pay 25 years
of today's profit. If profit grows, it takes fewer years to earn that back.

| Version | EPS used | Where you find it |
|---|---|---|
| **Trailing (TTM)** | The last four reported quarters | Fundamentals page, the `fund.X.pe` charts |
| **Forward** | Analysts' estimate for the next 12 months | **Not stored in this app** — brokers and data sites quote it |
| **Shiller / CAPE** | 10-year average of inflation-adjusted earnings | Market-level only; not stored |

The app's EPS is the **reported, diluted EPS from the filings** (SEC and NSE
data). It is not the "adjusted" EPS that companies put in their headlines. Each
quarter counts only from its filing date, so a past P/E uses only what was
known then. Three consequences:

- **One-off charges distort it.** Stored trailing P/E reached about 1,195 for
  AMD (end-2023) and 189 for Broadcom (end-2024). Charges from acquisitions
  had crushed their reported EPS. When a P/E looks crazy, look at the EPS line
  first.
- **It lags fast growers.** Dividing today's price by last year's profit makes
  a company about to double its earnings look more expensive than it is
  (NVIDIA, section 4).
- **Data caveat:** for a few stored companies, EPS was not adjusted for a
  share split. Their P/E reads about 1–2 on some dates. The studies below drop
  entry P/Es under 4.

## 2. Earnings yield — P/E turned upside down

**Earnings yield = 1 / P/E.** It is 4% at a P/E of 25, and 10% at a P/E of 10.
This makes a stock comparable with a bond. If the 10-year bond pays 4–5%, a 4%
earnings yield pays little for the extra risk of owning a stock. If the bond
pays 1.5%, the same 4% looks generous. That is why rising bond yields push
P/Es down. The arithmetic (discounting, duration, and the extra return
investors demand for holding stocks — the equity risk premium) is in
[the interest-rates guide](learn-macro-rates.md). **Interest rates limit how
high a P/E the market will pay. Earnings decide which stocks get paid.**

## 3. The other yardsticks — and which ones the app has

| Measure | Formula | Good for | In this app |
|---|---|---|---|
| **PEG** | P/E ÷ EPS growth rate (%) | Comparing growers: P/E 40 growing 40% = PEG 1 | Quality page: P/E ÷ annual EPS CAGR over the statement years (cheap ≤ 1, fair ≤ 1.5) |
| **EV/EBITDA** | (market cap + net debt) ÷ EBITDA | Comparing companies with different debt loads; takeovers | **Not computed.** The Quality page shows *Net debt/EBITDA*, a leverage measure, not a valuation |
| **Price/sales** | market cap ÷ revenue | Companies with no profit yet; cyclicals at a trough | **Not computed.** Divide *Market cap* by *Sales (TTM)* on the Fundamentals page yourself |
| **Price/book** | price ÷ book value per share | Banks, insurers, asset-heavy firms | **Not computed as a ratio.** The Fundamentals page shows *Book value* per share; divide the price by it |
| **FCF yield** | free cash flow ÷ market cap | Cash-generating businesses | Quality page (cheap ≥ 5%, fair ≥ 3%; not used for banks) |
| **Dividend yield** | dividends ÷ price | Income stocks | Fundamentals page |

(EBITDA is profit before interest, tax, depreciation and amortisation. EV,
enterprise value, is market cap plus net debt.) PEG uses **past** growth, but
the price reflects expected **future** growth. So a low PEG on a company whose
growth is slowing is not cheap. Price/book suits banks. It means little for
software, whose assets are people and code.

## 4. Why leaders look expensive

The stocks that go on to double and triple usually start with P/Es the
textbook calls "expensive". The reason: **the market sets the price on the
earnings it can see coming, not the ones already reported**. When the growth
arrives, the P/E falls while the price keeps rising.

```series
title: NVIDIA 2022–2024 — the price rose ninefold while the P/E fell
from: 2022-10-01
to: 2024-12-31
tf: W
line: us:NVDA | NVIDIA (split-adjusted) | log
line: us:fund.NVDA.pe | Trailing P/E | pane2
mark: 2023-05-25 | guidance gap
caption: At the end of 2022, NVIDIA traded at 62× trailing earnings. The May 2023 guidance gap pushed the trailing P/E above 200 (peak 248 in July), because the price moved before the earnings had been reported. Then the earnings arrived. By September 2024 the P/E was 48, below where the rally began.
```

Closes and the trailing EPS known on each date:

| NVIDIA | Price | Trailing EPS | Trailing P/E |
|---|---|---|---|
| 30 Dec 2022 | 14.61 | 0.236 | 62.0 |
| 24 May 2023 (day before the gap) | 30.54 | 0.173 | 176 |
| 29 Dec 2023 | 49.52 | 0.757 | 65.4 |
| 31 Dec 2024 | 134.29 | 2.541 | 52.9 |
| **Two-year change** | **×9.2** | **×10.8** | **×0.85** |

**All of the gain came from earnings; the P/E multiple shrank.** Avoiding the
stock at 62×, or above 100× (late February to November 2023), meant judging
it by last year's profit — when it was about to earn ten times as much.

### The app's own big winners

The app's US Donchian breakout backtest (`v1.1-69e24dab`, 506 trades,
2013–2026, with trading costs modelled) made most of its result from a few long
holds. Here are its largest winners, with the P/E on the entry and exit days
(changes computed from daily closes):

| Trade | R | P/E at entry → exit | Price | EPS | P/E |
|---|---|---|---|---|---|
| NVDA, May 2016 → Oct 2018 | +53 | 39 → 34 | ×5.6 | ×6.3 | ×0.88 |
| SFM (Sprouts), Oct 2023 → Jul 2025 | +42 | 17 → 31 | ×3.7 | ×2.0 | ×1.8 |
| ANET, Sep 2016 → Oct 2018 | +26 | 43 → 94 | ×2.9 | ×1.3* | ×2.2 |
| ADBE, May 2017 → Oct 2018 | +21 | 52 → 49 | ×1.8 | ×1.9 | ×0.95 |

\*Arista's 2018 EPS was depressed by one-off charges. Three of the four
started at 39–52×. The median P/E of stored US stocks was 21–23 on those
dates. Sprouts was a cheap stock whose P/E rose as its growth sped up (a
"re-rating"). (The NVIDIA trade is charted in
[the stops guide](learn-risk-stops-exits.md).) O'Neil reported the same of
past big winners: they began above the market's P/E, and their P/E then rose.

### Does P/E at entry predict the trade? Not in this app's backtests

Every trade of two current-version US runs, by trailing P/E on entry day:

| Entry P/E | Minervini v1.6 (2010–2026): trades / win % / avg R | Donchian v1.1 (2013–2026): trades / win % / avg R |
|---|---|---|
| under 20 | 119 / 27% / +0.12 | 98 / 28% / +0.63 |
| 20–35 | 145 / 25% / −0.09 | 97 / 29% / +0.01 |
| 35–60 | 91 / 27% / +0.10 | 43 / 26% / +1.86 (+0.63 without its top trade) |
| over 60 | 69 / 32% / −0.02 | 43 / 37% / +0.47 |
| no P/E (loss-making or not covered) | 121 / 31% / +0.06 | 221 / 29% / +0.38 |

Minervini `v1.6-39a21ebf`: 557 trades, 424 with a usable P/E (median 29).
Donchian: 506 trades, 281 usable (median 25). The rank correlation of entry
P/E with R was −0.04 and +0.01: **no relationship**. Trades bought above 60×
won as often as those bought below 20×. The samples are small and dominated by
a few outliers. Read this as "no evidence that P/E helps", not as proof that it
never does.

## 5. The two sources of return

**Price change = EPS change × P/E change.** A stock rises because earnings
grow, or because buyers pay more for each unit of earnings (a re-rating), or
both. Stored cases:

| Case | Period | Price | EPS | P/E | Driven by |
|---|---|---|---|---|---|
| NVIDIA | end-2022 → end-2024 | ×9.2 | ×10.8 | 62 → 53 (×0.85) | Earnings |
| Celsius (CELH) | Jun 2022 → Dec 2023 | ×2.5 | ×11.9 | 512 → 108 (×0.21) | Earnings caught up with the price |
| Microsoft | Jun 2019 → Dec 2021 | ×2.5 | ×2.0 | 30 → 38 (×1.26) | Mostly earnings |
| Apple | end-2018 → end-2021 | ×4.5 | ×1.9 | 13 → 32 (×2.4) | Mostly re-rating |
| Meta | 3 Nov 2022 → end-2023 | ×4.0 | ×1.08 | 8.5 → 31 (×3.7) | Re-rating from a panic low |
| Super Micro (SMCI) | end-2022 → 13 Mar 2024 | ×14.5 | ×1.6 | 10 → 93 (×9.2) | Re-rating |
| HAL (India) | Mar 2023 → Jun 2024 | ×3.9 | ×1.25 | 15 → 46 (×3.1) | Re-rating |
| Trent (India) | end-2022 → Sep 2024 | ×5.8 | ×4.7 | 198 → 245 (×1.24) | Mostly earnings |

**Earnings-driven gains are durable.** The P/E can shrink and the stock still
holds its price. **Re-rating gains depend on growth that has not happened
yet.** They reverse fast when that growth does not arrive (SMCI, section 7).

## 6. Cheap stocks that stayed cheap

A low P/E is often low for a reason: earnings about to fall, a shrinking
business, or debt. Stocks that look cheap and stay cheap are called *value
traps*:

```series
title: Verizon 2019–2023 — cheap, then cheaper
from: 2019-06-01
to: 2023-12-31
tf: W
line: us:VZ | Verizon
line: us:fund.VZ.pe | Trailing P/E | pane2
caption: At the end of 2019 Verizon traded at about 16× earnings. Its EPS then rose 28%, but the P/E halved to 7.6 and the price fell from 61.40 to 37.70. A low P/E is not a floor (price only; the dividend made up part of the loss).
```

- **Intel**, end-2019 → June 2024: "cheap" at 14×. Then EPS fell to a quarter
  of its level and the price halved (59.85 → 30.97). The trailing P/E *rose*
  to 32.
- **Adobe**, end-2021 → Oct 2026: EPS +47%, P/E 47 → 13, price 567 → 236. The
  whole sector's P/Es fell (a de-rating). "Cheapest ever" was true most of the
  way down.

Over those periods, Verizon and Adobe closed below their 200-day average on
about three days in four, Intel on more than half. **A cheap stock without an
uptrend gives you nothing to trade.**

## 7. When valuation does matter

### 7.1 At the market level: 2022

In 2022 the US 10-year yield went from 1.5% to 3.9% (with a 4.2% peak in
October). P/Es fell almost everywhere. Across ~950–970 profitable US companies
with stored filings, the **median trailing P/E fell from 25.5 to 20.0**. The
share of companies above 50× fell from 21% to 12%.

```series
title: Microsoft in 2022 — earnings up, price down
from: 2021-06-01
to: 2023-06-30
tf: W
line: us:MSFT | Microsoft | log
line: us:fund.MSFT.pe | Trailing P/E | pane2
line: us:US10Y | US 10-year yield (%) | right
caption: Microsoft's EPS grew 4% in 2022, but its P/E fell from 38 to 26 as the 10-year more than doubled, and the stock lost 29%. The multiple bottomed at 23 on 3 Nov 2022, the stock's low.
```

In 2022 Adobe's price went ×0.59 (EPS ×0.84, P/E 47 → 33). NVIDIA's went ×0.50
(EPS ×0.73, P/E 91 → 62). Meanwhile JPMorgan's P/E *rose* from 10.1 to 11.4.
High-P/E stocks lost most. That is the duration effect explained in
[the rates guide](learn-macro-rates.md): the further in the future a company's
profits lie, the more a rise in rates cuts their value today. A rate shock is a
problem for the whole market. It shows first in the market's trend and breadth
([learn-health-trend](learn-health-trend.md)). The fix is to hold less in the
market, not to hunt for low P/Es.

### 7.2 Late in a run: extreme multiples

```series
title: Super Micro 2022–2024 — from 10× to 93× and back
from: 2022-07-01
to: 2024-12-31
tf: W
line: us:SMCI | Super Micro Computer | log
line: us:fund.SMCI.pe | Trailing P/E | pane2
mark: 2024-03-13 | peak, P/E 93
caption: A ×14.5 move, about ninefold of it from re-rating. From the March 2024 peak the stock fell 85% by November while trailing EPS kept rising, and the P/E went back to 17.
```

A P/E that has risen several times over is not a sell signal. (NVIDIA spent
most of 2023 above 100× and kept rising.) But it measures **fragility**.
Nothing in the valuation holds the price up, so any disappointment cuts the
price at once. Tighten the stop. Sell part of the position into very fast,
steep run-ups. Expect gaps ([learn-risk-stops-exits](learn-risk-stops-exits.md)).

**Mean-reversion and value approaches** are where valuation earns its place.
If you buy weakness, expecting the price to bounce back, you need a fair value
for it to return *to*. The Quality page's BUY ZONE is built that way. It needs
high quality, a valuation that scores as attractive, and a pullback. It never
buys a stock in free fall (more than 15% below the 200-day).

## 8. Sector norms — compare within a group

Median stored trailing P/E of seven US banks (JPM, BAC, WFC, GS, MS, USB,
PNC) against eight software companies (MSFT, ADBE, CRM, ORCL, INTU, ADSK,
CDNS, SNPS):

| Year-end | Banks | Software |
|---|---|---|
| 2015 | 13 | 51 |
| 2018 | 11 | 46 |
| 2021 | 11 | 61 |
| 2022 | 11 | 54 |
| 2024 | 16 | 48 |
| Oct 2026 | 12.5 | 26 |

Banks earn their profit from borrowed money, and their profits rise and fall
with the economy. They are valued on book value and trade at P/Es in the low
teens. Software has high margins, recurring revenue and needs little capital,
so it usually trades at several times that. A bank at 18× is expensive;
software at 25× may be cheap.

The software median halved in 2025–26 (Adobe at 13×). That is a sector
de-rating. It showed on Markets → **Sectors** as weak group strength long
before it looked like "cheapness". Cyclical companies are the opposite trap:
**their P/E is lowest when their earnings peak**
([learn-macro-cycle](learn-macro-cycle.md), [learn-sectors-groups](learn-sectors-groups.md)).

## 9. India — higher multiples as the norm

Indian stocks have long traded at higher P/Es than most markets. Over the past
decade, the Nifty 50's trailing P/E (published daily by NSE) was mostly in the
low-to-mid 20s. Mid- and small-caps were higher. The reasons:

- higher nominal growth;
- steady monthly SIP money from Indian savers;
- high return on equity (ROE) at the leading companies;
- few large listed growth companies to choose from.

The premium widens and narrows as money flows in and out (approximate; check
NSE). Median trailing P/E of profitable companies with stored filings (for
India, the ~390 most-traded stocks, with P/E from mid-2022):

| Date | India (covered) | US (covered) |
|---|---|---|
| 30 Jun 2023 | 32 (n=265) | 22 (n=971) |
| 27 Sep 2024 | 43 (n=314) | 25 (n=1,048) |
| 28 Mar 2025 | 34 (n=327) | 22.5 (n=1,069) |
| 13 Oct 2026 | 36 (n=364) | 23 (n=1,205) |

This is an illustration, not an index: the Indian set is small and leans to
popular names. But it matches the market. At the September 2024 peak, 43% of
covered Indian companies were above 50×. The fall to March 2025 matches the
Nifty's 16% drawdown over that time.

```series
title: Indian IT de-rates — TCS and Infosys P/E, 2023–2026
from: 2023-01-01
line: india:fund.TCS.NS.pe | TCS trailing P/E
line: india:fund.INFY.NS.pe | Infosys trailing P/E
caption: Both earned more in 2026 than in 2024 (EPS +11% and +14%), yet their P/Es halved, from 33 and 29 to about 16 and 14, and the shares fell by roughly 45%. A sector re-rating, the same pattern as US software.
```

Sector norms hold in India too. In September 2024 the P/Es were: HDFC Bank 20,
ICICI Bank 21, SBI 11, against TCS 33, DMart 125, Dixon 188, Trent 245.
Government-owned (PSU) banks and energy companies sit low (Coal India about 5×
at end-2022). Consumer and retail companies sit high. Re-ratings run both
ways: Trent fell 62% from September 2024 to October 2026 as its P/E halved.
(Its stored trailing EPS also fell — check the filings.)

## 10. What the trader does with valuation

1. **Time entries with growth and price action**: trend, relative strength,
   base, breakout, accelerating earnings ([learn-fund-earnings](learn-fund-earnings.md)).
   That is what the app's strategies do; none of them filters on valuation.
2. **Do not avoid or short a leader for a high P/E alone.** Every big winner
   in section 4 looked expensive. Short a broken chart, not a high P/E.
3. **Valuation is context and a risk flag.** Suppose the P/E has tripled in a
   year, or sits far above its own history while growth slows. Then use a
   smaller size, a tighter trailing stop, and sell into strength. Do not sell
   before the chart breaks.
4. **Check the EPS before trusting the P/E** (one-offs, split errors).
5. **Compare within the peer group** (the Fundamentals page's peers table). A
   leader at twice its peers' P/E should be growing much faster.
6. **When rates jump, hold less** in high-P/E stocks ([learn-macro-rates](learn-macro-rates.md)).
7. **For long-term or buy-the-dip money, valuation comes first** — use the
   Quality page.

## 11. What the evidence says

- **Robust:** over decades, cheap stocks (low P/B or P/E) beat expensive ones
  on average (the Fama–French value premium). But slowly, with a long dry
  spell after 2007, and it says nothing about when to enter a swing trade.
- **Robust:** the market's starting valuation predicts its 10-year return far
  better than next year's (Shiller's CAPE). So it is a poor timing tool.
- **Here:** entry P/E did not separate winning from losing backtest trades.
  The largest winners started at 17–52×.
- **Folklore:** "a high P/E must fall", "a low P/E can't fall much".
- **Lags:** trailing P/E makes fast growers look too expensive and cyclicals
  at the peak look too cheap. One-off charges break it. Forward P/E rests on
  estimates not stored here.

## 12. Checklist

- [ ] Leaders held: P/E against their own history and peers — is growth fast enough to bring it down?
- [ ] P/E up several-fold in a year? Tighten stops, sell part of the position
- [ ] Extreme P/E (over 200, under 3): check the EPS line for one-offs or split errors
- [ ] Low-P/E idea: Stage 2 uptrend, or a value trap under a falling 200-day?
- [ ] 10-year yield rising fast: smaller size on high-multiple breakouts; cyclicals at record earnings are late-cycle

## Further reading

- William J. O'Neil, *How to Make Money in Stocks* — P/Es of past big winners.
- Mark Minervini, *Trade Like a Stock Market Wizard* — growth over valuation.
- Aswath Damodaran, *Investment Valuation*; his NYU Stern data on sector multiples.
- Peter Lynch, *One Up on Wall Street* — PEG and fair P/Es for growers.
- Benjamin Graham, *The Intelligent Investor* — the value investor's case.
- Fama and French, "The Cross-Section of Expected Stock Returns", *Journal of Finance* (1992).
- Robert Shiller, *Irrational Exuberance*, and his CAPE data (Yale).
- NSE Indices (niftyindices.com) — daily P/E, P/B and dividend yield of the Nifty indices.
