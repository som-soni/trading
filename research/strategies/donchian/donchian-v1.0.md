# Donchian channel breakout

`donchian` · family **donchian** · **v1.0** · fingerprint `69e24dab`

> No demonstrated edge: backtested with a 50-day channel exit and no target, it trailed the index in both markets on the widest runs (India full universe 7.34% CAGR vs 11.68%; US 500-sample 5.78% vs ~12.8%). Trade shape is sound (profit factor ~1.2) but signal selection among tied breakouts is arbitrary. Measured before the 2026-10 cost fix (exit slippage was charged twice); re-measured runs moved by −0.8 to +0.9 points of CAGR (the extra cash changes which later signals are taken), so re-run before relying on it.

Classical trend following: buy an N-day high, exit on an M-day low, stop at a volatility multiple, and filter almost nothing.

## Thesis

Trends persist, so buy a new N-day high and hold until the trend breaks. The edge is in never capping a winner, paid for with a low win rate and many small losses.

## How it works

1. **Screen** only for price, liquidity and enough history — no trend, momentum or volatility filter.
2. **Gate N1** requires price above its 200-day average (the one concession: this is a long-only equity book, not a long/short futures portfolio that can profit from downtrends).
3. **Gate N2** rejects a stock already more than 1 ATR above the channel high, i.e. the breakout has run away before you could act.
4. **Setup DC-01** fires when the close exceeds the highest high of the last 55 bars; DC-02 marks a coil within 1 ATR below it. Only DC-01 is the entry signal, so DC-02 never reaches TRADE - HIGH CONFIDENCE.
5. **Entry** is 0.1% above the channel high, rounded up to the tick — where a resting buy-stop fills (in the backtest it usually fills at the next open, because DC-01 only fires once the close is already through the channel). **Stop** is 2 ATR below it (the Turtles' 2N), floored at 2% so a very quiet stock does not get a stop that daily noise alone would trigger.
6. **Exit** is a close below an N-day low, with no profit target: that is the whole point. The screener reports the 20-day low, but nothing manages live positions; backtests use `--donchian-bars` (50 in every recorded run), not 20.

## Hard gates (failing any one means AVOID)

| code | meaning |
|---|---|
| `N1` | Today's close must be above the 200-day simple moving average. Fails if the close is at or below it, or if there is not enough history to compute the SMA200. |
| `N2` | Today's close must be no more than 1 ATR(14) above the 55-day channel high (the highest high of the 55 bars before today). A close further above it means the breakout has already run away and the symbol is AVOID. |

## Watch flags (these cap confidence)

| code | meaning |
|---|---|
| `XN1` | Raised only on a DC-01 breakout day when today's volume is below its 50-day average volume. Caps the decision at TRADE ON TRIGGER and lowers setup quality by 0.5, which demotes it in the backtest's ranking of competing signals. |
| `XN2` | Raised when 2 x ATR(14) is more than 12% of the close (a very wide raw volatility stop). Caps the decision at TRADE ON TRIGGER. Separately, any plan whose actual stop risk exceeds 15% of entry is downgraded to WATCH - WAIT. |

## Setups

| code | meaning |
|---|---|
| `DC-01` | Breakout: today's close is above the highest high of the prior 55 bars. This is also the entry signal, so DC-01 is the only setup that can produce TRADE - HIGH CONFIDENCE and the only one the backtest trades. |
| `DC-02` | Coil: today's close is within 1 ATR(14) below the 55-day channel high (inclusive of the high itself). It builds a plan but the entry signal has not fired, so it is capped at TRADE ON TRIGGER live and never taken by the default backtest. |

## Entry

- Channel high = highest high of the 55 bars before today (today's bar excluded).
- Entry is a buy-stop at the channel high + 0.1%, rounded up to the market tick size. Because DC-01 already closed above the channel, the next bar usually opens through it; the backtest fills at max(entry, open) plus slippage.
- Stop is the lower of entry - 2 x ATR(14) and entry x (1 - 2%), rounded down to the tick, so the stop is never closer than 2% below entry.
- Target is a nominal entry + 10 x ATR(14), used only for sizing and the reported R multiple — the plan is not meant to exit there.
- Size = risk budget (account x risk %) / (entry - stop), capped by the maximum position notional. No minimum-R test is applied.
- In the backtest an unfilled order rests for up to 10 business days and is cancelled if price trades down to the stop first.

## Exit

- Intended exit: a daily close below the lowest low of the prior 20 bars (the reported channel_low), or the initial stop, whichever comes first. The stop never trails.
- Live, the screener only reports channel_low and exit_channel; it does not manage open positions — the trader applies the channel exit by hand.
- Backtest with --exit-mode donchian: exits at the close when the close is below the lowest low of the prior --donchian-bars bars (default 50, not the strategy's own 20); the stop fills at min(stop, open) and wins a same-bar tie. --no-target removes the nominal target so winners can run.
- Without those flags the backtest uses the default bracket exit (stop or the nominal 10-ATR target, filled intrabar), which defeats the strategy's premise.

## Parameters

| parameter | value | meaning |
|---|---|---|
| Minimum price | `None` | Screen: last close must be at least this. |
| Minimum liquidity | `None` | Screen: 20-day average dollar volume must be at least this. |
| Risk per trade | `None` | Fraction of equity risked between entry and stop when sizing. |
| Max position size | `None` | Cap on one position's notional as a fraction of equity. |
| Position cap | `None` | Backtest slots; with many tied breakouts this is the binding limit. |
| Tick size | `None` | Entry rounded up and stop rounded down to this increment. |
| Slippage | `None` | Backtest cost per side, in basis points of notional. |

## Known caveats

- **No demonstrated edge.** Backtested with a 50-day channel exit: India full universe 7.34% CAGR vs the index's 11.68%; US 500-symbol sample 5.78% vs about 12.8%. Its exit rule was the only one of eight tested with positive per-trade expectancy, which is why it exists.
- Trend following's track record is in diversified futures traded long and short. A long-only single-market equity book removes both the cross-market diversification and the short side.
- Expect a LOW win rate (30-40%) by design. Judge it on expectancy and the size of winners, never on hit rate.
- Run it with `--exit-mode donchian --no-target`; the bracket exit defeats the strategy's entire premise.

## Commands

```bash
python3 -m swing_screener.screening.pipeline --market us --strategy donchian
python3 -m swing_screener.screening.inspect --market us --symbol AAPL --strategy donchian
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --strategy donchian --exit-mode donchian --no-target --donchian-bars 50
```

---

*Generated from `scripts/swing_screener/strategies/donchian.py`. Do not edit by hand — re-run `python3 -m swing_screener.strategies.docs --write`.*
