"""Total-return index series — the data layer for index-investing backtests.

Why a SEPARATE table from `prices`
----------------------------------
`prices` is deliberately unadjusted (`auto_adjust=False` in the provider):
the screener needs real traded prices because stops, pivots and measured
moves are levels someone actually has to place an order at, and a
back-adjusted series silently moves them.

Index investing is the opposite problem. Dividends are roughly 1.9%/yr on
the S&P 500 and 1.3%/yr on the Nifty — an order of magnitude larger than
any of the calendar effects being tested here. Worse, dropping them is not
a symmetric understatement: a strategy that sits in cash part of the time
forgoes less dividend income than buy-and-hold does, so excluding dividends
systematically flatters every market-timing rule. Any conclusion about
timing drawn from price-only data is an artefact.

So this module keeps a second, small store (~25k rows per series) fetched
with `auto_adjust=True`, and never writes to `prices`.

    python3 -m swing_screener.marketdata.index_data --list
    python3 -m swing_screener.marketdata.index_data --refresh
    python3 -m swing_screener.marketdata.index_data --calibrate-dividends
"""

import argparse
import logging
import warnings
from dataclasses import dataclass

import pandas as pd

from . import db

logger = logging.getLogger("index_data")

SCHEMA = """
CREATE TABLE IF NOT EXISTS index_series (
    market VARCHAR(16) NOT NULL,
    series VARCHAR(32) NOT NULL,
    date DATE NOT NULL,
    -- DIVIDEND-ADJUSTED for total_return series. This is why the table is
    -- separate from `prices`, which is deliberately unadjusted.
    close DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (market, series, date)
);
"""


@dataclass(frozen=True)
class Series:
    """One investable index proxy (or rate series).

    `total_return` says whether the fetched series already contains
    dividends. Where it does not, `div_yield` is added as a daily accrual
    and the run's caveats say so — an assumption, never silent.
    """

    key: str
    ticker: str
    market: str
    kind: str          # equity | bond | gold | cash | yield | fx
    total_return: bool
    label: str
    div_yield: float = 0.0      # annual, ADDED to price-only equity series
    expense_ratio: float = 0.0  # annual drag applied when held
    note: str = ""

    @property
    def synthetic_dividends(self) -> bool:
        return not self.total_return and self.div_yield > 0


# --- the registry ---------------------------------------------------------
#
# Coverage was verified by fetching each one (`--list` reprints it from the
# DB). Start dates are the binding constraint on every window below, so they
# are recorded here rather than rediscovered per experiment.

_US = [
    # Vanguard's 500 index FUND, not an index: 46 years of true total return,
    # the longest clean US series available without paying for data. Its own
    # expense ratio (0.14%) is already inside the NAV, hence expense_ratio=0.
    Series("SP500_TR", "VFINX", "us", "equity", True,
           "S&P 500 total return (VFINX)", note="1980-01 onward; ER already in NAV"),
    Series("SPY", "SPY", "us", "equity", True,
           "S&P 500 ETF (SPY)", expense_ratio=0.0009, note="1993-01 onward"),
    Series("NASDAQ100", "QQQ", "us", "equity", True,
           "Nasdaq 100 ETF (QQQ)", expense_ratio=0.0020, note="1999-03 onward"),
    Series("RUSSELL2000", "IWM", "us", "equity", True,
           "Russell 2000 ETF (IWM)", expense_ratio=0.0019, note="2000-05 onward"),
    Series("TOTAL_MKT", "VTI", "us", "equity", True,
           "US total market (VTI)", expense_ratio=0.0003, note="2001-06 onward"),
    Series("INTL", "EFA", "us", "equity", True,
           "Developed ex-US (EFA)", expense_ratio=0.0033, note="2001-08 onward"),
    # Price-only, 1927 onward. The 98-year sanity check: if a calendar effect
    # exists at all it should leave a trace here, and if it only appears in
    # the post-1993 window it is a regime, not an effect.
    Series("SP500_PRICE_LONG", "^GSPC", "us", "equity", False,
           "S&P 500 price index (^GSPC)", div_yield=0.0189,
           note="1927-12 onward; PRICE ONLY. 1.89%/yr is MEASURED, not assumed: "
                "^GSPC vs VFINX over 1980-2026 (--calibrate-dividends). Applying a "
                "1980-2026 average back to 1927 understates the 1930s-70s, when the "
                "yield ran 3-5%, so pre-1980 total returns here are conservative"),
    Series("BONDS", "IEF", "us", "bond", True,
           "7-10y Treasuries (IEF)", expense_ratio=0.0015, note="2002-07 onward"),
    Series("BONDS_LONG", "TLT", "us", "bond", True,
           "20y+ Treasuries (TLT)", expense_ratio=0.0015, note="2002-07 onward"),
    Series("GOLD", "GLD", "us", "gold", True,
           "Gold (GLD)", expense_ratio=0.0040, note="2004-11 onward"),
    # 13-week T-bill YIELD in percent, not a price. 1960 onward, so the cash
    # leg is real data for the whole of every US window here.
    Series("CASH_YIELD", "^IRX", "us", "yield", False,
           "13-week T-bill yield (^IRX)", note="1960-01 onward; annualised %"),
]

