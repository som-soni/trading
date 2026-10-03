# Research

Written findings. Code lives in `scripts/`, generated output in `reports/`.

| document | what it covers |
|---|---|
| [momentum-trend-research.md](momentum-trend-research.md) | The main log: results ledger for every strategy tested, what each experiment established, methodology, known biases, and the queue of open experiments |

## How to use the research log

**Adding a strategy.** Run it, then append a row to the ledger in §2 under the
right market. Keep the columns identical so rows stay comparable — CAGR,
maxDD, Sharpe, Calmar, excess vs benchmark, trade count. A result without a
benchmark comparison is not interpretable.

**Before trusting a result**, read §5 (known biases). Survivorship bias is
unfixed and is worst exactly where the returns look best.

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
