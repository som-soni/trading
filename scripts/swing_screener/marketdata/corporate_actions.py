"""Corporate actions — the cash a holder receives that the stored prices show as a fall.

`prices` is unadjusted for dividends on purpose (stops and pivots must be levels someone can place an
order at; see `index_data`). So on an ex-date the stored close falls by the payout, and a backtest that
values a holding at the close books that fall as a loss the holder never had. For an ordinary dividend
the fall is a percent or two and both the strategy and its price-index benchmark leave it out. For a
special dividend or a demerger it is not: AURUM (ex-Majesco) paid out 98% of its price on 2020-12-23
and the stored close went 717.20 -> 8.88; a momentum book holding it booked -98% where a holder got the
cash back.

This module stores the actions and says which of them a backtest credits.

  corporate_actions   one row per action, per source:
      dividend    Yahoo, both markets. `value` = cash per share, on the split-adjusted scale `prices`
                  is stored on (Yahoo adjusts both the same way).
      split       Yahoo, both markets. `value` = new shares per old share (4.0 for a 4-for-1).
      demerger    NSE, India: an ex-date whose action is a demerger or scheme of arrangement. `value`
                  is empty -- NSE does not publish the spun-off value; `credits` measures it.
      bonus / face_split   NSE, India: `value` = shares after per share before, parsed from the
                  subject ("Bonus 1:1" -> 2.0). Used by `splits` to corroborate a gap the source
                  forgot to adjust, never credited.
  corporate_actions_fetched   per symbol, when Yahoo's actions were last read and over what period.

What a backtest credits (`credits`), on the first stored session on or after the ex-date:

  * a SPECIAL dividend: a dividend of at least SPECIAL_DIVIDEND_MIN_YIELD of the prior close, whose
    ex-date open is at least GAP_CONFIRM of the dividend below that close (so a dividend on a different
    price scale -- a split the stored history has not caught up with -- is never credited);
  * a demerger: prior close minus the ex-date open, when that is at least DEMERGER_MIN_GAP of the
    prior close. NSE discovers the parent's ex-date price in a special pre-open session; the difference
    is the market's value of what was spun off, which is how NSE's own indices carry a demerger.
    The holder is credited it as cash on the ex-date rather than holding the new shares, which list
    weeks later and are often not in `prices` at all.

Ordinary dividends are stored but never credited: a price index leaves them out too, so crediting
them to a strategy and not to its benchmark would flatter the excess return. Index providers treat a
demerger and a large special dividend as a capital adjustment, not a fall in the index, so crediting
those is what puts the strategy on the benchmark's footing.

US spin-offs have no free source here (Yahoo does not record them), so they are not credited; the
scan in `report` lists the large US one-day falls with nothing stored to explain them.

The loader honours `asof.end()`: inside a backtest stage nothing dated after its end is returned, and
the prices a credit is measured from are read up to the same boundary.

    PYTHONPATH=. python3 -m swing_screener.marketdata.corporate_actions --market india --refresh
    PYTHONPATH=. python3 -m swing_screener.marketdata.corporate_actions --market india --report
"""

import argparse
import bisect
import datetime as dt
import logging
import re
import time

import pandas as pd

from ..config import MARKETS
from . import asof, db

logger = logging.getLogger("corporate_actions")

SPECIAL_DIVIDEND_MIN_YIELD = 0.05   # a dividend this share of the prior close or more is credited
GAP_CONFIRM = 0.5                   # ... if the ex-date open is at least this share of it below the close
DEMERGER_MIN_GAP = 0.05             # a demerger is credited when the ex-date open is this far below the close
YAHOO_BATCH = 50                    # symbols per Yahoo download
YAHOO_PAUSE = 1.0                   # seconds between batches
RECENT_PERIOD = "1y"                # what a routine refresh re-reads per symbol (a full read is "max")
NSE_FIRST = dt.date(2005, 1, 1)     # India's stored prices start in 2005
NSE_WINDOW_DAYS = 90                # NSE's corporate-actions API, queried a quarter at a time
NSE_RECENT_DAYS = 400               # what a routine refresh re-reads from NSE

