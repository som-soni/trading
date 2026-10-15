# App notes moved out of learn-fund-quality

## Intro — guide outline bullets (app-specific ones)

- the CAN SLIM letters and Minervini's SEPA fundamentals, and exactly how this app scores them;
- what the app's own backtests say about filtering on them;

## Intro — "Where this shows in the app"

**Where this shows in the app.** Chart → **Fundamentals** covers one company. Its tabs are Overview,
Quarters, Profit & Loss, Balance Sheet, Cash Flows, Ratios, Shareholding and Peers. It also has a
**Minervini SEPA** section with tests F1–F8 and a verdict. The chart's side panel has two blocks. The
**Quarterly fundamentals** block shows the latest EPS and sales growth, ROE, the SEPA verdict and a
CODE 33 tag. The **Fundamentals** block comes from the Quality tracker. Screens → **Quality** opens the
*Quality companies* page: a score out of 100, the F-score, ROIC / ROE, margins, cash conversion and
debt. The rules live in `scripts/fundamentals/sepa.py`, `fundamentals/quality.py` and
`fundamentals/growth.py`. Every threshold below is a named constant in those files.

## §1 table row

| In this app | Quality page | Minervini SEPA section |

(Asian Paints) "In October 2026 Asian Paints scores **80/100** on the Quality page"

## §2 What the app stores and computes (whole section)

The app stores filings, not opinions. For the US it uses SEC XBRL data (from 2009, ~1,590
companies). For India it uses NSE results filings (from late 2020, ~388 companies). Yahoo is the
fallback. Two database tables matter:

- **`quarterly_results`** — one row per quarter: revenue, net income, EPS, pretax income, equity,
  share count, the filing date (`filed`), `basis`, `derived`; for the US also the year-ago figures
  *from the same filing* (`*_prior`), operating income and, for about 32,000 of 76,000 rows, gross
  profit. India rows carry no gross profit and no year-ago columns.
- **`financial_lines`** — the statement lines behind the Fundamentals page:

| Statement | Lines stored |
|---|---|
| P&L (quarterly `Q`, annual `FY`) | sales, expenses, operating_profit, other_income, interest, depreciation, pbt, tax, net_profit, eps; India also exceptional, face_value |
| Balance sheet (`BS`) | equity, equity_capital, reserves, borrowings, total_assets / liabilities, fixed_assets, cash, receivables, inventory, investments, minority; India cwip; banks deposits, advances |
| Cash flow (`FY` only) | cfo, cfi, cff, net_cash, capex, dividends_paid (US also dividend_ps) |

Cash flow is annual only — US from 2011, India from about FY2021 (Q4 filings carry it).

**Operating profit means different things by market.** In the US it is the filing's operating
income, *after* depreciation. In India the app follows screener.in's convention: sales less operating
expenses, *before* other income, interest and depreciation.

From these tables, `growth.py` computes:

- year-over-year EPS and sales growth per quarter (blank when the year-ago figure is not positive);
- **net margin** (net income ÷ revenue) and its year-ago value;
- trailing-twelve-month EPS;
- annual EPS growth over `ANNUAL_YEARS` = 3 fiscal years;
- ROE.

The charts in these guides can draw any company's `eps`, `eps_ttm`, `eps_g`, `rev_g`, `revenue`,
`margin` and `pe`. Each quarter is dated on the day it was filed.

## §4 ROE — how the app computes it

The app computes it from the filings: the last twelve
months' net income, divided by the average of the latest equity and the equity about a year earlier.
If that is missing, it uses the Quality page's annual average. ... So the app also shows measures
that include debt:

| Measure | Where | Formula in the code |
|---|---|---|
| ROE | Fundamentals Overview, SEPA F6 | TTM net income ÷ average equity |
| ROCE | Fundamentals Overview and Ratios | (profit before tax + interest) ÷ (equity + borrowings) at the year end |
| ROIC | Quality page | EBIT × (1 − tax rate) ÷ invested capital, per year |

## §5 Debt

The Fundamentals page shows **Debt to equity** (borrowings ÷ equity) in the Overview, and the
balance sheet's Borrowings line.

## §6 Cash flow

The app stores annual cash from operations
and capital spending (capex). The Cash Flows table adds **Free cash flow** = CFO − capex. The Quality
tracker requires FCF to be positive every year ...
The Quality page catches this. SMCI scores 70 but carries the red flag *negative free cash flow in
the latest year* (F-score 2), so it is not "high quality".

## §8 How this app encodes them — 8.1 The Minervini SEPA section (`fundamentals/sepa.py`)

