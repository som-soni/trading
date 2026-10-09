# Trend pullback / continuation

`trend_pullback` · family **trend_pullback** · **v1.0** · fingerprint `0acddbda`

> No demonstrated edge: portfolio backtest from 2013 with bracket exits returned -0.87% CAGR in the US (SPY 12.79%) and +0.57% in India (index 11.68%); seven alternative exit policies did not rescue it. Measured before the 2026-10 cost fix (exit slippage was charged twice); re-measured runs moved by −0.8 to +0.9 points of CAGR (the extra cash changes which later signals are taken), so re-run before relying on it.

Long pullbacks (TC-01) and tight continuation bases (TC-02) within an established uptrend, entered on a resumption signal above resistance.

## Thesis

A stock in a confirmed uptrend that pulls back a measured amount and then resumes should continue, so buy the resumption rather than the dip.

## How it works

1. **Screen** the universe on price, liquidity, ADX and volatility, and require SMA50 above SMA200.
2. **Hard gates (W/T/D)** confirm the uptrend is real — weekly price above a rising 30-week EMA, higher swing lows, positive 12-1 momentum, within 25% of the 52-week high — and disqualify specific hazards such as earnings inside 10 days or an unheld gap.
3. **Setups** look for the shape: TC-01 a pullback 30-60% of the prior impulse (or 1-3 ATR) from a high 3-10 bars old, holding above the prior swing low and not on rising volume; TC-02 a tight continuation base on below-average volume. TC-04 is informational only.
4. **Watch flags (X1-X9)** cap confidence without disqualifying — e.g. X1 marks a stock extended more than 2.5 ATR above its SMA20 or with RSI14 above 75.
5. **Entry is a resting buy-stop ABOVE the current price**, so you only buy if price actually resumes. In the backtest it expires unfilled after 10 business days (the live screener only states this in the report).
6. **Exit** is a fixed bracket: for TC-01 the stop sits just below the pullback low and the target is a measured move; for TC-02 the stop is the 10-bar low minus 0.1 ATR and the target the 10-bar high plus twice the range. Either target is cut to the nearest overhead level above entry. There is no trailing stop and no time stop.

## Hard gates (failing any one means AVOID)