# MEASURED from ^NSEI vs NIFTYBEES over 2009-2026 (--calibrate-dividends),
# then applied to every India price index since no other TR series exists to
# calibrate against. It is a LOWER BOUND: NIFTYBEES' own expense ratio and
# tracking error are inside the difference, and NSE's published Nifty 50 yield
# has run 1.1-1.4%. Absolute India CAGRs here are therefore ~0.3-0.5pp
# conservative; relative comparisons, where both arms carry the same accrual,
# are unaffected.
INDIA_DIV_YIELD = 0.0083

_INDIA = [
    # India's problem: no long total-return index series exists on Yahoo.
    # NIFTYBEES is clean TR but starts 2009; ^BSESN reaches back to 1997 but
    # is price-only. Both windows are run, per the design decision, and the
    # synthetic yield below is CALIBRATED against the overlap rather than
    # guessed — see calibrate_dividend_yield().
    Series("NIFTY50_TR", "NIFTYBEES.NS", "india", "equity", True,
           "Nifty 50 total return (NIFTYBEES)", expense_ratio=0.0005,
           note="2009-01 onward; ER already in NAV"),
    Series("NIFTY50", "^NSEI", "india", "equity", False,
           "Nifty 50 price index (^NSEI)", div_yield=INDIA_DIV_YIELD,
           note="2007-09 onward; PRICE ONLY"),
    Series("SENSEX", "^BSESN", "india", "equity", False,
           "Sensex price index (^BSESN)", div_yield=INDIA_DIV_YIELD,
           note="1997-07 onward; PRICE ONLY — the long India window"),
    Series("NIFTY500", "^CRSLDX", "india", "equity", False,
           "Nifty 500 price index (^CRSLDX)", div_yield=INDIA_DIV_YIELD,
           note="2005-09 onward; PRICE ONLY"),
    Series("NEXT50", "JUNIORBEES.NS", "india", "equity", True,
           "Nifty Next 50 (JUNIORBEES)", expense_ratio=0.0015, note="2009-01 onward"),
    # Yahoo has no Midcap 150 series (both ^NSEMDCP150 and
    # NIFTY_MIDCAP_150.NS return nothing); Midcap 50 is the available proxy.
    Series("MIDCAP", "^NSEMDCP50", "india", "equity", False,
           "Nifty Midcap 50 price index", div_yield=INDIA_DIV_YIELD,
           note="2007-09 onward; PRICE ONLY; midcaps actually yield less than "
                "the Nifty, so this slightly flatters them"),
    Series("GOLD", "GOLDBEES.NS", "india", "gold", True,
           "Gold (GOLDBEES)", expense_ratio=0.0055, note="2009-01 onward"),
    # Motilal Nasdaq 100 — real INR-denominated US exposure, so the
    # India/US split can be tested without inventing an FX conversion.
    Series("US_IN_INR", "MON100.NS", "india", "equity", True,
           "Nasdaq 100 in INR (MON100)", expense_ratio=0.0058, note="2011-03 onward"),
    # Liquid fund TR — India's cash leg. Starts 2009, so the long Sensex
    # window needs a constant before that (see cash_rate_series).
    Series("CASH_FUND", "LIQUIDBEES.NS", "india", "cash", True,
           "Liquid fund (LIQUIDBEES)", note="2009-01 onward"),
    Series("USDINR", "INR=X", "india", "fx", False,
           "USD/INR", note="2003-12 onward"),
]

