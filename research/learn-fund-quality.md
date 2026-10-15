# Quality and the growth checklist — margins, returns, cash, and what CAN SLIM and SEPA ask for

**In short**

- To an investor, quality means a great business for years: high returns on capital, cash that matches profit, little debt. To a growth trader it means a business improving fast right now.
- Margin expansion drives earnings growth more than anything else. Check that cash from operations keeps up with reported profit.
- O'Neil's CAN SLIM and Minervini's SEPA ask for fast, accelerating EPS and sales growth, widening margins and a high return on equity. Both can be written as a checklist.
- Fundamentals lag the price. In the examples here, a perfect checklist score often arrived near or after the top.
- On US uptrend stocks since 2010, strong growth did not improve the next three months' return. In India since 2021 it did, but on a short and uneven sample.

This guide covers what "quality" means to a trader and to an investor. It explains margins, return on equity, debt and cash flow, then the CAN SLIM letters and Minervini's SEPA fundamentals as a checklist. It ends with worked examples, red flags, India specifics and what the evidence says about filtering on growth.

It is the third of three fundamentals guides, after [earnings that move stocks](learn-fund-earnings.md) and [valuation for traders](learn-fund-valuation.md).

---

## 1. Quality to a trader, quality to an investor

In October 2026 Asian Paints still looked excellent on five years of annual statements. Its returns were high, it had more cash than debt, and its margins were intact on an annual view. Yet its quarterly record from mid-2024 to early 2025 failed the growth tests every quarter (§9). Both views are right. They answer different questions.

An investor asks: **is this a great business I can own for years?** That means high returns on capital, steady growth, cash that matches profit, and little debt. The answer changes slowly, because it is read from annual statements.

A growth trader asks something narrower: **is the business improving fast enough, right now, that big funds will keep paying higher prices for it?** That means earnings and sales accelerating, and margins widening. The answer changes every quarter. And the price usually moves before the numbers are published.

| | Investor's quality | Trader's quality |
|---|---|---|
| Horizon | 5 years of annual statements | the last 4–8 quarters |
| Key numbers | ROIC (return on invested capital), FCF conversion (free cash flow ÷ profit), debt, steady growth | EPS / sales growth and its *acceleration*, margin trend |
| Tool | a long-term scorecard (§8.2) | a growth checklist (§8.1) |
| Typical failure | a great company bought at the wrong price | a great quarter bought after the stock has peaked |

For a swing trader the fundamentals are a **filter on the stocks whose chart already looks good**. They are never a reason to buy on their own.

## 2. What the filings give you

Everything in this guide comes from company filings: SEC XBRL data for the US and NSE results filings for India. The useful lines are:

| Statement | Lines |
|---|---|
| Profit and loss (quarterly and annual) | sales, expenses, operating profit, other income, interest, depreciation, profit before tax, tax, net profit, EPS; in India also exceptional items |
| Balance sheet | equity, reserves, borrowings, total assets and liabilities, fixed assets, cash, receivables, inventory, investments |
| Cash flow (annual) | cash from operations, investing and financing; capital spending (capex); dividends paid |

From these you can compute year-over-year EPS and sales growth per quarter, the **net margin** (net income ÷ revenue), trailing-twelve-month EPS, annual EPS growth over three years, and ROE. Growth is left blank when the year-ago figure is not positive. The charts in this guide date each quarter on the day it was filed.

**Operating profit means different things by market.** In US filings it is operating income, *after* depreciation. Indian data sites such as screener.in use sales less operating expenses, *before* other income, interest and depreciation. That is close to EBITDA (profit before interest, tax, depreciation and amortisation). So compare operating margin (OPM %) within a market, not across markets.

## 3. Margins — and margin expansion

Take a company growing sales 30% while its net margin widens from 10% to 15%. Its profit grows about 95%. When sales rise faster than costs, profit grows faster than sales. This is called **operating leverage**.

- **Gross margin** = (sales − cost of goods) ÷ sales. It reflects pricing power and product mix.
- **Operating margin** = operating profit ÷ sales: what is left after running the business.
- **Net margin** = net profit ÷ sales: what is left after interest and tax — and one-offs.

**Margin expansion drives earnings growth more than anything else.** That is why a growth checklist asks for a net margin above the year-ago quarter. Minervini's "Code 33" asks for margins rising three quarters running.

