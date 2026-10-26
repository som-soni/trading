# Reading a quarterly report — beyond the headline

**In short**

- Headline growth says how fast profit grew. The lines underneath say whether that growth is real and whether it can last.
- Six checks go past the headline: where profit came from, gross margin, inventory, receivables, cash and the share count. Each compares one line with sales or with profit.
- Inventory growing much faster than sales is the classic warning. Target in 2022 is the textbook case; NVIDIA in 2023 is the case where it was wrong.
- Measured on US filings, the warnings point the right way but are small and uneven. A falling gross margin was the most consistent. The inventory warning held only in recent years.
- Use the checks to decide how far to trust a strong quarter, not as buy or sell signals. The price makes the final call.

[Earnings that move stocks](learn-fund-earnings.md) covers the headline: growth, acceleration, surprises and the results-day move. This guide reads the rest of the report. It asks one question of every strong quarter: is the growth coming from the business, or from something that will not repeat?

[Quality and the growth checklist](learn-fund-quality.md) explains margins, returns on capital, debt and cash flow in general. Here the same lines are used as a routine for each new report. Every figure below comes from company filings, and the method of each measurement is stated with it.

---

## 1. A record year with a warning inside — Target, 2021

Target's fiscal year ended on 29 January 2022. Sales rose 13%, a strong year for one of America's largest retailers. Net profit reached a record $6.95 billion, up 59%. The headline could hardly have looked better.

Two lines underneath disagreed.

| Fiscal year ending | Jan 2021 | Jan 2022 | Change |
|---|---|---|---|
| Sales | $93.6 bn | $106.0 bn | +13% |
| Net profit | $4.37 bn | $6.95 bn | +59% |
| **Inventory at year end** | $10.65 bn | $13.90 bn | **+31%** |
| **Cash from operations** | $10.53 bn | $8.63 bn | **−18%** |

**Inventory** is goods bought but not yet sold. It grew more than twice as fast as sales. That means one of two things. Either the company expects sales to speed up, or goods are piling up that customers are not buying.

Cash pointed the same way. Profit rose by more than half, but the cash the business brought in fell by almost a fifth. Much of the swing was sitting in the warehouse as unsold stock.

```series
title: Target, 2021–2023, with net margin as filed
from: 2021-07-01
to: 2023-06-30
line: us:TGT | Target
line: us:fund.TGT.margin | Net margin, % (as filed) | pane2 zero
mark: 2022-05-18 | results: −25%
caption: Net margin fell from about 6% in late 2021 to under 1% by mid-2022. The stock gapped down 24% at the open on 18 May 2022 and was 31% lower a year after the annual figures were public, while the S&P 500 ETF was flat.
```

The next two quarters showed what the warning meant.

| Quarter ending | Sales growth | Operating profit | A year earlier |
|---|---|---|---|
| Apr 2022 | +4% | $1.35 bn | $2.37 bn |
| Jul 2022 | +3.5% | $0.32 bn | $2.47 bn |

Sales kept growing, slowly. But the goods bought for a demand that had faded had to be sold at lower prices. In early June 2022 the company said it would cut prices and cancel orders to clear the excess. Operating profit fell 43% and then 87%.

On 18 May 2022 the stock opened at $163.07, against $215.28 the evening before. A trader who had read the balance sheet in March was not surprised by the direction. Nobody could have known the date.

## 2. The six checks

Each check compares one line of the report with sales or with profit. A gap between them is the question to answer.

| Check | Compare | Warning sign | What it can mean |
|---|---|---|---|
| 1. Where profit came from | EPS growth with pre-tax profit growth | EPS growing much faster | A lower tax rate, fewer shares, other income or a one-off gain |
| 2. Gross margin | Gross profit ÷ sales, against a year earlier | Falling while sales rise | Discounting, rising costs or a weaker product mix |
| 3. Inventory | Inventory growth with sales growth | Inventory growing 10+ points faster | Goods piling up; price cuts ahead |
| 4. Receivables | Receivables growth with sales growth | Receivables growing 10+ points faster | Customers paying slower, or sales pulled forward on easy terms |
| 5. Cash | Cash from operations with net profit | Profit rising, cash flat or falling | Profit not yet turning into cash |
| 6. Share count | Diluted shares, against a year earlier | Shares falling fast, or rising fast | Buybacks lifting EPS; new shares diluting it |