# What every strategy page says about it -- built from the constants above, so a threshold change
# cannot leave stale text behind. One text per way a runner holds a position.
_WHAT = (f"a special dividend (a dividend of at least {SPECIAL_DIVIDEND_MIN_YIELD:.0%} of the prior close) or a "
         f"demerger (valued at the prior close less the ex-date open, when that is at least "
         f"{DEMERGER_MIN_GAP:.0%})")
_REST = ("Ordinary dividends stay out of both the strategy and its price-index benchmark, which leaves "
         "them out too. US spin-offs have no free source and are not credited; none was found among the "
         "large one-day falls the optimise-stage runs held.")
CAVEAT_HELD = (f"**Special dividends and demergers are credited.** On the ex-date of {_WHAT}, a held "
               f"position receives the cash, where the stored close only falls by it (AURUM's 98% special "
               f"dividend on 2020-12-23 was once booked as a -98% loss). Every signal -- the momentum "
               f"ranking, volatility weights and the 200-day trend test -- reads the closes back-adjusted "
               f"for the same actions, so a demerged parent keeps its rank instead of reading as a crash "
               f"for a year; fills, valuation, the price floor and turnover read the traded prices. "
               f"{_REST}")
CAVEAT_TRADED = (f"**Special dividends and demergers are credited as a return of capital.** On the ex-date of "
                 f"{_WHAT}, a held position receives the cash, and its entry, stop, target and every other "
                 f"level it carries move down by the payout per share, so the payout alone never hits the "
                 f"stop, and pnl and R include the cash. Brokers do not move a resting stop for a dividend; "
                 f"this models a trader re-placing it. An order still resting in that stock is cancelled. "
                 f"The indicators the rules read (the moving averages, the 52-week high and low, RS) are "
                 f"still computed on traded prices, so for a year after a large payout the stock can fail a "
                 f"trend test it would pass on total return -- measured on the optimise stage, 1.4% of India's "
                 f"and 0.9% of the US's trades entered within a year after a credited action, most of them "
                 f"after a 5-10% dividend that barely moves those tests. {_REST}")
CAVEAT_SHORT = (f"**A short pays special dividends and demergers.** On the ex-date of {_WHAT}, a short "
                f"position pays the cash (it owes the lender what a holder receives), and its stop moves down "
                f"by the payout. The stage, the lines and the signals are computed on prices back-adjusted for "
                f"the same actions, so a demerger is not read as a Stage 4 breakdown; each stop is then put "
                f"back on its own day's price scale. Ordinary dividends are the flat yield charged above.")