```series
title: NVIDIA — net margin and sales growth, 2022–2024
from: 2022-06-01
to: 2024-12-31
line: us:NVDA | NVIDIA | log
line: us:fund.NVDA.margin | Net margin, % | pane2
line: us:fund.NVDA.rev_g | Sales growth, % y/y | pane2 zero
mark: 2023-05-26 | Q1 FY24 filed
mark: 2024-02-21 | passes the growth checklist
caption: Net margin went from about 10% (filed Aug 2022) to 57% (May 2024) while sales growth swung from −21% to +265%. The price led: about $39 on 2023-05-26, $67 when the checklist verdict reached "leader", $115 by 2024-05-29.
```

Note what the mechanical checklist of §8.1 did next. By the filing of 29 May 2024, EPS growth had "slowed":

| Quarter | EPS growth, y/y |
|---|---|
| Filed Nov 2023 | +1,274% |
| Filed Feb 2024 | +774% |
| Filed May 2024 | +629% |

So the acceleration and no-slowdown tests failed, and the verdict fell to **weak**, even though margins were at their peak. The stock still rose to about $149 in November 2024, after a 27% drawdown from June to August. When growth is extreme, it has to slow down eventually. That slowdown is arithmetic, not always a warning.

## 4. Return on equity (and on capital)

**ROE** = net profit ÷ shareholders' equity: how much the business earns on the owners' money. O'Neil and Minervini both ask for **17%+**. A common way to compute it: the last twelve months' net income, divided by the average of the latest equity and the equity a year earlier.

ROE can look better than the business really is. **Debt** makes equity small relative to assets. **Buybacks or big dividends** shrink equity itself. Nestlé India shows an ROE of about 82% (standalone filings), largely because it pays out most of its profit. So look also at measures that include debt:

| Measure | Formula |
|---|---|
| ROE | trailing-twelve-month net income ÷ average equity |
| ROCE | (profit before tax + interest) ÷ (equity + borrowings) at the year end |
| ROIC | EBIT × (1 − tax rate) ÷ invested capital, per year |

## 5. Debt and interest cover

Debt makes a good year better. In a bad year it can end a company. Two numbers:

- **Net debt ÷ EBITDA** — how many years of operating cash profit it would take to repay borrowings, after subtracting cash. A common test passes at **2× or less**, or when the company has more cash than debt (net cash).
- **Interest cover** = EBIT (operating profit before interest and tax) ÷ interest expense. A common test wants **8× or more**.

**Debt to equity** (borrowings ÷ equity) is the simplest check. Banks and insurers skip these tests: lending borrowed money is their business.

## 6. Cash flow against reported earnings (accruals)

Super Micro Computer is the textbook case. Its reported profit nearly doubled in fiscal 2024. Its cash from operations went deeply negative, while inventory tripled.

| Fiscal year (June) | Net profit | Cash from operations | Inventory at year end |
|---|---|---|---|
| FY2023 | $640M | $664M | $1,446M |
| FY2024 | $1,153M | **−$2,486M** | $4,333M |
| FY2026 | $2,230M | **−$6,810M** | $12,896M |

Profit depends on accounting choices; cash in the bank does not. The gap between net income and **cash from operations** (CFO) is called **accruals**. It is made of things like bills customers have not yet paid, inventory not yet sold, and costs recorded as assets instead of expenses. Accruals that stay high predict weaker future earnings (Sloan, 1996).

**Free cash flow** (FCF) is CFO minus capital spending. A long-term scorecard typically wants FCF positive every year, adding up to at least **80%** of net income. Negative FCF in the latest year is a **red flag** that overrides any score.

```series
title: Super Micro — the SEPA verdict arrived after the top
from: 2023-01-01
to: 2025-06-30
line: us:SMCI | Super Micro | log
line: us:fund.SMCI.margin | Net margin, % | pane2
line: us:fund.SMCI.rev_g | Sales growth, % y/y | pane2 zero
mark: 2024-03-13 | price peak
mark: 2024-05-06 | passes, with Code 33
caption: The quarter filed on 2024-05-06 passed every growth test, with Code 33 — seven weeks after the $119 peak, with the stock already 30% off it. It fell about 85% peak to trough by November 2024. Operating cash flow for that fiscal year was −$2.5 billion.
```

The long-term scorecard of §8.2 catches this. SMCI scores 70, but it carries the red flag *negative free cash flow in the latest year*, and its Piotroski F-score is 2. So it is not "high quality". The quarterly growth tests never look at cash.

Minervini's Trend Template (his chart checklist) did its job too. On 6 May 2024 the price was 68% above its 200-day average and 30% below its high. The template allows at most 25% below the high, so the stock failed it.

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

