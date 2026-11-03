"""Backtest stages: one window to tune a strategy in, one to verify it in, and nothing shared.

A rule tuned on the same years it is then judged on will agree with those years by construction,
and the agreement says nothing about the future. This shelf has a measured case: blocking cheats on
VCP-09 bases was worth +17.8R in the India run it was discovered in, and +12.1R when re-run. So:

    optimise   2013-01-01 -> 2021-12-31   tune, explore, compare variants -- as often as you like
    verify     2022-01-01 -> today        judge a FINISHED candidate, once per version
    full       2013-01-01 -> today        context for a reader, never a verdict

The optimise window holds the 2015-16 chop, the 2018 sell-off, the 2020 crash and the 2021 boom; the
verify window holds a different regime -- the 2022 bear, then 2023 onward -- so a pass means more
than surviving one bull market.

Two rules make the verify window worth anything, and both are enforced rather than remembered:

* It is never read while optimising. Inside a stage, `marketdata.asof.boundary` stops every loader a
  backtest uses at the stage's end, so an optimise run cannot see 2022 through a price, an indicator,
  a universe filter or a "latest" lookup.
* It is used once per candidate. A verify run is refused if the same strategy version with the same
  options already has one (`verify_runs`). Run it again with `--again` and the repeat is recorded as
  a repeat: a verify result looked at twice and acted on is in-sample.

A verify run's verdict is recorded too (`judge`: `passed` and the `criterion` it was judged against).
Positive excess is not a pass: the criterion written before the run is, and the Strategies page grades
an edge "verified" only from a recorded pass. A verify run with positive excess that did not pass (a
deeper drawdown than its criterion allowed, say) is shown as a return edge with its risk beside it and
the criterion's verdict named -- not as "no edge", and not as verified.

Honest limit: every year up to October 2026 informed some decision made before this module existed,
so strategies refined until then have no clean historical hold-out. The split protects decisions
made from here on.
"""

import contextlib
import json
from dataclasses import dataclass

import pandas as pd

from ..marketdata import asof, db


@dataclass(frozen=True)
class Window:
    start: str
    end: str | None       # None = up to the latest stored data
    purpose: str


STAGES = {
    "optimise": Window("2013-01-01", "2021-12-31", "tune and compare variants; read as often as you like"),
    "verify": Window("2022-01-01", None, "judge a finished candidate, once per version"),
    "full": Window("2013-01-01", None, "context only, never a verdict"),
}
DEFAULT = "optimise"


def resolve(stage: str | None, start: str | None = None) -> tuple[str, str, str | None]:
    """(stage, start, end) for a request.

    No stage and no start  -> the default stage, optimise.
    No stage but a start   -> `full` from that start, which is what an explicit start meant before
                              stages existed; a run asked for that way is context, not a verdict.
    A stage, and a start   -> the start moves within the stage. It may not reach past the stage's
                              end, and a verify run may not start before the hold-out does, because
                              that would put in-sample years into the verdict.
    """
    if stage is None:
        if start:
            return "full", str(start), None
        stage = DEFAULT
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}; choose from {sorted(STAGES)}")
    w = STAGES[stage]
    s = str(start or w.start)
    if w.end and pd.Timestamp(s) > pd.Timestamp(w.end):
        raise ValueError(f"start {s} is after the {stage} window's end, {w.end}")
    if stage == "verify" and pd.Timestamp(s) < pd.Timestamp(STAGES["verify"].start):
        raise ValueError(f"a verify run cannot start before the hold-out ({STAGES['verify'].start}): "
                         f"{s} would put optimised years into the verdict")
    return stage, s, w.end


def tag(stage: str, end: str | None) -> str:
    """The suffix a run directory carries: ingest reads the stage (and the end) back out of it."""
    return f"stage-{stage}" + (f"-to-{end}" if end else "")


@contextlib.contextmanager
def active(stage: str, start: str, end: str | None):
    """Run a backtest inside its stage: no read past `end`, and run directories tagged."""
    with asof.boundary(end, tag(stage, end)):
        yield


# ------------------------------------------------------------------ verify once

_SCHEMA = """
CREATE TABLE IF NOT EXISTS verify_runs (
    id         SERIAL PRIMARY KEY,
    market     TEXT NOT NULL,
    strategy   TEXT NOT NULL,
    spec_id    TEXT NOT NULL,
    signature  TEXT NOT NULL,          -- the options that change what is tested, as sorted JSON
    repeat     BOOLEAN NOT NULL DEFAULT FALSE,
    run_dir    TEXT,
    ran_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS verify_runs_key ON verify_runs (market, strategy, spec_id, signature);
-- the verdict against the pass criterion written before the run (judge); NULL = not judged yet
ALTER TABLE verify_runs ADD COLUMN IF NOT EXISTS passed BOOLEAN;
ALTER TABLE verify_runs ADD COLUMN IF NOT EXISTS criterion TEXT;
ALTER TABLE verify_runs ADD COLUMN IF NOT EXISTS judged_at TIMESTAMPTZ;
"""

