# Using the app — reading its backtests and screen studies: what each number means, and when to doubt it

Learning material. This guide reads one real stored backtest, number by
number, as the app shows it, then one screen study. It then shows, on the
app's own runs, what should make you distrust a result and how to compare two
runs fairly. [Backtesting honestly](learn-test-backtesting.md) covers the ways
a backtest misleads; this guide is about reading what is on the screen. For R,
expectancy and sample size, see [expectancy](learn-risk-expectancy.md); for
basic terms, [Start here](learn-start-here.md).

**Where this shows in the app.** Backtests appear in two places:

- **System → Reports archive.** Every backtest and screening report the
  offline scripts wrote. Pick *Backtests* on the left, then a market and a
  strategy. Click a row to open the run's own page.
- **Strategies → (a strategy) → Backtests.** The same runs for one strategy,
  grouped by the version of its rules.

Screen studies are on **Screens → (a screen) → Study**, and in the screen
builder as *Study (5 years of month-ends)*. A study is computed when you open
the tab (`screens/study.py`); backtests are run offline and loaded into the
app (`report_runs`, `report_tables`). The numbers below were read from the
stored runs on 15 October 2026, or recomputed with the study's own method.
My analysis scripts are not part of the app.

---

## 1. The run we will read

The example is the **US Donchian channel** backtest at the strategy's current
version, v1.1. Donchian buys a close above the highest high of the last 55
days. This run sells when price closes below its 50-day low, with no profit
target. It covers January 2013 to October 2026, 13.77 years. It is the app's
clearest positive expectancy, and its profit comes from very few trades:
exactly what a reader must learn to spot.

## 2. The Reports archive row

The archive is a table, one row per run. For backtests the columns are:

| Column | What it holds |
|---|---|
| Market, strategy | US / India and the strategy's key |
| From | The first date simulated |
| Exit | The exit policy in words, e.g. "Donchian exit (50 days, no target)" |
| Options | Anything else switched on, e.g. "market filter", "ranked by RS", "liquidity ≥ 100M/day" |
| Version | The rule version that produced the run, e.g. v1.1 |
| cagr %, excess cagr %, max dd %, sharpe | Four headline numbers, copied from the report |
| Generated | When the run was written |

The exit and options are decoded from the run's folder name. The backtester
names each run `<start>_<exit policy>_<options>_v<version>-<fingerprint>`.
Our run is `2013-01-01_donchian-50d-noTarget_v1.1-69e24dab`.

Above the table, the page names the run with the **best excess CAGR**. Treat
it with care: it is the maximum over every row shown, whatever their periods.
With all runs shown, it points at an India Donchian run covering only January
2024 to October 2026 (−0.63%). It tops the 13-year runs mainly because the
Nifty 500 rose only 4.4% a year in that window. The best of many is a source
of false confidence (§5.5).

## 3. The run's page

A run's page has five tiles (**CAGR, Excess CAGR, Max drawdown, Sharpe,
Total return**) and tabs: **Report** (the written report), **Funnel**,
**Equity curve**, **Trades (506)** and **Data** (the stored tables).

### 3.1 The verdict line

The report opens with one sentence. For this run:

> **Did not beat buy-and-hold** (−6.30% excess CAGR). Drawdown was also
> worse (−49.3% vs −34.1%).

A fixed rule writes it. "Beat the benchmark on both return and
risk-adjusted return" needs a higher CAGR *and* Sharpe than the index; "on
return but not risk-adjusted" needs only the higher CAGR; anything else is
"Did not beat buy-and-hold". Read it first: was this better than doing nothing?

### 3.2 The Headline table

| Line | Strategy | Benchmark | What it means |
|---|---|---|---|
| Equity | $50,000 → $119,514 | — | Starting account and where it ended, open positions valued at the last close |
| Total return | 139.03% | 426.93% | End ÷ start − 1 |
| CAGR | 6.53% | 12.83% | The steady yearly rate that turns start into end over 13.77 years |
| Max drawdown | −49.30% | −34.10% | The worst fall from a previous high in the account value |
| Sharpe | 0.43 | 0.80 | Average daily return ÷ its standard deviation, scaled to a year, with a 0% risk-free rate |
| Sortino | 0.39 | — | The same, but counting only down days as risk |
| Calmar | 0.13 | 0.376 | CAGR ÷ the size of the max drawdown |
| Exposure | 100.0% of days | 100% | Share of days holding **at least one** position |
| Excess CAGR | −6.30% | — | Strategy CAGR minus benchmark CAGR |

