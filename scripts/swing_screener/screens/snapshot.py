"""The daily stock snapshot: ~50 fields per stock per session — what every screen filters on.

Any screen is a set of conditions over these fields (screens/definitions.py), evaluated instantly by a
query over the snapshot. The fields that need history or the whole market — RS rank, weekly trend,
higher swing lows, "holding the 50-day" — are computed here once, so a screen never has to.

Stored as one Parquet file per market per session under data/snapshots/<market>/<date>.parquet:
the last KEEP_DAILY sessions, plus every month's last session for good (the history the screen study
reads). `backfill` builds the month-end history.

    PYTHONPATH=. python3 -m swing_screener.screens.snapshot --market us                 # today's snapshot
    PYTHONPATH=. python3 -m swing_screener.screens.snapshot --market india --backfill 5  # 5 years of month-ends

Fields that only describe the present (sector and industry classification, quality score, days to
earnings, group RS) are filled for the latest session only; history snapshots leave them empty rather
than leak today's knowledge into the past.
"""

import argparse
import logging
import time
from types import SimpleNamespace

import numpy as np
import pandas as pd

from .. import paths
from ..config import MARKETS
from ..core import indicators as ind
from ..marketdata import cache, db, freshness
from . import criteria as crit
from .base import MIN_BARS, Screen

logger = logging.getLogger(__name__)
SNAP_DIR = paths.DATA_DIR / "snapshots"
KEEP_DAILY = 40                 # daily snapshots kept; month-end ones are kept for good
MIN_SNAPSHOT_BARS = 60          # a stock needs this much history to appear at all (longer-window fields are empty until it has it)
LOOKBACK_DAYS = 480
PEER_MIN = 3                    # a sub-industry is a stock's peer group only with this many tradable stocks (else its industry group)

