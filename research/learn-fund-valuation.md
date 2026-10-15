# Valuation for traders — why leaders look expensive, and when the price tag matters

**In short**

- P/E is the price of one rupee or dollar of yearly profit. Trailing P/E uses last year's profit, so it makes fast growers look expensive.
- A stock's return has two sources: growth in earnings and a change in the P/E. Gains from earnings last; gains from a rising P/E can reverse fast.
- Big winners rarely look cheap when they start. Among US uptrend stocks since 2010, the P/E at a month end said nothing about the next three months.
- Valuation matters at the market level (rate shocks hit high-P/E stocks hardest), late in a run (extreme multiples are fragile), and for buy-the-dip or long-term money.
- Compare a P/E with the company's peers and its own history, never with a single "fair" number.

This guide covers P/E (trailing and forward), earnings yield, PEG, EV/EBITDA, price/sales and price/book. It shows why big winners look expensive when they start, and splits real returns into earnings growth and a change in the multiple. It ends with when valuation matters, sector norms and India's higher multiples.

It is the second of three fundamentals guides. It comes after [earnings that move stocks](learn-fund-earnings.md) and before [quality and the growth checklist](learn-fund-quality.md).

---

## 1. P/E — the price of one rupee or dollar of profit

Suppose a share costs ₹500 and the company earned ₹20 per share over the last year. Its P/E is 25. Buyers are paying 25 years of today's profit. If profit grows, it takes fewer years to earn that back.

**P/E = share price ÷ earnings per share.** There are three common versions:

| Version | EPS used | Where you find it |
|---|---|---|
| **Trailing (TTM)** | The last four reported quarters | Computed from filings; quoted everywhere |
| **Forward** | Analysts' estimate for the next 12 months | Brokers and data sites |
| **Shiller / CAPE** | 10-year average of inflation-adjusted earnings | Market level only; Shiller's published data |

The P/E figures in this guide use the **reported, diluted EPS from the filings** (SEC and NSE data). They do not use the "adjusted" EPS that companies put in their headlines. Each quarter counts only from its filing date, so a past P/E uses only what was known then. Three consequences:

- **One-off charges distort it.** Trailing P/E reached about 1,195 for AMD (end-2023) and 189 for Broadcom (end-2024). Charges from acquisitions had crushed their reported EPS. When a P/E looks crazy, look at the EPS line first.
- **It lags fast growers.** Dividing today's price by last year's profit makes a company about to double its earnings look more expensive than it is (NVIDIA, section 4).
- **Data errors:** for a few companies in the data, EPS was not adjusted for a share split. Their P/E reads about 1–2 on some dates. The studies below drop P/Es under 4.

## 2. Earnings yield — P/E turned upside down

At a P/E of 25, each share earns 4% of its price a year. At a P/E of 10, it earns 10%. That percentage is the **earnings yield**, which is 1 ÷ P/E.

It makes a stock comparable with a bond. Suppose the 10-year bond pays 4–5%. Then a 4% earnings yield pays little for the extra risk of owning a stock. If the bond pays 1.5%, the same 4% looks generous. That is why rising bond yields push P/Es down.

The arithmetic is in [the interest-rates guide](learn-macro-rates.md). It covers discounting, duration, and the extra return investors demand for holding stocks (the equity risk premium). **Interest rates limit how high a P/E the market will pay. Earnings decide which stocks get paid.**

## 3. The other yardsticks

| Measure | Formula | Good for | Notes |
|---|---|---|---|
| **PEG** | P/E ÷ EPS growth rate (%) | Comparing growers: P/E 40 growing 40% = PEG 1 | A common reading: cheap at 1 or below, fair up to 1.5 |
| **EV/EBITDA** | (market cap + net debt) ÷ EBITDA | Companies with different debt loads; takeovers | Not the same as net debt ÷ EBITDA, which measures leverage |
| **Price/sales** | market cap ÷ revenue | Companies with no profit yet; cyclicals at a trough | Market cap ÷ trailing twelve months' sales |
| **Price/book** | price ÷ book value per share | Banks, insurers, asset-heavy firms | Means little for software |
| **FCF yield** | free cash flow ÷ market cap | Cash-generating businesses | A common reading: cheap at 5% or more, fair at 3%; not for banks |
| **Dividend yield** | dividends ÷ price | Income stocks | |

