"""The two order mechanics the donchian review (2026-11-14) found in the shared simulator.

  1. Crumbs. A full book bought whatever cash was left -- often ~0.02% of equity -- and that position
     held a slot for weeks. `min_fill_frac` (`--min-fill`) skips a fill the cash allows less than that
     fraction of its planned shares; a fill above it is still cut to the cash, as before.
  2. Late fills. A resting buy-stop that triggered with every slot full kept resting to its own expiry
     and filled whenever a slot freed, carrying the stop planned at the signal. `slot_wait_bdays`
     (`--slot-wait`, or meta["slot_wait_bdays"]) bounds that wait; 0 drops it on the session it
     triggers. The per-fill re-tests (meta["max_fill"], meta["max_risk_pct"]) apply to a late fill
     against the price actually paid.

Both are off by default, and the defaults are pinned here: a crumb is still bought, a late fill still
fills. Each trade also records its signal date and how many sessions it waited for a slot.

Synthetic bars, no database and no cached prices.

    PYTHONPATH=. .venv/bin/python -m tests.test_fill_mechanics
"""

import dataclasses
import sys

import pandas as pd

from swing_screener.backtesting.portfolio_sim import (
    MIN_FILL_SKIP, SLOT_WAIT_LAPSE, ExitPolicy, Signal, simulate, trades_to_df,
)
from swing_screener.config import MARKETS

FAILS: list[str] = []
CFG = dataclasses.replace(MARKETS["india"], slippage_bps=0.0, commission_per_order=0.0, risk_pct=0.01,
                          max_position_pct=1.0, account_size=1_000_000)
POLICY = ExitPolicy(mode="bracket", use_target=False)
FLAT = (100, 101, 99, 100)


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _frame(bars: list[tuple]) -> pd.DataFrame:
    """bars: (open, high, low, close) from 2024-01-01, business days."""
    idx = pd.bdate_range("2024-01-01", periods=len(bars))
    df = pd.DataFrame([dict(open=b[0], high=b[1], low=b[2], close=b[3], volume=1000.0) for b in bars], index=idx)
    df["atr14"], df["sma50"] = 2.0, 50.0
    return df


def _sig(df, day: int, sym: str, entry=100.0, stop=90.0, quality=1.0, **meta) -> Signal:
    return Signal(date=df.index[day], symbol=sym, setup="S", entry=entry, stop=stop, target=1e9,
                  decision="TRADE - HIGH CONFIDENCE", quality=quality, meta=dict(meta))


def _trade(res, sym):
    return next((t for t in res.trades if t.symbol == sym), None)


def crumbs() -> None:
    print("crumb fills (min_fill_frac)")
    a, b = _frame([FLAT] * 6), _frame([FLAT] * 6)
    # A: risk 1% of 1,000,000 over 1.0005 a share -> 9,995 shares at 100, leaving 500 in cash.
    # B: risk 10,000 over 10 a share -> 1,000 shares planned; the 500 buys 5 of them (0.5%).
    sigs = [_sig(a, 0, "A", stop=98.9995, order="open"), _sig(b, 1, "B", order="open")]
    px = {"A": a, "B": b}

    res = simulate(sigs, px, CFG, a.index[0], max_positions=5, exit_policy=POLICY)
    tb = _trade(res, "B")
    check("default: the crumb is bought, cut to the cash (5 of 1,000 shares)",
          tb is not None and tb.shares == 5 and res.partial_fills == 1, repr(tb))

    res = simulate(sigs, px, CFG, a.index[0], max_positions=5, exit_policy=POLICY, min_fill_frac=0.5)
    why = MIN_FILL_SKIP.format(pct=50)
    check("with 0.5 the crumb is skipped and named", _trade(res, "B") is None and res.skipped.get(why) == 1,
          repr(res.skipped))
    check("...and the session it was refused on is recorded for the funnel",
          res.skipped_at.get(why) == [("B", b.index[2])], repr(res.skipped_at))
    check("...and it is not also counted as 'not enough cash'", res.signals_missed_no_cash == 0)

    # A takes 30% (3,000 shares); B plans 10,000 shares (stop 99) and the cash buys 7,000: 70% is kept
    sigs = [_sig(a, 0, "A", stop=100 - 10_000 / 3_000, order="open"), _sig(b, 1, "B", stop=99.0, order="open")]
    res = simulate(sigs, px, CFG, a.index[0], max_positions=5, exit_policy=POLICY, min_fill_frac=0.5)
    tb = _trade(res, "B")
    check("a 70% fill is still bought, cut to the cash", tb is not None and tb.shares == 7_000, repr(tb))

    for bad in (0, 1.5):
        try:
            simulate(sigs, px, CFG, a.index[0], exit_policy=POLICY, min_fill_frac=bad)
            check(f"min_fill_frac={bad} is refused", False)
        except ValueError:
            check(f"min_fill_frac={bad} is refused", True)


