# The RS line in Minervini's setups — a study scope

*Status: **scoped 2026-11-09, not run.** Definitions, samples and pass criteria are fixed here before any data is
read, so the result cannot shape the test. Built and run after the 1.57 baseline backtests (#1338 US, #1339 India)
finish, because they write the signal cache this study reads.*

## Why

Four of Minervini's book cases point at the RS line (the stock's close ÷ the market's) ([book cases](minervini-book-cases.md)):

| Case | What the RS line did | What our strategy did |
|---|---|---|
| Amazon, Oct 2002 | New 52-week highs in Sep–Oct, price 12% under its base high, index at new lows | Refused: market gate closed, entry rules |
| eBay, Jan 2003 | New highs from Sep 2002 on, well before the price | Missed: base anchored on an old high (gate also closed) |
| Wal-Mart, 1981–82 | New highs again and again while the index fell 27% | Refused: liquidity floor, market gate at every buy point |
| Netflix, Oct 2009 | **Lagged** through the base and at the breakout | Bought on his day |

Two ideas follow, and Netflix limits both:

1. **Evidence.** An RS line at a new high when a setup triggers marks a better trade.
2. **A gate override.** Our market gate refuses new buys while the index is below a rising 50-day average. In three of
   the four cases it refused a stock whose RS line was making new highs *against* a falling index: the strongest
   stock at its strongest moment. Let such a stock through a closed gate.

Netflix's best trade came with a lagging RS line, so the RS line can never become a hard gate for every setup.

## What is already known — and what this study adds

The [breakout anticipation study](breakout-anticipation-study.md) (2026-11-06) measured the same signal,
"RS line at its 55-session high before price clears its pivot":

- **US:** it predicted that a breakout *happens* within four weeks (a lift of 1.20 in discovery, 1.21 on the
  2022–2026 hold-out). The chance that the breakout *followed through* stayed at about 36%.
- **India:** no lift.

That study used the `breakout` strategy's setups and a four-week follow-through. This one asks different questions:

- the **Minervini** setups (S1–S9) as the strategy itself finds them;
- **trade outcome in R** under the strategy's own exits, not a four-week window;
- and the **gate-closed subset**, which no study has looked at.

## Questions

- **Q1 — evidence.** Among setups that trigger, does an RS line at a new high on the signal day mean a better trade?
- **Q2 — gate override.** Among setups that trigger *while the market gate is closed*, do the ones whose RS line
  is at a new high pay well enough to take?
- **Q3 — the cost of a gate.** Of the best trades, how many had a lagging RS line at the signal? That is what an
  RS-line requirement would throw away (the Netflix case).

## Definitions (fixed now)

| Term | Definition |
|---|---|
| RS line | Close ÷ the market benchmark: the S&P 500 (US), the Nifty 500 (India), as the stock snapshot uses |
| **RS55** | RS line at or above its highest of the 55 sessions before the signal day: the snapshot's `rs_line_high` (`core/indicators.at_prior_high`), as the anticipation study's R2 |
| **RS252** | RS line at its highest of the 252 sessions before the signal day |
| **Divergence** | RS252 on a day the benchmark closes below its 50-day average |
| Setup | A Minervini setup (S1–S9) that triggers: a row of the 1.57 signal cache with a setup and every hard gate passed |
| Gate closed | The strategy's own market gate (`backtesting/spec.market_ok`, the guide's test with its 5-session confirmation) is off that session |
| Trade | The setup's plan as `build_plans` makes it, managed by the strategy's own exits (`ExitPolicy`, mode `minervini`), **one trade at a time per setup**: no portfolio limits, no results blackout. Result in R, net of the market's cost model |

## Samples

- **Window: optimise only, 2013-01-01 → 2021-12-31.** Both markets.
- The verify years (2022 on) are not read. The anticipation study already spent its one look at 2022–2026 on its
  own question. Any rule this study proposes gets its own verify run, once, as a new version.
- The trades the strategy refuses for reasons other than the gate (risk over 10%, R under the minimum, liquidity)
  stay out, as they would in a backtest.

## Measurements

For each market, and for gate-open and gate-closed setups separately:

| Group | Reported |
|---|---|
| All setups | n, mean R, median R, win rate, share of trades ≥ +5R |
| RS55 / not RS55 | the same, and the difference in mean R with a bootstrap 95% interval |
| RS252 / not | the same |
| Divergence / not (gate-closed only) | the same |
| Top 5% of trades by R | share with RS55 and with RS252 at the signal (Q3) |

Also, by setup (S1 breakout, S2 coil, S4 3-C and so on), so a result that comes from one setup is not credited to
all of them.

## Pass criteria (decided now, before the data)

- **Q1 passes** if, in **both** markets, setups with RS55 average at least **+0.10R** more than those without. The
  sign must agree in both, and the bootstrap 95% interval must exclude zero in at least one. A pass makes RS55 a
  watch flag on the setup card and a ranking input when slots are short. It never becomes a gate.
- **Q2 passes** if, in **both** markets:
  1. gate-closed divergence setups number at least 100 trades;
  2. they average at least the mean R of gate-open setups;
  3. their worst calendar year is no worse than −1R per trade.

  A pass builds a research switch (off) that lets a divergence setup through a closed gate, at pilot size. That
  switch runs as an optimise variant. It is adopted only if the variant raises CAGR in both markets without
  deepening the maximum drawdown by more than 2 points. Then it gets one verify run, as its own version.
- **Q3** is reported, not judged. If more than a third of the top-5% trades had no RS55, Q1's flag must not be used
  to filter, only to rank.
- **A failure is reported as one**, in this note and in the strategy's `status`, as the other studies have been.

## Out of scope

- Changing any rule before the pass criteria are met.
- The RS *rating* (the 1–99 rank). G8 already uses it; this study is about the line.
- Using the book cases as evidence: they are chosen after the fact. They motivated the study; they do not count
  in it.

## Build

- `analytics/rs_line_study.py`, offline, reading only stored data: the signal cache, prices, and the benchmarks.
  It reuses `build_plans`, `ExitPolicy` and `market_ok`, not copies of them.
- Its output is written into this note under a **Results** heading, with the reproduce command.
- One process per market. The trades are independent, so the run is minutes, not the hours of a backtest.
