"""The funnel's arithmetic and its reason-grouping.

Two things here are easy to get wrong and expensive to notice:

  * a drop belongs to the stage an item is LEAVING, so that drops[X] explains
    the fall from X to the stage after it. Recording it against the stage the
    item failed to reach puts every reason one row too low.
  * reasons are normalised so one rejection phrased with a different number each
    time collapses into one row -- but a gate code is an identifier, not a
    quantity, and normalising its digits merges TT-03 with TT-05 and throws away
    exactly what the funnel exists to show.

    PYTHONPATH=. .venv/bin/python -m tests.test_funnel
"""

import sys

from swing_screener.backtesting import funnel as F


def _problems() -> list[str]:
    bad: list[str] = []
    n = F.normalise

    # gate codes keep their digits and stay distinct
    for code in ("hard gate TT-03", "VCP-06", "hard gate B3", "DC-02", "MV-01"):
        if n(code) != code:
            bad.append(f"normalise mangled the gate code {code!r} -> {n(code)!r}")
    if n("hard gate TT-03") == n("hard gate TT-05"):
        bad.append("TT-03 and TT-05 collapsed into one reason")
    if n("VCP-06") == n("VCP-04"):
        bad.append("VCP-06 and VCP-04 collapsed into one reason")

    # the same sentence with a different measurement is one reason
    a = n("projects only 0.90R against the 2:1 minimum")
    b = n("projects only 1.81R against the 2:1 minimum")
    if a != b:
        bad.append(f"numeric variants did not collapse: {a!r} vs {b!r}")
    if n(None) != "unspecified" or n("") != "unspecified":
        bad.append("an empty reason should read 'unspecified'")

    # arithmetic: 'lost here' is count - next count, within one unit only
    fn = F.Funnel()
    fn.set_count("symbols", 100)
    fn.set_count("candidates", 40)
    fn.dropped("symbols", "never passed the pre-filter in the window", 60)
    fn.reached("bars", 1000)
    fn.dropped("bars", "hard gate TT-03", 700)
    fn.dropped("bars", "hard gate TT-05", 100)
    fn.reached("hard_gates", 200)
    rows = {r["stage"]: r for r in fn.rows()}

    if rows["symbols"]["count"] != 100 or rows["candidates"]["count"] != 40:
        bad.append("symbol counts not recorded as set")
    if [d["reason"] for d in rows["bars"]["drops"]] != ["hard gate TT-03", "hard gate TT-05"]:
        bad.append(f"bar drops should be two distinct gates, got {rows['bars']['drops']}")
    if sum(d["count"] for d in rows["bars"]["drops"]) != 800:
        bad.append("bar drop counts do not sum to 800")

    md = fn.render_md()
    # candidates (symbols) -> bars (bars) crosses a unit boundary: no subtraction
    cand_line = next(l for l in md.splitlines() if l.startswith("| Pass the pre-filter"))
    if cand_line.split("|")[3].strip():
        bad.append(f"'lost here' was printed across a unit change: {cand_line}")
    sym_line = next(l for l in md.splitlines() if l.startswith("| Symbols in the universe"))
    if sym_line.split("|")[3].strip() != "60":
        bad.append(f"symbols -> candidates should lose 60: {sym_line}")

    # merging per-symbol funnels must add up
    a_fn, b_fn = F.Funnel(), F.Funnel()
    a_fn.reached("bars", 3); a_fn.dropped("bars", "VCP-06", 2)
    b_fn.reached("bars", 4); b_fn.dropped("bars", "VCP-06", 5)
    a_fn.merge(b_fn)
    if a_fn.counts["bars"] != 7 or a_fn.drops["bars"]["VCP-06"] != 7:
        bad.append("merge() did not add counts and drops")
    return bad