**EBITDA** is profit before interest, tax, depreciation and amortisation. **EV**, enterprise value, is market cap plus net debt.

PEG uses **past** growth, but the price reflects expected **future** growth. So a low PEG on a company whose growth is slowing is not cheap. Price/book suits banks. It means little for software, whose assets are people and code.

## 4. Why leaders look expensive

At the end of 2022, NVIDIA traded at 62 times its trailing earnings. Two years later the stock was up more than ninefold, and its P/E was *lower*.

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

**All of the gain came from earnings; the P/E multiple shrank.** Avoiding the stock at 62×, or above 100× (late February to November 2023), meant judging it by last year's profit. The company was about to earn ten times as much.

The general point: **the market sets the price on the earnings it can see coming, not the ones already reported**. When the growth arrives, the P/E falls while the price keeps rising. O'Neil reported the same of past big winners: they began above the market's P/E, and their P/E then rose.

### Where the biggest winners started

**Method.** US stocks with filings, at each year end from 2010 to 2024. Each stock's trailing P/E on that day is set against its price change over the next 252 sessions (about a year). A "big winner" is a stock in that year's top 5% of gainers. The sample is 17,341 stock-years in 1,419 companies. The median big winner rose 127%.

| Starting trailing P/E | Stock-years | Became a big winner (top 5%) | Became a big loser (bottom 5%) |
|---|---|---|---|
| under 20 | 5,496 | 2.4% | 3.0% |
| 20–35 | 3,821 | 1.8% | 2.1% |
| 35–60 | 1,639 | 2.5% | 3.3% |
| over 60 | 1,323 | 4.9% | 5.7% |
| no P/E (no positive trailing earnings, mostly loss-making) | 5,062 | 11.2% | 9.9% |

Big winners came disproportionately from stocks with a P/E above 60 or no P/E at all. So did big losers. Expensive and loss-making stocks are the most volatile ones: they produce more extreme moves in both directions. A low P/E did not protect against a big loss either.

### Does the P/E predict the next three months?

**Method.** The same US stocks, at every month end from January 2010 to June 2026. The study keeps only stocks in an uptrend: the close above its 200-day average and within 10% of its 52-week high. It measures the next 63 sessions' return minus the S&P 500 ETF (SPY). The sample is 101,983 stock-months in 1,442 companies.

| Trailing P/E at the month end | Stock-months | Median return over SPY, next 63 sessions | Share that beat SPY |
|---|---|---|---|
| under 20 | 29,662 | −0.6% | 47.7% |
| 20–35 | 28,090 | −0.6% | 47.4% |
| 35–60 | 11,922 | −0.3% | 49.1% |
| over 60 | 8,735 | −0.5% | 48.7% |
| no P/E | 23,574 | +0.4% | 51.3% |

The rank correlation between P/E and the next three months' excess return was 0.006: **no relationship**. Uptrend stocks bought above 60× did as well as those bought below 20×. (The medians are slightly negative because the typical stock lags a cap-weighted index.) Read this as "no evidence that a low P/E helps a swing trade", not as proof that valuation never matters.

## 5. The two sources of return

**Price change = EPS change × P/E change.** A stock rises because earnings grow, or because buyers pay more for each unit of earnings (a re-rating), or both. Cases from the filings:

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

**Earnings-driven gains are durable.** The P/E can shrink and the stock still holds its price. **Re-rating gains depend on growth that has not happened yet.** They reverse fast when that growth does not arrive (SMCI, section 7).

## 6. Cheap stocks that stayed cheap

At the end of 2019 Verizon traded at about 16 times earnings. Over the next four years its EPS rose 28%. Its P/E halved anyway, and the price fell.

```series
title: Verizon 2019–2023 — cheap, then cheaper
from: 2019-06-01
to: 2023-12-31
tf: W
line: us:VZ | Verizon
line: us:fund.VZ.pe | Trailing P/E | pane2
caption: At the end of 2019 Verizon traded at about 16× earnings. Its EPS then rose 28%, but the P/E halved to 7.6 and the price fell from 61.40 to 37.70. A low P/E is not a floor (price only; the dividend made up part of the loss).
```

