"""Scan the cached universe for ONE chart pattern and list every match.

Matches are graded against the textbook description, not just detected:
`textbook`, `moderate` and `low` say how far a structure sits from the
pattern whose reputation is being borrowed, and `flaws` says exactly why.
Nothing is dropped for being imperfect — a 49%-deep cup whose right side has
not reached its own rim is a real structure worth watching, it is simply not
the thing the statistics are about.

The daily pipeline answers "what should I trade today", so it reports only
what cleared the screen and the gates. This answers a different question —
"show me every cup-and-handle on the board so I can look at the charts
myself" — and so it deliberately reports matches the strategy would reject,
with the reason attached.

    PYTHONPATH=. python3 -m swing_screener.screening.find_pattern --pattern CUP
    PYTHONPATH=. python3 -m swing_screener.screening.find_pattern \
        --pattern VCP --market india --min-quality 0.5

Detection is as-of the last cached bar. Nothing here is a recommendation:
see `ChartPatternStrategy.caveats` for what happened when the strategy built
on these patterns was backtested (it lost money).
"""

import argparse
import logging

import pandas as pd

from ..config import MARKETS
from ..core import chart_patterns as cp
from ..core import context as ctx_mod
from ..core import indicators as ind
from ..core import sizing
from ..marketdata import cache, earnings
from ..marketdata.universe import load_sector_cache
from ..paths import REPORTS_DIR
from . import links
from ..strategies import get_strategy

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("find_pattern")

# Enough bars for every indicator the gates read (SMA200, 52-week high) plus
# the longest base the detector looks back over. Scanning on a tail rather
# than full history is ~4x faster per symbol and cannot change a match:
# every detector is lookback-capped at 250 bars.
SCAN_TAIL = 460


