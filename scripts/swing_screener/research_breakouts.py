"""Breakout case studies: scan large-cap US/India stocks for major VCP breakouts, classify
each as successful or failed by what happened afterward, and render research/app-guide-
breakouts*.md pages of ```series chart fences (price, candles, volume, pivot/stop levels)
from the findings.

Reuses the Minervini strategy's own base detector and price-level functions
(core/vcp_spec.detect, minervini_spec.entry_misses / pivot_buy_stop / pivot_stop /
vcp_measured_move) -- one implementation of the VCP rules, never a second copy. The one
thing nothing else in the app computes is added here: whether a breakout held and
followed through, or failed.

"Major" = large-cap by the market's own cap_classes (config/<market>.py) AND a genuine VCP
breakout the strategy's own MV-01 entry tests would have bought (volume, range position,
distance past the pivot) -- not just a big percentage move.

Two phases, since the scan is the expensive part:

    PYTHONPATH=. python3 -m swing_screener.research_breakouts --scan out.json [--market us]
    PYTHONPATH=. python3 -m swing_screener.research_breakouts --render out.json --chunk-size 20
"""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from . import paths
from .config import MARKETS
from .core import indicators as ind
from .core import vcp_spec
from .marketdata import cache, db, names
from .strategies.minervini_spec import (
    BUY_RANGE_PCT, VCP, VOL_MULT, entry_misses, pivot_buy_stop, pivot_stop, vcp_measured_move,
)

# ---- outcome classification (nothing else in the app judges this) -----------------------

HOLD_WINDOW = 10               # sessions: closing back below the pivot within this = failed
FOLLOW_THROUGH_PCT = 15.0      # minimum gain from the pivot to count as a real follow-through
FOLLOW_THROUGH_HORIZON = 60    # sessions (~3 months) to show that follow-through

MAX_PER_COUNTRY = 99


def candidate_universe(market: str) -> list[dict]:
    """Large-cap symbols per the market's own cap_classes -- config, not a hard-coded market name."""
    cfg = MARKETS[market]
    kind, floor_or_rank = cfg.cap_classes[0], cfg.cap_classes[1]
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, market_cap FROM symbol_industry WHERE market=%s AND market_cap IS NOT NULL "
                    "ORDER BY market_cap DESC", (market,))
        rows = cur.fetchall()
    if kind == "rank":
        rows = rows[: int(floor_or_rank)]
    else:  # "cap": a minimum market cap, in the market's own currency
        rows = [r for r in rows if r[1] >= floor_or_rank]
    return [{"symbol": s, "market_cap": float(mc)} for s, mc in rows]


def _classify_outcome(close: np.ndarray, high: np.ndarray, i: int, pivot: float) -> dict | None:
    """Walk forward from breakout bar `i`. Returns {"outcome", "outcome_i", "pct"} or None
    (excluded: not enough forward data yet, or held the level with no real follow-through)."""
    n = len(close)
    hold_end = i + HOLD_WINDOW
    if hold_end >= n:
        return None  # too close to the end of stored history to judge the hold window
    for j in range(i + 1, hold_end + 1):
        if close[j] < pivot:
            return {"outcome": "failed", "outcome_i": j, "pct": (close[j] / pivot - 1) * 100}
    horizon_end = min(i + FOLLOW_THROUGH_HORIZON, n - 1)
    pre_high = high[:i].max() if i > 0 else high[i]
    best_j, best_gain, made_new_high = i, 0.0, False
    for j in range(i, horizon_end + 1):
        gain = (close[j] / pivot - 1) * 100
        if gain > best_gain:
            best_gain, best_j = gain, j
        if high[j] > pre_high:
            made_new_high = True
    confirmed = best_gain >= FOLLOW_THROUGH_PCT or made_new_high
    if not confirmed and horizon_end < i + FOLLOW_THROUGH_HORIZON:
        return None  # not enough data yet to confirm follow-through either way
    if confirmed:
        return {"outcome": "successful", "outcome_i": best_j, "pct": best_gain}
    return None  # excluded: held the level, but never really went anywhere


