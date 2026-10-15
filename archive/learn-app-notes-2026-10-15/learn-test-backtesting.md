# App notes moved out of learn-test-backtesting

Everything below was removed from the guide verbatim (app-specific, or evidence from the app's own strategy backtests, which Learn must not cite). Section numbers refer to the old guide.

## Intro (lines 3-23 of the old guide)

Learning material: what a backtest is, and the main ways it misleads. These are
trying too many variants, using information from the future, testing only the
companies that survived, bad data, costs, fills and gaps, results that come from
one kind of market, and samples too small to mean anything. Each one comes with a
real example from this app and a measurement on its stored runs. Then come the
defences: holding data back, robustness checks, and a checklist to run before a
test.

**Where this shows in the app.** Each strategy's page on **Strategies** has a
**Backtests** tab. It lists that strategy's stored runs grouped by version, and
says when runs "do not reflect the current rules". **System → Reports archive**
opens any run, with the tabs *Report*, *Funnel*, *Equity curve* and *Trades*.
Each screen has a **Study** tab, which tests the screen on past month-ends
instead of trading it. The research notes behind the strategies are in the same
archive, under *Research notes*.

**The data.** The 46 stored backtests (`report_runs`, with their trade and
equity tables), each strategy's latest full run at its current rules, and two
research notes that tested many variants: the Minervini parameter sensitivity
notes for the US and India. All results are backtests with modelled costs. My
analysis scripts are not part of the app.

## §2 How this app's backtester works (whole section)

## 2. How this app's backtester works

The portfolio backtester walks the calendar one session at a time, across all
stocks together, with one pool of money. Each day it sees only data up to that
day. It first closes positions that hit an exit, then fills waiting buy orders
(if a position slot and the cash are free), cancels stale orders, and finally
turns today's signals into orders for later days. Each detail is an assumption:

| Item | What the code does |
|---|---|
| Entry | A buy-stop order at the strategy's trigger, filled only on a **later** day whose high reaches it. Never on the signal day itself. |
| Gap up at entry | Filled at the open if the stock opens above the trigger (a worse price). Skipped if it opens past the whole target. |
| Unfilled orders | Cancelled after 10 business days. The Minervini spec's "next open" orders live for one day only. |
| Stop | Filled at the stop price, or at the open if the stock opens below it. |
| Stop and target on the same day | Counted as a stop. Daily bars cannot show which came first. |
| Exit modes | `bracket` (fixed stop and target), `trail_atr`, `ma`, `donchian`, `minervini`. A time stop exists only in the Minervini exits, and is off by default. |
| Costs | Slippage of 5 bp per side in the US and 10 bp in India, no commission. The Minervini spec runs add charges: 1 bp + 5 bp slippage (US), 12 bp + 15 bp (India), with slippage doubled for stocks trading under $25 million / ₹25 crore a day. |
| Position size | 1% of current equity at risk per trade, capped at 25% of equity in one stock. At most 10 positions (8 in the Minervini spec runs). |

(A basis point, bp, is a hundredth of a percent: 5 bp = 0.05%.)

What it **does not** do, unlike a live trader using the app:

- **Earnings dates are ignored.** No history of past earnings dates is stored,
  so trades the live screen would block before results can appear.
- **High-volatility sizing is ignored.** Live sizing halves risk to 0.5% in a
  volatile market; the backtest risks 1% (unless a run turns on its own
  progressive-exposure rule).
- **The live market downgrade is not applied.** The `--market-filter` option is
  a simpler rule: no new buys while the benchmark is below its 200-day average,
  or its 50-day is below its 200-day. Minervini uses it by default from v1.7.
- **There is no sector limit.**


## §3.1-3.3 (variant counts, best vs typical variant, inside the winner)

### 3.1 How many variants this app has tried

The danger grows with the number of tries, so count them honestly:

| Strategy | Stored backtests | Other variant runs on record |
|---|---|---|
| Minervini, US | 22 (3 rule versions) | 46 runs in the sensitivity note (23 settings × 2 entry methods) |
| Minervini, India | 15 (7 rule versions) | 46 runs in the sensitivity note (23 settings × 2 entry methods) |
| Donchian | 1 US, 2 India | sample vs full universe, three rankings (research log) |
| Breakout, trend pullback, chart patterns | 1–2 per market | earlier versions and exit tests in the research log |

The stored Minervini runs vary the failed-breakout exit, liquidity floors,
pyramiding, fundamentals filters, progressive exposure and the market filter.
Each is a reasonable question; together they are dozens of looks at the same
16 years of data.

### 3.2 The best variant against the typical one

Sixteen full-history US Minervini runs (2010 to October 2026) are stored.
Closed trades only; the standard error (SE) is the uncertainty of the average,
explained in [Expectancy](learn-risk-expectancy.md) §5:

| Variant | Trades | Expectancy | SE | CAGR | Max drawdown |
|---|---|---|---|---|---|
| Market filter on (the v1.7 baseline) | 482 | +0.056R | 0.069 | 1.34% | −28.6% |
| $100M liquidity floor (v1.5) | 560 | +0.045R | 0.066 | 0.85% | −42.2% |
| v1.6 default | 551 | +0.043R | 0.065 | 0.65% | −43.5% |
| Progressive exposure | 583 | +0.030R | 0.063 | 0.58% | −34.6% |
| Fundamentals "covered" | 479 | +0.026R | 0.068 | 0.63% | −36.3% |
| No liquidity floor (v1.5) | 615 | −0.022R | 0.060 | −1.17% | −48.8% |
| Failed-breakout exit after 2 days (v1.5) | 836 | −0.056R | 0.038 | −3.02% | −50.9% |
| Fundamentals "acceptable" | 114 | −0.101R | 0.150 | −0.70% | −17.9% |

Across all 16, expectancy runs from −0.10R to +0.06R. The median is +0.03R. CAGR
runs from −3.0% to +1.3%, median 0.5%. **The best variant beats the median by
0.026R. That is less than half of one standard error.** The ranking of these
variants is mostly noise.

### 3.3 Looking inside the winner

Version 1.7 made the market filter the default, because it was the first change
to improve return and drawdown together. The filter comes from the written
specification and is an old, widely used idea, not something found by
searching. But the trade lists show how little the expectancy gain proves:

| Trades | Count | Average R | SE |
|---|---|---|---|
| In both runs | 450 | +0.07R | 0.07 |
| Only in the v1.6 run (mostly blocked by the filter) | 101 | −0.07R | 0.14 |
| New, taken in the freed slots | 32 | −0.10R | 0.19 |

The trades the filter removed were slightly negative, well within noise. The
case for it rests on the **drawdown** (−43.5% to −28.6%), the thing it was
designed to cut. That is how a variant should be adopted: for a reason stated
before the test, with an effect in the direction the reason predicts.


## §4 Look-ahead bias — app-specific cases

## 4. Look-ahead bias

**Look-ahead bias** means the test uses information that did not exist yet on
the day of the decision. It is the most common cause of a backtest that looks
too good. This app has found and fixed several cases, each a pattern worth
knowing:

- **Choosing stocks by today's data.** Picking the stocks to test by whether
  they pass the pre-filter *today* drops every stock that trended for years but
  is resting now. Measured on US data, it silently excluded 1,421 of 2,544 real
  candidates. The backtester now includes any stock that passed on at least one
  day of the test window.
- **Knowing the close at the moment of a touch.** Since v1.1 the Minervini
  buy-stop needs a close above the pivot. Filling it at the intraday trigger
  would use information (how the day closed) that did not exist at the touch,
  so the fill is the close.
- **Today's industry for past dates.** Group strength is rebuilt for each past
  date from prices up to that date, but the industry classification is today's.
  Companies rarely change industry, so the error is small, not zero.
- **Fundamentals as they are now.** The app stores quarterly results with their
  filing date, and the fundamentals filter uses only results public on the
  signal day. Analysts' estimates have no history, so that test is left out.
  The history starts in 2021 and covers part of the universe.

A milder case: in the `ma` and `donchian` exit modes, an exit triggered by a
close fills *at that close*. In practice you would sell near the close or at the
next open, which the Minervini exits use.


## §5 Survivorship — app universe facts

This app's universe is a list of today's listed stocks. Checked against stored
prices: of the 5,387 US and 3,418 Indian names with prices, only one has a last
price older than September 2026. About half the US list (2,648) and a third of
the Indian list (1,112) have prices back to January 2013. Every backtest report
states the bias. It cannot be fixed without past listings. The effect is
largest in small caps — and the research log notes that India's momentum
premium sits in small and mid caps.

**A related trap: split-adjusted prices.** Stored prices are adjusted for later
splits. Version 1.2 of the Minervini strategy found that a minimum *price* rule
($10 in the US) read against adjusted history removed the early years of the
best stocks. NVIDIA traded around $15 in 2013. After later splits the stored
price is about $0.30–0.40, so the price rule kept NVIDIA out until July 2020.
The fix uses traded value (price × volume), which splits do not change.

## §6 Bad data — HEG runs table, split-gap check counts, caption

caption: Volume on the day was about 1.6 times normal, not the flood a real collapse brings. Two India backtests were "stopped out" here, at −7.3R and −8.6R.
```

Two current India runs held HEG through that day:

| Run | Fake loss | Expectancy with it | Without it | Share of the run's net profit lost |
|---|---|---|---|---|
| Chart patterns, India (515 trades) | −7.3R, ₹2.8 lakh | +0.141R | +0.155R | about 22% |
| Trend pullback, India (347 trades) | −8.6R, ₹2.6 lakh | +0.116R | +0.142R | about 35% |

The app has a check for this. It looks for split-shaped gaps (a one-day move
close to a split ratio such as 1:2 or 1:5). Today it lists 693 suspect gaps in
446 US stocks and 182 in 101 Indian stocks. The Minervini reports count the
trades held across one. HEG's gap is a ratio of about 2.7, not a split ratio,
so **the check does not catch it**. No automatic check catches everything.

**Earnings per share (EPS) errors.** Some stored US EPS figures are not adjusted
for splits, so the P/E (price ÷ trailing EPS) is wrong. Apple's P/E reads as low
as 1.3 in April 2013. Alphabet's reads 0.95 in July 2022. Trent's sales growth
for one quarter, filed in April 2023, reads about 16,300%. Any test that filters
on P/E, EPS growth or sales growth would treat these as real.

**What to do:** look at the worst and best trades of any run by hand. A single
trade beyond −3R or +20R deserves a chart before you believe it.

## §7 Costs (bug fix and India cost table)

## 7. Costs and slippage

Costs are small per trade and large in total. The arithmetic in R is in
[Expectancy](learn-risk-expectancy.md) §7. Two of this app's own examples:

**A bug fix moved results in both directions.** Until 9 October 2026 the
portfolio simulator charged slippage on exits twice. After the fix, re-measured
runs moved by −0.8 to +0.9 points of CAGR. India Minervini went from 4.38% to
4.98%. US Minervini went from −0.95% to −1.70%. Cheaper trading made the US run
*worse*, because the extra cash changed which later signals the account could
afford. **A small change in an assumption reshuffles which trades are taken,
and the result can move either way.** The research log warns that its figures
measured before the fix should be re-run before being relied on.

**India costs are understated outside the Minervini runs.** They model 10 bp of
slippage per side and nothing else. Real Indian trading also pays securities
transaction tax (STT), stamp duty, exchange fees and GST on brokerage. Adding
0.24% per round trip to every closed trade:

| India run | Expectancy as stored | With 0.24% more per round trip | Typical extra cost per trade |
|---|---|---|---|
| Chart patterns (515 trades) | +0.141R | +0.101R | 0.039R |
| Trend pullback (347) | +0.116R | +0.075R | 0.038R |
| Donchian (437) | +0.419R | +0.391R | 0.027R |

A third of the chart-pattern and trend-pullback edge goes. Donchian barely
notices, because its edge is large. Taxes on gains are not modelled anywhere.


## §8 Fills and gaps (run table)

## 8. Fills and gaps

Daily bars show four prices a day. The backtester has to guess the rest, and its
guesses are deliberately on the cautious side: a stop and target touched on the
same day count as a stop, and a gap fills at the open.

Even so, gaps matter. Share of stop exits filled more than 1% below the stop,
because the stock opened below it:

| Run | Stop exits | Filled >1% below the stop | Worst trade |
|---|---|---|---|
| Donchian, US | 288 | 9.0% | −7.4R |
| Trend pullback, US | 633 | 7.6% | −6.0R |
| Volume breakout, US | 462 | 6.7% | −4.1R |
| Donchian, India | 257 | 5.4% | −2.1R |
| Chart patterns, India | 350 | 4.0% | −7.3R (HEG, §6) |
| Minervini, US | 139 | 2.2% | −2.0R |

What daily bars still cannot show: a stock that is locked at its lower circuit
limit in India (no buyers at any price), thin order books in small stocks, and
whether you would really have been at the screen. The [stops and exits
guide](learn-risk-stops-exits.md) has the real gap examples.


## §9 Results from one kind of market (year table)

## 9. Results that come from one kind of market

A strategy can look good over 14 years because of two or three of them. Total R
by the year the trade was entered (2026 is to October):

| Year | Donchian US | Donchian India | Trend pullback US |
|---|---|---|---|
| 2013 | +53 | +69 | +36 |
| 2014 | +5 | +20 | +14 |
| 2015 | −21 | −17 | −8 |
| 2016 | +99 | +9 | −2 |
| 2017 | +35 | +17 | +48 |
| 2018 | −7 | −17 | −11 |
| 2019 | +1 | −5 | −2 |
| 2020 | −8 | +44 | +31 |
| 2021 | −15 | +7 | −20 |
| 2022 | −37 | −14 | −20 |
| 2023 | +104 | +113 | −26 |
| 2024 | +7 | −1 | −8 |
| 2025 | +36 | −27 | −21 |
| 2026 | −10 | −15 | −20 |
| **Total** | **+241** | **+183** | **−12** |

- US Donchian made 203R of its 241R in two years, 2016 and 2023. In the other
  twelve it made 38R.
- India Donchian made 182R of its 183R in 2013 and 2023.
- Trend pullback US made money in 4 of the first 8 years and lost in every year
  since 2021.
- Donchian lost money in 6 (US) and 7 (India) of the fourteen years.
- In the other six current runs, the best two years made *more* R than the
  whole run did.

That is normal for trend following: it earns in long, broad advances and gives
some back in between. But it means **the result depends on whether those few
years repeat.** The research log adds a further caution: 2013–2026 has no long
bear market like 2000–02 or 2008. The market-level guides describe how to
recognise the kind of market you are in ([the trend guide](learn-health-trend.md)).


## §10 Small samples (app examples)

## 10. Samples too small to mean anything

The full treatment is in [Expectancy](learn-risk-expectancy.md) §5: the error of
an average shrinks only with the square root of the number of trades. Three
examples from this app:

- **A few trades.** The fundamentals "leader" filter left 24 US trades, with a
  standard error of 0.34R — larger than any difference it could show
  ([quality guide](learn-fund-quality.md) §12). The Minervini v1.5 changelog
  turned the low-cheat entry off on 25 trades and said so: "a thin basis".
- **A sample of stocks.** Donchian in India looked like it beat the index by
  3.06% a year on a 500-stock sample. On the full universe it trailed the index
  by 4.34%. The cause: with more stocks competing for 10 slots, the rule that
  breaks ties decides which trades are taken, and that rule was arbitrary.
- **One-parameter tests on tiny counts.** In the US sensitivity note, one
  variant made +0.31R in-sample on 12 trades and −0.76R afterwards on 2.


## §11 In-sample / out-of-sample (half splits, sensitivity notes, walk-forward note)

## 11. Holding data back: in-sample and out-of-sample

The basic defence against overfitting is to **hold data back**. Develop and tune
the rules on one period (**in-sample**). Then test them once on a period you did
not look at (**out-of-sample**). If the result holds, the rules probably found
something real. If it collapses, they fitted noise.

### 11.1 First half against second half

None of this app's strategies was built on a formal in-sample period. But the
same check can be made on each current run by splitting its trades at the middle
of the test period (late 2019 for the 2013 runs, mid-2018 for the 2010 runs).
Expectancy, with the standard error in brackets:

| Run | First half: trades, expectancy | Second half: trades, expectancy | CAGR first / second |
|---|---|---|---|
| Donchian, US | 235, +0.71R (0.31) | 261, +0.29R (0.30) | 9.0% / 4.2% |
| Donchian, India | 224, +0.34R (0.24) | 213, +0.50R (0.29) | 5.7% / 9.8% |
| Chart patterns, India | 159, +0.03R (0.14) | 356, +0.19R (0.10) | 0.7% / 6.6% |
| Volume breakout, US | 342, −0.01R (0.09) | 361, +0.09R (0.08) | 0.7% / 3.7% |
| Trend pullback, US | 430, +0.18R (0.10) | 433, −0.20R (0.09) | 5.8% / −2.1% |
| Trend pullback, India | 92, −0.05R (0.19) | 255, +0.17R (0.13) | 0.7% / 4.0% |
| Minervini, US (v1.7 rules) | 215, +0.10R (0.11) | 267, +0.03R (0.09) | 2.1% / 0.6% |
| Minervini, India (v1.5) | 59, +0.18R (0.19) | 133, −0.00R (0.10) | 0.9% / 0.1% |

(CAGR of each half is computed from the run's equity curve.)

- **Donchian is positive in both halves in both markets.** That is what a real
  effect looks like, even though the size moves a lot.
- **Trend pullback US flipped**: +0.18R, then −0.20R. The gap is about 2.9
  standard errors — unlikely to be chance alone. Something that worked in
  2013–2019 stopped working.
- Most other runs move by about one standard error between halves. That is
  noise: neither half proves anything on its own.

### 11.2 The best in-sample variant, out of sample

The Minervini sensitivity notes moved one parameter at a time and split every
run at the end of 2019. For each of the four tables (two entry methods, two
markets), here is what happened to the variant that looked best before 2020:

| Table | Best variant before 2020 | Before 2020 | After 2019 |
|---|---|---|---|
| US, buy-stop entry | `prior_advance 50%` | +0.14R (183 trades) | −0.11R (159) |
| US, next-open entry | `tight_days 15` | +0.31R (12) | −0.76R (2) |
| India, buy-stop entry | `tight_days 15` | +0.25R (10) | −0.22R (35) |
| India, next-open entry | `tight_days 5` | +1.18R (9) | +0.10R (16) |

The best in-sample variant fell sharply every time. Across all variants, the
in-sample ranking said almost nothing about the out-of-sample ranking: the rank
correlations were −0.23 (US, buy-stop) and −0.12 (India, buy-stop). In the US
buy-stop table, 18 of 19 distinct variants did worse after 2019 than before. (These notes
were generated on 9 October 2026 with earlier rules; the lesson does not depend
on the version.)

### 11.3 Walk-forward

**Walk-forward testing** repeats the split: tune on, say, five years, test on
the next year, move forward a year, and repeat. The joined-up test years form an
out-of-sample record. The written Minervini specification lists it as the second
validation step. **The app does not run it.** Its backtester calls itself
"walk-forward" only because each day sees only earlier data; nothing is re-tuned
on a rolling window.


## §12 Robustness (sensitivity neighbourhoods, both markets)

## 12. Robustness checks

A real edge should survive small changes. Three checks:

**Parameter neighbourhoods.** Move each setting one step either way. A real
edge fades gradually. An edge that vanishes after a small change was probably
fitted. The sensitivity notes do exactly this. In the US buy-stop table, the
default made −0.81% a year while its neighbours ranged from −2.89% to +1.23%.
Nothing was stable enough to call an edge.

**Sub-periods.** Split by halves (§11.1), by year (§9) or by market regime. Ask
whether the result needs one particular stretch.

**Both markets.** The same rule tested in the US and India is close to an
independent test. Applied to the Minervini buy-stop variants:

| Variant | US CAGR | India CAGR |
|---|---|---|
| `tight_days 15` | +1.23% | −0.32% |
| `swing_k 7` | +1.20% | −0.46% |
| default | −0.81% | +0.10% |
| `dryup 0.85` | −1.57% | +0.96% |

The four best US variants all lost money in India. The best India variant was
among the worst in the US. The rank correlation between the two markets was
−0.53. **No setting was good in both.** By contrast, Donchian's expectancy is
+0.49R in the US and +0.42R in India, and positive in both halves of both. It
is the only result here that passes the sub-period and market checks. It still trailed the
index in both markets ([Expectancy](learn-risk-expectancy.md) §8).

Two more checks are covered elsewhere: resampling the trade order to see the
range of possible drawdowns ([Position sizing](learn-risk-sizing.md) §7), and
how a strategy's run-to-run rank changes — chasing last year's best strategy
lost money here ([biases guide](learn-process-biases.md)).


## §13 Results go stale (versions, golden tests, stored studies)

## 13. Results go stale

A stored result belongs to the code and data that produced it. Both change.

- **Versions.** Each strategy has a `version` and a `changelog`. Each run is
  stamped with a spec id, `v<version>-<fingerprint>` (the fingerprint comes from
  the strategy's numeric settings). The Backtests tab groups runs by it and
  warns when later changes exist. `tests.test_strategy_versions` fails if the
  settings change without a new version number.
- **Unchanged behaviour, proven.** `tests.golden_strategies` records every
  strategy's decisions for 120 sampled stocks per market on frozen data. A
  refactor that should change nothing must reproduce them exactly.
- **Stored studies.** An old stored copy of the screen studies was computed
  once, on 7 October 2026, on dates that were not month-ends (for example
  24 September 2021), and was never updated. The Study tab ignored it and
  recomputes on request; the copy was removed on 15 October 2026. Check the
  date and method of any stored number before quoting it.
- **Bug fixes.** A number measured before a fix (like the cost fix in §7) is a
  different measurement.


## §14 Evidence bullets and §15 checklist items about the app

## 14. What the evidence says

- **Robust:** the best of many backtests overstates the truth. Bailey, Borwein,
  López de Prado and Zhu showed how fast; Harvey, Liu and Zhu argued a new factor
  needs a much higher bar than the usual "t above 2". Here, the best in-sample
  variant fell sharply out of sample in all four sensitivity tables.
- **Robust:** survivorship and look-ahead bias inflate results. Both are present
  here in small, named forms.
- **Measured here:** one bad price cost a run a fifth to a third of its net
  profit; a cost-model fix moved CAGR by up to 0.9 points either way; a 500-stock
  sample moved a result by 7.6 points a year.
- **Measured here:** results lean on two or three years, and the differences
  between variants are usually smaller than one standard error.
- **Folklore:** that a long backtest with hundreds of trades is "proven". Seven
  hundred trades could not separate the US breakout's +0.04R from zero.
- **The honest summary of this app's tests:** Donchian's positive expectancy
  survives every check here. Nothing has beaten simply holding the index after
  costs.

## 15. Before you run a test — checklist

- [ ] Write the idea and the reason for it *before* testing. Predict the direction of the effect.
- [ ] Decide the test period, the out-of-sample period and the costs in advance. Do not look at the held-back period until the end.
- [ ] Count every variant you try, including the ones you throw away.
- [ ] Change one thing at a time, as a new version with its own run.
- [ ] Check that every input was known on the decision day: prices, industry, fundamentals (filing date), index membership.
- [ ] Use realistic costs. India: add STT, stamp duty and exchange charges.
- [ ] Open the five best and five worst trades on a chart. Look for data errors.
- [ ] Split the result by half, by year and by market. Note how much comes from the best two years.
- [ ] Compare the difference you care about with its standard error. Under two is noise.
- [ ] Compare with the benchmark and the momentum baseline, over the same dates.
- [ ] Record the run's spec id. Re-run after any fix to the simulator or data.

