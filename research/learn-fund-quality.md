# Quality and the growth checklist — margins, returns, cash, and what CAN SLIM and SEPA ask for

Learning material. This guide covers:

- what "quality" means to a trader compared with an investor;
- margins and margin expansion; return on equity; debt and interest cover;
- cash flow against reported earnings;
- the CAN SLIM letters and Minervini's SEPA fundamentals, and exactly how this app scores them;
- what the app's own backtests say about filtering on them;
- worked examples from stored filings; red flags;
- the India specifics (consolidated vs standalone, shareholding).

It is the third of three Fundamentals guides, after [earnings that move stocks](learn-fund-earnings.md)
and [valuation for traders](learn-fund-valuation.md).

**Where this shows in the app.** Chart → **Fundamentals** covers one company. Its tabs are Overview,
Quarters, Profit & Loss, Balance Sheet, Cash Flows, Ratios, Shareholding and Peers. It also has a
**Minervini SEPA** section with tests F1–F8 and a verdict. The chart's side panel has two blocks. The
**Quarterly fundamentals** block shows the latest EPS and sales growth, ROE, the SEPA verdict and a
CODE 33 tag. The **Fundamentals** block comes from the Quality tracker. Screens → **Quality** opens the
*Quality companies* page: a score out of 100, the F-score, ROIC / ROE, margins, cash conversion and
debt. The rules live in `scripts/fundamentals/sepa.py`, `fundamentals/quality.py` and
`fundamentals/growth.py`. Every threshold below is a named constant in those files.

---

## 1. Quality to a trader, quality to an investor

An investor asks: **is this a great business I can own for years?** That means high returns on
capital, steady growth, cash that matches profit, and little debt. The answer changes slowly, because
it is read from annual statements.

A growth trader asks something narrower: **is the business improving fast enough, right now, that
big funds will keep paying higher prices for it?** That means earnings and sales accelerating, and
margins widening. The answer changes every quarter. And the price usually moves before the numbers
are published.

| | Investor's quality | Trader's quality |
|---|---|---|
| Horizon | 5 years of annual statements | the last 4–8 quarters |
| Key numbers | ROIC (return on invested capital), FCF conversion (free cash flow ÷ profit), debt, steady growth | EPS / sales growth and its *acceleration*, margin trend |
| In this app | Quality page | Minervini SEPA section |
| Typical failure | a great company bought at the wrong price | a great quarter bought after the stock has peaked |

The two can disagree sharply. In October 2026 Asian Paints scores **80/100** on the Quality page:
high returns, more cash than debt, and margins intact on an annual view. Yet its quarterly record
from mid-2024 to early 2025 was SEPA **WEAK** (§9). Both are right, about different questions. For a
swing trader the fundamentals are a **filter on the stocks whose chart already looks good**. They are
never a reason to buy on their own.

## 2. What the app stores and computes

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
expenses, *before* other income, interest and depreciation. That is close to EBITDA (profit before
interest, tax, depreciation and amortisation). So compare operating margin (OPM %) within a market,
not across markets.

From these tables, `growth.py` computes:

- year-over-year EPS and sales growth per quarter (blank when the year-ago figure is not positive);
- **net margin** (net income ÷ revenue) and its year-ago value;
- trailing-twelve-month EPS;
- annual EPS growth over `ANNUAL_YEARS` = 3 fiscal years;
- ROE.

The charts in these guides can draw any company's `eps`, `eps_ttm`, `eps_g`, `rev_g`, `revenue`,
`margin` and `pe`. Each quarter is dated on the day it was filed.

## 3. Margins — and margin expansion

- **Gross margin** = (sales − cost of goods) ÷ sales. It reflects pricing power and product mix.
- **Operating margin** = operating profit ÷ sales: what is left after running the business.
- **Net margin** = net profit ÷ sales: what is left after interest and tax — and one-offs.

**Margin expansion drives earnings growth more than anything else.** When sales rise faster than
costs, profit grows faster than sales. This is called operating leverage. Take a company growing
sales 30% while its net margin widens from 10% to 15%: its profit grows about 95%. That is why SEPA
test F4 asks for a net margin above the year-ago quarter. Code 33 asks for margins rising three
quarters running.

