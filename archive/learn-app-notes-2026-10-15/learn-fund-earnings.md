# App notes moved out of learn-fund-earnings

## Intro (opening paragraph)

Every reaction figure here was measured on the app's own stored prices and
filing dates. The method is stated each time.

## Intro — "Where this shows in the app"

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

## §1 What a quarterly report contains — data sources

The app's growth figures come from the **filings** themselves: SEC XBRL data
for the US, NSE XBRL data for India (XBRL is the machine-readable format of a
filing). So they are GAAP / Ind AS figures, and one-off items are *not*
removed. When a quarter looks extreme, open the filing.

(India) The app's Indian data comes from those
**NSE filings** (downloaded by `marketdata/financials.py`). It uses the
consolidated figures (the whole group) where the company files them.

## §2 Year over year

The app does exactly that. US filings carry their own year-ago figure. For
India, the app compares each quarter with the stored quarter a year back. If
there was a split or bonus issue in between, it first adjusts the old figure
to today's number of shares.

- **Growth from a loss cannot be measured.** ... The app leaves it blank.

## §3 Acceleration — SEPA section

The app's SEPA section encodes this: F1 EPS growth ≥ 25%, F2 accelerating, F3
sales ≥ 20% or rising, F4 margins up, F8 no two-quarter slowdown, plus the
Code 33 badge. All eight tests and the verdicts are in
[the quality guide](learn-fund-quality.md).

## §4 heading

"Real examples on the app's data" — each chart shows growth as filed (step per filing).

## §5 What the app stores, exactly

**What the app stores, exactly.** **The app does not store a history of
consensus estimates.** It keeps Yahoo's earnings history for about the **last
four quarters** per company: actual EPS, estimate, and surprise %. The newest
of these is shown as "the surprise", but only when it is within 45 days of the
latest filed quarter. SEPA's test F7 passes when actual > estimate. Two
caveats. Yahoo's "actual" can be an **adjusted** EPS. And the stored estimates
are today's record, not what was known at the time. So **backtests never use
F7**.

**How informative is a beat?** The app has 6,250 stored readings for the US
(1,573 companies) and 1,154 for India (308 companies).

## §6 Method — table names

- **US events:** every quarter except Q4 in the app's stored quarterly
  results (`quarterly_results`, from SEC filings), dated by the first filing.
- The app's table of announcement dates (`stock_events`) covers only about a
  year. The filing history gives a much longer sample.

## §7 How the app uses earnings (whole section, removed; backtest results NOT to be cited in Learn)

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

## §9 Evidence — caveat

- **Caveats:** ... small filtered backtests.

## §10 Checklist item

- [ ] SEPA section: verdict, and any F8 slowdown flag?
