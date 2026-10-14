# Earnings that move stocks — growth, acceleration and the results-day reaction

Learning material: what a quarterly report contains, why growth is measured
year over year, why **accelerating** earnings and sales sit behind most big
winners, what a "beat" really means, and how big the results-day move
usually is. Every reaction figure here was measured on the app's own stored
prices and filing dates, with the method stated.

**Where this shows in the app.** Each stock's **Fundamentals** view (next to
Chart and News) shows the last 12 quarters and a **Minervini SEPA** section
that applies eight growth tests to the filings (`scripts/fundamentals/growth.py`
holds the shared numbers, `fundamentals/sepa.py` the tests). The Chart marks
past results with an "E", **News & events** lists the next report, and
**Markets → Post-market** has an *Earnings in the next 10 days* card. Earnings
season and the strategies' earnings gates are in the
[calendar guide](learn-macro-calendar.md); valuation in
[learn-fund-valuation.md](learn-fund-valuation.md); margins, returns and the
full growth checklist in [learn-fund-quality.md](learn-fund-quality.md).

---

## 1. What a quarterly report contains

| Line | What it is | Why it matters |
|---|---|---|
| **Revenue (sales)** | What customers paid | Hard to fake; growth has to start here |
| **Net income** | What is left after all costs, interest and tax | The bottom line |
| **EPS** | Net income per share (diluted) | What O'Neil and Minervini measure |
| **Margins** | Net income ÷ revenue (also gross, operating) | Rising margins = each sale earns more |
| **Guidance** | Management's forecast for next quarter or year | Often moves the stock more than the quarter |

**GAAP against adjusted.** Filed numbers follow the accounting rules (**GAAP**
in the US, **Ind AS** in India). Most US companies also publish an
**adjusted** EPS that leaves out stock-based pay, acquisition amortisation and
restructuring charges. Analysts forecast the adjusted figure, so headlines
("beat by 5 cents") compare adjusted with adjusted. Adjusted removes real
one-off noise, but can also leave out costs that recur every year. The app's
growth figures come from the **filings** (SEC XBRL for the US, NSE XBRL for
India), so they are GAAP / Ind AS, and one-off items are *not* removed. When
a quarter looks extreme, open the filing.

**When results arrive.** US: a press release (8-K, Item 2.02), mostly before
the open or after the close. The 10-Q follows, often the same day, sometimes
weeks later (due 40 days after quarter end for large companies, 45 for
smaller ones). India: SEBI's listing rules require quarterly results
**within 45 days** of quarter end and year-end results **within 60 days**.
The board meeting is announced in advance and the results reach the
exchange soon after it ends, often during market hours. The app's Indian
data comes from those **NSE filings** (`marketdata/financials.py`),
consolidated where the company files it.

## 2. Year over year, not quarter over quarter

Retailers peak in the holiday quarter, Indian consumer companies around
festivals, cooling makers in summer. Comparing December with September
measures the season, not the business. So **growth is measured against the
same quarter a year earlier**. The app does exactly that (`growth_series`):
SEC filings carry their own year-ago figure, and NSE quarters are compared
with the stored quarter a year back, put on today's share basis after a
split or bonus. Two traps: **growth from a loss cannot be measured** (−₹2 to
+₹1 is not "+150%"; the app leaves it blank), and **base effects** — a
quarter set against a terrible year-ago one (2020 lockdowns, a one-off
charge) shows a huge percentage that says little. Read the EPS beside it.

## 3. Acceleration: growth that is still speeding up

Growing 30% every quarter is good. Going from 15% to 30% to 60% is what the
market pays most for: **the change in the growth rate is the signal**,
because each step forces analysts to raise forecasts and funds to raise
targets.

**O'Neil's "C".** In CAN SLIM, *current quarterly earnings*: his rule is
latest-quarter EPS **up at least 25%** on the same quarter a year earlier,
higher and accelerating being better, with **sales up too** (about 25%, or
accelerating over three quarters). His **A** asks for strong annual growth
over three years, so one good quarter is not mistaken for a trend.