Things the table does not say out loud:

- **The benchmark is the index's price, without dividends** (SPY in the US,
  the Nifty 500 in India). Stored prices are not dividend-adjusted and the
  strategy collects none either. Dividends are roughly 1.3–1.9% a year on
  these indices, so buy-and-hold is a little better than shown.
- **Excess CAGR is a difference of two CAGRs.** It says nothing about risk.
- **Exposure is not "share of money invested".** It is the share of days with
  at least one position open. A strategy holding one small position most days
  would also read close to 100%. (Donchian did hold 9.7 of its 10 slots on
  average.)
- **Sharpe and Sortino come from the daily equity curve**, so a short run or a
  few huge days make them unstable.

One line below adds the longest stretch below a previous peak (**1,393
days**), annualised volatility (18.67%), turnover (3.07× average equity a
year) and costs paid ($3,233). The 1,393 are trading sessions. The account
peaked at about $97,900 on 14 February 2020, fell to about $49,600 by 27
October 2023, and regained the peak only on 3 September 2025: five and a half
years without a new high. Would you have kept following the rules?

### 3.3 The Trades section

| Line | Value | Computed on |
|---|---|---|
| Trades | 506 | Every trade, including the 10 still open at the end |
| Win rate | 28.6% | Closed trades only: share with a profit after costs |
| Avg R per trade | 0.486 | Closed trades only: the average R-multiple. This is the expectancy |
| Profit factor | 1.37 | Closed trades only: dollars won ÷ dollars lost |
| Avg positions held | 9.7 (peak 10, cap 10) | From the daily equity table |

- **Expectancy is in R; profit factor is in dollars.** They can disagree,
  because trades are not all the same size (§5.3).
- **The Trades tab's tiles differ slightly.** Its *Win rate* (29.2%) and *Avg
  R* (+0.49) count all 506 rows, the 10 open trades valued at the last close.
  The report uses the 496 closed trades. Know which one you are quoting.
- **R includes modelled costs.** Slippage (5 basis points a side in the US,
  10 in India for these runs) is built into the fill prices.

The *By exit reason* table is the shape of the strategy in three rows:

| Exit | Trades | Total P&L | Avg R | Median days |
|---|---|---|---|---|
| STOP | 288 | −$137,824 | −1.07 | 14 |
| TREND_EXIT | 208 | +$196,658 | +2.64 | 149 |
| OPEN | 10 | +$10,681 | +0.84 | 50 |

Losers are cut in two weeks; winners are held for five months. The average
stop-out is a little worse than −1R, because some stocks opened below the stop.

Then come the **Best 10** and **Worst 10** trades. Always read the best ten.
Here the top two (SFM, +42.1R, and BAR, +56.8R) made $33,482: more than half of
the $58,834 the closed trades made. Section 5 measures this properly.

```series
title: Sprouts Farmers Market (SFM) — the run's biggest dollar winner
from: 2023-06-01
to: 2025-10-31
line: us:SFM | SFM | log
mark: 2023-10-03 | Donchian entry about $42
mark: 2025-07-31 | Trend exit about $151
caption: One trade, held 667 days, made $21,128 — over a third of what all 496 closed trades made. The stock peaked near $180 in June 2025; the 50-day-low exit gave back part of the move, then the stock fell to about $79.
```

### 3.4 The Funnel

The Funnel shows where candidates stopped on the way to becoming trades: a
table in the report, and on the **Funnel** tab a list you can open stage by
stage to see the stocks.

| Stage | Reached | Main reasons for the drop |
|---|---|---|
| Symbols in the universe | 5,387 | 1,456 never passed the pre-filter |
| Pass the pre-filter (point in time) | 3,931 | |
| Bars evaluated | 5,251,571 | hard gate N1 (2,122,028) |
| Bars passing every hard gate | 3,072,164 | no setup formed |
| Bars with a complete setup | 843,244 | entry trigger did not fire |
| Setups whose entry trigger fired | 196,196 | |
| Plans the decision rules accept | 104,760 | 88,596 rated "TRADE ON TRIGGER", not accepted |
| Signals taken as trades | 506 | slots full, order already resting, order expired |