**SEPA** (Mark Minervini) has five parts: trend (the Stage 2 Trend Template), fundamentals, catalyst, entry point and exit. His entry point is the VCP (volatility contraction pattern: a base whose pullbacks get smaller and quieter). The trading side is in [learn-strat-vcp-sepa](learn-strat-vcp-sepa.md).

SEPA's fundamental part is close to O'Neil's C and A. It puts more weight on **acceleration**, **margin expansion** and **beating estimates**. And it names one warning sign: two quarters of significant deceleration. "Code 33" is his shorthand for EPS growth, sales growth and margins all accelerating three quarters in a row.

## 8. Turning them into checklists

### 8.1 A growth checklist (CAN SLIM / SEPA)

One way to write the books' fundamentals as tests a program can check:

| Test | Rule |
|---|---|
| F1 EPS growth | latest quarter's EPS up at least **25%** on the year-ago quarter |
| F2 EPS accelerating | the growth rate rose in at least **2** of the last **3** quarters |
| F3 Sales growth | latest sales up at least **20%**, or sales growth rising **3** quarters running |
| F4 Margins expanding | net margin above the same quarter a year earlier |
| F5 Annual EPS growth | at least **25%** a year over **3** fiscal years, no loss-making year |
| F6 Return on equity | trailing-twelve-month ROE at least **17%** |
| F7 Beat estimates | latest EPS above the consensus estimate |
| F8 No slowdown | growth has not slowed two quarters running by **15** points or more |

The verdicts used in this guide:

- **Leader** — F1, F2, F3, F4 and F8 pass, and F5 and F6 pass or cannot be computed.
- **Acceptable** — F1, F3 and F8 pass.
- **Weak** — anything else.
- **No data** — fewer than **2** of the last four quarters have an EPS growth reading, or the latest results are more than 200 days old.
- **Code 33** — EPS growth, sales growth and net margin all rising for **3** quarters.

Its built-in limits: growth from a loss cannot be measured, so turnarounds fail F1. **One-off gains and charges are not removed.** And a history of past analyst estimates is hard to get, so F7 often cannot be tested.

### 8.2 A long-term quality scorecard

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

Banks and insurers skip the margin, margin trend, cash conversion and balance-sheet tests. Their score is rescaled to 100. **High quality = 70+ and no red flag.** A red flag is a loss-making year, or negative FCF in the latest year.

The Piotroski **F-score** is a useful companion: nine yes/no checks of financial health, scored 0–9. Pairing the scorecard with a valuation is covered in [valuation for traders](learn-fund-valuation.md).

## 9. Worked examples from the filings

### Intel, 2021–2022: a "leader" verdict built on one-offs

Judged on what was known at the time, the quarter filed 22 October 2021 made Intel a **leader with Code 33**. EPS was up 64%, and net margin up 12 points. The operating figures told another story:

| Quarter filed | EPS growth | Sales growth | Pretax profit | … of which outside the core business |
|---|---|---|---|---|
| 22 Oct 2021 | +64% | +4.7% | $6.9 billion | about $1.6 billion |
| 29 Apr 2022 | +141% | −6.7% | $9.7 billion | $5.3 billion |

In the October 2021 quarter, operating margin was 27.2%, against 27.6% a year earlier. The tax charge was $35 million, or 0.5% of pretax profit. Meanwhile gross margin slid from 55% to 50%. In the next quarter's comparison it slid from 57% to 36%.

```series
title: Intel — margins and sales growth turn, 2020–2023
from: 2020-07-01
to: 2023-06-30
line: us:INTC | Intel
line: us:fund.INTC.margin | Net margin, % | pane2 zero
line: us:fund.INTC.rev_g | Sales growth, % y/y | pane2
mark: 2021-10-22 | passes, with Code 33
caption: The "leader" quarter flattered by non-operating gains and a near-zero tax charge. Intel was already 14% below its 200-day average that day, so the Trend Template excluded it; the stock bottomed at about $25 in October 2022, from $68 in April 2021.
```

### Muthoot Finance, 2024–2026: real expansion, late verdict (India)

Muthoot is a gold-loan lender, so "margin" here is net profit over total income.

| | Late 2024 | Filed May 2026 |
|---|---|---|
| Net margin | about 26% | 36% |
| EPS growth | +14% | +127% |
| Sales growth | +27% | +65% |

The verdict climbed from acceptable (F5 failing), to Code 33 in November 2025. It reached **leader** on the filing of 14 May 2026, with ROE 31%.

