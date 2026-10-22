"""O'Neil's CAN SLIM: a strategy view over the shared metrics of `fundamentals/growth.py`, plus the
stock's chart and the market.

William O'Neil's seven letters: C (current quarterly earnings), A (annual earnings), N (a new high),
S (supply and demand), L (a leader), I (institutional sponsorship), M (the market's direction). C and A
come from the filings — the same numbers every strategy sees (growth.metrics). N, S, L, I and M come from
the stock's prices, its RS rank, its shareholding and the index: `context()` gathers them for one
company, and `evaluate()` judges whatever it is given (without a context, only C and A are scored).
The Fundamentals page shows it as the CAN SLIM section; the rules match the Learn guide's.

Every threshold is a module constant and the page renders the rules from them.

Not investment advice: these are screening rules of thumb over filings that can be restated.
"""

from __future__ import annotations

import datetime as dt

from .growth import ANNUAL_YEARS, metrics as _metrics  # noqa: F401 — ANNUAL_YEARS is a {placeholder} in TESTS

key = "canslim"

# ---------------------------------------------------------------- thresholds
EPS_Q_GROWTH_MIN = 0.25       # C1: latest quarter's EPS growth vs the same quarter a year ago
SALES_Q_GROWTH_MIN = 0.20     # C2: latest quarter's sales growth ...
SALES_ACCEL_QUARTERS = 3      # ... or sales growth rising this many quarters in a row
ANNUAL_EPS_GROWTH_MIN = 0.25  # A1: EPS growth in EACH of the last ANNUAL_YEARS years (growth.py)
ROE_MIN = 0.17                # A2: trailing-twelve-month return on equity
NEW_HIGH_MAX_BELOW = 0.15     # N: price within this of the 52-week high
UPDOWN_SESSIONS = 50          # S: volume on up days vs down days over this many sessions ...
UPDOWN_MIN = 1.0              # ... up-day volume above down-day volume
RS_MIN = 80                   # L: relative-strength percentile (12-month performance rank) at least this
MARKET_SMA = 50               # M: the index closes above this moving average ...
DIST_SESSIONS = 25            # ... with at most DIST_MAX distribution days (down 0.2%+ on higher volume)
DIST_MAX = 4                  #     in this many sessions
MIN_GROWTH_READINGS = 2       # fewer EPS growth readings (of the last 4) than this = not scored

TESTS = (
    ("C1", "Current EPS", "Latest quarter's EPS up at least {EPS_Q_GROWTH_MIN:.0%} on the same quarter a year earlier"),
    ("C2", "Current sales", "Latest quarter's sales up at least {SALES_Q_GROWTH_MIN:.0%} a year, or sales growth rising "
                            "{SALES_ACCEL_QUARTERS} quarters in a row"),
    ("A1", "Annual EPS", "Annual EPS up at least {ANNUAL_EPS_GROWTH_MIN:.0%} in each of the last {ANNUAL_YEARS} years "
                         "(fiscal years, else trailing twelve months)"),
    ("A2", "Return on equity", "Trailing-twelve-month return on equity at least {ROE_MIN:.0%}"),
    ("N", "New high", "Price within {NEW_HIGH_MAX_BELOW:.0%} of its 52-week high"),
    ("S", "Supply and demand", "Over the last {UPDOWN_SESSIONS} sessions, volume on up days above volume on down days"),
    ("L", "Leader", "Relative-strength rank (12-month performance, percentile) at least {RS_MIN}"),
    ("I", "Institutional sponsorship", "Combined FII and DII holding higher than a quarter earlier (India's shareholding "
                                       "filings; not available for US stocks)"),
    ("M", "Market direction", "The market index above its {MARKET_SMA}-day average, with at most {DIST_MAX} distribution "
                              "days in the last {DIST_SESSIONS} sessions"),
)
EARNINGS = ("C1", "C2", "A1")                 # must pass for any CAN SLIM verdict
EARNINGS_NOT_FAILING = ("A2",)                # must pass or be unavailable
STOCK_AND_MARKET = ("N", "S", "L")            # must pass for QUALIFIES ...
STOCK_AND_MARKET_NOT_FAILING = ("I", "M")     # ... and these pass or be unavailable


def _fmt(text: str) -> str:
    return text.format(**{k: v for k, v in globals().items() if k.isupper()})