- **The unit changes.** The first two rows count stocks; the rest count bars
  (one stock on one day). A drop means something only between rows that count
  the same thing.
- **The last drop matters most here.** 104,760 acceptable signals became 506
  trades. *Which* 506 was decided by the order in which signals compete for a
  free slot, not by the entry rules.
- **The last stage's reasons add up to more than the drop.** "All position
  slots full" reads 374,334, because a triggered order with no free slot keeps
  resting and is counted again each day, for up to 10 business days. Those
  figures count rejections, not signals.

Triggered orders are ranked by the setup's quality score, and almost every
Donchian signal gets the same score. Ties then fall to scan order: roughly
alphabetical. The research note on this strategy found that in India a
seeded random order changed CAGR by about 1.3 points, and ranking by 12-month
momentum added about 7.8 points over random (`research/momentum-trend-research.md`,
measured before a 2026-10-09 cost fix that moved results by under a point).
**A result that depends on a tie-break is partly an accident of it.**

### 3.5 Caveats, Reproduce and the equity curve

**Caveats** is the backtester's own list of what the number leaves out: here
survivorship bias, the cost assumption, a bar touching both stop and target
counted as a stop, and the skipped signals. **Reproduce** gives the command,
but it does not pin the code: run today, it runs today's rules (hence the
version stamp, §4).

The **Equity curve** tab charts the account with a drawdown pane, over the
daily table (date, equity, cash, positions open, drawdown %). This run made
+44.9% in 2013, +52.5% in 2024 and +52.1% in 2025, and lost 35.5% in 2022.
Most other years did little. A CAGR of 6.5% was never a steady 6.5%.

## 4. Spec id and version

Each run is stamped with a **spec id**, here `v1.1-69e24dab`. **v1.1** is
the version number in the strategy's code, which must be raised (with a
changelog entry) whenever the rules change. **69e24dab** is a fingerprint, a
short code computed from the strategy's numeric settings. A test fails if the
fingerprint moves while the version stays the same
(`strategies/versions.lock.json`).

The strategy's **Backtests** tab groups runs by it:

- **Version** chips, each with its run count; the current rules carry a dot.
  A chip can show zero: Minervini's current v1.7 has no stored backtest yet.
- Selecting an old version lists every later change under "**N change(s)
  since, so these runs do not reflect the current rules**". Donchian's v1.0
  chip lists the v1.1 change to the pre-filter's price floor.
- When two rule sets share a version number, the chip shows the full spec id
  and the page warns "same version number, different fingerprint". India
  Minervini has two such pairs (v1.1 and v1.3).
- The table: Market, Run, Version (▲ when superseded), CAGR, Excess CAGR,
  Max DD, Sharpe, Generated. A run that found nothing reads "no trades — open
  for the funnel".

Two cautions. First, the fingerprint sees only numeric settings. Donchian
v1.0 and v1.1 share the fingerprint `69e24dab`, because the v1.1 change was in
the code, not in a number. Only the version bump records it. Second, **the
Backtests tab has no trade count and no expectancy.** Open the run for those.
A CAGR without a trade count cannot be judged.

## 5. What should make you distrust a result

### 5.1 It depends on a handful of trades

Remove each run's five best trades and recompute. Every run below is the
strategy's latest full-history run at its current version (for Minervini,
v1.6 with the market filter). Closed trades only; R is net of modelled costs.

| Run | Closed trades | Expectancy | Without best 5 | Without best 10 | P&L | P&L without the 5 biggest |
|---|---|---|---|---|---|---|
| Donchian, US | 496 | +0.49R | +0.08R | −0.04R | +$58,834 | +$786 |
| Donchian, India | 437 | +0.42R | +0.12R | −0.04R | +₹25.4 lakh | −₹12.0 lakh |
| Chart patterns, India (v1.5) | 515 | +0.14R | +0.08R | +0.04R | +₹12.0 lakh | +₹4.3 lakh |
| Trend pullback, India | 347 | +0.12R | +0.04R | −0.03R | +₹7.2 lakh | −₹0.2 lakh |
| Minervini, US (v1.6, market filter) | 482 | +0.06R | −0.01R | −0.07R | +$11,198 | −$6,599 |
| Volume breakout, US | 703 | +0.04R | +0.02R | −0.01R | +$16,907 | +$7,935 |
| Trend pullback, US | 863 | −0.01R | −0.06R | −0.09R | +$9,443 | −$13,505 |

