"""Support & resistance levels (core/sr_levels.py, the chart's S/R indicator): a golden set and invariants.

Two checks, both on stored daily prices cut at fixed dates (so new prices cannot move them):

1. **Golden set** (`sr_golden.json`). Cases where the levels are plain on the candle chart — a double
   bottom broken and now overhead, a triple top, a gap with no history inside it, an all-time high with
   nothing above. Each states the levels a careful reader marks, labelled from the bare candles before the
   module's output was looked at. A `must` expectation that fails, fails this test; a `should` one is
   reported as a miss; a `must` carrying a `known` note (why the module does not draw it yet) is reported
   as KNOWN every run without failing, so the gap stays in view. A level passes when a KEY zone (what the chart draws by default) of an allowed role
   contains the price, within `tol_atr` x the chart timeframe's ATR of its edges.

2. **Invariants**, on the golden cases and a fixed sample of symbols x dates x {daily, weekly} charts —
   rules that hold for every chart whatever one thinks of a particular level:
   - a support lies wholly below the close, a resistance above, a pivot at it; the line sits on the near edge;
   - key zones never overlap, lie within the relevance window (unless promoted to fill a gap), and number
     at most MAX_KEY;
   - no zone is taller than CAP_ATR of its own timeframe's ATR, and `height_atr` says how tall it is;
   - every visit is a real bar high (H) or low (L) on or before the as-of date, is listed once, came to the
     zone (a high at or above its bottom, a low at or below its top), and the zone starts at its first visit.

Run from scripts/ (about a minute):

    PYTHONPATH=. .venv/bin/python -m tests.test_sr_levels
    PYTHONPATH=. .venv/bin/python -m tests.test_sr_levels --case INTC-2024-08-09 -v   # one case, every zone
"""

from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

from swing_screener.core import indicators as ind
from swing_screener.core import sr_levels as sr
from swing_screener.marketdata import cache

GOLDEN = Path(__file__).resolve().parent / "sr_golden.json"
SAMPLE_DATES = ("2019-06-28", "2023-03-15", "2026-09-30")
EPS = 1e-6


def _load(market: str, symbol: str, as_of: str) -> pd.DataFrame | None:
    d = cache.load_cached(market, symbol)
    if d is None or d.empty:
        return None
    d = d.loc[:as_of]
    return d if len(d) >= 300 else None


def _ap(daily: pd.DataFrame, tf: str) -> float:
    """ATR as a share of price on `tf` bars — the unit sr_levels measures a zone's height in."""
    b = sr.bars(daily, tf)
    return float(ind.atr(b, sr.ATR_BARS).iloc[-1]) / float(b["close"].iloc[-1])


# ---- invariants ---------------------------------------------------------------------------------------

