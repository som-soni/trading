# Candlestick patterns — a field guide

Learning material: how to read daily and weekly candles, the patterns worth
knowing, and how they are used in this project. Companion to
[learn-chart-patterns.md](learn-chart-patterns.md) — candles are the
single-bar vocabulary, chart patterns are the multi-week sentences.

**Where this shows up in the app.** The screener writes a one-line candle
summary for every candidate (the `candles` column, built by
`scripts/swing_screener/core/patterns.py`), and
`python3 -m swing_screener.screening.inspect --symbol XYZ` prints the last
five bars' stats with their detected patterns. The chart page draws raw
candles. Nothing in any strategy *trades* a candlestick pattern — see
"How candles are used here" at the end for why.

---

## 1. Anatomy of a candle

A candle compresses one session's auction into four prices:

```pattern
anatomy
```

Three questions tell you most of what one candle can say:

1. **How big is the body relative to the range?** A large body means one side
   controlled the session; a tiny body means a stand-off.
2. **Where in the range did it close?** A close in the top third means buyers
   had the last word; the bottom third, sellers.
3. **Which wick is long?** A long wick marks prices the market visited and
   rejected — a long lower wick means dip-buyers absorbed the selling.

The quantitative versions used by this project's commentary
(`core/patterns.py`):

| Measure | Definition | Thresholds used |
|---|---|---|
| Body % | \|close − open\| / (high − low) | doji when ≤ 10% |
| Close location | (close − low) / (high − low) | top ≥ 0.66, bottom ≤ 0.34 |
| Wick ratio | wick length / body length | "long" when ≥ 2× the body |
| Gap % | open vs the prior close | a gap when beyond ±0.3% |
| Volume ratio | volume / 50-day average volume | notable above 1.2 or below 0.8 |

**Volume is half the message.** A reversal candle on 2× average volume is a
statement; the same shape on 0.6× volume is noise. Every pattern below should
be read with its volume ratio.

---

## 2. Context first, pattern second

A candlestick pattern is not a signal by itself. The same hammer means:

- at the 50-day average after a 3-week pullback in an uptrend → *potential
  resumption*, worth attention;
- mid-air, in the middle of a range → nothing;
- after a 40% collapse in a downtrend → usually just the first bounce that
  gets sold again.

Rules of thumb that survive contact with real charts:

1. **Only read reversal candles at a level** — a prior low, a moving average
   the stock respects, a pattern pivot, a gap edge. The candle marks *who won
   the fight at the level*; without a level there is no fight to win.
2. **Trend beats candle.** A bearish candle in a strong uptrend is usually a
   pause. Do not short an uptrend on a shooting star; at most, tighten a stop.
3. **Bigger timeframe, bigger meaning.** A weekly hammer at support outranks
   five daily candles. The screener prints a weekly candle note for this
   reason (`weekly_candle_note`).
4. **Wait for the confirming close** when the candle is the whole case. A
   hammer is only "confirmed" by the next bar closing above its body.

---

## 3. Single-candle patterns

### Doji — stand-off

Body ≤ ~10% of the range: open and close nearly equal.

```pattern
doji
```

After a sustained advance, a doji on high volume says the buyers who drove
the move met equal selling for the first time. In a quiet range it says
nothing at all.

Variants: **gravestone** (long upper wick, close near the low — a failed
rally, bearish at highs), **dragonfly** (long lower wick, close near the high
— a rejected sell-off, bullish at support), **spinning top** (small body,
wicks both sides — indecision, slightly weaker message than a doji).

### Hammer — rejected sell-off

Long lower wick (≥ 2× body), close in the top third, appearing **after a
decline or pullback**. Sellers drove price down during the session; buyers
took it all back.

```pattern
hammer
```

Bullish at support. The low of the hammer is the natural stop — if price
trades back below it, the rejection failed.

The identical shape after an *advance* is a **hanging man** — a warning, not
a sell signal, and much weaker evidence than the hammer is.

### Shooting star — rejected rally

Mirror image: long upper wick (≥ 2× body), close in the bottom third, after
an advance. Buyers pushed to new highs intraday and were overwhelmed.
Meaningful at resistance or after a climactic run; a routine candle inside a
base. The **inverted hammer** is the same shape after a decline — mildly
bullish, needs next-bar confirmation.

### Marubozu — total control

A body that is (nearly) the whole range, no wicks. A green marubozu through a
pivot on heavy volume is exactly the breakout bar you want; a red one through
support is distribution. The commentary calls these "plain top-range close" /
"plain bottom-range close" when no other pattern applies.

### NR7 — the quiet before the move

Not a classical candlestick, but in the commentary: the narrowest range of
the last 7 bars. Volatility contracts before it expands; a cluster of
NR7/inside bars near a pivot is the daily-timeframe version of what the VCP
strategies look for. Direction comes from the break, not from the NR7 itself.

---

## 4. Two-candle patterns

### Bullish engulfing

A down candle, then an up candle whose body opens at or below the prior close
and closes at or above the prior open — the second session completely
retraces and reverses the first.

```pattern
bullish-engulfing
```

Strong at support after a pullback, on rising volume. Stop below the
engulfing bar's low.

**Bearish engulfing** is the mirror at highs. Both are among the few candle
patterns with modest statistical support — and both still fail routinely
against the prevailing trend.

### Harami / inside bar