```series
title: Muthoot Finance — accelerating growth, widening margin
from: 2024-01-01
to: 2026-10-13
line: india:MUTHOOTFIN.NS | Muthoot Finance
line: india:fund.MUTHOOTFIN.NS.margin | Net margin, % | pane2
line: india:fund.MUTHOOTFIN.NS.eps_g | EPS growth, % y/y | pane2 zero
mark: 2026-05-14 | passes the growth checklist
caption: The price roughly doubled from ₹1,816 (Aug 2024) to ₹3,393 at the Code 33 filing, peaked at ₹4,092 on 2026-01-29 — before the "leader" verdict — and was ₹2,626 by mid-October 2026, 37% off the top.
```

### Asian Paints, 2023–2025: deteriorating quality (India)

Net margin peaked at 16.9% in the quarter filed 25 July 2023. The stock had peaked at ₹3,544 the day before. Over the next seven quarters, sales growth turned negative and EPS growth reached −45%. Net margin fell to 8.3% (filed 8 May 2025).

The checklist said weak throughout, with F8 failing in mid-2024. The stock fell 40%, to ₹2,132 by March 2025.

```series
title: Asian Paints — margin and growth roll over
from: 2022-10-01
to: 2025-12-31
line: india:ASIANPAINT.NS | Asian Paints
line: india:fund.ASIANPAINT.NS.margin | Net margin, % | pane2
line: india:fund.ASIANPAINT.NS.rev_g | Sales growth, % y/y | pane2 zero
mark: 2023-07-25 | margin peak filed
caption: The high-water mark of the margin coincided with the high of the stock. Each later quarter confirmed the slide; the long-term scorecard of §8.2, built on annual statements, still rates it 80.
```

## 10. Red flags

- **One-off gains.** Bharti Airtel's December 2024 quarter had an exceptional gain of ₹7,546 crore. That was half its ₹15,232 crore pretax profit, and EPS rose 491%. Its March 2025 quarter had a tax *credit* of ₹2,892 crore, so net profit was larger than pretax profit.
- **More one-offs.** Vodafone Idea's March 2026 quarter had an exceptional gain of +₹57,491 crore. It turned the usual quarterly loss of about ₹4,000–7,000 crore into a ₹51,970 crore profit. A growth checklist does not strip these out. So compare the growth in **operating profit** and **profit before tax** with EPS growth, and read the exceptional items line.
- **Share-count dilution.** Vodafone Idea's share count grew from 2,874 crore (2021) to 10,834 crore (2025), about 3.8×, as it issued new shares. Two of those issues were close to a 3:2 ratio. A program that detects splits from share counts can read that as a bonus issue and wrongly "adjust" older EPS. When a data source says *EPS on today's share basis*, check there really was a split.
- **Derived quarters.** A US company does not file Q4 on its own. Data sources take the full year less the first nine months, so Q4 EPS is approximate.
- **Data glitches.** A quarter with zero or near-zero margin in an otherwise steady series (Solar Industries shows two) is usually a gap in reading the filing, not a collapse. Open the filing.
- **Stale results.** No results for 200+ days. Find out why.

## 11. India specifics

