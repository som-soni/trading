"""`--const` reaches the exit ladder, instead of changing the run's name and nothing else.

ExitPolicy takes the Minervini exit constants as its defaults. They used to be plain dataclass
defaults, which Python evaluates once, when the class is created at import -- before `--const`
patches the strategy module. So an override set the constant, changed the fingerprint and
therefore the run directory, and left the policy on the old value: the run was filed as a
distinct experiment while silently measuring the control. `--const BREAKEVEN_R=0` and
`--const TREND_EXIT_NEEDS_VOLUME=1` were both no-ops that way.

A `default_factory` runs at construction, after the patch. This test pins that down, because the
failure is invisible -- nothing errors, the numbers are simply those of a different arm.

    PYTHONPATH=. .venv/bin/python -m tests.test_exit_policy_overrides
"""

import sys

import swing_screener.strategies.minervini_spec as ms
from swing_screener.backtesting.portfolio_sim import ExitPolicy

FAILS: list[str] = []

# field name on ExitPolicy -> (constant name on minervini_spec, value to patch in, expected)
OVERRIDES = {
    "breakeven_r": ("BREAKEVEN_R", 0.0, 0.0),
    "partial_r": ("PARTIAL_R", 0.0, 0.0),
    "partial_frac": ("STRENGTH_FRAC", 0.5, 0.5),
    "fail_days": ("FAIL_DAYS", 7, 7),
    "time_stop_days": ("TIME_STOP_DAYS", 30, 30),
    "trend_volume": ("TREND_EXIT_NEEDS_VOLUME", 1, True),
    "climax_partial": ("CLIMAX_IS_PARTIAL", 0, False),
    "strength_ext": ("STRENGTH_EXT_PCT", 50.0, 0.5),   # stored as a fraction
}


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def main() -> int:
    print("every exit constant an override can name is read at construction")
    for field_name, (const, patched, expected) in OVERRIDES.items():
        original = getattr(ms, const)
        try:
            setattr(ms, const, patched)          # what --const does
            got = getattr(ExitPolicy(mode="minervini"), field_name)
            check(f"--const {const}={patched:g} reaches policy.{field_name}",
                  got == expected, f"got {got!r}, wanted {expected!r}")
        finally:
            setattr(ms, const, original)

    # ...and the unpatched defaults still come from the strategy, so a plain run is unchanged
    p = ExitPolicy(mode="minervini")
    check("an unpatched policy still takes the strategy's own numbers",
          p.breakeven_r == ms.BREAKEVEN_R and p.partial_r == ms.PARTIAL_R
          and p.time_stop_days == ms.TIME_STOP_DAYS,
          f"breakeven_r={p.breakeven_r} partial_r={p.partial_r} time_stop_days={p.time_stop_days}")

    # an explicit argument still wins over the constant, which is how --breakeven-r works
    check("an explicit argument beats the constant",
          ExitPolicy(mode="minervini", breakeven_r=3.5).breakeven_r == 3.5)

    print(f"\n{'OK — overrides reach the exit ladder.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