SCHEMA = """
CREATE TABLE IF NOT EXISTS corporate_actions (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    ex_date DATE NOT NULL,
    kind VARCHAR(16) NOT NULL,          -- dividend | split | demerger | bonus | face_split
    value DOUBLE PRECISION,             -- dividend: cash per share; split/bonus: shares after per share before
    source VARCHAR(16) NOT NULL,        -- yahoo | nse
    detail TEXT,                        -- the source's own description
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol, ex_date, kind, source)
);
CREATE INDEX IF NOT EXISTS corporate_actions_by_date ON corporate_actions (market, ex_date);
CREATE TABLE IF NOT EXISTS corporate_actions_fetched (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,        -- a symbol, or '*nse' for NSE's whole-market feed
    fetched_at TIMESTAMPTZ NOT NULL,
    period VARCHAR(8) NOT NULL,         -- max | 1y ...
    PRIMARY KEY (market, symbol)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


# ------------------------------------------------------------------ fetch: Yahoo

def _yahoo_rows(market: str, symbols: list[str], period: str) -> tuple[list[tuple], set[str]]:
    """Dividends and splits for `symbols`, as table rows; and the symbols Yahoo answered for."""
    import yfinance as yf
    rows, answered = [], set()
    got = yf.download(symbols, period=period, actions=True, auto_adjust=False, threads=True,
                      progress=False, group_by="ticker")
    if got is None or got.empty:
        return rows, answered
    for sym in symbols:
        try:
            df = got[sym] if isinstance(got.columns, pd.MultiIndex) else got
        except KeyError:
            continue
        if df is None or df["Close"].dropna().empty:
            continue
        answered.add(sym)
        for col, kind in (("Dividends", "dividend"), ("Stock Splits", "split")):
            if col not in df.columns:
                continue
            s = df[col].dropna()
            for ts, v in s[s > 0].items():
                rows.append((market, sym, pd.Timestamp(ts).date(), kind, float(v), "yahoo", None))
    return rows, answered


def refresh_yahoo(market: str, symbols: list[str], full: bool = False, progress=None) -> dict:
    """Read Yahoo's dividends and splits: the whole history for a symbol never read in full (or with
    `full`), the last year otherwise."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol FROM corporate_actions_fetched WHERE market=%s AND period='max'", (market,))
        done_max = {s for (s,) in cur.fetchall()}
    groups = {"max": [s for s in symbols if full or s not in done_max]}
    groups[RECENT_PERIOD] = [s for s in symbols if s not in set(groups["max"])]
    n_rows = n_ok = 0
    total = sum(len(v) for v in groups.values())
    seen = 0
    for period, syms in groups.items():
        for i in range(0, len(syms), YAHOO_BATCH):
            chunk = syms[i: i + YAHOO_BATCH]
            try:
                rows, answered = _yahoo_rows(market, chunk, period)
            except Exception as e:  # noqa: BLE001 -- one bad batch must not stop the rest
                logger.warning("%s: Yahoo batch from %s failed: %s", market, chunk[0], e)
                rows, answered = [], set()
            if rows:
                db.execute_values(
                    "INSERT INTO corporate_actions (market, symbol, ex_date, kind, value, source, detail) VALUES %s "
                    "ON CONFLICT (market, symbol, ex_date, kind, source) DO UPDATE SET value=EXCLUDED.value, fetched_at=now()",
                    rows)
            if answered:
                db.execute_values(
                    "INSERT INTO corporate_actions_fetched (market, symbol, fetched_at, period) VALUES %s "
                    "ON CONFLICT (market, symbol) DO UPDATE SET fetched_at=EXCLUDED.fetched_at, "
                    "period=CASE WHEN corporate_actions_fetched.period='max' THEN 'max' ELSE EXCLUDED.period END",
                    [(market, s, dt.datetime.now(dt.timezone.utc), period) for s in sorted(answered)])
            n_rows += len(rows)
            n_ok += len(answered)
            seen += len(chunk)
            if progress:
                progress(f"Yahoo actions {seen:,}/{total:,} symbols", done=seen, total=total)
            time.sleep(YAHOO_PAUSE)
    return {"symbols": total, "answered": n_ok, "rows": n_rows, "full": len(groups["max"])}


# ------------------------------------------------------------------ fetch: NSE (India)

_DEMERGER = re.compile(r"demerger|de-merger|scheme of arrangement|spin[- ]?off", re.I)
_BONUS = re.compile(r"bonus\s*(?:issue)?\s*[-:]?\s*(\d+)\s*:\s*(\d+)", re.I)
_FACE = re.compile(r"(?:split|sub-?division).*?(?:rs\.?|re\.?|inr)\s*([\d.]+).*?(?:to|-)\s*(?:rs\.?|re\.?|inr)\s*([\d.]+)", re.I)


def classify_nse(subject: str) -> list[tuple[str, float | None]]:
    """(kind, value) for the actions an NSE corporate-action subject names that this store keeps."""
    out = []
    if _DEMERGER.search(subject):
        out.append(("demerger", None))
    m = _BONUS.search(subject)
    if m and int(m.group(2)):
        a, b = int(m.group(1)), int(m.group(2))   # a new shares for every b held
        out.append(("bonus", (a + b) / b))
    m = _FACE.search(subject)
    if m:
        try:
            old, new = float(m.group(1)), float(m.group(2))
        except ValueError:
            old = new = 0.0
        if old > 0 and new > 0 and old != new:
            out.append(("face_split", old / new))
    return out


