# Does group strength help? — leaders in leading groups

*Generated 2026-10-08 by `python -m swing_screener.screens.group_research`; re-run it to refresh.*

**Question.** Are stocks in strong peer groups (sub-industry, else industry group, rated RS 80+ on the Sectors page's scale) better buys than the same kind of stock in a weak group (RS below 50)? Does being one of the top 3 in the group add to that?

**Method.** On each month-end of the last five years, using only data up to that day — the month-end stock snapshot, with group RS rebuilt point in time from prices (it matches the Sectors page exactly on the US and to a Spearman 0.995 on India) — each set below is formed and its average return to the month-end 1, 3 and 6 months later measured; *excess* is that minus the average tradable stock's. Paired comparisons take the difference of two sets' 1-month returns on each month-end where both have at least 3 stocks: its mean, t-statistic and the share of months won. 3- and 6-month windows overlap, so their differences are shown for context without a t-statistic.

## US

### Every set

| Set | Stocks per month-end | Excess 1M | Excess 3M | Excess 6M | Hit rate 6M | Months won 6M |
|---|---:|---:|---:|---:|---:|---:|
| All tradable | 1755 | +0.00% | +0.00% | +0.00% | 50% | 0% |
| Tradable · strong group | 301 | +0.48% | +1.04% | +3.13% | 52% | 79% |
| Tradable · middling group | 555 | +0.15% | +0.46% | -0.02% | 50% | 46% |
| Tradable · weak group | 889 | -0.19% | -0.45% | -0.73% | 49% | 34% |
| Stage 2 | 336 | +0.46% | +0.63% | +2.53% | 53% | 75% |
| Stage 2 · strong group | 118 | +0.79% | +1.18% | +5.02% | 54% | 75% |
| Stage 2 · weak group | 86 | +0.33% | -0.15% | +1.43% | 54% | 68% |
| Stage 2 · top 3 in group | 206 | +0.54% | +0.64% | +2.75% | 53% | 68% |
| Stage 2 · not top 3 | 124 | +0.22% | +0.52% | +1.80% | 54% | 73% |
| Strong stocks in leading groups | 160 | +0.59% | +0.80% | +3.94% | 52% | 77% |
| Uptrend | 320 | +0.37% | +0.62% | +2.01% | 54% | 79% |
| Uptrend · strong group | 97 | +0.49% | +0.57% | +3.76% | 53% | 71% |
| Uptrend · weak group | 97 | +0.60% | +0.65% | +2.09% | 55% | 66% |
| Tradable · strong industry group | 342 | +0.52% | +1.45% | +4.16% | 54% | 80% |
| Sub-industry peers · strong sub-industry | 75 | +1.57% | +4.52% | +10.00% | 57% | 82% |
| Sub-industry peers · strong industry group | 116 | +1.58% | +4.98% | +11.45% | 60% | 84% |

### Head to head

| Comparison | A | B | Months | A − B, 1M | t (1M) | A won (1M) | A − B, 3M | A − B, 6M |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Group strength alone | Tradable · strong group | Tradable · weak group | 61 | +0.67% | 1.5 | 49% | +1.49% | +3.86% |
| Within Stage 2: strong vs weak group | Stage 2 · strong group | Stage 2 · weak group | 61 | +0.46% | 0.9 | 44% | +1.33% | +3.59% |
| Within Stage 2: requiring a strong group | Stage 2 · strong group | Stage 2 | 61 | +0.33% | 1.2 | 49% | +0.55% | +2.48% |
| Within Stage 2: leader of its group or not | Stage 2 · top 3 in group | Stage 2 · not top 3 | 61 | +0.32% | 0.8 | 54% | +0.13% | +0.95% |
| The preset vs Stage 2 | Strong stocks in leading groups | Stage 2 | 61 | +0.13% | 0.5 | 49% | +0.17% | +1.41% |
| Within the established uptrend: strong vs weak group | Uptrend · strong group | Uptrend · weak group | 61 | -0.11% | -0.2 | 43% | -0.08% | +1.66% |
| Sub-industry vs industry group (same stocks) | Sub-industry peers · strong sub-industry | Sub-industry peers · strong industry group | 61 | -0.01% | -0.0 | 54% | -0.46% | -1.45% |

## India

### Every set

| Set | Stocks per month-end | Excess 1M | Excess 3M | Excess 6M | Hit rate 6M | Months won 6M |
|---|---:|---:|---:|---:|---:|---:|
| All tradable | 303 | +0.00% | +0.00% | +0.00% | 50% | 0% |
| Tradable · strong group | 68 | +0.85% | +1.50% | +2.53% | 51% | 54% |
| Tradable · middling group | 93 | +0.24% | +0.52% | +0.67% | 51% | 61% |
| Tradable · weak group | 126 | -0.51% | -1.09% | -1.65% | 48% | 43% |
| Stage 2 | 71 | +0.93% | +1.84% | +2.67% | 52% | 62% |
| Stage 2 · strong group | 31 | +1.39% | +2.17% | +2.88% | 51% | 46% |
| Stage 2 · weak group | 12 | -0.04% | +0.52% | +1.96% | 50% | 54% |
| Stage 2 · top 3 in group | 49 | +1.32% | +1.94% | +2.97% | 51% | 62% |
| Stage 2 · not top 3 | 10 | +0.85% | +2.07% | +3.62% | 53% | 50% |
| Strong stocks in leading groups | 39 | +1.20% | +2.57% | +3.63% | 51% | 48% |
| Uptrend | 77 | +0.42% | +0.80% | +1.38% | 53% | 61% |
| Uptrend · strong group | 27 | +1.11% | +1.54% | +1.55% | 53% | 46% |
| Uptrend · weak group | 21 | +0.89% | +0.07% | +0.90% | 51% | 50% |
| Tradable · strong industry group | 63 | +0.63% | +1.47% | +1.78% | 50% | 48% |
| Sub-industry peers · strong sub-industry | 31 | +0.72% | +0.51% | +2.71% | 49% | 48% |
| Sub-industry peers · strong industry group | 28 | +0.24% | +0.40% | +2.91% | 45% | 37% |

### Head to head

| Comparison | A | B | Months | A − B, 1M | t (1M) | A won (1M) | A − B, 3M | A − B, 6M |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Group strength alone | Tradable · strong group | Tradable · weak group | 61 | +1.36% | 2.9 | 62% | +2.58% | +4.18% |
| Within Stage 2: strong vs weak group | Stage 2 · strong group | Stage 2 · weak group | 57 | +1.16% | 1.7 | 63% | +0.62% | -0.40% |
| Within Stage 2: requiring a strong group | Stage 2 · strong group | Stage 2 | 61 | +0.46% | 1.6 | 57% | +0.34% | +0.21% |
| Within Stage 2: leader of its group or not | Stage 2 · top 3 in group | Stage 2 · not top 3 | 37 | +0.17% | 0.2 | 51% | -0.30% | -0.41% |
| The preset vs Stage 2 | Strong stocks in leading groups | Stage 2 | 61 | +0.27% | 0.8 | 54% | +0.73% | +0.95% |
| Within the established uptrend: strong vs weak group | Uptrend · strong group | Uptrend · weak group | 56 | +1.25% | 1.8 | 59% | +2.14% | +1.86% |
| Sub-industry vs industry group (same stocks) | Sub-industry peers · strong sub-industry | Sub-industry peers · strong industry group | 57 | +0.27% | 0.5 | 53% | +0.66% | +0.77% |

## How to read it

- A t-statistic above about 2 (in absolute value) on the 1-month difference is unlikely to be luck; between 1 and 2 is suggestive; below 1 is noise. Five years is about 60 months — a modest sample, and one market regime.
- *Hit rate*: share of the set's stocks beating the median tradable stock. *Months won*: share of month-ends the set beat the average tradable stock.

## Caveats

- **Survivorship**: stocks delisted since are missing; it flatters every set, the weakest most.
- **Classification look-ahead**: today's industry groups and sub-industries are used for every past date.
- **No costs, equal weight, close to close**: a screen is not a strategy; a strategy adds entries, stops and exits, judged by its own backtest.
- **Overlap**: 3- and 6-month windows overlap month to month, so those columns are not independent observations.