REGISTRY: dict[str, Series] = {f"{s.market}:{s.key}": s for s in (*_US, *_INDIA)}


def for_market(market: str) -> dict[str, Series]:
    return {s.key: s for s in REGISTRY.values() if s.market == market}


def get(market: str, key: str) -> Series:
    try:
        return REGISTRY[f"{market}:{key}"]
    except KeyError:
        known = ", ".join(sorted(for_market(market)))
        raise KeyError(f"unknown series '{key}' for {market}; known: {known}") from None


# --- fetch / store -------------------------------------------------------


def init_schema() -> None:
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute(SCHEMA)


# A single-day move an index or index ETF has never made. The worst day in
# 98 years of ^GSPC is 1987-10-19 at -20.5%; India's circuit breakers cap the
# daily move well inside this. So anything past +/-40% is not a market move,
# it is a corporate action the data vendor applied inconsistently.
_IMPOSSIBLE_UP = 1.40
_IMPOSSIBLE_DOWN = 0.60
_REVERSAL_WINDOW = 7


def repair(df: pd.DataFrame, key: str = "") -> tuple[pd.DataFrame, list[str]]:
    """Fix vendor split-adjustment artefacts. Returns (clean, log).

    Yahoo applies some NSE splits to only part of a series, leaving a few
    days at the pre-split level: NIFTYBEES prints -89.9% on 2019-12-19 and
    +896.9% on 2019-12-23 (a 1:10 split), GOLDBEES -99% then +9900% (1:100),
    MON100 -90% then +892%. Left alone these produce a -90% "max drawdown"
    on a market that fell 38%, which would have silently wrecked every India
    comparison in the suite.

    Three cases, each repaired differently because they are different bugs:

    * **Spike reversal** — an impossible move undone within a week. The
      bracketing prices are right and the days between are at the wrong
      scale, so those are rebuilt by log-linear interpolation. Local and
      exact; no cumulative rescaling.
    * **Persistent jump** — an impossible move that is never undone: a real
      split the vendor never applied. Everything from that date on is
      rescaled to remove it, which is ordinary back-adjustment.
    * **Opening artefact** — an impossible move inside the first few bars,
      where index base values and ETF listing prices are unreliable. The
      series is truncated to start after it.

    Mutating data silently is worse than the bug, so every repair is logged
    and surfaced by `--validate`.
    """
    log: list[str] = []
    if df is None or len(df) < 10:
        return df, log

    s = df["close"].astype(float).copy()

    def outliers(series: pd.Series) -> list[int]:
        f = (series / series.shift(1)).values
        return [
            i for i in range(1, len(series))
            if f[i] == f[i] and (f[i] >= _IMPOSSIBLE_UP or f[i] <= _IMPOSSIBLE_DOWN)
        ]

    # 1. opening artefact
    bad = outliers(s)
    while bad and bad[0] <= 5:
        cut = bad[0]
        log.append(
            f"{key}: dropped {cut} opening bar(s) before "
            f"{s.index[cut].date()} ({(s.iloc[cut] / s.iloc[cut - 1] - 1) * 100:+.1f}% "
            f"on bar {cut} is a listing/base-value artefact)"
        )
        s = s.iloc[cut:]
        bad = outliers(s)

    # 2. spike reversals, then 3. persistent jumps
    guard = 0
    while bad and guard < 20:
        guard += 1
        i = bad[0]
        f_i = s.iloc[i] / s.iloc[i - 1]
        partner = next(
            (j for j in bad
             if i < j <= i + _REVERSAL_WINDOW
             and abs((s.iloc[j] / s.iloc[j - 1]) * f_i - 1) < 0.15),
            None,
        )
        if partner is not None:
            # read the reversing factor before the interpolation overwrites it
            f_j = s.iloc[partner] / s.iloc[partner - 1]
            # rebuild the inner days between the good bracket prices
            lo, hi = i - 1, partner
            span = hi - lo
            a, b = float(s.iloc[lo]), float(s.iloc[hi])
            for k in range(1, span):
                s.iloc[lo + k] = a * (b / a) ** (k / span)
            log.append(
                f"{key}: repaired split artefact "
                f"{s.index[i].date()}..{s.index[partner].date()} "
                f"({(f_i - 1) * 100:+.1f}% reversed by {(f_j - 1) * 100:+.1f}%) — "
                f"{span - 1} bar(s) interpolated"
            )
        else:
            s.iloc[i:] = s.iloc[i:] / f_i
            log.append(
                f"{key}: back-adjusted an unapplied {1 / f_i:.4g}:1 split at "
                f"{s.index[i].date()} ({(f_i - 1) * 100:+.1f}%, never reversed)"
            )
        bad = outliers(s)

    out = df.loc[s.index].copy()
    out["close"] = s
    return out, log