def _nse_day(s: str | None) -> dt.date | None:
    try:
        return dt.datetime.strptime((s or "").strip(), "%d-%b-%Y").date()
    except ValueError:
        return None


def refresh_nse(full: bool = False, progress=None) -> dict:
    """India: NSE's whole-market corporate-action feed, a quarter at a time — every window since
    NSE_FIRST on a full read, the last NSE_RECENT_DAYS (and the announced ones ahead) otherwise."""
    from . import financials as fin
    init_schema()
    market = "india"
    suffix = MARKETS[market].symbol_suffix
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT 1 FROM corporate_actions_fetched WHERE market=%s AND symbol='*nse' AND period='max'", (market,))
        have_full = cur.fetchone() is not None
    today = dt.date.today()
    first = NSE_FIRST if (full or not have_full) else today - dt.timedelta(days=NSE_RECENT_DAYS)
    last = today + dt.timedelta(days=60)
    windows, d = [], first
    while d <= last:
        e = min(d + dt.timedelta(days=NSE_WINDOW_DAYS - 1), last)
        windows.append((d, e))
        d = e + dt.timedelta(days=1)
    rows, failed = {}, 0
    for i, (a, b) in enumerate(windows):
        try:
            data = fin._nse.get(fin.NSE + "/api/corporates-corporateActions", index="equities",
                                from_date=a.strftime("%d-%m-%Y"), to_date=b.strftime("%d-%m-%Y")).json()
        except Exception as e:  # noqa: BLE001
            logger.warning("NSE corporate actions %s..%s failed: %s", a, b, e)
            failed += 1
            continue
        for x in data if isinstance(data, list) else data.get("data", []):
            day, subj, sym = _nse_day(x.get("exDate")), " ".join((x.get("subject") or "").split()), x.get("symbol")
            if day is None or not subj or not sym or (x.get("series") or "EQ") not in ("EQ", "BE", "BZ", "SM", "ST"):
                continue
            for kind, value in classify_nse(subj):
                rows[(sym + suffix, day, kind)] = (market, sym + suffix, day, kind, value, "nse", subj[:300])
        if progress:
            progress(f"NSE corporate actions {i + 1}/{len(windows)} quarters", done=i + 1, total=len(windows))
    if rows:
        db.execute_values(
            "INSERT INTO corporate_actions (market, symbol, ex_date, kind, value, source, detail) VALUES %s "
            "ON CONFLICT (market, symbol, ex_date, kind, source) DO UPDATE SET value=EXCLUDED.value, "
            "detail=EXCLUDED.detail, fetched_at=now()", list(rows.values()))
    if not failed:
        db.execute_values(
            "INSERT INTO corporate_actions_fetched (market, symbol, fetched_at, period) VALUES %s "
            "ON CONFLICT (market, symbol) DO UPDATE SET fetched_at=EXCLUDED.fetched_at, "
            "period=CASE WHEN corporate_actions_fetched.period='max' THEN 'max' ELSE EXCLUDED.period END",
            [(market, "*nse", dt.datetime.now(dt.timezone.utc), "max" if first == NSE_FIRST else "recent")])
    kinds = {}
    for r in rows.values():
        kinds[r[3]] = kinds.get(r[3], 0) + 1
    return {"windows": len(windows), "failed": failed, "rows": len(rows), "kinds": kinds}


