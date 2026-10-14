# Valuation for traders — why leaders look expensive, and when the price tag matters

Learning material: P/E (trailing against forward), earnings yield, PEG,
EV/EBITDA, price/sales and price/book; why big winners look expensive when
they start; the two sources of return (earnings growth and the multiple),
measured on real cases; when valuation matters; sector norms; India's higher
multiples. Second of three Fundamentals guides, after
[earnings that move stocks](learn-fund-earnings.md) and before
[quality and the growth checklist](learn-fund-quality.md).

**Where this shows in the app.** Chart → **Fundamentals** (`fundamentals/company.py`)
shows **Stock P/E** (price ÷ trailing-twelve-month EPS, blank when that EPS is
not positive), *Book value*, *Dividend yield*, *Market cap*, *Sales (TTM)*
and a peers table with P/E. Screens → **Quality** (`fundamentals/quality.py`)
values a company by free-cash-flow yield, P/E against its own median, and
PEG, and shows *Net debt/EBITDA*. **No screen, strategy or backtest uses
valuation as a filter** (`pe…` in backtest run names means *progressive
exposure*). The charts use `fund.SYMBOL.pe`: each close ÷ the trailing EPS
known that day.

---

## 1. P/E — the price of one rupee or dollar of profit

**P/E = share price ÷ earnings per share.** At 25, buyers pay 25 years of
today's profit — fewer if it grows.

| Version | EPS used | Where you find it |
|---|---|---|
| **Trailing (TTM)** | The last four reported quarters | Fundamentals page, the `fund.X.pe` charts |
| **Forward** | Analysts' estimate for the next 12 months | **Not stored in this app** — brokers and data sites quote it |
| **Shiller / CAPE** | 10-year average of inflation-adjusted earnings | Market-level only; not stored |

The app's EPS is **reported, diluted EPS from the filings** (SEC XBRL, NSE
results; `marketdata/financials.py`), not the "adjusted" EPS companies
headline, and each quarter counts from its filing date — a past P/E uses only
what was known then. So:

- **One-off charges distort it.** Stored trailing P/E reached about 1,195 for
  AMD (end-2023) and 189 for Broadcom (end-2024): acquisition charges had
  crushed reported EPS. When a P/E looks crazy, look at the EPS line first.
- **It lags fast growers.** Today's price over last year's profit overstates
  how expensive a company about to double its earnings is (NVIDIA, section 4).
- **Data caveat:** a few stored companies' EPS was not put on today's share
  basis after a split, so their P/E reads about 1–2 on some dates; the studies
  below drop entry P/Es under 4.

## 2. Earnings yield — P/E turned upside down

**Earnings yield = 1 / P/E** — 4% at a P/E of 25, 10% at 10 — which makes a
stock comparable with a bond: against a 4–5% 10-year, a 4% earnings yield
pays little for the risk; against 1.5%, it looks generous. That is why rising
yields compress multiples; the arithmetic (discounting, duration, the equity
risk premium) is in [the interest-rates guide](learn-macro-rates.md). **Rates
set the ceiling on what the market pays; earnings decide who gets paid.**

## 3. The other yardsticks — and which ones the app has

| Measure | Formula | Good for | In this app |
|---|---|---|---|
| **PEG** | P/E ÷ EPS growth rate (%) | Comparing growers: P/E 40 growing 40% = PEG 1 | Quality page: P/E ÷ annual EPS CAGR over the statement years (cheap ≤ 1, fair ≤ 1.5) |
| **EV/EBITDA** | (market cap + net debt) ÷ EBITDA | Comparing companies with different debt loads; takeovers | **Not computed.** The Quality page shows *Net debt/EBITDA*, a leverage measure, not a valuation |
| **Price/sales** | market cap ÷ revenue | Companies with no profit yet; cyclicals at a trough | **Not computed.** Divide *Market cap* by *Sales (TTM)* on the Fundamentals page yourself |
| **Price/book** | price ÷ book value per share | Banks, insurers, asset-heavy firms | **Not computed as a ratio.** The Fundamentals page shows *Book value* per share; divide the price by it |
| **FCF yield** | free cash flow ÷ market cap | Cash-generating businesses | Quality page (cheap ≥ 5%, fair ≥ 3%; not used for banks) |
| **Dividend yield** | dividends ÷ price | Income stocks | Fundamentals page |

PEG uses **past** growth while the price discounts **future** growth, so a
low PEG on a decelerating grower is not cheap. Price/book suits banks and
means little for software, whose assets are people and code.

## 4. Why leaders look expensive

The stocks that go on to double and triple usually start with P/Es the
textbook calls "expensive", because **the market prices the earnings it can
see coming, not the ones already reported**. When the growth arrives, the P/E
falls while the price keeps rising.

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

**All of the gain came from earnings; the multiple shrank.** Shunning it at
62×, or above 100× (late February to November 2023), meant judging by last
year's profit a company about to earn ten times as much.

