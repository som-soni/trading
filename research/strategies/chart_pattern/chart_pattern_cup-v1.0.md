# Cup-and-handle only

`chart_pattern_cup` · family **chart_pattern** · **v1.0** · fingerprint `422fb10b`

> Indecisive: US 2020-2026, 300-symbol sample, bracket exit, -0.24% CAGR and -0.019R per trade over 32 trades (t = -0.04). That is indistinguishable from zero and not significantly better than the full pattern set.

The chart-pattern strategy restricted to CUP and CUPNH — the only two detectors that are rare in random data.

*A variant of `chart_pattern` (Classical chart-pattern breakout).*

## Thesis

If classical chart patterns carry information, the one that a random walk almost never produces should carry more of it than the ones a random walk produces constantly.

## How it works

1. **Screen** for liquid stocks above their SMA200 and within 20% of the 52-week high, with enough history for a long base.
2. **Detect** all seven patterns geometrically (see `core/chart_patterns.py`); each returns a pivot, the structural low a stop belongs under, and the measured move it projects. Pivots are computed from bars BEFORE the current one, so a breakout bar can never define the level it breaks.
3. **Setups** fire per pattern once price is within 8% below the pivot and the pattern scores at least 0.45; several patterns may match one chart and all are reported.
4. **Gates P1-P7** require the SMA200 intact and not falling, price within 15% of the 52-week high, sane volatility, no earnings inside 10 days, a pattern scoring at least 0.45, and price no more than 4% above the pivot.
5. **Entry** 0.1% above the pivot (rounded up to the tick), or the market price if price has already cleared it. **Stop** under the pattern's own structural low (handle low, second bottom, box low, flag low), never wider than 2 ATR and never tighter than 0.6 ATR or 1.5% of price. **Target** the measured move, capped at overhead supply more than 1 ATR above the entry — nearer levels are the base's own resistance zone, not new supply. A plan projecting under 2R, or with a stop more than 8% below entry, is downgraded to WATCH rather than rejected. (The stop floor is applied after the 2 ATR cap, so on a very quiet stock the stop can end up wider than 2 ATR.)
6. **Confirmation**: the trigger is a close through the pivot on 1.4x average volume; without the volume it is still a setup, capped at WATCH.

## Hard gates (failing any one means AVOID)

| code | meaning |
|---|---|
| `P1` | The close must be above the 200-day SMA. Every pattern here is a continuation base; the same shape under a broken long-term trend is treated as a bear-market rally. |
| `P2` | The 200-day SMA must not be falling, i.e. not more than 0.5% below its value 20 bars ago. Flat or rising both pass. |
| `P3` | The close must be at least 85% of the 52-week high (within 15% of it). Fails if there is not enough history to compute the high. |
| `P4` | ATR14 as a percentage of price must be 10% or less. A missing ATR% passes. |
| `P5` | No earnings report within the next 10 trading days. Passes when no earnings date is known, which is always the case in the backtest (there is no point-in-time earnings calendar). |
| `P6` | At least one of this strategy's allowed patterns must be detected with a quality score of at least 0.45 AND a close at or above pivot x (1 - 0.08). The failure note says whether nothing was found, the best match scored too low, or its pivot is too far overhead. |
| `P7` | The close must not be more than pivot x (1 + 0.04) — a breakout already further past its pivot than that is a chase, not an entry. Only checked when P6 found an actionable pattern. |

## Watch flags (these cap confidence)

| code | meaning |
|---|---|
| `XP1` | Raised when the close is already above the traded pattern's pivot but volume is below 1.4x its 50-day average — the classic unconfirmed breakout. Caps the decision at WATCH and cuts the ranking score by 1.0. |
| `XP2` | Raised when the close is more than 2.5 ATR above the 20-day SMA (extended from the mean). Caps the decision at TRADE ON TRIGGER and cuts the ranking score by 0.5. |
| `XP3` | Raised when RSI14 is above 80 (overbought). Caps the decision at TRADE ON TRIGGER. |
| `XP4` | Raised when the traded pattern is more than 35% deep. Not disqualifying, but a deep base is a damaged one: caps the decision at TRADE ON TRIGGER and cuts the ranking score by 0.25. |
| `XP5` | Raised when a live topping structure (double top or head and shoulders top) is on the same chart — one whose last peak is under 90 bars old, has not been exceeded by more than 1%, and has either broken its neckline (confirmed) or rolled over below both 95% of the peak and the peak-to-neckline midpoint (forming). A confirmed top caps the decision at WATCH; a forming one at TRADE ON TRIGGER. It never creates or removes a setup. |

## Setups

| code | meaning |
|---|---|
| `CUP` | Cup-and-handle. The left rim is the highest confirmed swing high of the last 250 bars; the cup bottom sits 12-50% below it, the right rim recovers to 90-105% of the left, the cup spans 25-250 bars with neither side shorter than 20% of it, and enough bars sit in its lower third to make it rounded rather than a V. The handle is the last 5-20 bars: 2-15% deep and no deeper than a third of the cup, its low in the cup's upper half, falling no faster than 1.2% per bar, on average volume below the cup's. Pivot: right rim. Stop: handle low. Move: cup depth. |
| `CUPNH` | Cup without a handle. The same cup body as CUP, but price is still pinned to the rim: fewer than 5 bars since the right rim or less than a 2% pullback from it, never more than 4% off it, a close within 7% of it, and a right rim within 3% of the left. Pivot: right rim. Stop: the lowest low since about 5 bars before the rim. Move: cup depth. |