The second bar's range sits entirely inside the first's. The commentary flags
this as **inside bar**: contraction, the market catching its breath. Like the
NR7 it is direction-neutral — trade the break of the inside bar's range, in
the direction of the trend, rather than the bar itself. The **outside bar**
(engulfs the prior range both ways) is expansion; its close location decides
who won.

### Piercing line / dark cloud cover

Weaker cousins of the engulfing pair: the second body retraces more than half
of the first body but does not engulf it. Piercing line (bullish, at lows):
gap down, then a close above the midpoint of the prior red body. Dark cloud
cover (bearish, at highs): gap up, then a close below the midpoint of the
prior green body. Treat as "engulfing-lite" — same logic, less conviction.

### Tweezers

Two consecutive bars with (nearly) equal lows (tweezer bottom) or highs
(tweezer top) — the same level defended twice in a row. Mostly useful as
evidence *for the level*, not as a pattern on its own.

---

## 5. Three-candle patterns

### Morning star / evening star

The classic three-act reversal. Morning star, at a low: a strong red bar
(sellers in control), a small-bodied star that gaps or drifts lower
(exhaustion), then a strong green bar closing well into the first bar's body
(buyers take over).

```pattern
morning-star
```

The evening star is the mirror at highs. The project's **3-bar reversal**
flag is a loose version of this: close down, then a close back up through the
first bar's open (bullish), or the mirror (bearish).

### Three white soldiers / three black crows

Three consecutive full-bodied candles in the same direction, each closing
near its extreme. After a long decline, three white soldiers mark a genuine
character change. *Late* in an advance, three accelerating white soldiers on
expanding volume start to look like a climax — see the climax-top discussion
in [learn-chart-patterns.md](learn-chart-patterns.md).

---

## 6. Quick reference

| Pattern | Bars | Bias | Where it means something | Invalidation |
|---|---|---|---|---|
| Doji | 1 | neutral | after a one-way move | — (a warning, not a trade) |
| Hammer | 1 | bullish | at support after a decline | close below its low |
| Hanging man | 1 | mildly bearish | after an advance | close above its high |
| Shooting star | 1 | bearish | at resistance after an advance | close above its high |
| Inverted hammer | 1 | mildly bullish | after a decline, needs confirmation | close below its low |
| Marubozu | 1 | with its color | through a level, on volume | retrace through the level |
| NR7 / inside bar | 1–2 | neutral (contraction) | near a pivot | — (trade the break) |
| Bullish engulfing | 2 | bullish | at support, rising volume | close below pattern low |
| Bearish engulfing | 2 | bearish | at highs/resistance | close above pattern high |
| Piercing line | 2 | bullish | at lows | close below pattern low |
| Dark cloud cover | 2 | bearish | at highs | close above pattern high |
| Morning star | 3 | bullish | at lows, volume on bar 3 | close below star's low |
| Evening star | 3 | bearish | at highs | close above star's high |
| Three white soldiers | 3 | bullish | after a decline/base | — context-dependent |
| Three black crows | 3 | bearish | after an advance | — context-dependent |

---

## 7. How candles are used here — and the evidence

**In this project candles are commentary, not signals.** The screener and
`inspect` print them so that when you review a candidate you see at a glance
how the last bars behaved at the levels that matter (the summary names the
nearby SMA20/SMA50/pivot explicitly). The strategies' entries are level- and
structure-based — a resumption through resistance, a pivot breakout — never
"buy because yesterday was a hammer".

That is deliberate, and the honest reading of the evidence:

- Academic tests of candlestick rules on daily equity data (e.g. Marshall,
  Young & Rose 2006 on the Dow; Horton 2009; Fock et al. on intraday data)
  find **no reliable stand-alone predictive value** after costs.
- Bulkowski's large pattern catalogs find individual candle patterns barely
  better than a coin flip on their own, improving only when filtered by trend
  and confirmation — i.e. by exactly the context rules in §2.
- Candle shapes depend on session mechanics: a stock that gaps every day
  (earnings, ADRs, thin names) produces "patterns" constantly; a 24-hour
  instrument produces different candles than an exchange session. The same
  price path sampled differently gives different candles — a reason to treat
  them as *description*, not *prediction*.

Where they earn their keep in a swing workflow like this one:

1. **Entry-day quality.** On the day price takes out your trigger, a
   full-bodied close in the top of the range on above-average volume is the
   breakout behaving; a shooting-star close back under the pivot on the same
   volume is the first sign of a failed breakout (the `minervini_spec` exit
   spec treats a close back below the pivot as exactly that).
2. **Stop placement.** Reversal candles give natural invalidation points —
   the hammer's low, the engulfing bar's low — usually tighter and more
   honest than a percentage.
3. **Pullback reading.** In a `trend_pullback`-style setup, contraction
   candles (inside bars, NR7, dojis) with lower wicks near the rising 50-day
   are what an orderly pullback looks like; wide red marubozus on expanding
   volume are what distribution looks like. Same depth of pullback, opposite
   conclusion.

## Further reading

- Steve Nison, *Japanese Candlestick Charting Techniques* — the source text
  that brought candles west; read for vocabulary, not for win rates.
- Thomas Bulkowski, *Encyclopedia of Candlestick Charts* — per-pattern
  statistics; most honest about how weak single patterns are.
- The pattern thresholds actually used here:
  `scripts/swing_screener/core/patterns.py`.
