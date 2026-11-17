# An index short that is short in declines (2026-11-17)

Third hedge test after [Hedge sleeves beside the long books](sleeve-turtle-trend-2026-11-17.md): `stage4_shorts` was
almost never short, so this sleeve shorts the market's own index whenever a trend rule says its trend is down, and sits
in cash otherwise. Produced by `swing_screener/backtesting/index_hedge.py`. Held as index futures: collateral earns the
cash rate, the short pays the index's total return (dividends included), 5 bps a switch.

**In short**

- **It is short when it should be.** The fast signal (`sma50_fall`: close below a falling 50-day) was short on 60–62%
  of decline sessions from 2022 on, and moved against the books (monthly correlation −0.43 to −0.59).
- **It passed the pre-set test on three India books**, including the ₹5L `momentum_dual_combo`, and failed or did not
  qualify on every US book.
- **But it beats plain cash by very little.** ₹5L book from 2022 on: 10% sleeve 20.9% CAGR / −20.1% drawdown / Sharpe
  0.84; 10% cash 21.0% / −21.1% / 0.82; book alone 22.5% / −23.6% / 0.82. One point of drawdown.
- **On its own it loses to cash** (India `sma50_fall`, 2022 on: Sharpe −0.14). Shorting an index that rises over time
  costs the equity premium in every false signal; the hedge pays only in the declines.
- **It is hard to hold at this size in India.** One Nifty futures lot is about ₹15 lakh of index, and India has no
  inverse ETF; a 10% sleeve of ₹5L (₹50,000) can only be held as bought puts, which this test did not model.

## The rules (written before any figure)

Three signals on the benchmark's close: `sma200` (below the 200-day), `sma50_fall` (below a 50-day that is lower than
10 sessions earlier) and `tsmom12` (12-month return negative, checked monthly). The signal and the weight (10/20/30%)
were chosen together in-sample (2013–2021) by `sleeve_blend`'s rule — cut the book's drawdown by ≥ 20% while giving up
≤ 2 CAGR points, then the best Sharpe — and judged once on 2022 on: Sharpe ≥ the book's, a shallower drawdown, CAGR
no more than 2 points lower. The same weight in cash is shown beside it.

## The sleeve on its own

| Market | Signal | Window | CAGR | Max DD | Sharpe over cash | Sessions short | Short on decline sessions |
|---|---|---|---|---|---|---|---|
| US | `sma200` | 2013–2021 | −5.3% | −41.8% | −0.47 | 12% | 49% |
| US | `sma200` | 2022 on | −1.6% | −18.0% | −0.36 | 24% | 78% |
| US | `sma50_fall` | 2013–2021 | −3.6% | −29.1% | −0.32 | 13% | 43% |
| US | `sma50_fall` | 2022 on | 2.0% | −21.2% | −0.09 | 19% | 62% |
| US | `tsmom12` | 2013–2021 | −3.9% | −32.8% | −0.66 | 11% | 23% |
| US | `tsmom12` | 2022 on | 2.3% | −15.4% | −0.12 | 22% | 50% |
| India | `sma200` | 2013–2021 | 0.9% | −31.0% | −0.44 | 25% | 40% |
| India | `sma200` | 2022 on | −0.4% | −13.8% | −0.66 | 27% | 38% |
| India | `sma50_fall` | 2013–2021 | 5.5% | −23.3% | −0.07 | 20% | 44% |
| India | `sma50_fall` | 2022 on | 4.6% | −9.8% | −0.14 | 27% | 60% |
| India | `tsmom12` | 2013–2021 | −2.1% | −41.9% | −1.02 | 22% | 10% |
| India | `tsmom12` | 2022 on | −3.6% | −18.3% | −1.94 | 16% | 0% |

## Beside the books, 2022 on

| Market | Book | Pick (in-sample) | Verdict | Book alone: CAGR / DD / Sharpe | With the sleeve | Same weight in cash |
|---|---|---|---|---|---|---|
| India | `momentum_dual_combo` | `sma50_fall`, 10% | PASS | 22.5% / −23.6% / 0.82 | 20.9% / −20.1% / 0.84 | 21.0% / −21.1% / 0.82 |
| India | `quality_momentum` | `sma50_fall`, 10% | PASS | 22.9% / −42.3% / 0.65 | 21.6% / −37.4% / 0.66 | 21.6% / −37.9% / 0.65 |
| India | `momentum_baseline` | `sma50_fall`, 20% | PASS | 18.9% / −45.5% / 0.53 | 17.1% / −36.3% / 0.54 | 17.1% / −37.3% / 0.53 |
| India | `dual_momentum` | none qualified | — | | | |
| US | `value_ranking` | `sma50_fall`, 20% | FAIL (CAGR) | 15.1% / −29.0% / 0.53 | 13.0% / −22.4% / 0.54 | 13.3% / −23.5% / 0.53 |
| US | `quality_momentum`, `momentum_dual_combo`, `dual_momentum`, `masonson_tqqq` | none qualified | — | | | |