### Check 1 — where the profit came from

Start from the top. Sales pay for the costs of making and selling. What remains is **operating profit**, the profit of the business itself. Below it come interest, other income, one-off items and tax. Then EPS divides what is left by the number of shares.

If EPS grew 40% but pre-tax profit grew 10%, the extra came from below the line. A lower tax rate, a smaller share count or an investment gain can all do it. None of them is the business growing.

Indian results show an **exceptional items** line and **other income** separately. Read both. [Quality and the growth checklist](learn-fund-quality.md) has two Indian cases where a single exceptional gain was larger than a whole year's normal profit.

### Check 2 — gross margin

**Gross margin** is gross profit (sales minus the direct cost of the goods) divided by sales. It is the first line to show discounting. A retailer that cuts prices to clear stock, or a maker whose input costs jump, shows it here before anywhere else.

A strong quarter with a falling gross margin means profit grew *despite* the core economics getting worse. Usually a cost cut lower down covered it. That can work for a quarter or two.

Indian results do not print a gross profit line. Sales minus the cost of materials, purchases of finished goods and the change in inventories is a close stand-in.

### Check 3 — inventory against sales

Compare the two growth rates:

```
inventory gap (points) = inventory growth % − sales growth %
inventory days         = inventory ÷ yearly sales × 365
```

A gap above about +10 points deserves an explanation. **Inventory days** tells the same thing in another form: how many days of sales are sitting in stock. Rising days mean stock is turning over more slowly.

There are good reasons for a build-up. A company may be stocking up for a product launch, a new customer or a season. The test is whether something in the report backs that up: higher guidance, new orders, or sales already accelerating. Target had none of these. NVIDIA, in section 3, did.

### Check 4 — receivables against sales

**Receivables** are sales already booked but not yet paid for. If they grow much faster than sales, customers are taking longer to pay. Or the company may be shipping on generous terms to make the quarter's number.

**Debtor days** (receivables ÷ yearly sales × 365) shows how long customers take to pay. A sudden jump is worth a question. For banks and lenders this check does not apply: their receivables are their loans.

### Checks 5 and 6 — cash and the share count

Cash from operations should, over a year or two, roughly match net profit, and move with it. At Target in 2021 profit rose while cash fell, and the inventory build-up explains much of it. Super Micro Computer in 2024 was starker: profit up, operating cash deeply negative. [Quality and the growth checklist](learn-fund-quality.md) works through that case and the measure behind it, called accruals.

The share count matters because EPS is profit *per share*. A company buying back 5% of its shares lifts EPS by about 5% with no growth at all. A company issuing many new shares does the opposite. Compare EPS growth with net profit growth; a big gap is the share count at work.

### When to check

US companies file a balance sheet every quarter. Indian companies publish one twice a year, with the September and March results. So in India the inventory and receivables checks can be run only every second quarter.

## 3. When the warning is wrong — NVIDIA, 2023

NVIDIA's fiscal year ended on 29 January 2023. On the inventory check it looked worse than Target.

| Fiscal year ending | Jan 2022 | Jan 2023 | Jan 2024 |
|---|---|---|---|
| Sales | $26.9 bn | $27.0 bn | $60.9 bn |
| Sales growth | +61% | +0% | +126% |
| Inventory at year end | $2.61 bn | $5.16 bn | $5.28 bn |
| Inventory growth | +43% | **+98%** | +2% |

Inventory nearly doubled on flat sales. Earlier in the year, demand for gaming chips had slumped. In the quarter to July 2022, gross margin fell from about 65% to about 44% as the company wrote down stock.

```series
title: NVIDIA, 2022–2024, with sales growth as filed
from: 2022-01-01
to: 2024-06-30
line: us:NVDA | NVIDIA | log
line: us:fund.NVDA.rev_g | Sales growth, % y/y (as filed) | pane2 zero
mark: 2023-05-25 | results + guidance: +24%
caption: The inventory warning was at its loudest in early 2023. A year after the annual figures were public, the stock had more than tripled while the S&P 500 ETF rose 22%.
```