**Minervini** looks only at stocks already in a Stage 2 uptrend, then wants
**EPS, sales and margins accelerating together**; three quarters of all
three rising is his "Code 33". He treats **deceleration** — growth slowing
two quarters running — as a sign the best of the move may be over. The
app's SEPA section encodes this: F1 EPS growth ≥ 25%, F2 accelerating, F3
sales ≥ 20% or rising, F4 margins up, F8 no two-quarter slowdown, plus the
Code 33 badge. All eight tests and the verdicts are in
[the quality guide](learn-fund-quality.md).

**Sales must confirm.** EPS can rise through buybacks, a lower tax rate, cost
cuts or a one-off gain; revenue is much harder to manage. **Strong EPS on
flat sales has a ceiling; strong EPS on fast-rising sales does not, yet.**

## 4. Real examples on the app's data

Price on top; underneath, growth as **filed** — each step is a new filing,
what a trader could actually have known then.

```series
title: NVIDIA and its EPS growth, 2022–2024
from: 2022-07-01
to: 2024-12-31
line: us:NVDA | NVIDIA | log
line: us:fund.NVDA.eps_g | EPS growth, % y/y (as filed) | pane2 zero
mark: 2023-05-25 | results + guidance: +24%
caption: In May 2023 the filed quarter showed EPS up only 28% and sales down 13%, yet the stock rose 24% in a day on guidance. The next filings showed EPS growth of about 850%, 1,270% and 770%. From about $14.6 at the end of 2022 to $49.5 a year later; peak near $136 in June 2024.
```

**NVIDIA 2023: guidance first, numbers after.** On 25 May 2023 the quarter
was ordinary, but guidance for next-quarter revenue was far above
expectations on AI data-centre demand: $30.54 to $37.98 in a day. The filed
acceleration came later — EPS growth from −52% (February 2023) to +1,274%
(November 2023), revenue growth +265% by February 2024 — and waiting for it
still caught most of the move: the stock **tripled** in 2023.

```series
title: Netflix and its sales growth, 2020–2022
from: 2020-01-01
to: 2022-12-31
line: us:NFLX | Netflix | log
line: us:fund.NFLX.rev_g | Sales growth, % y/y (as filed) | pane2 zero
mark: 2021-11-17 | peak
mark: 2022-01-21 | results −22%
mark: 2022-04-20 | results −35%
caption: Sales growth slowed from about 31% to 16% while the stock made new highs. It peaked on 17 November 2021, fell 22% and 35% on the next two results days, and 76% in all by May 2022.
```

**Netflix 2021: sales growth slowed before the top.** Growth fell almost
every quarter, **31% to 16%**, over two years while the price kept rising on
the pandemic boom. After the November 2021 top, January's results (weak
subscriber guidance) gapped it down **22%**, and April's report of lost
subscribers took **35% in a day**. **Slowing growth does not date the top;
it tells you the stock now runs on expectations rather than numbers.**

```series
title: Etsy and its sales growth, 2020–2022
from: 2020-01-01
to: 2022-12-31
line: us:ETSY | Etsy | log
line: us:fund.ETSY.rev_g | Sales growth, % y/y (as filed) | pane2 zero
mark: 2021-08-05 | growth collapses
mark: 2021-11-24 | peak
caption: Sales growth fell from about 141% to 23% in one filing (August 2021), a base effect after the lockdown boom. The stock dipped 10%, rallied 63% to a November 2021 peak, then lost 77% by June 2022.
```

**Etsy 2021: the honest counter-example.** Growth collapsed (a **base
effect**), yet the stock made a new high in November (+13% on that results
day) before losing **77%**. Deceleration is a reason to tighten stops and
stop adding, not a sell signal on its own. **Price makes the final call.**

