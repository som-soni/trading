# Supply and demand — zones, and how this app uses them

Learning material: what supply and demand actually mean on a chart, how to
find demand and supply zones, when a level changes sides, and — the part that
matters here — how the same ideas already drive this project's strategies.
It is a companion to [learn-bases.md](learn-bases.md) (a base *is* a demand
zone being built) and [learn-chart-patterns.md](learn-chart-patterns.md).

**Where this shows up in the app.** The app calculates overhead supply — the
old price levels above the current price where sellers may be waiting —
rather than leaving it to the eye. In the code,
`scripts/swing_screener/core/context.py` builds a list of these levels
(`overhead_levels`) from the swing highs above the price. Every trade plan
records the nearest one above the entry price
(`nearest_overhead_above_entry`). The strategies use both: they cap targets
just below supply, and they refuse entries directly beneath it. The drawn
examples below are in the pattern catalogue under **Supply & demand**.

---

## 1. How prices move, in one paragraph

Price does not move because of opinions. It moves because, at the current
price, one side runs out of people to trade with. In a rally, buyers keep
paying the sellers' asking price until no one is left offering stock cheaply.
The rally stops where enough sellers appear to fill all the buy orders.
Every level on a chart says the same thing: *at this price, last time, one
side took everything the other side offered.* Support is where all the
selling was bought. Resistance is where all the buying was met by sellers.
A zone is the more honest way to draw this, because that happens across a
band of prices, not at one exact price.

Two kinds of trader behaviour keep old levels relevant:

- **Trapped positions.** Someone who bought near the top before a fall is
  sitting on a loss. They are waiting to "get out at breakeven", so their
  selling waits at the old level. Someone who sold near the bottom before a
  rise regrets it and waits to buy back.
- **Anchoring.** Even traders with no position see the same prior high,
  prior low and round number, and place orders around them. The level works
  partly because everyone expects it to.

## 2. Demand zones — where buyers are waiting

```pattern
demand-zone
```

A demand zone is the **starting point of a strong move up**. It is the pause
where a decline stopped and big buyers bought everything that was for sale.
The rally that followed shows that they still wanted more shares than they
got. You identify a zone by the way the price *left* it, not by the pause
itself:

1. **Find the move away first** — a fast, large rally (wide green bars,
   rising volume). If the price only drifted away, the big buyers probably
   got all the shares they wanted, and there is no reason to expect more
   buyers waiting there.
2. **Mark the base the move started from** — from the pause's low to its
   high. This is the last small consolidation before the move. Zone traders
   call it a *drop-base-rally* when a decline came before it, and a
   *rally-base-rally* inside an uptrend. Short and tight is better than long
   and loose: when the selling is soaked up quickly, the buyer is bigger than
   the seller.
3. **Judge freshness.** Each time the price comes back to the zone, some of
   the waiting buy orders get filled and used up. The first retest (the
   first return to the zone) is the trade; the third is a coin flip. A zone
   the price has already broken through is gone — do not keep buying more
   as it falls.
4. **Judge location.** The zone should sit inside a chart you would want to
   own anyway — a higher low in an uptrend, a base inside a Stage 2 advance.
   The same shape at the bottom of a collapsing downtrend is trying to catch
   a falling knife.

**Trading the retest:** wait for evidence *inside* the zone — a hammer, a
bullish engulfing bar, a tight shelf
([learn-candlestick-patterns.md](learn-candlestick-patterns.md)). Enter on
that. Put the stop just under the zone: if the demand is real, the price
should not trade through it. Put the target just below the next supply
above. The appeal is the reward compared with the risk: the stop is only a
zone's width away, while the target is a whole swing's height away.

## 3. Supply zones — where sellers are waiting

```pattern
supply-zone
```

This is the mirror image: the **starting point of a strong move down**. It is
a pause near a high where sellers met all the buying in the rally. The fall
that followed proves it. Everyone who bought during that pause is now
trapped at a loss, and their selling at breakeven waits above the price. The
same four tests apply: a strong move away, little time spent in the zone, a
fresh zone, and a location in a downtrend or under a failed high.

This is what William O'Neil calls **overhead supply**. It is the reason his
rules prefer stocks near 52-week highs: a stock at new highs has *no one
trapped above it* — no sellers waiting to get back what they paid. Each base
left behind and each old swing high on the way up is a level where sellers
may be waiting. A rally that approaches one on fading volume is likely to
meet selling.

What uses up a supply zone is a push **through** it on rising volume. The
trapped sellers have sold. Short sellers are forced to buy back their
shares. The level has done its job, and it often changes sides:

## 4. Role reversal — levels change sides

```pattern
role-reversal
```

This is called the polarity principle: **broken resistance becomes support;
broken support becomes resistance.** Three groups change behaviour at once:

