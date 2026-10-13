# Supply and demand — zones, and how this app uses them

Learning material: what supply and demand actually mean on a chart, how to
identify demand and supply zones, when a level changes sides, and — the part
that matters here — how the same ideas already drive this project's
strategies. Companion to [learn-bases.md](learn-bases.md) (a base *is* a
demand zone being built) and [learn-chart-patterns.md](learn-chart-patterns.md).

**Where this shows up in the app.** Overhead supply is computed, not
eyeballed: `scripts/swing_screener/core/context.py` builds `overhead_levels`
from the swing highs above price, every trade plan records
`nearest_overhead_above_entry`, and the strategies use both (targets capped in
front of supply, entries refused directly beneath it). The drawn examples
below are in the pattern catalogue under **Supply & demand**.

---

## 1. The auction, in one paragraph

Price does not move because of opinions; it moves because at the current
price one side runs out of counterparties. A rally is buyers lifting every
offer until no more stock is offered cheap; it stops where enough sellers
appear to absorb them. Every level on a chart is shorthand for the same
sentence: *at this price, last time, one side absorbed the other.* Support is
where selling was absorbed; resistance is where buying was absorbed. Zones
are just the honest version of that — absorption happens across a band of
prices, not at one tick.

Two behavioural engines keep old levels relevant:

- **Trapped positions.** Whoever bought the top of a markdown is under water
  and waiting to "get out at breakeven" — their selling sits at the old level.
  Whoever sold the bottom of a markup regrets it and waits to rebuy.
- **Anchoring.** Even uninvolved traders see the same prior high, prior low
  and round number, and place orders around them. The level works partly
  because everyone expects it to.

## 2. Demand zones — where buyers are waiting

```pattern
demand-zone
```

A demand zone is the **origin of a strong move up**: the pause where a
decline stopped, big buyers absorbed everything offered, and the departure
rally proved they were left unfilled. Identify one by the *leaving*, not the
pause itself:

1. **Find the departure first** — a fast, large rally (wide green bars,
   expanding volume). Weak departures mean the buying was fully filled;
   there is no reason to expect more waiting there.
2. **Mark the base it left from** — the pause's low to its high (the last
   small consolidation before the move; in zone-trading jargon a
   *drop-base-rally* when a decline preceded it, a *rally-base-rally* inside
   an uptrend). Short and tight beats long and loose: quick absorption is the
   signature of a buyer bigger than the seller.
3. **Judge freshness.** Resting demand is consumed by every revisit. The
   first retest is the trade; the third is a coin flip. A zone that already
   broke is gone — do not average into it.
4. **Judge location.** The zone should sit inside a structure you would own
   anyway — an uptrend's higher low, a base inside a Stage 2 advance. The
   same shape at the bottom of a collapsing downtrend is knife-catching.

**Trading the retest:** wait for evidence *inside* the zone — a hammer, a
bullish engulfing bar, a tight shelf ([learn-candlestick-patterns.md](learn-candlestick-patterns.md))
— enter on that, stop just under the zone (if the demand is real, price
should not trade through it), target in front of the next supply above.
Reward:risk is the whole appeal: the stop is a zone's width, the target a
swing's height.

## 3. Supply zones — where sellers are waiting

```pattern
supply-zone
```

The mirror: the **origin of a strong move down** — a pause near a high where
sellers absorbed the rally, proven by the markdown that followed. Everyone
who bought that pause is trapped, and their breakeven selling waits
overhead. The same four tests apply (strong departure, little time, fresh,
in a downtrend or under a failed high).

This is O'Neil's **overhead supply**, and it is the reason his rules prefer
stocks near 52-week highs: a stock at new highs has *no one trapped above it*
— no anchored sellers waiting to break even. Each left-behind base and old
swing high on the way up is a shelf of potential supply; a rally approaching
one on fading volume is asking to be sold.

What consumes a supply zone: a push **through** it on expanding volume. The
trapped sellers are out, shorts are squeezed — the level's job is done, and
it often flips sides:

## 4. Role reversal — levels change sides

```pattern
role-reversal
```

The polarity principle: **broken resistance becomes support; broken support
becomes resistance.** Three groups flip at once — breakout buyers defend
their entries, shorts from the old level cover into dips, and the sellers
who made the level have no stock left. Practically:

