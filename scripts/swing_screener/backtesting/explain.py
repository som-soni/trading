"""Replay one symbol through a strategy's history: what fired, what traded, why.

`screening.inspect` answers "what does this strategy think of this stock
TODAY". This answers the question you actually have after a bad backtest:
*over the whole window, where did this symbol fall out?* It joins three
things that were previously only inspectable separately —

  - the cached per-date gate/setup vector (`backtest_signals`)
  - the trades a run actually took (`trades.csv`)
  - the price history, to say what the stock did meanwhile

— and prints the funnel: bars evaluated, bars passing every gate, bars with a
setup, signals, trades, exits. When a strategy produces nine trades in sixteen
years, the funnel says whether that is the gates, the setup definition, the
entry trigger or the portfolio refusing to fund it, and those have completely
different fixes.

    python3 -m swing_screener.backtesting.explain --market us --symbol NVDA \\
        --strategy minervini
    python3 -m swing_screener.backtesting.explain --market india --symbol ICICIBANK.NS \\
        --strategy minervini --run 2013-01-01_ma-sma50-noTarget

Reads the signal cache, so it only reports bars a backtest has already
scanned; run the backtest first.
"""

import argparse
import json
import logging
from collections import Counter

import pandas as pd

from ..config import MARKETS
from ..marketdata import cache, db
from ..paths import REPORTS_DIR
from ..strategies import get_strategy, list_strategies

logger = logging.getLogger("explain")


def _jload(v):
    if v is None:
        return {}
    return v if isinstance(v, dict) else json.loads(v)


def load_signal_history(market: str, strategy: str, symbol: str) -> pd.DataFrame:
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT date, hard_gates_passed, first_failed_gate, hard_gates, "
            "has_setup, setups, watch_flags FROM backtest_signals "
            "WHERE market=%s AND strategy=%s AND symbol=%s ORDER BY date",
            (market, strategy, symbol),
        )
        rows = cur.fetchall()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([
        {"date": pd.Timestamp(r[0]), "gates_passed": r[1], "first_failed_gate": r[2],
         "hard_gates": _jload(r[3]), "has_setup": r[4], "setups": _jload(r[5]),
         "watch_flags": _jload(r[6])}
        for r in rows
    ])


def find_trades(market: str, strategy: str, symbol: str, run: str | None = None) -> pd.DataFrame:
    """Every trade this symbol produced, across runs unless one is named."""
    base = REPORTS_DIR / market / strategy
    if not base.exists():
        return pd.DataFrame()
    frames = []
    for path in sorted(base.glob("**/trades.csv")):
        rel = str(path.parent.relative_to(base))
        if run and rel != run:
            continue
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if "symbol" not in df:
            continue
        mine = df[df["symbol"] == symbol]
        if not mine.empty:
            frames.append(mine.assign(run=rel))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _extras_on(market: str, strategy: str, symbol: str, date) -> dict:
    """The strategy's own stashed values for one bar (pivot, tight low, ...)."""
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT extras, setups FROM backtest_signals WHERE market=%s AND "
            "strategy=%s AND symbol=%s AND date=%s",
            (market, strategy, symbol, pd.Timestamp(date).date()),
        )
        row = cur.fetchone()
    return {"extras": _jload(row[0]), "setups": _jload(row[1])} if row else {}


# EX-05 and EX-06 are QUEUED: the rule fires on one session's close and the
# position is sold at the NEXT session's open. Explaining them from the exit
# bar reads the wrong day's numbers -- on TCS 2010-04-26 that showed volume at
# 0.67x average and concluded the run "did not require volume confirmation",
# when the rule had in fact fired the session before on 1.14x. Anything in here
# is explained from the bar that triggered it.
_QUEUED_EXITS = {"TREND_EXIT", "CLIMAX"}


