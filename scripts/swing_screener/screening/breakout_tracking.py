"""Breakout tracking: a paper record of hand-picked breakout candidates, checked after each close.

The stocks are the watchlist named LIST_NAME. Each item's note carries its plan, written when it was
added:

    Added 2026-11-10 at 221.50 (close 2026-11-09). Pivot 223.73, stop 220.54 (1.4%). ...

and this module reads the stored daily bars from the day after `close` and says what happened, by the
rules written in the same note:

* **breakout**  a close above the pivot on at least BREAKOUT_VOLUME x the 50-session average volume (a
  close above it on less volume is reported as light, and is not a breakout);
* **failed**    after a breakout, a close back below the pivot within FAIL_SESSIONS sessions;
* **stopped**   a close below the stop, before or after a breakout;
* **success**   after a breakout, a high at least TARGET_R x (pivot - stop) above the pivot within
  WINDOW_SESSIONS sessions of the breakout;
* **expired**   no breakout within WINDOW_SESSIONS sessions of the plan.

A tracked stock ends at stopped, failed, success or expired; until then it is waiting or open. The plan
is read from the note once and stored (`breakout_track`), so a later edit of the note cannot move the
levels being judged; each day's verdict goes to `breakout_track_log`, and the note's first line is
rewritten as "Status <date>: ..." so the list shows it. A paper record, never an order.

    PYTHONPATH=. python3 -m swing_screener.screening.breakout_tracking --market india
"""

import argparse
import re

import pandas as pd

from ..marketdata import cache, db

LIST_NAME = "Breakout tracking (paper)"
BREAKOUT_VOLUME = 1.4    # x the 50-session average volume, for a close above the pivot to count
FAIL_SESSIONS = 3        # a close back below the pivot this soon after a breakout is a failed breakout
TARGET_R = 2.0           # success: a high this many times (pivot - stop) above the pivot...
WINDOW_SESSIONS = 20     # ...within this many sessions of the breakout; and no breakout within this many
                         # sessions of the plan ends it as expired
VOLUME_AVG = 50

SCHEMA = """
CREATE TABLE IF NOT EXISTS breakout_track (
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    from_date DATE NOT NULL,          -- the close the plan was made on; judging starts the session after
    ref_price DOUBLE PRECISION,
    pivot DOUBLE PRECISION NOT NULL,
    stop DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting',
    status_date DATE,
    breakout_date DATE,
    detail TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol, from_date)
);
CREATE TABLE IF NOT EXISTS breakout_track_log (
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    from_date DATE NOT NULL,
    as_of DATE NOT NULL,
    status TEXT NOT NULL,
    close DOUBLE PRECISION,
    rel_volume DOUBLE PRECISION,
    detail TEXT,
    PRIMARY KEY (market, symbol, from_date, as_of)
);
"""

_PLAN = re.compile(r"at ([\d.,]+) \(close (\d{4}-\d{2}-\d{2})\)\. Pivot ([\d.,]+), stop ([\d.,]+)")
_STATUS_LINE = re.compile(r"^Status \d{4}-\d{2}-\d{2}:[^\n]*\n?")
FINAL = ("stopped", "failed", "success", "expired")


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def parse_plan(note: str | None) -> dict | None:
    """The plan written in a note: {from_date, ref_price, pivot, stop}, or None when it has none."""
    m = _PLAN.search(note or "")
    if not m:
        return None
    f = lambda s: float(s.replace(",", ""))  # noqa: E731
    return {"ref_price": f(m.group(1)), "from_date": m.group(2), "pivot": f(m.group(3)), "stop": f(m.group(4))}