```series
title: NVIDIA — net margin and sales growth, 2022–2024
from: 2022-06-01
to: 2024-12-31
line: us:NVDA | NVIDIA | log
line: us:fund.NVDA.margin | Net margin, % | pane2
line: us:fund.NVDA.rev_g | Sales growth, % y/y | pane2 zero
mark: 2023-05-26 | Q1 FY24 filed
mark: 2024-02-21 | SEPA LEADER
caption: Net margin went from about 10% (filed Aug 2022) to 57% (May 2024) while sales growth swung from −21% to +265%. The price led: about $39 on 2023-05-26, $67 when the verdict reached LEADER, $115 by 2024-05-29.
```

Note what the mechanical tests did next. By the filing of 2024-05-29, EPS growth had "slowed" from
+1,274% to +774% to +629%. So F2 and F8 failed and the verdict fell to **WEAK**, even though margins
were at their peak. The stock still rose to about $149 in November 2024, after a 27% drawdown from
June to August. When growth is extreme, it has to slow down eventually. That slowdown is arithmetic,
not always a warning.

## 4. Return on equity (and on capital)

**ROE** = net profit ÷ shareholders' equity: how much the business earns on the owners' money.
O'Neil and Minervini both ask for **17%+**. The app computes it from the filings: the last twelve
months' net income, divided by the average of the latest equity and the equity about a year earlier.
If that is missing, it uses the Quality page's annual average.

ROE can look better than the business really is. **Debt** makes equity small relative to assets.
**Buybacks or big dividends** shrink equity itself. Nestlé India shows an ROE of about 82%
(standalone filings), largely because it pays out most of its profit. So the app also shows measures
that include debt:

| Measure | Where | Formula in the code |
|---|---|---|
| ROE | Fundamentals Overview, SEPA F6 | TTM net income ÷ average equity |
| ROCE | Fundamentals Overview and Ratios | (profit before tax + interest) ÷ (equity + borrowings) at the year end |
| ROIC | Quality page | EBIT × (1 − tax rate) ÷ invested capital, per year |

## 5. Debt and interest cover

Debt makes a good year better. In a bad year it can end a company. Two numbers:

- **Net debt ÷ EBITDA** — how many years of operating cash profit it would take to repay borrowings,
  after subtracting cash. The Quality test passes at **≤ 2×**, or when the company has more cash than
  debt (net cash).
- **Interest cover** = EBIT (operating profit before interest and tax) ÷ interest expense. The
  Quality test wants **≥ 8×**.

The Fundamentals page shows **Debt to equity** (borrowings ÷ equity) in the Overview, and the
balance sheet's Borrowings line. Banks and insurers skip these tests: lending borrowed money is their
business.

## 6. Cash flow against reported earnings (accruals)

Profit depends on accounting choices; cash in the bank does not. The gap between net income and
**cash from operations** (CFO) is called accruals. It is made of things like bills customers have
not yet paid, inventory not yet sold, and costs recorded as assets instead of expenses. Accruals that
stay high predict weaker future earnings (Sloan, 1996). The app stores annual cash from operations
and capital spending (capex). The Cash Flows table adds **Free cash flow** = CFO − capex. The Quality
tracker requires FCF to be positive every year, and to add up to at least **80%** of net income. It
treats negative FCF in the latest year as a **red flag** that overrides any score.

Super Micro Computer is the textbook case in this database:

| Fiscal year (June) | Net profit | Cash from operations | Inventory at year end |
|---|---|---|---|
| FY2023 | $640M | $664M | $1,446M |
| FY2024 | $1,153M | **−$2,486M** | $4,333M |
| FY2026 | $2,230M | **−$6,810M** | $12,896M |

```series
title: Super Micro — the SEPA verdict arrived after the top
from: 2023-01-01
to: 2025-06-30
line: us:SMCI | Super Micro | log
line: us:fund.SMCI.margin | Net margin, % | pane2
line: us:fund.SMCI.rev_g | Sales growth, % y/y | pane2 zero
mark: 2024-03-13 | price peak
mark: 2024-05-06 | LEADER + CODE 33
caption: The quarter filed on 2024-05-06 made SMCI a SEPA LEADER with Code 33 — seven weeks after the $119 peak, with the stock already 30% off it. It fell about 85% peak to trough by November 2024. Operating cash flow for that fiscal year was −$2.5 billion.
```

The Quality page catches this. SMCI scores 70 but carries the red flag *negative free cash flow in
the latest year* (F-score 2), so it is not "high quality". The quarterly SEPA tests never look at
cash. Minervini's Trend Template (his chart checklist) did its job too. On 2024-05-06 the price was
68% above its 200-day average and 30% below its high. The template allows at most 25% below the
high, so the stock failed it.

## 7. CAN SLIM and SEPA — what the books ask for

