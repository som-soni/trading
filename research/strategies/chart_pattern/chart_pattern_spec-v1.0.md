# Chart patterns (to the detection spec)

`chart_pattern_spec` · family **chart_pattern** · **v1.0** · fingerprint `1c17e9be`

> Backtested 2026-10-09 and it loses, by less than its sibling: -0.93% CAGR and -0.072R per trade over 253 trades (US, 2020-2026, 300-symbol sample), against `chart_pattern`'s -5.60% and -0.309R on the same run. The +0.234R difference has a Welch t of 1.16 and a 95% interval of [-0.16, +0.62], so the spec's discipline is NOT demonstrated to help; both lose 14-19 points of CAGR to the benchmark.

The written chart-pattern specification, rule for rule: eleven patterns detected with ATR-scaled tolerances, fitted trendlines and prior-trend context, traded at the spec's own trigger, invalidation and measured move.

*A variant of `chart_pattern` (Classical chart-pattern breakout).*

## Thesis

If classical chart patterns carry information, a detector built to a written specification — ATR-scaled tolerances, a prior-trend rule on every pattern, fitted boundary lines, and a breakout judged against a trigger frozen the day before — should find it where a looser reading of the same textbooks did not.

## How it works

1. **Swing points** come at two scales (3 and 8 bars each side), alternating high/low, with moves under max(3%, 1.5 x ATR/close) dropped as wiggles. Every level a pattern uses is built from them.
2. **Each pattern carries its own context rule** — a prior uptrend for continuations, a prior downtrend for reversals — so the same shape after a rise and after a fall are not treated as one thing.
3. **Setups** are the eleven bullish types, each detected by its own numbered rules; the report names which fired and, when none did, the first rule that failed.
4. **Gates S1-S5** require a live bullish pattern, no CONFIRMED topping pattern on the same chart, no earnings inside 10 trading days, ATR under 10% of price, and price no more than 4% past the trigger.
5. **Entry** is a tick through T x (1 + 0.5%), the level BO-01 calls a breakout, or the market price if price has already cleared it. **Target** is BO-06's measured move, T + H.
6. **The trigger fires** on a close through it on 1.4x average volume (BO-01 + BO-02). Without the volume it stays a setup, capped at WATCH.

## Hard gates (failing any one means AVOID)

| code | meaning |
|---|---|
| `S1` | A bullish pattern must be COMPLETE or newly CONFIRMED on this bar. A pattern that broke out more than its outcome horizon ago, or that BO-03/BO-04 voided, is history and does not qualify. |
| `S2` | No CONFIRMED topping pattern (double top, head and shoulders top, rising wedge, descending triangle) on the same chart. A long bought inside a confirmed top is the trade this screener would otherwise keep taking. |
| `S3` | Earnings must not fall within 10 trading days: a base breaking out two days before a print is a bet on the print. |
| `S4` | ATR14 must be at most 10% of price. |
| `S5` | The close must sit in the actionable band around the trigger: no more than 4% above it (past that the breakout happened without you) and no more than 10% below it. The spec has no such rule because §11's tracker holds a pattern from completion and lets BO-04 expire it; a screener asked about one bar needs the band, or it reports AEVA as a live double bottom with a trigger 108% overhead. |

## Watch flags (these cap confidence)

| code | meaning |
|---|---|
| `XS1` | A topping pattern is FORMING (rolled over but not yet through its neckline) on the same chart. Caps the decision at TRADE ON TRIGGER; a confirmed one fails gate S2 outright. |
| `XS2` | Price is through the trigger but volume is below 1.4x its 50-day average, so BO-02 has not confirmed the breakout. Caps at WATCH. |
| `XS3` | RSI14 above 80. Caps at TRADE ON TRIGGER. |

## Setups

| code | meaning |
|---|---|
| `CUP` | §4 cup with handle: a rounded correction of 12-33% recovering to its left lip, then a 5-25 day handle drifting down in the upper half of the cup on volume below 0.8x its 50-day average. T is the handle's high. |
| `CUPNH` | §4 the same cup read before a handle exists, with price still at the rim. T is the right lip C. O'Neil treats it as the weaker variant, which is why it is a separate code. |
| `DBOT` | §5.1 double bottom: two lows about equal within tolerance, at least 20 days apart, with a middle peak at least 10% above them. T is that peak. |
| `TBOT` | §5 triple bottom: the same with a third low, all three level. T is the higher of the two middle peaks. |
| `IHS` | §6.2 inverse head and shoulders: three lows with the middle one lowest and the shoulders level, under a neckline sloping no more than 0.3% per day. T is the neckline at today's bar, so it moves. |
| `ATRI` | §7 ascending triangle: a flat upper line and a rising lower one, at least five touches between them, converging with the apex still ahead and volume declining. T is the upper line. |
| `SYMM` | §7 symmetrical triangle: both lines converging at rates within a factor of two. Neutral by reputation; recorded here as a bullish break of the upper line. |
| `FWDG` | §10 falling wedge: both lines falling with the upper falling faster. The textbook reading is a bullish break. |
| `RECT` | §8.1 rectangle: two flat lines, a 5-25% range held for 20-250 days with at least four touches. T is the upper line. |
| `FBASE` | §8.2 flat base: a range no deeper than 15% over the longest window of 25-120 days that holds it, after a 20% advance, sitting within 5% of the 52-week high. T is the window high. |
| `FLAG` | §9.2 bull flag or pennant: a 15%+ pole inside 15 days on 1.3x volume, then a 5-20 day pause retracing at most half of it on falling volume. T is the pause's upper line. |
| `HTF` | §9.3 high tight flag: a pole that at least doubles in 20-40 days, then a 15-25 day flag no deeper than 25%. It carries no measured target, because the textbooks give none. |

