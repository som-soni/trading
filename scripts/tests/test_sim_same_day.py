"""A fill sees only what had happened by its own moment in the session (`portfolio_sim`).

Each case below failed before 2026-10-31, when the simulator read the session's close to decide
something that happened earlier in it:

  1. a position sold at today's close freed its slot for an order that filled at today's open;
  2. a resting order was cancelled on the market filter computed from today's close;
  3. a fill was sized with today's closing marks of the other positions;
  4. a buy that traded back through its stop on the fill bar survived to the next session.

And the cases that must NOT move: an exit at the open still frees its slot for an open fill, and an
order that buys the close still sees the whole session (kullamagi's close orders).

No database: the bars are synthetic.

    PYTHONPATH=. .venv/bin/python -m tests.test_sim_same_day
"""

import dataclasses

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS

CFG = dataclasses.replace(MARKETS["india"], slippage_bps=0.0, commission_per_order=0.0, risk_pct=0.01,
                          max_position_pct=1.0, account_size=1_000_000)
FLAT = (100, 101, 99, 100)


def _frame(bars: list[tuple], sma50: list[float] | None = None) -> pd.DataFrame:
    """bars: (open, high, low, close) from 2024-01-01, business days; sma50 defaults to 50 (never broken)."""
    idx = pd.bdate_range("2024-01-01", periods=len(bars))
    df = pd.DataFrame([dict(open=b[0], high=b[1], low=b[2], close=b[3], volume=1000.0) for b in bars], index=idx)
    df["atr14"], df["sma50"] = 2.0, sma50 if sma50 is not None else 50.0
    return df


def _sig(df, day: int, sym: str, entry=100.0, stop=90.0, target=1000.0, quality=1.0, **meta) -> Signal:
    return Signal(date=df.index[day], symbol=sym, setup="S", entry=entry, stop=stop, target=target,
                  decision="TRADE - HIGH CONFIDENCE", quality=quality, meta=dict(meta))


def _trade(res, sym):
    return next((t for t in res.trades if t.symbol == sym), None)


def test_close_exit_does_not_free_a_slot_for_an_open_fill():
    # A is bought at day 1's open and closes below its 50-day on day 3 (TREND_EXIT at that close);
    # B's open order fills at day 3's open, when A was still held and the only slot was taken
    a = _frame([FLAT] * 6, sma50=[50, 50, 50, 200, 50, 50])
    b = _frame([FLAT] * 6)
    res = simulate([_sig(a, 0, "A", order="open"), _sig(b, 2, "B", order="open")], {"A": a, "B": b}, CFG,
                   a.index[0], max_positions=1, exit_policy=ExitPolicy(mode="ma", use_target=False))
    ta = _trade(res, "A")
    assert ta.exit_reason == "TREND_EXIT" and ta.exit_date == a.index[3], ta
    assert _trade(res, "B") is None and res.signals_missed_no_slot == 1, res.trades


def test_open_exit_still_frees_a_slot_for_an_open_fill():
    # the same, but A gaps through its stop at day 3's open: sold before B's fill, so B takes the slot
    a = _frame([FLAT, FLAT, FLAT, (85, 86, 84, 85), FLAT, FLAT])
    b = _frame([FLAT] * 6)
    res = simulate([_sig(a, 0, "A", order="open"), _sig(b, 2, "B", order="open")], {"A": a, "B": b}, CFG,
                   a.index[0], max_positions=1, exit_policy=ExitPolicy(mode="ma", use_target=False))
    assert _trade(res, "A").exit_reason == "STOP"
    tb = _trade(res, "B")
    assert tb is not None and tb.entry_date == b.index[3], res.trades


def test_close_order_sees_the_whole_session():
    # kullamagi: A (a close order on day 0) is sold at day 2's close on its time stop; B's close
    # order on day 2 buys that same close and takes the slot, as it always did
    a = _frame([FLAT] * 5)
    b = _frame([FLAT] * 5)
    pol = ExitPolicy(mode="kullamagi", use_target=False, km_max_bars=2, km_partial_bars=0)
    res = simulate([_sig(a, 0, "A", order="close"), _sig(b, 2, "B", order="close")], {"A": a, "B": b}, CFG,
                   a.index[0], max_positions=1, exit_policy=pol)
    ta, tb = _trade(res, "A"), _trade(res, "B")
    assert ta.exit_reason == "TIME" and ta.exit_date == a.index[2], ta
    assert tb is not None and tb.entry_date == b.index[2], res.trades