("Best 5" is by R; "the 5 biggest" is by dollars. They are not always the same
trades.)

**In five of the seven runs, the closed trades' profit is gone, or nearly
gone, without five trades out of several hundred.** That is normal for trend
following, where rare big winners pay for everything
([expectancy](learn-risk-expectancy.md) §3). But the real question becomes
"would the rules catch the next few huge winners?", and five examples cannot
answer it. You can check any run: on the **Trades** tab, sort by R and add up
the top five.

### 5.2 It came from one period

Split each run at the middle of its period (late 2019; May 2018 for
Minervini, which starts in 2010). The first half stands in for the data the
rules were designed on, the second for new data: a rough out-of-sample test.

| Run | First half: trades · expectancy · CAGR | Second half: trades · expectancy · CAGR |
|---|---|---|
| Donchian, US | 235 · +0.71R · 9.0% | 261 · +0.29R · 4.2% |
| Donchian, India | 224 · +0.34R · 5.7% | 213 · +0.50R · 9.8% |
| Chart patterns, India | 159 · +0.03R · 0.7% | 356 · +0.19R · 6.6% |
| Trend pullback, India | 92 · −0.05R · 0.7% | 255 · +0.17R · 4.0% |
| Minervini, US | 215 · +0.10R · 2.1% | 267 · +0.03R · 0.6% |
| Volume breakout, US | 342 · −0.01R · 0.7% | 361 · +0.09R · 3.7% |
| Trend pullback, US | 430 · +0.18R · 5.8% | 433 · −0.20R · −2.1% |

(Halves split by entry date for trades, and by date for CAGR. Each half's
expectancy has a standard error of about 0.1–0.2R for most runs and about
0.3R for Donchian.)

- **US trend pullback changed sign**: +0.18R, then −0.20R. With standard
  errors near 0.1R, a 0.38R gap is unlikely to be chance. The rules worked in
  one market climate and not the next.
- **All three India runs did better in the second half.** That is not proof
  either; it may just have been a kinder market.
- **The US Donchian gap looks large but is noise**: 0.42R, about one standard
  error of the difference (0.43R).

The year-by-year view says the same. In the US Donchian run, trades entered in
2016 made +99R and trades entered in 2023 made +104R. Together that is 203R of
the run's 241R total. Trades entered in 2022 lost 37R.

### 5.3 R and dollars disagree

In the US Donchian run, 113 of the 496 closed trades put less than a quarter
of the intended 1% of the account at risk. They made +90R between them, but
little money: NVDA returned +53.3R on a $3 position. When a slot is free but
the cash is in other positions, the simulator buys what the cash allows rather
than skip the signal, and each trade counts once in the R average whatever its
size. Without these trades the expectancy is +0.39R, not +0.49R. **Expectancy
says how good the signals were; the equity curve says what an account made.**

### 5.4 Few trades

The standard error of expectancy is the standard deviation of R divided by
√(number of trades); the true figure lies roughly within two of them. At the
spread of R in these strategies, 100 trades give a standard error of
0.15–0.5R: as large as most expectancies above. The Minervini "leader"
fundamentals variant has 24 trades: +0.04R ± 0.34R
([quality guide](learn-fund-quality.md) §12 has the full test).

### 5.5 A big gap between close variants

Of the 46 stored backtests, 37 are Minervini (22 US, 15 India). Nine US runs
share the v1.6 rules from 2010 and differ by one or two options:

| Variant (US Minervini v1.6, 2010–2026) | Closed trades | Expectancy (± SE) | CAGR | Max DD |
|---|---|---|---|---|
| Market filter on | 482 | +0.06R ± 0.07 | 1.34% | −28.6% |
| Default | 551 | +0.04R ± 0.07 | 0.65% | −43.5% |
| Market filter, 5-day re-entry delay, scaled sizing | 493 | +0.04R ± 0.07 | 0.53% | −27.6% |
| Market filter, 5-day re-entry delay | 468 | +0.03R ± 0.07 | 0.72% | −31.2% |
| Scaled sizing (two settings) | 583–586 | +0.03R ± 0.06 | 0.58–0.68% | −35% |
| Fundamentals: covered | 479 | +0.03R ± 0.07 | 0.63% | −36.3% |
| Fundamentals: leader | 24 | +0.04R ± 0.34 | 0.02% | −10.9% |
| Fundamentals: acceptable | 114 | −0.10R ± 0.15 | −0.70% | −17.9% |

