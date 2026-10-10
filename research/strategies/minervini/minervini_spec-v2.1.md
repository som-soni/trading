# Minervini VCP (to the backtest spec)

`minervini_spec` · family **minervini** · **v2.1** · fingerprint `f75ef319`

> No demonstrated edge (India, 2010 onward, `--spec`). Confirmed breakouts (EN-01): 9 trades in 16 years, CAGR −0.1% — the spec's base rules almost never complete on Indian daily data. Buy-stops (EN-02): 114 trades, expectancy −0.03R, profit factor 0.86, CAGR 0.1% against the index's ~12%, max drawdown −8.6%; the failed-breakout exit closes ~80% of trades for −0.3R each. No parameter at either end of the spec's test ranges, and no failed-breakout window, gives an edge that holds both in and out of sample (research/minervini-spec-sensitivity-india.md). US, same rules: EN-01 26 trades, −0.14R; EN-02 526 trades, −0.02R, CAGR −0.8% (index ~13%), max drawdown −30% — +0.05R to 2019, −0.12R since; the stricter variants that help in sample all turn negative after 2019 (research/minervini-spec-sensitivity-us.md).

The written Minervini backtest specification, rule for rule: Trend Template, a base-high anchored VCP, confirmed breakouts at the next open or buy-stops through the pivot, and the spec's exits (failed breakout, breakeven, partial profit, climax, 50-day break).

## Thesis

The same edge as Minervini's SEPA — buy Stage-2 leaders as a volatility contraction completes, with small, capped losses against large winners — but tested exactly as the written specification defines it, so that the result measures the method rather than one reading of it.

## How it works