- A shallow, quiet pullback to a broken pivot that holds is the **retest
  entry** — the second chance at a breakout, usually with a tighter stop.
- A close back *below* the reclaimed level is the failure signal. Breakouts
  that cannot hold their pivot found supply after all; the minervini spec's
  failed-breakout exit encodes exactly this.

## 5. Scoring a zone — a checklist

| Test | Strong zone | Weak zone |
|---|---|---|
| Departure | Fast, large, volume expands | Drifted away quietly |
| Time at the level | A few bars (quick absorption) | A long grind (a range, not a zone) |
| Freshness | Untested since it formed | Hit two or three times already |
| Trend context | With the larger trend | Against it |
| Confluence | Overlaps a prior swing, a rising 50-day, a base top | Floating alone |
| Cleanliness | One clear pause | Overlapping chop — no single origin |

## 6. How this helps the strategies here

The strategies in this project do not draw boxes, but they trade the same
mechanics under different names — knowing the zone language makes their rules
legible:

- **A base is a demand zone under construction.** The sideways work after an
  advance ([learn-bases.md](learn-bases.md)) is supply from profit-takers
  being absorbed; the pivot is the price at which the last of it is gone.
  The breakout works *because* the supply above it was consumed inside the
  base — which is why wide-and-loose bases (supply never truly absorbed)
  fail more.
- **Entries avoid buying into supply.** `trend_pullback` refuses to place an
  entry directly beneath an overhead level within 3% — a buy-stop under a
  shelf of trapped sellers is a donation. Its TC-01 pullback entry is a
  demand retest with a trigger: price must *resume* through H, not merely
  touch support.
- **Targets stop in front of supply, not inside it.** The `chart_pattern`
  strategy caps its measured-move target at the nearest overhead swing level
  at least 1 ATR above entry (`nearest_overhead_above_entry` on every trade
  plan): expecting price to slice through a fresh supply shelf is how paper
  targets stay paper.
- **Stops belong under demand.** Handle lows, tight-area lows, prior swing
  lows — every strategy's stop is "just below the nearest demand", because
  that is where the trade's premise (buyers are here) is proven wrong.
- **Strength is the absence of supply.** The Stage 2 screen's "within 25% of
  the 52-week high" and the near-highs screen's 15% are overhead-supply
  filters in disguise: the less trapped stock above you, the less selling a
  rally must chew through.

## 7. Evidence and caveats — read before drawing boxes everywhere

- Retail "supply and demand zone" trading is a **discretionary framing, not
  a measured edge**. The academic record supports the weaker claims — prices
  do pause and react more than chance at prior extremes and round numbers —
  but no public study shows that boxes drawn by the usual rules produce
  excess returns after costs. Treat zones as a *reading aid*, like the
  pattern names.
- The framing's real value here is **risk placement**: zones say where a stop
  is wrong by a little versus where the idea is wrong, and where a target is
  asking too much. That is also exactly how this project's backtests use
  levels — and those backtests' results (see each strategy's page) are the
  honest measure, not the elegance of the story.
- Zones are self-eroding: the better known a level, the more orders front-run
  it, smearing the zone wider. Expect reactions *around* zones, not at ticks.
- Beware hindsight: on any chart, *some* box catches every turn. Score zones
  prospectively with §5, write the level down before the retest, and let the
  chart grade you.

## 8. Practicing in the app

1. Draw the zones: the chart's **Rectangle tool** (Alt+Shift+R) is made for
   this, and drawings now persist server-side per symbol — mark a departure's
   base, then check back after the retest.
2. See computed supply: `python3 -m swing_screener.screening.inspect --market
   us --symbol XYZ --strategy trend_pullback` prints the stock's overhead
   levels and the plan built around them.
3. The drawn examples live in **Library → Learn → Chart patterns → Supply &
   demand** (demand zone, supply zone, role reversal).

## Further reading

- Richard Wyckoff's accumulation/distribution schematics — the 1930s
  original of every zone diagram; absorption, springs and tests.
- William O'Neil, *How to Make Money in Stocks* — overhead supply and why
  new highs beat bargains.
- Edwards & Magee, *Technical Analysis of Stock Trends* — the support/
  resistance and polarity chapters; the oldest systematic statement of §4.
