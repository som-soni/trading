# Screens and strategies — two different questions, and where each rule belongs

Learning material: a screen tells you what is *worth looking at*; a strategy
tells you what to *do about it*. They are judged differently, they fail
differently, and the most common structural mistake in a trading system is
letting one do the other's job.

Companion guides: [learn-system-filters.md](learn-system-filters.md) (the
stages between a universe and a trade) and
[learn-system-families.md](learn-system-families.md) (what the bet is).

**Where this shows up in the app.** The **Screens** page lists each screen and
its criteria; the **Strategies** page lists each strategy, the screen it draws
from, its gates, flags and setups. In the code the split is physical:
`scripts/swing_screener/screens/` and `scripts/swing_screener/strategies/`.

---

## 1. The two questions

**A screen asks: does this stock qualify?** It is a list of conditions over
one day's data. It has no entry price, no stop, no position size and no
opinion about when to buy. Its output is a list.

**A strategy asks: is there a trade here, and what exactly is it?** It starts
from a screen's list and adds everything that makes a trading system — the
setup, the trigger, the entry, the stop, the target, the exit and the size.
Its output is a decision.

The difference is not academic. It determines how each is *tested*:

| | screen | strategy |
|---|---|---|
| output | a list of stocks | a trade with a price and a size |
| tested by | forward returns of the list over time | a backtest with costs, slippage and a position cap |
| failure looks like | the list is no better than the market | the equity curve trails the benchmark |
| typical lifetime | years — these are slow-moving conditions | revised often |

A screen can be perfectly good and still produce no profitable strategy,
because *when* and *how* you buy from the list is a separate problem.

## 2. What a screen is made of

Named criteria, each of which is a single question with a single threshold.
In this app the four screens are:

| screen | thesis | criteria |
|---|---|---|
| **Stage 2 — Trend Template** | big winners come from confirmed long-term uptrends that are stronger than the market | 8 |
| **Established uptrend** | pullbacks only work inside a trend that already exists on both the weekly and daily charts | 8 |
| **Near highs, rising 200-day** | breakouts that work complete near the highs, above a long-term average that is not falling | 3 |
| **Above the 200-day** | the broadest filter: a long-only system should not buy under its 200-day average | 1 |

Two design rules make that set maintainable, and both are worth copying:

**One question, one place.** Several screens ask whether price is above the
200-day average. That question is implemented once; each screen supplies its
own threshold where it needs a different one. Otherwise tuning one screen
moves another without anyone noticing.

**A threshold is a named constant, never a number in prose.** The page that
explains a screen renders the live value, so documentation cannot drift from
behaviour.

## 3. What a strategy adds

Everything that turns a name into a position:

- **Setups** — the specific patterns it recognises, each with a code so a
  report can say which one fired.
- **Gates** — hard rules; failing one means no trade, with a reason.
- **Watch flags** — soft warnings that cap confidence instead of vetoing.
- **Entry, stop, target** — the three prices.
- **Exits** — how a trade ends when none of those three is hit.
- **Sizing** — how the stop distance becomes a number of shares.

The five strategies here, and the screen each draws from:

| strategy | screen | setups |
|---|---|---|
| `trend_pullback` | Established uptrend | pullback, continuation base |
| `chart_pattern` | Near highs | twelve chart patterns |
| `breakout` | Near highs | range breakout, coil |
| `minervini` | Stage 2 | contraction breakout, coil |
| `donchian` | Above the 200-day | channel breakout, coil |

Note that two strategies share a screen. That is normal and desirable: the
screen says "these are in the right condition", and each strategy expresses a
different bet about them.

## 4. Where does this rule belong?

The practical test: **would this rule still make sense if I were not trading
today?**

- *"Price is above a rising 200-day average"* — true regardless of whether
  there is a setup. **Screen.**
- *"Earnings are inside ten days"* — only matters because you are about to
  take a position. **Strategy.**
- *"Within 15% of the 52-week high"* — a condition of the stock. **Screen.**
- *"The stop would be more than 8% away"* — a property of the trade, not the
  stock. **Strategy.**
- *"ATR is above 10% of price"* — ambiguous, and either can be right. Decide
  by asking which you want to reuse: if every strategy should refuse it, it is
  a screen criterion.

Getting this wrong has a specific cost. A trade rule hidden in a screen is
applied to strategies that never wanted it; a qualification rule hidden in a
strategy has to be rewritten for the next one.

## 5. The mechanism that stops them drifting

When a strategy's gate *is* a screen criterion, it should not be a second
implementation of the same idea. In this app a strategy declares the mapping
— this gate is that criterion — and both evaluate the same code. Four of the
five strategies map most of their trend gates this way.

The fifth, `chart_pattern`, declares no mapping at all: every one of its five
gates is its own trade rule, and the screen stands in front of it untouched.
Both arrangements are fine. What is not fine is a gate that *looks* like a
screen criterion and quietly uses a different number.

## 6. How each is judged

**A screen is judged by a forward-return study:** take the list it produced at
each month-end, measure what those names did over the following weeks and
months, and compare with the market. A good screen's list beats the index on
average. No entries or stops are involved.

**A strategy is judged by a backtest:** simulate the trades with costs,
slippage, a position cap and a shared pool of capital, and compare the
resulting equity curve with buying the index.

Keeping these apart tells you *where* a system is broken. If the screen's list
beats the market and the strategy loses, the problem is entries, exits or
sizing. If the list does not beat the market, no amount of entry tuning will
save it.

## 7. What the evidence says

- In this app, **no strategy has beaten its benchmark**, across five families
  and many revisions.
- The split has nevertheless paid for itself diagnostically: because screens
  are tested separately, it is possible to say that the trouble is not
  entirely in the qualification stage.
- **The clearest measured win came from a stage above both** — a market filter
  deciding whether to trade at all.
- A caution that follows from the structure: when two strategies share a
  screen, their results are correlated. Four of the five here draw from
  trend-following screens, so they tend to be wrong at the same time.

## 8. Checklist

1. For each rule: does it describe the **stock** or the **trade**?
2. Is any question implemented twice with different numbers?
3. Does each screen have a thesis you could state in one sentence?
4. Is the screen tested on its own, separately from the strategy?
5. If the strategy loses, do you know whether the list was any good?
6. How many of your strategies draw from the same screen — and would they all
   be wrong together?

## Further reading

- Robert Carver, *Systematic Trading* — separating the forecast from the
  position, which is the same split one layer down.
- Marcos López de Prado, *Advances in Financial Machine Learning* — chapters
  on backtest overfitting; the argument for testing components separately.