def _symbol_problems() -> list[str]:
    """The names behind each stage: recorded, merged and capped.

    The counts and the names are two different quantities — a stage counts BARS while
    its name list counts the stocks that reached it on any bar — so the one thing that
    must hold is that a name never appears at a stage the stock did not reach.
    """
    bad = []
    f = F.Funnel()
    f.set_count("symbols", 4)
    f.set_symbols("candidates", ["A", "B", "C"])
    f.set_count("candidates", 3)
    for sym in ("A", "B", "C"):
        f.reached("bars", 10, symbol=sym)
    f.reached("hard_gates", 5, symbol="A")
    f.reached("hard_gates", 5, symbol="B")
    f.dropped("bars", "hard gate VCP-02", 5, symbol="C")
    rows = {r["stage"]: r for r in f.rows()}

    if rows["hard_gates"]["symbols"] != ["A", "B"]:
        bad.append(f"hard_gates named {rows['hard_gates']['symbols']}, expected ['A', 'B']")
    if "C" in rows["hard_gates"]["symbols"]:
        bad.append("C never reached hard_gates but is named there")
    drop = next(d for d in rows["bars"]["drops"] if d["reason"] == "hard gate VCP-02")
    if drop["symbols"] != ["C"]:
        bad.append(f"the VCP-02 drop named {drop['symbols']}, expected ['C']")

    # a bulk set replaces rather than adds to, so a later narrowing (--symbols) cannot
    # leave a stage naming more stocks than its own count
    f.set_symbols("candidates", ["A"])
    if {r["stage"]: r for r in f.rows()}["candidates"]["symbols"] != ["A"]:
        bad.append("set_symbols must replace the stage's names, not union with them")

    # merging two per-symbol funnels keeps both sets
    a, b = F.Funnel(), F.Funnel()
    a.reached("setup", 1, symbol="A")
    b.reached("setup", 1, symbol="B")
    a.merge(b)
    if {r["stage"]: r for r in a.rows()}["setup"]["symbols"] != ["A", "B"]:
        bad.append("merge lost one side's names")

    # a capped stage list must not be an alphabetical prefix. At 2,000 with sorted()[:n] the
    # `candidates` list on a US run stopped at NMIH, so NVDA read as "never reached this stage"
    # when it had -- the cap was deciding which stocks could be looked up.
    wide = F.Funnel()
    universe = [f"{c}{i:03d}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for i in range(200)]
    wide.set_symbols("candidates", universe)
    wide.set_count("candidates", len(universe))
    row = {r["stage"]: r for r in wide.rows()}["candidates"]
    if len(universe) > F.Funnel.MAX_STAGE_NAMES:
        bad.append("the fixture no longer exceeds the cap; raise it to keep testing truncation")
    kept = row["symbols"]
    if len(kept) != len(universe) or row["symbols_truncated"]:
        bad.append(f"a {len(universe)}-name universe was truncated at {len(kept)}; the cap is too low "
                   f"to hold a real run's candidates")
    sampled = F._capped(universe, 60)
    letters = {n[0] for n in sampled}
    if len(letters) < 20:
        bad.append(f"a truncated sample covered only {len(letters)} letters ({''.join(sorted(letters))}) "
                   f"— it is taking a prefix, not a spread")
    if sampled != sorted(sampled):
        bad.append("the sample is not sorted, so it cannot be scanned by eye")

    # the caps hold, and say so
    big = F.Funnel()
    many = [f"S{i:05d}" for i in range(F.Funnel.MAX_STAGE_NAMES + 50)]
    big.set_symbols("candidates", many)
    big.set_count("candidates", len(many))
    for sym in many:
        big.dropped("candidates", "too many", 1, symbol=sym)
    row = {r["stage"]: r for r in big.rows()}["candidates"]
    if len(row["symbols"]) != F.Funnel.MAX_STAGE_NAMES or not row["symbols_truncated"]:
        bad.append(f"stage names not capped: {len(row['symbols'])}, truncated={row['symbols_truncated']}")
    dn = row["drops"][0]
    if len(dn["symbols"]) > F.Funnel.MAX_DROP_NAMES:
        bad.append(f"drop names not capped: {len(dn['symbols'])}")
    if dn["count"] != len(many):
        bad.append("capping the names must not change the count")
    return bad


def _dated_problems() -> list[str]:
    """Drops after signal collection (portfolio filters, the simulator) name the stock AND the
    date. Without them a stored run cannot answer "why didn't CRWD trade in August?" -- it took a
    bar-by-bar replay to learn the results blackout had blocked its 08-14 and 08-17 signals."""
    import pickle
    from types import SimpleNamespace as Sig

    import pandas as pd

    bad = []
    f = F.Funnel()
    f.dropped_each("accepted", "results due within 14 days",
                   [Sig(symbol="CRWD", date=pd.Timestamp("2026-08-17")),
                    Sig(symbol="CRWD", date=pd.Timestamp("2026-08-14")),
                    Sig(symbol="NVDA", date=pd.Timestamp("2026-05-20"))])
    f.dropped_each("ranked", "all position slots full", [("TYL", pd.Timestamp("2021-03-02"))])
    f.dropped_each("ranked", "not enough cash", [])
    rows = {r["stage"]: r for r in f.rows()}
    rb = next(d for d in rows["accepted"]["drops"] if d["reason"] == "results due within # days")
    if rb["count"] != 3 or rb["symbols"] != ["CRWD", "NVDA"]:
        bad.append(f"dropped_each should count 3 and name CRWD, NVDA: {rb}")
    if rb.get("dates") != {"CRWD": ["2026-08-14", "2026-08-17"], "NVDA": ["2026-05-20"]}:
        bad.append(f"blackout dates wrong: {rb.get('dates')}")
    slot = next(d for d in rows["ranked"]["drops"] if d["reason"] == "all position slots full")
    if slot.get("dates") != {"TYL": ["2021-03-02"]}:
        bad.append(f"(symbol, date) pairs not recorded: {slot}")
    cash = next((d for d in rows["ranked"]["drops"] if d["reason"] == "not enough cash"), None)
    if cash is None or cash["count"] != 0 or "dates" in cash:
        bad.append(f"an empty drop should still be a zero row with no dates: {cash}")
    # a drop that does not know its date keeps the old shape
    f.dropped("bars", "VCP-06", 1, symbol="A")
    if "dates" in next(d for d in {r["stage"]: r for r in f.rows()}["bars"]["drops"]):
        bad.append("an undated drop grew a dates field")

    # dates follow the name cap: a symbol past MAX_DROP_NAMES is counted, not dated
    g = F.Funnel()
    many = [(f"S{i:04d}", "2024-01-02") for i in range(F.Funnel.MAX_DROP_NAMES + 10)]
    g.dropped_each("ranked", "open-risk cap", many)
    d = g.rows()[0]["drops"][0]
    if d["count"] != len(many) or len(d["symbols"]) != F.Funnel.MAX_DROP_NAMES \
            or set(d["dates"]) != set(d["symbols"]):
        bad.append("dates are not capped with the names, or the count moved")
    # and per symbol, only the most recent MAX_DROP_DATES are kept
    h = F.Funnel()
    days = pd.bdate_range("2020-01-01", periods=F.Funnel.MAX_DROP_DATES + 5)
    h.dropped_each("ranked", "all position slots full", [("X", t) for t in days])
    kept = h.rows()[0]["drops"][0]["dates"]["X"]
    if len(kept) != F.Funnel.MAX_DROP_DATES or kept[-1] != str(days[-1].date()):
        bad.append(f"per-symbol dates not capped to the most recent: {len(kept)}, last {kept[-1]}")

    # a worker's funnel still pickles, and merge carries its dates
    w = F.Funnel()
    w.dropped_each("accepted", "RS rating below 70", [("B", "2023-04-05")])
    w.drop_symbols = {st: dict(r) for st, r in w.drop_symbols.items()}
    w = pickle.loads(pickle.dumps(w))
    f.merge(w)
    rs = next(d for d in {r["stage"]: r for r in f.rows()}["accepted"]["drops"] if d["reason"].startswith("RS"))
    if rs.get("dates") != {"B": ["2023-04-05"]}:
        bad.append(f"merge lost the dates: {rs}")
    return bad


def main() -> int:
    bad = _problems() + _symbol_problems() + _dated_problems()
    if bad:
        print("FAIL — funnel:")
        for b in bad:
            print("  " + b)
        return 1
    print("OK — funnel arithmetic, units, reason grouping and per-stage names behave")
    return 0


if __name__ == "__main__":
    sys.exit(main())
