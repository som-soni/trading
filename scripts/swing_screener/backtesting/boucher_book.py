"""Boucher combined book — his stock, bond and gold timing models as three sleeves of one book.

Mark Boucher, *The Hedge Fund Edge* (Wiley, 1999), presents his timing models as inputs to one
top-down allocation, not as three all-in books. This runner holds them together at fixed weights:

    stocks  BOOK_STOCKS_PCT  the S&P 500 total return while boucher_stocks' base rule is in
                             (40-week trend + rates, with the 1.1 zero-bound floor); T-bills otherwise
    bonds   BOOK_BONDS_PCT   long Treasuries (TLT total return) while boucher_bonds_gold's
                             Bond-Bill-Utility model is in; T-bills otherwise
    gold    BOOK_GOLD_PCT    gold miners (GDX total return) while the Gold-Silver-GMI model is in;
                             T-bills otherwise

Each sleeve switches on its own model's weekly signal, filled at the close FILL_DELAY_SESSIONS later
and paying `cost_bps` a side on the sleeve (boucher_stocks.simulate, the same book the two single
strategies use). The sleeves are rebalanced back to their weights at each month's last session, paying
`cost_bps` on what moves. The rules of every model are imported, never restated here.

The weights come from the 2026-11-14 boucher_bonds_gold review's test plan (50/30/20) and were fixed
before any run. The comparisons, all total return and rebalanced the same way: the same weights held
untimed (`--mode hold_book`), 60/40 SPY/TLT and 60/40 SPY/IEF.
"""
from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd

from ..marketdata import index_data
from ..strategies.base import PortfolioStrategy
from . import boucher_bonds_gold as bg
from .boucher_stocks import (FILL_DELAY_SESSIONS, MARKET, SP_TICKER, SP_TR, TBILL, closes, context_boundary,
                             finish, long_yield, month_ends, simulate, sp_total_return, timing_target, to_sessions, week_ends)

logger = logging.getLogger("backtest")

MODES = ("book", "hold_book", "sixty_forty_tlt", "sixty_forty_ief")
IEF = "BONDS"                    # IEF total return (7-10 year Treasuries), from 2002-07

# ---- the weights, fixed before any run (the bonds_gold review's test plan)
BOOK_STOCKS_PCT = 50
BOOK_BONDS_PCT = 30
BOOK_GOLD_PCT = 20
SIXTY_FORTY_STOCKS_PCT = 60      # the conventional comparison: 60% SPY, 40% Treasuries

# ---- the pass criteria, fixed before any run (status has them in words)
PASS_SHARPE_MARGIN = 0.10        # Sharpe over T-bills at least this above the same weights held untimed
PASS_DD_SHALLOWER_PCT = 25       # max drawdown at least this % shallower than the untimed book's
PASS_MAX_CAGR_SHORTFALL = 2.0    # CAGR at most this many points below the untimed book's
NEIGHBOUR_STEP_PCT = 10          # the weights moved this many points, one pair at a time, must keep the margin
HALVES_SPLIT = "2017-07-03"      # the halves whose Sharpe differences must both be positive


# ------------------------------------------------------------------ the book