## Entry

- A pattern is a setup once the close is at or above pivot x (1 - 0.08) and its quality score is at least 0.45. When several qualify, the highest-scoring one is traded. Pivots come only from bars before the current one.
- The trigger is a daily close above that pivot on volume of at least 1.4x the 50-day average. That close, with gates passed and no watch-flag cap, is TRADE HIGH CONFIDENCE. A setup that has not triggered yet is TRADE ON TRIGGER.
- Entry is the higher of pivot x 1.001 and the current close, rounded up to the tick. Once price has cleared the pivot, you pay the market price, not the pivot.
- Stop is 0.1 ATR under the pattern's structural low, but no more than 2 ATR below entry. It is then widened if needed so it sits at least 0.6 ATR and at least 1.5% below entry. It is rounded down to the tick.
- Target is entry plus the pattern's measured move, with no floor. It is capped at the nearest overhead swing-high level that is at least 1 ATR above entry. Levels nearer than that are the base's own resistance zone and are ignored.
- A plan whose reward:risk is under 2R (after the overhead cap), whose stop is more than 8% below entry, or whose size is too large for the account is downgraded to WATCH. It is not padded up to look acceptable.

## Exit

- A fixed bracket. The stop and target are set at entry and never move. The strategy has no trailing stop, time stop or discretionary exit.
- In the backtest, a TRADE HIGH CONFIDENCE signal becomes a resting buy-stop at the entry price. It fills on a later bar whose high reaches it, at the open if that bar gaps above. It is cancelled if the low reaches the stop first, if the open gaps past the target, or if it is still unfilled after 10 business days.
- A position exits on whichever of stop or target a later bar touches first. When both are touched on the same bar, the stop is assumed to fill. Gaps through either level fill at the open. Positions still open at the end are marked at the last close.
- Backtest only: the earnings gate (P5) and the market-regime downgrade are not applied, and only TRADE HIGH CONFIDENCE signals are taken.

## Parameters

| parameter | value | meaning |
|---|---|---|
| Near-pivot zone | `None` | Fraction below the pivot within which a detected pattern counts as a setup (0.08). Further out, it is reported but not actionable. |
| Max chase | `None` | Fraction above the pivot beyond which gate P7 fails (0.04). |
| Breakout volume | `None` | Multiple of 50-day average volume that a close through the pivot needs to count as the trigger (1.4x). Below it, XP1 fires. |
| Minimum price | `None` | Screen: closes below this price are excluded. |
| Minimum liquidity | `None` | Screen: the 20-day average of close x volume must reach this. |
| Tick size | `None` | Entry is rounded up and the stop rounded down to this increment. |
| Risk per trade | `None` | Fraction of equity risked between entry and stop, which sets position size. |
| Max open positions | `None` | Portfolio backtest slot limit. Triggered orders beyond it keep resting until they expire. |

## Known caveats

- **RUN, AND THE RESULT IS INDECISIVE.** US, 2020-01-02 to 2026-10-02, 300-symbol sample, identical to `chart_pattern`'s run: -0.24% CAGR (vs -4.08%), -13.0% max drawdown (vs -42.2%), 32 trades at a 25.0% win rate, -0.019R per trade (vs -0.213R), profit factor 0.94. Every headline favours the selective detector AND NONE OF IT IS SIGNIFICANT: the difference is +0.194R with a Welch t of 0.42, bootstrap 95% CI [-0.67, +1.12], P(cup better) = 0.66. Its own expectancy is -0.019R at t = -0.04 — indistinguishable from zero in either direction. Do not read the CAGR gap as evidence.
- **32 trades in 6.75 years is the price of selectivity.** CUP fires on ~0.2% of names, so the more selective the detector the longer it takes to learn whether it works. Settling this needs roughly 10x the sample: the full universe over the full 13.75-year window, not a 300-symbol draw.
- Of those 32 trades, 27 were CUPNH (-0.25R) and 5 were CUP proper (+1.23R). Five trades is not a finding, and the temptation to read one into it is exactly what the t-statistics above exist to resist.
- **This exists to be falsified.** It is the same code as `chart_pattern` with five of seven detectors switched off; compare the two over an identical window and sample, and read the difference, not either number alone.
- CUP fires on ~0.2% of liquid names, so expect FEW trades and wide error bars. A difference of a point or two of CAGR over ~20 trades says nothing at all.
- Every caveat on `chart_pattern` applies here unchanged.

## Commands

```bash
python3 -m swing_screener.screening.pipeline --market us --strategy chart_pattern_cup
python3 -m swing_screener.screening.inspect --market us --symbol AAPL --strategy chart_pattern_cup
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --strategy chart_pattern_cup
```

---

*Generated from `scripts/swing_screener/strategies/chart_pattern.py`. Do not edit by hand — re-run `python3 -m swing_screener.strategies.docs --write`.*
