"""The live screen decides as the backtest does: minervini, as of in-sample dates.

The daily screen (screening/pipeline.py) and the backtest (backtest.collect_signals) are two drivers of one
strategy. The 2026-11-14 review found them disagreeing on 5 of 64 names: a market-cap floor only the live run
applied (India), a higher live price floor, and a base count read on a truncated history. This replays the live
run's own decision path -- `pipeline.live_candidates` and `pipeline.live_decision`, the functions the run calls --
as of past dates D, on what the offline run would have read (the stored bars since D minus the run's window, cut
at D by `asof.boundary`, the market-wide RS rank of D), and compares it with:

  * the backtest's scan of the same bar (`collect_signals` on the full stored history cut at D, then
    `filter_min_rs`, as `--spec` runs it): the same names accepted, with the same setup, entry and stop;
  * the backtest's stored signal rows for that bar (`backtest_signals`, under any spec id sharing the current
    signal id; read only): the same gates passed and setups found.

The live price floor reads the price the stock traded at on D (its stored close times the splits after D,
`spec.split_factor_after`), which is what the run read that day. The market filter and the results blackout are
compared elsewhere (the review's §3.6); both drivers call the same `spec.market_ok`, and the live screen reads
the earnings calendar, which is not stored as of a past date. Reads the database; writes nothing. Minutes:

    PYTHONPATH=. .venv/bin/python -m tests.test_live_parity
"""

import sys

import pandas as pd

from swing_screener.backtesting import backtest as bt
from swing_screener.backtesting import spec as spec_mod
from swing_screener.config import MARKETS
from swing_screener.core import context as ctx_mod, indicators as ind
from swing_screener.marketdata import asof, cache, corporate_actions, db
from swing_screener.screening import pipeline
from swing_screener.strategies import get_strategy, minervini_spec as ms
from swing_screener.strategies.variants import market_rules