DOC = {
    "key": key,
    "name": "CAN SLIM",
    "strategy": None,
    "description": "William O'Neil's seven letters: current and annual earnings from the filings, then the stock's "
                   "new high, its volume, its strength, its owners and the market.",
    "thesis": "O'Neil studied the biggest winners and found they had strong current and annual earnings growth, broke "
              "out to new highs on heavy demand, led their groups, drew institutional buying, and rose in a rising market.",
    "verdicts": (
        "QUALIFIES — every letter passes: C1, C2, A1, N, S and L pass; A2, I and M pass or are unavailable.",
        "EARNINGS PASS — C1, C2 and A1 pass (A2 not failing), but the stock or the market does not yet: wait for N, S, "
        "L or M.",
        "WEAK — C or A fails: the earnings are not there.",
        _fmt("NO DATA — fewer than {MIN_GROWTH_READINGS} of the last four quarters have an EPS growth reading, or the "
             "latest results are stale."),
    ),
    "caveats": (
        "O'Neil reads the letters together with a chart: a stock should also be breaking out of a proper base. "
        "The base itself is the strategy's job, not this scorecard's.",
        "Growth from a loss is not measurable, so it does not pass C1.",
        "I uses India's quarterly shareholding filings (FII and DII); there is no US equivalent stored, so it is "
        "unavailable for US stocks.",
        "M is the same for every stock in the market; when it fails, O'Neil buys nothing new.",
        "One-off gains and charges are not removed from earnings.",
    ),
}


def criteria() -> dict:
    return {**DOC, "tests": [{"key": k, "label": label, "text": _fmt(t)} for k, label, t in TESTS]}


def _rising(vals: list, n: int) -> bool | None:
    v = vals[:n]
    if len(v) < n or any(x is None for x in v):
        return None
    return all(v[k] > v[k + 1] for k in range(n - 1))


def context(market: str, symbol: str, srow: dict | None = None, shareholding: list | None = None) -> dict:
    """The non-filing inputs for N, S, L, I and M, from stored prices, the day's snapshot row and the
    shareholding pattern. Anything missing is left out (its letter is then unavailable)."""
    from swing_screener.config import MARKETS
    from swing_screener.core import demand_supply as ds
    from swing_screener.marketdata import cache

    srow, ctx = srow or {}, {}
    daily = cache.load_cached(market, symbol)
    if daily is not None and len(daily) > UPDOWN_SESSIONS:
        daily = daily[~((daily["volume"] <= 0) & (daily["high"] <= daily["low"]))]
        price = float(daily["close"].iloc[-1])
        yr = daily[daily.index > daily.index[-1] - dt.timedelta(days=365)]
        ctx["price"], ctx["high_52w"] = price, float(yr["high"].max())
        ctx["updown"] = ds.up_down_volume_ratio(daily, UPDOWN_SESSIONS)
    if srow.get("rs_rank") is not None:
        ctx["rs_rank"] = float(srow["rs_rank"])
    sh = [r for r in (shareholding or []) if r.get("fii") is not None and r.get("dii") is not None]
    if len(sh) >= 2:
        ctx["inst_now"], ctx["inst_prev"] = sh[-1]["fii"] + sh[-1]["dii"], sh[-2]["fii"] + sh[-2]["dii"]
    cfg = MARKETS.get(market)
    idx = cache.load_cached(market, cfg.benchmark_ticker) if cfg else None
    if idx is not None and len(idx) > MARKET_SMA:
        close = float(idx["close"].iloc[-1])
        sma = float(idx["close"].iloc[-MARKET_SMA:].mean())
        _, dist = ds.accumulation_distribution_days(idx, DIST_SESSIONS)
        ctx["market"] = {"index": cfg.benchmark_symbol, "above_sma": close > sma, "dist_days": int(dist)}
    return ctx