def fetch(series: Series) -> pd.DataFrame:
    """Full history for one series, dividend-adjusted where applicable.

    `auto_adjust=True` is the whole point of this module; the equity
    provider in `providers/` deliberately does the opposite.
    """
    import yfinance as yf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = yf.Ticker(series.ticker).history(
            period="max", interval="1d", auto_adjust=True
        )
    if raw is None or raw.empty:
        raise ValueError(f"{series.ticker}: no data returned")
    out = raw.rename(columns=str.lower)[["close"]].copy()
    out.index = pd.to_datetime(out.index).tz_localize(None)
    out = out[~out.index.duplicated(keep="last")].sort_index().dropna()
    # A yield series can legitimately be 0.0 (ZIRP 2009-2015); a price
    # series cannot, and a zero there is bad data.
    if series.kind != "yield":
        out = out[out["close"] > 0]
        out, log = repair(out, f"{series.market}:{series.key}")
        for line in log:
            logger.warning("REPAIR %s", line)
    return out


def save(series: Series, df: pd.DataFrame, replace: bool = False) -> int:
    if replace:
        # a repair can DROP leading bars; an upsert alone would leave the old
        # artefact rows in place and the series would still be wrong
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM index_series WHERE market=%s AND series=%s",
                (series.market, series.key),
            )
    rows = [
        (series.market, series.key, idx.date(), float(row["close"]))
        for idx, row in df.iterrows()
    ]
    db.execute_values(
        "INSERT INTO index_series (market, series, date, close) VALUES %s "
        "ON CONFLICT (market, series, date) DO UPDATE SET close = EXCLUDED.close",
        rows,
    )
    return len(rows)


def load(market: str, key: str) -> pd.Series:
    """Stored series as a float Series indexed by date. Raises if absent —
    a silently empty series would turn into a zero-return backtest."""
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT date, close FROM index_series WHERE market=%s AND series=%s "
            "ORDER BY date",
            (market, key),
        )
        rows = cur.fetchall()
    if not rows:
        raise ValueError(
            f"{market}:{key} not stored — run "
            f"`python3 -m swing_screener.marketdata.index_data --refresh`"
        )
    s = pd.Series(
        [float(c) for _, c in rows],
        index=pd.to_datetime([d for d, _ in rows]),
        name=key,
    )
    return s


def refresh(market: str | None = None, keys: list[str] | None = None) -> None:
    init_schema()
    targets = [
        s for s in REGISTRY.values()
        if (market is None or s.market == market) and (keys is None or s.key in keys)
    ]
    for s in targets:
        try:
            df = fetch(s)
        except Exception as e:  # noqa: BLE001 — one bad ticker must not stop the rest
            logger.warning("%s:%s (%s) FAILED: %s", s.market, s.key, s.ticker, e)
            continue
        n = save(s, df, replace=True)
        logger.info(
            "%s:%-18s %s -> %s  n=%d", s.market, s.key,
            df.index[0].date(), df.index[-1].date(), n,
        )


# --- holding returns -----------------------------------------------------


