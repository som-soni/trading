# Research

Written findings. Code lives in `scripts/`, generated output in `reports/`.

| document | what it covers |
|---|---|
| [momentum-trend-research.md](momentum-trend-research.md) | The main log: results ledger for every strategy tested, what each experiment established, methodology, known biases, and the queue of open experiments |
| [index-investing-research.md](index-investing-research.md) | *When* to put money into an index rather than *which* stocks to own: SIP day-of-month and frequency, lump sum vs DCA, dip-buying, trend overlays, allocation and rebalancing, rotation — with pre- and after-tax results for both markets |

## How to use the research log

**Adding a strategy.** Run it, then append a row to the ledger in §2 under the
right market. Keep the columns identical so rows stay comparable — CAGR,
maxDD, Sharpe, Calmar, excess vs benchmark, trade count. A result without a
benchmark comparison is not interpretable.

**Before trusting a result**, read §5 (known biases). Survivorship bias is
unfixed and is worst exactly where the returns look best — though it does not
apply to the index-investing log, which has no selection step at all.

**For the index log specifically**, note that its scoring differs by family:
accumulation strategies are judged on XIRR and terminal wealth per unit
contributed (CAGR is meaningless once money is flowing in), lump-sum ones on
CAGR and drawdown. Calendar findings there are reported against a
randomised-day null, because the best of 30 contribution days is a selected
maximum before it is a finding.

**Before concluding a strategy failed**, check it is not one of the measurement
artefacts already catalogued in §4 — right-censoring, optimistic fills, and
today's-row candidate selection each produced badly misleading numbers before
they were found and fixed.

## Repository layout

```
trading/
  scripts/        code (see scripts/README.md)
  data/           inputs: universe lists, earnings overrides, caches
  reports/        generated output, one directory per run
    <market>/<strategy>/<run>/
      report.md trades.csv equity.csv figures/
    _experiments/ A/B sweep CSVs
    _history/     daily screener run snapshots
  logs/           run logs
  research/       this directory
  archive/        superseded material, kept not deleted (see archive/README.md)
```
