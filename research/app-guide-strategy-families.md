# Using the app — the strategy families it implements: the handful of ways a trade can make money

Learning material: almost every systematic strategy belongs to one of a small
number of families. Each family makes a different bet about what price does
next, needs a different market to work in, and fails in its own
characteristic way. This guide names the families, says what each one needs,
and — for the ones this app implements — what the backtests actually found.

It is a companion to
[app-guide-screens-strategies.md](app-guide-screens-strategies.md)
(where a rule belongs) and
[learn-system-filters.md](learn-system-filters.md) (how a candidate is
narrowed to a trade).

**Where this shows up in the app.** Every strategy in **Strategies** names
its family in the `style` field — `pullback`, `breakout` or `trend`. The
backtests behind each status line are in **Runs** and **Reports**.

---

## 1. Why families, not strategies

Two strategies with different rules can be the same bet. A 55-day channel
breakout and a 20-day channel breakout differ in a parameter; a channel
breakout and a pullback entry differ in what they believe. If you cannot say
which family a strategy belongs to, you cannot say what would have to be true
in the market for it to work — and you will keep building the same bet with
new thresholds, believing you are diversifying.

A family is defined by three things:

1. **The bet.** What must happen for this to pay.
2. **The regime it needs.** The market condition in which that is likely.
3. **The shape of its returns.** Win rate against average win size.

## 2. The families that trade price direction

### Trend continuation

*The bet:* a stock already moving in one direction keeps moving, and a pause
inside that move is an opportunity rather than a warning.

Two common forms: buying a **pullback** (price retraces part of an advance and
resumes) and buying a **continuation base** (price goes quiet near its highs,
then breaks out again). Both need an established trend first, so both spend
long periods with nothing to do.

*Shape:* moderate win rate, moderate winners. Fails when a trend ends — which
looks exactly like a pullback until it does not.

### Breakout from a base

*The bet:* a long quiet period has transferred stock from impatient holders to
patient ones, so when price clears the top of that range there is little
supply left to stop it.

The defining feature is the **base**: a measurable period of contraction
before the signal. Volume usually dries up inside it and expands on the
breakout. This family is the one most sensitive to false signals, because
every base produces a breakout eventually, including the ones that fail.

*Shape:* low win rate, large winners. It depends entirely on cutting the
failures quickly.

### Channel breakout (trend following)

*The bet:* a new N-day extreme means a trend is starting, and the only reliable
way to catch large moves is to take every one of them.

Nearly rule-free by design: no base, no pattern, often no trend filter. It
accepts a poor win rate and many small losses in exchange for never missing a
large move.

*Shape:* low win rate (30-40% is normal), a few very large winners carrying
everything. Judge it on expectancy, never on hit rate.

### Cross-sectional momentum

*The bet:* stocks that have outperformed over the last several months continue
to outperform, relative to each other.

Different from the others in an important way: it is a **ranking** rather than
a chart pattern. You do not ask "is this a good setup", you ask "is this stock
in the top N by return over the last twelve months". There is no entry trigger
and no stop in the classic sense — you hold the top of the list and rebalance.

*Shape:* broad, shallow edge spread over many holdings. It is the family with
the most published academic support.

### Mean reversion

*The bet:* price has moved too far too fast, and will snap back toward where it
was.

Forms include fading the edge of a range, buying a stock stretched a long way
below its moving average, and buying a panic. The bet is the opposite of every
family above, so it needs the opposite market: ranges, not trends.

*Shape:* high win rate, small winners, occasional catastrophic loss — because
"too far" has no upper bound. Risk control matters more here than anywhere
else.

### Reversal and failed moves

*The bet:* a move has ended, and the traders positioned for its continuation are
trapped and will have to exit.

The most reliable form is the **failed breakout**: price clears a level,
fails to hold it, and falls back through. Everyone who bought the breakout is
now losing, and their stops become fuel.

*Shape:* infrequent, high reward when right, and extremely easy to anticipate
too early. Most reversal attempts fail; trends end rarely.

### Rotation

*The bet:* leadership moves between sectors and groups in a sequence, and being
early to the next leader beats holding the last one.

*Shape:* medium-frequency, needs a view on groups rather than single stocks.

### Event-driven

*The bet:* a scheduled event — results, an index change, a corporate action —
creates a predictable flow that can be traded.

