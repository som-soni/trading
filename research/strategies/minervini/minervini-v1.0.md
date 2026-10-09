# Minervini SEPA (trend template + VCP)

`minervini` · family **minervini** · **v1.0** · fingerprint `4b8719af`

> No demonstrated edge. Portfolio backtest 2013 onward, 50-day exit: India CAGR 5.0% (index 11.7%), max drawdown −29%, 771 trades; US −1.7% (index 12.8%), max drawdown −43%, 1,286 trades. Skipping signals from industry groups rated below 50 (`--min-group-rs 50`) helped in both: India 6.3%, US 1.8%. See `minervini_spec` for the version built to the written specification.

Stage-2 uptrend by the Trend Template, entered on a volatility contraction breakout, with a stop tight enough to keep the average loss near 7%.

## Thesis

Stocks making large advances are already strong beforehand, so buy only confirmed Stage-2 uptrends, and buy them at the one moment when supply has dried up enough that a 10%-maximum stop sits just below support. Small, strictly-capped losses against much larger winners is the whole arithmetic.

## How it works

1. Gates M1-M8 are Minervini's Trend Template: price above the 50/150/200-day averages, those averages stacked in that order, the 200-day rising for at least 21 sessions, price at least 30% above its 52-week low and within 25% of its 52-week high, and relative strength above a floor.
2. Inside that, the base is tested for a Volatility Contraction Pattern: successive pullbacks each shallower than the last over the final 3 legs, the newest no deeper than 10%, and volume in the tight area below its own 50-day average.
3. The pivot is the high of that final tight area. Entry is a buy-stop just through it; the protective stop goes below the tight area's low.
4. If the structural stop would be more than 10% below entry, the trade is refused rather than widened — the risk cap is a constraint on which trades exist, not a number to stretch.
5. Ranking among competing signals is 12-1 momentum, standing in for the cross-sectional RS Rating.

## Hard gates (failing any one means AVOID)

| code | meaning |
|---|---|
| `M1` | Close above the 50-day simple moving average. |
| `M2` | Close above the 150-day simple moving average. |
| `M3` | Close above the 200-day simple moving average. |
| `M4` | The averages stacked for a Stage-2 advance: 50-day above 150-day above 200-day. |
| `M5` | The 200-day average is higher than it was 21 sessions ago — rising for at least a month. |
| `M6` | Close at least 30% above the 52-week low, so the stock has already left its base behind. |
| `M7` | Close within 25% of the 52-week high — near highs, not recovering from a collapse. |
| `M8` | Relative strength proxy: 12-1 month momentum of at least 0.1. Stands in for an RS Rating of 70+, which is cross-sectional and cannot be computed per symbol. |

## Watch flags (these cap confidence)

| code | meaning |
|---|---|
| `V1` | The final contraction is deeper than 8% — a base, but not a tight one. |
| `V2` | Volume in the tight area has not dried up below its 50-day average, so sellers may not be exhausted. |
| `V3` | Fewer than 3 contraction legs: the pattern is present but shallowly evidenced. |
| `V4` | Price is more than 4 ATR above the 50-day average — extended, with climax risk. |
| `V5` | Earnings are due inside the holding window, which can gap price straight through the stop. |
| `V6` | Price has run more than 5% beyond the pivot, so the entry level has already passed — taking it now means chasing, and the stop would no longer sit just below the tight area. |

## Setups

| code | meaning |
|---|---|
| `MV-01` | Volatility contraction complete and price has closed above the pivot — the high of the final tight area. |
| `MV-02` | Volatility contraction complete and price is coiled within 8% below the pivot, not yet through it. |

## Entry

- Entry: a buy-stop at the pivot (the high of the final tight area) plus one tick.
- Stop: just below the low of the final tight area, and never more than 10% below entry — a wider structural stop refuses the trade instead of stretching the cap.
- Target: a nominal 3R, used only for sizing and reporting. The real exit is a rule, not a price.

## Exit

- Live: cut at the stop without hesitation; raise the stop toward breakeven once the trade advances; sell into unusual strength and out of bad behaviour (heavy-volume declines, a break of key moving averages).
- Backtest: run with a 50-day moving-average exit and no fixed target (`--exit-mode ma --ma-col sma50 --no-target`), which approximates 'sell into weakness' but models neither the breakeven raise nor partial profit-taking.

## Parameters

| parameter | value | meaning |
|---|---|---|
| Minimum above 52-week low | `None` | Stage-2 stocks have left their lows. |
| Maximum below 52-week high | `None` | Buy near highs, not in recovery. |
| 200-day rising window | `None` | Sessions the long average must have risen over. |
| RS momentum floor | `None` | Per-symbol proxy for an RS Rating of 70+. |
| VCP lookback | `None` | Bars of base examined for contractions. |
| Contraction legs tested | `None` | How many recent pullbacks must shrink in sequence. |
| Tight-area ceiling | `None` | Deepest the final contraction may be. |
| Volume dry-up ratio | `None` | Tight-area volume against its own 50-day average. |
| Maximum stop | `None` | His absolute loss limit; wider structural stops refuse the trade. |
| Maximum chase above pivot | `None` | Beyond this the breakout entry has passed. |
| Minimum history | `None` | Bars required before the template can judge a symbol. |

## Known caveats

- **The fundamental screen (SEPA part 2) is NOT implemented.** yfinance carries 5 quarters of current-restatement financials; measuring growth acceleration needs 8+ quarters of point-in-time data. The daily screener attaches current fundamentals as watch flags; no backtest here includes them.
- Minervini raises the stop to breakeven once a trade advances and sells into strength; this version's backtest runs a plain 50-day exit instead (all-or-nothing, no breakeven). `minervini_spec` runs the full exit set.
- The Trend Template is public and heavily data-mined. An in-sample edge on the same 13.75 years everything else here uses is weak evidence.
- The VCP thresholds are an interpretation calibrated for selectivity, not fitted to returns — but they are still choices, and a different reading of 'contraction' would give different trades.

## Changelog

| version | date | change |
|---|---|---|
| 1.0 | 2026-10-05 | First implementation, built from a prose description of SEPA. Approximates the exits with a 50-day moving-average break because the simulator had no mode for the real selling rules. |

## Commands

```bash
python3 -m swing_screener.screening.pipeline --market us --strategy minervini
python3 -m swing_screener.screening.inspect --market us --symbol AAPL --strategy minervini
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --strategy minervini --strategy minervini --exit-mode ma --ma-col sma50 --no-target
```

---

*Generated from `scripts/swing_screener/strategies/minervini.py`. Do not edit by hand — re-run `python3 -m swing_screener.strategies.docs --write`.*