def _why_exit(reason: str, bar, policy_ma: str, pivot, entry: float,
              initial_stop: float, stop_on_exit) -> list[str]:
    """Restate the rule that fired, with the numbers from that bar.

    The exit ladder is checked in a fixed order each session, so naming the
    rule is only half an explanation -- the useful half is the comparison it
    made. "TREND_EXIT" means nothing; "close 108.54 below SMA50 109.12 on
    volume 1.4x its average" is the thing you can argue with.
    """
    c = float(bar.get("close", float("nan")))
    lo = float(bar.get("low", float("nan")))
    ma = float(bar.get(policy_ma, float("nan")))
    vol = float(bar.get("volume", float("nan")))
    v50 = float(bar.get("vol_sma50", float("nan")))
    out = []
    if reason in ("STOP", "BREAKEVEN_STOP"):
        where = "the initial stop" if reason == "STOP" else "a stop raised to breakeven"
        out.append(f"EX-01 {where}: the bar's low {lo:,.2f} touched {stop_on_exit:,.2f}")
        if reason == "BREAKEVEN_STOP":
            out.append(f"      (initial stop was {initial_stop:,.2f}; it had been raised "
                       f"after the trade reached its breakeven trigger)")
    elif reason == "FAILED_BREAKOUT":
        pv = f"{pivot:,.2f}" if pivot else "the pivot"
        out.append(f"EX-02 failed breakout: closed {c:,.2f}, back below the pivot {pv}, "
                   f"within the spec's grace window of the entry")
        out.append("      The breakout did not hold. This is the rule doing its job, not a loss "
                   "to tune away.")
    elif reason == "CLIMAX":
        out.append(f"EX-05 climax: closed {c:,.2f}, {(c / entry - 1) * 100:+.1f}% from entry, "
                   f"on an exhaustion signature (biggest daily gain on biggest volume, a run "
                   f"of up days, extension above the 200-day, or a gap)")
        out.append("      Selling into strength, by design.")
    elif reason == "TREND_EXIT":
        out.append(f"EX-06 trend break: closed {c:,.2f} below {policy_ma.upper()} {ma:,.2f}")
        if v50 == v50 and vol == vol and v50 > 0:
            # The run's `trend_volume` setting is not recorded in trades.csv, so
            # report the ratio and say what it implies rather than asserting a
            # requirement that may not have applied.
            out.append(f"      volume {vol:,.0f} vs 50-day average {v50:,.0f} "
                       f"({vol / v50:.2f}x)"
                       + ("" if vol >= v50 else
                          " — below average, so volume confirmation was off for this run"))
    elif reason == "TIME_STOP":
        out.append(f"EX-07 time stop: still below entry+1R after the allowed holding period")
    elif reason == "OPEN":
        out.append("still open at the end of the window; marked at the final close")
    else:
        out.append(f"{reason}")
    return out


