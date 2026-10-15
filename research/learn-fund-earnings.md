# Earnings that move stocks — growth, acceleration and the results-day reaction

Learning material. This guide covers:

- what a quarterly report contains;
- why growth is measured year over year;
- why **accelerating** earnings and sales are behind most big winners;
- what a "beat" really means;
- how big the move on results day usually is.

Every reaction figure here was measured on the app's own stored prices and
filing dates. The method is stated each time.

**Where this shows in the app.** Each stock has a **Fundamentals** view, next to
Chart and News. It shows the last 12 quarters. It also has a **Minervini SEPA**
section, which applies eight growth tests to the company's filings. (In the
code, `scripts/fundamentals/growth.py` computes the shared numbers and
`fundamentals/sepa.py` runs the tests.) The Chart marks past results with an
"E". **News & events** lists the next report date. **Markets → Post-market**
has an *Earnings in the next 10 days* card. Earnings season, and the rules that
keep strategies out of trades just before results (earnings gates), are in the
[calendar guide](learn-macro-calendar.md); valuation in
[learn-fund-valuation.md](learn-fund-valuation.md). Margins, returns on capital
and the full growth checklist are in [learn-fund-quality.md](learn-fund-quality.md).

---

## 1. What a quarterly report contains

| Line | What it is | Why it matters |
|---|---|---|
| **Revenue (sales)** | What customers paid | Hard to fake; growth has to start here |
| **Net income** | What is left after all costs, interest and tax | The bottom line |
| **EPS** | Net income per share (diluted) | What O'Neil and Minervini measure |
| **Margins** | Net income ÷ revenue (also gross, operating) | Rising margins = each sale earns more |
| **Guidance** | Management's forecast for next quarter or year | Often moves the stock more than the quarter |

**GAAP against adjusted.** Filed numbers follow the official accounting rules:
**GAAP** in the US, **Ind AS** in India. Most US companies also publish an
**adjusted** EPS. It leaves out stock-based pay, the write-down of acquired
assets (acquisition amortisation) and restructuring charges. Analysts forecast
the adjusted figure. So headlines like "beat by 5 cents" compare adjusted with
adjusted. Adjusting removes genuine one-off noise. But it can also leave out
costs that come back every year.

The app's growth figures come from the **filings** themselves: SEC XBRL data
for the US, NSE XBRL data for India (XBRL is the machine-readable format of a
filing). So they are GAAP / Ind AS figures, and one-off items are *not*
removed. When a quarter looks extreme, open the filing.

**When results arrive.** In the US, a company first issues a press release
(form 8-K, Item 2.02), mostly before the open or after the close. The full
quarterly report (10-Q) follows. It often comes the same day, sometimes weeks
later. It is due 40 days after quarter end for large companies, 45 for smaller
ones.

In India, SEBI's listing rules require quarterly results **within 45 days** of
quarter end, and year-end results **within 60 days**. The company announces
the board meeting in advance. The results reach the exchange soon after the
meeting ends, often during market hours. The app's Indian data comes from those
**NSE filings** (downloaded by `marketdata/financials.py`). It uses the
consolidated figures (the whole group) where the company files them.

## 2. Year over year, not quarter over quarter

Retailers peak in the holiday quarter, Indian consumer companies around
festivals, cooling makers in summer. Comparing December with September
measures the season, not the business. So **growth is measured against the
same quarter a year earlier**.

The app does exactly that. US filings carry their own year-ago figure. For
India, the app compares each quarter with the stored quarter a year back. If
there was a split or bonus issue in between, it first adjusts the old figure
to today's number of shares.

Two traps:

- **Growth from a loss cannot be measured.** Going from −₹2 to +₹1 is not
  "+150%". The app leaves it blank.
- **Base effects.** If the year-ago quarter was terrible (2020 lockdowns, a
  one-off charge), this quarter shows a huge percentage that says little.
  Read the EPS figure itself beside it.

## 3. Acceleration: growth that is still speeding up