## What it means

A short that is really short in declines does hedge — the correlation is strongly negative and the three India passes
are honest passes of a rule written first. What it buys over simply holding less of the book is about one point of
drawdown and a hundredth or two of Sharpe. That is within what a different four years could undo, and the instrument
problem (lot size, no inverse ETF) makes it impractical at the ₹5L book's size. **Recommendation: no change to the ₹5L
book.** If the account grows to where one Nifty lot is a sensible hedge, this is the version to register as a strategy
and paper-trade first.

## Caveats

- A research test, not a registered strategy: the sleeve is computed from the benchmark's closes, point in time, and
  cut by date; it has no version or verify-ledger entry.
- The signal was chosen from three on 2013–2021 — the same signal won on every book, which is reassuring but still a
  choice.
- Futures roll costs and the basis are not modelled beyond the 5 bps switch cost.

## Full tables

_Computed 2026-11-17 from stored full-period runs and the benchmarks' stored closes._

### US — short SPY while its trend is down

| Signal | Window | CAGR | Max DD | Sharpe over cash | Sessions short | Short on decline sessions |
|---|---|---|---|---|---|---|
| `sma200` | 2013–2021 | -5.3% | -41.8% | -0.47 | 12% | 49% |
| `sma200` | 2022 on | -1.6% | -18.0% | -0.36 | 24% | 78% |
| `sma50_fall` | 2013–2021 | -3.6% | -29.1% | -0.32 | 13% | 43% |
| `sma50_fall` | 2022 on | 2.0% | -21.2% | -0.09 | 19% | 62% |
| `tsmom12` | 2013–2021 | -3.9% | -32.8% | -0.66 | 11% | 23% |
| `tsmom12` | 2022 on | 2.3% | -15.4% | -0.12 | 22% | 50% |

#### US — `quality_momentum`: no (signal, weight) qualified in-sample; nothing to verify.

#### US — `momentum_dual_combo`: no (signal, weight) qualified in-sample; nothing to verify.

#### US — `dual_momentum`: no (signal, weight) qualified in-sample; nothing to verify.

#### US — `value_ranking` + `index short (sma50_fall)` (monthly correlation -0.59)

**In-sample choice: 20% sleeve. Out-of-sample: FAIL** (failed: cagr).

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 9.5% | -58.8% | 0.44 | 27.8% |
| 90% book + 10% sleeve | 8.5% | -51.7% | 0.44 | 23.9% |
| 80% book + 20% sleeve ← | 7.5% | -45.6% | 0.43 | 20.4% |
| 70% book + 30% sleeve | 6.4% | -39.7% | 0.41 | 17.1% |
| *80% book + 20% cash* | 8.2% | -48.7% | 0.44 | 21.9% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 15.1% | -29.0% | 0.53 | 25.0% |
| 90% book + 10% sleeve | 14.1% | -25.7% | 0.54 | 21.8% |
| 80% book + 20% sleeve ← | 13.0% | -22.4% | 0.54 | 18.7% |
| 70% book + 30% sleeve | 11.9% | -19.2% | 0.54 | 15.7% |
| *80% book + 20% cash* | 13.3% | -23.5% | 0.53 | 19.9% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 11.4% | -58.8% | 0.47 | 26.9% |
| 90% book + 10% sleeve | 10.5% | -51.7% | 0.47 | 23.2% |
| 80% book + 20% sleeve ← | 9.4% | -45.6% | 0.46 | 19.8% |
| 70% book + 30% sleeve | 8.3% | -39.7% | 0.45 | 16.6% |
| *80% book + 20% cash* | 9.9% | -48.7% | 0.47 | 21.2% |

#### US — `masonson_tqqq`: no (signal, weight) qualified in-sample; nothing to verify.

### INDIA — short NIFTY500 while its trend is down

| Signal | Window | CAGR | Max DD | Sharpe over cash | Sessions short | Short on decline sessions |
|---|---|---|---|---|---|---|
| `sma200` | 2013–2021 | 0.9% | -31.0% | -0.44 | 25% | 40% |
| `sma200` | 2022 on | -0.4% | -13.8% | -0.66 | 27% | 38% |
| `sma50_fall` | 2013–2021 | 5.5% | -23.3% | -0.07 | 20% | 44% |
| `sma50_fall` | 2022 on | 4.6% | -9.8% | -0.14 | 27% | 60% |
| `tsmom12` | 2013–2021 | -2.1% | -41.9% | -1.02 | 22% | 10% |
| `tsmom12` | 2022 on | -3.6% | -18.3% | -1.94 | 16% | 0% |