- buyers from the breakout buy more to defend their entry price;
- short sellers who sold at the old level buy back on dips;
- the sellers who created the level have no stock left to sell.

In practice:

- A shallow, quiet pullback to a broken pivot that holds is the **retest
  entry** — a second chance at a breakout, usually with a tighter stop.
- A close back *below* the level the price just climbed above is the failure
  signal. A breakout that cannot hold its pivot ran into supply after all.
  The `minervini` strategy's exit for a failed breakout follows exactly this
  rule.

## 5. Scoring a zone — a checklist

| Test | Strong zone | Weak zone |
|---|---|---|
| Departure (how the price left) | Fast, large, volume rises | Drifted away quietly |
| Time at the level | A few bars (the selling was bought quickly) | A long, slow grind (a range, not a zone) |
| Freshness | Not revisited since it formed | Hit two or three times already |
| Trend context | With the larger trend | Against it |
| Overlap with other levels | Overlaps a prior swing, a rising 50-day, a base top | Stands alone |
| Cleanliness | One clear pause | Messy, overlapping bars — no single starting point |

## 6. How this helps the strategies here

The strategies in this project do not draw boxes. But they trade the same
ideas under different names, and knowing the zone vocabulary makes their
rules easier to follow:

- **A base is a demand zone being built.** In the sideways stretch after an
  advance ([learn-bases.md](learn-bases.md)), buyers are taking the shares
  that profit-takers sell. The pivot is the price at which the last of those
  sellers is gone. The breakout works *because* the sellers above it were
  used up inside the base. That is why wide-and-loose bases — where the
  selling was never fully taken up — fail more often.
- **Entries avoid buying into supply.** The `trend_pullback` strategy
  refuses to place an entry within 3% directly below an overhead level. A
  buy-stop order just under a level full of trapped sellers is likely to
  lose money. Its TC-01 pullback entry is a retest of demand with a trigger:
  the price must *resume* its rise through H (the swing high the pullback
  started from), not merely touch support.
- **Targets stop just below supply, not inside it.** The `chart_pattern`
  strategy caps its measured-move target at the nearest overhead swing level
  that is at least 1 ATR above the entry. (Every trade plan records this
  level as `nearest_overhead_above_entry`.) A target that expects the price
  to cut straight through a fresh level of sellers usually never gets hit.
- **Stops belong under demand.** Handle lows, tight-area lows, prior swing
  lows — every strategy puts its stop "just below the nearest demand". That
  is where the trade's premise (buyers are here) is proven wrong.
- **Strength means little supply above.** The Stage 2 screen's "within 25%
  of the 52-week high" and the near-highs screen's 15% are really filters for
  overhead supply. The fewer trapped holders above the price, the less
  selling a rally has to get through.

## 7. Evidence and caveats — read before drawing boxes everywhere

- Retail "supply and demand zone" trading is **a way of looking at charts
  by judgement, not a measured edge**. The academic research supports the
  weaker claims: prices do pause and react more often than chance at prior
  highs and lows and at round numbers. But no public study shows that boxes
  drawn by the usual rules beat the market after costs. Treat zones as a
  *reading aid*, like the pattern names.
- Their real value here is **deciding where risk goes**. Zones tell you
  where a stop is just slightly off and where the whole idea is wrong, and
  when a target is asking too much. That is also exactly how this project's
  backtests use levels. Those backtests' results (see each strategy's page)
  are the honest measure — not how neat the story sounds.
- Zones wear themselves out. The better known a level, the more traders
  place orders just ahead of it to get in first, which spreads the zone
  wider. Expect the price to react *around* zones, not at an exact price.
- Beware hindsight: on any chart, *some* box lines up with every turn. Score
  zones in advance with §5, write the level down before the retest, and then
  see whether the chart proves you right.

## 8. Practicing in the app

1. Draw the zones. The chart's **Rectangle tool** (Alt+Shift+R) is made for
   this, and drawings are now saved on the server for each symbol. Mark the
   base that a strong move started from, then check back after the retest.
2. See the supply levels the app calculates:
   `python3 -m swing_screener.screening.inspect --market
   us --symbol XYZ --strategy trend_pullback` prints the stock's overhead
   levels and the trade plan built around them.
3. The drawn examples live in **Library → Learn → Chart patterns → Supply &
   demand** (demand zone, supply zone, role reversal).

## Further reading

- Richard Wyckoff's diagrams of accumulation and distribution — the 1930s
  original of every zone diagram. They cover how selling gets soaked up,
  "springs" (a quick dip below support that reverses) and tests.
- William O'Neil, *How to Make Money in Stocks* — overhead supply, and why
  stocks at new highs do better than bargains.
- Edwards & Magee, *Technical Analysis of Stock Trends* — the chapters on
  support, resistance and polarity; the oldest systematic statement of §4.