def total_return_index(
    market: str, key: str, div_yield: float | None = None,
    apply_expense: bool = True,
) -> tuple[pd.Series, list[str]]:
    """A series that can be HELD: dividends in, expense ratio out.

    Returns (index, caveats). For a price-only series a flat dividend
    accrual is added at `div_yield` (annual, 252-day accrual) — an
    approximation that smooths real lumpy ex-dates, which is harmless for
    horizon returns and slightly wrong for any single week.
    """
    spec = get(market, key)
    px = load(market, key)
    caveats: list[str] = []

    rets = px.pct_change().fillna(0.0)
    dy = spec.div_yield if div_yield is None else div_yield
    if not spec.total_return and dy:
        rets = rets + dy / 252.0
        caveats.append(
            f"{key} is a PRICE index; a flat {dy * 100:.2f}%/yr dividend accrual was "
            f"added to make it holdable. Real ex-dates are lumpy."
        )
    elif not spec.total_return and not dy and spec.kind == "equity":
        caveats.append(
            f"{key} is a PRICE index with NO dividend added — returns understate "
            f"holding it by roughly 1-2%/yr."
        )
    if apply_expense and spec.expense_ratio:
        rets = rets - spec.expense_ratio / 252.0
        caveats.append(f"{key}: {spec.expense_ratio * 100:.2f}%/yr expense ratio charged daily.")

    idx = (1.0 + rets).cumprod() * float(px.iloc[0])
    idx.name = key
    return idx, caveats


def cash_rate_series(
    market: str, index: pd.DatetimeIndex, override: float | None = None,
    fallback: float | None = None,
) -> tuple[pd.Series, list[str]]:
    """Annualised cash rate per date, aligned to `index`.

    This is not a detail. Every strategy that waits in cash — dip-buying,
    trend overlays, "wait for the crash" — is scored against what the money
    earned while waiting, and at a 0% assumption those strategies are being
    charged a penalty they would not actually pay. `override` exists so the
    assumption can be swept rather than chosen.
    """
    caveats: list[str] = []
    if override is not None:
        caveats.append(f"Cash modelled at a flat {override * 100:.2f}%/yr.")
        return pd.Series(override, index=index), caveats

    if market == "us":
        # ^IRX is the annualised discount rate in percent, 1960 onward — real
        # data across every US window used here.
        y = load("us", "CASH_YIELD").reindex(index).ffill() / 100.0
        if y.isna().any():
            y = y.bfill()
        caveats.append("Cash earns the 13-week T-bill yield (^IRX), daily accrual.")
        return y.clip(lower=0.0), caveats

    # India: LIQUIDBEES total return implies the realised liquid-fund rate,
    # but only from 2009. Before that there is no series, so the pre-2009
    # stretch takes a constant and says so.
    fund = load("india", "CASH_FUND").reindex(index).ffill()
    r = fund.pct_change().rolling(63, min_periods=20).mean() * 252
    r = r.clip(lower=0.0)
    pre = 0.065 if fallback is None else fallback
    missing = r.isna()
    if missing.any():
        r = r.fillna(pre)
        caveats.append(
            f"Cash: realised LIQUIDBEES yield from 2009; a flat {pre * 100:.2f}%/yr "
            f"before that ({int(missing.sum())} days), where no series exists. "
            f"Sweep it with --cash-rate."
        )
    else:
        caveats.append("Cash earns the realised LIQUIDBEES liquid-fund yield.")
    return r, caveats


# --- dividend calibration ------------------------------------------------


def calibrate_dividend_yield(
    market: str, price_key: str, tr_key: str
) -> tuple[float, pd.Timestamp, pd.Timestamp]:
    """Implied dividend yield = TR CAGR − price CAGR over the overlap.

    Lets the long price-only windows (Sensex 1997, ^GSPC 1927) carry an
    EMPIRICAL yield measured from this market's own data, instead of a
    number borrowed from somewhere else.
    """
    p, t = load(market, price_key), load(market, tr_key)
    joined = pd.concat([p.rename("p"), t.rename("t")], axis=1, sort=True).dropna()
    if len(joined) < 252 * 3:
        raise ValueError(f"overlap too short to calibrate: {len(joined)} bars")
    years = (joined.index[-1] - joined.index[0]).days / 365.25
    p_cagr = (joined["p"].iloc[-1] / joined["p"].iloc[0]) ** (1 / years) - 1
    t_cagr = (joined["t"].iloc[-1] / joined["t"].iloc[0]) ** (1 / years) - 1
    return float(t_cagr - p_cagr), joined.index[0], joined.index[-1]


