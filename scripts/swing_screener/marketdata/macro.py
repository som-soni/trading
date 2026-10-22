"""Macro series to read beside the market: rates, the dollar, oil, metals, credit.

These are levels to WATCH, not series to invest in, so they differ from `index_data` on purpose:
raw daily closes (no dividend adjustment), and no outlier repair or positivity filter — WTI really
did settle at -37.63 on 2020-04-20, and VIX-like spikes are the point, not artefacts. They land in
the same `index_series` table under the market each one informs most, so each market's `indexes`
job refreshes its own few:

    us     US10Y, US5Y (yields, %), DXY, WTI, GOLD_FUT, COPPER, NATGAS, HYG (high-yield credit)
    india  BRENT (India imports most of its oil); USD/INR and India VIX are already stored by
           index_data and the Breadth page

Yahoo has no India 10-year government bond yield, so it is not here.

`analysis(market)` reads them for the Today page: SIGNALS (rates, curve, dollar, oil, rupee, credit, growth,
fear) each supportive or a headwind against the thresholds below, a label from the count (MACRO_TONE), and
where each series stands against its history since RANK_SINCE.

    PYTHONPATH=. python3 -m swing_screener.marketdata.macro            # refresh both markets
    PYTHONPATH=. python3 -m swing_screener.marketdata.macro --list     # what is stored
"""

import argparse
import logging
import warnings
from dataclasses import dataclass

import pandas as pd

from . import db

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Macro:
    key: str        # series name in index_series
    ticker: str     # Yahoo symbol
    label: str
    unit: str       # "%" for a yield, else what the price is quoted in
    why: str        # what it tells a trader, for the app
    short: str = ""  # the strip's tile label (label when empty)


SERIES: dict[str, list[Macro]] = {
    "us": [
        Macro("US10Y", "^TNX", "US 10-year Treasury yield", "%",
              "Rising long yields pressure growth-stock valuations; sharp jumps often come with selling.", short="US 10Y yield"),
        Macro("US5Y", "^FVX", "US 5-year Treasury yield", "%",
              "Moves with where the market expects the Fed to take rates over the next few years.", short="US 5Y yield"),
        Macro("DXY", "DX-Y.NYB", "US Dollar Index", "index",
              "A strong dollar weighs on emerging markets (India included) and on US multinationals.", short="Dollar index"),
        Macro("WTI", "CL=F", "WTI crude oil", "$/bbl",
              "Energy stocks, inflation expectations, consumer spending.", short="WTI crude"),
        Macro("GOLD_FUT", "GC=F", "Gold", "$/oz",
              "Fear and hedging demand; falls when real yields rise.", short="Gold"),
        Macro("COPPER", "HG=F", "Copper", "$/lb",
              "A rough read on global industrial growth; metals and miners.", short="Copper"),
        Macro("NATGAS", "NG=F", "Natural gas (Henry Hub)", "$/MMBtu",
              "Heating/cooling demand and power-generation cost; a swing factor for utilities and chemicals margins.", short="Nat gas"),
        Macro("HYG", "HYG", "High-yield corporate bonds (HYG)", "$",
              "Credit risk appetite: HYG falling while stocks rise is an early warning.", short="HY credit (HYG)"),
    ],
    "india": [
        Macro("BRENT", "BZ=F", "Brent crude oil", "$/bbl",
              "India imports most of its oil: dearer crude widens the deficit, weakens the rupee and "
              "lifts inflation. Oil marketers, paints, aviation, tyres.", short="Brent crude"),
    ],
}


# Read-only extras the strip shows but this module does not fetch (index_data stores them).
EXTRA = {
    ("india", "USDINR"): Macro("USDINR", "INR=X", "US dollar in rupees", "₹",
                               "A weaker rupee usually comes with foreign selling of Indian stocks; it helps IT "
                               "exporters and hurts importers.", short="USD/INR"),
}

# What each market's macro strip shows, in order: (stored market, series). India's includes the US 10-year
# and the dollar, which drive foreign flows into India.
STRIP: dict[str, list[tuple[str, str]]] = {
    "us": [("us", "US10Y"), ("us", "US5Y"), ("us", "DXY"), ("us", "WTI"), ("us", "GOLD_FUT"), ("us", "COPPER"),
           ("us", "NATGAS"), ("us", "HYG")],
    "india": [("india", "BRENT"), ("india", "USDINR"), ("us", "US10Y"), ("us", "DXY"), ("us", "GOLD_FUT")],
}


def _meta(market: str, key: str) -> Macro | None:
    return next((m for m in SERIES.get(market, []) if m.key == key), None) or EXTRA.get((market, key))