def refresh(market: str, full: bool = False, progress=None) -> dict:
    """Every source for the market: Yahoo for every symbol with stored prices, and NSE for India."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT DISTINCT symbol FROM prices WHERE market=%s", (market,))
        symbols = sorted(s for (s,) in cur.fetchall() if not s.startswith("^"))
    out = {"yahoo": refresh_yahoo(market, symbols, full=full, progress=progress)}
    if market == "india":
        out["nse"] = refresh_nse(full=full, progress=progress)
    return out


# ------------------------------------------------------------------ load

def load(market: str, symbols=None, kinds=None) -> pd.DataFrame:
    """Stored actions (symbol, ex_date, kind, value, source, detail), none dated after `asof.end()`."""
    init_schema()
    sql = "SELECT symbol, ex_date, kind, value, source, detail FROM corporate_actions WHERE market=%s"
    params: list = [market]
    if symbols is not None:
        sql += " AND symbol = ANY(%s)"
        params.append(list(symbols))
    if kinds is not None:
        sql += " AND kind = ANY(%s)"
        params.append(list(kinds))
    if asof.end_date() is not None:
        sql += " AND ex_date <= %s"
        params.append(asof.end_date())
    with db.get_connection().cursor() as cur:
        cur.execute(sql + " ORDER BY ex_date, symbol", params)
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["symbol", "ex_date", "kind", "value", "source", "detail"])
    df["ex_date"] = pd.to_datetime(df["ex_date"])
    return df


def _bars_around(market: str, pairs: list[tuple[str, dt.date]]) -> dict:
    """{(symbol, ex_date): (session, prev_close, open)}: the first stored session on or after each
    ex-date, the close before it and its open -- read no later than `asof.end()`."""
    if not pairs:
        return {}
    end = asof.end_date()
    out = {}
    with db.get_connection().cursor() as cur:
        cur.execute(f"""
            WITH ev(symbol, ex_date) AS (SELECT * FROM unnest(%s::text[], %s::date[]))
            SELECT ev.symbol, ev.ex_date, nx.date, nx.open, pv.close
            FROM ev
            CROSS JOIN LATERAL (SELECT date, open FROM prices p WHERE p.market=%s AND p.symbol=ev.symbol
                                AND p.date >= ev.ex_date {"AND p.date <= %s" if end else ""}
                                ORDER BY date LIMIT 1) nx
            CROSS JOIN LATERAL (SELECT close FROM prices p WHERE p.market=%s AND p.symbol=ev.symbol
                                AND p.date < nx.date ORDER BY date DESC LIMIT 1) pv""",
                    [[p[0] for p in pairs], [p[1] for p in pairs], market] + ([end] if end else []) + [market])
        for sym, ex, day, o, prev in cur.fetchall():
            out[(sym, ex)] = (day, prev, o)
    return out


def credits(market: str, symbols=None) -> pd.DataFrame:
    """The cash per share a holder is credited, one row per creditable action:
    symbol, date (the stored session it lands on), kind (special_dividend | demerger), cash,
    prev_close, open, pct (cash / prev_close), detail. See the module docstring for the rules."""
    acts = load(market, symbols, kinds=("dividend", "demerger"))
    cols = ["symbol", "date", "kind", "cash", "prev_close", "open", "pct", "detail"]
    if acts.empty:
        return pd.DataFrame(columns=cols)
    # a demerger is often recorded twice (NSE "Demerger" and "Scheme of Arrangement" the same day): one key
    acts = acts.drop_duplicates(["symbol", "ex_date", "kind"])
    bars = _bars_around(market, [(r.symbol, r.ex_date.date()) for r in acts.itertuples()])
    out = []
    for r in acts.itertuples():
        b = bars.get((r.symbol, r.ex_date.date()))
        if b is None:
            continue
        day, prev, o = b
        if not prev or prev <= 0 or o is None or o != o or o <= 0:
            continue
        gap = prev - o
        if r.kind == "dividend":
            cash = float(r.value or 0.0)
            if not (SPECIAL_DIVIDEND_MIN_YIELD * prev <= cash < prev) or gap < GAP_CONFIRM * cash:
                continue
            kind = "special_dividend"
        else:
            if gap < DEMERGER_MIN_GAP * prev:
                continue
            cash, kind = gap, "demerger"
        out.append({"symbol": r.symbol, "date": pd.Timestamp(day), "kind": kind, "cash": cash,
                    "prev_close": float(prev), "open": float(o), "pct": cash / float(prev),
                    "detail": r.detail if isinstance(r.detail, str) else f"{r.source} {r.kind} {r.value or 0:g}"})
    df = pd.DataFrame(out, columns=cols)
    # one credit per symbol and session: a special dividend paid on a demerger's ex-date is inside its gap
    return df.sort_values(["date", "symbol", "kind"]).drop_duplicates(["symbol", "date"], keep="first").reset_index(drop=True)


def back_adjust(px: pd.DataFrame, cr: pd.DataFrame | None) -> pd.DataFrame:
    """`px` (dates x symbols, raw closes) back-adjusted for the credited actions `cr` (`credits`):
    every close before an ex-date is multiplied by (prior close - cash) / prior close, so the series
    shows the holder's total return instead of a fall on the ex-date.

    Use it ONLY for scale-free signals -- returns, volatility, a close against its own moving average,
    a relative-strength ratio. An action dated after t scales every bar up to t by the same factor, so
    a ratio read at t cannot see it: no look-ahead. An absolute level read at t (a stop, an ATR, a
    turnover floor, a price floor) is scaled by those future actions and would leak them; take levels
    from the raw prices, or put an adjusted level back on t's scale with `pit_scale`."""
    out = px.copy()
    if cr is None or not len(cr):
        return out
    for r in cr.itertuples():
        if r.symbol not in out.columns or not r.prev_close:
            continue
        f = (float(r.prev_close) - float(r.cash)) / float(r.prev_close)
        if f > 0:
            col = out.columns.get_loc(r.symbol)
            mask = out.index < r.date
            out.iloc[mask, col] = out.iloc[mask, col] * f
    return out


