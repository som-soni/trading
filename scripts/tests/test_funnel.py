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


def main() -> int:
    bad = _problems()
    if bad:
        print("FAIL — funnel:")
        for b in bad:
            print("  " + b)
        return 1
    print("OK — funnel arithmetic, units and reason grouping behave")
    return 0


if __name__ == "__main__":
    sys.exit(main())
