# App notes moved out of learn-supply-demand

## Title and intro

Title was: "Supply and demand — zones, and how this app uses them".

Learning material: what supply and demand actually mean on a chart, how to
find demand and supply zones, when a level changes sides, and — the part that
matters here — how the same ideas already drive this project's strategies.

**Where this shows up in the app.** The app calculates overhead supply — the
old price levels above the current price where sellers may be waiting —
rather than leaving it to the eye. In the code,
`scripts/swing_screener/core/context.py` builds a list of these levels
(`overhead_levels`) from the swing highs above the price. Every trade plan
records the nearest one above the entry price
(`nearest_overhead_above_entry`). The strategies use both: they cap targets
just below supply, and they refuse entries directly beneath it. The drawn
examples below are in the pattern catalogue under **Supply & demand**.

## §4 Role reversal

The `minervini` strategy's exit for a failed breakout follows exactly this
rule.

## §6 How this helps the strategies here

The strategies in this project do not draw boxes. But they trade the same
ideas under different names, and knowing the zone vocabulary makes their
rules easier to follow:

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
- **Stops belong under demand.** ... every strategy puts its stop "just below the nearest demand".
- **Strength means little supply above.** The Stage 2 screen's "within 25%
  of the 52-week high" and the near-highs screen's 15% are really filters for
  overhead supply.

(The general ideas — avoid entries just below an overhead level, e.g. within 3%; require the price to resume through
the swing high rather than merely touch support; cap targets at the nearest overhead level at least 1 ATR above entry;
stops under demand; near-high filters as overhead-supply filters — are kept in the guide in general words.)

## §7 Evidence

That is also exactly how this project's
  backtests use levels. Those backtests' results (see each strategy's page)
  are the honest measure — not how neat the story sounds.

## §8 Practicing in the app

1. Draw the zones. The chart's **Rectangle tool** (Alt+Shift+R) is made for
   this, and drawings are now saved on the server for each symbol. Mark the
   base that a strong move started from, then check back after the retest.
2. See the supply levels the app calculates:
   `python3 -m swing_screener.screening.inspect --market
   us --symbol XYZ --strategy trend_pullback` prints the stock's overhead
   levels and the trade plan built around them.
3. The drawn examples live in **Library → Learn → Chart patterns → Supply &
   demand** (demand zone, supply zone, role reversal).
