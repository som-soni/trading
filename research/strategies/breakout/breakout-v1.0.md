# Volume-confirmed breakout

`breakout` · family **breakout** · **v1.0** · fingerprint `a796b288`

> Not validated, no demonstrated edge: thresholds are untuned defaults, and the one recorded run (US, 500-symbol sample, bracket exits) returned -1.74% CAGR, about 14.6 points a year behind SPY. Measured before the 2026-10 cost fix (exit slippage was charged twice); re-measured runs moved by −0.8 to +0.9 points of CAGR (the extra cash changes which later signals are taken), so re-run before relying on it.

Long breakouts to new 55-day highs out of a tight consolidation, confirmed by expanding volume.

## Thesis

A decisive, volume-confirmed break to new highs out of a tight consolidation continues, so buy strength rather than weakness.

## How it works

1. **Screen** for stocks above their SMA200 and within 20% of the 52-week high.
2. **Gates B1-B7** require an SMA200 that is not falling (no more than 0.5% below its level 20 bars ago), price within 5% of the 52-week high, a tight 20-bar base (range under 6 ATR), not already extended beyond 4 ATR above SMA20, ATR no more than 8% of price, and no earnings inside 10 days.
3. **Setups**: BO-01 is a close above the 55-day pivot on confirming volume; BO-02 is a coil sitting within 3% below that pivot. Only BO-01 is the entry signal, so only BO-01 can reach TRADE - HIGH CONFIDENCE.
4. **Entry** is 0.1% above the higher of today's high and the pivot, rounded up to the tick; for BO-01 the signal *is* the setup, because the close has already cleared the pivot.
5. **Exit**: stop below the consolidation (never wider than 2 ATR), target the entry plus the base height, lowered to the nearest overhead level if one is in the way. Plans projecting under 2R are not traded.

## Hard gates (failing any one means AVOID)

| code | meaning |
|---|---|
| `B1` | The latest close must be strictly above the 200-day SMA. A missing SMA200 fails. |
| `B2` | The 200-day SMA must not be falling. It fails only if SMA200 is more than 0.5% below its value 20 bars ago, so a flat SMA200 passes as well as a rising one. |
| `B3` | The close must be at least 95% of the 52-week high (high_252, which includes today's bar), i.e. no more than 5% below it. Fails if the 52-week high is unavailable. |
| `B4` | The 20 bars before today must form a tight base: their highest high minus lowest low must be at most 6 x ATR14. Fails if there are fewer than 20 prior bars or ATR is missing or zero. |
| `B5` | The close must not be more than 4 x ATR14 above the 20-day SMA (exactly 4 ATR passes). If SMA20 or ATR is missing the gate passes. |
| `B6` | ATR14 as a percent of the close must be 8% or less. If ATR% is missing the gate passes. |
| `B7` | Earnings must not be 10 or fewer days away. Passes when no earnings date is known; the backtest has no historical earnings calendar, so it always passes there. |

## Watch flags (these cap confidence)

| code | meaning |
|---|---|
| `XB1` | Raised when the close is more than 2.5 x ATR14 above the 20-day SMA (extended; the note suggests SMA20 as a pullback level). Caps the decision at TRADE ON TRIGGER and lowers setup quality by 0.5. |
| `XB2` | Meant to flag a breakout on below-average volume: raised only when BO-01 is active AND today's volume is below its 50-day average. Would cap the decision at WATCH - WAIT and cut setup quality by 1. In practice it can never fire, because BO-01 itself requires volume above 1.5x the 50-day average. |
| `XB3` | Raised when RSI14 is above 80 (overbought). Caps the decision at TRADE ON TRIGGER; no effect on setup quality. |

## Setups

| code | meaning |
|---|---|
| `BO-01` | Breakout: today's close is strictly above the pivot (the highest high of the 55 bars before today) AND today's volume is more than 1.5x its 50-day average. Entry-eligible, and it is also the entry signal, so only BO-01 can reach TRADE - HIGH CONFIDENCE (setup quality 2). |
| `BO-02` | Coil: the close is within 3% below the pivot (between 97% and 100% of it), not through it yet. Entry-eligible but the signal has not fired, so the best it gets is TRADE ON TRIGGER (setup quality 1). If BO-01 is also true, BO-01 is used. |

## Entry

- Entry is a buy-stop at 0.1% above the higher of today's high and the 55-bar pivot, rounded up to the market's tick size.
- Stop is the lowest low of the 20 bars before today minus 0.1 ATR, but never more than 2 ATR below entry (whichever is higher), rounded down to the tick.
- Target is entry plus the base height (highest high minus lowest low of the 20 prior bars), with no minimum R. If an overhead supply level sits between entry and that target, the target is lowered to the nearest one.
- A plan is WATCH - WAIT if the position is too large for the account, the stop is more than 8% below entry, or the plan offers less than 2R. TRADE - HIGH CONFIDENCE additionally needs BO-01, no watch-flag cap, a stop of 7% or less, at least 2R and no earnings within 15 days; otherwise TRADE ON TRIGGER. A market-regime downgrade lowers the label one tier.

## Exit

- Live: a fixed bracket. The stop and target set at entry do not move; there is no trailing stop or time exit in the strategy itself.
- Backtest (default bracket mode): only TRADE - HIGH CONFIDENCE signals (so only BO-01) are placed, as resting buy-stops that fill on a later bar trading through the entry (at the open if it gaps above) and expire unfilled after 10 business days, or are cancelled if price hits the stop first or gaps past the target.
- Backtest exits: the first later bar whose low touches the stop or whose high touches the target closes the trade; if both on one bar the stop is assumed first, and gaps fill at the open. Positions still open at the end are marked at the last close.

## Parameters

| parameter | value | meaning |
|---|---|---|
| Consolidation length | `None` | Bars before today that must form the tight base (B4) and that define stop and target. |
| Pivot lookback | `None` | Bars before today whose highest high is the breakout pivot for BO-01/BO-02 and entry. |
| Minimum price | `None` | Pre-filter: symbols closing below this price are not screened. |
| Minimum ATR% | `None` | Pre-filter: ATR14 as % of close must exceed this, so very quiet stocks are skipped. |
| Minimum liquidity | `None` | Pre-filter: 20-day average dollar volume must be at least this. |
| Tick size | `None` | Entry is rounded up and the stop rounded down to this increment. |
| Max open positions | `None` | Portfolio backtest: position slots; signals arriving with no free slot are missed. |

## Known caveats

- **NOT VALIDATED.** The thresholds are reasonable defaults, not tuned. Backtested once (US, 500-symbol sample, bracket exits): -1.74% CAGR, about 14.6 points a year behind SPY — see research/momentum-trend-research.md.
- Treat anything it produces as a hypothesis to test, not a signal to act on.
- The target is the measured move off the base, with no floor; setups projecting under 2R are rejected rather than padded. When an overhead level lowers the target, the R column is smaller than `structural_r`, and the 2R test uses the lowered R.
- Watch flag XB2 (breakout on below-average volume) can never fire: it needs BO-01, which already requires volume above 1.5x average.

## Commands

```bash
python3 -m swing_screener.screening.pipeline --market us --strategy breakout
python3 -m swing_screener.screening.inspect --market us --symbol AAPL --strategy breakout
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --strategy breakout
```

---

*Generated from `scripts/swing_screener/strategies/breakout.py`. Do not edit by hand — re-run `python3 -m swing_screener.strategies.docs --write`.*