Then demand for chips to run artificial intelligence arrived. On 25 May 2023 the company's forecast for the next quarter far exceeded expectations. The stock built for that demand sold, and sales more than doubled the next year.

The lesson is not that the inventory check failed. It flagged a real risk, and the gross margin had already shown the cost. What changed the outcome was new demand that nobody's balance sheet could show in advance. **The guidance was the line that answered the question the inventory raised.**

## 4. India — Dixon Technologies, 2024

Dixon assembles phones and electronics for other brands. In the year to March 2024 it was adding customers and production lines fast.

| Fiscal year ending | Mar 2023 | Mar 2024 | Mar 2025 |
|---|---|---|---|
| Sales | ₹12,192 cr | ₹17,691 cr | ₹38,860 cr |
| Sales growth | +14% | +45% | +120% |
| Inventory at year end | ₹958 cr | ₹1,695 cr | ₹3,992 cr |
| Inventory growth | — | **+77%** | +136% |

Inventory ran 32 points ahead of sales. Here the build-up came ahead of fast-rising demand, and sales more than doubled the next year. The stock rose 50% in the six months from the end of June 2024, while the Nifty 500 was flat.

```series
title: Dixon Technologies, 2023–2025, with sales growth as filed
from: 2023-06-01
to: 2025-06-30
line: india:DIXON.NS | Dixon Technologies | log
line: india:fund.DIXON.NS.rev_g | Sales growth, % y/y (as filed) | pane2 zero
mark: 2024-12-17 | peak
caption: Sales growth kept rising through 2024 as inventory built up. The stock peaked on 17 December 2024, about 58% above its level at the end of June.
```

The checks are the same in India. The answer still depends on what the rest of the report says about demand.

## 5. Traps when reading the lines

- **Acquisitions.** Crocs bought the HEYDUDE brand in early 2022. Its year-end inventory rose 121% against sales growth of 54%. Both lines included the newly bought business, so the gap said little about either brand. Compare growth without the acquisition where the company reports it.
- **Seasons.** Inventory swings with the season. Compare a balance sheet with the one a year earlier, never with the last quarter's.
- **Supply shocks.** In 2021 and 2022 many companies stocked up on purpose as supply chains broke down. Part of every build-up in those years was deliberate.
- **Banks and lenders.** They have no inventory, and their receivables are their loans. Their quality checks are different: bad loans, provisions and deposit growth.
- **Data errors.** A machine-read filing can be wrong by a factor of a thousand. If a ratio looks impossible, open the filing before drawing a conclusion.

## 6. What the growth books add

Mark Minervini's *Trade Like a Stock Market Wizard* asks for earnings that accelerate with sales and margins together. The headline side of his approach is in [Earnings that move stocks](learn-fund-earnings.md). He also looks under the headline. One of his checks is inventory against sales: stock growing faster than sales warns that demand may be slowing.

William O'Neil's *How to Make Money in Stocks* makes a related point: strong EPS growth should be backed by strong sales growth. Sales are also the line hardest for a company to manage.

Both writers studied big winners and described what their numbers looked like. That shows what to look for. It does not show how often a stock with those numbers went on to win. The next section measures that.

## 7. What the evidence says

**Published research.** Lev and Thiagarajan (1993) listed the signals analysts use, among them inventory and receivables growing faster than sales and a falling gross margin. They found these signals carry information about value beyond the earnings figure itself. Abarbanell and Bushee (1997, 1998) found several of the same signals helped predict future earnings, and that a strategy built on them earned excess returns. Thomas and Zhang (2002) found that companies whose inventory rose unusually fast went on to lower returns.

**On stored US filings — inventory.** Each event is a fiscal year with both years' sales and year-end inventory stored. It is treated as public 90 days after the year end. The outcome is the stock's return over the next 252 sessions, minus the S&P 500 ETF's. The sample is fiscal years 2017 to 2025.

Across all companies, the inventory gap made no consistent difference. Among fast growers — sales up 20% or more — it did:

| Inventory growth minus sales growth (sales +20% or more) | Events | Median excess, next 12 months | Beat the market |
|---|---|---|---|
| Leaner than sales (below −10 points) | 757 | +1.0% | 52% |
| In line (−10 to +10) | 341 | +0.2% | 50% |
| Ahead (+10 to +30) | 198 | −1.1% | 49% |
| Far ahead (above +30) | 227 | −7.5% | 44% |