def fetch(m: Macro) -> pd.Series:
    """Full daily history of one series, raw closes."""
    import yfinance as yf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = yf.Ticker(m.ticker).history(period="max", interval="1d", auto_adjust=False)
    if raw is None or raw.empty:
        raise ValueError(f"{m.ticker}: no data returned")
    s = raw["Close"].dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s[~s.index.duplicated(keep="last")].sort_index()


def refresh(market: str) -> dict[str, int]:
    """Fetch and upsert each of the market's macro series. -> {key: rows stored (0 = failed)}."""
    from . import index_data
    index_data.init_schema()
    out = {}
    for m in SERIES.get(market, []):
        try:
            s = fetch(m)
            db.execute_values(
                "INSERT INTO index_series (market, series, date, close) VALUES %s "
                "ON CONFLICT (market, series, date) DO UPDATE SET close = EXCLUDED.close",
                [(market, m.key, d.date(), float(c)) for d, c in s.items()])
            out[m.key] = len(s)
        except Exception as exc:  # noqa: BLE001 — one missing series must not stop the rest
            logger.warning("macro %s (%s) failed: %s", m.key, m.ticker, exc)
            out[m.key] = 0
    return out


def latest(market: str, spark_days: int = 63) -> list[dict]:
    """The market's strip (STRIP): each series' last close, its 1-day and 1-month change — in basis points
    for a yield, percent otherwise — and the last `spark_days` closes for a sparkline. Unstored series are left out."""
    rows = []
    with db.get_connection().cursor() as cur:
        for mk, key in STRIP.get(market, []):
            m = _meta(mk, key)
            if m is None:
                continue
            cur.execute("SELECT date, close FROM index_series WHERE market=%s AND series=%s ORDER BY date DESC LIMIT %s",
                        (mk, key, max(spark_days, 22)))
            got = cur.fetchall()
            if not got:
                continue
            last_d, last = got[0]
            prev = got[1][1] if len(got) > 1 else None
            month = got[21][1] if len(got) > 21 else None
            bp = m.unit == "%"   # a yield's move is quoted in basis points; a price's in percent

            def chg(a):
                if a is None:
                    return None
                return (last - a) * 100 if bp else ((last / a - 1) * 100 if a else None)
            rows.append({"key": key, "market": mk, "label": m.label, "short": m.short or m.label, "unit": m.unit, "why": m.why, "date": str(last_d),
                         "close": last, "d1": chg(prev), "m1": chg(month), "change_unit": "bp" if bp else "%",
                         "spark": [c for _, c in reversed(got[:spark_days])]})
    return rows


# ---------------------------------------------------------------- the read: is the macro backdrop helping or hurting?

# A rule-based read of the backdrop, like the post-market tone: each market checks SIGNALS, each one either
# supportive (ok) or a headwind, and the count names it (MACRO_TONE). Thresholds are the constants below.
MONTH, QUARTER = 21, 63           # sessions in a month / three months
RANK_SINCE = "2015-01-01"         # levels and moves are ranked against every session since
RATE_JUMP_BP = 25                 # a 10-year yield up this many bp in a month is a valuation headwind
DOLLAR_SURGE_PCT = 2.0            # the dollar index up this much in a month tightens global conditions
OIL_SPIKE_PCT = 15.0              # crude up this much in a month feeds inflation and squeezes margins
INR_WEAK_PCT = 1.5                # the rupee down this much against the dollar in a month (USD/INR up)
CREDIT_SMA = 50                   # high-yield credit (HYG) above its 50-day average = risk appetite intact
VIX_CALM = 20.0                   # US VIX below this = fear contained
INDIA_VIX_CALM = 18.0             # India VIX below this
UNUSUAL_RANK = 95                 # a 1-month move bigger than this percentile of months since RANK_SINCE is "unusual"
EXTREME_RANK = 90                 # a level above this percentile (or below 100 minus it) of days since RANK_SINCE is noted