```series
title: Trent and its sales growth, 2023–2026
from: 2023-07-01
to: 2026-06-30
line: india:TRENT.NS | Trent | log
line: india:fund.TRENT.NS.rev_g | Sales growth, % y/y (as filed) | pane2 zero
mark: 2024-10-11 | peak
caption: Sales growth held around 45–56% through 2023–24 while the stock rose about 4.9 times. After the October 2024 peak growth stepped down every quarter, to about 16% by late 2025, and the stock fell 73% by March 2026.
```

**India — Trent.** From about ₹1,666 (July 2023) to ₹8,235 (October 2024)
on ~50% sales growth, then 39%, 34%, 28%, 19%, 16% and a 73% fall. (One
stored April 2023 quarter shows growth in the thousands of percent, a data
artefact the chart starts after: **check the filing behind a big number**.)

## 5. Surprises, expectations and guidance

A stock reacts to **the number against what was expected**, and to what
management says next. The **consensus** is the average analyst forecast;
the **surprise** is actual minus consensus; for popular growth stocks the
unofficial **whisper** is higher still, so beating consensus is the minimum.

**What the app stores, exactly.** **A history of consensus estimates is not
stored.** The app keeps Yahoo's earnings history for about the **last four
quarters** per company (`fetch_surprises`: actual, estimate, surprise %).
`growth.py` takes the newest as "the surprise", shown only when it is within
45 days (`SURPRISE_MATCH_DAYS`) of the latest filed quarter; SEPA's F7 passes
when actual > estimate. Yahoo's "actual" can be an **adjusted** EPS, and
because estimates are not point in time, **backtests never use F7**.

**How informative is a beat?** In the stored readings (US 6,250 across 1,573
companies; India 1,154 across 308), **77% of US quarters beat**, against 55%
in India. Matched to the results-day move (method in §6):

| | US beats | US misses / in line | India beats | India misses / in line |
|---|---|---|---|---|
| Reactions | 3,263 | 871 | 598 | 484 |
| Closed up on the day | 53% | 40% | 62% | 40% |
| Median day move | +0.5% | −1.2% | +1.1% | −1.0% |
| Beats that fell > 5% | 18% | | 6.5% | |

(US March 2025 – October 2026; India October 2025 – October 2026.) **A US
beat is close to a coin flip on the day**, and nearly one beat in five fell
more than 5%. Guidance, revenue, the quality of the beat and how far the
stock had already run decide it.

## 6. The earnings reaction, measured

**Method.** US events: every non-Q4 quarter in `quarterly_results` from SEC
filings, dated by first filing (Q4 is skipped — the 10-K can come weeks after
the release). India: every NSE results filing, by its filing date.
(`stock_events` holds only about a year of announcement dates, so the filing
history gives the long sample.) The **reaction day** is the highest-volume
session from three sessions before the filing to one after (US), or the
filing day and the next (India). Checked against the 518 US reports where
`stock_events` has the 8-K date, **90%** fell on that day or the next
session. Move = close ÷ previous close; gap = open ÷ previous close; 27 US
moves over 60% dropped as likely artefacts. Baseline: the same stocks'
ordinary days (±3 sessions around reports excluded). Sample: **US 58,049
reports, 1,446 companies, July 2009 – October 2026; India 6,770 reports, 382
companies, November 2020 – October 2026.**

| Absolute move on reaction day | US results | US normal | India results | India normal |
|---|---|---|---|---|
| Median | 2.7% | 1.1% | 2.8% | 1.2% |
| 90th percentile | 10.6% | 3.6% | 7.7% | 3.7% |
| 99th percentile | 25.6% | 9.2% | 15.6% | 8.2% |
| Closed > 5% away | 29.7% | 4.9% | 24.6% | 4.4% |
| Closed > 10% away | 11.2% | 0.8% | 4.6% | 0.5% |
| **Gapped > 5% at the open** | **18.1%** | 1.0% | **8.4%** | 0.5% |
| Gapped > 10% | 6.1% | 0.2% | 1.0% | 0.1% |