# The field catalog: key, label, group, kind (price | pct | num | money | bool | text), description.
# pct fields are percentages (12.5 means 12.5%).
FIELDS = [
    ("close", "Close", "Price", "price", "The session's closing price."),
    ("r1w", "Return 1W", "Performance", "pct", "Return over the last 5 sessions."),
    ("r1m", "Return 1M", "Performance", "pct", "Return over the last 21 sessions."),
    ("r3m", "Return 3M", "Performance", "pct", "Return over the last 63 sessions."),
    ("r6m", "Return 6M", "Performance", "pct", "Return over the last 126 sessions."),
    ("r12m", "Return 12M", "Performance", "pct", "Return over the last 252 sessions."),
    ("mom_12_1", "Momentum 12-1M", "Performance", "pct", "Return from a year ago to a month ago (skips the latest month)."),
    ("rs_rank", "RS rank", "Performance", "num", "Relative strength 1–99 across every stock with a year of history "
                                                 "(2 × 3-month + 6 + 9 + 12-month return, ranked)."),
    ("sma20", "SMA 20", "Moving averages", "price", "20-day simple moving average."),
    ("sma50", "SMA 50", "Moving averages", "price", "50-day simple moving average."),
    ("sma150", "SMA 150", "Moving averages", "price", "150-day simple moving average."),
    ("sma200", "SMA 200", "Moving averages", "price", "200-day simple moving average."),
    ("ema20", "EMA 20", "Moving averages", "price", "20-day exponential moving average."),
    ("sma200_21d_ago", "SMA 200, a month ago", "Moving averages", "price", "The 200-day average 21 sessions ago (compare with SMA 200 for its trend)."),
    ("pct_vs_sma20", "% vs SMA 20", "Moving averages", "pct", "How far the close is above (+) or below (−) the 20-day average."),
    ("pct_vs_sma50", "% vs SMA 50", "Moving averages", "pct", "How far the close is above or below the 50-day average."),
    ("pct_vs_sma200", "% vs SMA 200", "Moving averages", "pct", "How far the close is above or below the 200-day average."),
    ("high_252", "52-week high", "Range", "price", "Highest high of the last 252 sessions."),
    ("low_252", "52-week low", "Range", "price", "Lowest low of the last 252 sessions."),
    ("pct_below_high", "% below 52-week high", "Range", "pct", "How far the close is below the 52-week high (0 = at the high)."),
    ("pct_above_low", "% above 52-week low", "Range", "pct", "How far the close is above the 52-week low."),
    ("atr_pct", "ATR %", "Volatility", "pct", "Average true range (14 days) as a % of the close."),
    ("adx14", "ADX 14", "Volatility", "num", "Trend strength (0–100); above ~25 is a strong trend."),
    ("rsi14", "RSI 14", "Momentum", "num", "Relative strength index (0–100)."),
    ("volume", "Volume", "Volume", "num", "The session's volume."),
    ("rvol", "Relative volume", "Volume", "num", "The session's volume ÷ its 50-day average."),
    ("value20", "Avg traded value (20d)", "Volume", "money", "20-day average of close × volume, in the market's currency."),
    ("bars", "Days of history", "Data", "num", "Sessions of price history stored."),
    ("tradable", "Tradable", "Trend & structure", "bool", "Clears the market's floor: minimum price and 20-day traded value, a year of history, "
                                                          "a valid ATR — the floor the built-in screens and the strategies use."),
    ("weekly_uptrend", "Weekly uptrend", "Trend & structure", "bool", "Weekly close above a rising 30-week EMA."),
    ("weekly_ma_aligned", "Weekly averages aligned", "Trend & structure", "bool", "Weekly 20-week average above the 50-week."),
    ("holding_50d", "Holding the 50-day", "Trend & structure", "bool", "50-day above the 200-day, and price has not broken down through the 50-day "
                                                                       "(more than 2 ATR below it, or 5 closes in a row under it)."),
    ("mas_not_falling", "Averages not falling", "Trend & structure", "bool", "Neither the 50-day nor the 200-day is falling."),
    ("sma200_not_falling", "200-day not falling", "Trend & structure", "bool", "The 200-day is not more than 0.5% below its value 20 sessions ago."),
    ("higher_swing_lows", "Higher swing lows", "Trend & structure", "bool", "The last two confirmed swing lows (last ~50 sessions) are rising."),
    ("momentum_positive", "12-1M momentum positive", "Trend & structure", "bool", "The close a month ago is above the close a year ago."),
    ("trend_not_fading", "Trend not fading", "Trend & structure", "bool", "Not both a negative 3-month return and a flat or falling 50-day."),
    ("sector", "Sector", "Classification", "text", "Yahoo sector."),
    ("industry", "Industry group", "Classification", "text", "Yahoo industry group."),
    ("sub_industry", "Sub-industry", "Classification", "text", "The sub-industry, where the industry group mixes businesses (Library → Sub-industries)."),
    ("group_rs", "Group RS rating", "Classification", "num", "RS rating (1–99) of the stock's industry group, from the Sectors page."),
    ("peer_group", "Peer group", "Classification", "text", "Who the stock is compared with: its sub-industry where the group is split and the sub-industry has 3+ tradable stocks, else its industry group."),
    ("peer_rs", "Peer group RS", "Classification", "num", "RS rating (1–99) of the peer group — the sub-industry, else the industry group — from the Sectors page."),
    ("peer_rank", "Rank in peer group", "Classification", "num", "The stock's place among the tradable stocks of its peer group by RS rank (1 = the strongest)."),
    ("peer_count", "Stocks in peer group", "Classification", "num", "Tradable stocks in the peer group."),
    ("market_cap", "Market cap (local currency)", "Fundamentals", "money", "Market capitalisation in the market's own currency (from the industry classification, refreshed monthly)."),
    ("market_cap_usd", "Market cap ($B)", "Fundamentals", "num", "Market capitalisation in US$ billions — converted at the session's USD rate (USDINR for India), so markets compare directly."),
    ("quality", "Quality score", "Fundamentals", "num", "Quality score 0–100 from the Quality page, where scored."),
    ("earnings_days", "Days to earnings", "Fundamentals", "num", "Calendar days to the next known earnings date."),
]
FIELD_KEYS = [f[0] for f in FIELDS]
PRESENT_ONLY = ("sector", "industry", "sub_industry", "group_rs", "peer_group", "peer_rs", "peer_rank", "peer_count",
                "market_cap", "market_cap_usd", "quality", "earnings_days")


def _path(market: str, d) -> "pd.Path":
    return SNAP_DIR / market / f"{pd.Timestamp(d).date().isoformat()}.parquet"


def dates(market: str) -> list:
    d = SNAP_DIR / market
    return sorted(pd.Timestamp(p.stem).date() for p in d.glob("*.parquet")) if d.exists() else []


