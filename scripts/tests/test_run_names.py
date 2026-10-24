"""Every portfolio limit that changes a result is in the run's name, and defaults add nothing.

A backtest is filed under its name. An input missing from the name makes two different runs share
a directory, and the later silently replaces the earlier -- the stored report then describes a
configuration it does not hold. `--max-positions 4` overwrote the default Minervini run it was
meant to be compared with, and `--max-base 1` and `--max-base 2` named the same directory.

The other half matters as much: a value equal to the default must add nothing, or every existing
run is renamed and its history detaches from the runs that follow.

    PYTHONPATH=. .venv/bin/python -m tests.test_run_names
"""

import sys
from argparse import Namespace

import swing_screener.strategies.minervini_spec as ms
from swing_screener.backtesting.backtest import _portfolio_suffix
from swing_screener.config import MARKETS

FAILS: list[str] = []
CFG = MARKETS["india"]


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def spec(**over) -> Namespace:
    """Arguments as spec mode leaves them: every limit filled from the strategy's constants."""
    a = dict(spec=True, max_positions=ms.MAX_POSITIONS, max_open_risk=ms.MAX_OPEN_RISK_PCT,
             max_adv_pct=ms.MAX_ADV_PCT, max_base=None)
    a.update(over)
    return Namespace(**a)


def plain(**over) -> Namespace:
    a = dict(spec=False, max_positions=None, max_open_risk=None, max_adv_pct=None, max_base=None)
    a.update(over)
    return Namespace(**a)


def main() -> int:
    print("defaults keep a run's name")
    check("a default spec run adds nothing", _portfolio_suffix(spec(), CFG) == "",
          repr(_portfolio_suffix(spec(), CFG)))
    check("a default plain run adds nothing", _portfolio_suffix(plain(), CFG) == "",
          repr(_portfolio_suffix(plain(), CFG)))
    check("naming the market's own position cap adds nothing",
          _portfolio_suffix(plain(max_positions=CFG.max_open_positions), CFG) == "")

    print("each override names its own directory")
    base = _portfolio_suffix(spec(), CFG)
    cases = {
        "--max-positions 4": spec(max_positions=4),
        "--max-open-risk 3": spec(max_open_risk=3.0),
        "--max-adv-pct 2": spec(max_adv_pct=2.0),
        "--max-base 1": spec(max_base=1),
        "--max-base 2": spec(max_base=2),
    }
    names = {k: _portfolio_suffix(v, CFG) for k, v in cases.items()}
    for k, v in names.items():
        check(f"{k} differs from the default run", v != base, repr(v))
    check("--max-base 1 and --max-base 2 do not share a directory",
          names["--max-base 1"] != names["--max-base 2"], f"{names['--max-base 1']!r}")
    check("no two overrides collide", len(set(names.values())) == len(names), repr(names))

    print(f"\n{'OK — every portfolio limit reaches the run name.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