### The app's own big winners

The US donchian backtest (`v1.1-69e24dab`, 506 trades, 2013–2026, modelled
costs) made most of its result from a few long holds. Its largest winners,
with the P/E on entry and exit days (changes from daily closes):

| Trade | R | P/E at entry → exit | Price | EPS | P/E |
|---|---|---|---|---|---|
| NVDA, May 2016 → Oct 2018 | +53 | 39 → 34 | ×5.6 | ×6.3 | ×0.88 |
| SFM (Sprouts), Oct 2023 → Jul 2025 | +42 | 17 → 31 | ×3.7 | ×2.0 | ×1.8 |
| ANET, Sep 2016 → Oct 2018 | +26 | 43 → 94 | ×2.9 | ×1.3* | ×2.2 |
| ADBE, May 2017 → Oct 2018 | +21 | 52 → 49 | ×1.8 | ×1.9 | ×0.95 |

\*Arista's 2018 EPS was depressed by one-off charges. Three of the four
started at 39–52×, against a stored-US median of 21–23 on those dates; Sprouts
was a cheap stock re-rated as growth sped up. (The NVIDIA trade is charted in
[the stops guide](learn-risk-stops-exits.md).) O'Neil reported the same of
past big winners: they began above the market's P/E, which then expanded.

### Does P/E at entry predict the trade? Not in this app's backtests

Every trade of two current-version US runs, by trailing P/E on entry day:

| Entry P/E | Minervini v1.6 (2010–2026): trades / win % / avg R | Donchian v1.1 (2013–2026): trades / win % / avg R |
|---|---|---|
| under 20 | 119 / 27% / +0.12 | 98 / 28% / +0.63 |
| 20–35 | 145 / 25% / −0.09 | 97 / 29% / +0.01 |
| 35–60 | 91 / 27% / +0.10 | 43 / 26% / +1.86 (+0.63 without its top trade) |
| over 60 | 69 / 32% / −0.02 | 43 / 37% / +0.47 |
| no P/E (loss-making or not covered) | 121 / 31% / +0.06 | 221 / 29% / +0.38 |

Minervini `v1.6-39a21ebf`: 557 trades, 424 with a usable P/E (median 29);
donchian: 506 trades, 281 usable (median 25). Rank correlation of entry P/E
with R: −0.04 and +0.01 — **no relationship**; trades bought above 60× won as
often as those below 20×. Small samples dominated by outliers: read it as "no
evidence that P/E helps", not proof that it never does.

## 5. The two sources of return

**Price change = EPS change × P/E change**: a stock rises because earnings
grow, because buyers pay more per unit of earnings, or both. Stored cases:

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

**Earnings-driven gains are durable** — the multiple can shrink and the
stock still holds. **Re-rating gains are borrowed against the future**: they
reverse fast when the growth does not arrive (SMCI, section 7).

## 6. Cheap stocks that stayed cheap

A low P/E is often low for a reason — earnings about to fall, a shrinking
business, debt. The *value traps*:

```series
title: Verizon 2019–2023 — cheap, then cheaper
from: 2019-06-01
to: 2023-12-31
tf: W
line: us:VZ | Verizon
line: us:fund.VZ.pe | Trailing P/E | pane2
caption: At the end of 2019 Verizon traded at about 16× earnings. Its EPS then rose 28%, but the P/E halved to 7.6 and the price fell from 61.40 to 37.70. A low P/E is not a floor (price only; the dividend made up part of the loss).
```

- **Intel**, end-2019 → June 2024: "cheap" at 14×, then EPS fell to a
  quarter and the price halved (59.85 → 30.97); the trailing P/E *rose* to 32.
- **Adobe**, end-2021 → Oct 2026: EPS +47%, P/E 47 → 13, price 567 → 236 — a
  sector de-rating; "cheapest ever" was true most of the way down.

Verizon and Adobe closed below their 200-day average on about three days in
four over those spans, Intel on more than half. **Cheapness without a trend
gives you nothing to trade.**

## 7. When valuation does matter

### 7.1 At the market level: 2022

In 2022 the US 10-year went from 1.5% to 3.9% (4.2% peak in October) and
multiples compressed almost everywhere: across ~950–970 profitable US
companies with stored filings, the **median trailing P/E fell from 25.5 to
20.0**, and the share above 50× from 21% to 12%.

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

In 2022 Adobe went ×0.59 (EPS ×0.84, P/E 47 → 33) and NVIDIA ×0.50 (EPS
×0.73, P/E 91 → 62), while JPMorgan's P/E *rose* from 10.1 to 11.4. High
multiples lost most — the duration effect of [the rates guide](learn-macro-rates.md).
A rate shock is a **regime** problem that shows first in trend and breadth
([learn-health-trend](learn-health-trend.md)); the fix is lower exposure, not
hunting for low P/Es.

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