def back_adjust_ohlc(df: pd.DataFrame, cr: pd.DataFrame | None) -> pd.DataFrame:
    """One symbol's OHLC frame back-adjusted the same way (`cr` already filtered to that symbol). Volume
    is left as traded. Same caveat as `back_adjust`: levels read from it carry future actions."""
    out = df.copy()
    if cr is None or not len(cr):
        return out
    cols = [c for c in ("open", "high", "low", "close") if c in out.columns]
    for r in cr.itertuples():
        if not r.prev_close:
            continue
        f = (float(r.prev_close) - float(r.cash)) / float(r.prev_close)
        if f > 0:
            out.loc[out.index < r.date, cols] = out.loc[out.index < r.date, cols] * f
    return out


def pit_scale(raw_close: pd.Series, adj_close: pd.Series) -> pd.Series:
    """Per bar, raw / adjusted close: multiply a level computed on the adjusted series AT bar t by this
    bar-t value and it is on the scale of t's own price -- adjusted for every action up to t and for
    none after it, i.e. point in time."""
    return (raw_close / adj_close).where(adj_close > 0)


class Credits:
    """The credits a backtest walks through, by session: `between(after, upto)` -> [(symbol, cash, kind)]
    for every credit dated after `after` and up to `upto`, so a session the runner dropped or a symbol
    that did not print that day still gets its credit on the next one it marks."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.sort_values("date").reset_index(drop=True) if df is not None and len(df) else \
            pd.DataFrame(columns=["symbol", "date", "kind", "cash"])
        self._dates = list(self.df["date"])

    @classmethod
    def for_market(cls, market: str, symbols=None) -> "Credits":
        return cls(credits(market, symbols))

    def __len__(self) -> int:
        return len(self.df)

    def between(self, after, upto) -> list[tuple[str, float, str]]:
        lo = 0 if after is None else bisect.bisect_right(self._dates, pd.Timestamp(after))
        hi = bisect.bisect_right(self._dates, pd.Timestamp(upto))
        return [(self.df.at[i, "symbol"], float(self.df.at[i, "cash"]), self.df.at[i, "kind"]) for i in range(lo, hi)]

    def on(self, upto, after, held) -> dict[str, float]:
        """{symbol: cash per share} for the symbols in `held` credited in (after, upto]."""
        out: dict[str, float] = {}
        for sym, cash, _kind in self.between(after, upto):
            if sym in held:
                out[sym] = out.get(sym, 0.0) + cash
        return out

    def note(self) -> str:
        """One caveat line for a run's report."""
        k = self.df["kind"].value_counts().to_dict() if len(self.df) else {}
        return (f"Corporate actions: a held position is credited the cash of a special dividend (at least "
                f"{SPECIAL_DIVIDEND_MIN_YIELD:.0%} of the prior close) or a demerger's value (prior close less the "
                f"ex-date open) on the ex-date -- {k.get('special_dividend', 0)} special dividends and "
                f"{k.get('demerger', 0)} demergers in this market's data. Ordinary dividends stay out of both the "
                f"strategy and the benchmark.")