def explain_trades(market: str, strategy: str, symbol: str, tr, px, cfg,
                   policy_ma: str = "sma50") -> None:
    """Entry and exit of each trade, restated as the rules that produced them."""
    from ..core import indicators as ind

    enriched = ind.enrich_daily(px)
    seen = set()
    for _, t in tr.iterrows():
        ed = pd.Timestamp(t["entry_date"])
        xd = pd.Timestamp(t["exit_date"]) if pd.notna(t.get("exit_date")) else None
        key = (ed, xd, t.get("exit_reason"))
        if key in seen:       # the same trade reproduced across run variants
            continue
        seen.add(key)

        entry, istop = float(t["entry_price"]), float(t["initial_stop"])
        ctx = _extras_on(market, strategy, symbol, ed - pd.Timedelta(days=1)) or \
              _extras_on(market, strategy, symbol, ed)
        ex = ctx.get("extras") or {}
        pivot = ex.get("pivot") or ex.get("base_high") or ex.get("channel_high")
        setups = [k for k, v in (ctx.get("setups") or {}).items() if v]

        print(f"\n  {'=' * 72}")
        print(f"  {ed.date()} -> {xd.date() if xd is not None else '(open)'}   "
              f"{t.get('exit_reason')}   {t.get('r_multiple'):+.3f}R   "
              f"{int(t.get('holding_days', 0))} days")
        print(f"  {'-' * 72}")
        print("  ENTRY")
        if setups:
            print(f"    setup {', '.join(setups)}")
        if pivot:
            print(f"    pivot (the level the breakout had to clear): {float(pivot):,.2f}")
        print(f"    filled at {entry:,.2f}", end="")
        if pivot and entry > float(pivot) * 1.002:
            print(f"  — {(entry / float(pivot) - 1) * 100:+.1f}% above the pivot, so the "
                  f"buy-stop filled at the open rather than at the level")
        else:
            print()
        print(f"    stop {istop:,.2f}, i.e. {(1 - istop / entry) * 100:.1f}% of entry at risk")

        print("  EXIT")
        reason = str(t.get("exit_reason"))
        bar = enriched.loc[xd] if (xd is not None and xd in enriched.index) else None
        if bar is not None and reason in _QUEUED_EXITS:
            # step back to the session whose close actually fired the rule
            pos = enriched.index.get_loc(xd)
            if pos > 0:
                xd, bar = enriched.index[pos - 1], enriched.iloc[pos - 1]
                print(f"    (fired on {xd.date()}'s close; sold at the next open)")
        if bar is None:
            print(f"    no bar for {xd}")
        else:
            for line in _why_exit(reason, bar, policy_ma, pivot,
                                  entry, istop, float(t.get("stop", istop))):
                print(f"    {line}")

        # what the trade gave up, which is the question a losing run really asks
        if xd is not None:
            held = px.loc[ed:xd]
            if not held.empty:
                mfe = (float(held["high"].max()) / entry - 1) * 100
                print(f"  WHILE HELD: best close-to-high {mfe:+.1f}% from entry")
            after = px.loc[xd:]
            if len(after) > 1:
                peak = float(after["high"].max())
                nxt = float(px["close"].iloc[-1])
                print(f"  AFTER THE EXIT: peaked at {peak:,.2f} "
                      f"({(peak / entry - 1) * 100:+.0f}% vs entry), "
                      f"latest close {nxt:,.2f} ({(nxt / entry - 1) * 100:+.0f}%)")