*Shape:* rare, concentrated, and dangerous: the event's outcome is unknown, so
position size has to be smaller than the chart alone would justify.

## 3. Which families this app implements

| family | strategy | screen | what the backtest found |
|---|---|---|---|
| Trend continuation (pullback) | `trend_pullback` | `uptrend` | No edge. From 2013: **US 1.75% CAGR** against the benchmark's 12.8% (max drawdown -46.5%); **India 2.30%** against 11.7% (-32.1%). Seven alternative exit policies did not rescue it. |
| Trend continuation (base) | `chart_pattern` | `near_highs` | No edge at v1.5. **India, full universe from 2013: 3.61% CAGR** against 11.6% (-27.8%). The US run at this version is still going. |
| Breakout from a base (range) | `breakout` | `near_highs` | Not validated — the thresholds were never tuned. **US from 2013: 2.15% CAGR** against 12.8% (-29.7%). |
| Breakout from a base (contraction) | `minervini` | `stage2` | No edge. India: 114 trades at -0.03R, profit factor 0.86. US: 526 trades at -0.02R, CAGR -0.8%. One rule did help — the market filter, which took US expectancy from +0.04R to +0.06R and max drawdown from -43.5% to -28.6%. |
| Channel breakout | `donchian` | `above_200` | No edge. **India 7.68% CAGR** against 11.7% (-44.2%), **US 6.53%** against 12.8% (-49.3%). The trade shape is sound; the choice among simultaneous breakouts is arbitrary. |
| Cross-sectional momentum | *(the benchmark)* | — | Built as the bar every strategy must clear, not as a strategy. It is the only approach here that has beaten its index. |

## 4. Which families it does not — and why

Three different reasons, worth keeping apart:

**Not built, but buildable.** Mean reversion in all its forms; moving-average
trend systems; gap continuation; reversal entries; sector rotation as a
strategy; earnings-direction trades. Nothing blocks these except work. Two
have most of their ingredients already: distance-from-average is computed as a
watch flag in several strategies, and group strength is computed and published
for the Sectors page.

**Blocked by missing data.** Anything needing intraday bars (opening-range
breakouts, gap fades) — this app stores daily bars only, and a daily bar
cannot tell you whether the high or the low came first. Anything needing an
options chain. Anything needing index-constituent changes or a
corporate-action feed.

**Blocked by the account, not the data.** Everything requiring a short side:
market-neutral pairs, and trading topping patterns directly. This is a
long-only book. Topping structures are still detected, but they are used to
*veto* a long rather than to open a short.

## 5. What the evidence says

- Of the five families implemented here, **none has demonstrated an edge**.
  Four trail their benchmark by 9 to 11 points of CAGR; the fifth is slightly
  negative.
- The one approach that has beaten its index is **cross-sectional momentum**,
  which is used as the benchmark rather than traded.
- Across many measured changes, exactly one improved both return and drawdown
  together: a **market filter** that stands aside when the index is weak. That
  is a regime rule, not a setup rule — the family and the entry mattered less
  than whether to be invested at all.
- Deep changes to detection quality moved per-trade expectancy by a rounding
  error. A day of refinement to one detector moved it from -0.214R to -0.213R.

Read that as a warning about where effort pays: the choice of *when to be in
the market* has produced more measurable improvement here than the choice of
*what pattern to buy*.

## 6. Checklist

Before building another strategy, answer these:

1. **Which family is this?** If you cannot say, you do not yet have a
   strategy — you have a set of rules.
2. **What market does it need?** Write down the condition in which it should
   lose money. If there isn't one, the rules are too loose.
3. **Do I already have this bet?** Two strategies from the same family are
   one bet in two forms, and they will lose together.
4. **What shape should the returns have?** Decide the expected win rate before
   the backtest, so a 20% win rate reads as normal for a breakout and alarming
   for a mean-reversion system.
5. **What would make me abandon it?** Decide now, while nothing is at stake.

## Further reading

- Andreas Clenow, *Following the Trend* — why trend following has a low win
  rate by construction, and what that does to a return series.
- Narasimhan Jegadeesh and Sheridan Titman (1993) — the original
  cross-sectional momentum paper.
- William O'Neil, *How to Make Money in Stocks* — the base-and-breakout family
  stated in full.
- Perry Kaufman, *Trading Systems and Methods* — the broadest survey of
  families and how each behaves in different regimes.