# options that only place the run in time or control the queue; everything else changes what is tested
_NOT_IDENTITY = {"stage", "start", "again", "strategies", "force", "no_ingest", "allow_stale"}


# `--bt` passthroughs that change how fast a run goes, not what it tests -> how many values each takes.
# Without this, every run queued with `--bt=--workers 6` reads as a variant of the strategy, and two
# verify requests that differ only in worker count look like different tests.
_SPEED_ONLY_BT = {"--workers": 1}


def _arg_pairs(args: str) -> tuple[set, set]:
    """(flag, value) pairs and bare flags in a command-line string such as a strategy's backtest_args."""
    import shlex
    toks, pairs, bare = shlex.split(args or ""), set(), set()
    for i, t in enumerate(toks):
        if not t.startswith("--"):
            continue
        if "=" in t:
            f, v = t.split("=", 1); pairs.add((f, v))
        elif i + 1 < len(toks) and not toks[i + 1].startswith("--"):
            pairs.add((t, toks[i + 1]))
        else:
            bare.add(t)
    return pairs, bare


def overrides(opts: dict, strategy_args: str | None = None) -> dict:
    """What a queue item changes about the strategy it tests: the options outside _NOT_IDENTITY.

    Empty means the strategy exactly as it is configured -- its own `backtest_args` and constants,
    in whatever window the stage gives it. Pass the strategy's `backtest_args` as `strategy_args` and an
    option that merely repeats one of them is not counted. This is the one definition of "a variant": verify's
    de-duplication keys on it, and the Strategies page uses it to keep variants out of the headline.
    """
    import shlex
    out = {k: v for k, v in sorted((opts or {}).items())
           if k not in _NOT_IDENTITY and v not in (None, False, "", [])}
    # An option that only repeats the strategy's own `backtest_args` changes nothing: early minervini
    # runs passed --accept-labels with exactly the labels the strategy already names.
    pairs, bare = _arg_pairs(strategy_args or "")
    for k in list(out):
        if k == "bt":
            continue
        flag, v = "--" + k.replace("_", "-"), out[k]
        if (v is True and flag in bare) or (not isinstance(v, (list, bool)) and (flag, str(v)) in pairs):
            out.pop(k)
    if "bt" in out:
        kept = []
        for extra in out["bt"]:
            toks, i, keep = shlex.split(str(extra)), 0, []
            while i < len(toks):
                flag = toks[i].split("=", 1)[0]
                if flag in _SPEED_ONLY_BT:
                    i += 1 + (0 if "=" in toks[i] else _SPEED_ONLY_BT[flag])
                    continue
                nxt = toks[i + 1] if i + 1 < len(toks) and not toks[i + 1].startswith("--") else None
                if (nxt is not None and (toks[i], nxt) in pairs) or (nxt is None and toks[i] in bare):
                    i += 2 if nxt is not None else 1      # restates the strategy's own argument
                    continue
                keep.append(toks[i]); i += 1
            if keep:
                kept.append(" ".join(keep))
        if kept:
            out["bt"] = kept
        else:
            out.pop("bt")
    return out


def runner_defaults(main) -> str:
    """A portfolio runner's argparse defaults as a command line ("--system 2 ..."), for `overrides()`'s
    `strategy_args`: a queue item that restates a default (turtle_trend's `--bt '--system 2'`) tests the
    strategy as configured, not a variant. Read by stopping `main` at its parse_args, so nothing runs."""
    import argparse

    class _Stop(Exception):
        pass

    def grab(self, *a, **k):
        raise _Stop(self)

    orig, argparse.ArgumentParser.parse_args = argparse.ArgumentParser.parse_args, grab
    try:
        main([])
    except _Stop as stop:
        parser = stop.args[0]
    else:
        return ""
    finally:
        argparse.ArgumentParser.parse_args = orig
    out = []
    for act in parser._actions:
        longs = [o for o in act.option_strings if o.startswith("--")]
        if longs and act.default not in (None, False, argparse.SUPPRESS) and act.nargs in (None, "?"):
            out.append(f"{longs[0]} {act.default}")
    return " ".join(out)


