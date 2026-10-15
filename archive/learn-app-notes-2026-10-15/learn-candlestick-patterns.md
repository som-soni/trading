# App notes moved out of learn-candlestick-patterns

## Intro — "Where this shows up in the app"

**Where this shows up in the app.** The screener writes a one-line summary of
the recent candles for every candidate. It goes in the `candles` column and is
built by `scripts/swing_screener/core/patterns.py`. The command
`python3 -m swing_screener.screening.inspect --symbol XYZ` prints the stats of
the last five bars, with the patterns it detected. The chart page draws plain
candles. No strategy buys or sells because of a candlestick pattern — see
"How candles are used here" at the end for why.

## §1 Anatomy — the commentary's thresholds

The app's candle commentary measures these with numbers. The rules live in
`core/patterns.py`:

| Measure | Definition | Thresholds used |
|---|---|---|
| Body % | \|close − open\| / (high − low) | doji when ≤ 10% |
| Close location | (close − low) / (high − low) | top ≥ 0.66, bottom ≤ 0.34 |
| Wick ratio | wick length / body length | "long" when ≥ 2× the body |
| Gap % | open vs the prior close | a gap when beyond ±0.3% |
| Volume ratio | volume / 50-day average volume | notable above 1.2 or below 0.8 |

(The table itself is kept in the guide as "common definitions"; the app framing is removed.)

## §2 Context — weekly candle note

3. **A longer timeframe carries more meaning.** A weekly hammer at support
   counts for more than five daily candles. That is why the screener also
   prints a note on the weekly candle (`weekly_candle_note`).

## §3 Marubozu — commentary wording

The
commentary calls these "plain top-range close" / "plain bottom-range close"
when no other pattern applies.

## §3 NR7 — commentary reports it

It is not a classical candlestick, but the commentary reports it: the bar
with the narrowest range of the last 7 bars. ... A cluster of NR7 or inside bars near a pivot is the
daily-chart version of what the VCP strategies look for.

## §4 Harami / inside bar

The commentary flags this as an **inside bar**.

## §5 Morning star — project's 3-bar reversal flag

The project's **3-bar
reversal** flag is a loose version of this. The bullish version is a close
down, then a close back up through the first bar's open. The bearish version
is the mirror.

## §7 How candles are used here

**In this project candles are commentary, not signals.** The screener and
`inspect` print them so that, when you review a candidate, you can see at a
glance how the last bars behaved at the levels that matter. The summary names
the nearby level explicitly: the 20-day average (SMA20), the 50-day average
(SMA50) or the pivot. The strategies enter on price levels and chart
structure — the price resuming its move through resistance, or breaking out
through a pivot. They never "buy because yesterday was a hammer".

Where they are useful in a swing-trading workflow like this one:

1. ... A
   shooting-star close back under the pivot on the same volume is the first
   sign of a failed breakout. (The `minervini` strategy's exit rules treat a
   close back below the pivot as exactly that.)
3. **Reading a pullback.** In a setup like the `trend_pullback` strategy's
   (buying a dip in an uptrend), an orderly pullback looks like small-range
   candles (inside bars, NR7, dojis) with lower wicks near the rising 50-day
   average.

## Further reading

- The pattern thresholds actually used here:
  `scripts/swing_screener/core/patterns.py`.
