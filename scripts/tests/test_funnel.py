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


def main() -> int:
    bad = _problems() + _symbol_problems()
    if bad:
        print("FAIL — funnel:")
        for b in bad:
            print("  " + b)
        return 1
    print("OK — funnel arithmetic, units, reason grouping and per-stage names behave")
    return 0


if __name__ == "__main__":
    sys.exit(main())