def test_resting_order_is_cancelled_on_the_previous_sessions_filter():
    # a buy-stop placed on day 0 triggers on day 2; the filter turns risk-off on day 2's CLOSE
    x = _frame([FLAT, FLAT, (100, 103, 99, 102), FLAT, FLAT])
    sig = _sig(x, 0, "X", entry=102.0, stop=95.0)
    late = pd.Series([True, True, False, False, False], index=x.index)
    res = simulate([sig], {"X": x}, CFG, x.index[0], regime_ok=late)
    t = _trade(res, "X")
    assert t is not None and t.entry_date == x.index[2], res.skipped        # unknown at the fill
    early = pd.Series([True, False, False, False, False], index=x.index)  # risk-off on day 1's close
    res = simulate([sig], {"X": x}, CFG, x.index[0], regime_ok=early)
    assert not res.trades and res.skipped.get("cancelled: market filter is risk-off") == 1, res.skipped
    # no reading yet (the benchmark starts later) is risk-off, not open
    unborn = pd.Series([True] * 2, index=x.index[3:])
    res = simulate([sig], {"X": x}, CFG, x.index[0], regime_ok=unborn)
    assert not res.trades, res.trades


def test_sizing_reads_the_previous_close_of_other_positions():
    # A is held from day 1; B fills at day 3's open. A's day-3 close is 100 or 300: B's size must not care
    def b_shares(a_close_day3: float) -> int:
        a = _frame([FLAT, FLAT, FLAT, (100, a_close_day3 + 1, 99, a_close_day3), FLAT])
        b = _frame([FLAT] * 5)
        res = simulate([_sig(a, 0, "A", order="open"), _sig(b, 2, "B", order="open", quality=0.5)],
                       {"A": a, "B": b}, CFG, a.index[0], max_positions=5, exit_policy=ExitPolicy(use_target=False))
        return _trade(res, "B").shares
    assert b_shares(100.0) == b_shares(300.0), (b_shares(100.0), b_shares(300.0))


def test_open_risk_cap_reads_the_previous_close():
    # the cap is on capital at risk, priced at the entry or below; A falling to 92 by day 3's close
    # (stop 90) would shrink its risk and let B in, which is not known at B's open
    def b_taken(a_close_day3: float) -> bool:
        a = _frame([FLAT, FLAT, FLAT, (100, 101, a_close_day3 - 0.5, a_close_day3), FLAT])
        b = _frame([FLAT] * 5)
        res = simulate([_sig(a, 0, "A", order="open"), _sig(b, 2, "B", order="open", quality=0.5)],
                       {"A": a, "B": b}, CFG, a.index[0], max_positions=5, max_open_risk_pct=0.015,
                       exit_policy=ExitPolicy(use_target=False))
        return _trade(res, "B") is not None
    assert b_taken(100.0) == b_taken(92.0) is False


def test_fill_bar_through_the_stop_is_stopped():
    # a buy-stop at 100 fills on day 1, and the same bar trades down to 94 (stop 95)
    x = _frame([FLAT, (99, 101, 94, 100), FLAT, FLAT])
    for mode in ("bracket", "ma", "trail_atr"):
        res = simulate([_sig(x, 0, "X", entry=100.5, stop=95.0)], {"X": x}, CFG, x.index[0],
                       exit_policy=ExitPolicy(mode=mode, use_target=False))
        t = res.trades[0]
        assert t.exit_reason == "STOP" and t.exit_date == x.index[1] and t.exit_price == 95.0, (mode, t)
    # an open fill whose bar then falls through the stop: unambiguous, the whole bar came after
    res = simulate([_sig(x, 0, "X", entry=99.0, stop=95.0, order="open")], {"X": x}, CFG, x.index[0],
                   exit_policy=ExitPolicy(mode="ma", use_target=False))
    t = res.trades[0]
    assert t.exit_reason == "STOP" and t.exit_date == x.index[1], t
    # a fill bar that stays above the stop is untouched
    res = simulate([_sig(x, 0, "X", entry=100.5, stop=93.0)], {"X": x}, CFG, x.index[0],
                   exit_policy=ExitPolicy(mode="ma", use_target=False))
    assert res.trades[0].exit_reason == "OPEN", res.trades[0]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