def load(market: str, d=None) -> pd.DataFrame:
    ds = dates(market)
    if not ds:
        return pd.DataFrame()
    d = pd.Timestamp(d).date() if d else ds[-1]
    df = pd.read_parquet(_path(market, d))
    for k in FIELD_KEYS:          # a snapshot saved before a field existed: the field is empty, not missing
        if k not in df.columns:
            df[k] = None
    df.attrs["date"] = d
    if "market_cap" in df.columns and ("market_cap_usd" not in df.columns or df["market_cap_usd"].isna().all()):
        _add_usd_cap(market, df, d)        # snapshots saved before the field existed
    return df


def usd_rate(market: str, d) -> float | None:
    """Local currency per US$1 on (or before) day d — 1.0 for a market priced in dollars, None if unknown."""
    series = getattr(MARKETS[market], "fx_to_usd", None)
    if series is None:          # a config without the setting (a long-running process from before it existed)
        return None
    if not series:
        return 1.0
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT close FROM index_series WHERE market=%s AND series=%s AND date <= %s ORDER BY date DESC LIMIT 1",
                    (market, series, pd.Timestamp(d).date()))
        r = cur.fetchone()
    return float(r[0]) if r and r[0] else None


def _add_usd_cap(market: str, df: pd.DataFrame, d) -> None:
    fx = usd_rate(market, d)
    df["market_cap_usd"] = (df["market_cap"].astype(float) / fx / 1e9).round(3) if fx else np.nan


def _rs_raw(close: pd.Series, i: int) -> float | None:
    def ret(n):
        if i - n < 0 or not close.iloc[i - n]:
            return None
        return float(close.iloc[i] / close.iloc[i - n] - 1)
    q1, q2, q3, q4 = ret(63), ret(126), ret(189), ret(252)
    if q1 is None or q4 is None:
        return None
    return 2 * q1 + (q2 if q2 is not None else q4) + (q3 if q3 is not None else q4) + q4


def _row(cfg, sym: str, raw: pd.DataFrame, enriched: pd.DataFrame, i: int) -> dict:
    """Every price-derived field of one stock as of bar i (point in time: only bars up to i are read)."""
    row = enriched.iloc[i]
    close = float(row["close"])
    c = enriched["close"]
    ret = lambda n: (float(close / c.iloc[i - n] - 1) * 100) if i - n >= 0 and c.iloc[i - n] else None
    num = lambda k: (float(row[k]) if pd.notna(row.get(k)) else None)
    hi, lo = num("high_252"), num("low_252")
    out = {"symbol": sym, "close": close, "r1w": ret(5), "r1m": ret(21), "r3m": ret(63), "r6m": ret(126), "r12m": ret(252),
           "mom_12_1": (num("mom_12_1") * 100 if num("mom_12_1") is not None else None), "rs_raw": _rs_raw(c, i),
           **{k: num(k) for k in ("sma20", "sma50", "sma150", "sma200", "ema20", "sma200_21d_ago", "atr_pct", "adx14", "rsi14", "high_252", "low_252")},
           "volume": num("volume"), "rvol": (float(row["volume"] / row["vol_sma50"]) if num("vol_sma50") else None),
           "value20": num("dollar_vol_sma20"), "bars": i + 1}
    for k, sma in (("pct_vs_sma20", "sma20"), ("pct_vs_sma50", "sma50"), ("pct_vs_sma200", "sma200")):
        out[k] = (close / out[sma] - 1) * 100 if out[sma] else None
    # the same formulas as the Stage 2 criteria (screens/criteria.py), so a condition on them is exact
    out["pct_below_high"] = (1 - close / hi) * 100 if hi and hi > 0 else None
    out["pct_above_low"] = (close / lo - 1) * 100 if lo and lo > 0 else None
    # structure flags: the criteria functions themselves, on the history up to bar i
    ctx = SimpleNamespace(daily=enriched.iloc[: i + 1], weekly=ind.enrich_weekly(ind.resample_weekly(raw.iloc[: i + 1])),
                          last=row, close=close, extras={})
    for k, fn in (("weekly_uptrend", crit.weekly_above_rising_ema30), ("weekly_ma_aligned", crit.weekly_sma20_above_sma50),
                  ("holding_50d", crit.daily_structure), ("mas_not_falling", crit.averages_not_falling),
                  ("sma200_not_falling", crit.sma200_not_falling), ("higher_swing_lows", crit.higher_swing_lows),
                  ("momentum_positive", crit.momentum_12_1_positive), ("trend_not_fading", crit.trend_not_fading)):
        out[k] = bool(fn(ctx)[0])
    out["tradable"] = bool(i + 1 >= MIN_BARS and Screen.tradable(cfg, row)[0])
    return out