A results day is about **two and a half normal days**, and a US stock is
about **18 times more likely to gap over 5%** (10.1% up, 8.1% down). Indian
stocks move as much but **gap far less**: results often land intraday.
US reactions have **grown**: the median move was 2.0% in 2009–2014 and
3.7% in 2023–2026; moves over 5% rose from 20% to **40% of reports**, and
gaps over 5% from 9.5% to 29%. Part of this may be the company mix (today's
universe), but for a stop 5–8% below entry, **one report can gap straight
through it** — the [stops guide](learn-risk-stops-exits.md) measures the cost.

### Do big gaps keep going?

Studies since the 1960s found prices **drift** after big surprises in the
same direction ("post-earnings-announcement drift"). The same test here:
return from the reaction-day close over the next 20 and 60 sessions,
**minus the market** (SPY; NIFTY 500 for India).

| Excess return | Reports (60d) | 20-day median | 60-day median | 60-day mean | 60d % beating |
|---|---|---|---|---|---|
| US, all reports | 56,790 | −0.2% | −0.2% | +2.0% | 49% |
| US, gap up ≥ 5% | 5,598 | +0.3% | +0.9% | +3.1% | 52% |
| US, gap up ≥ 10% | 1,873 | +0.6% | +1.8% | +4.3% | 54% |
| US, gap down ≤ −5% | 4,500 | −0.4% | −0.8% | +2.3% | 48% |
| US, gap down ≤ −10% | 1,485 | −0.2% | −0.5% | +4.7% | 49% |
| India, all reports | 6,435 | −0.2% | +0.8% | +3.8% | 52% |
| India, gap up ≥ 5% | 301 | +1.7% | +4.1% | +7.2% | 57% |
| India, gap down ≤ −5% | 234 | −1.1% | +0.7% | +3.5% | 52% |

**The direction is right; the edge is small.** Big US up-gaps beat the
market by a median 1–2 points over 60 sessions, big down-gaps lagged
slightly, and barely more than half of either beat the market. India's
up-gaps drifted more, but on a few hundred events in under six years.
Every mean is positive — even after big down-gaps — because of
**survivorship**: the stored universe is mostly today's companies, so the
ones that collapsed and delisted are missing. Trust the medians.

### Does growth itself predict the reaction?

Each US reaction joined to the growth in its filing (43,881 reports):

| Filed quarter | Reports | Median day move | Median 60-day excess |
|---|---|---|---|
| EPS falling y/y | 17,531 | −0.2% | −0.6% |
| EPS up 0–25% | 11,953 | +0.1% | −0.1% |
| EPS up ≥ 25% | 14,397 | +0.6% | +0.3% |
| … and accelerating | 9,008 | +0.6% | +0.3% |
| … and decelerating | 3,766 | +0.3% | +0.2% |
| … with sales up ≥ 20% | 4,450 | +0.7% | +0.3% |
| … with sales up < 10% | 5,892 | +0.5% | +0.1% |

India (4,776 reports) ranks the same, with larger numbers: EPS ≥ 25% with
sales ≥ 20% had a median reaction of +1.2%, falling EPS −1.2%. **Every rule
in this guide points the right way, and each alone is worth a fraction of a
percent across average stocks.** Growth matters in combination — a leading
stock, in a leading group, in a healthy market, *with* accelerating numbers
— which is the setup O'Neil and Minervini describe, not a growth screen.

## 7. How the app uses earnings

- **Earnings dates as gates.** Several strategies refuse or flag a setup
  with results due within about 10 trading days; the table, and the caveat
  that an unknown date passes, are in [the calendar guide](learn-macro-calendar.md).
  **Backtests apply no earnings rule**, so tested trades hold through results.
