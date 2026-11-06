"""The market snapshot's catalog matches what it computes, and every reading is point in time.

The review's rules (and any study of them) read the stored snapshot as of past sessions, so a value must be
what the evening of that session would have shown: computed from rows up to and including it, never revised
by later data. Checked per market, per instrument, at a few sessions spread over the history: the fields
computed on prices TRUNCATED at the session equal the stored-history computation's row for it. A centred
average, a weekly EMA that reads the current week's Friday close, or a forward fill would fail here.

Also: every computed column is in FIELDS (and every FIELDS entry is computed by some subject), each with a doc.

Run:  PYTHONPATH=. .venv/bin/python -m tests.test_market_snapshot
"""

import sys

import numpy as np

from swing_screener.analytics import market_snapshot as ms
from swing_screener.config import MARKETS
from swing_screener.marketdata import cache

PROBES = 4           # sessions checked per instrument, spread over its history


def check_catalog(computed: dict[str, set]) -> list[str]:
    problems = []
    by_scope = {"instrument": set(), "market": set(), "pair": set()}
    for f in ms.FIELDS:
        if not f.doc.strip():
            problems.append(f"field {f.key}: no doc")
        by_scope.setdefault(f.scope, set()).add(f.key)
    for scope, cols in computed.items():
        for c in cols - by_scope.get(scope, set()):
            problems.append(f"{scope} field {c} is computed but not in FIELDS")
    for scope, keys in by_scope.items():
        for k in keys - computed.get(scope, set()):
            problems.append(f"{scope} field {k} is in FIELDS but never computed")
    return problems


def check_point_in_time(market: str) -> tuple[list[str], int]:
    problems, n = [], 0
    for label, ticker in ms.instruments(market).items():
        d = cache.load_cached(market, ticker)
        if d is None or len(d) < ms.SMA_LONG * 2:
            continue
        full = ms.instrument_fields(d)
        for pos in np.linspace(ms.SMA_LONG * 2, len(d) - 1, PROBES).astype(int):
            day = d.index[pos]
            cut = ms.instrument_fields(d.iloc[: pos + 1]).loc[day]
            a, b = full.loc[day].to_numpy(float), cut.to_numpy(float)
            same = np.isclose(a, b, rtol=1e-9, atol=1e-9, equal_nan=True)
            for col in full.columns[~same]:
                problems.append(f"{market} {label} {day.date()} {col}: {full.loc[day, col]} with later data, "
                                f"{cut[col]} without")
            n += 1
    return problems, n


def main() -> int:
    problems, probes = [], 0
    computed = {"instrument": set(), "market": set(), "pair": set()}
    for market in MARKETS:
        out = ms.compute(market)
        for subject, df in out.items():
            scope = "market" if subject == "market" else "pair" if "/" in subject else "instrument"
            computed[scope] |= set(df.columns)
        p, n = check_point_in_time(market)
        problems += p
        probes += n
    problems += check_catalog(computed)
    if problems:
        print("FAIL — market snapshot:\n")
        for p in problems:
            print(" ", p)
        return 1
    print(f"OK — {len(ms.FIELDS)} fields documented and computed; {probes} instrument-sessions point in time")
    return 0


if __name__ == "__main__":
    sys.exit(main())