("Scaled sizing" is the progressive-exposure option: half risk after recent
losses. ± is one standard error.)

The best variant beats the median by about 0.02R; each run's standard error
is about 0.07R. **The ranking of these variants is mostly noise.** The market
filter's shallower drawdown is the more believable gain, and it is the reason
the changelog gives for making the filter the default. The Minervini
sensitivity notes go further: in the US, 20 of 23 settings of the buy-stop
entry were profitable to 2019, and only one both before and after
(`research/minervini-spec-sensitivity-us.md`). Quoting the best of many
variants is how a backtest overstates an edge
([backtesting honestly](learn-test-backtesting.md)).

## 6. Comparing two runs fairly

Before you say "run B is better than run A", check each line:

| Check | Why |
|---|---|
| Same market, same start and end dates | CAGR depends heavily on the years covered (§2, §5.2) |
| Same exit policy and options | Read the Exit and Options columns; one option can change hundreds of trades |
| Same or stated version | A superseded version (▲) ran different rules |
| Same cost model | India runs other than Minervini model slippage only, no STT or stamp duty; Minervini's spec runs add statutory charges |
| Enough trades in both | See §5.4 |
| The difference against its standard error | Standard error of a difference = √(SE₁² + SE₂²) |
| Overlap of trades | Two runs that share most trades are not two independent tests |

A worked example. India chart patterns ran at v1.1 and again at v1.5, same
dates, same exits. The headline numbers look like a clear step backwards:

| | v1.1 | v1.5 (current) |
|---|---|---|
| CAGR | 5.72% | 3.61% |
| Closed trades | 593 | 515 |
| Win rate | 31.0% | 32.0% |
| Expectancy | +0.20R ± 0.08 | +0.14R ± 0.08 |

The expectancy difference, −0.06R, has a standard error of 0.115R: about half
a standard error, no evidence either way. Only 85 trades are common to both
runs. The v1.2–v1.5 changes stopped the rules buying what the pattern
definitions exclude (stale cups, repeat entries), a correctness reason that
needs no better CAGR. The right reading is "the corrected rules are no worse,
within noise", not "v1.5 lost two points of CAGR".

Compare every run with **doing nothing** too. None of the stored strategy
backtests beat its index over its full period. (The momentum baseline runs by
its own command and is not stored here; its Strategies page says it beats the
index in India but not in the US.)

## 7. The screen study page

A screen only picks stocks. It has no entry, stop or exit, so it is not
backtested. The Study tab asks a simpler question: **did the stocks that
passed the screen go on to beat the other tradable stocks?**

### 7.1 How it is computed

On each month-end, the screen's conditions are applied to that day's stored
snapshot of every stock. Then it measures the return from that month-end to
the month-end 1, 3 and 6 months later, close to close. Each qualifying stock
counts equally, and no costs are charged. The same is done for every
tradable stock. The study is recomputed whenever you open the tab.

### 7.2 Reading the table

US **Stage 2 — Trend Template**, 61 month-ends from August 2021 to August
2026, about 336 qualifiers each:

| Held for | Qualifiers | All tradable | Excess | Hit rate | Dates won |
|---|---|---|---|---|---|
| 1M | +0.7% | +0.2% | +0.46% | 51% | 66% |
| 3M | +1.6% | +1.0% | +0.63% | 51% | 59% |
| 6M | +5.0% | +2.5% | +2.53% | 53% | 75% |

- **Qualifiers / All tradable**: the average return over the holding period,
  averaged over the month-ends.
- **Excess**: the difference, the screen's edge before costs.
- **Hit rate**: the share of qualifying stocks that beat the median tradable
  stock. At 51% the typical qualifier did about as well as the typical stock;
  the excess comes from a minority of big winners, as in the backtests.
- **Dates won**: the share of month-ends on which the qualifiers' average won.

The bars to the right compare the built-in screens' 6-month excess. In the
US: Stage 2 +2.53%, Established uptrend +2.01%, Near highs +1.64%, Above the
200-day +1.50%. The page notes "A stricter screen should beat a looser one",
and here it does. The chart below shows each month-end's 3-month excess as a
bar, and the number of qualifiers as a line.