- **Fundamentals as a backtest filter.** `backtest.py --fundamentals
  covered|acceptable|leader` keeps signals whose SEPA verdict, from the
  filings public **on the signal date**, meets the level (no F7). Stored US
  `minervini` runs (2010–2026, version 1.6; now 1.7 with the same
  fingerprint): covered **487 trades, +0.04R average**; acceptable **115,
  −0.08R**; leader **24, +0.04R**. India (2022–2026, v1.5): 59, 16 and 7
  trades. **Requiring strong fundamentals has not improved this app's
  backtests so far**, on small filtered samples — see
  [the quality guide](learn-fund-quality.md).
- **On screen.** The Fundamentals view's quarterly table and SEPA section
  (LEADER / ACCEPTABLE / WEAK, Code 33) are what to read before a trade.

## 8. What the trader does

1. **Check the next report date before every entry.** A new position a week
   or two before results is a bet on the gap, not on the setup.
2. **If you hold through results, decide beforehand**: smaller size, or a
   profit cushion that makes a 10–20% gap survivable.
3. **Read the last 4–8 quarters, not one**: speeding up or slowing? Real
   (sales up) or engineered (flat sales, lower tax, buybacks)?
4. **Prefer acceleration with confirming sales**, in a stock and group
   already leading — that is where the small edges in §6 add up.
5. **Treat deceleration as a warning**: tighten the stop, stop adding, let
   price confirm (Netflix, Etsy). A big down-gap in a leader is rarely a
   bargain; the medians did not recover.

## 9. What the evidence says

- **Robust:** results days are the largest scheduled single-stock risk — a
  US report moves a stock ~2.5× a normal day and gapped it over 5% in 18% of
  reports, 29% since 2023. India gaps less; results often arrive intraday.
- **Real but small:** growth, sales confirmation and acceleration all point
  the right way; drift after big US up-gaps is about 1–2 points at the
  median. Published work (e.g. Martineau, below) finds the drift has shrunk.
- **Folklore:** "a beat sends the stock up." 77% of US quarters beat, and
  beats rose barely half the time.
- **Lags and failures:** growth peaks show only in hindsight — Etsy rallied
  63% after its slowdown; Zoom peaked in October 2020 with filed sales growth
  above 350%, and fell 27% in three weeks on vaccine news. Filings get
  restated, US Q4 is derived, Indian data has occasional artefacts.
- **Caveats:** survivorship, detected reaction days (~90% exact), one to two
  years of surprises, small filtered backtests. Education, not advice.

## 10. Checklist

- [ ] Next results date known for every position and planned entry?
- [ ] Nothing new in the 1–2 weeks before a report, or a smaller size?
- [ ] Last 4–8 quarters read: EPS growth, sales growth, margin — accelerating or slowing?
- [ ] EPS growth confirmed by sales growth (≥ ~20%)?
- [ ] Any growth from a loss or a distorted base — filing checked?
- [ ] SEPA section: verdict, and any F8 slowdown flag?
- [ ] After each report: did it gap? Act on the gap, don't argue with it.
- [ ] Holdings whose growth slowed two quarters running: stops tightened?

## Further reading

- William J. O'Neil, *How to Make Money in Stocks* (CAN SLIM; the "C" and "A").
- Mark Minervini, *Trade Like a Stock Market Wizard* (SEPA, earnings acceleration, Code 33).
- Ray Ball and Philip Brown, "An Empirical Evaluation of Accounting Income Numbers", *Journal of Accounting Research* (1968).
- Victor Bernard and Jacob Thomas, "Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?", *Journal of Accounting Research* (1989).
- Charles Martineau, "Rest in Peace Post-Earnings Announcement Drift", *Critical Finance Review* (2022).
- SEC EDGAR (sec.gov/edgar) for 8-K, 10-Q and 10-K filings; SEBI (LODR) Regulations, 2015; NSE corporate filings (nseindia.com).