Growing 30% every quarter is good. Going from 15% to 30% to 60% is what the
market pays most for. **The change in the growth rate is the signal.** Each
step up forces analysts to raise their forecasts and funds to raise their
price targets.

**O'Neil's "C".** O'Neil's method is called CAN SLIM, and its "C" stands for
*current quarterly earnings*. His rule: latest-quarter EPS **up at least 25%**
on the same quarter a year earlier. Higher is better, and accelerating is
better still. **Sales must be up too**: about 25%, or accelerating over three
quarters. His **A** asks for strong annual growth over three years. That way
one good quarter is not mistaken for a trend.

**Minervini** looks only at stocks already in a Stage 2 uptrend (the rising
phase of a stock's cycle). Then he wants **EPS, sales and margins accelerating
together**. Three quarters in a row of all three rising is what he calls "Code
33". He treats **deceleration** — growth slowing two quarters running — as a
sign the best of the move may be over.

The app's SEPA section encodes this: F1 EPS growth ≥ 25%, F2 accelerating, F3
sales ≥ 20% or rising, F4 margins up, F8 no two-quarter slowdown, plus the
Code 33 badge. All eight tests and the verdicts are in
[the quality guide](learn-fund-quality.md).

**Sales must confirm.** EPS can rise through share buybacks, a lower tax rate,
cost cuts or a one-off gain. Revenue is much harder to manage. **Strong EPS on
flat sales has a ceiling. Strong EPS on fast-rising sales does not — yet.**

## 4. Real examples on the app's data

Each chart shows the price on top. Underneath is growth as **filed**. Each step
in that line is a new filing — what a trader could actually have known then.

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
itself was ordinary. But the company's forecast for next-quarter revenue was
far above expectations, because of demand for AI data-centre chips. The stock
went from $30.54 to $37.98 in a day. The acceleration showed up in the filings
later. EPS growth went from −52% (February 2023) to +1,274% (November 2023).
Revenue growth reached +265% by February 2024. A trader who waited for those
filed numbers still caught most of the move: the stock **tripled** in 2023.

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

**Netflix 2021: sales growth slowed before the top.** Over two years, growth
fell almost every quarter, from **31% to 16%**. Meanwhile the price kept rising
on the pandemic boom. The top came in November 2021. January's results came
with a weak forecast for new subscribers, and the stock gapped down **22%**.
In April the company reported it had lost subscribers, and the stock fell
**35% in a day**. **Slowing growth does not tell you when the top will come.
It tells you the stock is now rising on expectations rather than on numbers.**

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
effect**). Yet the stock made a new high in November (+13% on that results
day), and only then lost **77%**. Deceleration is a reason to tighten stops
and stop adding. It is not a sell signal on its own. **The price action makes
the final call.**

```series
title: Trent and its sales growth, 2023–2026
from: 2023-07-01
to: 2026-06-30
line: india:TRENT.NS | Trent | log
line: india:fund.TRENT.NS.rev_g | Sales growth, % y/y (as filed) | pane2 zero
mark: 2024-10-11 | peak
caption: Sales growth held around 45–56% through 2023–24 while the stock rose about 4.9 times. After the October 2024 peak growth stepped down every quarter, to about 16% by late 2025, and the stock fell 73% by March 2026.
```

**India — Trent.** The stock went from about ₹1,666 (July 2023) to ₹8,235
(October 2024) on ~50% sales growth. Then growth slowed: 39%, 34%, 28%, 19%,
16%. The stock fell 73%. (One stored April 2023 quarter shows growth in the
thousands of percent. That is a data error, and the chart starts after it.
**Check the filing behind any big number.**)

## 5. Surprises, expectations and guidance

A stock reacts to **the number compared with what was expected**. It also
reacts to what management says about the future. The **consensus** is the
average analyst forecast. The **surprise** is the actual figure minus the
consensus. For popular growth stocks, traders also talk of an unofficial
**whisper** number — what they really expect — and it is higher still. So
beating consensus is the minimum.

