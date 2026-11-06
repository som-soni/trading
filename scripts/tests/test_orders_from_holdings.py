"""Rebalance orders start from what you actually hold, not from the replayed model book.

With a rank buffer (`hold_rank` > `top_n`) the rule keeps a held stock while it ranks within
`hold_rank`, so the decision depends on what is held going in. The live view used to feed in the
MODEL's holdings (36 month-ends replayed from an empty book); a stock you bought and the model did not
would then be sold although the rule keeps it. `current_selection(held_now=...)` takes your holdings
(`_selection_rows` is its uncached step), and `rebalance.orders` passes the ledger's.

Checked here, on a synthetic ranking and no database:
  * a held stock ranked between top_n and hold_rank is kept (HOLD), though the model does not hold it;
  * a held stock ranked outside hold_rank, or no longer eligible, is sold;
  * free slots go to the best-ranked names you do not hold;
  * without a buffer the book is the plain top N whatever you hold, and equals the model's;
  * with the regime off nothing is held;
  * the drift lists both directions.

    PYTHONPATH=. .venv/bin/python -m tests.test_orders_from_holdings
"""

import sys

import pandas as pd

from swing_screener.backtesting import baseline, rebalance

FAILS: list[str] = []
TOP_N, HOLD_RANK = 5, 10
RANKED = [f"R{i:02d}.NS" for i in range(1, 31)]          # R01 best


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


class Strat:
    top_n, hold_rank, cost_bps = TOP_N, HOLD_RANK, 10.0

    @staticmethod
    def spec_id():
        return "v0-test"


def state(buffered=True, regime_on=True, model=None):
    today = pd.Timestamp("2026-11-05")
    mom = {s: 1.0 - i / 100 for i, s in enumerate(RANKED)}
    return {"today": today, "mom": mom, "full": list(RANKED), "rank_of": {s: i + 1 for i, s in enumerate(RANKED)},
            "model_held": list(model if model is not None else RANKED[:TOP_N]) if regime_on else [],
            "replay_book": [], "replayed": 36, "regime": {"kind": "test", "on": regime_on}, "buffered": buffered,
            "hold_rank": HOLD_RANK, "weighting": "equal", "vol_today": None,
            "close": pd.Series(100.0, index=RANKED), "turnover": None}


def test_selection() -> None:
    print("the selection from your holdings")
    mine = {"R08.NS", "R12.NS", "R02.NS"}            # rank 8 inside the band, 12 outside it
    sel = baseline._selection_rows(state(), "india", "t", Strat, None, mine)
    held = set(sel["held"])
    check("a held stock ranked between top_n and hold_rank is kept", "R08.NS" in held, str(sorted(held)))
    check("a held stock ranked outside hold_rank is dropped", "R12.NS" not in held, str(sorted(held)))
    check("a held stock in the top N stays", "R02.NS" in held)
    check("free slots go to the best names not held", held == {"R01.NS", "R02.NS", "R03.NS", "R04.NS", "R08.NS"},
          str(sorted(held)))
    check("the model book is returned beside it", sel["model_held"] == RANKED[:TOP_N])
    check("a kept stock below the top N is listed", any(r["symbol"] == "R08.NS" and r["held"] for r in sel["rows"]))
    gone = baseline._selection_rows(state(), "india", "t", Strat, None, {"NOTELIGIBLE.NS", "R09.NS"})
    check("a held stock no longer eligible is dropped", "NOTELIGIBLE.NS" not in gone["held"]
          and "R09.NS" in gone["held"], str(gone["held"]))
    model = baseline._selection_rows(state(), "india", "t", Strat, None, None)
    check("without held_now the book is the model's", model["held"] == RANKED[:TOP_N] and not model["from_holdings"])
    plain = baseline._selection_rows(state(buffered=False), "india", "t", Strat, None, mine)
    check("without a buffer the book is the plain top N whatever you hold", plain["held"] == RANKED[:TOP_N],
          str(plain["held"]))
    off = baseline._selection_rows(state(regime_on=False), "india", "t", Strat, None, mine)
    check("regime off: nothing is held", off["held"] == [])
    eq = [r["weight_pct"] for r in sel["rows"] if r["held"]]
    check("equal weights over the book you would hold", len(eq) == TOP_N and all(abs(w - 20.0) < 1e-9 for w in eq),
          str(eq))


def test_orders() -> None:
    print("the orders from your ledger")
    positions = {"R08.NS": 10.0, "R12.NS": 10.0, "R02.NS": 10.0}
    acct = {"positions": positions, "cash": 2000.0, "updated_at": None}
    seen = {}

    def fake_sel(market, key, limit=None, replay_months=36, held_now=None):
        seen["held_now"] = held_now
        return baseline._selection_rows(state(), market, key, Strat, limit, held_now)

    orig = (baseline.current_selection, rebalance.get_positions, rebalance._last_closes)
    import swing_screener.strategies as strategies
    orig_ps = strategies.portfolio_strategies
    try:
        baseline.current_selection = fake_sel
        rebalance.get_positions = lambda b, m: acct
        rebalance._last_closes = lambda m, syms, as_of: {s: 100.0 for s in syms}
        strategies.portfolio_strategies = lambda: {"t": Strat}
        o = rebalance.orders("t", "india")
    finally:
        baseline.current_selection, rebalance.get_positions, rebalance._last_closes = orig
        strategies.portfolio_strategies = orig_ps
    act = {r["symbol"]: r["action"] for r in o["rows"]}
    check("the ledger's holdings are what the selection starts from", seen["held_now"] == set(positions),
          str(seen["held_now"]))
    check("R08 (rank 8, inside the band) is kept, not sold", act.get("R08.NS") in ("HOLD", "ADD", "TRIM"), str(act))
    check("R12 (rank 12, outside the band) is sold", act.get("R12.NS") == "SELL ALL", str(act))
    check("the best names not held are bought", all(act.get(s) == "BUY" for s in ("R01.NS", "R03.NS", "R04.NS")),
          str(act))
    check("the model's R05 is not bought: the slot is R08's", "R05.NS" not in act, str(act))
    check("drift: the model holds R01 R03 R04 R05 that you do not",
          o["drift"]["model_only"] == ["R01.NS", "R03.NS", "R04.NS", "R05.NS"], str(o["drift"]))
    check("drift: you hold R08 R12 that the model does not", o["drift"]["held_only"] == ["R08.NS", "R12.NS"],
          str(o["drift"]))
    total = 2000.0 + 3 * 10 * 100.0
    check("each target is a whole-share fifth of the account", all(
        r["target"] == int(total * 0.2 // 100.0) for r in o["rows"] if r["weight_pct"]), str(o["rows"]))


def main() -> int:
    test_selection()
    test_orders()
    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'orders start from your holdings'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
