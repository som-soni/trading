# App-specific material moved out of learn-start-here

## From §1 (Dividends) — phrase removed

**Dividends.** Some companies pay out part of their profit as cash, usually
quarterly or yearly. A price chart normally ignores dividends, so it
understates what holding the share actually returned — by roughly 1.9% a year
on the S&P 500 and 0.8% a year on the Nifty, measured over the windows this
project uses. Returns that include them are called **total return**.

## From §4 (costs) — repo research reference removed

The last row is the one that decides things. A strategy trading monthly pays
short-term rates on everything it makes; one that holds for years defers tax
entirely. In the index-investing work in this repo that difference was worth
1–3 percentage points a year — larger than most of the effects being tested.

## §7 What this app is, and what it is not (removed whole)

## 7. What this app is, and what it is not

It screens and backtests; it does not trade. Nothing here places an order or
connects to a broker. The screener produces a list of candidates each day from
stored price data, and the backtester measures whether a set of rules would
have made money in the past — with costs, with a cap on how many positions can
be held at once, and with deliberately pessimistic fills.

Two things to hold on to while reading any result in this project:

- **A backtest is not a promise.** It is one path through history, with the
  rules chosen after seeing some of that history. The research logs state
  their own biases; read those sections before trusting a number.
- **Most of what is tested here did not work.** The honest summary of
  [momentum-trend-research.md](momentum-trend-research.md) is that no hand-built strategy in this repo has
  beaten simply holding the index in both markets. That is a normal result,
  and a reason the guides spend more time on risk than on entries.

## From §8 Where to go next — link to a non-Learn research document removed

| when to put money into an index | [index-investing-research.md](index-investing-research.md) |