## Entry

- **Entry** is a tick through T x (1 + 0.5%) — BO-01's breakout level — rounded up to the tick size, or the market price when price has already cleared it, since there is no resting buy-stop below the market.
- **Stop.** The spec's X is an INVALIDATION level, not a stop: BO-03 voids a pattern on a close beyond X, and for a double bottom that sits a full pattern height below the trigger. The stop is placed under X but never wider than 2 ATR, and never tighter than max(0.6 ATR, 1.5%) — a stop inside the spread is not a stop, and dividing a measured move by it fabricates R.
- **Target** is BO-06's measured move, T + H, with no floor. A setup projecting under 2R is rejected rather than padded.
- **Rejected as a trade** when the stop is more than 8% below the entry or the measured move projects under 2R; the row is kept as WATCH with the reason.

## Exit

- Live: the plan's fixed bracket — the stop under the pattern's low, or BO-06's measured target.
- The spec's own exit is BO-05: a close back through T within 10 days marks the pattern FAILED. That is a pattern-status rule, not a position rule, and the portfolio simulator does not implement it; a backtest of this strategy uses the shared exit policies like any other.
- Backtest: whatever `--exit-mode` selects (default the fixed bracket).

## Parameters

| parameter | value | meaning |
|---|---|---|
| Swing scales | `None` | Bars each side defining a confirmed swing point: 3 for flags and handles, 8 for cups, doubles and shoulders. A swing at bar i is only known at bar i + k. |
| Minimum swing | `None` | Moves smaller than max(3%, 1.5 x ATR/close) are wiggles and are dropped before any pattern is looked for. |
| Price tolerance | `None` | Two prices count as equal within max(3%, 0.75 x ATR/close) — wider on a volatile stock, which a fixed percentage is not. |
| Breakout buffer | `None` | BO-01: a close must clear the trigger by this percentage (0.5%). |
| Breakout volume | `None` | BO-02: and do it on 1.4x the 50-day average volume. |
| Actionable band | `None` | Gate S5 wants the close between 10% below the trigger and 4% above it. |
| Stop width | `None` | The stop sits under the pattern's invalidation level but never wider than 2 ATR nor tighter than max(0.6 ATR, 1.5%). |
| Minimum reward | `None` | A measured move projecting under 2R is WATCH, not a trade. |
| Minimum price | `None` | Screen: closes below this price are excluded. |
| Minimum liquidity | `None` | Screen: the 20-day average of close x volume must reach this. |
| Tick size | `None` | Entry is rounded up and the stop rounded down to this increment. |
| Risk per trade | `None` | Fraction of equity risked between entry and stop, which sets position size. |

## Known caveats

- **73% of its trades are one pattern.** CUPNH took 185 of 253; DBOT 15, IHS 18, FWDG 15, RECT 10, ATRI 4, TBOT 6; and CUP, FBASE, SYMM, FLAG and HTF took NONE. Whatever the backtest measured, it measured the cup-without-handle — the weaker O'Neil variant — not the spec's breadth. DBOT was the only pattern with positive expectancy (+0.05R on 15 trades, which is nothing).
- **It is signal-saturated.** 942 signals produced 253 trades: 85 were passed up with all 10 slots full and 132 for insufficient cash, and exposure ran at 93.9% against `chart_pattern`'s 79.3%. A position cap, not the detector, decided much of what got traded.
- **Five of the spec's rules cannot fire at its own default parameters** (CH-09, HS-06, TR-04, TR-07, FL-04) because §2.1's 3% minimum swing and §2.2's 3% tolerance are large relative to what those rules ask for. They are implemented and tested, and the defaults are left as written; see core/pattern_spec.py.
- **Flags and the high tight flag find nothing in practice.** Over 283 liquid US names the pole rules rejected 255 of them (FP-01 172, FP-02 63): a 15% rise inside 15 days on 1.3x volume is simply rare.
- **The flat base is the least selective pattern here**, firing on 24% of random walks against the cup's 0%. It has no touch requirement and its volume rule is off by default.
- **Detection costs ~40ms per symbol-day** against `chart_pattern`'s ~1ms, because eleven detectors run where seven did and each refits swings. A backtest of it is slower in proportion.
- **§5 has no ceiling on the middle swing**, so two lows either side of a spike pass DB-03: AEVA screened as a live double bottom with lows of 13.51 and 13.90 around a 28.42 peak. Gate S5's band keeps it out of the report rather than the detector rejecting it, because the detector implements the spec as written; `PatternParams.db_max_peak` exists to test a cap.
- **The reversal patterns are mostly unreachable through this screen.** `near_highs` wants price within 15% of the 52-week high above a rising 200-day, while DBOT and IHS require a prior DOWNTREND (PT-02) and form well below the highs. They are implemented and tested, and they will rarely fire here. Measuring them needs a screen that does not demand an uptrend — a deliberate follow-up, not an oversight: changing the screen would also break the like-for-like comparison with `chart_pattern` that this strategy exists for.
- Several patterns usually match one chart. The traded one is the highest-priority live match; `pattern` names it and the setup columns show the rest.

## Commands

```bash
python3 -m swing_screener.screening.pipeline --market us --strategy chart_pattern_spec
python3 -m swing_screener.screening.inspect --market us --symbol AAPL --strategy chart_pattern_spec
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --strategy chart_pattern_spec
```

---

*Generated from `scripts/swing_screener/strategies/chart_pattern_spec.py`. Do not edit by hand — re-run `python3 -m swing_screener.strategies.docs --write`.*