**What the app stores, exactly.** **The app does not store a history of
consensus estimates.** It keeps Yahoo's earnings history for about the **last
four quarters** per company: actual EPS, estimate, and surprise %. The newest
of these is shown as "the surprise", but only when it is within 45 days of the
latest filed quarter. SEPA's test F7 passes when actual > estimate. Two
caveats. Yahoo's "actual" can be an **adjusted** EPS. And the stored estimates
are today's record, not what was known at the time. So **backtests never use
F7**.

**How informative is a beat?** The app has 6,250 stored readings for the US
(1,573 companies) and 1,154 for India (308 companies). **77% of US quarters
beat**, against 55% in India. Here they are matched to the move on results day
(method in §6):

| | US beats | US misses / in line | India beats | India misses / in line |
|---|---|---|---|---|
| Reactions | 3,263 | 871 | 598 | 484 |
| Closed up on the day | 53% | 40% | 62% | 40% |
| Median day move | +0.5% | −1.2% | +1.1% | −1.0% |
| Beats that fell > 5% | 18% | | 6.5% | |

(US March 2025 – October 2026; India October 2025 – October 2026.) **Whether a
US beat closes up on the day is close to a coin flip.** Nearly one beat in five
fell more than 5%. What decides the move is the forecast, revenue, the quality
of the beat, and how far the stock had already run.

## 6. The earnings reaction, measured

**Method.**

- **US events:** every quarter except Q4 in the app's stored quarterly
  results (`quarterly_results`, from SEC filings), dated by the first filing.
  Q4 is skipped because the annual report (10-K) can come weeks after the
  press release.
- **India events:** every NSE results filing, by its filing date.
- The app's table of announcement dates (`stock_events`) covers only about a
  year. The filing history gives a much longer sample.
- **Reaction day.** For the US, the highest-volume session from three sessions
  before the filing to one after. For India, the higher-volume of the filing
  day and the next. Check: in the 518 US reports where the 8-K press-release
  date is stored, **90%** of detected reaction days fell on that date or the
  next session.
- **Move** = close ÷ previous close. **Gap** = open ÷ previous close. 27 US
  moves over 60% were dropped as likely data errors.
- **Baseline:** the same stocks' ordinary days, leaving out ±3 sessions around
  each report.
- **Sample:** **US 58,049 reports, 1,446 companies, July 2009 – October 2026;
  India 6,770 reports, 382 companies, November 2020 – October 2026.**

| Absolute move on reaction day | US results | US normal | India results | India normal |
|---|---|---|---|---|
| Median | 2.7% | 1.1% | 2.8% | 1.2% |
| 90th percentile | 10.6% | 3.6% | 7.7% | 3.7% |
| 99th percentile | 25.6% | 9.2% | 15.6% | 8.2% |
| Closed > 5% away | 29.7% | 4.9% | 24.6% | 4.4% |
| Closed > 10% away | 11.2% | 0.8% | 4.6% | 0.5% |
| **Gapped > 5% at the open** | **18.1%** | 1.0% | **8.4%** | 0.5% |
| Gapped > 10% | 6.1% | 0.2% | 1.0% | 0.1% |

A results day moves a stock about as much as **two and a half normal days**. A
US stock is about **18 times more likely to gap over 5%** (10.1% up, 8.1%
down). Indian stocks move as much but **gap far less**, because results often
arrive during market hours.

US reactions have **grown**. The median move was 2.0% in 2009–2014 and 3.7% in
2023–2026. Moves over 5% rose from 20% to **40% of reports**. Gaps over 5% rose
from 9.5% to 29%. Part of this may be the company mix, since the stored
universe is today's companies. But if your stop is 5–8% below entry, **one
report can gap straight through it**. The [stops guide](learn-risk-stops-exits.md)
measures what that costs.

### Do big gaps keep going?