A low P/E is often low for a reason: earnings about to fall, a shrinking business, or debt. Stocks that look cheap and stay cheap are called **value traps**. Two more:

| Stock | Period | Starting P/E | EPS | Price | Ending P/E |
|---|---|---|---|---|---|
| Intel | end-2019 → Jun 2024 | 14 | fell to a quarter | 59.85 → 30.97 | 32 |
| Adobe | end-2021 → Oct 2026 | 47 | +47% | 567 → 236 | 13 |

Intel's earnings collapsed, so its "cheap" P/E *rose* as the price halved. Adobe's earnings grew, but the whole sector's P/Es fell (a de-rating). "Cheapest ever" was true most of the way down.

Over those periods, Verizon and Adobe closed below their 200-day average on about three days in four. Intel did so on more than half. **A cheap stock without an uptrend gives you nothing to trade.**

## 7. When valuation does matter

### 7.1 At the market level: 2022

In 2022 the US ten-year yield went from 1.5% to 3.9%. On the way it peaked at 4.2% in October.

P/Es fell almost everywhere. The sample is about 950–970 profitable US companies with filings. Their **median trailing P/E fell from 25.5 to 20.0**. The share of companies above 50× fell from 21% to 12%.

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

The same year, by company:

| 2022 | Price | EPS | P/E |
|---|---|---|---|
| Adobe | ×0.59 | ×0.84 | 47 → 33 |
| NVIDIA | ×0.50 | ×0.73 | 91 → 62 |
| JPMorgan | | | 10.1 → 11.4 |

High-P/E stocks lost most, while JPMorgan's P/E *rose*. That is the duration effect explained in [the rates guide](learn-macro-rates.md). The further in the future a company's profits lie, the more a rise in rates cuts their value today.

A rate shock is a problem for the whole market. It shows first in the market's trend and breadth ([Reading the market's trend](learn-health-trend.md)). The fix is to hold less in the market, not to hunt for low P/Es.

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

A P/E that has risen several times over is not a sell signal. NVIDIA spent most of 2023 above 100× and kept rising. But a high multiple measures **fragility**. Nothing in the valuation holds the price up, so any disappointment cuts the price at once.

So tighten the stop, sell part of the position into very fast, steep run-ups, and expect gaps ([Stops and exits](learn-risk-stops-exits.md)).

**Mean-reversion and value approaches** are where valuation earns its place. If you buy weakness, expecting the price to bounce back, you need a fair value for it to return *to*. A common rule set asks for high quality, an attractive valuation, and a pullback. It never buys a stock in free fall, such as one more than 15% below its 200-day average.

## 8. Sector norms — compare within a group

Median trailing P/E of seven US banks (JPM, BAC, WFC, GS, MS, USB, PNC) against eight software companies (MSFT, ADBE, CRM, ORCL, INTU, ADSK, CDNS, SNPS):

| Year-end | Banks | Software |
|---|---|---|
| 2015 | 13 | 51 |
| 2018 | 11 | 46 |
| 2021 | 11 | 61 |
| 2022 | 11 | 54 |
| 2024 | 16 | 48 |
| Oct 2026 | 12.5 | 26 |

Banks earn their profit from borrowed money, and their profits rise and fall with the economy. They are valued on book value and trade at P/Es in the low teens. Software has high margins and recurring revenue, and needs little capital. So it usually trades at several times a bank's P/E. A bank at 18× is expensive; software at 25× may be cheap.

The software median halved in 2025–26 (Adobe at 13×). That was a sector de-rating. It showed as weak group relative strength long before it looked like "cheapness" ([Sectors and groups](learn-sectors-groups.md)). Cyclical companies are the opposite trap: **their P/E is lowest when their earnings peak** ([Growth and the business cycle](learn-macro-cycle.md)).

## 9. India — higher multiples as the norm