def describe(over: dict) -> list[str]:
    """`overrides()` as the command-line pieces a reader recognises: ["--const X=1", "--min-turnover 1e8"]."""
    parts = []
    for k, v in sorted((over or {}).items()):
        if k == "bt":
            parts += [str(x) for x in v]
        elif isinstance(v, list):
            parts += [f"--{k.replace('_', '-')} {x}" for x in v]
        elif v is True:
            parts.append(f"--{k.replace('_', '-')}")
        else:
            parts.append(f"--{k.replace('_', '-')} {v}")
    return parts


def signature(opts: dict) -> str:
    return json.dumps(overrides(opts), sort_keys=True, default=str)


def _init() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(_SCHEMA)


def previous(market: str, strategy: str, spec_id: str, opts: dict) -> list[dict]:
    _init()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT ran_at, repeat, run_dir FROM verify_runs WHERE market=%s AND strategy=%s "
                    "AND spec_id=%s AND signature=%s ORDER BY ran_at", (market, strategy, spec_id, signature(opts)))
        return [{"ran_at": r[0], "repeat": r[1], "run_dir": r[2]} for r in cur.fetchall()]


def check(market: str, strategy: str, spec_id: str, opts: dict) -> bool:
    """Raise if this candidate has already been verified, unless the request says `again`.

    Returns whether the run about to happen is a repeat, so it can be recorded as one."""
    done = previous(market, strategy, spec_id, opts)
    if done and not (opts or {}).get("again"):
        first = done[0]
        raise RuntimeError(
            f"{strategy} {spec_id} ({market}) was already verified on {first['ran_at']:%Y-%m-%d}"
            f"{' -> ' + first['run_dir'] if first['run_dir'] else ''}. A hold-out looked at twice and acted "
            f"on is in-sample. Change the rules (a new version) and verify that, or pass --again to repeat "
            f"this one knowingly; the repeat is recorded as one.")
    return bool(done)


def record(market: str, strategy: str, spec_id: str, opts: dict, repeat: bool, run_dir: str | None) -> None:
    _init()
    with db.get_connection().cursor() as cur:
        cur.execute("INSERT INTO verify_runs (market, strategy, spec_id, signature, repeat, run_dir) "
                    "VALUES (%s, %s, %s, %s, %s, %s)", (market, strategy, spec_id, signature(opts), repeat, run_dir))


def judge(run_dir: str, passed: bool, criterion: str) -> int:
    """Record whether the verify run in `run_dir` (its directory, or just the directory's name) met the pass
    criterion written before it ran. Returns the number of verify_runs rows updated (0 = no such run).

    The verdict is the reader's, against the criterion -- not a number this module can work out: positive
    excess with a deeper drawdown than the criterion allowed is a fail (momentum_vol_scaled 1.6, India)."""
    if not (criterion or "").strip():
        raise ValueError("a verdict needs the criterion it was judged against")
    _init()
    with db.get_connection().cursor() as cur:
        cur.execute("UPDATE verify_runs SET passed=%s, criterion=%s, judged_at=now() "
                    "WHERE run_dir=%s OR run_dir LIKE %s",
                    (bool(passed), criterion.strip(), run_dir, "%/" + run_dir.rstrip("/").rsplit("/", 1)[-1]))
        return cur.rowcount


def verdict_details() -> dict:
    """{(market, strategy, spec_id, run directory name): {"passed", "criterion"}} -- what the page shows
    beside a verify run's return and risk."""
    _init()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT market, strategy, spec_id, run_dir, passed, criterion FROM verify_runs "
                    "WHERE run_dir IS NOT NULL")
        return {(m, k, sp, rd.rstrip("/").rsplit("/", 1)[-1]): {"passed": p, "criterion": c}
                for m, k, sp, rd, p, c in cur.fetchall()}


def verdicts() -> dict:
    """{(market, strategy, spec_id, run directory name): passed (True / False / None = not judged)}."""
    _init()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT market, strategy, spec_id, run_dir, passed FROM verify_runs WHERE run_dir IS NOT NULL")
        return {(m, k, sp, rd.rstrip("/").rsplit("/", 1)[-1]): p for m, k, sp, rd, p in cur.fetchall()}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Record a verify run's verdict against its pass criterion.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    j = sub.add_parser("judge", help="record whether a verify run met its pass criterion")
    j.add_argument("run_dir", help="the run's directory, or its name")
    v = j.add_mutually_exclusive_group(required=True)
    v.add_argument("--passed", action="store_true")
    v.add_argument("--failed", action="store_true")
    j.add_argument("--criterion", required=True, help="the pass criterion, as written before the run")
    a = ap.parse_args()
    n = judge(a.run_dir, a.passed, a.criterion)
    print(f"{n} verify run(s) recorded as {'passed' if a.passed else 'failed'}" if n
          else f"no verify run recorded at {a.run_dir}")


if __name__ == "__main__":
    main()