1. Gates M1–M8 are the Trend Template (the Stage 2 screen's criteria): price above the 50/150/200-day averages, the averages stacked, the 200-day rising over 21 sessions, at least 30% above the 52-week low and within 25% of the high, and relative strength. The backtest applies the true cross-sectional RS rating of 70+ on top.
2. The base starts at the base high: the most recent confirmed swing high (5 bars either side, known only 5 bars later) that no close has exceeded since. It must follow a 30% advance, last 15–325 sessions, start with the full template in force, and keep the long averages in order every day of it.
3. Contractions run from each swing high to the lowest low before the next. There must be 2–6, the first no deeper than 35% and each at most 0.8 × the one before. Wiggles under 2% are ignored.
4. The final tight area is the last 10 sessions: its high is the pivot, its low the tight low. It must span at most 10%, the pivot must be within 0.9 of the base high, and its volume must have dried up to 0.7 × the 50-day average.
5. MV-02 (coiled): the base is complete and the close is within 8% below the pivot. A buy-stop rests just above the pivot.
6. MV-01 (breakout): the base was complete yesterday, yesterday's close was at or below yesterday's pivot and today's close is above it — on at least 1.4 × average volume, in the upper half of the day's range, and no more than 5% past the pivot. Bought at the next open.

## Hard gates (failing any one means AVOID)

| code | meaning |
|---|---|
| `M1` | TT-05: close above the 50-day average. |
| `M2` | TT-01: close above the 150-day average. |
| `M3` | TT-01: close above the 200-day average. |
| `M4` | TT-02 and TT-04: the 50-day above the 150-day above the 200-day. |
| `M5` | TT-03: the 200-day higher than 21 sessions ago. |
| `M6` | TT-06: close at least 30% above the 52-week low. |
| `M7` | TT-07: close within 25% of the 52-week high. |
| `M8` | TT-08 stand-in: 12-1 month momentum of at least 0.1. The backtest also requires the true RS rating of 70+ across the market. |

## Watch flags (these cap confidence)

| code | meaning |
|---|---|
| `B1` | Closed through the pivot on light volume — under 1.4 × the 50-day average (MV-01a), so not a confirmed breakout. |
| `B2` | Closed more than 5% past the pivot (MV-01b): extended beyond the buy range. |
| `B3` | Closed through the pivot but in the lower half of the day's range (MV-01c). |
| `B4` | Earnings are due within 10 days (live screen only). |

## Setups

| code | meaning |
|---|---|
| `MV-01` | Breakout: yesterday's base was complete, and today's close went through yesterday's pivot on volume, in the upper half of the range, within 5% of the pivot. |
| `MV-02` | Coiled: the base is complete and the close is within 8% below the pivot. |

## Entry

- MV-01 (EN-01): buy at the next session's open; skip it if that open is more than 5% above the pivot or at or below the tight low.
- MV-02 (EN-02): a buy-stop at the pivot plus 0.1%, resting for up to 10 sessions; it fills at the stop price or the open if the stock gaps over it, is skipped if that is more than 5% above the pivot, and is cancelled by a close below the tight low.
- Stop: 0.5% under the tight low. A fill whose stop is more than 8% below it is skipped. Size: 1% of equity at risk, capped at the market's position limit.
- One entry per base: a base already traded is not entered again.
- Target: a nominal 3R, for sizing and reporting only.

## Exit

- In priority order, each session: EX-01 the stop (filled at the open if it gapped through); EX-02 a close below the pivot within 5 sessions of entry — a failed breakout, sold at the next open; EX-03 once the high reaches 2R, the stop rises to breakeven plus costs; EX-04 one third sold at 3R; EX-05 a climax run once up 25% (the biggest up day on the biggest volume since entry, 8 of 10 up closes, 70% above the 200-day, or a 3% gap after a 50% gain), sold at the next open; EX-06 a close below the 50-day average on at least average volume, sold at the next open.
- Backtest: `--exit-mode minervini` in the portfolio simulator; the spec's run adds `--spec`, which sets 8 positions, a 6% open-risk cap, a 5% liquidity cap, RS ranking and the spec's costs.

## Parameters

| parameter | value | meaning |
|---|---|---|
| Swing confirmation | `None` | Bars either side of a swing point; it is known only this many bars later. |
| Prior advance | `None` | Rise into the base high from the low of the 126 sessions before (VCP-01). |
| Base length, minimum | `None` | Sessions from the base high (VCP-02). |
| Base length, maximum | `None` | About 65 weeks (VCP-02). |
| Contractions, minimum | `None` | VCP-04. |
| Contractions, maximum | `None` | VCP-04. |
| First contraction, deepest | `None` | VCP-05. |
| Shrink factor | `None` | Each contraction at most this × the previous (VCP-06). |
| Tight area | `None` | Sessions in the final tight area (VCP-08). |
| Tight-area span | `None` | Deepest final contraction and widest tight area (VCP-08). |
| Pivot near the base high | `None` | VCP-09. |
| Volume dry-up | `None` | Tight-area volume against its 50-day average (VCP-10). |
| Coil distance | `None` | MV-02: how far below the pivot still counts. |
| Breakout volume | `None` | MV-01a. |
| Buy range | `None` | MV-01b, and the most a fill may sit above the pivot. |
| Stop buffer | `None` | SL-01. |
| Maximum stop | `None` | SL-03, checked at the fill. |
| Positions | `None` | PF-02, with --spec. |
| Open-risk cap | `None` | PF-04, with --spec. |
| Liquidity cap | `None` | SL-06: largest order as a % of 50-day average traded value, with --spec. |
| Minimum history | `None` | Bars required before the template can judge a symbol. |

## Known caveats

- **Survivorship bias.** The universe is today's listed stocks; companies delisted since are missing, which flatters every result.
- **Corporate actions.** Prices are adjusted when fetched; a split or bonus after a symbol's last full fetch shows as a crash until its history is re-fetched (`marketdata.splits`).
- **Relative strength** is applied twice: the per-stock gate M8 uses 12-1 month momentum of 0.1+ (a stand-in that a one-symbol evaluation can compute), and the backtest's `--min-rs` applies the true RS rating across the market. The stand-in rarely binds when the rating is 70+.
- **The fundamental screen (SEPA part 2) is not part of the spec or the backtest** — there is no point-in-time fundamental history.
- **Circuit limits** (C-03, India) are not modelled: a stop on a locked day fills at the next open, which daily bars cannot tell apart from a gap.
- **Base number** counts the bases that produced a breakout since the trend last broke; it is worked out by the backtest from the signal list, and only reported, not filtered on by default.
- EN-03 (buying inside the tight area before any breakout) is not implemented.
- The detector turns a chart-reading judgement into numbers; every threshold is a parameter of the spec (section 11), most of them marked there as assumptions.

## Changelog

| version | date | change |
|---|---|---|
| 2.1 | 2026-10-10 | VCP detector corrected (core/vcp_spec.py). Contractions are now segmented by a zig-zag requiring a real reversal in BOTH directions, not by swing highs alone: a two-day bounce used to start a new leg, splitting one 20% pullback into 8% then 15% so the 'second' read deeper and VCP-06 rejected a valid base. The threshold is ATR-scaled, because a fixed 3% sits below one day's range on a volatile name (MU's median ATR is 3.79% of close) and turned noise into a median of 12 legs against a limit of 6. The base-period trend rule no longer demands close > SMA150 every day, which contradicted VCP-05's allowance of a 35% first contraction; it now requires the MA structure plus close above 0.97x SMA200. The dry-up baseline is taken from before the tight area rather than from a 50-day average that already includes it, and the tight area runs from the last confirmed zig-zag low instead of a fixed 10 bars. A prior-advance window shorter than 126 bars now fails instead of silently shortening. |
| 2.0 | 2026-10-09 | Rebuilt to the written backtest specification: base-high anchored VCP, confirmed breakouts, and the real exit ladder (failed breakout, breakeven, partial profit, climax, 50-day break) via --exit-mode minervini. Max stop 10% -> 8%; cross-sectional RS rank replaces v1's absolute momentum floor. |

## Commands

```bash
python3 -m swing_screener.screening.pipeline --market us --strategy minervini_spec
python3 -m swing_screener.screening.inspect --market us --symbol AAPL --strategy minervini_spec
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --strategy minervini_spec --strategy minervini_spec --spec --accept-labels 'TRADE - HIGH CONFIDENCE'
```

---

*Generated from `scripts/swing_screener/strategies/minervini_spec.py`. Do not edit by hand — re-run `python3 -m swing_screener.strategies.docs --write`.*