def evaluate(m: dict, ctx: dict | None = None) -> dict:
    """growth.metrics() (+ context()) -> {verdict, passed, scored, tests}. Without a context, N–M are unavailable."""
    if not m.get("quarters"):
        return {"verdict": "NO DATA", "code33": False, "passed": 0, "scored": 0, "tests": {}}
    ctx = ctx or {}
    eg, sg = m["eps_g"], m["rev_g"]
    tests: dict[str, dict] = {}

    def put(k, ok, value=None, detail="", unit="pct"):
        tests[k] = {"status": "na" if ok is None else "pass" if ok else "fail", "value": value, "detail": detail, "unit": unit}

    # C1
    if eg[0] is None:
        put("C1", False if m["latest_has_prior"] else None, None,
            "the year-ago quarter was a loss" if m["latest_has_prior"] else "no year-ago quarter")
    else:
        put("C1", eg[0] >= EPS_Q_GROWTH_MIN, eg[0])
    # C2
    acc = _rising(sg, SALES_ACCEL_QUARTERS)
    if sg[0] is None:
        put("C2", None, None, "no year-ago quarter")
    else:
        put("C2", sg[0] >= SALES_Q_GROWTH_MIN or bool(acc), sg[0], "growth rising" if acc and sg[0] < SALES_Q_GROWTH_MIN else "")
    # A1: each year's growth, newest first
    years, basis = m["eps_annual"], m["eps_annual_basis"]
    if years is None:
        put("A1", None, None, f"needs {ANNUAL_YEARS + 1} fiscal years (or {4 * (ANNUAL_YEARS + 1)} consecutive quarters)")
    elif any(x <= 0 for x in years[1:]):
        put("A1", False, None, f"a loss-making year ({basis})")
    else:
        rates = [years[k] / years[k + 1] - 1 for k in range(ANNUAL_YEARS)]
        put("A1", all(r >= ANNUAL_EPS_GROWTH_MIN for r in rates), min(rates),
            "lowest of " + " · ".join(f"{r:+.0%}" for r in rates) + f" ({basis})")
    # A2
    r = m["roe"]
    put("A2", None if r is None else r >= ROE_MIN, r, "" if r is None else f"from {m['roe_source']}")
    # N
    if ctx.get("price") and ctx.get("high_52w"):
        below = 1 - ctx["price"] / ctx["high_52w"]
        put("N", below <= NEW_HIGH_MAX_BELOW, -below, "below the 52-week high" if below > 0.001 else "at the 52-week high")
    else:
        put("N", None, None, "no stored prices")
    # S
    ud = ctx.get("updown")
    put("S", None if ud is None else ud > UPDOWN_MIN, ud, "" if ud is None else "up-day / down-day volume", unit="ratio")
    # L
    rs = ctx.get("rs_rank")
    put("L", None if rs is None else rs >= RS_MIN, rs, "" if rs is not None else "no RS rank today", unit="num")
    # I
    if ctx.get("inst_now") is not None:
        d = ctx["inst_now"] - ctx["inst_prev"]
        put("I", d > 0, d, f"FII + DII {ctx['inst_now']:.1%}, was {ctx['inst_prev']:.1%}", unit="pt")
    else:
        put("I", None, None, "no shareholding filings stored")
    # M
    mk = ctx.get("market")
    if mk:
        ok = mk["above_sma"] and mk["dist_days"] <= DIST_MAX
        put("M", ok, mk["dist_days"], f"{mk['index']} {'above' if mk['above_sma'] else 'below'} its {MARKET_SMA}-day · "
                                      f"{mk['dist_days']} distribution days", unit="num")
    else:
        put("M", None, None, "no index prices")

    st = {k: v["status"] for k, v in tests.items()}
    earnings = all(st[k] == "pass" for k in EARNINGS) and all(st[k] != "fail" for k in EARNINGS_NOT_FAILING)
    if sum(x is not None for x in eg[:4]) < MIN_GROWTH_READINGS or m["stale"]:
        verdict = "NO DATA"
    elif earnings and all(st[k] == "pass" for k in STOCK_AND_MARKET) and all(st[k] != "fail" for k in STOCK_AND_MARKET_NOT_FAILING):
        verdict = "QUALIFIES"
    elif earnings:
        verdict = "EARNINGS PASS"
    else:
        verdict = "WEAK"
    return {"verdict": verdict, "code33": False, "passed": sum(v == "pass" for v in st.values()),
            "scored": sum(v != "na" for v in st.values()), "tests": tests}


def counts(r: dict) -> dict:
    """What growth.run() reports for this view (C and A only there: the batch has no context)."""
    return {f"canslim_{r['verdict'].lower().replace(' ', '_')}": 1}


def score(rows: list[dict], meta: dict | None = None, today: dt.date | None = None, roe_fallback: float | None = None) -> dict:
    """Convenience: quarters -> metrics -> this view's verdict (C and A only)."""
    return evaluate(_metrics(rows, meta, today, roe_fallback))
