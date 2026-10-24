"""Backtest stages keep the hold-out held out (backtesting/windows.py, marketdata/asof.py).

What is checked, and why each one matters:

* the stage rules -- which window a request gets, and that a verify run cannot reach back into the
  tuning years;
* every loader a backtest reads through stops at the boundary -- a loader that does not is a leak,
  and a leak is silent: nothing errors, the optimise result just knows the future;
* run directories carry their stage, so an optimise run never overwrites a verify run, and outside a
  stage nothing is tagged;
* `--stage` survives the trip through `queue.command_for` to the worker -- an option missing there is
  dropped silently, which is how a `--vcp` variant once ran the shipped rules looking successful;
* a verify run is refused the second time, unless asked for knowingly;
* a real runner, run inside the optimise stage, ends at the boundary.

`--all` also runs EVERY registered strategy inside the optimise stage (per-symbol ones on a sample)
into a scratch reports directory, and fails if any equity row or trade lands after the boundary. It
is slow -- minutes -- so it is not the default; run it after touching a loader or adding a runner.

    PYTHONPATH=. .venv/bin/python -m tests.test_backtest_stages
    PYTHONPATH=. .venv/bin/python -m tests.test_backtest_stages --all
"""

import sys
import tempfile
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

from swing_screener.backtesting import windows  # noqa: E402
from swing_screener.marketdata import asof, cache, financials, index_data  # noqa: E402