def scan_symbol(market: str, symbol: str, market_cap: float) -> list[dict]:
    """Every genuine VCP breakout over the symbol's full stored history: the same per-bar
    detection loop `MinerviniSpecStrategy.bases_live` runs (minervini_spec.py:2690-2745), not a
    cheap heuristic -- `vcp_spec.detect` is bounded to its own lookback window (460 bars), so
    this is tractable per symbol even over decades of history."""
    raw = cache.load_cached(market, symbol)
    if raw is None or len(raw) < 300:
        return []
    daily = ind.enrich_daily(raw)
    close, high, low, vol = (daily[k].to_numpy(float) for k in ("close", "high", "low", "volume"))
    v50 = daily["vol_sma50"].to_numpy(float)
    start = 2 * VCP.swing_k + VCP.prior_window
    if len(daily) <= start + 1:
        return []
    dets = [None] * len(daily)
    for i in range(start, len(daily)):
        dets[i] = vcp_spec.detect(daily.iloc[: i + 1], VCP)

    tick = MARKETS[market].tick_size
    out = []
    seen_bh = set()
    for i in range(start + 1, len(daily)):
        p = dets[i - 1]
        if not p or not p["ok"] or not p["pivot"] or p["bh_date"] in seen_bh:
            continue
        if not (close[i - 1] <= p["pivot"] < close[i]):
            continue
        miss, vol_ratio, _ = entry_misses(close[i], high[i], low[i], vol[i], v50[i], p["pivot"])
        if any(miss.values()):
            continue
        seen_bh.add(p["bh_date"])
        outcome = _classify_outcome(close, high, i, p["pivot"])
        if outcome is None:
            continue
        out.append({
            "market": market, "symbol": symbol, "market_cap": market_cap,
            "bh_date": str(p["bh_date"].date()) if hasattr(p["bh_date"], "date") else str(p["bh_date"]),
            "breakout_date": str(daily.index[i].date()), "breakout_i": int(i),
            "pivot": float(p["pivot"]), "tight_low": float(p["tight_low"]) if p["tight_low"] else None,
            "base_high": float(p["bh"]), "base_depth_pct": p["base_depth_pct"],
            "stop": float(pivot_stop(p["tight_low"], tick)) if p["tight_low"] else None,
            "buy_stop": float(pivot_buy_stop(p["pivot"], tick)),
            "measured_move": (float(vcp_measured_move(p["bh"], p["base_depth_pct"]))
                               if p["base_depth_pct"] else None),
            "vol_ratio": float(vol_ratio) if vol_ratio else None,
            "outcome": outcome["outcome"],
            "outcome_date": str(daily.index[outcome["outcome_i"]].date()),
            "pct": float(outcome["pct"]),
        })
    return out


def _scan_one(args: tuple) -> list[dict]:
    market, symbol, market_cap = args
    try:
        return scan_symbol(market, symbol, market_cap)
    except Exception as e:  # noqa: BLE001 -- one bad symbol (odd data) must not kill the whole scan
        print(f"  {market}:{symbol} skipped: {e}")
        return []


def scan_market(market: str, limit_symbols: int | None = None, workers: int = 6) -> list[dict]:
    universe = candidate_universe(market)
    if limit_symbols:
        universe = universe[:limit_symbols]
    jobs = [(market, c["symbol"], c["market_cap"]) for c in universe]
    events = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for n, found in enumerate(pool.map(_scan_one, jobs, chunksize=4), 1):
            if found:
                events.extend(found)
            if n % 100 == 0:
                print(f"  {market}: {n}/{len(universe)} symbols scanned, {len(events)} events so far")
    return events


def select_major(events: list[dict], cap: int = MAX_PER_COUNTRY) -> list[dict]:
    """Rank by how "major" the event is (market cap, breakout-day volume surge, move size),
    scale-free (percentile rank per metric, summed), then take the top `cap`, kept roughly
    balanced between successful and failed."""
    if not events:
        return []
    df = pd.DataFrame(events)
    df["score"] = (df["market_cap"].rank(pct=True) + df["vol_ratio"].fillna(0).rank(pct=True)
                   + df["pct"].abs().rank(pct=True))
    df = df.sort_values("score", ascending=False)
    per_bucket = cap // 2
    picked = []
    for outcome in ("successful", "failed"):
        picked.append(df[df["outcome"] == outcome].head(per_bucket))
    out = pd.concat(picked).sort_values("score", ascending=False)
    return out.to_dict("records")


# ---- rendering ----------------------------------------------------------------------------

def _fence(ev: dict, display_name: str) -> str:
    lead_in, tail = pd.Timedelta(days=35), pd.Timedelta(days=35)
    frm = (pd.Timestamp(ev["bh_date"]) - lead_in).date()
    to = (pd.Timestamp(ev["outcome_date"]) + tail).date()
    ref = f"{ev['market']}:{ev['symbol']}"
    outcome_label = (f"held, +{ev['pct']:.0f}%" if ev["outcome"] == "successful"
                      else f"back below pivot, -{abs(ev['pct']):.0f}%")
    lines = [
        f"title: {display_name} ({ev['symbol']}) — {'successful' if ev['outcome'] == 'successful' else 'failed'} "
        f"breakout, {pd.Timestamp(ev['breakout_date']).strftime('%B %Y')}",
        f"from: {frm}", f"to: {to}", "tf: D",
        f"line: {ref} | {display_name} | candles",
        f"line: {ref}@vol | Volume | pane2 bars",
        f"level: {ev['pivot']:.2f} | Pivot | {ev['bh_date']} {to} | pivot",
    ]
    if ev["stop"]:
        lines.append(f"level: {ev['stop']:.2f} | Stop | {ev['bh_date']} {to} | stop")
    lines += [
        f"mark: {ev['breakout_date']} | breakout {ev['pivot']:.2f}",
        f"mark: {ev['outcome_date']} | {outcome_label}",
        "caption: Study the base in the weeks before the breakout — the contractions tightening, "
        "volume drying up, then expanding through the pivot.",
    ]
    return "```series\n" + "\n".join(lines) + "\n```"