# ------------------------------------------------------------------ report

def unexplained_drops(market: str, min_drop: float = 0.4, min_turnover: float | None = None) -> pd.DataFrame:
    """One-day falls of at least `min_drop` on liquid stocks, with what (if anything) is stored to explain
    them: a credited action, a stored action that is not credited, or nothing (a real move, a spin-off
    with no source, or bad data)."""
    floor = min_turnover if min_turnover is not None else (1e8 if market == "india" else 1e7)
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT symbol, date, prev, open, close FROM (
                           SELECT symbol, date, open, close, dollar_vol_sma20,
                                  lag(close) OVER (PARTITION BY symbol ORDER BY date) AS prev,
                                  lag(dollar_vol_sma20) OVER (PARTITION BY symbol ORDER BY date) AS dv
                           FROM prices WHERE market=%s) x
                       WHERE prev > 0 AND close / prev <= %s AND dv > %s""", (market, 1 - min_drop, floor))
        drops = pd.DataFrame(cur.fetchall(), columns=["symbol", "date", "prev_close", "open", "close"])
    if drops.empty:
        return drops
    drops["date"] = pd.to_datetime(drops["date"])
    cr = credits(market, sorted(set(drops["symbol"])))
    crk = {(r.symbol, r.date): r.kind for r in cr.itertuples()}
    acts = load(market, sorted(set(drops["symbol"])))
    near = {}
    for r in acts.itertuples():
        near.setdefault(r.symbol, []).append(r)
    expl = []
    for r in drops.itertuples():
        if (r.symbol, r.date) in crk:
            expl.append(crk[(r.symbol, r.date)])
            continue
        hit = [a for a in near.get(r.symbol, []) if abs((a.ex_date - r.date).days) <= 5 and a.kind != "dividend"
               or (a.kind == "dividend" and abs((a.ex_date - r.date).days) <= 5 and (a.value or 0) >= 0.2 * r.prev_close)]
        expl.append("stored: " + ",".join(sorted({a.kind for a in hit})) if hit else "")
    drops["explained_by"] = expl
    return drops.sort_values("date").reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=sorted(MARKETS))
    ap.add_argument("--refresh", action="store_true", help="read the sources")
    ap.add_argument("--full", action="store_true", help="with --refresh: every symbol's whole history")
    ap.add_argument("--report", action="store_true", help="credited actions and large unexplained falls")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if a.refresh:
        print(refresh(a.market, full=a.full))
    if a.report:
        pd.set_option("display.width", 220)
        c = credits(a.market)
        print(c.groupby("kind").size().to_string() if len(c) else "no credits")
        print(c.tail(40).to_string(index=False))
        d = unexplained_drops(a.market)
        print(f"\n{len(d)} one-day falls of 40%+ on liquid stocks; by explanation:")
        print(d["explained_by"].replace("", "(nothing stored)").value_counts().to_string())


if __name__ == "__main__":
    main()
