"""A running job's ETA starts as a historical guess and tightens once the step reports progress
(status.py `_estimate_remaining`): no history and no fraction gives no estimate; history alone
counts down at a fixed pace; a progress fraction alone extrapolates from elapsed/frac; both blend,
weighted by the fraction, so the estimate moves from the historical guess toward the live figure.

    PYTHONPATH=. .venv/bin/python -m tests.test_job_eta
"""

import sys

from swing_screener.web import status as S

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(what)


def main() -> int:
    print("no signal")
    check("no history, no progress -> unknown", S._estimate_remaining(30, None, None, None) is None)
    check("progress with total=0 is ignored, not a div/0", S._estimate_remaining(30, 0, 0, None) is None)

    print("history only")
    check("counts down from the historical median", S._estimate_remaining(40, None, None, 100) == 60)
    check("never goes negative once past the median", S._estimate_remaining(150, None, None, 100) == 0)

    print("progress only")
    r = S._estimate_remaining(40, 1, 4, None)  # 40s for 1/4 -> ~160s total -> 120s left
    check("extrapolates from elapsed/frac", abs(r - 120) < 1e-6, str(r))
    check("done but no total is ignored like no progress", S._estimate_remaining(40, 1, None, None) is None)

    print("both: blended, bounded by the two single-signal estimates")
    lo, hi = sorted([S._estimate_remaining(40, None, None, 100), S._estimate_remaining(40, 1, 4, None)])
    blended = S._estimate_remaining(40, 1, 4, 100)
    check("blend sits between the historical and the progress-based estimate", lo - 1e-6 <= blended <= hi + 1e-6, str(blended))
    near_done = S._estimate_remaining(90, 999, 1000, 100)
    check("near-complete progress dominates a stale historical prior", near_done < 1, str(near_done))

    print(f"\n{'OK — ETA starts from history and tightens with progress.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