| code | meaning |
|---|---|
| `W1` | Passes when the latest weekly close is above the 30-week EMA AND that EMA is higher than it was one week earlier. Fails with fewer than 31 weekly bars. |
| `W2` | Passes when the weekly SMA20 is strictly above the weekly SMA50. Fails with fewer than 50 weekly bars. |
| `T1` | Passes when daily SMA50 > SMA200 AND price has not broken down through the SMA50 — i.e. the close is not more than 2 ATR14 below the SMA50 and the last 5 closes are not all below the SMA50. |
| `T2` | Passes unless either average is falling: SMA50 more than 1% below its value 10 bars ago, or SMA200 more than 0.5% below its value 20 bars ago. A flat average passes (a flat SMA50 raises X4). |
| `T3` | Passes when the last two confirmed daily swing lows (3 bars either side) in the last 50 bars are rising; with fewer than two, the lowest low of the last 25 bars must be above the lowest low of the 25 bars before. |
| `T4` | Passes when 12-1 month momentum is positive: the close 21 bars ago is above the close 252 bars ago. Needs at least 253 daily bars. |
| `T5` | Passes when the close is at least 75% of the 52-week (252-bar) high, i.e. no more than 25% below it. |
| `T6` | Fails only when BOTH the 63-bar (about 3-month) return is negative AND the SMA50 is flat or falling (T2's definition); otherwise passes. |
| `D2` | Passes unless the next earnings date is 10 or fewer business days away. Unknown earnings dates pass, and the backtest never enforces this gate (no point-in-time earnings calendar). |
| `D3` | Fails when the pullback is on rising volume: the average volume of the bars since the swing high H is higher than the average volume of the impulse from L (lowest low in the 40 bars before H) up to H. |
| `D4` | Fails when the close is below the prior structural swing low (the last confirmed daily swing low before H); passes if there is none. |
| `D5` | Fails when any overhead resistance level (daily swing highs of the last year, weekly of ~5 years, monthly of all history, plus H) sits within 3% above the close — unless the only such level is H itself and a TC-01 or TC-02 setup is present. |
| `D6` | Fails when ATR14 is more than 8% of price (too volatile). |
| `D7` | Fails when any of the last 10 bars opened with a gap of more than 8% (up or down) versus the prior close and the current close is still below that pre-gap close. |

## Watch flags (these cap confidence)

| code | meaning |
|---|---|
| `X1` | Extended: close more than 2.5 ATR14 above the SMA20, OR RSI14 above 75. Caps the decision at WATCH - WAIT (wait for a pullback toward the SMA20). |
| `X2` | Close below the SMA50 while still passing T1. Caps the decision at TRADE ON TRIGGER and lifts Plan A's trigger to at least 0.1% above the SMA50. |
| `X3` | Positive flag: close within 1 ATR14 of a rising SMA50. No cap; adds 1.0 to setup quality (used for ranking). |
| `X4` | SMA50 flat (neither higher than 10 bars ago nor more than 1% lower). Labelled base (10-bar range at most 4.5 ATR and close within 10% of the 52-week high) or drift; drift caps at TRADE ON TRIGGER and subtracts 1.0 from setup quality, base has no effect. |
| `X5` | Low trend strength: ADX14 from 15 up to (not including) 20. Labelled base or drift as for X4; drift subtracts 1.0 from setup quality. Never caps the decision. |
| `X6` | ADX14 lower than 5 bars ago. If price is more than 5% below H and is closer to the SMA50 than 5 bars ago it is noted as momentum fading and subtracts 1.0 from setup quality. Never caps the decision. |
| `X7` | Late move: ADX14 above 40 together with X1. Forces Plan A (no switch to Plan B); X1 already caps the decision at WATCH - WAIT. |
| `X8` | Weak momentum: RSI14 below 40 while the close is above the SMA50. Caps the decision at TRADE ON TRIGGER. |
| `X9` | Monthly structure not confirmed (the former hard gate M1): with at least 24 months of history, any of — monthly close not above its 10-month SMA, last-12-month high not above the prior 12 months', or last-12-month low not above the prior 12 months'. Caps the decision at TRADE ON TRIGGER. |

## Setups

| code | meaning |
|---|---|
| `TC-01` | Pullback (entry-eligible, takes priority over TC-02). The drop from H to the pullback low P is 30-60% of the impulse H-L, or 1-3 ATR14; H was set 3-10 bars ago; P is above the prior structural swing low; and the pullback is not on rising volume (the D3 test). |
| `TC-02` | Tight continuation base (entry-eligible). The last 10 bars span at most 4.5 ATR14, the 5-day average volume is below the 50-day average, and the 10-bar low is above the prior structural swing low. |
| `TC-04` | Informational only, never an entry on its own: close within 2% of the 55-bar high or of the 52-week high. Adds 0.5 to setup quality. |

## Entry

- The active setup is TC-01 if valid, otherwise TC-02; with neither there is no plan. Every hard gate must pass or the decision is AVOID.
- Resumption signal (needed for TRADE - HIGH CONFIDENCE and for a backtest entry): the close is above the SMA20 and above the prior bar's high (TC-01) or the highest high of the 10 bars before today (TC-02), and no overhead level within 3% above the close sits more than 0.5% above H (H itself does not block).
- Plan A trigger starts at today's high (TC-01) or the higher of today's high and the prior 10-bar high (TC-02); with X2 it is raised to at least 0.1% above the SMA50. It then walks up: while any overhead level lies within 3% above the trigger, the trigger moves to the highest such level.
- Plan B trigger is H with no resistance walk-up, so its entry can sit just under resistance (known defect 1).
- Entry is a resting buy-stop at trigger + 0.1%, rounded up to the tick size, so it only fills if price trades up through it on a later bar.
- Stop: TC-01 uses the pullback low P minus 0.1 ATR14; TC-02 the lowest low of the last 10 bars (including today) minus 0.1 ATR14; rounded down to the tick.
- Target: TC-01 is P + (H - L), a measured move; TC-02 is the 10-bar high plus twice the 10-bar range. Either is cut to the nearest overhead level above the entry if that is lower.
- Plan choice: with X7 always Plan A; otherwise if Plan A is below 2R and Plan B reaches 2R, Plan B is used; else Plan A.
- TRADE - HIGH CONFIDENCE needs the signal fired, no capping watch flag, a stop no wider than 3.0 ATR and 12% of entry, at least 2R, and earnings not within 14 business days (note: D2 uses 10 — known defect 4).
- WATCH - WAIT if the position is too large for the account, the stop exceeds 3.5 ATR or 15% of entry, R is below 2, demand/supply reads 'Supply in control', or X1 is set. Everything else that passes the gates is TRADE ON TRIGGER. Live, a market-regime downgrade then drops the label one tier.
- A plan with NaN risk is not rejected in the live path (known defect 2); the backtest discards it via TradePlan.is_valid.

## Exit

- Fixed bracket: the stop and target set at entry never move. No trailing stop, no time stop, no exit on a trend break.
- Unfilled buy-stops expire after 10 business days; in the backtest an order is also cancelled if price falls to the stop before filling, or if it gaps open at or above the target.
- Backtest fills: a gap through the trigger fills at the open; if stop and target are both touched on one bar the stop wins; a gap through the stop exits at the open. Positions still open at the end are marked at the last close.
- The portfolio backtest (the default) adds a position cap, slippage and commission, and sizes off current equity; it does not apply the earnings gate, the market-regime downgrade or the per-sector cap.

## Parameters

| parameter | value | meaning |
|---|---|---|
| Minimum price | `None` | Pre-screen: close must be at least this (0 disables it, as in India). |
| Minimum liquidity | `None` | Pre-screen: 20-day average of close x volume must be at least this. |
| Minimum ADX | `None` | Pre-screen: ADX14 must be strictly above this. |
| Minimum ATR % | `None` | Pre-screen: ATR14 as % of price must be strictly above this. |
| Tick size | `None` | Entry is rounded up and the stop rounded down to this increment. |
| Risk per trade | `None` | Fraction of the account risked between entry and stop; sets share count. |
| Risk per trade, high volatility | `None` | Used instead of risk_pct when the volatility index is above its threshold. |
| Max position size | `None` | Notional cap per position as a fraction of the account; can shrink size. |
| Max open positions | `None` | Portfolio backtest: signals arriving with no free slot are missed. |
| Per-sector limit | `None` | Live: at most this many tradeable names kept per sector (ranked by setup quality); the rest become WATCH - SECTOR LIMIT. |
| Slippage | `None` | Portfolio backtest: cost per side in basis points of notional. |

## Known caveats

- **No demonstrated edge.** Backtested over 13.75 years it returned -0.87% CAGR in the US and +0.57% in India, against indices doing 12.79% and 11.68%.
- The confidence tiers do not discriminate — TRADE - HIGH CONFIDENCE performed no better than TRADE ON TRIGGER across 484 trades.
- The fixed target caps the upside: on Micron's 2025 run it would have exited at +36% against a +484% move.
- Plan B enters at H when Plan A fails the 2R test, which manufactures the R rather than earning it (when Plan A's resistance walk-up has already moved past H, Plan B's entry is actually lower).

## Commands

```bash
python3 -m swing_screener.screening.pipeline --market us --strategy trend_pullback
python3 -m swing_screener.screening.inspect --market us --symbol AAPL --strategy trend_pullback
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --strategy trend_pullback
```

---

*Generated from `scripts/swing_screener/strategies/trend_pullback.py`. Do not edit by hand — re-run `python3 -m swing_screener.strategies.docs --write`.*