**CAN SLIM** (William O'Neil, from studying big winners before their moves):

| Letter | Meaning | Fundamental? |
|---|---|---|
| **C** | Current quarterly EPS up sharply on the year-ago quarter (he asks for 25%+), ideally accelerating; sales growing too | yes |
| **A** | Annual earnings growth of 25%+ over three years; ROE 17%+ | yes |
| **N** | Something New — product, management, industry change — and price at new highs | partly |
| **S** | Supply and demand — share count, volume on up days | partly |
| **L** | Leader or laggard — top relative strength in a leading group | no |
| **I** | Institutional sponsorship, rising | no |
| **M** | Market direction — buy only in a confirmed uptrend | no |

**SEPA** (Mark Minervini) has five parts: trend (the Stage-2 Trend Template), fundamentals, catalyst,
entry point and exit. His entry point is the VCP (volatility contraction pattern: a base whose
pullbacks get smaller and quieter). SEPA's fundamental part is close to O'Neil's C and A. It puts more
weight on **acceleration**, **margin expansion** and **beating estimates**. And it names one warning
sign: two quarters of significant deceleration. "Code 33" is his shorthand for EPS growth, sales
growth and margins all accelerating three quarters in a row.

## 8. How this app encodes them

### 8.1 The Minervini SEPA section (`fundamentals/sepa.py`)

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

Verdicts (as documented in the code's `DOC`):

- **LEADER** — F1, F2, F3, F4 and F8 pass, and F5 and F6 pass or are unavailable.
- **ACCEPTABLE** — F1, F3 and F8 pass.
- **WEAK** — anything else.
- **NO DATA** — fewer than **2** of the last four quarters have an EPS growth reading, or the latest
  results are more than 200 days old (`STALE_RESULTS_DAYS`).
- **CODE 33** — EPS growth, sales growth and net margin all rising for **3** quarters
  (`CODE33_QUARTERS`).

The code's own caveats: growth from a loss cannot be measured, so turnarounds fail F1. **One-off
gains and charges are not removed.** And past estimates (F7) are not stored. As of mid-October 2026:
US 17 LEADER, 185 ACCEPTABLE, 991 WEAK, 397 NO DATA; India 17 LEADER, 99 ACCEPTABLE, 241 WEAK, 31 NO
DATA.

Separately, the live Minervini screener adds a note to rows that pass the chart rules. The note gives
current revenue and earnings growth and the change in gross margin (`fundamentals_ok`). It is only a
note: it does not exclude any stock.

### 8.2 The long-term Quality tracker (`fundamentals/quality.py`)

Up to five years of annual statements, scored out of 100:

| Points | Test |
|---|---|
| 20 | ROIC averages ≥ **15%** (banks / insurers: ROE ≥ **12%**) |
| 10 | no year below **10%** ROIC (banks: latest ROA ≥ **1.0%**) |
| 10 | profitable in every year |
| 10 | revenue grows ≥ **7%** a year |
| 10 | diluted EPS grows ≥ **7%** a year |
| 10 | operating margin ≥ **15%** |
| 5 | margin not shrinking: latest within **1%** of the earlier average |
| 10 | FCF positive every year and ≥ **80%** of net income |
| 10 | net debt ≤ **2×** EBITDA and interest covered **8×** |
| 5 | share count grows ≤ **1%** a year |

Banks and insurers skip the margin, margin trend, cash conversion and balance-sheet tests. Their score
is rescaled to 100. **High quality = 70+ and no red flag.** A red flag is a loss-making year, or
negative FCF in the latest year. The Piotroski **F-score** is shown beside it: nine yes/no checks of
financial health, scored 0–9. The page then values the stock at each day's close (FCF yield, P/E
against its own median, PEG). It sorts the result into BUY ZONE / ACCUMULATE / WAIT, covered in
[valuation for traders](learn-fund-valuation.md). In October 2026, 275 of 1,500 scored US companies
and 278 of 819 Indian ones score 70 or more.

## 9. Worked examples from the stored filings

### Intel, 2021–2022: a LEADER verdict built on one-offs

Judged on what was known at the time, the quarter filed 2021-10-22 made Intel a **LEADER with Code
33**: EPS +64%, net margin up 12 points. The operating figures told another story. Operating margin
was 27.2%, against 27.6% a year earlier. Sales were up only 4.7%. About $1.6 billion of the $6.9
billion pretax profit came from outside the core business. The tax charge was $35 million — 0.5% of
pretax profit. The quarter filed 2022-04-29 repeated the pattern: EPS +141% on sales −6.7%. $5.3
billion of the $9.7 billion pretax profit came from outside the core business. Meanwhile gross margin
slid from 55% to 50% (and from 57% to 36% a quarter later).

```series
title: Intel — margins and sales growth turn, 2020–2023
from: 2020-07-01
to: 2023-06-30
line: us:INTC | Intel
line: us:fund.INTC.margin | Net margin, % | pane2 zero
line: us:fund.INTC.rev_g | Sales growth, % y/y | pane2
mark: 2021-10-22 | SEPA LEADER, Code 33
caption: The "leader" quarter flattered by non-operating gains and a near-zero tax charge. Intel was already 14% below its 200-day average that day, so the Trend Template excluded it; the stock bottomed at about $25 in October 2022, from $68 in April 2021.
```

### Muthoot Finance, 2024–2026: real expansion, late verdict (India)

Muthoot is a gold-loan lender, so "margin" here is net profit over total income. Net margin rose from
about 26% (late 2024) to 36% (filed May 2026). EPS growth accelerated from +14% to +127%. Sales growth
accelerated from +27% to +65%. The verdict climbed from ACCEPTABLE (F5 failing), to Code 33 in
November 2025, to **LEADER** on the filing of 2026-05-14, with ROE 31%.

```series
title: Muthoot Finance — accelerating growth, widening margin
from: 2024-01-01
to: 2026-10-13
line: india:MUTHOOTFIN.NS | Muthoot Finance
line: india:fund.MUTHOOTFIN.NS.margin | Net margin, % | pane2
line: india:fund.MUTHOOTFIN.NS.eps_g | EPS growth, % y/y | pane2 zero
mark: 2026-05-14 | SEPA LEADER
caption: The price roughly doubled from ₹1,816 (Aug 2024) to ₹3,393 at the Code 33 filing, peaked at ₹4,092 on 2026-01-29 — before the LEADER verdict — and was ₹2,626 by mid-October 2026, 37% off the top.
```

### Asian Paints, 2023–2025: deteriorating quality (India)

Net margin peaked at 16.9% in the quarter filed 2023-07-25. The stock had peaked at ₹3,544 the day
before. Over the next seven quarters, sales growth turned negative, EPS growth reached −45%, and net
margin fell to 8.3% (filed 2025-05-08). SEPA said WEAK throughout, with F8 failing in mid-2024. The
stock fell 40%, to ₹2,132 by March 2025.

```series
title: Asian Paints — margin and growth roll over
from: 2022-10-01
to: 2025-12-31
line: india:ASIANPAINT.NS | Asian Paints
line: india:fund.ASIANPAINT.NS.margin | Net margin, % | pane2
line: india:fund.ASIANPAINT.NS.rev_g | Sales growth, % y/y | pane2 zero
mark: 2023-07-25 | margin peak filed
caption: The high-water mark of the margin coincided with the high of the stock. Each later quarter confirmed the slide; the Quality page's annual view still scores it 80.
```

## 10. Red flags

- **One-off gains.** Bharti Airtel's December 2024 quarter had an exceptional gain of ₹7,546 crore.
  That was half its ₹15,232 crore pretax profit, and EPS rose 491%. Its March 2025 quarter had a tax
  *credit* of ₹2,892 crore, so net profit was larger than pretax profit. Vodafone Idea's March 2026
  quarter had an exceptional gain of +₹57,491 crore. It turned the usual quarterly loss of about
  ₹4,000–7,000 crore into a ₹51,970 crore profit. The app does not strip these out. So compare the
  growth in **operating profit** and **profit before tax** with EPS growth. And read the Exceptional
  items line on India's Quarters table.
- **Share-count dilution.** The app stores the share count each quarter. Vodafone Idea's grew from
  2,874 crore (2021) to 10,834 crore (2025) — about 3.8× — as it issued new shares. Worse, two of
  those issues were close to a 3:2 ratio. The app's split-detection code (`growth.split_factors`)
  reads that as a bonus issue, and so "adjusts" older EPS by 2.25×. The code itself warns of this
  ("a large share issue at such a ratio would be misread"). When the page says *EPS on today's share
  basis*, check there really was a split.
- **Derived quarters.** A US company does not file Q4 on its own. The app takes the full year less
  the first nine months (marked `derived`, about 16,500 of 76,000 US rows). So Q4 EPS is approximate.
- **Data glitches.** A quarter with zero or near-zero margin in an otherwise steady series (Solar
  Industries shows two) is usually a gap in reading the filing, not a collapse. Open the filing
  (`doc_url`).
- **Stale results.** No results for 200+ days turns the verdict into NO DATA. Find out why.

## 11. India specifics

- **Consolidated vs standalone (`basis`).** Consolidated figures include subsidiaries. Standalone
  figures cover the listed company alone. The app uses consolidated when a company files it for at
  least 75% of recent quarters (`CONSOLIDATED_SHARE`), and standalone otherwise. It **never mixes the
  two** within a company. 353 companies are consolidated, 34 standalone. For a holding company or a
  group with large subsidiaries, standalone numbers can be very different. The basis is printed
  beside the units.
- **NSE filings.** Quarterly results are due within 45 days of the quarter end, audited annual
  results within 60 days (SEBI's listing regulations). The app reads both NSE feeds: the legacy one,
  and the Integrated Filing from 2025. Indian filings carry no year-ago column, so growth is measured
  against the stored quarter a year earlier.
- **Shareholding (`shareholding` table, 381 companies).** The app stores the promoter and public
  share each quarter (from 2015). (The promoter is the founding family or parent company that
  controls the firm.) FII / DII shares come from the detailed filing, for the latest four quarters.
  How to read it: a **steadily rising promoter stake** (buying, or buybacks) shows the owners'
  confidence. A fall can mean new shares issued, a parent raising cash, or an exit — read the reason.
  Whirlpool of India's promoter went from 75% to 51% in the March 2024 quarter (the parent sold). The
  stock bottomed at ₹1,221 that month and reached ₹2,408 by October 2024. **Rising FII and DII
  together** over several quarters is O'Neil's "I". Changes under half a point are noise. Pledged
  shares (promoter shares put up as loan collateral) are not stored.

## 12. The evidence from this app's backtests

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

## 13. What the evidence says

- **Robust in the literature:** profitability and quality predict returns modestly (gross
  profitability, Novy-Marx; "quality minus junk", Asness et al.); high accruals predict weaker
  earnings (Sloan); post-earnings drift after big surprises is long documented.
- **Robust here:** fundamentals **lag** price. The verdicts for SMCI, Muthoot and NVIDIA (the later
  one) all came after or near a top. Asian Paints' margin peak was filed the day after its price
  peak.
- **Not shown here:** that requiring SEPA LEADER improves the Minervini breakouts. Filtering cut the
  number of trades and the CAGR. Within the US comparison group, WEAK did no worse than ACCEPTABLE.
- **Folklore:** that a perfect fundamental score makes a buy. Intel's Code 33 came from accounting
  items, not from the business. The Trend Template, not the fundamentals, kept it out.

## 14. Checklist

- [ ] Chart first: Stage 2, near highs, strong RS — fundamentals only rank the stocks that pass
- [ ] EPS and sales growth ≥ 25% / 20% and rising; check F8 for a two-quarter slowdown
- [ ] Margin up on the year-ago quarter — and operating profit growing with EPS, not behind it
- [ ] Exceptional items, other income and tax rate normal? (Quarters table)
- [ ] Cash from operations near net profit; inventory and receivables not outgrowing sales
- [ ] ROE ≥ 17% without heavy debt (Debt to equity, ROCE); no red flag on the Quality page
- [ ] Share count flat; a "split-adjusted" EPS backed by a real split or bonus
- [ ] India: basis (consolidated / standalone); promoter trend; FII + DII direction
- [ ] Results date known ([the calendar guide](learn-macro-calendar.md); gaps in
      [stops and exits](learn-risk-stops-exits.md)); group leadership in [sectors](learn-sectors-groups.md)

## Further reading

- William J. O'Neil, *How to Make Money in Stocks* — CAN SLIM from a study of big winners.
- Mark Minervini, *Trade Like a Stock Market Wizard* and *Think & Trade Like a Champion* — SEPA,
  earnings acceleration, Code 33.
- Richard Sloan (1996), "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows about
  Future Earnings?", *The Accounting Review*.
- Joseph Piotroski (2000), "Value Investing: The Use of Historical Financial Statement Information
  to Separate Winners from Losers", *Journal of Accounting Research* — the F-score.
- Robert Novy-Marx (2013), "The Other Side of Value: The Gross Profitability Premium", *Journal of
  Financial Economics*; Asness, Frazzini and Pedersen, "Quality Minus Junk".
- SEC EDGAR (sec.gov) for US 10-Q / 10-K filings; NSE (nseindia.com) corporate filings and SEBI's
  Listing Obligations and Disclosure Requirements regulations for India.