ACCEPT = ("TRADE - HIGH CONFIDENCE", "TRADE ON TRIGGER")
LIVE_DAYS = int(pipeline.LOOKBACK_DAYS * 1.6) + 30      # what cache.get_many_bars reads offline
# In-sample dates of the review's check, each with the names its mismatches were found on: DELTACORP (India,
# under Rs 5,000 crore and Rs 100), HCA / STX / LBTYK (US, late bases the live window counted as early), DXCM and
# INN (US, between $10 and $15).
DATES = {
    "india": [("2013-12-04", ["DELTACORP.NS"]), ("2015-01-12", [])],
    "us": [("2014-12-31", ["HCA", "STX", "LBTYK"]), ("2013-01-17", ["DXCM"]), ("2015-03-13", ["INN"])],
}
FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _stored(market: str, strategy, day: pd.Timestamp) -> dict:
    """{symbol: (hard_gates_passed, has_setup, setups)} of the stored scan rows on `day` that passed the gates,
    under any spec id with the current signal id."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT spec_id FROM backtest_signal_specs WHERE market=%s AND strategy=%s AND signal_id=%s",
                    (market, strategy.key, strategy.signal_id()))
        specs = [r[0] for r in cur.fetchall()] + [strategy.spec_id()]
        cur.execute("SELECT DISTINCT ON (symbol) symbol, hard_gates_passed, has_setup, setups FROM backtest_signals "
                    "WHERE market=%s AND strategy=%s AND date=%s AND spec_id = ANY(%s) AND hard_gates_passed "
                    "ORDER BY symbol", (market, strategy.key, day.date(), specs))
        return {s: (bool(g), bool(h), {k for k, v in (st or {}).items() if v}) for s, g, h, st in cur.fetchall()}


def one(market: str, day: str, named: list[str]) -> None:
    D = pd.Timestamp(day)
    strategy, cfg = get_strategy("minervini"), MARKETS[market]
    print(f"{market} {day}")
    stored = _stored(market, strategy, D)
    syms = sorted(set(stored) | set(named))
    check(f"stored scan rows exist for the date ({len(stored)} past the gates)", bool(stored))
    with asof.boundary(D), cache.offline():
        window = cache.load_many_cached(market, syms, since=D - pd.Timedelta(days=LIVE_DAYS))
        window = {s: df for s, df in window.items() if len(df) and df.index[-1] == D}
        enriched = {s: ind.enrich_daily(df, corporate_actions.credits_for(market, s, df)) for s, df in window.items()}
        # the pre-filter's price floor on the price traded that day: prices x the splits after D, volume / them
        k = spec_mod.split_factor_after(market, pd.DatetimeIndex([D]), list(enriched))
        as_traded = {}
        for s, e in enriched.items():
            f = float(k.loc[D, s]) if s in k.columns else 1.0
            px = [c for c in e.columns if c in ("open", "high", "low", "close") or c.startswith(("sma", "ema", "high_", "low_"))]
            as_traded[s] = e.assign(**{c: e[c] * f for c in px}, volume=e["volume"] / f,
                                    **({"vol_sma50": e["vol_sma50"] / f} if "vol_sma50" in e else {}))
        bars = dict(window)
        live_syms, why = pipeline.live_candidates(strategy, cfg, market, as_traded, bars)
        ranks, ranked = spec_mod.rs_rank_asof(market, D, strategy.rs_young_min_bars())
        risk_off = strategy.market_risk_off(market, False)
        live = {}
        for s in live_syms:
            d = pipeline.live_decision(strategy, cfg, s, bars[s], None, ranks, ranked, risk_off, False,
                                       credits=corporate_actions.credits_for(market, s, bars[s]))
            if d["decision"] is not None and d["decision"].label_before in ACCEPT:
                live[s] = (d["plan"].setup, round(d["plan"].entry, 6), round(d["plan"].stop, 6))
        full = cache.load_many_cached(market, syms)
        sigs, fresh = [], {}
        for s, df in full.items():
            if not len(df) or df.index[-1] != D:
                continue
            # the scan needs two sessions in its window (collect_signals), so it starts one session before D
            got = bt.collect_signals(s, df, cfg, df.index[-2], strategy, market_key="", use_signal_cache=False,
                                     accept_labels=ACCEPT)
            sigs += [g for g in got if g.date == D]
            ctx = ctx_mod.build_context(s, df, None, as_of=D)
            if ctx is not None:
                r = strategy.evaluate(ctx)
                fresh[s] = (bool(r.hard_gates_passed), bool(r.has_setup), {c for c, v in r.setups.items() if v})
        kept, _ = spec_mod.filter_min_rs(sigs, market, int(ms.RS_MIN_RANK), strategy.rs_young_min_bars())
        backtest = {g.symbol: (g.setup, round(g.entry, 6), round(g.stop, 6)) for g in kept}
    only_live, only_bt = sorted(set(live) - set(backtest)), sorted(set(backtest) - set(live))
    check(f"the same names accepted ({len(backtest)} by the backtest)", not only_live and not only_bt,
          f"live only {only_live}, backtest only {only_bt} (live pre-filter: "
          f"{ {s: why.get(s) for s in only_bt if s in why} })")
    diff = {s: (live[s], backtest[s]) for s in set(live) & set(backtest) if live[s] != backtest[s]}
    check("the same setup, entry and stop on every name both accept", not diff, str(diff))
    bad = {s: (stored[s], fresh.get(s)) for s in stored if s in fresh and stored[s][:2] != fresh[s][:2]}
    check("the stored scan rows agree with the scan's code on gates and setups", not bad, str(list(bad.items())[:3]))


def main() -> int:
    for market, dates in DATES.items():
        with market_rules("minervini", market):
            for day, named in dates:
                one(market, day, named)
    print(f"\n{'FAILED: ' + '; '.join(FAILS) if FAILS else 'the live screen decides as the backtest does'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