def _finish(market: str, rows: list[dict], d, present: bool) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    v = df["rs_raw"].astype(float)
    n = v.notna().sum()
    df["rs_rank"] = (1 + 98 * (v.rank(pct=True) - 1 / n) / max(1e-9, 1 - 1 / n)).round() if n > 1 else np.nan
    df = df.drop(columns="rs_raw")
    for k in PRESENT_ONLY:
        df[k] = None
    if present:
        _add_present(market, df, d)
    return df[["symbol", *FIELD_KEYS]]


def _add_present(market: str, df: pd.DataFrame, d) -> None:
    """Fields that describe the present: classification, group RS, market cap, quality, days to earnings."""
    from ..marketdata import industries, subindustries
    ind_ = industries.load(market)
    sub = subindustries.load(market)
    df["sector"] = df["symbol"].map(lambda s: (ind_.get(s) or (None,))[0])
    df["industry"] = df["symbol"].map(lambda s: (ind_.get(s) or (None, None))[1])
    df["market_cap"] = df["symbol"].map(lambda s: (ind_.get(s) or (None, None, None))[2])
    _add_usd_cap(market, df, d)
    df["sub_industry"] = df["symbol"].map(lambda s: sub[s][1] if s in sub and sub[s][1] != "other" else None)
    with db.get_connection().cursor() as cur:
        try:
            cur.execute("""SELECT grp, rs FROM sector_daily WHERE market=%s AND level='industry'
                           AND date = (SELECT max(date) FROM sector_daily WHERE market=%s AND date <= %s)""", (market, market, d))
            grs = dict(cur.fetchall())
            cur.execute("""SELECT grp, rs FROM sector_daily WHERE market=%s AND level='sub'
                           AND date = (SELECT max(date) FROM sector_daily WHERE market=%s AND date <= %s)""", (market, market, d))
            subrs = dict(cur.fetchall())
        except Exception:  # noqa: BLE001
            grs, subrs = {}, {}
        try:
            cur.execute("SELECT DISTINCT ON (symbol) symbol, quality_score FROM quality_scores WHERE market=%s ORDER BY symbol, computed_at DESC", (market,))
            qual = dict(cur.fetchall())
        except Exception:  # noqa: BLE001
            qual = {}
    df["group_rs"] = df["industry"].map(grs)
    add_peers(df, grs, subrs)
    df["quality"] = df["symbol"].map(qual)
    from ..marketdata.earnings import earnings_cache_path
    p = earnings_cache_path(market)
    if p.exists():
        e = pd.read_csv(p, keep_default_na=False)
        nxt = {str(s): pd.to_datetime(x, errors="coerce") for s, x in zip(e["symbol"], e["next_earnings_date"])}
        day = pd.Timestamp(d)
        df["earnings_days"] = df["symbol"].map(lambda s: (nxt[s] - day).days if s in nxt and pd.notna(nxt[s]) and nxt[s] >= day else None)


def add_peers(df: pd.DataFrame, grs: dict, subrs: dict) -> None:
    """Peer group, its RS rating, and each tradable stock's place in it (leaders in leading groups).
    Needs industry, sub_industry, tradable and rs_rank; `grs` / `subrs`: industry group / sub-industry
    ("Industry › Sub") -> RS rating on the snapshot's date. Used by the daily snapshot and — with ratings
    rebuilt for past dates (analytics/group_history.py) — by the screen study.

    A sub-industry is the peer group only when it is big enough to compare within: PEER_MIN tradable
    stocks and an RS rating (the Sectors page rates groups of 3+); otherwise the industry group is."""
    sub_key = df["industry"].astype(str) + " › " + df["sub_industry"].astype(str)
    trad0 = df["tradable"].astype(bool)
    sub_n = sub_key[trad0 & df["sub_industry"].notna()].value_counts()
    use_sub = df["sub_industry"].notna() & sub_key.map(sub_n).fillna(0).ge(PEER_MIN) & sub_key.isin(subrs.keys())
    df["peer_group"] = np.where(use_sub, sub_key, df["industry"])
    df.loc[df["industry"].isna(), "peer_group"] = None
    df["peer_rs"] = [subrs.get(g) if us else grs.get(i) for g, i, us in zip(df["peer_group"], df["industry"], use_sub)]
    trad = trad0 & df["peer_group"].notna() & df["rs_rank"].notna()
    df["peer_rank"] = df[trad].groupby("peer_group")["rs_rank"].rank(ascending=False, method="min")
    df["peer_count"] = df["peer_group"].map(df[trad].groupby("peer_group").size())