- **Consolidated vs standalone.** Consolidated figures include subsidiaries. Standalone figures cover the listed company alone. Pick one basis per company and **never mix the two**: growth computed across a switch is meaningless. For a holding company or a group with large subsidiaries, standalone numbers can be very different.
- **NSE filings.** Quarterly results are due within 45 days of the quarter end, and audited annual results within 60 days (SEBI's listing regulations). Indian filings carry no year-ago column, so growth is measured against the quarter a year earlier.
- **Shareholding.** Companies report the promoter and public share each quarter. (The promoter is the founding family or parent company that controls the firm.) A **steadily rising promoter stake** (buying, or buybacks) shows the owners' confidence. A fall can mean new shares issued, a parent raising cash, or an exit — read the reason.
- **An example.** Whirlpool of India's promoter went from 75% to 51% in the March 2024 quarter (the parent sold). The stock bottomed at ₹1,221 that month and reached ₹2,408 by October 2024.
- **FII and DII.** **Rising FII and DII holdings together** over several quarters is O'Neil's "I". Changes under half a point are noise. Also check pledged shares (promoter shares put up as loan collateral) in the exchange filing.

## 12. Does a growth filter help? The evidence

**Published research.** Several fundamental signals predict returns modestly across all stocks:

- **Profitability.** Gross profit relative to assets predicts higher returns (Novy-Marx, 2013).
- **Quality.** Profitable, growing, safe companies earn more than "junk" (Asness, Frazzini and Pedersen).
- **Accruals.** Profit not backed by cash predicts weaker earnings and returns (Sloan, 1996).
- **Financial health.** Piotroski's F-score separated winners from losers among cheap stocks. Mohanram's G-score did the same among growth stocks, using profitability, earnings stability and spending on research and advertising.

O'Neil's studies began from the biggest winners and recorded what they had in common. That shows what winners looked like, not how often stocks with those traits went on to win.

**An event study on growth among uptrend stocks.** Method: at each month end, take stocks in a Trend-Template-style uptrend:

- the close is above the 200-day average, and the 50-day is above the 200-day;
- the close is within 25% of its 52-week high;
- the close is at least 30% above its 52-week low.

Read the latest quarter filed by that date. Measure the next 63 sessions' return minus the benchmark (SPY for the US, the Nifty 500 for India).

| Filed quarter, uptrend stocks | US stock-months | US median excess | US share beating | India stock-months | India median excess | India share beating |
|---|---|---|---|---|---|---|
| All with a recent filing | 85,199 | −0.2% | 49.3% | 8,609 | +1.7% | 54.3% |
| EPS growth ≥ 25% | 27,352 | −0.1% | 49.7% | 3,126 | +2.7% | 56.5% |
| … and sales growth ≥ 20% | 9,260 | −0.4% | 48.9% | 1,739 | +3.8% | 58.6% |
| … and margin up | 8,589 | −0.3% | 49.2% | 1,231 | +3.8% | 59.2% |
| … and EPS growth accelerating | 5,005 | −0.4% | 48.7% | 675 | +5.0% | 60.6% |
| None of the four | 21,105 | −0.5% | 48.5% | 3,155 | +1.2% | 52.6% |

The US sample runs from January 2010 to June 2026, in 1,542 companies. India's runs from January 2021 to June 2026, in 362 companies.

**In the US, the growth tests made no difference.** Uptrend stocks with every growth test passed did no better over the next three months than those with none. The price trend had already done the sorting.

**In India, the tests lined up in order.** Stocks passing all four beat the Nifty 500 by about 5% at the median, against about 1% for stocks passing none. But the sample is five and a half years of a strong market for mid and small caps. Year by year it is uneven: in 2022 the stocks passing all four lagged the index.

## 13. What the evidence says

- **Robust in the literature:** profitability and quality predict returns modestly (Novy-Marx; Asness et al.). High accruals predict weaker earnings (Sloan). Post-earnings drift after big surprises is long documented.
- **Robust in the examples:** fundamentals **lag** price. The checklist verdicts for SMCI, Muthoot and NVIDIA (the later one) all came after or near a top. Asian Paints' margin peak was filed the day after its price peak.
- **Mixed:** whether a growth filter improves a price-based selection. On US uptrend stocks it added nothing over three months; in India since 2021 it helped, on a short sample.
- **Folklore:** that a perfect fundamental score makes a buy. Intel's Code 33 came from accounting items, not from the business. The Trend Template, not the fundamentals, kept it out.
- **Limits of the event study:** today's companies only (survivorship); no costs; month-end samples overlap, so they are not independent; one-offs are not removed; a three-month horizon may miss slower effects.

## 14. Checklist

- [ ] Chart first: Stage 2, near highs, strong RS — fundamentals only rank the stocks that pass
- [ ] EPS and sales growth ≥ 25% / 20% and rising; no two-quarter slowdown
- [ ] Margin up on the year-ago quarter — and operating profit growing with EPS, not behind it
- [ ] Exceptional items, other income and tax rate normal?
- [ ] Cash from operations near net profit; inventory and receivables not outgrowing sales
- [ ] ROE ≥ 17% without heavy debt (debt to equity, ROCE); no red flag (loss year, negative FCF)
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
- Partha Mohanram (2005), "Separating Winners from Losers among Low Book-to-Market Stocks using
  Financial Statement Analysis", *Review of Accounting Studies* — the G-score.
- Robert Novy-Marx (2013), "The Other Side of Value: The Gross Profitability Premium", *Journal of
  Financial Economics*; Asness, Frazzini and Pedersen, "Quality Minus Junk".
- SEC EDGAR (sec.gov) for US 10-Q / 10-K filings; NSE (nseindia.com) corporate filings and SEBI's
  Listing Obligations and Disclosure Requirements regulations for India.