def invariants(daily: pd.DataFrame, tf: str, r: dict) -> list[str]:
    errs: list[str] = []
    close = r["close"]
    clean = sr.bars(daily, "D")
    ap = {t: _ap(daily, t) for t in ("D", "W", "M")}
    near = sr.AT_PRICE_ATR * ap["D"] * close
    win = {"D": 0, "W": 8, "M": 35}
    keys = r["zones"]
    for z in keys + r["others"] + r.get("longterm", []):
        kind = "key" if any(z is k for k in keys) else "other"
        lo, hi, name = z["bottom"], z["top"], f"{kind} {z['role']} {z['tf']} {z['bottom']:.2f}-{z['top']:.2f}"
        if lo > hi:
            errs.append(f"{name}: bottom above top")
        if z["role"] == "support" and not hi < close:
            errs.append(f"{name}: a support reaching the close {close:.2f}")
        if z["role"] == "resistance" and not lo > close:
            errs.append(f"{name}: a resistance reaching the close {close:.2f}")
        if z["role"] == "pivot" and not lo - near - EPS <= close <= hi + near + EPS:
            errs.append(f"{name}: a pivot away from the close {close:.2f}")
        if z["role"] == "support" and abs(z["line"] - hi) > EPS or z["role"] == "resistance" and abs(z["line"] - lo) > EPS:
            errs.append(f"{name}: line {z['line']:.2f} not on the near edge")
        if not lo - EPS <= z["line"] <= hi + EPS:
            errs.append(f"{name}: line {z['line']:.2f} outside the zone")
        u = ap[z["tf"]] * z["reference"]
        if z["height_atr"] > sr.CAP_ATR + 0.01:
            errs.append(f"{name}: {z['height_atr']} x {z['tf']} ATR tall (cap {sr.CAP_ATR})")
        if abs((hi - lo) / u - z["height_atr"]) > 0.02 + 0.01 * z["height_atr"]:
            errs.append(f"{name}: height_atr {z['height_atr']} but {(hi - lo) / u:.2f} measured")
        ts = z["touches"]
        if not ts:
            errs.append(f"{name}: no visits")
            continue
        if len({(t["date"], t["kind"]) for t in ts}) != len(ts):
            errs.append(f"{name}: a visit listed twice {[t['date'] for t in ts]}")
        if z["from"] > min(t["date"] for t in ts):
            errs.append(f"{name}: starts {z['from']}, after its first visit")
        if z["from"] < min(t["date"] for t in ts) and not z.get("merged"):
            errs.append(f"{name}: starts {z['from']}, before its first visit {min(t['date'] for t in ts)}")
        tol = 0.15 * u
        for t in ts:
            dt = pd.Timestamp(t["date"])
            if dt > daily.index[-1]:
                errs.append(f"{name}: visit {t['date']} after the as-of date")
            col = "high" if t["kind"] == "H" else "low"
            seg = clean[col].loc[dt - pd.Timedelta(days=win[z["tf"]]):dt]
            if not (abs(seg - t["price"]) < EPS * max(1.0, t["price"])).any():
                errs.append(f"{name}: visit {t['date']} {t['price']:.2f} is not a bar {col}")
            if t["kind"] == "H" and t["price"] < lo - tol or t["kind"] == "L" and t["price"] > hi + tol:
                errs.append(f"{name}: visit {t['date']} {t['kind']} {t['price']:.2f} never reached the zone")
    s = sorted(keys, key=lambda z: z["bottom"])
    for a, b in zip(s, s[1:]):
        if b["bottom"] < a["top"] - EPS:
            errs.append(f"key zones overlap: {a['bottom']:.2f}-{a['top']:.2f} and {b['bottom']:.2f}-{b['top']:.2f}")
    own = sr.STACK[tf][1]
    window = sr.RELEVANCE_ATR[own] * ap[own] * close
    for z in keys:
        if abs(z["line"] - close) > window * 1.001 and not z.get("promoted"):
            errs.append(f"key {z['role']} {z['line']:.2f} is {abs(z['line'] - close) / (ap[own] * close):.1f} ATR from the close")
    if len(keys) > sr.MAX_KEY + 2:
        errs.append(f"{len(keys)} key zones (MAX_KEY {sr.MAX_KEY})")
    return errs


# ---- golden expectations ------------------------------------------------------------------------------

def expectation(e: dict, r: dict, unit: float) -> tuple[bool, str]:
    """(passed, what was found) for one expectation."""
    keys = r["zones"]
    if "no_key" in e:
        bad = [z for z in keys if z["role"] == e["no_key"]]
        return not bad, ("none" if not bad else ", ".join(f"{z['bottom']:.2f}-{z['top']:.2f}" for z in bad))
    if "empty" in e:
        a, b = e["empty"]
        bad = [z for z in keys if z["bottom"] <= b and z["top"] >= a]
        return not bad, ("empty" if not bad else ", ".join(f"{z['role']} {z['bottom']:.2f}-{z['top']:.2f}" for z in bad))
    if "line" in e:
        ok = [l for l in r["lines"] if l["kind"] == e["line"]]
        return bool(ok), (f"{ok[0]['label']} at {ok[0]['price']:.2f}" if ok else "no such line")
    px, tol = e["level"], unit
    roles = e.get("role", "any")
    roles = [roles] if isinstance(roles, str) else roles
    hit = [z for z in keys if (roles == ["any"] or z["role"] in roles) and z["bottom"] - tol <= px <= z["top"] + tol]
    if hit:
        z = hit[0]
        return True, f"{z['role']} {z['tf']} {z['bottom']:.2f}-{z['top']:.2f}"
    if e.get("or_line"):
        ln = [l for l in r["lines"] if abs(l["price"] - px) <= tol]
        if ln:
            return True, f"line: {ln[0]['label']} {ln[0]['price']:.2f}"
    near = sorted(keys + r["others"], key=lambda z: min(abs(z["bottom"] - px), abs(z["top"] - px)))[:1]
    if near:
        z = near[0]
        where = "key" if any(z is k for k in keys) else f"not key, score {z['score']}, {len(z['touches'])} visit(s)"
        return False, f"nearest: {z['role']} {z['tf']} {z['bottom']:.2f}-{z['top']:.2f} ({where})"
    return False, "nothing near"


def _golden_case(c: dict, tol_atr: float) -> dict:
    d = _load(c["market"], c["symbol"], c["as_of"])
    if d is None:
        return {"id": c["id"], "error": "no stored prices"}
    r = sr.levels(d, c["tf"])
    unit = tol_atr * _ap(d, sr.STACK[c["tf"]][1]) * r["close"]
    res = [(e, *expectation(e, r, unit)) for e in c["expect"]]
    return {"id": c["id"], "results": res, "invariants": invariants(d, c["tf"], r), "levels": r}