Studies since the 1960s found that after a big surprise, prices keep moving
slowly in the same direction for weeks. This is called "post-earnings-announcement
drift". The same test here: the return from the reaction-day close over the
next 20 and 60 sessions, **minus the market's return** over the same days (SPY
for the US; NIFTY 500 for India).

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

**The direction is right; the edge is small.** After big US up-gaps, the
median stock beat the market by 1–2 points over 60 sessions. After big
down-gaps, it lagged slightly. In both cases barely more than half beat the
market. India's up-gaps drifted more, but that rests on a few hundred events
in under six years.

Every mean is positive, even after big down-gaps. That is **survivorship**
bias. The stored universe is mostly today's companies, so the ones that
collapsed and were delisted are missing. Trust the medians.

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

India (4,776 reports) ranks the same way, with larger numbers. EPS ≥ 25% with
sales ≥ 20% had a median reaction of +1.2%. Falling EPS had −1.2%. **Every rule
in this guide points the right way. But each one alone is worth only a
fraction of a percent across average stocks.** Growth matters in combination:
a leading stock, in a leading group, in a healthy market, *with* accelerating
numbers. That combination is the setup O'Neil and Minervini describe. A growth
screen on its own is not.

## 7. How the app uses earnings

- **Earnings dates as gates.** Several strategies refuse or flag a setup when
  results are due within about 10 trading days. The table is in
  [the calendar guide](learn-macro-calendar.md), with one caveat: if the date
  is unknown, the setup passes. **Backtests apply no earnings rule**, so tested
  trades hold through results.
- **Fundamentals as a backtest filter.** The backtester can keep only signals
  whose SEPA verdict meets a chosen level (`backtest.py --fundamentals
  covered|acceptable|leader`). The verdict uses only the filings that were
  public **on the signal date**, and leaves out F7. Results from stored US
  `minervini` strategy runs (2010–2026, version 1.6; now 1.7, with the same
  rule fingerprint): covered **487 trades, +0.04R average**; acceptable **115,
  −0.08R**; leader **24, +0.04R**. India (2022–2026, v1.5): 59, 16 and 7
  trades. **Requiring strong fundamentals has not improved this app's
  backtests so far.** The filtered samples are small — see
  [the quality guide](learn-fund-quality.md).
- **On screen.** The Fundamentals view's quarterly table and SEPA section
  (LEADER / ACCEPTABLE / WEAK, Code 33) are what to read before a trade.

## 8. What the trader does

1. **Check the next report date before every entry.** A new position a week
   or two before results is a bet on the gap, not on the setup.
2. **If you hold through results, decide beforehand.** Either use a smaller
   size, or hold only with enough profit that a 10–20% gap would not hurt
   badly.
3. **Read the last 4–8 quarters, not one.** Is growth speeding up or slowing?
   Is it real (sales up) or engineered (flat sales, lower tax, buybacks)?
4. **Prefer acceleration with confirming sales**, in a stock and group that
   are already leading. That is where the small edges in §6 add up.
5. **Treat deceleration as a warning.** Tighten the stop, stop adding, and let
   the price confirm (Netflix, Etsy). A big down-gap in a leader is rarely a
   bargain: the medians did not recover.

## 9. What the evidence says

- **Robust:** results days are the largest scheduled risk for a single stock.
  A US report moves a stock ~2.5× a normal day. It gapped the stock over 5% in
  18% of reports, and in 29% since 2023. India gaps less, because results
  often arrive during market hours.
- **Real but small:** growth, sales confirmation and acceleration all point
  the right way. Drift after big US up-gaps is about 1–2 points at the median.
  Published work (e.g. Martineau, below) finds the drift has shrunk.
- **Folklore:** "a beat sends the stock up." 77% of US quarters beat, and
  beats rose barely half the time.
- **Lags and failures:** growth peaks show only in hindsight. Etsy rallied
  63% after its slowdown. Zoom peaked in October 2020 with filed sales growth
  above 350%, and fell 27% in three weeks on vaccine news. Filings get
  restated. US Q4 figures are derived (the full year minus the first nine
  months). Indian data has occasional errors.
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