FAILS: list[str] = []
OPT_END = pd.Timestamp(windows.STAGES["optimise"].end)


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def raises(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def stage_rules() -> None:
    print("which window a request gets")
    check("no stage and no start is the optimise stage",
          windows.resolve(None, None) == ("optimise", windows.STAGES["optimise"].start, windows.STAGES["optimise"].end))
    check("an explicit start with no stage keeps its old meaning: full, to the latest data",
          windows.resolve(None, "2020-01-01") == ("full", "2020-01-01", None))
    check("a start can move inside the optimise window, which keeps its end",
          windows.resolve("optimise", "2016-01-01") == ("optimise", "2016-01-01", windows.STAGES["optimise"].end))
    check("an optimise start after the optimise end is refused", raises(lambda: windows.resolve("optimise", "2023-01-01")))
    check("a verify run cannot start inside the tuning years", raises(lambda: windows.resolve("verify", "2020-01-01")))
    check("an unknown stage is refused", raises(lambda: windows.resolve("backfit")))


def loaders() -> None:
    print("every loader a backtest reads through stops at the boundary")
    probes = {
        "cache.load_cached": lambda: cache.load_cached("us", "SPY").index.max(),
        "cache.load_many_cached": lambda: max(v.index.max() for v in cache.load_many_cached("us", ["SPY", "AAPL"]).values()),
        "cache.load_cached_with_indicators": lambda: cache.load_cached_with_indicators("us", "SPY", pd.Timestamp.today()).index.max(),
        "index_data.load": lambda: index_data.load("us", "CASH_YIELD").index.max(),
        "index_data.total_return_index": lambda: index_data.total_return_index("us", "SPY")[0].index.max(),
        "financials.load": lambda: max(pd.Timestamp(r.get("filed") or r["period_end"])
                                       for rows in financials.load("us", ["AAPL", "MSFT"]).values() for r in rows),
    }
    from swing_screener.analytics import group_history
    from swing_screener.backtesting import pead
    probes["group_history.load"] = lambda: max(pd.Timestamp(d) for d in group_history.load("us").keys())
    probes["pead.load_events"] = lambda: pead.load_events("us")["filed"].max()
    with cache.offline():
        for name, probe in probes.items():
            free = probe()
            with asof.boundary(OPT_END, "test"):
                bounded = probe()
            check(f"{name} ends at or before {OPT_END.date()} inside a stage",
                  bounded <= OPT_END, f"read to {bounded}")
            check(f"{name} is unchanged outside one", free > OPT_END, f"unbounded read ends {free}")


def tagging() -> None:
    from swing_screener.paths import run_dir
    print("run directories carry their stage")
    plain = run_dir("us", "x", "2013-01-01_demo_v1.0-abcdef12", create=False).name
    check("outside a stage, nothing is tagged", plain == "2013-01-01_demo_v1.0-abcdef12", plain)
    with windows.active(*windows.resolve("optimise")):
        tagged = run_dir("us", "x", "2013-01-01_demo_v1.0-abcdef12", create=False).name
        nested = run_dir("us", "x", "2013-01-01_demo_v1.0-abcdef12", create=False).name
    check("inside optimise, the run is tagged with stage and end",
          tagged.endswith("_stage-optimise-to-2021-12-31"), tagged)
    check("tagging is idempotent", tagged == nested)
    from swing_screener.web.ingest import spec_id_of, stage_of
    check("ingest still reads the spec id from a tagged name", spec_id_of(tagged) == "v1.0-abcdef12", str(spec_id_of(tagged)))
    st = stage_of(tagged)
    check("ingest reads the stage and the end back", st["stage"] == "optimise" and st["end"] == "2021-12-31", str(st))
    check("an untagged run reads as legacy", stage_of(plain)["stage"] is None)


def command_round_trip() -> None:
    from jobs import queue
    print("--stage reaches the worker")
    cmd = queue.command_for(["backtest"], "us", {"strategies": ["donchian"], "stage": "verify", "again": True})
    check("command_for carries --stage", "--stage" in cmd and cmd[cmd.index("--stage") + 1] == "verify", " ".join(cmd))
    check("command_for carries --again", "--again" in cmd, " ".join(cmd))


def verify_once() -> None:
    from swing_screener.marketdata import db
    print("a verify run is used once per candidate")
    key = ("us", "__stage_test__", "v0.0-00000000")
    try:
        check("the first verify is allowed", windows.check(*key, {}) is False)
        windows.record(*key, {}, False, "/tmp/x")
        refused = False
        try:
            windows.check(*key, {})
        except RuntimeError:
            refused = True
        check("the second is refused", refused)
        check("...unless asked for knowingly, and then it is a repeat", windows.check(*key, {"again": True}) is True)
        check("different options are a different candidate", windows.check(*key, {"const": ["X=1"]}) is False)
        check("the window does not make a different candidate", windows.signature({"start": "2023-01-01"}) == windows.signature({}))
    finally:
        with db.get_connection().cursor() as cur:
            cur.execute("DELETE FROM verify_runs WHERE strategy=%s", (key[1],))


def one_runner() -> None:
    from swing_screener.backtesting import dual_momentum as dm
    from swing_screener.strategies import portfolio_strategies
    print("a real runner, inside the optimise stage, ends at the boundary")
    c = portfolio_strategies()["dual_momentum"]
    with cache.offline(), windows.active(*windows.resolve("optimise")):
        tdf, eq, pos, _px, _c = dm.run("us", windows.STAGES["optimise"].start, c.lookback_months, c.rebalance, c.cost_bps)
    check("dual_momentum's equity ends at or before the boundary", eq.index.max() <= OPT_END, str(eq.index.max()))
    late = [d for d in pd.to_datetime(tdf.get("exit_date", pd.Series(dtype=str)), errors="coerce").dropna() if d > OPT_END]
    check("no trade exits after it", not late, f"{len(late)} late exits")


def every_strategy() -> None:
    """Every registered strategy through its own runner, inside optimise, into a scratch directory."""
    import importlib
    import shlex
    from swing_screener import paths
    from swing_screener.backtesting import backtest as bt
    from swing_screener.strategies import get_strategy, list_strategies, portfolio_strategies
    print("every registered strategy, inside the optimise stage, ends at the boundary  (--all)")
    stage, start, end = windows.resolve("optimise")
    real = paths.REPORTS_DIR
    with tempfile.TemporaryDirectory() as tmp:
        paths.REPORTS_DIR = Path(tmp)
        try:
            jobs = [(k, "portfolio") for k in sorted(portfolio_strategies())] + [(k, "symbol") for k in list_strategies()]
            for key, kind in jobs:
                for market in ("us",):
                    try:
                        with cache.offline(), windows.active(stage, start, end):
                            if kind == "portfolio":
                                mod = importlib.import_module(
                                    f"swing_screener.backtesting.{getattr(portfolio_strategies()[key], 'runner', 'baseline')}")
                                r = mod.main(["--strategy", key, "--market", market, "--start", start, "--no-ingest"])
                            else:
                                args = shlex.split(type(get_strategy(key)).backtest_args or "")
                                r = bt.main(["--market", market, "--start", start, "--strategy", key, "--sample", "25",
                                             *args, "--no-ingest"])
                    except SystemExit as e:
                        check(f"{key} ({market}) ran", False, f"exited {e.code}")
                        continue
                    except Exception as e:   # noqa: BLE001
                        check(f"{key} ({market}) ran", False, f"{type(e).__name__}: {e}"[:160])
                        continue
                    d = Path(r["run_dir"]) if r and r.get("run_dir") else None
                    if not d or not (d / "equity.csv").exists():
                        check(f"{key} ({market}) wrote an equity curve", False, str(d))
                        continue
                    eq = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True)
                    worst = eq.index.max()
                    tr = d / "trades.csv"
                    if tr.exists() and tr.stat().st_size:
                        t = pd.read_csv(tr)
                        for col in ("entry_date", "exit_date"):
                            if col in t:
                                v = pd.to_datetime(t[col], errors="coerce").max()
                                if pd.notna(v):
                                    worst = max(worst, v)
                    check(f"{key} ({market}) stays inside the window -- last date {worst.date()}, tagged {d.name.endswith(windows.tag(stage, end))}",
                          worst <= OPT_END and d.name.endswith(windows.tag(stage, end)), f"{worst} / {d.name}")
        finally:
            paths.REPORTS_DIR = real


def main() -> int:
    stage_rules()
    loaders()
    tagging()
    command_round_trip()
    verify_once()
    one_runner()
    if "--all" in sys.argv:
        every_strategy()
    print(f"\n{'OK — the hold-out stays held out.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