| Test | Rule, with the constant |
|---|---|
| F1 EPS growth | latest quarter's EPS up at least **25%** (`EPS_Q_GROWTH_MIN`) on the year-ago quarter |
| F2 EPS accelerating | the growth rate rose in at least **2** (`ACCEL_MIN_RISES`) of the last **3** (`ACCEL_WINDOW`) quarters |
| F3 Sales growth | latest sales up at least **20%** (`SALES_Q_GROWTH_MIN`), or sales growth rising **3** quarters running |
| F4 Margins expanding | net margin above the same quarter a year earlier |
| F5 Annual EPS growth | at least **25%** a year (`ANNUAL_EPS_CAGR_MIN`) over **3** fiscal years, no loss-making year |
| F6 Return on equity | trailing-twelve-month ROE at least **17%** (`ROE_MIN`) |
| F7 Beat estimates | latest EPS above the consensus estimate (Yahoo's) |
| F8 No slowdown | growth has not slowed two quarters running by **15** points or more (`DECEL_DROP_MIN`) |

Verdicts (as documented in the code's `DOC`) ... NO DATA ... (`STALE_RESULTS_DAYS`); CODE 33 (`CODE33_QUARTERS`).

The code's own caveats: ... past estimates (F7) are not stored. As of mid-October 2026:
US 17 LEADER, 185 ACCEPTABLE, 991 WEAK, 397 NO DATA; India 17 LEADER, 99 ACCEPTABLE, 241 WEAK, 31 NO
DATA.

Separately, the live Minervini screener adds a note to rows that pass the chart rules. The note gives
current revenue and earnings growth and the change in gross margin (`fundamentals_ok`). It is only a
note: it does not exclude any stock.

## §8.2 The long-term Quality tracker (`fundamentals/quality.py`)

The page then values the stock at each day's close (FCF yield, P/E
against its own median, PEG). It sorts the result into BUY ZONE / ACCUMULATE / WAIT, covered in
[valuation for traders](learn-fund-valuation.md). In October 2026, 275 of 1,500 scored US companies
and 278 of 819 Indian ones score 70 or more.

## §9 Asian Paints caption

"the Quality page's annual view still scores it 80."

## §10 Red flags

The app does not strip these out. ... And read the Exceptional items line on India's Quarters table.
- **Share-count dilution.** The app stores the share count each quarter. ... The app's split-detection code (`growth.split_factors`)
  reads that as a bonus issue, and so "adjusts" older EPS by 2.25×. The code itself warns of this
  ("a large share issue at such a ratio would be misread"). When the page says *EPS on today's share
  basis*, check there really was a split.
- **Derived quarters.** ... (marked `derived`, about 16,500 of 76,000 US rows).
- **Data glitches.** ... Open the filing (`doc_url`).
- **Stale results.** No results for 200+ days turns the verdict into NO DATA.

## §11 India specifics

- **Consolidated vs standalone (`basis`).** ... The app uses consolidated when a company files it for at
  least 75% of recent quarters (`CONSOLIDATED_SHARE`), and standalone otherwise. It **never mixes the
  two** within a company. 353 companies are consolidated, 34 standalone. ... The basis is printed
  beside the units.
- **NSE filings.** ... The app reads both NSE feeds: the legacy one,
  and the Integrated Filing from 2025.
- **Shareholding (`shareholding` table, 381 companies).** The app stores the promoter and public
  share each quarter (from 2015). FII / DII shares come from the detailed filing, for the latest four quarters.
  Pledged shares are not stored.

## §12 The evidence from this app's backtests (whole section; backtest results NOT to be cited in Learn)

The Minervini strategy's backtest can apply the SEPA verdict as it stood at the time
(`--fundamentals`). Each signal is judged only on quarters filed by its date, and F7 is left out.
The `covered` level keeps any company that can be scored. It is **the right comparison group**,
because companies without a score differ from the rest in systematic ways.

**US, 2010 → October 2026, current version v1.6** (failed-breakout exit off, at most 8 positions):

| Filter | Trades | Win % | Expectancy | Profit factor | CAGR | Max drawdown |
|---|---|---|---|---|---|---|
| none | 557 | 27.8 | +0.04R | 1.04 | 0.65% | −43.5% |
| covered | 487 | 26.5 | +0.03R | 1.03 | 0.63% | −36.3% |
| acceptable | 115 | 18.4 | −0.10R | 0.77 | −0.70% | −17.9% |
| leader | 24 | 25.0 | +0.04R | 1.03 | 0.02% | −10.9% |

Buy-and-hold returned about 12% a year (drawdown −34%). LEADER-only made +0.58R per trade up to 2019
(14 trades), and −0.72R since (10). Inside the `covered` run, by verdict: LEADER +0.23R (19 trades),
ACCEPTABLE −0.21R (75), WEAK +0.06R (393).

**2022-07 → October 2026, earlier version v1.5** (entries by buy-stop orders):

| Filter | US trades | US expectancy | US CAGR | India trades | India expectancy | India CAGR |
|---|---|---|---|---|---|---|
| none | 442 | −0.01R | 1.07% | 90 | +0.21R | 4.15% |
| covered | 337 | +0.02R | 1.23% | 59 | +0.28R | 3.74% |
| acceptable | 72 | −0.18R | −2.99% | 16 | +0.22R | 0.78% |
| leader | 19 | −0.40R | −1.72% | 7 | +0.27R | 0.42% |

Caveats, all serious:

- The standard error of expectancy is about 0.34R for the 24 US leader trades, and 0.7R for India's
  7. So **no difference here is statistically meaningful**.
- India covers only 4.3 years.
- The universe is today's listed stocks, so **survivorship** flatters every row.
- The strategy itself shows no edge, so a filter on top has little to improve.
- One-offs are not removed.

The v1.5 rows predate the current rules (Strategies → Minervini SEPA → Backtests groups runs by
version). `research/momentum-trend-research.md` records the same conclusion: no consistent edge from
the tests.

## §13 Evidence bullet

- **Not shown here:** that requiring SEPA LEADER improves the Minervini breakouts. Filtering cut the
  number of trades and the CAGR. Within the US comparison group, WEAK did no worse than ACCEPTABLE.

## §14 Checklist items

- [ ] EPS and sales growth ≥ 25% / 20% and rising; check F8 for a two-quarter slowdown
- [ ] Exceptional items, other income and tax rate normal? (Quarters table)
- [ ] ROE ≥ 17% without heavy debt (Debt to equity, ROCE); no red flag on the Quality page
