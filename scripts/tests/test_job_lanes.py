"""Worker lanes route each queue item to the right lane, never start two writers of one dataset, and keep
the main lane in queue order (jobs/registry.py `fast_item` / `research_item` / `clashes` / `choose_for`).

No database: the lane policies are pure functions of the waiting and running items, except the main lane's
question "is the backtest lane alive?", which is stubbed here.

    PYTHONPATH=. .venv/bin/python -m tests.test_job_lanes
"""

import sys

from jobs import queue
from jobs import registry as R

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(what)


_ids = iter(range(1, 10_000))


def item(targets, market="us", **kw) -> dict:
    return {"id": next(_ids), "targets": list(targets), "market": market, **kw}


class backtest_lane:
    """Stub queue.worker_status so choose_for('main') sees the backtest lane alive or not."""
    def __init__(self, alive: bool):
        self.alive = alive

    def __enter__(self):
        self.real = queue.worker_status
        queue.worker_status = lambda lane="main": {"alive": self.alive if lane == "backtest" else True, "lane": lane}

    def __exit__(self, *exc):
        queue.worker_status = self.real


def main() -> int:
    print("routing")
    check("a pipeline expands to its jobs", R.item_jobs(["close"])[:2] == ["universe", "prices"] and "ingest" in R.item_jobs(["close"]))
    check("the backtest pipeline is backtest + ingest", R.item_jobs(["backtest"]) == ["backtest", "ingest"])
    for t in (["screens"], ["breadth"], ["strategies"], ["report", "ingest"]):
        check(f"fast: {'+'.join(t)}", R.fast_item(item(t)))
    for t in (["close"], ["prices"], ["backtest"], ["quality"], ["screens", "prices"], []):
        check(f"not fast: {'+'.join(t) or '(empty)'}", not R.fast_item(item(t)))
    for t in (["backtest"], ["screen_history"], ["group_research"]):
        check(f"research: {'+'.join(t)}", R.research_item(item(t)))
    for t in (["close"], ["quality"], ["backtest", "prices"], ["ingest"], []):
        check(f"not research: {'+'.join(t) or '(empty)'}", not R.research_item(item(t)))

    print("clashes")
    india, us = "india", "us"
    check("same job, same market", R.clashes(item(["screens"], india), [item(["screens"], india)]))
    check("same job, other market: no clash", not R.clashes(item(["screens"], india), [item(["screens"], us)]))
    check("'all' overlaps every market", R.clashes(item(["screens"], india), [item(["screens"], "all")]))
    check("a pipeline containing the job clashes", R.clashes(item(["screens"], india), [item(["close"], india)]))
    check("ingest/report are exempt: close vs a running backtest", not R.clashes(item(["close"], us), [item(["backtest"], us)]))
    check("a fast job waits for that market's download", R.clashes(item(["screens"], india), [item(["prices"], india)]))
    check("…but not for another market's", not R.clashes(item(["screens"], india), [item(["prices"], us)]))
    check("a backtest does not wait for a download", not R.clashes(item(["backtest"], us), [item(["prices"], us)]))

    print("claim policies")
    bt, scr, close, qual = item(["backtest"], us), item(["screens"], india), item(["close"], india), item(["quality"], us)
    fast, btl = R.choose_for("fast"), R.choose_for("backtest")
    check("fast lane: first fast item, skipping others", fast([bt, close, scr], []) is scr)
    check("fast lane: nothing fast waiting → None", fast([bt, close], []) is None)
    check("fast lane: skips a fast item that clashes", fast([scr], [item(["prices"], india)]) is None)
    check("backtest lane: first research item", btl([close, bt, scr], []) is bt)
    check("backtest lane: none waiting → None", btl([close, scr], []) is None)
    with backtest_lane(alive=True):
        main = R.choose_for("main")
        check("main lane leaves backtests to a live backtest lane", main([bt, qual], []) is qual)
        check("main lane: only research waiting → None", main([bt], []) is None)
        check("main lane waits on a clash instead of skipping ahead", main([close, qual], [item(["screens"], india)]) is None)
        check("main lane takes queue order when clear", main([close, qual], []) is close)
    with backtest_lane(alive=False):
        main = R.choose_for("main")
        check("main lane runs backtests itself when that lane is down", main([bt, qual], []) is bt)

    print("registry")
    check("every fast job exists", all(j in R.JOBS for j in R.FAST_JOBS), str(sorted(set(R.FAST_JOBS) - set(R.JOBS))))
    check("every research job exists", all(j in R.JOBS for j in R.RESEARCH_JOBS), str(sorted(set(R.RESEARCH_JOBS) - set(R.JOBS))))
    check("no fast job downloads", not any(R.JOBS[j].network for j in R.FAST_JOBS if j in R.JOBS))
    check("no research job downloads", not any(R.JOBS[j].network for j in R.RESEARCH_JOBS if j in R.JOBS))
    check("fast and research jobs do not overlap", not (R.FAST_JOBS & R.RESEARCH_JOBS))
    check("each lane has its own heartbeat row", len(set(queue._LANE_ROW.values())) == len(queue.LANES) and set(queue._LANE_ROW) == set(queue.LANES))
    check("choose_for covers every lane", all(callable(R.choose_for(ln)) for ln in queue.LANES))

    print(f"\n{'OK — lanes route, wait and stay apart as designed.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