# (key, supportive text, headwind text, why it matters) — the texts are short list lines; `why` is the hover
_SIG = {
    "rates": ("US 10-year yield steady (under +{RATE_JUMP_BP}bp in a month)",
              "US 10-year yield up {RATE_JUMP_BP}bp+ in a month",
              "Fast-rising long yields pressure growth-stock valuations."),
    "curve": ("Yield curve positively sloped (10Y above 5Y)", "Yield curve inverted (10Y below 5Y)",
              "An inverted curve has preceded most US recessions — a late-cycle warning."),
    "dollar": ("Dollar index not surging (under +{DOLLAR_SURGE_PCT}% in a month)",
               "Dollar index up {DOLLAR_SURGE_PCT}%+ in a month",
               "A surging dollar tightens global conditions and pulls money out of emerging markets."),
    "oil": ("Crude oil calm (under +{OIL_SPIKE_PCT}% in a month)", "Crude oil up {OIL_SPIKE_PCT}%+ in a month",
            "An oil spike feeds inflation and squeezes margins."),
    "rupee": ("Rupee stable (USD/INR up under {INR_WEAK_PCT}% in a month)",
              "Rupee down {INR_WEAK_PCT}%+ against the dollar in a month",
              "A sliding rupee usually comes with foreign selling of Indian stocks."),
    "credit": ("High-yield credit above its {CREDIT_SMA}-day average", "High-yield credit below its {CREDIT_SMA}-day average",
               "Credit (HYG) weakening while stocks hold up is an early warning: risk appetite is fading."),
    "growth": ("Copper outpacing gold over three months", "Gold outpacing copper over three months",
               "Copper rises with expected growth, gold with caution: the ratio shows which the market is pricing."),
    "fear": ("{vix} below {calm:g} — fear contained", "{vix} at {calm:g} or higher — fear elevated",
             "Implied volatility: what options traders pay for protection."),
}
# each market's signals, in order; the series they read are (stored market, series)
SIGNALS: dict[str, list[str]] = {
    "us": ["rates", "curve", "dollar", "oil", "credit", "growth", "fear"],
    "india": ["oil", "rupee", "rates", "dollar", "credit", "growth", "fear"],
}
OIL = {"us": ("us", "WTI"), "india": ("india", "BRENT")}
VIX = {"us": ("us", "VIX", "US VIX", VIX_CALM), "india": ("india", "INDIAVIX", "India VIX", INDIA_VIX_CALM)}
# score (of 7) -> label, highest first
MACRO_TONE = [(6, "Supportive"), (5, "Mostly supportive"), (3, "Mixed"), (2, "Cautious"), (0, "Hostile")]


def _series(market: str, key: str, since: str = RANK_SINCE) -> pd.Series:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, close FROM index_series WHERE market=%s AND series=%s AND date >= %s ORDER BY date",
                    (market, key, since))
        got = cur.fetchall()
    s = pd.Series([float(c) for _, c in got], index=pd.to_datetime([d for d, _ in got]), dtype=float)
    return s.dropna()


def _rank(hist: pd.Series, v: float) -> int | None:
    """Percent of `hist` below v (0–100)."""
    hist = hist.dropna()
    return int(round((hist < v).mean() * 100)) if len(hist) > 50 else None