def explain(market: str, symbol: str, strategy_key: str, run: str | None = None,
            show: int = 15, detail: bool = True, policy_ma: str = "sma50") -> None:
    cfg = MARKETS[market]
    strat = get_strategy(strategy_key)
    sig = load_signal_history(market, strategy_key, symbol)
    px = cache.load_cached(market, symbol)

    print(f"\n=== {symbol} ({cfg.name}) vs {strategy_key} {strat.spec_id()} ===")
    if px is None or px.empty:
        print("  no price history cached")
        return
    print(f"  price history: {len(px):,} bars, {px.index[0].date()} -> {px.index[-1].date()}")
    first, last = float(px["close"].iloc[0]), float(px["close"].iloc[-1])
    print(f"  buy & hold over that window: {(last / first - 1) * 100:+,.0f}%")

    if sig.empty:
        print("\n  NOTHING IN THE SIGNAL CACHE for this symbol+strategy.")
        print("  Either no backtest has scanned it, or it never passed the")
        print("  pre-filter on any bar (the pre-filter runs before caching).")
        print(f"  Run: python3 -m swing_screener.backtesting.backtest --market {market} "
              f"--strategy {strategy_key} --start <date>")
        return

    n = len(sig)
    passed = int(sig["gates_passed"].sum())
    setups = int(sig["has_setup"].sum())
    both = int((sig["gates_passed"] & sig["has_setup"]).sum())
    # Bars only reach the cache after passing the pre-filter, so a 100% gate
    # pass rate here does NOT mean the gates are inert -- it means the
    # pre-filter already applied them. Show the pre-filter's own rejection
    # first, or the funnel reads as though nothing was filtered.
    window = px[(px.index >= sig["date"].min()) & (px.index <= sig["date"].max())]
    in_window = len(window)
    print(f"\n  --- funnel over {sig['date'].min().date()} -> {sig['date'].max().date()} ---")
    print(f"  bars in the window                       : {in_window:,}")
    print(f"  passed the pre-filter (reached the cache): {n:,} "
          f"({n / max(in_window, 1) * 100:.1f}%)")
    note = "  <- the pre-filter already applies these" if passed == n else ""
    print(f"  passed every hard gate                   : {passed:,} "
          f"({passed / n * 100:.1f}%){note}")
    print(f"  had a setup                              : {setups:,} ({setups / n * 100:.1f}%)")
    print(f"  BOTH (a tradeable signal)                : {both:,} ({both / n * 100:.1f}%)")

    fails = Counter(sig.loc[~sig["gates_passed"], "first_failed_gate"].dropna())
    if fails:
        print(f"\n  --- which gate blocked it first ({sum(fails.values()):,} blocked bars) ---")
        for code, c in fails.most_common():
            doc = strat.gate_docs.get(code, "")
            text = strat.render_doc(doc)[:76] if doc else ""
            print(f"    {code:6} {c:6,} ({c / sum(fails.values()) * 100:5.1f}%)  {text}")

    # a gate that NEVER passes is a different problem from one that rarely does
    if passed:
        never = [c for c in strat.gate_codes
                 if not any(g.get(c) for g in sig["hard_gates"] if g)]
        if never:
            print(f"\n  gates that NEVER passed on any bar: {', '.join(never)}")

    if setups:
        kinds = Counter()
        for d in sig.loc[sig["has_setup"], "setups"]:
            for k, on in (d or {}).items():
                if on:
                    kinds[k] += 1
        print(f"\n  --- setups seen ---")
        for k, c in kinds.most_common():
            print(f"    {k:8} {c:5,} bars")

    sigdates = sig.loc[sig["gates_passed"] & sig["has_setup"], "date"]
    if len(sigdates):
        print(f"\n  --- tradeable-signal dates (first {show}) ---")
        for d in list(sigdates)[:show]:
            row = px.loc[:d]
            close = float(row["close"].iloc[-1]) if len(row) else float("nan")
            print(f"    {d.date()}  close {close:,.2f}")
        if len(sigdates) > show:
            print(f"    ... and {len(sigdates) - show:,} more")

    tr = find_trades(market, strategy_key, symbol, run)
    print(f"\n  --- trades actually taken ---")
    if tr.empty:
        print("    NONE.")
        if len(sigdates):
            print(f"    {len(sigdates):,} signals fired but none became a trade. That is the")
            print("    portfolio refusing them, not the strategy failing to see them:")
            print("    check the run report's line on signals passed up for a full book")
            print("    or insufficient cash.")
    else:
        cols = [c for c in ("run", "entry_date", "entry_price", "initial_stop", "exit_date",
                            "exit_reason", "exit_price", "r_multiple", "holding_days", "pnl")
                if c in tr.columns]
        print(tr[cols].to_string(index=False))
        if "r_multiple" in tr:
            print(f"\n    {len(tr)} trades, avg {tr['r_multiple'].mean():+.3f}R, "
                  f"total P&L {cfg.currency_symbol}{tr['pnl'].sum():,.0f}")
        if "exit_reason" in tr:
            print("    exits: " + ", ".join(f"{k} x{v}" for k, v in
                                            Counter(tr["exit_reason"]).most_common()))
        if detail:
            print(f"\n  --- why each entry and exit sat where it did ---")
            explain_trades(market, strategy_key, symbol, tr, px, cfg, policy_ma)


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--strategy", required=True, choices=list_strategies())
    ap.add_argument("--run", default=None,
                    help="limit trades to one run directory (default: every run)")
    ap.add_argument("--show", type=int, default=15, help="signal dates to list")
    ap.add_argument("--no-detail", action="store_true",
                    help="skip the per-trade entry/exit explanation")
    ap.add_argument("--ma-col", default="sma50",
                    help="the moving average the run's exit policy used")
    args = ap.parse_args()
    explain(args.market, args.symbol, args.strategy, args.run, args.show,
            detail=not args.no_detail, policy_ma=args.ma_col)


if __name__ == "__main__":
    main()
