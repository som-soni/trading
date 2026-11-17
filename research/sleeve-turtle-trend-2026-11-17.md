# Hedge sleeves beside the long books: turtle_trend and stage4_shorts (2026-11-17)

Follow-up to [Strategies by market regime](strategy-regimes-2026-11-17.md), where `turtle_trend` was the one book that
made money in the US declines of 2018, 2020 and 2022. Question: does holding a slice of it beside a long book make the
account better? Produced by `swing_screener/backtesting/sleeve_blend.py` from stored full-period runs (monthly
rebalance to the split, money moved charged at 20 bps a side for the stock book and 5 bps for the ETF sleeve; an India
book holds the sleeve in rupees through USD/INR).

**In short**

- **It fails.** Eight of nine books chose a weight in-sample; seven of those failed out-of-sample, and the one pass
  (India `momentum_baseline`) did no better than holding the same 20% in cash.
- **The sleeve bought nothing cash would not.** From 2022 on `turtle_trend` alone made 1.2% a year with a −42%
  drawdown and a Sharpe of about zero. Beside each book its effect matched holding less of the book.
- **In-sample it did help** (India `momentum_dual_combo`, 20%: drawdown −17.9% vs −22.3% for 20% in cash) — the 2020
  crash. That edge did not repeat in 2022–2026.
- **For the ₹5L book (`momentum_dual_combo`, India):** 10% in the sleeve from 2022 on: 21.2% CAGR, −21.3% drawdown;
  10% in cash: 21.0%, −21.1%; the book alone: 22.5%, −23.6%. No change recommended.

## The test (written before any blend was computed)

1. **Choose the weight in-sample** (2013–2021) among 10%, 20%, 30%: of the weights that cut the max drawdown by at
   least 20% (relative) while giving up at most 2 points of CAGR, the one with the highest Sharpe over cash.
2. **Judge it once out-of-sample** (2022 → 2026-11-13): pass if Sharpe ≥ the book's, drawdown shallower, CAGR no more
   than 2 points lower.

The cash row was added after the first results, as a comparison only — not part of the rule.

## Out-of-sample, 2022 on (the chosen weight)

| Market | Book | Chosen | Verdict | Book alone: CAGR / DD / Sharpe | With the sleeve | Same weight in cash |
|---|---|---|---|---|---|---|
| US | `quality_momentum` | 20% | FAIL | 26.9% / −41.8% / 0.66 | 23.4% / −35.7% / 0.64 | 23.9% / −35.0% / 0.65 |
| US | `momentum_dual_combo` | 30% | FAIL | 12.6% / −30.6% / 0.45 | 9.8% / −24.9% / 0.38 | 10.5% / −21.9% / 0.44 |
| US | `dual_momentum` | 30% | FAIL | 16.8% / −31.5% / 0.67 | 12.6% / −19.2% / 0.55 | 13.2% / −22.9% / 0.66 |
| US | `value_ranking` | 30% | FAIL | 15.1% / −29.0% / 0.53 | 11.6% / −22.6% / 0.48 | 12.3% / −20.7% / 0.53 |
| US | `masonson_tqqq` | none | — | 19.2% / −36.4% / 0.55 | — | — |
| India | `momentum_dual_combo` | 10% | FAIL | 22.5% / −23.6% / 0.82 | 21.2% / −21.3% / 0.81 | 21.0% / −21.1% / 0.82 |
| India | `dual_momentum` | none | — | 19.4% / −27.5% / 0.63 | — | — |
| India | `quality_momentum` | 30% | FAIL | 22.9% / −42.3% / 0.65 | 19.4% / −32.1% / 0.65 | 18.7% / −28.5% / 0.66 |
| India | `momentum_baseline` | 20% | PASS | 18.9% / −45.5% / 0.53 | 17.6% / −39.8% / 0.54 | 17.1% / −37.3% / 0.53 |

Monthly correlations with the books were low (−0.16 to +0.23), as a hedge needs — but a low correlation is worth only
as much as the sleeve's own return, and from 2022 that was about zero.

## Caveats

- **The sleeve is understated by the cash rate.** The `turtle_trend` runner credits no interest on idle collateral,
  which a real futures or ETF account earns (4–5% in the US in 2023–25). Credited, the sleeve would sit roughly where
  cash does plus its 1.2% — still not a reason to hold it.