def analysis(market: str) -> dict | None:
    """The macro read for one market: the signals (ok = supportive), the label they add up to, where each strip
    series stands against its history since RANK_SINCE, and any unusually large 1-month moves. None when the
    market has no signals or its series are not stored."""
    keys = SIGNALS.get(market)
    if not keys:
        return None
    cache: dict[tuple, pd.Series] = {}

    def s(mk, key):
        if (mk, key) not in cache:
            cache[(mk, key)] = _series(mk, key)
        return cache[(mk, key)]

    def chg(x: pd.Series, n: int, bp: bool) -> float | None:
        if len(x) <= n:
            return None
        return (x.iloc[-1] - x.iloc[-1 - n]) * 100 if bp else (x.iloc[-1] / x.iloc[-1 - n] - 1) * 100

    fmt = dict(RATE_JUMP_BP=RATE_JUMP_BP, DOLLAR_SURGE_PCT=f"{DOLLAR_SURGE_PCT:g}", OIL_SPIKE_PCT=f"{OIL_SPIKE_PCT:g}",
               INR_WEAK_PCT=f"{INR_WEAK_PCT:g}", CREDIT_SMA=CREDIT_SMA)
    signals, dates = [], []
    for k in keys:
        ok, detail = None, ""
        if k == "rates":
            y = s("us", "US10Y")
            c = chg(y, MONTH, True)
            if c is not None:
                ok, detail = c < RATE_JUMP_BP, f"{y.iloc[-1]:.2f}% · {c:+.0f}bp"
                dates.append(y.index[-1])
        elif k == "curve":
            sp = (s("us", "US10Y") - s("us", "US5Y")).dropna()
            if len(sp):
                ok, detail = sp.iloc[-1] > 0, f"{sp.iloc[-1] * 100:+.0f}bp spread"
        elif k == "dollar":
            x = s("us", "DXY")
            c = chg(x, MONTH, False)
            if c is not None:
                ok, detail = c < DOLLAR_SURGE_PCT, f"{x.iloc[-1]:.2f} · {c:+.1f}%"
        elif k == "oil":
            mk, key = OIL[market]
            x = s(mk, key)
            c = chg(x, MONTH, False)
            if c is not None:
                ok, detail = c < OIL_SPIKE_PCT, f"${x.iloc[-1]:.2f} · {c:+.1f}%"
        elif k == "rupee":
            x = s("india", "USDINR")
            c = chg(x, MONTH, False)
            if c is not None:
                ok, detail = c < INR_WEAK_PCT, f"₹{x.iloc[-1]:.2f} · {c:+.1f}%"
        elif k == "credit":
            x = s("us", "HYG")
            if len(x) > CREDIT_SMA:
                avg = x.iloc[-CREDIT_SMA:].mean()
                ok, detail = x.iloc[-1] > avg, f"${x.iloc[-1]:.2f} vs ${avg:.2f}"
        elif k == "growth":
            r = (s("us", "COPPER") / s("us", "GOLD_FUT")).dropna()
            c = chg(r, QUARTER, False)
            if c is not None:
                ok, detail = c > 0, f"ratio {c:+.1f}%"
        elif k == "fear":
            mk, key, name, calm = VIX[market]
            x = s(mk, key)
            if len(x):
                ok, detail = x.iloc[-1] < calm, f"{x.iloc[-1]:.1f}"
            fmt.update(vix=name, calm=calm)
        if ok is None:
            continue
        good, bad, why = (t.format(**fmt) for t in _SIG[k])
        signals.append({"key": k, "ok": bool(ok), "text": good, "text_not": bad, "why": why, "detail": detail})
    if not signals:
        return None
    score = sum(x["ok"] for x in signals)
    # the label's cut-offs are for SIGNALS' length; a missing series scales them
    scaled = score * len(keys) / len(signals)
    label = next(lbl for n, lbl in MACRO_TONE if scaled >= n)

    # where each strip series stands, and which moved unusually far this month
    levels, unusual, extremes = [], [], []
    for mk, key in STRIP.get(market, []):
        m = _meta(mk, key)
        x = s(mk, key)
        if m is None or len(x) <= MONTH:
            continue
        bp = m.unit == "%"
        moves = (x.diff(MONTH) * 100) if bp else (x.pct_change(MONTH) * 100)
        last_move = moves.iloc[-1]
        lvl, mv = _rank(x, x.iloc[-1]), _rank(moves.abs(), abs(last_move))
        levels.append({"key": key, "market": mk, "short": m.short or m.label, "level_rank": lvl, "move_rank": mv,
                       "m1": float(last_move), "m3": chg(x, QUARTER, bp), "change_unit": "bp" if bp else "%"})
        name = m.short or m.label
        if lvl is not None and (lvl >= EXTREME_RANK or lvl <= 100 - EXTREME_RANK):
            hi = lvl >= EXTREME_RANK
            extremes.append({"name": name, "text": f"{'' if lvl in (0, 100) else 'near its '}{'highest' if hi else 'lowest'} since {RANK_SINCE[:4]}" if lvl >= 99 or lvl <= 1
                             else f"{'above' if hi else 'below'} {lvl if hi else 100 - lvl}% of days since {RANK_SINCE[:4]}"})
        if mv is not None and mv >= UNUSUAL_RANK:
            unusual.append({"name": name, "text": f"{last_move:+.{0 if bp else 1}f}{'bp' if bp else '%'} in a month — bigger "
                                                  f"than {mv}% of months since {RANK_SINCE[:4]}", "why": m.why})
    return {"label": label, "score": score, "of": len(signals), "signals": signals, "levels": levels, "unusual": unusual, "extremes": extremes,
            "date": str(max(dates).date()) if dates else None,
            "doc": f"Counts how many of {len(keys)} macro signals are supportive for this market: "
                   + ", ".join(f"{n}+ = {lbl}" for n, lbl in MACRO_TONE if n) + f", fewer = {MACRO_TONE[-1][1]}. "
                   f"Ranks compare with every session since {RANK_SINCE[:4]}; a move is unusual past the "
                   f"{UNUSUAL_RANK}th percentile of 1-month moves, and a level is extreme past the {EXTREME_RANK}th (or "
                   f"below the {100 - EXTREME_RANK}th) percentile. Rules in marketdata/macro.py."}


def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh the macro series (rates, dollar, oil, metals, credit)")
    ap.add_argument("--market", choices=list(SERIES), help="one market (default: both)")
    ap.add_argument("--list", action="store_true", help="print what is stored instead of fetching")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for mk in [a.market] if a.market else list(SERIES):
        if a.list:
            for r in latest(mk):
                if r["market"] != mk:
                    continue
                d1 = f"{r['d1']:+.2f}{r['change_unit']}" if r["d1"] is not None else "—"
                print(f"{mk:6s} {r['key']:9s} {r['close']:>10.2f} {r['unit']:6s} {d1:>9s}  {r['date']}  {r['label']}")
        else:
            print(mk, refresh(mk))


if __name__ == "__main__":
    main()