Indian stocks have long traded at higher P/Es than most markets. Over the past decade, the Nifty 50's trailing P/E (published daily by NSE) was mostly in the low-to-mid 20s. Mid- and small-caps were higher. The reasons:

- higher nominal growth;
- steady monthly SIP money from Indian savers;
- high return on equity (ROE) at the leading companies;
- few large listed growth companies to choose from.

The premium widens and narrows as money flows in and out (approximate; check NSE). The table shows the median trailing P/E of profitable companies with filings. For India that is the ~390 most-traded stocks, with P/E from mid-2022.

| Date | India (covered) | US (covered) |
|---|---|---|
| 30 Jun 2023 | 32 (n=265) | 22 (n=971) |
| 27 Sep 2024 | 43 (n=314) | 25 (n=1,048) |
| 28 Mar 2025 | 34 (n=327) | 22.5 (n=1,069) |
| 13 Oct 2026 | 36 (n=364) | 23 (n=1,205) |

This is an illustration, not an index: the Indian set is small and leans to popular names. But it matches the market. At the September 2024 peak, 43% of covered Indian companies were above 50×. The fall to March 2025 matches the Nifty's 16% drawdown over that time.

```series
title: Indian IT de-rates — TCS and Infosys P/E, 2023–2026
from: 2023-01-01
line: india:fund.TCS.NS.pe | TCS trailing P/E
line: india:fund.INFY.NS.pe | Infosys trailing P/E
caption: Both earned more in 2026 than in 2024 (EPS +11% and +14%), yet their P/Es halved, from 33 and 29 to about 16 and 14, and the shares fell by roughly 45%. A sector re-rating, the same pattern as US software.
```

Sector norms hold in India too. Trailing P/Es in September 2024:

| Company | P/E | Company | P/E |
|---|---|---|---|
| HDFC Bank | 20 | TCS | 33 |
| ICICI Bank | 21 | DMart | 125 |
| SBI | 11 | Dixon | 188 |
| | | Trent | 245 |

Government-owned (PSU) banks and energy companies sit low; Coal India was about 5× at end-2022. Consumer and retail companies sit high. Re-ratings run both ways: Trent fell 62% from September 2024 to October 2026 as its P/E halved. (Its trailing EPS in the data also fell — check the filings.)

## 10. What the trader does with valuation

1. **Time entries with growth and price action**: trend, relative strength, base, breakout, accelerating earnings ([Earnings that move stocks](learn-fund-earnings.md)). None of these needs a valuation filter.
2. **Do not avoid or short a leader for a high P/E alone.** Big winners came disproportionately from high-P/E and loss-making stocks (section 4). Short a broken chart, not a high P/E.
3. **Valuation is context and a risk flag.** Suppose the P/E has tripled in a year, or sits far above its own history while growth slows. Then use a smaller size, a tighter trailing stop, and sell into strength. Do not sell before the chart breaks.
4. **Check the EPS before trusting the P/E** (one-offs, split errors).
5. **Compare within the peer group.** A leader at twice its peers' P/E should be growing much faster.
6. **When rates jump, hold less** in high-P/E stocks ([Interest rates and central banks](learn-macro-rates.md)).
7. **For long-term or buy-the-dip money, valuation comes first** ([Quality and the growth checklist](learn-fund-quality.md)).

## 11. What the evidence says

- **Robust:** over decades, cheap stocks (low P/B or P/E) beat expensive ones on average (the Fama–French value premium). But slowly, with a long dry spell after 2007, and it says nothing about when to enter a swing trade.
- **Robust:** the market's starting valuation predicts its 10-year return far better than next year's (Shiller's CAPE). So it is a poor timing tool.
- **Measured here:** among US uptrend stocks since 2010, P/E did not predict the next three months' return. Big winners and big losers both came disproportionately from high-P/E and loss-making stocks.
- **Folklore:** "a high P/E must fall", "a low P/E can't fall much".
- **Lags:** trailing P/E makes fast growers look too expensive and cyclicals at the peak look too cheap. One-off charges break it. Forward P/E depends on analysts' estimates, which change.
- **Limits of the studies:** today's companies only (survivorship); no costs; monthly samples overlap, so the stock-months are not independent; reported EPS includes one-offs.

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