A multiple that has expanded several times is not a sell signal (NVIDIA
spent most of 2023 above 100× and kept rising), but it measures **fragility**:
no valuation support, so any disappointment reprices at once. Tighten the
stop, take partials into climactic runs, expect gaps
([learn-risk-stops-exits](learn-risk-stops-exits.md)).

**Mean-reversion and value approaches** are where valuation earns its place:
buying weakness needs something to revert *to*. The Quality page's BUY ZONE
is built so — high quality, an attractive valuation vote, a pullback, never a
falling knife (more than 15% below the 200-day).

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

Banks earn on leveraged, cyclical balance sheets and trade on book value and
low-teens P/Es; software (high margins, recurring revenue, little capital)
usually carries several times that. A bank at 18× is expensive; software at
25× may be cheap. The 2025–26 halving of the software median (Adobe at 13×)
is a sector de-rating — visible on Markets → **Sectors** as weak group
strength long before it looked like "cheapness". Cyclicals are the reverse
trap: **their P/E is lowest at the earnings peak**
([learn-macro-cycle](learn-macro-cycle.md), [learn-sectors-groups](learn-sectors-groups.md)).

## 9. India — higher multiples as the norm

Indian equities have long carried higher multiples than most markets: the
Nifty 50's trailing P/E (published daily by NSE) mostly in the low-to-mid 20s
over the past decade, mid- and small-caps higher — on higher nominal growth,
steady domestic SIP inflows, high ROE at the leaders and few large listed
growth companies. The premium widens and narrows with flows (approximate;
check NSE). Median trailing P/E of profitable companies with stored filings
(India ~390 most-traded, P/E from mid-2022):

| Date | India (covered) | US (covered) |
|---|---|---|
| 30 Jun 2023 | 32 (n=265) | 22 (n=971) |
| 27 Sep 2024 | 43 (n=314) | 25 (n=1,048) |
| 28 Mar 2025 | 34 (n=327) | 22.5 (n=1,069) |
| 13 Oct 2026 | 36 (n=364) | 23 (n=1,205) |

An illustration, not an index (the Indian set is small and leans to popular
names), but the September 2024 peak — 43% of covered Indian companies above
50× — and the fall to March 2025 match the Nifty's 16% drawdown then.

```series
title: Indian IT de-rates — TCS and Infosys P/E, 2023–2026
from: 2023-01-01
line: india:fund.TCS.NS.pe | TCS trailing P/E
line: india:fund.INFY.NS.pe | Infosys trailing P/E
caption: Both earned more in 2026 than in 2024 (EPS +11% and +14%), yet their P/Es halved, from 33 and 29 to about 16 and 14, and the shares fell by roughly 45%. A sector re-rating, the same pattern as US software.
```

Sector norms hold in India too — in September 2024 HDFC Bank 20, ICICI Bank
21, SBI 11 against TCS 33, DMart 125, Dixon 188, Trent 245; PSU banks and
energy (Coal India about 5× at end-2022) sit low, consumer and retail high.
Re-ratings run both ways: Trent fell 62% from September 2024 to October 2026
as its P/E halved (its stored trailing EPS also fell — check the filings).

## 10. What the trader does with valuation

1. **Time entries with growth and price action** — trend, RS, base,
   breakout, accelerating earnings ([learn-fund-earnings](learn-fund-earnings.md)) —
   as the app's strategies do; none filters on valuation.
2. **Do not avoid or short a leader for a high P/E alone.** Every big winner
   in section 4 looked expensive. Short a broken chart, not a multiple.
3. **Valuation is context and a risk flag.** A multiple tripled in a year, or
   far above its own history while growth slows: smaller size, tighter
   trailing stop, sell into strength — not a sale before the chart breaks.
4. **Check the EPS before trusting the P/E** (one-offs, split errors).
5. **Compare within the peer group** (the Fundamentals page's peers table): a
   leader at twice its peers' multiple should be growing much faster.
6. **When rates jump, cut exposure** to high multiples ([learn-macro-rates](learn-macro-rates.md)).
7. **For long-term or buy-the-dip money, valuation leads** — the Quality page.

## 11. What the evidence says

- **Robust:** over decades, cheap stocks (low P/B or P/E) beat expensive ones
  on average (the Fama–French value premium) — slowly, with a long drought
  after 2007, and nothing to say about a swing trade's timing.
- **Robust:** starting valuation predicts the market's 10-year return far
  better than next year's (Shiller's CAPE) — a poor timing tool.
- **Here:** entry P/E did not separate winning from losing backtest trades;
  the largest winners started at 17–52×.
- **Folklore:** "a high P/E must fall", "a low P/E can't fall much".
- **Lags:** trailing P/E overstates fast growers, understates cyclicals at the
  peak and breaks on one-offs; forward P/E rests on estimates not stored here.

## 12. Checklist

- [ ] Leaders held: P/E against their own history and peers — is growth fast enough to bring it down?
- [ ] Multiple up several-fold in a year? Tighten stops, take partials
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