def validate() -> list[str]:
    """Largest single-day move per stored series.

    Run after every refresh. Anything beyond ~25% on an index or index ETF
    is a vendor artefact that `repair` failed to catch, and it will show up
    as a fake drawdown in any backtest that touches the series.
    """
    problems: list[str] = []
    print(f"\n{'series':28s} {'worst day':>10s} {'best day':>10s}  flag")
    print("-" * 64)
    for spec in REGISTRY.values():
        if spec.kind in ("yield", "fx"):
            continue
        try:
            px = load(spec.market, spec.key)
        except ValueError:
            continue
        r = px.pct_change().dropna()
        if r.empty:
            continue
        lo, hi = float(r.min()), float(r.max())
        flag = ""
        if lo < -0.25 or hi > 0.25:
            flag = "<-- CHECK"
            problems.append(
                f"{spec.market}:{spec.key} has a {min(lo, -hi) * 100:+.1f}% day "
                f"({r.idxmin().date() if lo < -0.25 else r.idxmax().date()})"
            )
        print(f"{spec.market + ':' + spec.key:28s} {lo * 100:9.1f}% {hi * 100:9.1f}%  {flag}")
    return problems


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Total-return index series store")
    ap.add_argument("--refresh", action="store_true", help="fetch/update series")
    ap.add_argument("--market", choices=["us", "india"])
    ap.add_argument("--series", nargs="*", help="specific keys to refresh")
    ap.add_argument("--list", action="store_true", help="what is stored, with coverage")
    ap.add_argument("--validate", action="store_true",
                    help="flag any remaining impossible single-day moves")
    ap.add_argument("--calibrate-dividends", action="store_true",
                    help="implied dividend yield from each price/TR overlap")
    args = ap.parse_args()

    if args.refresh:
        refresh(args.market, args.series)

    if args.validate:
        bad = validate()
        if bad:
            print("\nPROBLEMS:")
            for b in bad:
                print(f"  - {b}")
        else:
            print("\nNo impossible moves — every series is within +/-25% on a day.")

    if args.calibrate_dividends:
        print("\nImplied dividend yield (TR CAGR - price CAGR over the overlap):")
        for mkt, price_key, tr_key in (
            ("us", "SP500_PRICE_LONG", "SP500_TR"),
            ("india", "NIFTY50", "NIFTY50_TR"),
        ):
            try:
                dy, a, b = calibrate_dividend_yield(mkt, price_key, tr_key)
                print(f"  {mkt:6s} {price_key:18s} vs {tr_key:12s} "
                      f"{dy * 100:5.2f}%/yr   ({a.date()} -> {b.date()})")
            except Exception as e:  # noqa: BLE001
                print(f"  {mkt:6s} {price_key:18s} FAILED: {e}")

    if args.list or not (args.refresh or args.calibrate_dividends or args.validate):
        init_schema()
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT market, series, min(date), max(date), count(*) "
                "FROM index_series GROUP BY market, series ORDER BY market, series"
            )
            rows = cur.fetchall()
        have = {(m, s): (a, b, n) for m, s, a, b, n in rows}
        print(f"\n{'market':7s} {'key':20s} {'ticker':16s} {'kind':7s} {'TR':3s} coverage")
        print("-" * 86)
        for spec in REGISTRY.values():
            cov = have.get((spec.market, spec.key))
            cov_s = f"{cov[0]} -> {cov[1]}  n={cov[2]}" if cov else "NOT STORED"
            print(f"{spec.market:7s} {spec.key:20s} {spec.ticker:16s} "
                  f"{spec.kind:7s} {'yes' if spec.total_return else 'no ':3s} {cov_s}")


if __name__ == "__main__":
    main()