If a screen averages fewer than 10 qualifiers, the page shows a **Small
sample** warning above the table.

### 7.3 The t-statistic the page does not show

A t-statistic measures how far an average stands out from zero, given how
much it varies. It is the average monthly excess divided by its standard
error. About 2 or more is usually taken as meaningful. The page does not show
it, so here it is, recomputed by the study's method:

| Stage 2 | 1M excess (t) | 6M excess (naive t) |
|---|---|---|
| US | +0.46% (t 1.5) | +2.53% (t 3.9) |
| India | +0.93% (t 2.4) | +2.67% (t 3.2) |

**Use the 1-month t only.** The 6-month windows overlap: each month-end shares
five months with the next one. So the 61 dates are not 61 separate tests, and
the naive t is inflated by roughly √6 (about 2.4 times). Corrected, the US
6-month figure is around 1.6.

Then check how much depends on a few months. India's 1-month excess is +0.93%.
One month, February 2022, alone shows a +12.4% excess. Without the three best
months it falls to +0.57% (t 1.8). In the US, the average monthly excess was
+1.10% in 2024 and +0.11% in 2022. Five years is one or two market climates.
For the full Stage 2 study in both markets, see
[stages](learn-price-stages.md) §9; for groups,
[sectors and groups](learn-sectors-groups.md).

### 7.4 Two caveats the page states, and one it does not

The page's info note says: delisted stocks are missing (survivorship); the 3-
and 6-month windows overlap; sector and industry use today's classification.
It adds that a study measures the screen alone, and a strategy is judged by
its backtests.

The unstated one: a study number quoted anywhere else is a copy, and copies
go stale. Until 15 October 2026 the database held an old stored copy of these
studies, computed once on 7 October 2026 on dates around the 23rd–25th of each
month rather than on month-ends. Its US Stage 2 6-month excess read +2.98%
against the page's +2.53%. Nothing used it, so it was removed. If you see a
study number quoted elsewhere, check that it came from the Study tab.

## 8. Reading checklist

Before you believe a backtest:

- [ ] Verdict line and excess CAGR: did it beat doing nothing?
- [ ] Max drawdown and longest time below a peak, against the benchmark's
- [ ] Closed trades and the expectancy's standard error
- [ ] Trades tab sorted by R: what do the top five contribute?
- [ ] Equity curve: did one or two years make the result?
- [ ] Funnel's last stage and the Caveats: slots, costs, survivorship
- [ ] Version column: current rules (no ▲)? Best of how many variants?
- [ ] Like with like: market, dates, exits, options, costs

Before you believe a screen study:

- [ ] The 1-month excess and its t-statistic, not the 6-month one
- [ ] Hit rate and the month-end chart: broad edge, or a few winners and months?
- [ ] No costs, survivors only, five years

## 9. What the evidence says

- **Robust:** in every run here a few trades decide the result, and the
  median trade is a loss (a full −1R in six of the seven runs above). That is
  the nature of these strategies, and it means results need far more trades
  than intuition suggests.
- **Robust:** none of the app's strategy backtests beat buy-and-hold over
  their full periods, in either market. The screen studies show small
  positive edges for stricter trend screens, before costs.
- **Fragile:** most differences between variants and between versions are
  within one or two standard errors. Rankings of variants should not be
  trusted on their own.
- **Fragile:** results that change sign between halves of the period (US
  trend pullback) or rest on one or two calendar years (US Donchian).
- **Often missed:** which statistic you are looking at. Closed trades or all
  trades, R or dollars, 1-month or overlapping 6-month windows, the current
  version or a superseded one.

## Further reading

- Robert Carver, *Systematic Trading* — reading backtests, costs, and why
  most measured differences are noise.
- David Aronson, *Evidence-Based Technical Analysis* — data-mining bias and
  testing many rules on one history.
- David H. Bailey and Marcos López de Prado, "The Deflated Sharpe Ratio"
  (Journal of Portfolio Management, 2014) — adjusting a backtest's Sharpe for
  the number of variants tried.
- Campbell R. Harvey, Yan Liu and Heqing Zhu, "…and the Cross-Section of
  Expected Returns" (Review of Financial Studies, 2016) — why a t-statistic
  of 2 is too low a bar when many ideas are tested.
