"""`--const` reaches a PORTFOLIO strategy's backtest, or is refused -- never dropped.

Until 2026-11-14 the job runner (`jobs/registry.py`) passed `--const` to the per-symbol backtester only.
A portfolio strategy's runner (`backtesting/<runner>.py`) never saw it, so a `--const` variant of one ran
the shipped rules while its `overrides.json` named the variant: a default run filed as an experiment.

Checked here, with the runner's `main` swapped for a stub that records what it sees (no database, no
prices, nothing written outside a temp folder):

  * for every portfolio strategy, each module constant either moves its spec id when overridden (and is
    restored afterwards) or is refused with a reason -- an unknown name and a class attribute are refused;
  * through the job runner's own backtest step, the runner runs WITH the constant applied: its spec id
    (which names the run directory) is the variant's, and a result computed from the constant changes;
  * the next strategy in the same process sees the shipped value again;
  * an unknown constant fails the step before the runner is called.

    PYTHONPATH=. .venv/bin/python -m tests.test_portfolio_const
"""

import importlib
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _numeric_consts(mod) -> dict:
    return {k: v for k, v in vars(mod).items()
            if k.isupper() and isinstance(v, (int, float)) and not isinstance(v, bool)}


def every_constant_applies_or_is_refused() -> None:
    from swing_screener.strategies import portfolio_strategies
    from swing_screener.strategies.variants import overridden
    print("every portfolio strategy: a constant moves the spec id, or is refused")
    for key, cls in sorted(portfolio_strategies().items()):
        mod = importlib.import_module(cls.__module__)
        base, silent = cls.spec_id(), []
        for name, v in _numeric_consts(mod).items():
            try:
                with overridden(key, {name: v + 1}) as applied:
                    moved = cls.spec_id() != base and getattr(mod, name) == applied[name]
            except ValueError:
                continue                                   # refused, loudly: fine
            if not moved:
                silent.append(name)
        check(f"{key}: no constant applies without moving the spec id", not silent, str(silent))
        check(f"{key}: constants restored after the block", cls.spec_id() == base)
        for bad in ("NO_SUCH_CONSTANT", "cost_bps", "top_n"):
            try:
                with overridden(key, {bad: 1}):
                    pass
                refused = False
            except ValueError:
                refused = True
            check(f"{key}: refuses {bad}", refused)


def _step_fn(key: str, const: list | None):
    from jobs.registry import Ctx, _backtest_steps
    opts = {"strategies": [key], "stage": "optimise"}
    if const:
        opts["const"] = const
    ctx = Ctx("us", opts)
    _, _, fn = _backtest_steps(ctx)[0]
    ctx.step = SimpleNamespace(detail="", stats=None, progress=lambda *a, **k: None, skip=lambda why: None)
    return ctx, fn


def job_runner_applies_it() -> None:
    from swing_screener.strategies import portfolio_strategies
    key, name = "parabolic_short", "RISK_PCT"
    cls = portfolio_strategies()[key]
    mod = importlib.import_module(cls.__module__)
    shipped = getattr(mod, name)
    seen: list[dict] = []
    tmp = Path(tempfile.mkdtemp(prefix="portfolio_const_"))

    def stub(argv=None):
        if not argv:                       # windows.runner_defaults reads the parser only
            return None
        spec = cls.spec_id()
        # a "result" the constant decides, read while the runner runs, as the real runner reads it
        seen.append({"spec": spec, "value": getattr(mod, name), "result": 100.0 * getattr(mod, name)})
        out = tmp / f"run_{len(seen)}_{spec}"
        out.mkdir()
        perf = SimpleNamespace(cagr_pct=seen[-1]["result"], benchmark_cagr_pct=0.0, max_drawdown_pct=1.0)
        return {"perf": perf, "trades": 1, "run_dir": out}

    real = mod.main
    mod.main = stub
    try:
        print("through the job runner's backtest step (runner stubbed)")
        ctx, fn = _step_fn(key, None)
        fn(ctx)
        ctx, fn = _step_fn(key, [f"{name}={shipped * 4}"])
        fn(ctx)
        ctx, fn = _step_fn(key, None)
        fn(ctx)
        default, variant, after = seen
        check("the variant runs with the constant applied", variant["value"] == shipped * 4,
              f"saw {variant['value']}, shipped {shipped}")
        check("its spec id (the run directory's name) is the variant's", variant["spec"] != default["spec"])
        check("its result differs from the default run's", variant["result"] != default["result"])
        check("the next run in the process is back on the shipped rules",
              after["value"] == shipped and after["spec"] == default["spec"])
        import json
        rec = json.loads((Path(sorted(tmp.glob("run_2_*"))[0]) / "overrides.json").read_text())
        check("overrides.json records the constant", rec["overrides"].get("const") == [f"{name}={shipped * 4}"],
              str(rec))

        n = len(seen)
        for bad in ("NO_SUCH_CONSTANT=1", "cost_bps=5"):
            ctx, fn = _step_fn(key, [bad])
            try:
                fn(ctx)
                err = None
            except ValueError as e:
                err = str(e)
            check(f"{bad.split('=')[0]} fails the step", err is not None and "--const" in (err or ""), str(err))
        check("...before the runner is called", len(seen) == n)
        check("...and leaves the shipped rules in place", getattr(mod, name) == shipped and cls.spec_id() == default["spec"])
    finally:
        mod.main = real


def main() -> int:
    every_constant_applies_or_is_refused()
    job_runner_applies_it()
    print(f"\n{len(FAILS)} failure(s)" if FAILS else "\nall ok")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