METHODOLOGY = f"""# Major breakouts: successful vs. failed, US and India

This page studies what a major breakout looks like before it happens — the base, the
volume, the pivot — by lining up real historical examples that held and ran, next to ones
that broke out and immediately failed.

## How these were chosen

- **Universe**: large-cap stocks only, per each market's own large-cap definition (the US
  $10B+ convention; India's SEBI/AMFI top-100-by-market-cap rule) — well-known names, not
  obscure small caps.
- **Breakout**: a close through a completed VCP base's pivot that the Minervini strategy's
  own MV-01 entry tests would have bought — volume at least {VOL_MULT}× the 50-day average,
  no more than {BUY_RANGE_PCT:g}% past the pivot, closing in the upper half of the day's
  range (the same base detector, breakout tests and pivot/stop/measured-move levels the
  app's own Minervini strategy and chart indicator use — nothing here is recomputed by hand).
- **Successful**: the close never fell back below the pivot in the {HOLD_WINDOW} sessions
  after the breakout, and within {FOLLOW_THROUGH_HORIZON} sessions (~3 months) it either
  gained {FOLLOW_THROUGH_PCT:g}%+ from the pivot or made a fresh high.
- **Failed**: the close fell back below the pivot within {HOLD_WINDOW} sessions of the
  breakout.
- Breakouts that held the pivot but never showed real follow-through were left out — neither
  a clean success nor a clean failure.
- Kept to under 100 per country, ranked by how "major" the event was (market cap, the
  breakout day's volume surge, and the size of the eventual move or giveback).

India's stored price history is much shorter than the US's, so its examples skew more
recent — not a sign failures or successes cluster in any particular period, just a data
limit.

## Case studies
"""


def _interleave(successful: list[dict], failed: list[dict]) -> list[dict]:
    """Alternate the two outcomes (each already ranked by how major it is) so every page mixes
    successful and failed cases, instead of a global score sort clustering big-gain successes
    first and small-giveback failures last."""
    out, i, j = [], 0, 0
    while i < len(successful) or j < len(failed):
        if i < len(successful):
            out.append(successful[i]); i += 1
        if j < len(failed):
            out.append(failed[j]); j += 1
    return out


def render(events_path: Path, chunk_size: int) -> None:
    events = json.loads(events_path.read_text())
    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    index_lines = [METHODOLOGY]
    for market in ("us", "india"):
        mkt_events = [e for e in events if e["market"] == market]
        if not mkt_events:
            continue
        mkt_events = _interleave([e for e in mkt_events if e["outcome"] == "successful"],
                                  [e for e in mkt_events if e["outcome"] == "failed"])
        name_map = names.load(market)
        index_lines.append(f"\n### {MARKETS[market].name}\n")
        chunks = [mkt_events[i:i + chunk_size] for i in range(0, len(mkt_events), chunk_size)]
        for n, chunk in enumerate(chunks, 1):
            fname = f"app-guide-breakouts-{market}-{n}.md"
            title = f"Major breakouts — {MARKETS[market].name} ({n} of {len(chunks)})"
            fences = [_fence(ev, names.lookup(name_map, ev["symbol"]) or ev["symbol"]) for ev in chunk]
            (paths.RESEARCH_DIR / fname).write_text(f"# {title}\n\n" + "\n\n".join(fences) + "\n")
            succ = sum(1 for e in chunk if e["outcome"] == "successful")
            index_lines.append(f"- [{title}]({fname}) — {succ} successful, {len(chunk) - succ} failed")
    (paths.RESEARCH_DIR / "app-guide-breakouts.md").write_text("\n".join(index_lines) + "\n")
    print(f"wrote {paths.RESEARCH_DIR / 'app-guide-breakouts.md'} and its linked pages")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scan", type=Path, help="scan and write candidate events to this JSON file")
    ap.add_argument("--render", type=Path, help="render research/ pages from a --scan JSON file")
    ap.add_argument("--market", choices=list(MARKETS), help="scan only this market (default: both)")
    ap.add_argument("--limit-symbols", type=int, help="scan only the top N candidates per market (testing)")
    ap.add_argument("--workers", type=int, default=6, help="parallel symbol scans")
    ap.add_argument("--chunk-size", type=int, default=20, help="case studies per rendered page")
    a = ap.parse_args()
    if a.scan:
        markets = [a.market] if a.market else list(MARKETS)
        all_events = []
        for market in markets:
            print(f"scanning {market}...")
            all_events.extend(scan_market(market, a.limit_symbols, a.workers))
        print(f"{len(all_events)} raw qualifying events; selecting the major ones per country")
        selected = []
        for market in markets:
            selected.extend(select_major([e for e in all_events if e["market"] == market]))
        a.scan.write_text(json.dumps(selected, indent=2))
        print(f"{len(selected)} events written to {a.scan}")
    elif a.render:
        render(a.render, a.chunk_size)
    else:
        ap.error("pass --scan or --render")


if __name__ == "__main__":
    main()
