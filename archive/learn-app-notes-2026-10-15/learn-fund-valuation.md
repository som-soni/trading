# App notes moved out of learn-fund-valuation

## Intro — "Where this shows in the app"

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

## §1 P/E table — "Where you find it" column

| Version | EPS used | Where you find it |
|---|---|---|
| **Trailing (TTM)** | The last four reported quarters | Fundamentals page, the `fund.X.pe` charts |
| **Forward** | Analysts' estimate for the next 12 months | **Not stored in this app** — brokers and data sites quote it |
| **Shiller / CAPE** | 10-year average of inflation-adjusted earnings | Market-level only; not stored |

The app's EPS is the **reported, diluted EPS from the filings** (SEC and NSE
data). It is not the "adjusted" EPS that companies put in their headlines. Each
quarter counts only from its filing date, so a past P/E uses only what was
known then.

## §3 The other yardsticks — "In this app" column

| Measure | In this app |
|---|---|
| PEG | Quality page: P/E ÷ annual EPS CAGR over the statement years (cheap ≤ 1, fair ≤ 1.5) |
| EV/EBITDA | **Not computed.** The Quality page shows *Net debt/EBITDA*, a leverage measure, not a valuation |
| Price/sales | **Not computed.** Divide *Market cap* by *Sales (TTM)* on the Fundamentals page yourself |
| Price/book | **Not computed as a ratio.** The Fundamentals page shows *Book value* per share; divide the price by it |
| FCF yield | Quality page (cheap ≥ 5%, fair ≥ 3%; not used for banks) |
| Dividend yield | Fundamentals page |

## §4 "The app's own big winners" (removed: backtest evidence)

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

## §4 "Does P/E at entry predict the trade? Not in this app's backtests" (removed: backtest evidence)

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

## §7.2 Mean-reversion — Quality page BUY ZONE

The Quality page's BUY ZONE is built that way. It needs
high quality, a valuation that scores as attractive, and a pullback. It never
buys a stock in free fall (more than 15% below the 200-day).

## §8 Sector norms

It showed on Markets → **Sectors** as weak group strength long
before it looked like "cheapness".

## §10 What the trader does

1. ... That is what the app's strategies do; none of them filters on valuation.
5. **Compare within the peer group** (the Fundamentals page's peers table).
7. **For long-term or buy-the-dip money, valuation comes first** — use the
   Quality page.

## §11 Evidence

- **Here:** entry P/E did not separate winning from losing backtest trades.
  The largest winners started at 17–52×.
- Forward P/E rests on estimates not stored here.