#### INDIA — `momentum_dual_combo` + `index short (sma50_fall)` (monthly correlation -0.43)

**In-sample choice: 10% sleeve. Out-of-sample: PASS**.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 20.7% | -28.3% | 0.78 | 16.9% |
| 90% book + 10% sleeve ← | 19.4% | -21.8% | 0.80 | 14.7% |
| 80% book + 20% sleeve | 18.0% | -19.7% | 0.81 | 12.7% |
| 70% book + 30% sleeve | 16.6% | -18.1% | 0.81 | 11.0% |
| *90% book + 10% cash* | 19.4% | -24.9% | 0.78 | 15.2% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 22.5% | -23.6% | 0.82 | 18.8% |
| 90% book + 10% sleeve ← | 20.9% | -20.1% | 0.84 | 16.4% |
| 80% book + 20% sleeve | 19.3% | -17.2% | 0.85 | 14.1% |
| 70% book + 30% sleeve | 17.6% | -14.3% | 0.87 | 12.0% |
| *90% book + 10% cash* | 21.0% | -21.1% | 0.82 | 16.9% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 21.3% | -28.3% | 0.80 | 17.6% |
| 90% book + 10% sleeve ← | 19.9% | -21.8% | 0.81 | 15.3% |
| 80% book + 20% sleeve | 18.4% | -19.7% | 0.83 | 13.2% |
| 70% book + 30% sleeve | 16.9% | -18.1% | 0.83 | 11.3% |
| *90% book + 10% cash* | 19.9% | -24.9% | 0.79 | 15.8% |

#### INDIA — `dual_momentum`: no (signal, weight) qualified in-sample; nothing to verify.

#### INDIA — `quality_momentum` + `index short (sma50_fall)` (monthly correlation -0.45)

**In-sample choice: 10% sleeve. Out-of-sample: PASS**.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 8.5% | -30.9% | 0.17 | 14.0% |
| 90% book + 10% sleeve ← | 8.4% | -24.1% | 0.18 | 11.8% |
| 80% book + 20% sleeve | 8.3% | -17.1% | 0.17 | 10.0% |
| 70% book + 30% sleeve | 8.1% | -13.0% | 0.17 | 8.4% |
| *90% book + 10% cash* | 8.5% | -28.0% | 0.17 | 12.5% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 22.9% | -42.3% | 0.65 | 29.0% |
| 90% book + 10% sleeve ← | 21.6% | -37.4% | 0.66 | 25.6% |
| 80% book + 20% sleeve | 20.2% | -32.3% | 0.67 | 22.2% |
| 70% book + 30% sleeve | 18.6% | -27.2% | 0.68 | 19.0% |
| *90% book + 10% cash* | 21.6% | -37.9% | 0.65 | 26.1% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 13.4% | -42.3% | 0.40 | 20.6% |
| 90% book + 10% sleeve ← | 12.9% | -37.4% | 0.41 | 17.9% |
| 80% book + 20% sleeve | 12.3% | -32.3% | 0.41 | 15.4% |
| 70% book + 30% sleeve | 11.7% | -27.2% | 0.42 | 13.1% |
| *90% book + 10% cash* | 12.9% | -37.9% | 0.40 | 18.5% |

#### INDIA — `momentum_baseline` + `index short (sma50_fall)` (monthly correlation -0.55)

**In-sample choice: 20% sleeve. Out-of-sample: PASS**.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 16.7% | -54.4% | 0.48 | 25.0% |
| 90% book + 10% sleeve | 16.1% | -46.9% | 0.49 | 21.7% |
| 80% book + 20% sleeve ← | 15.4% | -38.9% | 0.51 | 18.6% |
| 70% book + 30% sleeve | 14.5% | -31.0% | 0.52 | 15.7% |
| *80% book + 20% cash* | 15.3% | -43.7% | 0.48 | 19.9% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 18.9% | -45.5% | 0.53 | 30.0% |
| 90% book + 10% sleeve | 18.1% | -41.0% | 0.54 | 26.4% |
| 80% book + 20% sleeve ← | 17.1% | -36.3% | 0.54 | 22.9% |
| 70% book + 30% sleeve | 16.1% | -31.5% | 0.55 | 19.6% |
| *80% book + 20% cash* | 17.1% | -37.3% | 0.53 | 23.8% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 17.4% | -54.4% | 0.50 | 26.8% |
| 90% book + 10% sleeve | 16.8% | -46.9% | 0.51 | 23.5% |
| 80% book + 20% sleeve ← | 16.0% | -38.9% | 0.52 | 20.2% |
| 70% book + 30% sleeve | 15.0% | -31.5% | 0.53 | 17.2% |
| *80% book + 20% cash* | 15.9% | -43.7% | 0.50 | 21.3% |
