# Classical chart-pattern breakout

`chart_pattern` · family **chart_pattern** · **v1.0** · fingerprint `31bf07b0`

> Backtested and lost money: US 2020-2026, 300-symbol sample, bracket exit, -4.08% CAGR vs the benchmark's +13.63%, -0.213R per trade over 146 trades. No demonstrated edge. Measured before the 2026-10 cost fix (exit slippage was charged twice); re-measured runs moved by −0.8 to +0.9 points of CAGR (the extra cash changes which later signals are taken), so re-run before relying on it.

Breakouts from a named base — cup-and-handle, double bottom, flat base, bull flag, ascending triangle, or VCP.

## Thesis

A base with a recognised shape — rounded cup, matched double bottom, tightening contractions — has absorbed supply in a way a merely narrow range has not, so its breakout meets less resistance.

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
| `DBOT` | Double bottom (W). Two confirmed swing lows 15-160 bars apart within 5% of each other, with a rally of at least 8% between them, preceded by a high at least 15% above the lows in the 80 bars before the first. The second low must be at most 80 bars old and have held (nothing since more than 2% below it), and nothing since may have cleared the middle peak by more than 3%. An undercutting second low scores higher. Pivot: highest high since the second low, at least the middle peak. Stop: second low. Move: middle peak minus the lower low. |
| `FLAT` | Flat base / Darvas box. A box of 25, 35, 45 or 65 bars ending yesterday whose high-to-low range is at most 15% deep, topping an advance of at least 20% from the lowest low of the 60 bars before it, with the close in the upper 60% of the box. Pivot: box high. Stop: box low. Move: the PRIOR ADVANCE (box high minus that pre-box low), not the box height. |
| `FLAG` | Bull flag. The pole high is the highest high of the last 45 bars, 4-35 bars ago; the pole rises at least 20% from the lowest low of the 40 bars before it; the flag since then has retraced no more than 40% of the pole. A gain of 80%+ with a retrace of 25% or less is labelled a high tight flag and scores higher. Pivot: pole high. Stop: flag low. Move: pole height. |
| `ATRI` | Ascending triangle. Within the last 120 bars, the three most recent confirmed swing highs all lie within 3% of the highest, the structure spans at least 25 bars, and the swing lows since it began rise (last more than 1% above first). The triangle is at least 6% tall at its left edge, the lows have closed 40-92% of that gap, and no high since the last touch is more than 3% above resistance. Pivot: resistance. Stop: last rising low. Move: triangle height. |
| `VCP` | Volatility contraction pattern. Within the last 140 bars, alternating confirmed swing highs and lows form pullbacks; the most recent run in which each pullback is at most 0.8x as deep as the one before must hold at least 2 contractions, the last no deeper than 12%. Pivot: the final contraction's high, or any higher high since. Stop: the final contraction's low. Move: first contraction's high minus the base low. |

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

- **RE-MEASURED 2026-10-09: -5.60% CAGR, 139 trades, -0.309R per trade (t = -1.90), profit factor 0.62.** The earlier -4.08% / -0.213R figures below came from a 4 October run; the data has since extended and the `near_highs` screen was formalised, so the baseline itself moved. Quote one vintage or the other, not a mix.
- **A DAY OF DETECTOR REFINEMENT MOVED EXPECTANCY BY 0.001R.** Tightening the handle, anchoring the cup to the prior peak, adding CUPNH and the XP5 topping veto took per-trade expectancy from -0.214R to -0.213R over the same window and sample (CAGR -3.26% to -4.08%, 146 trades). Every change was individually defensible and a human chart review motivated most of them; together they bought nothing measurable. Assume the same of the next refinement.
- **BACKTESTED AND IT LOST MONEY.** US, 2020-01-02 to 2026-10-02, a 300-symbol sample, bracket exit: -3.26% CAGR against the benchmark's +13.63% (excess -16.90%), -38.98% max drawdown, 140 trades at a 19.0% win rate, -0.214R per trade, profit factor 0.75. Per pattern, total R was FLAT -11.9 (57 trades), DBOT -7.5 (13), ATRI -4.7 (34), CUP -3.0 (3), FLAG +0.1 (26), VCP +2.4 (7) — nothing with a meaningful sample made money. 111 trades stopped out against 26 that reached a target.
- **Three quarters of random walks contain one of these patterns.** Measured over 150 seeded walks: VCP 44%, FLAT 31%, DBOT 31%, FLAG 11%, ATRI 9%, CUP 0.7%; 75% match something. Against 519 liquid US names the same day: VCP 27%, DBOT 27%, FLAT 11%, CUP 0.2%, 55% overall. Three of the seven detect noise about as readily as they detect the market, and they are exactly the ones the backtest traded most (FLAT 57 trades, ATRI 34). CUP is the only one whose match is rare in both columns. `tests/test_chart_patterns.py` holds the measurement and fails if any detector drifts looser.
- **The CUP numbers above are STALE.** A manual chart review after that backtest found the handle test was accepting things no one would call a handle — a 6-bar 8.5% rejection at the rim on rising volume (META), 37-38 bar drifts (EHC, EMBJ), a 0.5%-deep flat pause (TECH). The handle now has to be 5-20 bars, 2-15% deep, drifting at under 1.2%/bar, on volume below the cup's. That cut a live scan from 76 cup matches to a handful, so CUP's 3 backtest trades were taken under a definition that no longer exists. Re-run before quoting them. The other five patterns are untouched.
- **The exit is not what is wrong.** All eight exit policies were run over that identical 193-signal set: the best (a 20-day Donchian exit, no target) reached +0.27% CAGR and a 5 ATR trail 0.00%, against -3.26% for the bracket. So the exit costs about three points of CAGR, and none of the 13-17 point shortfall against the benchmark. The entry carries no edge to protect.
- That result is the strategy's headline, not a footnote. It is one market and one window, so it does not prove the patterns carry no information — but anyone trading this off the screener is trading a measured loss. Re-measure before believing otherwise.
- Pattern recognition is the most over-claimed idea in technical analysis, and this is one reading of seven informally-defined shapes. The open question is whether shape adds anything over `breakout`, which needs no shape at all; on the evidence above the burden of proof sits with the shape.
- Any detector is one reading of an informally-defined shape. A chart a human would call a cup may score 0.3 here, and vice versa. Read `pattern_note` before trusting `pattern_quality`.
- Flat bases and flags project their PRIOR ADVANCE as the measured move, not the base height (a 10% box cannot project 2R off a stop under its own low). That is the most aggressive assumption in the file.
- Several patterns usually match one chart (a VCP is often also a cup or a flat base). The traded one is whichever scores highest among those near their pivot; `patterns_seen` lists the rest. Do not read a long `patterns_seen` as corroboration — the detectors are not independent.

## Commands

```bash
python3 -m swing_screener.screening.pipeline --market us --strategy chart_pattern
python3 -m swing_screener.screening.inspect --market us --symbol AAPL --strategy chart_pattern
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --strategy chart_pattern
```

---

*Generated from `scripts/swing_screener/strategies/chart_pattern.py`. Do not edit by hand — re-run `python3 -m swing_screener.strategies.docs --write`.*
