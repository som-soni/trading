# Does group strength help? — leaders in leading groups

*Generated 2026-11-01 by `python -m swing_screener.screens.group_research`; re-run it to refresh.*

**Question.** Are stocks in strong peer groups (sub-industry, else industry group, rated RS 80+ on the Sectors page's scale) better buys than the same kind of stock in a weak group (RS below 50)? Does being one of the top 3 in the group add to that?

**Method.** On each month-end of the last five years, using only data up to that day — the month-end stock snapshot, with group RS rebuilt point in time from prices (it matches the Sectors page exactly on the US and to a Spearman 0.995 on India) — each set below is formed and its average return to the month-end 1, 3 and 6 months later measured; *excess* is that minus the average tradable stock's. Paired comparisons take the difference of two sets' 1-month returns on each month-end where both have at least 3 stocks: its mean, t-statistic and the share of months won. 3- and 6-month windows overlap, so their differences are shown for context without a t-statistic.

## US

### Every set

| Set | Stocks per month-end | Excess 1M | Excess 3M | Excess 6M | Hit rate 6M | Months won 6M |
|---|---:|---:|---:|---:|---:|---:|
| All tradable | 1724 | +0.00% | +0.00% | +0.00% | 50% | 0% |
| Tradable · strong group | 280 | +0.28% | +0.52% | +2.60% | 51% | 70% |
| Tradable · middling group | 551 | +0.17% | +0.50% | +0.23% | 51% | 55% |
| Tradable · weak group | 879 | -0.15% | -0.35% | -0.66% | 49% | 34% |
| Stage 2 | 336 | +0.27% | +0.21% | +1.90% | 53% | 70% |
| Stage 2 · strong group | 113 | +0.37% | +0.21% | +3.75% | 53% | 62% |
| Stage 2 · weak group | 86 | +0.15% | -0.27% | +1.17% | 54% | 66% |
| Stage 2 · top 3 in group | 209 | +0.29% | +0.13% | +1.99% | 52% | 66% |
| Stage 2 · not top 3 | 119 | +0.33% | +0.53% | +1.55% | 54% | 70% |
| Strong stocks in leading groups | 153 | +0.21% | +0.15% | +3.03% | 51% | 64% |
| Uptrend | 320 | +0.15% | +0.14% | +1.28% | 53% | 75% |
| Uptrend · strong group | 94 | +0.11% | -0.24% | +2.51% | 52% | 61% |
| Uptrend · weak group | 99 | +0.26% | +0.11% | +1.25% | 54% | 68% |
| Tradable · strong industry group | 355 | +0.42% | +1.25% | +3.57% | 52% | 70% |
| Sub-industry peers · strong sub-industry | 89 | +1.28% | +3.36% | +8.06% | 55% | 75% |
| Sub-industry peers · strong industry group | 164 | +1.10% | +3.52% | +7.98% | 56% | 75% |

### Head to head

| Comparison | A | B | Months | A − B, 1M | t (1M) | A won (1M) | A − B, 3M | A − B, 6M |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Group strength alone | Tradable · strong group | Tradable · weak group | 61 | +0.43% | 0.9 | 49% | +0.87% | +3.27% |
| Within Stage 2: strong vs weak group | Stage 2 · strong group | Stage 2 · weak group | 61 | +0.22% | 0.4 | 56% | +0.48% | +2.58% |
| Within Stage 2: requiring a strong group | Stage 2 · strong group | Stage 2 | 61 | +0.10% | 0.4 | 54% | +0.01% | +1.85% |
| Within Stage 2: leader of its group or not | Stage 2 · top 3 in group | Stage 2 · not top 3 | 61 | -0.04% | -0.1 | 56% | -0.40% | +0.44% |
| The preset vs Stage 2 | Strong stocks in leading groups | Stage 2 | 61 | -0.05% | -0.2 | 48% | -0.06% | +1.13% |
| Within the established uptrend: strong vs weak group | Uptrend · strong group | Uptrend · weak group | 60 | +0.03% | 0.0 | 50% | -0.35% | +1.24% |
| Sub-industry vs industry group (same stocks) | Sub-industry peers · strong sub-industry | Sub-industry peers · strong industry group | 61 | +0.18% | 0.5 | 51% | -0.16% | +0.09% |

## India

### Every set

| Set | Stocks per month-end | Excess 1M | Excess 3M | Excess 6M | Hit rate 6M | Months won 6M |
|---|---:|---:|---:|---:|---:|---:|
| All tradable | 303 | +0.00% | +0.00% | +0.00% | 50% | 0% |
| Tradable · strong group | 69 | +0.88% | +1.65% | +2.75% | 52% | 54% |
| Tradable · middling group | 92 | +0.22% | +0.39% | +0.32% | 51% | 61% |
| Tradable · weak group | 125 | -0.51% | -1.05% | -1.46% | 49% | 39% |
| Stage 2 | 71 | +0.93% | +1.84% | +2.67% | 52% | 62% |
| Stage 2 · strong group | 31 | +1.39% | +2.17% | +2.87% | 51% | 46% |
| Stage 2 · weak group | 12 | +0.15% | +0.78% | +2.25% | 50% | 54% |
| Stage 2 · top 3 in group | 49 | +1.32% | +1.94% | +2.97% | 51% | 62% |
| Stage 2 · not top 3 | 10 | +0.85% | +2.07% | +3.62% | 53% | 50% |
| Strong stocks in leading groups | 39 | +1.26% | +2.71% | +3.83% | 51% | 50% |
| Uptrend | 77 | +0.42% | +0.80% | +1.38% | 53% | 61% |
| Uptrend · strong group | 27 | +1.15% | +1.63% | +1.50% | 53% | 46% |
| Uptrend · weak group | 22 | +0.84% | +0.27% | +1.16% | 52% | 51% |
| Tradable · strong industry group | 64 | +0.75% | +1.60% | +1.88% | 50% | 50% |
| Sub-industry peers · strong sub-industry | 31 | +0.67% | +0.60% | +2.86% | 50% | 50% |
| Sub-industry peers · strong industry group | 27 | +0.37% | +0.27% | +2.44% | 45% | 36% |

### Head to head

| Comparison | A | B | Months | A − B, 1M | t (1M) | A won (1M) | A − B, 3M | A − B, 6M |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Group strength alone | Tradable · strong group | Tradable · weak group | 61 | +1.39% | 3.0 | 64% | +2.70% | +4.22% |
| Within Stage 2: strong vs weak group | Stage 2 · strong group | Stage 2 · weak group | 58 | +1.23% | 1.8 | 64% | +0.87% | -0.04% |
| Within Stage 2: requiring a strong group | Stage 2 · strong group | Stage 2 | 61 | +0.46% | 1.5 | 59% | +0.34% | +0.20% |
| Within Stage 2: leader of its group or not | Stage 2 · top 3 in group | Stage 2 · not top 3 | 37 | +0.17% | 0.2 | 51% | -0.30% | -0.41% |
| The preset vs Stage 2 | Strong stocks in leading groups | Stage 2 | 61 | +0.33% | 0.9 | 56% | +0.87% | +1.15% |
| Within the established uptrend: strong vs weak group | Uptrend · strong group | Uptrend · weak group | 56 | +1.28% | 1.9 | 62% | +2.16% | +1.55% |
| Sub-industry vs industry group (same stocks) | Sub-industry peers · strong sub-industry | Sub-industry peers · strong industry group | 58 | +0.43% | 0.8 | 53% | +0.77% | +1.09% |

## How to read it

- A t-statistic above about 2 (in absolute value) on the 1-month difference is unlikely to be luck; between 1 and 2 is suggestive; below 1 is noise. Five years is about 60 months — a modest sample, and one market regime.
- *Hit rate*: share of the set's stocks beating the median tradable stock. *Months won*: share of month-ends the set beat the average tradable stock.

## Caveats

- **Survivorship**: stocks delisted since are missing; it flatters every set, the weakest most.
- **Classification look-ahead**: today's industry groups and sub-industries are used for every past date.
- **No costs, equal weight, close to close**: a screen is not a strategy; a strategy adds entries, stops and exits, judged by its own backtest.
- **Overlap**: 3- and 6-month windows overlap month to month, so those columns are not independent observations.