def _sample_case(a: tuple) -> tuple:
    market, symbol, as_of, tf = a
    try:
        d = _load(market, symbol, as_of)
        if d is None:
            return a, None
        return a, invariants(d, tf, sr.levels(d, tf))
    except Exception as e:  # noqa: BLE001 — a crash is a finding
        return a, [f"crash: {type(e).__name__}: {e}"]


def _describe(z: dict) -> str:
    return (f"{z['role']:10s} {z['tf']} {z['bottom']:10.2f}-{z['top']:10.2f} line {z['line']:10.2f} score {z['score']} "
            f"visits {[(t['date'], round(t['price'], 2), t['kind']) for t in z['touches']]}"
            + "".join(f" [{k}]" for k in ("promoted", "capped", "merged", "refined", "flipped", "congestion") if z.get(k)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--case", help="run one golden case only")
    ap.add_argument("-v", "--verbose", action="store_true", help="print every key and graded zone of each case")
    ap.add_argument("--no-sample", action="store_true", help="skip the invariants sample")
    a = ap.parse_args(argv)
    g = json.loads(GOLDEN.read_text())
    cases = [c for c in g["cases"] if not a.case or c["id"] == a.case]
    failed, misses, inv_bad, known = 0, 0, 0, 0
    with Pool(8) as pool:
        out = pool.starmap(_golden_case, [(c, g["tol_atr"]) for c in cases])
        print(f"Golden set: {len(cases)} cases")
        for c, o in zip(cases, out):
            if "error" in o:
                print(f"  {o['id']}: {o['error']}")
                failed += 1
                continue
            bad = [x for x in o["results"] if not x[1] and x[0].get("must") and not x[0].get("known")]
            soft = [x for x in o["results"] if not x[1] and not x[0].get("must")]
            known += sum(1 for x in o["results"] if not x[1] and x[0].get("known"))
            failed += len(bad)
            misses += len(soft)
            inv_bad += len(o["invariants"])
            mark = "FAIL" if bad or o["invariants"] else "ok  "
            print(f"  {mark} {o['id']:22s} must {sum(1 for x in o['results'] if x[0].get('must') and x[1])}/"
                  f"{sum(1 for x in o['results'] if x[0].get('must'))}  should {sum(1 for x in o['results'] if not x[0].get('must') and x[1])}/"
                  f"{sum(1 for x in o['results'] if not x[0].get('must'))}"
                  + (f"  ({sum(1 for x in o['results'] if not x[1] and x[0].get('known'))} known gap)" if any(not x[1] and x[0].get("known") for x in o["results"]) else ""))
            for e, ok, found in o["results"]:
                if not ok or a.verbose:
                    what = (f"level {e['level']} {e.get('role', 'any')}" if "level" in e else
                            f"no key {e['no_key']}" if "no_key" in e else f"empty {e['empty']}" if "empty" in e else f"line {e['line']}")
                    tag = "ok  " if ok else "KNOWN" if e.get("known") else "MISS" if e.get("must") else "miss"
                    print(f"       {tag} {what}: {found} — {e['why']}" + (f"\n             known: {e['known']}" if e.get("known") and not ok else ""))
            for m in o["invariants"]:
                print(f"       INVARIANT {m}")
            if a.verbose:
                r = o["levels"]
                print(f"       close {r['close']:.2f}")
                for z in r["zones"]:
                    print(f"       KEY   {_describe(z)}")
                for z in r["others"]:
                    print(f"       other {_describe(z)}")
                print(f"       lines {[(l['kind'], round(l['price'], 2)) for l in r['lines']]}")
        if not a.no_sample and not a.case:
            jobs = [(m, s, dt, tf) for m, syms in g["_sample"].items() for s in syms for dt in SAMPLE_DATES for tf in ("D", "W")]
            done, bad_cases = 0, []
            for args, errs in pool.imap_unordered(_sample_case, jobs, chunksize=2):
                if errs is None:
                    continue
                done += 1
                if errs:
                    bad_cases.append((args, errs))
            print(f"\nInvariants: {done} charts ({len(g['_sample']['us'])} US + {len(g['_sample']['india'])} India symbols"
                  f" x {len(SAMPLE_DATES)} dates x daily/weekly), {len(bad_cases)} with a violation")
            for args, errs in sorted(bad_cases)[:25]:
                print(f"  {args}")
                for m in errs[:4]:
                    print(f"      {m}")
            inv_bad += sum(len(e) for _, e in bad_cases)
    print(f"\n{'FAIL' if failed or inv_bad else 'OK'} — {failed} must-level miss(es), {known} known gap(s), "
          f"{misses} should-level miss(es), {inv_bad} invariant violation(s)")
    return 1 if failed or inv_bad else 0


if __name__ == "__main__":
    sys.exit(main())