def bill_returns(rate: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """The T-bill return earned into each session, per calendar day, as `simulate` credits cash."""
    r = rate.reindex(index).ffill().fillna(0.0)
    days = index.to_series().diff().dt.days.fillna(0)
    return (1 + r.shift(1).fillna(0.0) / 365.0) ** days - 1


def mix(sleeves: dict[str, pd.Series], weights: dict[str, float], cost_bps: float,
        capital: float = 1.0) -> tuple[pd.Series, pd.DataFrame, float]:
    """Sleeve equity curves held at fixed weights, drifting between rebalances and set back to the
    weights at each month's last session, paying `cost_bps` on the value moved.

    -> (book equity, each sleeve's value, rebalancing costs)."""
    eq = pd.concat(sleeves, axis=1).dropna()
    rets = eq.pct_change().fillna(0.0)
    names = list(sleeves)
    w = np.array([weights[n] for n in names], float)
    w = w / w.sum()
    rebal = set(month_ends(eq.index))
    v = w * capital
    out, vals, paid = [], [], 0.0
    for d, r in zip(eq.index, rets.to_numpy(float)):
        v = v * (1 + r)
        if d in rebal:
            total = v.sum()
            fee = np.abs(w * total - v).sum() * cost_bps / 10_000
            paid += fee
            v = w * (total - fee)
        out.append(v.sum())
        vals.append(v.copy())
    return (pd.Series(out, index=eq.index), pd.DataFrame(vals, index=eq.index, columns=names), paid)


def book_stats(eq: pd.Series, rate: pd.Series, split: str = HALVES_SPLIT) -> dict:
    """CAGR, max drawdown, volatility and Sharpe over T-bills (daily, annualised), and the Sharpe of
    each half either side of `split`."""
    eq = eq.dropna()
    r = eq.pct_change().dropna()
    ex = r - bill_returns(rate, eq.index).reindex(r.index)

    def sharpe(x):
        return float(x.mean() / x.std() * np.sqrt(252)) if len(x) > 2 and x.std() > 0 else float("nan")

    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cut = pd.Timestamp(split)
    return {"cagr_pct": float(((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1) * 100),
            "max_dd_pct": float((eq / eq.cummax() - 1).min() * 100),
            "vol_pct": float(r.std() * np.sqrt(252) * 100),
            "sharpe": sharpe(ex), "sharpe_h1": sharpe(ex[ex.index < cut]), "sharpe_h2": sharpe(ex[ex.index >= cut])}


def sleeve_inputs():
    """Each sleeve's (price it earns, its fund's own close, the model's position wanted at each close,
    the first session the model has every input)."""
    tbill = index_data.load(MARKET, TBILL)
    sp = sp_total_return()
    want_s, _r = timing_target(closes(SP_TICKER), tbill, long_yield())
    bond = bg.long_bond()
    gold = index_data.load(MARKET, bg.GOLD_MINERS)
    out = {"stocks": (sp, closes(SP_TR), want_s, sp.index[0])}
    for name, price, fn, sym in (("bonds", bond, bg.bbu_state, "TLT"), ("gold", gold, bg.gold_state, bg.GDX)):
        state, _t = fn(week_ends(price.index))
        if state.dropna().empty:
            raise SystemExit(f"{name}: no week has every input before the window's end")
        out[name] = (price, closes(sym), to_sessions(state.fillna(False), price.index).astype(int),
                     state.dropna().index[0])
    return out


def build(start: str, mode: str, weights: tuple[float, float, float], cost_bps: float, capital: float):
    """-> (book equity, held sleeves, cash, trades, costs, start used, sleeve values)."""
    rate = (index_data.load(MARKET, TBILL) / 100.0).clip(lower=0.0)
    if mode.startswith("sixty_forty"):
        sym = "TLT" if mode.endswith("tlt") else "IEF"
        bond = index_data.load(MARKET, bg.LONG_BOND if sym == "TLT" else IEF)
        sp = sp_total_return()
        used = max(pd.Timestamp(start), bond.index[0])
        parts = {"SPY": (sp, closes(SP_TR)), sym: (bond, closes(sym))}
        wts = {k: (SIXTY_FORTY_STOCKS_PCT if k == "SPY" else 100 - SIXTY_FORTY_STOCKS_PCT) for k in parts}
        timed = {k: (p, q, pd.Series(1, index=p.index)) for k, (p, q) in parts.items()}
    else:
        inp = sleeve_inputs()
        used = max([pd.Timestamp(start)] + [v[3] for v in inp.values()])
        timed = {k: (p, q, (w if mode == "book" else pd.Series(1, index=p.index))) for k, (p, q, w, _f) in inp.items()}
        wts = dict(zip(("stocks", "bonds", "gold"), weights))
    s0 = used.date().isoformat()
    curves, helds, trades, sleeve_costs = {}, {}, [], 0.0
    total_w = sum(wts.values())
    for k, (price, quote, want) in timed.items():
        size = capital * wts[k] / total_w
        tdf, eq, held, _c, costs, _p = simulate(price, want, rate, s0, cost_bps, size, k, quote=quote)
        curves[k], helds[k] = eq / size, held
        sleeve_costs += costs
        if not tdf.empty:
            trades.append(tdf.assign(symbol=f"{k} ({wts[k] / total_w * 100:g}%)"))
    eq, vals, rebal = mix(curves, wts, cost_bps, capital)
    held = pd.concat(helds, axis=1).reindex(eq.index).fillna(0).sum(axis=1).astype(int)
    off = pd.concat(helds, axis=1).reindex(eq.index).fillna(0).eq(0)
    cash = (vals * off[vals.columns]).sum(axis=1)
    tdf = pd.concat(trades, ignore_index=True).sort_values("entry_date") if trades else pd.DataFrame()
    return eq, held, cash, tdf, sleeve_costs + rebal, used, rate


def verdict(book: dict, twin: dict, sf_tlt: dict, sf_ief: dict) -> tuple[bool, list[str]]:
    """The combined book's pass rule for one run (written before any run; the 10bps and neighbour-weight
    legs are this same check on their own runs)."""
    checks = [
        ("Sharpe over T-bills >= untimed + %.2f" % PASS_SHARPE_MARGIN,
         book["sharpe"] >= twin["sharpe"] + PASS_SHARPE_MARGIN, f"{book['sharpe']:.2f} vs {twin['sharpe']:.2f}"),
        ("max DD at least %d%% shallower than untimed" % PASS_DD_SHALLOWER_PCT,
         abs(book["max_dd_pct"]) <= (1 - PASS_DD_SHALLOWER_PCT / 100) * abs(twin["max_dd_pct"]),
         f"{book['max_dd_pct']:.1f}% vs {twin['max_dd_pct']:.1f}%"),
        ("CAGR no more than %.1f points below untimed" % PASS_MAX_CAGR_SHORTFALL,
         book["cagr_pct"] >= twin["cagr_pct"] - PASS_MAX_CAGR_SHORTFALL,
         f"{book['cagr_pct']:.2f}% vs {twin['cagr_pct']:.2f}%"),
        ("Sharpe edge positive in both halves (split %s)" % HALVES_SPLIT,
         book["sharpe_h1"] > twin["sharpe_h1"] and book["sharpe_h2"] > twin["sharpe_h2"],
         f"{book['sharpe_h1'] - twin['sharpe_h1']:+.2f} / {book['sharpe_h2'] - twin['sharpe_h2']:+.2f}"),
        ("Sharpe >= both 60/40 books", book["sharpe"] >= max(sf_tlt["sharpe"], sf_ief["sharpe"]),
         f"{book['sharpe']:.2f} vs SPY/TLT {sf_tlt['sharpe']:.2f}, SPY/IEF {sf_ief['sharpe']:.2f}"),
        ("max DD no deeper than either 60/40", book["max_dd_pct"] >= max(sf_tlt["max_dd_pct"], sf_ief["max_dd_pct"]),
         f"{book['max_dd_pct']:.1f}% vs SPY/TLT {sf_tlt['max_dd_pct']:.1f}%, SPY/IEF {sf_ief['max_dd_pct']:.1f}%"),
    ]
    lines = [f"{'PASS' if ok else 'FAIL'}: {name} ({detail})" for name, ok, detail in checks]
    return all(ok for _n, ok, _d in checks), lines


def compare(start: str, weights, cost_bps: float, capital: float) -> dict:
    """The timed book and its three yardsticks on the same sessions, with the verdict."""
    eq, *_rest, used, rate = build(start, "book", weights, cost_bps, capital)
    out = {"book": eq}
    for m in ("hold_book", "sixty_forty_tlt", "sixty_forty_ief"):
        out[m] = build(used.date().isoformat(), m, weights, cost_bps, capital)[0]
    common = out["book"].index
    for v in out.values():
        common = common.intersection(v.index)
    st = {k: book_stats(v.reindex(common), rate) for k, v in out.items()}
    ok, lines = verdict(st["book"], st["hold_book"], st["sixty_forty_tlt"], st["sixty_forty_ief"])
    return {"stats": st, "pass": ok, "lines": lines, "curves": out}


def parse_weights(text: str | None) -> tuple[float, float, float]:
    if not text:
        return (BOOK_STOCKS_PCT, BOOK_BONDS_PCT, BOOK_GOLD_PCT)
    parts = tuple(float(x) for x in text.split(","))
    if len(parts) != 3 or min(parts) < 0 or sum(parts) <= 0:
        raise SystemExit("--weights takes three non-negative numbers: stocks,bonds,gold")
    return parts


# ------------------------------------------------------------------ docs

BB_DOC = {
    "key": "boucher_book",
    "name": "Boucher combined book",
    "description": "Boucher's stock, bond and gold timing models as three sleeves of one book: "
                   "{BOOK_STOCKS_PCT}% S&P, {BOOK_BONDS_PCT}% long Treasuries, {BOOK_GOLD_PCT}% gold miners, "
                   "each sleeve in T-bills while its own model is out, rebalanced monthly.",
    "status": (
        "1.0 -- PASS CRITERIA FIXED 2026-11-14 BEFORE ANY RUN, optimise stage (2013-2021, in-sample). The book "
        "passes only if ALL hold: against the same {BOOK_STOCKS_PCT}/{BOOK_BONDS_PCT}/{BOOK_GOLD_PCT} weights "
        "held untimed (SPY, TLT, GDX total return, rebalanced monthly), (1) Sharpe over T-bills at least "
        "{PASS_SHARPE_MARGIN} higher; (2) max drawdown at least {PASS_DD_SHALLOWER_PCT}% shallower; (3) CAGR no more than "
        "{PASS_MAX_CAGR_SHORTFALL} points lower; (4) the Sharpe edge positive in both halves (split "
        "{HALVES_SPLIT}); (5) at 10bps a side, (1) still holds against the untimed book at 10bps; (6) with the "
        "weights moved {NEIGHBOUR_STEP_PCT} points one pair at a time (60/20/20, 40/40/20, 50/40/10, 50/20/30), "
        "(1) still holds against the same moved weights untimed; and against the conventional books (7) a "
        "Sharpe at least that of both 60/40 SPY/TLT and 60/40 SPY/IEF, and (8) a max drawdown no deeper than "
        "either. A fail is reported as a fail, and the weights are never tuned. RESULT: not yet run. No "
        "verify run."
    ),
    "thesis": (
        "Boucher's models were built to feed one top-down allocation: hold the asset whose liquidity and "
        "trend are favourable and step to T-bills from the ones that are not. Stocks tend to suffer when "
        "rates rise, long bonds rally when rates fall, and gold shares trend on their own cycle, so the "
        "sleeves are out at different times. Judged one at a time, each model mostly holds less of its "
        "asset; held together, the question is whether the timing builds a better book than simply holding "
        "the same assets."
    ),
    "how_it_works": (
        "Three sleeves at fixed weights, each switching on its own model's weekly signal: {BOOK_STOCKS_PCT}% "
        "in the S&P 500 total return while boucher_stocks' base rule is in (S&P above its 40-week average and "
        "a falling T-bill or long yield, the T-bill silent below its zero-bound floor); {BOOK_BONDS_PCT}% in "
        "long Treasuries while boucher_bonds_gold's Bond-Bill-Utility model is in; {BOOK_GOLD_PCT}% in gold "
        "miners while its Gold-Silver-GMI model is in. A sleeve whose model is out earns the 13-week T-bill "
        "rate.",
        "The rules are the two strategies' own functions, imported: a change to either strategy's rules "
        "changes this book (bump this version by hand; its fingerprint sees only this module's constants).",
        "Each sleeve fills at the close {FILL_DELAY_SESSIONS} session after its signal close, paying "
        "{cost_bps}bps a side on the sleeve. At each month's last session the sleeves are set back to their "
        "weights, paying {cost_bps}bps on the value moved.",
        "Boucher's monthly stock models (liquidity, economic, sentiment) are not used: combining them needs "
        "a vote or a weight of evidence, and with no copy of the book in the repository there is no "
        "documented vote to fix in advance, so the stock sleeve is the base rule alone. AND-stacking them "
        "on the base rule would only cut exposure, by construction.",
        "`--mode hold_book` holds the same weights untimed; `--mode sixty_forty_tlt` and `--mode "
        "sixty_forty_ief` hold 60% SPY and 40% TLT or IEF, all total return and rebalanced monthly. "
        "`--weights S,B,G` moves the weights for the neighbour checks. A book run prints every pass check "
        "against the yardsticks on the same sessions.",
    ),
    "caveats": (
        "**One secular bond bull.** 2013-2021 is mostly falling yields, which flatters any book holding long "
        "Treasuries; that is why the yardsticks hold Treasuries too.",
        "**The gold model failed on its own** (boucher_bonds_gold 1.1 status): it is kept as a sleeve "
        "because the method holds it, not because it showed an edge, and its {BOOK_GOLD_PCT}% is fixed from "
        "the review's test plan, not from its result.",
        "**Weights are not Boucher's.** He gives no fixed split in the material available here; 50/30/20 is "
        "the review's pre-registered choice. The neighbour checks ask whether the verdict depends on it.",
        "**Trade rows are sleeve switches.** Each row is one sleeve's round trip, sized at the sleeve's "
        "starting weight; the book's equity is the monthly-rebalanced mix, so the rows' P&L does not add up "
        "to it. Costs in the report include the rebalancing costs.",
        "**The instruments.** SPY total return (VFINX before 1993), TLT total return (a synthetic long "
        "Treasury before 2002-07-30), GDX total return; the gold model has every input from late 2007, so a "
        "run cannot start before then. IEF starts 2002-07.",
    ),
    "entry_rules": (
        "Each sleeve buys its asset at the close {FILL_DELAY_SESSIONS} session after a week-end close at "
        "which its model turns in, less {cost_bps}bps, with the money that sleeve holds.",
        "At each month's last close every sleeve is set back to its weight ({BOOK_STOCKS_PCT}/"
        "{BOOK_BONDS_PCT}/{BOOK_GOLD_PCT}), less {cost_bps}bps on the value moved.",
    ),
    "exit_rules": (
        "A sleeve sells its asset in full at the close {FILL_DELAY_SESSIONS} session after a week-end close "
        "at which its model turns out, less {cost_bps}bps, and holds T-bills until the model turns in.",
        "No stop and no target. A holding at the end of a run is valued at the final close (OPEN).",
    ),
    "commands": {
        "The book (optimise)": "python -m jobs enqueue backtest --market us --strategies boucher_book --stage optimise",
        "Compare: same weights untimed": "python -m jobs enqueue backtest --market us --strategies boucher_book --stage optimise --bt='--mode hold_book'",
        "Compare: 60/40 SPY/TLT": "python -m jobs enqueue backtest --market us --strategies boucher_book --stage optimise --bt='--mode sixty_forty_tlt'",
        "Compare: 60/40 SPY/IEF": "python -m jobs enqueue backtest --market us --strategies boucher_book --stage optimise --bt='--mode sixty_forty_ief'",
        "Pass check: doubled costs": "python -m jobs enqueue backtest --market us --strategies boucher_book --stage optimise --bt='--cost-bps 10'",
        "Pass check: moved weights (e.g. 60/20/20)": "python -m jobs enqueue backtest --market us --strategies boucher_book --stage optimise --bt='--weights 60,20,20'",
    },
}


class BoucherBookStrategy(PortfolioStrategy):
    """Boucher's stock (base rule), bond (Bond-Bill-Utility) and gold (Gold-Silver-GMI) timing as sleeves."""

    key = BB_DOC["key"]
    doc = BB_DOC
    family = "boucher_book"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-14",
         "First version, from the 2026-11-14 reviews of boucher_stocks and boucher_bonds_gold (tracker #75, "
         "#76): the method as Boucher would hold it. Sleeves at weights FIXED BEFORE ANY RUN: 50% S&P total "
         "return on boucher_stocks 1.1's base rule (with the 0.50% T-bill floor), 30% TLT total return on "
         "Bond-Bill-Utility, 20% GDX total return on Gold-Silver-GMI; each in T-bills while its model is out; "
         "5bps a side on switches and on monthly rebalancing. No vote of his monthly stock models (no copy of "
         "the book to fix one from) and no AND-stacking. Pass criteria written into the status before the "
         "run: against the same weights untimed, Sharpe over T-bills +0.10, drawdown 25% shallower, CAGR "
         "within 2 points, both halves, at 10bps, at weights moved 10 points; Sharpe and drawdown no worse "
         "than 60/40 SPY/TLT and SPY/IEF."),
    )
    name = BB_DOC["name"]
    description = BB_DOC["description"]
    status = BB_DOC["status"]
    thesis = BB_DOC["thesis"]
    how_it_works = tuple(BB_DOC["how_it_works"])
    caveats = tuple(BB_DOC["caveats"])
    entry_rules = tuple(BB_DOC["entry_rules"])
    exit_rules = tuple(BB_DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "time_series"
    style = "trend"
    horizon = "positional"
    runner = "boucher_book"

    mode = "book"
    cost_bps = 5.0

    param_docs = (
        ("Mode", "mode", "book: the timed sleeves. hold_book: the same weights untimed. sixty_forty_tlt / sixty_forty_ief: 60/40 SPY with TLT or IEF."),
        ("Stocks weight", "BOOK_STOCKS_PCT", "% of the book in the stock-timing sleeve (S&P total return or T-bills)."),
        ("Bonds weight", "BOOK_BONDS_PCT", "% in the Bond-Bill-Utility sleeve (TLT total return or T-bills)."),
        ("Gold weight", "BOOK_GOLD_PCT", "% in the Gold-Silver-GMI sleeve (GDX total return or T-bills)."),
        ("60/40 stocks", "SIXTY_FORTY_STOCKS_PCT", "% SPY in the conventional comparison books; the rest TLT or IEF."),
        ("Sharpe margin", "PASS_SHARPE_MARGIN", "Sharpe over T-bills the book must add over the same weights untimed."),
        ("Drawdown cut", "PASS_DD_SHALLOWER_PCT", "% by which the book's max drawdown must be shallower than the untimed book's."),
        ("CAGR shortfall", "PASS_MAX_CAGR_SHORTFALL", "Points of CAGR the book may give up against the untimed book."),
        ("Neighbour step", "NEIGHBOUR_STEP_PCT", "Points the weights are moved, one pair at a time, for the robustness check."),
        ("Cost per side", "cost_bps", "Basis points per side, on sleeve switches and on rebalancing."),
    )


# ------------------------------------------------------------------ runner

def main(argv: list[str] | None = None) -> dict | None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Boucher combined book")
    ap.add_argument("--strategy", default=BoucherBookStrategy.key)
    ap.add_argument("--market", default=MARKET, choices=[MARKET])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", default=None, help="an earlier end than the stage's, for a context run")
    ap.add_argument("--mode", default=BoucherBookStrategy.mode, choices=list(MODES))
    ap.add_argument("--weights", default=None, help="stocks,bonds,gold in % (default the fixed 50,30,20)")
    ap.add_argument("--cost-bps", type=float, default=BoucherBookStrategy.cost_bps)
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    from ..config import MARKETS
    capital = float(MARKETS[MARKET].account_size)
    w = parse_weights(a.weights)
    wtxt = "/".join(f"{x:g}" for x in w)
    with context_boundary(a.end):
        eq, held, cash, tdf, costs, used, rate = build(a.start, a.mode, w, a.cost_bps, capital)
        twin = build(used.date().isoformat(), "hold_book", w, a.cost_bps, capital)[0]
        bench = twin * (capital / twin.iloc[0])
        bench_name = f"The same weights ({wtxt} SPY/TLT/GDX total return) held untimed, rebalanced monthly"
        what = {"book": f"Timed book: stocks/bonds/gold sleeves at {wtxt}%, each in T-bills while its model is out.",
                "hold_book": f"Comparison: SPY/TLT/GDX at {wtxt}% held untimed.",
                "sixty_forty_tlt": f"Comparison: {SIXTY_FORTY_STOCKS_PCT}/{100 - SIXTY_FORTY_STOCKS_PCT} SPY/TLT.",
                "sixty_forty_ief": f"Comparison: {SIXTY_FORTY_STOCKS_PCT}/{100 - SIXTY_FORTY_STOCKS_PCT} SPY/IEF."}[a.mode]
        what += " Rebalanced at each month's last session."
        st = book_stats(eq, rate)
        what += (f" Sharpe over T-bills {st['sharpe']:.2f} (halves {st['sharpe_h1']:.2f} / {st['sharpe_h2']:.2f}),"
                 f" CAGR {st['cagr_pct']:.2f}%, max DD {st['max_dd_pct']:.1f}%.")
        result = None
        if a.mode == "book":
            result = compare(used.date().isoformat(), w, a.cost_bps, capital)
            what += " PASS CHECKS: " + "; ".join(result["lines"]) + "."
            print("\n".join(result["lines"]))
        note = ("" if used <= pd.Timestamp(a.start) else
                f"Start moved from {a.start} to {used.date()}: the first session every sleeve has its inputs.")
        tag = a.mode + ("" if a.weights is None else "_w" + "-".join(f"{x:g}" for x in w))
        out = finish(a, argv, BoucherBookStrategy, tdf, eq, held, cash, costs, bench, bench_name, what, tag,
                     f"Boucher combined book ({tag}), {a.start} onward", "boucher_book", start_note=note)
        out["stats"] = st
        if result:
            out["pass"] = result["pass"]
            out["checks"] = result["lines"]
            out["yardsticks"] = result["stats"]
        return out


if __name__ == "__main__":
    main()