def scan_market(
    market: str, code: str, min_quality: float, require_liquidity: bool = True
) -> list[dict]:
    cfg = MARKETS[market]
    strategy = get_strategy("chart_pattern")
    topping = code in cp.TOPPING_CODES
    symbols = sorted(cache.cached_symbols(market))
    logger.info("%s: scanning %d cached symbols for %s", market, len(symbols), code)

    hits: list[tuple[str, cp.PatternMatch]] = []
    for i, sym in enumerate(symbols, 1):
        if i % 1000 == 0:
            logger.info("  %d/%d scanned, %d matches so far", i, len(symbols), len(hits))
        raw = cache.load_cached(market, sym)
        if raw is None or len(raw) < strategy.min_bars:
            continue
        tail = raw.tail(SCAN_TAIL)
        enriched = ind.enrich_daily(tail)
        last = enriched.iloc[-1]
        # price/liquidity only — the trend and 52-week-high conditions are
        # GATES, and this report is meant to show what they reject too
        if require_liquidity:
            if cfg.screener.min_price and last["close"] < cfg.screener.min_price:
                continue
            dv = last.get("dollar_vol_sma20")
            if pd.isna(dv) or dv < cfg.screener.min_dollar_volume:
                continue
        match = next(
            (m for m in cp.detect_patterns(enriched, include_topping=topping)
             if m.code == code), None
        )
        if match is not None and match.quality >= min_quality:
            hits.append((sym, match))

    logger.info("%s: %d %s matches; re-evaluating on full history", market, len(hits), code)
    if not hits:
        return []

    # Earnings is one network request per ticker, so it runs only for the
    # handful that matched — same rule as the pipeline.
    try:
        days_away = earnings.load_earnings_days_away(market, [s for s, _ in hits])
    except Exception as exc:  # network/provider failure must not lose the scan
        logger.warning("earnings lookup failed (%s); gate P5 not evaluated", exc)
        days_away = {}
    sectors = load_sector_cache(market)

    rows: list[dict] = []
    for sym, scan_match in hits:
        raw = cache.load_cached(market, sym)
        ctx = ctx_mod.build_context(sym, raw, earnings_days_away=days_away.get(sym))
        if ctx is None:
            continue
        result = strategy.evaluate(ctx)
        # evaluate() picks the best ACTIONABLE pattern, which may not be the
        # one being searched for; report the searched one's geometry either way
        match = next(
            (m for m in cp.detect_patterns(ctx.daily, include_topping=topping)
             if m.code == code), scan_match
        )
        plan = strategy.build_plans(ctx, result, cfg).chosen
        decision = None
        if plan is not None and plan.is_valid:
            sz = sizing.size_position(cfg, plan.entry, plan.stop, False)
            decision = strategy.classify(
                ctx, result, plan, sz, days_away.get(sym), False
            )
        traded = ctx.extras.get("pattern")
        rows.append({
            "market": market,
            "symbol": sym,
            "chart": links.chart_url(sym),
            "sector": sectors.get(sym, ""),
            "price": round(ctx.close, 2),
            "confidence": match.confidence,
            "quality": round(match.quality, 2),
            "pivot": round(match.pivot, 2),
            "pct_from_pivot": round((ctx.close / match.pivot - 1) * 100, 1),
            "depth_pct": round(match.depth_pct, 1),
            "length_bars": match.length_bars,
            "stop_ref": round(match.stop_ref, 2),
            "measured_target": round(match.target, 2),
            "decision": decision.label_after if decision else "NO PLAN",
            "first_failed_gate": result.first_hard_fail or "",
            "why": (decision.reason if decision
                    else result.hard_notes.get(result.first_hard_fail or "", "")),
            "entry": round(plan.entry, 2) if plan else None,
            "stop": round(plan.stop, 2) if plan else None,
            "risk_pct": round(plan.risk_per_share / plan.entry * 100, 1) if plan else None,
            "target_r": round(plan.r_multiple, 2) if plan else None,
            "structural_r": ctx.extras.get("structural_r"),
            "traded_pattern": traded if traded != code else "",
            "earnings_in": days_away.get(sym),
            "note": match.note,
            "flaws": match.flaw_text,
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(
        description="List every symbol currently showing one chart pattern.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--pattern", default=cp.CUP, choices=cp.ALL_CODES,
                    help="which pattern to look for (default: CUP). The "
                         f"topping codes {', '.join(cp.TOPPING_CODES)} are "
                         "bearish: in a long-only book they mark a veto or an "
                         "exit, never an entry, so their pivot is the NECKLINE "
                         "and the measured move projects DOWN.")
    ap.add_argument("--market", choices=list(MARKETS.keys()), default=None,
                    help="one market; default scans all of them")
    ap.add_argument("--min-quality", type=float, default=0.0,
                    help="drop matches scoring below this (0-1)")
    ap.add_argument("--no-liquidity-filter", action="store_true",
                    help="include names below the market's price/volume floor")
    args = ap.parse_args()

    markets = [args.market] if args.market else list(MARKETS.keys())
    rows: list[dict] = []
    for market in markets:
        rows += scan_market(
            market, args.pattern, args.min_quality,
            require_liquidity=not args.no_liquidity_filter,
        )

    if not rows:
        print(f"No {args.pattern} matches.")
        return

    df = pd.DataFrame(rows)
    # textbook examples first, then the ones worth watching with their
    # deviations named — nothing is dropped for being imperfect
    order = {"textbook": 0, "moderate": 1, "low": 2, "unassessed": 3}
    df["_rank"] = df["confidence"].map(lambda c: order.get(c, 9))
    df = df.sort_values(["_rank", "quality"], ascending=[True, False]).drop(columns="_rank")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"{args.pattern.lower()}_candidates_{pd.Timestamp.today():%Y-%m-%d}.csv"
    df.to_csv(out, index=False)

    name = cp.PATTERN_NAMES.get(args.pattern, args.pattern)
    counts = df["confidence"].value_counts().to_dict()
    print(f"\n{len(df)} {name} candidate(s): "
          + ", ".join(f"{counts.get(k, 0)} {k}" for k in
                      ("textbook", "moderate", "low") if counts.get(k)))
    cols = ["market", "symbol", "price", "confidence", "quality", "pivot",
            "pct_from_pivot", "depth_pct", "length_bars", "decision",
            "first_failed_gate"]
    pd.set_option("display.width", 220, "display.max_colwidth", 70)
    for grade in ("textbook", "moderate", "low", "unassessed"):
        part = df[df["confidence"] == grade]
        if part.empty:
            continue
        print(f"\n--- {grade.upper()} ({len(part)}) ---")
        print(part[cols].to_string(index=False))
        for _, r in part.iterrows():
            if r["flaws"]:
                print(f"    {r['symbol']}: {r['flaws']}")
            print(f"      {r['chart']}")
    print(f"\nFull detail (entry/stop/R/note/sector): {out}")
    print("\nThese are pattern matches, NOT recommendations — the strategy built "
          "on them lost money in backtest (see ChartPatternStrategy.caveats).")


if __name__ == "__main__":
    main()