*1,523 events from 727 companies.*

That looks like a clean result. Split by period, it is not:

| Fiscal years | Far ahead: median | Far ahead: beat | Everything else: median | Everything else: beat |
|---|---|---|---|---|
| 2017–2020 | +2.7% | 51% | −6.9% | 46% |
| 2021–2025 | −9.8% | 41% | +2.2% | 53% |

The whole effect comes from 2021–2025, the years of supply shocks and the inventory glut that followed. In the earlier years it went the other way.

Inventory build-ups also did not predict slower sales. Fast growers whose inventory ran far ahead grew sales *faster* the next year, not slower. Companies building stock were usually right about demand. The stock price, on average, still did worse in the recent years.

**On stored US filings — the quality of a strong quarter.** These events are quarters with EPS up 25% or more on a year earlier, from 2009 to 2026. The outcome is the return over the next 60 sessions, starting two sessions after the filing, minus the S&P 500 ETF's.

| Strong quarter (EPS +25% or more) | Events | Median excess, next 60 sessions | Beat the market |
|---|---|---|---|
| Gross margin up 1 point or more | 3,556 | −0.1% | 50% |
| Gross margin within 1 point | 2,654 | +0.4% | 52% |
| Gross margin down 1 point or more | 885 | −1.2% | 46% |
| EPS growth within 15 points of pre-tax profit growth | 7,361 | 0.0% | 50% |
| EPS growth more than 15 points above pre-tax growth | 4,880 | −0.3% | 49% |

A falling gross margin was the most consistent warning. Split into three periods, it did worse than a rising margin in each one. The difference was small, about one to two points over three months. EPS growth outrunning pre-tax profit made almost no difference.

**Receivables** showed no consistent pattern, in any group. **India** has stored half-yearly balance sheets only from late 2022. That gives a few dozen events per group and no consistent pattern, so it is too early to say.

**Limits.** The samples are today's companies, so failed and delisted ones are missing. The 90-day delay is an assumption, not each company's filing date. The 12-month windows of different events overlap, so they are not independent. No trading costs are included. Education, not advice.

## 8. A template for each quarter

Run this on every results filing of a stock you hold or plan to buy.

- [ ] **Headline:** EPS and sales growth on the year-ago quarter. Accelerating or slowing over the last 4 quarters?
- [ ] **Check 1 — source:** pre-tax profit growth close to EPS growth? Any exceptional items, other income or tax change?
- [ ] **Check 2 — gross margin:** up, flat or down against the year-ago quarter?
- [ ] **Check 3 — inventory:** inventory growth minus sales growth. Above +10 points? If so, what explains it — guidance, orders, a launch?
- [ ] **Check 4 — receivables:** receivables growth minus sales growth. Debtor days rising?
- [ ] **Check 5 — cash:** cash from operations near net profit over the last year?
- [ ] **Check 6 — shares:** EPS growth close to net profit growth? Any large buyback or new issue?
- [ ] **Distortions:** an acquisition, a one-off, a season or a data error behind any odd figure?
- [ ] **Guidance:** what did management say about the next quarter, and does it answer the questions above?
- [ ] **Verdict:** how far do I trust this quarter's growth — fully, partly or not at all?
- [ ] **Price:** did the stock confirm the report or reject it?

## Further reading

- Mark Minervini, *Trade Like a Stock Market Wizard* (2013) — SEPA's fundamentals and the quality of earnings.
- William J. O'Neil, *How to Make Money in Stocks* — CAN SLIM's "C" and "A".
- Baruch Lev and S. Ramu Thiagarajan, "Fundamental Information Analysis", *Journal of Accounting Research* (1993).
- Jeffery Abarbanell and Brian Bushee, "Fundamental Analysis, Future Earnings, and Stock Prices", *Journal of Accounting Research* (1997).
- Jeffery Abarbanell and Brian Bushee, "Abnormal Returns to a Fundamental Analysis Strategy", *The Accounting Review* (1998).
- Jacob Thomas and Huai Zhang, "Inventory Changes and Future Returns", *Review of Accounting Studies* (2002).
- Richard Sloan, "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows about Future Earnings?", *The Accounting Review* (1996).