- The windows are cut from one full-period run per strategy, so positions open on 2021-12-31 carry across.
- One configuration of `turtle_trend` (System 2, 1% risk, v1.1). A different one — the time-series momentum variant,
  more assets — is a separate test and would need its own pre-set rule.
- The judgement here is on 2022–2026, which contained one bear market (2022) in which `turtle_trend` did well (+16% in
  the decline) and still lost overall; one more crash could flip it. The evidence for trend following is decades
  long; this sample is four years.


## Second sleeve: `stage4_shorts`

Same test, same pre-set rule, run after the turtle results (`--sleeve stage4_shorts --sleeve-cost-bps 20`: a
stock book's cost). An India book takes India's own `stage4_shorts` run; a US book the US run.

**It fails too, and for a plainer reason: the sleeve is almost all cash.**

| Market | Window | `stage4_shorts` alone: CAGR / max DD / Sharpe over cash | Sessions holding a short |
|---|---|---|---|
| US | 2013–2021 | 0.0% / −3.8% / −0.40 | 7% |
| US | 2022 on | 3.5% / −5.1% / −0.11 | 31% |
| India | 2013–2021 | 6.9% / −0.4% / −0.47 | 0.2% |
| India | 2022 on | 6.3% / −0.6% / −0.27 | 4% |

- **US:** no book chose a weight in-sample — 2013–2021 the sleeve earned nothing (US cash paid under 1%), so it
  only diluted the book.
- **India:** only `quality_momentum` chose one (30%), and out-of-sample the blend was identical to 30% in cash
  (18.7% / −28.6% vs 18.7% / −28.5%). The India "returns" are the 6.5% cash rate on money that almost never traded.
- So the earlier regime note's "positive in every India decline" was the cash rate, corrected there. A short book
  that trades this rarely is not a hedge; a real test of a short sleeve needs a short strategy that is short often
  enough to matter in a decline.

Full tables for this sleeve are at the end of the note.

## Full tables — turtle_trend

_Computed 2026-11-17 from stored full-period runs; sleeve `turtle_trend` 2013-01-03 → 2026-11-13._

#### US — `quality_momentum` + `turtle_trend` (monthly correlation +0.07)

**In-sample choice: 20% sleeve. Out-of-sample: FAIL** (failed: sharpe, cagr).

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 15.5% | -42.7% | 0.59 | 32.5% |
| 90% book + 10% sleeve | 14.6% | -36.6% | 0.59 | 28.9% |
| 80% book + 20% sleeve ← | 13.6% | -33.9% | 0.60 | 25.7% |
| 70% book + 30% sleeve | 12.5% | -31.0% | 0.60 | 22.8% |
| *80% book + 20% cash* | 13.0% | -34.8% | 0.58 | 25.8% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 26.9% | -41.8% | 0.66 | 47.0% |
| 90% book + 10% sleeve | 25.2% | -38.8% | 0.65 | 42.4% |
| 80% book + 20% sleeve ← | 23.4% | -35.7% | 0.64 | 38.0% |
| 70% book + 30% sleeve | 21.3% | -33.0% | 0.62 | 33.8% |
| *80% book + 20% cash* | 23.9% | -35.0% | 0.65 | 37.4% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 19.3% | -45.2% | 0.61 | 38.2% |
| 90% book + 10% sleeve | 18.2% | -41.9% | 0.61 | 34.3% |
| 80% book + 20% sleeve ← | 16.9% | -38.6% | 0.61 | 30.6% |
| 70% book + 30% sleeve | 15.5% | -35.3% | 0.60 | 27.1% |
| *80% book + 20% cash* | 16.7% | -36.7% | 0.60 | 30.4% |

#### US — `momentum_dual_combo` + `turtle_trend` (monthly correlation +0.14)

**In-sample choice: 30% sleeve. Out-of-sample: FAIL** (failed: sharpe, cagr).

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 8.3% | -38.4% | 0.45 | 21.7% |
| 90% book + 10% sleeve | 8.0% | -32.3% | 0.46 | 19.4% |
| 80% book + 20% sleeve | 7.6% | -26.8% | 0.47 | 17.4% |
| 70% book + 30% sleeve ← | 7.1% | -25.5% | 0.48 | 15.7% |
| *70% book + 30% cash* | 6.3% | -27.3% | 0.44 | 15.1% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 12.6% | -30.6% | 0.45 | 24.2% |
| 90% book + 10% sleeve | 11.8% | -28.6% | 0.43 | 22.3% |
| 80% book + 20% sleeve | 10.8% | -26.7% | 0.41 | 20.6% |
| 70% book + 30% sleeve ← | 9.8% | -24.9% | 0.38 | 19.3% |
| *70% book + 30% cash* | 10.5% | -21.9% | 0.44 | 16.9% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 9.8% | -38.4% | 0.45 | 22.6% |
| 90% book + 10% sleeve | 9.3% | -32.3% | 0.45 | 20.4% |
| 80% book + 20% sleeve | 8.7% | -26.8% | 0.45 | 18.6% |
| 70% book + 30% sleeve ← | 8.0% | -25.5% | 0.43 | 17.1% |
| *70% book + 30% cash* | 7.7% | -27.3% | 0.44 | 15.7% |

#### US — `dual_momentum` + `turtle_trend` (monthly correlation +0.18)

**In-sample choice: 30% sleeve. Out-of-sample: FAIL** (failed: sharpe, cagr).

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 8.7% | -36.1% | 0.51 | 18.5% |
| 90% book + 10% sleeve | 8.2% | -33.7% | 0.53 | 16.4% |
| 80% book + 20% sleeve | 7.8% | -31.2% | 0.54 | 14.8% |
| 70% book + 30% sleeve ← | 7.2% | -28.7% | 0.54 | 13.6% |
| *70% book + 30% cash* | 6.4% | -26.6% | 0.50 | 12.8% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 16.8% | -31.5% | 0.67 | 20.6% |
| 90% book + 10% sleeve | 15.4% | -27.3% | 0.64 | 19.2% |
| 80% book + 20% sleeve | 14.0% | -23.2% | 0.60 | 18.1% |
| 70% book + 30% sleeve ← | 12.6% | -19.2% | 0.55 | 17.4% |
| *70% book + 30% cash* | 13.2% | -22.9% | 0.66 | 14.5% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 11.4% | -36.1% | 0.57 | 19.2% |
| 90% book + 10% sleeve | 10.7% | -33.7% | 0.57 | 17.4% |
| 80% book + 20% sleeve | 9.9% | -31.2% | 0.56 | 16.0% |
| 70% book + 30% sleeve ← | 9.1% | -28.7% | 0.54 | 15.0% |
| *70% book + 30% cash* | 8.7% | -26.6% | 0.56 | 13.4% |

#### US — `value_ranking` + `turtle_trend` (monthly correlation -0.13)

**In-sample choice: 30% sleeve. Out-of-sample: FAIL** (failed: sharpe, cagr).

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 9.5% | -58.8% | 0.44 | 27.8% |
| 90% book + 10% sleeve | 9.3% | -51.7% | 0.46 | 24.3% |
| 80% book + 20% sleeve | 9.1% | -44.6% | 0.49 | 21.2% |
| 70% book + 30% sleeve ← | 8.6% | -38.1% | 0.51 | 18.5% |
| *70% book + 30% cash* | 7.4% | -43.4% | 0.44 | 19.0% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 15.1% | -29.0% | 0.53 | 25.0% |
| 90% book + 10% sleeve | 14.0% | -25.5% | 0.52 | 22.3% |
| 80% book + 20% sleeve | 12.9% | -24.1% | 0.51 | 19.9% |
| 70% book + 30% sleeve ← | 11.6% | -22.6% | 0.48 | 18.0% |
| *70% book + 30% cash* | 12.3% | -20.7% | 0.53 | 17.4% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 11.4% | -58.8% | 0.47 | 26.9% |
| 90% book + 10% sleeve | 11.0% | -51.7% | 0.48 | 23.6% |
| 80% book + 20% sleeve | 10.4% | -44.6% | 0.49 | 20.7% |
| 70% book + 30% sleeve ← | 9.7% | -38.1% | 0.50 | 18.4% |
| *70% book + 30% cash* | 9.1% | -43.4% | 0.47 | 18.4% |

#### US — `masonson_tqqq` + `turtle_trend` (monthly correlation +0.18)

**In-sample choice: none.** No weight cut the drawdown by 20% while giving up at most 2.0 points of CAGR, so there is nothing to verify.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 21.1% | -55.5% | 0.71 | 34.5% |
| 90% book + 10% sleeve | 19.8% | -51.5% | 0.71 | 31.7% |
| 80% book + 20% sleeve | 18.3% | -47.4% | 0.71 | 29.0% |
| 70% book + 30% sleeve | 16.7% | -43.0% | 0.69 | 26.5% |
| *80% book + 20% cash* | 17.9% | -47.0% | 0.71 | 27.7% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 19.2% | -36.4% | 0.55 | 37.4% |
| 90% book + 10% sleeve | 18.0% | -32.6% | 0.54 | 34.2% |
| 80% book + 20% sleeve | 16.6% | -28.7% | 0.52 | 31.3% |
| 70% book + 30% sleeve | 15.1% | -24.9% | 0.50 | 28.5% |
| *80% book + 20% cash* | 17.1% | -30.0% | 0.55 | 30.0% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 20.4% | -55.5% | 0.65 | 35.5% |
| 90% book + 10% sleeve | 19.1% | -51.5% | 0.65 | 32.6% |
| 80% book + 20% sleeve | 17.7% | -47.4% | 0.64 | 29.8% |
| 70% book + 30% sleeve | 16.2% | -43.0% | 0.62 | 27.2% |
| *80% book + 20% cash* | 17.6% | -47.0% | 0.65 | 28.6% |

#### INDIA — `momentum_dual_combo` + `turtle_trend` (monthly correlation -0.02)

**In-sample choice: 10% sleeve. Out-of-sample: FAIL** (failed: sharpe).

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 20.7% | -28.3% | 0.78 | 16.9% |
| 90% book + 10% sleeve ← | 19.5% | -21.9% | 0.79 | 15.2% |
| 80% book + 20% sleeve | 18.3% | -17.9% | 0.78 | 13.8% |
| 70% book + 30% sleeve | 17.0% | -15.4% | 0.74 | 12.9% |
| *90% book + 10% cash* | 19.4% | -24.9% | 0.78 | 15.2% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 22.5% | -23.6% | 0.82 | 18.8% |
| 90% book + 10% sleeve ← | 21.2% | -21.3% | 0.81 | 17.2% |
| 80% book + 20% sleeve | 19.7% | -19.0% | 0.79 | 16.1% |
| 70% book + 30% sleeve | 18.2% | -18.8% | 0.74 | 15.4% |
| *90% book + 10% cash* | 21.0% | -21.1% | 0.82 | 16.9% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 21.3% | -28.3% | 0.80 | 17.6% |
| 90% book + 10% sleeve ← | 20.1% | -21.9% | 0.80 | 15.9% |
| 80% book + 20% sleeve | 18.8% | -19.0% | 0.78 | 14.7% |
| 70% book + 30% sleeve | 17.4% | -18.8% | 0.74 | 13.8% |
| *90% book + 10% cash* | 19.9% | -24.9% | 0.79 | 15.8% |

#### INDIA — `dual_momentum` + `turtle_trend` (monthly correlation +0.23)

**In-sample choice: none.** No weight cut the drawdown by 20% while giving up at most 2.0 points of CAGR, so there is nothing to verify.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 16.1% | -26.3% | 0.51 | 19.2% |
| 90% book + 10% sleeve | 15.3% | -24.1% | 0.51 | 17.3% |
| 80% book + 20% sleeve | 14.5% | -21.9% | 0.50 | 15.7% |
| 70% book + 30% sleeve | 13.7% | -19.7% | 0.48 | 14.5% |
| *80% book + 20% cash* | 14.4% | -21.1% | 0.50 | 15.4% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 19.4% | -27.5% | 0.63 | 21.3% |
| 90% book + 10% sleeve | 18.4% | -26.3% | 0.62 | 19.7% |
| 80% book + 20% sleeve | 17.2% | -25.2% | 0.60 | 18.4% |
| 70% book + 30% sleeve | 16.1% | -24.1% | 0.57 | 17.4% |
| *80% book + 20% cash* | 17.0% | -22.0% | 0.62 | 17.1% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 17.2% | -27.5% | 0.55 | 20.0% |
| 90% book + 10% sleeve | 16.4% | -26.3% | 0.55 | 18.2% |
| 80% book + 20% sleeve | 15.5% | -25.2% | 0.54 | 16.7% |
| 70% book + 30% sleeve | 14.5% | -24.1% | 0.51 | 15.6% |
| *80% book + 20% cash* | 15.3% | -22.0% | 0.55 | 16.0% |

#### INDIA — `quality_momentum` + `turtle_trend` (monthly correlation -0.16)

**In-sample choice: 30% sleeve. Out-of-sample: FAIL** (failed: cagr).

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 8.5% | -30.9% | 0.17 | 14.0% |
| 90% book + 10% sleeve | 8.6% | -24.9% | 0.19 | 12.4% |
| 80% book + 20% sleeve | 8.7% | -18.7% | 0.20 | 11.3% |
| 70% book + 30% sleeve ← | 8.6% | -13.7% | 0.20 | 10.9% |
| *70% book + 30% cash* | 8.3% | -21.9% | 0.17 | 9.7% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 22.9% | -42.3% | 0.65 | 29.0% |
| 90% book + 10% sleeve | 21.9% | -37.2% | 0.66 | 26.2% |
| 80% book + 20% sleeve | 20.7% | -34.4% | 0.66 | 23.7% |
| 70% book + 30% sleeve ← | 19.4% | -32.1% | 0.65 | 21.6% |
| *70% book + 30% cash* | 18.7% | -28.5% | 0.66 | 20.2% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 13.4% | -42.3% | 0.40 | 20.6% |
| 90% book + 10% sleeve | 13.1% | -37.2% | 0.41 | 18.5% |
| 80% book + 20% sleeve | 12.7% | -34.4% | 0.42 | 16.8% |
| 70% book + 30% sleeve ← | 12.3% | -32.1% | 0.41 | 15.5% |
| *70% book + 30% cash* | 11.8% | -28.5% | 0.40 | 14.3% |

#### INDIA — `momentum_baseline` + `turtle_trend` (monthly correlation -0.16)

**In-sample choice: 20% sleeve. Out-of-sample: PASS**.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 16.7% | -54.4% | 0.48 | 25.0% |
| 90% book + 10% sleeve | 16.2% | -46.8% | 0.49 | 22.3% |
| 80% book + 20% sleeve ← | 15.7% | -38.7% | 0.50 | 19.8% |
| 70% book + 30% sleeve | 15.0% | -30.9% | 0.50 | 17.8% |
| *80% book + 20% cash* | 15.3% | -43.7% | 0.48 | 19.9% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 18.9% | -45.5% | 0.53 | 30.0% |
| 90% book + 10% sleeve | 18.3% | -42.7% | 0.54 | 27.0% |
| 80% book + 20% sleeve ← | 17.6% | -39.8% | 0.54 | 24.3% |
| 70% book + 30% sleeve | 16.7% | -36.8% | 0.54 | 22.0% |
| *80% book + 20% cash* | 17.1% | -37.3% | 0.53 | 23.8% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 17.4% | -54.4% | 0.50 | 26.9% |
| 90% book + 10% sleeve | 17.0% | -46.8% | 0.51 | 24.0% |
| 80% book + 20% sleeve ← | 16.3% | -39.8% | 0.52 | 21.5% |
| 70% book + 30% sleeve | 15.6% | -36.8% | 0.51 | 19.4% |
| *80% book + 20% cash* | 15.9% | -43.7% | 0.50 | 21.3% |


## Full tables — stage4_shorts

_Computed 2026-11-17 from stored full-period runs; sleeve `stage4_shorts`._

_US sleeve: the us run, 2013-01-03 → 2026-11-13._

#### US — `quality_momentum` + `stage4_shorts` (monthly correlation -0.11)

**In-sample choice: none.** No weight cut the drawdown by 20% while giving up at most 2.0 points of CAGR, so there is nothing to verify.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 15.5% | -42.7% | 0.59 | 32.5% |
| 90% book + 10% sleeve | 14.2% | -38.8% | 0.58 | 29.1% |
| 80% book + 20% sleeve | 12.8% | -34.8% | 0.57 | 25.8% |
| 70% book + 30% sleeve | 11.4% | -30.6% | 0.56 | 22.5% |
| *80% book + 20% cash* | 12.9% | -34.8% | 0.58 | 25.8% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 26.9% | -41.8% | 0.66 | 47.0% |
| 90% book + 10% sleeve | 25.4% | -38.3% | 0.66 | 42.1% |
| 80% book + 20% sleeve | 23.7% | -34.5% | 0.65 | 37.2% |
| 70% book + 30% sleeve | 21.9% | -30.5% | 0.65 | 32.4% |
| *80% book + 20% cash* | 23.8% | -35.0% | 0.65 | 37.4% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 19.3% | -45.2% | 0.61 | 38.2% |
| 90% book + 10% sleeve | 18.0% | -41.1% | 0.60 | 34.2% |
| 80% book + 20% sleeve | 16.5% | -36.8% | 0.60 | 30.3% |
| 70% book + 30% sleeve | 14.9% | -32.5% | 0.59 | 26.4% |
| *80% book + 20% cash* | 16.6% | -36.8% | 0.60 | 30.4% |

#### US — `momentum_dual_combo` + `stage4_shorts` (monthly correlation -0.09)

**In-sample choice: none.** No weight cut the drawdown by 20% while giving up at most 2.0 points of CAGR, so there is nothing to verify.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 8.3% | -38.4% | 0.45 | 21.7% |
| 90% book + 10% sleeve | 7.6% | -34.9% | 0.44 | 19.5% |
| 80% book + 20% sleeve | 6.8% | -31.2% | 0.43 | 17.2% |
| 70% book + 30% sleeve | 6.1% | -27.5% | 0.43 | 15.0% |
| *80% book + 20% cash* | 7.0% | -31.2% | 0.44 | 17.3% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 12.6% | -30.6% | 0.45 | 24.2% |
| 90% book + 10% sleeve | 11.9% | -27.8% | 0.45 | 21.7% |
| 80% book + 20% sleeve | 11.1% | -24.9% | 0.44 | 19.2% |
| 70% book + 30% sleeve | 10.3% | -21.9% | 0.44 | 16.7% |
| *80% book + 20% cash* | 11.2% | -24.9% | 0.44 | 19.3% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 9.8% | -38.4% | 0.45 | 22.6% |
| 90% book + 10% sleeve | 9.1% | -34.9% | 0.44 | 20.3% |
| 80% book + 20% sleeve | 8.3% | -31.2% | 0.44 | 17.9% |
| 70% book + 30% sleeve | 7.5% | -27.5% | 0.43 | 15.6% |
| *80% book + 20% cash* | 8.4% | -31.2% | 0.44 | 18.0% |

#### US — `dual_momentum` + `stage4_shorts` (monthly correlation -0.01)

**In-sample choice: none.** No weight cut the drawdown by 20% while giving up at most 2.0 points of CAGR, so there is nothing to verify.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 8.7% | -36.1% | 0.51 | 18.5% |
| 90% book + 10% sleeve | 7.9% | -33.3% | 0.50 | 16.5% |
| 80% book + 20% sleeve | 7.1% | -30.3% | 0.50 | 14.6% |
| 70% book + 30% sleeve | 6.2% | -27.3% | 0.49 | 12.8% |
| *80% book + 20% cash* | 7.2% | -29.9% | 0.50 | 14.7% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 16.8% | -31.5% | 0.67 | 20.6% |
| 90% book + 10% sleeve | 15.6% | -28.5% | 0.66 | 18.5% |
| 80% book + 20% sleeve | 14.3% | -25.5% | 0.66 | 16.4% |
| 70% book + 30% sleeve | 13.0% | -22.5% | 0.65 | 14.3% |
| *80% book + 20% cash* | 14.4% | -25.8% | 0.66 | 16.5% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 11.4% | -36.1% | 0.57 | 19.2% |
| 90% book + 10% sleeve | 10.5% | -33.3% | 0.56 | 17.2% |
| 80% book + 20% sleeve | 9.5% | -30.3% | 0.56 | 15.3% |
| 70% book + 30% sleeve | 8.6% | -27.3% | 0.55 | 13.3% |
| *80% book + 20% cash* | 9.7% | -29.9% | 0.56 | 15.3% |

#### US — `value_ranking` + `stage4_shorts` (monthly correlation -0.28)

**In-sample choice: none.** No weight cut the drawdown by 20% while giving up at most 2.0 points of CAGR, so there is nothing to verify.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 9.5% | -58.8% | 0.44 | 27.8% |
| 90% book + 10% sleeve | 8.8% | -53.9% | 0.44 | 24.8% |
| 80% book + 20% sleeve | 8.1% | -48.8% | 0.44 | 21.8% |
| 70% book + 30% sleeve | 7.3% | -43.4% | 0.43 | 18.9% |
| *80% book + 20% cash* | 8.2% | -48.8% | 0.44 | 21.9% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 15.1% | -29.0% | 0.53 | 25.0% |
| 90% book + 10% sleeve | 14.2% | -26.1% | 0.53 | 22.3% |
| 80% book + 20% sleeve | 13.2% | -23.0% | 0.53 | 19.5% |
| 70% book + 30% sleeve | 12.2% | -19.9% | 0.53 | 16.9% |
| *80% book + 20% cash* | 13.3% | -23.5% | 0.53 | 19.9% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 11.4% | -58.8% | 0.47 | 26.9% |
| 90% book + 10% sleeve | 10.7% | -53.9% | 0.47 | 23.9% |
| 80% book + 20% sleeve | 9.8% | -48.8% | 0.47 | 21.0% |
| 70% book + 30% sleeve | 8.9% | -43.4% | 0.46 | 18.2% |
| *80% book + 20% cash* | 9.9% | -48.8% | 0.47 | 21.2% |

#### US — `masonson_tqqq` + `stage4_shorts` (monthly correlation -0.09)

**In-sample choice: none.** No weight cut the drawdown by 20% while giving up at most 2.0 points of CAGR, so there is nothing to verify.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 21.1% | -55.5% | 0.71 | 34.5% |
| 90% book + 10% sleeve | 19.5% | -51.5% | 0.71 | 31.1% |
| 80% book + 20% sleeve | 17.7% | -47.3% | 0.71 | 27.7% |
| 70% book + 30% sleeve | 15.8% | -42.9% | 0.70 | 24.3% |
| *80% book + 20% cash* | 17.8% | -47.1% | 0.71 | 27.7% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 19.2% | -36.4% | 0.55 | 37.4% |
| 90% book + 10% sleeve | 18.2% | -33.3% | 0.55 | 33.7% |
| 80% book + 20% sleeve | 17.0% | -30.0% | 0.54 | 30.0% |
| 70% book + 30% sleeve | 15.7% | -26.7% | 0.54 | 26.3% |
| *80% book + 20% cash* | 17.1% | -30.0% | 0.55 | 30.0% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 20.4% | -55.5% | 0.65 | 35.5% |
| 90% book + 10% sleeve | 19.0% | -51.5% | 0.65 | 32.0% |
| 80% book + 20% sleeve | 17.4% | -47.3% | 0.65 | 28.5% |
| 70% book + 30% sleeve | 15.8% | -42.9% | 0.64 | 25.0% |
| *80% book + 20% cash* | 17.6% | -47.1% | 0.65 | 28.6% |

_INDIA sleeve: its own india run, 2013-01-02 → 2026-11-12._

#### INDIA — `momentum_dual_combo` + `stage4_shorts` (monthly correlation -0.03)

**In-sample choice: none.** No weight cut the drawdown by 20% while giving up at most 2.0 points of CAGR, so there is nothing to verify.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 20.7% | -28.3% | 0.78 | 16.9% |
| 90% book + 10% sleeve | 19.4% | -24.9% | 0.78 | 15.2% |
| 80% book + 20% sleeve | 18.0% | -22.3% | 0.78 | 13.5% |
| 70% book + 30% sleeve | 16.7% | -19.6% | 0.78 | 11.8% |
| *80% book + 20% cash* | 18.0% | -22.3% | 0.78 | 13.5% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 22.5% | -23.6% | 0.82 | 18.8% |
| 90% book + 10% sleeve | 21.0% | -21.1% | 0.82 | 16.9% |
| 80% book + 20% sleeve | 19.4% | -18.8% | 0.82 | 15.0% |
| 70% book + 30% sleeve | 17.8% | -16.5% | 0.82 | 13.1% |
| *80% book + 20% cash* | 19.4% | -18.8% | 0.82 | 15.0% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 21.3% | -28.3% | 0.80 | 17.6% |
| 90% book + 10% sleeve | 19.9% | -24.9% | 0.79 | 15.8% |
| 80% book + 20% sleeve | 18.5% | -22.3% | 0.79 | 14.0% |
| 70% book + 30% sleeve | 17.1% | -19.6% | 0.79 | 12.3% |
| *80% book + 20% cash* | 18.5% | -22.3% | 0.79 | 14.0% |

#### INDIA — `dual_momentum` + `stage4_shorts` (monthly correlation -0.06)

**In-sample choice: none.** No weight cut the drawdown by 20% while giving up at most 2.0 points of CAGR, so there is nothing to verify.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 16.1% | -26.3% | 0.51 | 19.2% |
| 90% book + 10% sleeve | 15.2% | -23.7% | 0.51 | 17.3% |
| 80% book + 20% sleeve | 14.4% | -21.1% | 0.50 | 15.4% |
| 70% book + 30% sleeve | 13.5% | -18.5% | 0.50 | 13.4% |
| *80% book + 20% cash* | 14.4% | -21.1% | 0.50 | 15.4% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 19.4% | -27.5% | 0.63 | 21.3% |
| 90% book + 10% sleeve | 18.2% | -24.8% | 0.62 | 19.2% |
| 80% book + 20% sleeve | 16.9% | -22.0% | 0.62 | 17.1% |
| 70% book + 30% sleeve | 15.7% | -19.1% | 0.61 | 15.0% |
| *80% book + 20% cash* | 17.0% | -22.0% | 0.62 | 17.1% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 17.2% | -27.5% | 0.55 | 20.0% |
| 90% book + 10% sleeve | 16.3% | -24.8% | 0.55 | 18.0% |
| 80% book + 20% sleeve | 15.3% | -22.0% | 0.55 | 16.0% |
| 70% book + 30% sleeve | 14.3% | -19.1% | 0.54 | 14.0% |
| *80% book + 20% cash* | 15.3% | -22.0% | 0.55 | 16.0% |

#### INDIA — `quality_momentum` + `stage4_shorts` (monthly correlation -0.06)

**In-sample choice: 30% sleeve. Out-of-sample: FAIL** (failed: cagr).

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 8.5% | -30.9% | 0.17 | 14.0% |
| 90% book + 10% sleeve | 8.4% | -28.0% | 0.17 | 12.5% |
| 80% book + 20% sleeve | 8.3% | -24.9% | 0.17 | 11.1% |
| 70% book + 30% sleeve ← | 8.2% | -21.9% | 0.17 | 9.7% |
| *70% book + 30% cash* | 8.3% | -21.9% | 0.17 | 9.7% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 22.9% | -42.3% | 0.65 | 29.0% |
| 90% book + 10% sleeve | 21.6% | -37.9% | 0.65 | 26.0% |
| 80% book + 20% sleeve | 20.2% | -33.4% | 0.65 | 23.1% |
| 70% book + 30% sleeve ← | 18.7% | -28.6% | 0.65 | 20.2% |
| *70% book + 30% cash* | 18.7% | -28.5% | 0.65 | 20.2% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 13.4% | -42.3% | 0.40 | 20.6% |
| 90% book + 10% sleeve | 12.9% | -37.9% | 0.40 | 18.5% |
| 80% book + 20% sleeve | 12.3% | -33.4% | 0.40 | 16.4% |
| 70% book + 30% sleeve ← | 11.8% | -28.6% | 0.40 | 14.3% |
| *70% book + 30% cash* | 11.8% | -28.5% | 0.40 | 14.3% |

#### INDIA — `momentum_baseline` + `stage4_shorts` (monthly correlation +0.00)

**In-sample choice: none.** No weight cut the drawdown by 20% while giving up at most 2.0 points of CAGR, so there is nothing to verify.

*In-sample 2013-01-01 → 2021-12-31*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 16.7% | -54.4% | 0.48 | 25.0% |
| 90% book + 10% sleeve | 16.0% | -49.3% | 0.48 | 22.4% |
| 80% book + 20% sleeve | 15.2% | -43.8% | 0.48 | 19.9% |
| 70% book + 30% sleeve | 14.4% | -37.8% | 0.48 | 17.3% |
| *80% book + 20% cash* | 15.2% | -43.8% | 0.48 | 19.9% |

*Out-of-sample 2022-01-01 →*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 18.9% | -45.5% | 0.53 | 30.0% |
| 90% book + 10% sleeve | 18.0% | -41.5% | 0.53 | 26.9% |
| 80% book + 20% sleeve | 17.1% | -37.3% | 0.53 | 23.8% |
| 70% book + 30% sleeve | 16.0% | -32.9% | 0.53 | 20.8% |
| *80% book + 20% cash* | 17.1% | -37.3% | 0.53 | 23.8% |

*Full period (context)*

| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |
|---|---|---|---|---|
| Book alone | 17.4% | -54.4% | 0.50 | 26.8% |
| 90% book + 10% sleeve | 16.7% | -49.3% | 0.50 | 24.1% |
| 80% book + 20% sleeve | 15.9% | -43.8% | 0.50 | 21.3% |
| 70% book + 30% sleeve | 15.0% | -37.8% | 0.50 | 18.6% |
| *80% book + 20% cash* | 15.9% | -43.8% | 0.50 | 21.3% |