def late_fills() -> None:
    print("late fills (slot_wait_bdays, and the re-tests at the price paid)")
    # One slot. A is bought at day 1's open (stop 97) and stopped on day 6 (low 96). B's buy-stop at
    # 100.5 is placed on day 1 and triggers on days 2-5 with no slot free; day 6 stays under it, and
    # day 7 opens at 106 -- so it fills there, well past where it was planned.
    a = _frame([FLAT, FLAT, FLAT, FLAT, FLAT, FLAT, (100, 101, 96, 97), FLAT, FLAT, FLAT])
    up = (106, 108, 105, 107)
    b = _frame([FLAT, FLAT, FLAT, FLAT, FLAT, FLAT, (99, 100, 98, 99), up, up, up])
    px = {"A": a, "B": b}

    def run(b_meta=None, **kw):
        sigs = [_sig(a, 0, "A", stop=97.0, order="open"),
                _sig(b, 1, "B", entry=100.5, stop=95.0, **(b_meta or {}))]
        return simulate(sigs, px, CFG, a.index[0], max_positions=1, exit_policy=POLICY, **kw)

    res = run()
    tb = _trade(res, "B")
    check("default: the order waits for the slot and fills late, at 106 with the planned stop 95",
          tb is not None and tb.entry_date == b.index[7] and tb.entry_price == 106.0 and tb.initial_stop == 95.0,
          repr(tb))
    check("...and the trade records its signal date and the sessions it waited",
          tb is not None and tb.signal_date == b.index[1] and tb.slot_waits == 4, repr(tb))
    row = trades_to_df(res.trades).set_index("symbol").loc["B"]
    check("...which reach the trades table", row["slot_waits"] == 4 and str(row["signal_date"]) == "2024-01-02",
          repr(row.to_dict()))

    res = run(slot_wait_bdays=0)
    check("slot_wait 0: dropped on the session it triggers with no slot", _trade(res, "B") is None
          and res.signals_missed_no_slot == 1, repr(res.trades))

    res = run(slot_wait_bdays=2)
    check("slot_wait 2: lapses two business days after its first refusal, named",
          _trade(res, "B") is None and res.skipped_at.get(SLOT_WAIT_LAPSE) == [("B", b.index[5])],
          repr(res.skipped_at))

    res = run(b_meta={"slot_wait_bdays": 0})
    check("a signal's own slot_wait_bdays wins over the run's (None here)", _trade(res, "B") is None)
    res = run(b_meta={"slot_wait_bdays": 10}, slot_wait_bdays=0)
    check("...and over a run-level 0", _trade(res, "B") is not None)

    res = run(b_meta={"max_fill": 100.5 * 1.03})
    check("a late fill past the anti-chase ceiling (max_fill) is skipped at the price paid",
          _trade(res, "B") is None and res.skipped.get("gapped above the buy range") == 1, repr(res.skipped))
    res = run(b_meta={"max_risk_pct": 0.08})
    check("a late fill whose planned stop is too far below the price paid (max_risk_pct) is skipped",
          _trade(res, "B") is None and res.skipped.get("stop too far below the fill") == 1, repr(res.skipped))

    # a fill on the session after the signal is untouched by any of it
    res = run(slot_wait_bdays=0, min_fill_frac=0.5, b_meta={"max_fill": 103.0, "max_risk_pct": 0.08})
    check("next-session fills are unchanged (A, signal day 0, filled day 1)",
          _trade(res, "A") is not None and _trade(res, "A").slot_waits == 0
          and _trade(res, "A").signal_date == a.index[0], repr(_trade(res, "A")))


def main() -> None:
    crumbs()
    late_fills()
    if FAILS:
        print(f"\nFAILED: {len(FAILS)}")
        sys.exit(1)
    print("\nOK — crumb fills and slot waits are opt-in, and late fills are re-tested at the price paid.")


if __name__ == "__main__":
    main()