def judge(bars: pd.DataFrame, plan: dict) -> dict:
    """What happened to `plan` on `bars` (daily OHLCV, dated index, the full history so the volume average has
    its look-back). Returns {status, as_of, breakout_date, close, rel_volume, detail}."""
    pivot, stop = plan["pivot"], plan["stop"]
    risk = pivot - stop
    avg = bars["volume"].rolling(VOLUME_AVG).mean().shift(1)     # the sessions before, not the day itself
    after = bars[bars.index > pd.Timestamp(plan["from_date"])]
    out = {"status": "waiting", "as_of": None, "breakout_date": None, "close": None, "rel_volume": None,
           "detail": "no session since the plan yet"}
    if after.empty:
        return out
    last = after.index[-1]
    rv = lambda d: float(after.at[d, "volume"] / avg.at[d]) if avg.at[d] else None  # noqa: E731
    out.update(as_of=str(last.date()), close=float(after.at[last, "close"]), rel_volume=rv(last))
    light = None
    bo = None
    for i, d in enumerate(after.index):
        c = float(after.at[d, "close"])
        if bo is None:
            if c < stop:
                return {**out, "status": "stopped", "detail": f"closed {c:.2f} below the stop {stop:.2f} on "
                                                              f"{d.date()} before breaking out"}
            if c > pivot:
                v = rv(d)
                if v is not None and v >= BREAKOUT_VOLUME:
                    bo = i
                    out["breakout_date"] = str(d.date())
                    continue
                light = light or (d, v)
            if i + 1 >= WINDOW_SESSIONS:
                return {**out, "status": "expired", "detail": f"no breakout on volume in {WINDOW_SESSIONS} sessions"}
            continue
        # after the breakout
        if c < stop:
            return {**out, "status": "stopped", "detail": f"broke out {out['breakout_date']}, then closed {c:.2f} "
                                                          f"below the stop on {d.date()}"}
        if i - bo <= FAIL_SESSIONS and c < pivot:
            return {**out, "status": "failed", "detail": f"broke out {out['breakout_date']}, closed back below the "
                                                         f"pivot {pivot:.2f} on {d.date()}"}
        if float(after.at[d, "high"]) >= pivot + TARGET_R * risk:
            return {**out, "status": "success", "detail": f"broke out {out['breakout_date']}, reached +{TARGET_R:g}R "
                                                          f"({pivot + TARGET_R * risk:.2f}) on {d.date()}"}
        if i - bo >= WINDOW_SESSIONS:
            return {**out, "status": "expired", "detail": f"broke out {out['breakout_date']}, no +{TARGET_R:g}R in "
                                                          f"{WINDOW_SESSIONS} sessions"}
    n = len(after)
    if bo is not None:
        bo_close = float(after.iloc[bo]["close"])
        r_now = (out["close"] - pivot) / risk if risk else 0.0
        return {**out, "status": "open", "detail": f"broke out {out['breakout_date']} at {bo_close:.2f} "
                                                   f"({after.iloc[bo]['volume'] / avg.iloc[avg.index.get_loc(after.index[bo])]:.1f}x volume); "
                                                   f"now {out['close']:.2f}, {r_now:+.1f}R"}
    gap = (pivot / out["close"] - 1) * 100
    extra = (f"; closed above it on light volume on {light[0].date()} ({light[1]:.1f}x)" if light and light[1] else "")
    return {**out, "detail": f"{gap:+.1f}% to the pivot {pivot:.2f} after {n} session(s){extra}"}


def run(market: str) -> dict:
    """Judge every tracked stock of `market` on the stored bars; store the verdicts and update the notes."""
    from . import watchlist as wl
    init_schema()
    lid = wl.list_id(LIST_NAME)
    if lid is None:
        return {"tracked": 0, "note": f"no watchlist named {LIST_NAME!r}"}
    counts: dict[str, int] = {}
    lines = []
    conn = db.get_connection()
    for it in wl.items(lid):
        if it["market"] != market:
            continue
        sym = it["symbol"]
        with conn.cursor() as cur:
            cur.execute("SELECT from_date, ref_price, pivot, stop, status FROM breakout_track WHERE market=%s AND symbol=%s "
                        "ORDER BY from_date DESC LIMIT 1", (market, sym))
            row = cur.fetchone()
        if row:
            plan = {"from_date": str(row[0]), "ref_price": row[1], "pivot": row[2], "stop": row[3]}
            if row[4] in FINAL:
                counts[row[4]] = counts.get(row[4], 0) + 1
                continue
        else:
            plan = parse_plan(it["note"])
            if not plan:
                counts["no plan"] = counts.get("no plan", 0) + 1
                continue
            with conn.cursor() as cur:
                cur.execute("INSERT INTO breakout_track (market, symbol, from_date, ref_price, pivot, stop) "
                            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                            (market, sym, plan["from_date"], plan["ref_price"], plan["pivot"], plan["stop"]))
        bars = cache.load_cached(market, sym)
        if bars is None or bars.empty:
            continue
        v = judge(bars, plan)
        with conn.cursor() as cur:
            cur.execute("UPDATE breakout_track SET status=%s, status_date=%s, breakout_date=%s, detail=%s, updated_at=now() "
                        "WHERE market=%s AND symbol=%s AND from_date=%s",
                        (v["status"], v["as_of"], v["breakout_date"], v["detail"], market, sym, plan["from_date"]))
            if v["as_of"]:
                cur.execute("INSERT INTO breakout_track_log (market, symbol, from_date, as_of, status, close, rel_volume, detail) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (market, symbol, from_date, as_of) DO UPDATE "
                            "SET status=EXCLUDED.status, close=EXCLUDED.close, rel_volume=EXCLUDED.rel_volume, detail=EXCLUDED.detail",
                            (market, sym, plan["from_date"], v["as_of"], v["status"], v["close"], v["rel_volume"], v["detail"]))
        if v["as_of"]:
            body = _STATUS_LINE.sub("", it["note"] or "")
            wl.set_item_note(lid, market, sym, f"Status {v['as_of']}: {v['status'].upper()} -- {v['detail']}\n{body}")
        counts[v["status"]] = counts.get(v["status"], 0) + 1
        if v["status"] not in ("waiting",):
            lines.append(f"{sym.split('.')[0]} {v['status']}")
    return {"tracked": sum(counts.values()), "counts": counts, "moves": lines}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--market", required=True)
    a = ap.parse_args()
    with cache.offline():
        print(run(a.market))


if __name__ == "__main__":
    main()