def _save(market: str, df: pd.DataFrame, d) -> None:
    p = _path(market, d)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, index=False)


def _prune(market: str) -> None:
    """Keep the last KEEP_DAILY sessions and every month's last session."""
    ds = dates(market)
    month_end = {max(x for x in ds if (x.year, x.month) == ym) for ym in {(x.year, x.month) for x in ds}}
    for x in ds[:-KEEP_DAILY]:
        if x not in month_end:
            _path(market, x).unlink(missing_ok=True)


def _universe_bars(market: str, since) -> dict:
    from ..analytics.breadth import eligible
    with cache.offline():
        return cache.load_many_cached(market, eligible(market), since=since)


def build(market: str, d=None) -> pd.DataFrame:
    """Today's (or a given session's) snapshot, saved."""
    t0 = time.time()
    cfg = MARKETS[market]
    d = pd.Timestamp(d or freshness.sessions(market)[-1])
    bars = _universe_bars(market, d - pd.Timedelta(days=LOOKBACK_DAYS))
    rows = []
    for sym, raw in bars.items():
        raw = raw[raw.index <= d]
        if len(raw) < MIN_SNAPSHOT_BARS or raw.index[-1] != d:
            continue
        rows.append(_row(cfg, sym, raw, ind.enrich_daily(raw), len(raw) - 1))
    df = _finish(market, rows, d, present=True)
    _save(market, df, d)
    df.attrs["date"] = d.date()
    _prune(market)
    logger.info("snapshot %s %s: %d stocks, %d tradable, %.0fs", market, d.date(), len(df), int(df["tradable"].sum()), time.time() - t0)
    return df


def month_ends(market: str, years: float) -> list:
    days = freshness.sessions(market, since_days=int(years * 365 + 40))
    by = {}
    for x in days:
        by[(x.year, x.month)] = x
    return sorted(by.values())[:-1]          # the current month is not over yet


def backfill(market: str, years: float = 5, force: bool = False) -> int:
    """Month-end snapshots for the last `years` years (point in time; present-only fields left empty)."""
    t0 = time.time()
    cfg = MARKETS[market]
    have = set(dates(market))
    todo = [d for d in month_ends(market, years) if force or d not in have]
    if not todo:
        return 0
    bars = _universe_bars(market, pd.Timestamp(todo[0]) - pd.Timedelta(days=LOOKBACK_DAYS))
    per_date: dict = {d: [] for d in todo}
    for n, (sym, raw) in enumerate(bars.items(), 1):
        enriched = ind.enrich_daily(raw)
        idx = enriched.index
        for d in todo:
            t = pd.Timestamp(d)
            if t not in idx:
                continue
            i = idx.get_loc(t)
            if i + 1 < MIN_SNAPSHOT_BARS:
                continue
            per_date[d].append(_row(cfg, sym, raw, enriched, i))
        if n % 500 == 0:
            logger.info("  backfill %s: %d/%d symbols (%.0fs)", market, n, len(bars), time.time() - t0)
    for d, rows in per_date.items():
        _save(market, _finish(market, rows, d, present=False), d)
    logger.info("backfill %s: %d month-end snapshots in %.0fs", market, len(todo), time.time() - t0)
    return len(todo)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--backfill", type=float, default=None, help="build month-end snapshots for this many years")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if a.backfill:
        print(backfill(a.market, a.backfill, a.force))
    else:
        df = build(a.market)
        print(df.shape, int(df["tradable"].sum()))


if __name__ == "__main__":
    main()
