"""Does one stored backtest really beat buy-and-hold? A fair benchmark, beta vs alpha, simpler
alternatives, after-tax returns, capacity, and how many years it would take to know.

Reads the run's report tables through the web app's API and stored prices and index series read-only,
never past the run's window. Prints markdown. Every assumption it makes (tax rates, the dividend proxy
for India, the liquidity floor) is printed with the figure it moves.

    cd scripts && PYTHONPATH=. .venv/bin/python ../.claude/skills/backtest-review/scripts/benchmark_check.py \
        --run 1730 [--host http://127.0.0.1:8000] [--st-tax 0.20 --lt-tax 0.125]
"""

import argparse
import json
import math
import urllib.request
from statistics import NormalDist

import numpy as np
import pandas as pd

from swing_screener.config import MARKETS
from swing_screener.marketdata import cache, db, index_data

Z95 = NormalDist().inv_cdf(0.975)
# tax rates: TODAY's statutory rates, applied to the whole window (they changed over it -- say so)
TAX = {"india": (0.20, 0.125),   # STCG 20%, LTCG 12.5% on listed equity (from July 2024); exemption ignored
       "us": (0.32, 0.15)}       # ASSUMED bracket: ordinary income 32% short-term, 15% long-term; no state tax
LT_DAYS = 365                    # held at least this long = long-term
ADV_LIMIT = 0.01                 # a position above 1% of the stock's 20-day average traded value is hard to fill
EDGE_TO_DETECT = 3.0             # "how many years to tell a 3-point-a-year edge from noise"
MOM_TOP = 0.10                   # momentum alternative: top decile by 12-1 month return
NW_LAGS = 5                      # Newey-West lags for the alpha t-statistic


def get(host, path):
    with urllib.request.urlopen(host.rstrip("/") + path, timeout=120) as r:
        return json.load(r)


def table(host, rid, name):
    try:
        t = get(host, f"/api/reports/{rid}/tables/{name}")
    except Exception:
        return None
    return pd.DataFrame(t["rows"], columns=t["columns"]) if t.get("rows") else None


def cagr_of(ret: pd.Series) -> float:
    eq = (1 + ret.fillna(0)).cumprod()
    yrs = max((ret.index[-1] - ret.index[0]).days / 365.25, 1e-9) if isinstance(ret.index, pd.DatetimeIndex) \
        else len(ret) / 252
    return (eq.iloc[-1] ** (1 / yrs) - 1) * 100 if eq.iloc[-1] > 0 else float("nan")


def mdd(ret: pd.Series) -> float:
    eq = (1 + ret.fillna(0)).cumprod()
    return ((eq / eq.cummax()) - 1).min() * 100


def sharpe(ret: pd.Series, rf: pd.Series) -> float:
    x = (ret - rf).dropna()
    return x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else float("nan")


def series(market, key, idx):
    try:
        s = index_data.load(market, key)
    except Exception:
        return None
    s.index = pd.to_datetime(s.index)
    return s.reindex(idx.union(s.index)).ffill().reindex(idx)


def benchmarks(market, idx, div_yield=None):
    """(price benchmark, total-return benchmark, cash daily return, notes)."""
    notes = []
    px = cache.load_cached(market, MARKETS[market].benchmark_ticker)
    price = px["close"].astype(float).reindex(idx.union(px.index)).ffill().reindex(idx)
    if market == "us":
        tr = series("us", "SPY", idx)
        notes.append("Total return: SPY with dividends reinvested (stored series SPY).")
        y = series("us", "CASH_YIELD", idx)
        cash = (y / 100 / 252).fillna(0) if y is not None else pd.Series(0.0, index=idx)
        notes.append("Cash: 3-month T-bill yield (^IRX), accrued daily.")
    else:
        n50, n50tr = series("india", "NIFTY50", idx), series("india", "NIFTY50_TR", idx)
        tr = None
        if div_yield is not None:
            div = pd.Series(div_yield / 252, index=idx)
            tr = price.iloc[0] * (1 + price.pct_change().fillna(0) + div).cumprod()
            notes.append(f"Total return: Nifty 500 price plus an ASSUMED {div_yield:.2%} a year dividend yield (--div-yield).")
        elif n50 is not None and n50tr is not None:
            div = (n50tr.pct_change() - n50.pct_change()).fillna(0).clip(lower=-0.02, upper=0.02)
            tr = price.iloc[0] * (1 + price.pct_change().fillna(0) + div).cumprod()
            notes.append("Total return: Nifty 500 price plus the Nifty 50's measured dividend return (NIFTYBEES "
                         "against ^NSEI, so net of the ETF's small fee) -- a proxy; Nifty 500 TR is not stored.")
            got = div.mean() * 252
            if got < 0.01:
                notes.append(f"**Check:** the measured yield is {got:.2%} a year, low against the index dividend yields "
                             "NSE publishes (roughly 1-1.5% over 2013-2021); the ETF's stored series may miss "
                             "payouts. Re-run with --div-yield set from NSE's published figure to bound the effect.")
        c = series("india", "CASH_FUND", idx)
        cash = c.pct_change().fillna(0) if c is not None else pd.Series(0.0, index=idx)
        notes.append("Cash: a liquid fund's NAV (stored series CASH_FUND).")
    return price, tr, cash, notes


def fair(eq, cash_tbl, price, tr, cash_r, notes, trades) -> list[str]:
    out = ["## 1. A fair benchmark"] + [f"- {n}" for n in notes]
    r = eq.pct_change().fillna(0)
    expo = (1 - cash_tbl / eq).clip(0, 1) if cash_tbl is not None else pd.Series(1.0, index=eq.index)
    r_cash = r + (1 - expo).shift().fillna(0) * cash_r        # idle cash earns the cash rate
    div_yield = (tr.pct_change() - price.pct_change()).mean() * 252 if tr is not None else 0.0
    r_div = r_cash + expo.shift().fillna(1) * div_yield / 252   # optimistic: held stocks yield like the index
    rows = [("Strategy as run (idle cash 0%, no dividends)", r),
            ("+ cash rate on idle cash", r_cash),
            ("+ dividends at the index's yield on what is held (optimistic)", r_div),
            ("Benchmark, price only (what the run compares with)", price.pct_change().fillna(0))]
    if tr is not None:
        rows.append(("Benchmark, total return", tr.pct_change().fillna(0)))
    out += ["", "| Book | CAGR | Max DD | Sharpe over cash |", "|---|---|---|---|"]
    for name, x in rows:
        out.append(f"| {name} | {cagr_of(x):.2f}% | {mdd(x):.1f}% | {sharpe(x, cash_r):.2f} |")
    if tr is not None:
        lo, hi = cagr_of(r_cash) - cagr_of(tr.pct_change().fillna(0)), cagr_of(r_div) - cagr_of(tr.pct_change().fillna(0))
        out.append(f"\n- Fair excess over total-return buy-and-hold: {lo:+.2f} to {hi:+.2f} points a year "
                   f"(without / with the dividend credit). Mean exposure {expo.mean() * 100:.0f}%; "
                   f"index dividend yield {div_yield * 100:.2f}%.")
    return out, r_cash, expo


def alpha_beta(r, rb, rf, expo) -> list[str]:
    out = ["## 2. Beta or alpha?"]
    df = pd.concat([r - rf, rb - rf], axis=1).dropna()
    y, x = df.iloc[:, 0].values, df.iloc[:, 1].values
    X = np.column_stack([np.ones_like(x), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    n = len(y)
    # Newey-West covariance
    S = (X * e[:, None]).T @ (X * e[:, None])
    for L in range(1, NW_LAGS + 1):
        w = 1 - L / (NW_LAGS + 1)
        G = (X[L:] * e[L:, None]).T @ (X[:-L] * e[:-L, None])
        S += w * (G + G.T)
    XtXi = np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(XtXi @ S @ XtXi))
    a_ann, t = b[0] * 252 * 100, b[0] / se[0]
    out.append(f"Daily returns over the cash rate, regressed on the benchmark's (total return), Newey-West t ({NW_LAGS} lags):")
    out.append(f"- Beta {b[1]:.2f}; alpha {a_ann:+.2f}% a year, t = {t:.2f} "
               f"({'significant' if abs(t) >= 2 else 'not significant'} at about 95%); R² {1 - e.var() / y.var():.2f}.")
    blend = expo.shift().fillna(1) * rb + (1 - expo.shift().fillna(1)) * rf
    k = (rb - rf).std() / (r - rf).std()
    scaled = rf + k * (r - rf)
    out += ["", "| Same exposure or same risk | CAGR | Max DD |", "|---|---|---|",
            f"| Strategy (cash earning the cash rate) | {cagr_of(r):.2f}% | {mdd(r):.1f}% |",
            f"| Index held at the strategy's own daily exposure, rest in cash | {cagr_of(blend):.2f}% | {mdd(blend):.1f}% |",
            f"| Strategy scaled to the index's volatility (×{k:.2f}) | {cagr_of(scaled):.2f}% | {mdd(scaled):.1f}% |",
            f"| Index, total return | {cagr_of(rb):.2f}% | {mdd(rb):.1f}% |"]
    out.append("\nAn excess that disappears against the exposure-matched index is market exposure, not skill. A "
               "strategy that wins once scaled to the index's volatility has an edge that leverage or a larger "
               "allocation could use -- scaled above 1× it borrows at the cash rate here, which is optimistic.")
    return out


def alternatives(market, start, end, rf_daily, strat_r) -> list[str]:
    out = ["## 3. Simpler alternatives on the same universe"]
    floor = MARKETS[market].screener.min_dollar_volume
    cur = db.get_connection().cursor()
    cur.execute("""WITH me AS (SELECT max(date) d FROM prices WHERE market=%s AND date BETWEEN %s::date - 400 AND %s
                               GROUP BY date_trunc('month', date))
                   SELECT p.symbol, p.date, p.close, p.dollar_vol_sma20 FROM prices p JOIN me ON p.date = me.d
                   WHERE p.market=%s""", (market, start, end, market))
    m = pd.DataFrame(cur.fetchall(), columns=["symbol", "date", "close", "dv"])
    m["date"] = pd.to_datetime(m.date)
    close = m.pivot(index="date", columns="symbol", values="close").astype(float)
    dv = m.pivot(index="date", columns="symbol", values="dv").astype(float)
    fwd = close.shift(-1) / close - 1                      # next month's price return
    mom = close.shift(1) / close.shift(12) - 1             # 12-1 month momentum, known at month-end
    liquid = dv >= floor
    months = close.index[(close.index >= pd.Timestamp(start)) & (close.index < pd.Timestamp(end))]
    ew, mo, n_liq, gone = [], [], [], 0
    for d in months:
        u = liquid.loc[d] & fwd.loc[d].notna()
        gone += int((liquid.loc[d] & fwd.loc[d].isna()).sum())
        n_liq.append(int(u.sum()))
        ew.append(fwd.loc[d][u].mean())
        mm = mom.loc[d][u].dropna()
        top = mm[mm >= mm.quantile(1 - MOM_TOP)].index if len(mm) >= 20 else []
        mo.append(fwd.loc[d][top].mean() if len(top) else np.nan)
    idx = pd.DatetimeIndex(months)
    ew, mo = pd.Series(ew, index=idx).fillna(0), pd.Series(mo, index=idx).fillna(0)
    sm = (1 + strat_r).resample("ME").prod() - 1
    sm.index = sm.index.to_period("M")
    ewp, mop = ew.copy(), mo.copy()
    ewp.index, mop.index = ewp.index.to_period("M"), mop.index.to_period("M")

    def stats(x):
        x = x.dropna()
        eq = (1 + x).cumprod()
        return (eq.iloc[-1] ** (12 / len(x)) - 1) * 100, ((eq / eq.cummax()) - 1).min() * 100

    out.append(f"Month-end rebalanced, price only, equal weight; universe = stocks whose 20-day average traded "
               f"value is at least {floor:,.0f} at the month-end (the strategy's liquidity floor), median "
               f"{int(np.median(n_liq))} stocks. {gone} stock-months dropped because the stock has no next "
               f"month-end price (delisted or suspended) -- a survivorship gap that flatters these books slightly.")
    last = close.loc[:pd.Timestamp(end)].apply(lambda c: c.last_valid_index())
    ever = liquid.loc[months].any()
    died = int((last[ever[ever].index] < pd.Timestamp(end) - pd.Timedelta(days=60)).sum())
    out.append(f"- **Survivorship check:** of {int(ever.sum())} stocks liquid at some month-end, {died} stop trading more "
               "than two months before the window ends. " + (
                   "None or almost none: the stored universe is today's listed stocks (documented in "
                   "research/app-guide-how-it-computes.md), so companies that failed are missing. That flatters "
                   "every long-only book here -- the strategy and these alternatives alike -- AGAINST THE INDEX, "
                   "which did hold the failures. A small excess over buy-and-hold is within this bias."
                   if died < 0.02 * max(int(ever.sum()), 1) else "Delisted stocks are present."))
    out += ["", "| Book (monthly) | CAGR | Max DD (monthly) |", "|---|---|---|"]
    for name, x in (("Strategy", sm), ("Equal weight, every liquid stock", ewp),
                    (f"Momentum: top {MOM_TOP:.0%} by 12-1 month return", mop)):
        c, d = stats(x)
        out.append(f"| {name} | {c:.2f}% | {d:.1f}% |")
    out.append("\nThese books carry no costs and the strategy does: monthly rebalancing of the momentum book "
               "turns over most of it each month, so knock off roughly its turnover times the market's cost a "
               "year before comparing. The index with a trend filter is in the audit's regime section. If equal weight beats the "
               "strategy, its selection loses to owning everything it could have picked from; if momentum "
               "does, a plainer rule captures the same thing.")
    return out


def after_tax(eq, trades, tr, market, st, lt, interest=None) -> list[str]:
    out = [f"## 4. After tax (short-term {st:.1%}, long-term {lt:.1%}: {'today’s Indian rates' if market == 'india' else 'an ASSUMED US bracket'}, applied to the whole window)"]
    if trades is None or "pnl" not in trades or tr is None:
        return out + ["Needs a trades table and a total-return benchmark."]
    t = trades.dropna(subset=["exit_date"]).copy()
    t["year"] = pd.to_datetime(t.exit_date).dt.year
    t["is_lt"] = t.holding_days >= LT_DAYS
    years = range(eq.index[0].year, eq.index[-1].year + 1)
    carry_st = carry_lt = 0.0
    wealth, tax_paid = eq.iloc[0], 0.0
    yr_end = eq.resample("YE").last()
    prev = eq.iloc[0]
    for y in years:
        g = t[t.year == y]
        st_g, lt_g = g[~g.is_lt].pnl.sum() + carry_st, g[g.is_lt].pnl.sum() + carry_lt
        # losses offset the other bucket, then carry forward
        if st_g < 0 < lt_g:
            lt_g, st_g = lt_g + st_g, 0.0
        elif lt_g < 0 < st_g:
            st_g, lt_g = st_g + lt_g, 0.0
        carry_st, carry_lt = min(st_g, 0.0), min(lt_g, 0.0)
        cash_int = float(interest[interest.index.year == y].sum()) if interest is not None else 0.0
        tax = max(st_g, 0) * st + max(lt_g, 0) * lt + max(cash_int, 0) * st
        end = yr_end[yr_end.index.year == y].iloc[0]
        r = end / prev - 1
        wealth = wealth * (1 + r) - tax * wealth / prev
        tax_paid += tax * wealth / end
        prev = end
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    s_pre = ((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100
    s_post = ((wealth / eq.iloc[0]) ** (1 / yrs) - 1) * 100
    b_mult = tr.iloc[-1] / tr.iloc[0]
    b_pre = (b_mult ** (1 / yrs) - 1) * 100
    b_post = ((1 + (b_mult - 1) * (1 - lt)) ** (1 / yrs) - 1) * 100
    out += ["", "| | Before tax | After tax |", "|---|---|---|",
            f"| Strategy, idle cash at the cash rate (taxed each year on realised trade gains; losses carried forward) | {s_pre:.2f}% | {s_post:.2f}% |",
            f"| Buy-and-hold, total return (taxed once at the end, long-term) | {b_pre:.2f}% | {b_post:.2f}% |",
            "", f"- Excess before tax {s_pre - b_pre:+.2f}, after tax {s_post - b_post:+.2f} points a year. "
            f"{(~t.is_lt).mean() * 100:.0f}% of trades are short-term. Dividend tax and the Indian LTCG exemption "
            "are ignored on both sides; the strategy's cash interest is taxed at the short-term rate as a stand-in "
            "for the income rate; "
            "buy-and-hold's tax is owed only when it is sold."]
    return out


def capacity(trades, market, eq) -> list[str]:
    out = ["## 5. Capacity: could it be traded at size?"]
    if trades is None or not {"symbol", "entry_date", "shares", "entry_price"} <= set(trades):
        return out + ["Needs per-symbol trades."]
    cur = db.get_connection().cursor()
    t = trades.copy()
    t["entry_date"] = pd.to_datetime(t.entry_date)
    adv = []
    for s, d in zip(t.symbol, t.entry_date):
        cur.execute("SELECT dollar_vol_sma20 FROM prices WHERE market=%s AND symbol=%s AND date < %s "
                    "ORDER BY date DESC LIMIT 1", (market, s, d.date()))
        r = cur.fetchone()
        adv.append(float(r[0]) if r and r[0] else np.nan)
    t["adv"] = adv
    if t.adv.notna().sum() < 10:
        return out + ["No stock liquidity data for these instruments (an index or ETF book): capacity is the "
                      "instrument's own, not a per-stock question."]
    t["pct_adv"] = t.shares * t.entry_price / t.adv * 100
    eqb = [eq[eq.index < d].iloc[-1] if (eq.index < d).any() else eq.iloc[0] for d in t.entry_date]
    t["w"] = t.shares * t.entry_price / pd.Series(eqb, index=t.index)
    cap = (ADV_LIMIT * t.adv / t.w).replace([np.inf], np.nan)
    out.append(f"- Position as % of the stock's 20-day average traded value at entry: median {t.pct_adv.median():.3f}%, "
               f"95th pct {t.pct_adv.quantile(0.95):.3f}%; above {ADV_LIMIT:.0%}: {(t.pct_adv > ADV_LIMIT * 100).sum()} trades.")
    out.append(f"- Capital at which the median position reaches {ADV_LIMIT:.0%} of its stock's traded value: "
               f"{cap.median():,.0f}; at which a quarter of positions do: {cap.quantile(0.25):,.0f} "
               f"(start capital {eq.iloc[0]:,.0f}).")
    if "r_multiple" in t:
        t = t.dropna(subset=["adv"])
        t["q"] = pd.qcut(t.adv.rank(method="first"), 5, labels=["thinnest", "2", "3", "4", "deepest"])
        g = t.groupby("q", observed=True).agg(n=("r_multiple", "size"), avgR=("r_multiple", "mean"), pnl=("pnl", "sum"))
        out += ["", "| Liquidity quintile at entry | n | Avg R | P&L |", "|---|---|---|---|"]
        for q, row in g.iterrows():
            out.append(f"| {q} | {int(row.n)} | {row.avgR:+.2f} | {row.pnl:,.0f} |")
        out.append("\nAn edge concentrated in the thinnest fifth is the one most likely to vanish at real size.")
    return out


def power(r, rb) -> list[str]:
    out = ["## 6. How many years would it take to know?"]
    x = (r - rb).dropna()
    te = x.std() * math.sqrt(252) * 100
    ir = x.mean() / x.std()
    z = (x - x.mean()) / x.std()
    g3, g4 = (z ** 3).mean(), (z ** 4).mean()
    out.append(f"- Tracking error against the total-return benchmark {te:.1f}% a year; information ratio "
               f"{ir * math.sqrt(252):+.2f}.")
    yrs_edge = (Z95 * te / EDGE_TO_DETECT) ** 2
    out.append(f"- Years of results needed to tell a {EDGE_TO_DETECT:.0f}-point-a-year edge from zero at this tracking "
               f"error (95%): about {yrs_edge:.0f}. The window holds {len(x) / 252:.1f}.")
    if ir > 0:
        mintrl = 1 + (1 - g3 * ir + (g4 - 1) / 4 * ir ** 2) * (Z95 / ir) ** 2
        out.append(f"- Minimum track record length for the observed excess (Bailey & López de Prado): "
                   f"{mintrl / 252:.0f} years.")
    else:
        out.append("- The observed excess is not positive, so there is nothing to confirm.")
    out.append("\nThis is also the paper-trading horizon: forward results shorter than this cannot settle the question "
               "on their own.")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", type=int, required=True)
    ap.add_argument("--host", default="http://127.0.0.1:8000")
    ap.add_argument("--st-tax", type=float, default=None)
    ap.add_argument("--lt-tax", type=float, default=None)
    ap.add_argument("--div-yield", type=float, default=None,
                    help="India: an annual dividend yield to add to the Nifty 500 price index instead of the measured proxy")
    ap.add_argument("--no-capacity", action="store_true", help="skip the per-trade liquidity lookups")
    a = ap.parse_args()
    rep = get(a.host, f"/api/reports/{a.run}")
    if (rep.get("stage") or "") == "verify":
        raise SystemExit("This is a verify-stage run: the review never reads one.")
    market = rep["market"]
    end = pd.Timestamp(str(rep.get("window_end") or "2100-01-01"))
    e = table(a.host, a.run, "equity")
    e = e.set_index(pd.to_datetime(e["date"]))
    e = e[e.index <= end]
    eq = e["equity"].astype(float)
    cash_tbl = e["cash"].astype(float) if "cash" in e else None
    trades = table(a.host, a.run, "trades")
    price, tr, cash_r, notes = benchmarks(market, eq.index, a.div_yield)
    st, lt = a.st_tax or TAX[market][0], a.lt_tax or TAX[market][1]
    print(f"# Against buy-and-hold, fairly: run {a.run}, {rep.get('strategy')} {market}, stage "
          f"{rep.get('stage') or 'legacy'}, {eq.index[0].date()} to {eq.index[-1].date()}\n")
    lines, r_cash, expo = fair(eq, cash_tbl, price, tr, cash_r, notes, trades)
    print("\n".join(lines) + "\n")
    rb = (tr if tr is not None else price).pct_change().fillna(0)
    print("\n".join(alpha_beta(r_cash, rb, cash_r, expo)) + "\n")
    print("\n".join(alternatives(market, str(eq.index[0].date()), str(eq.index[-1].date()), cash_r, r_cash)) + "\n")
    eq_cash = eq.iloc[0] * (1 + r_cash).cumprod()   # the same basis as section 1: idle cash earns the cash rate
    interest = eq_cash.shift().fillna(eq.iloc[0]) * (r_cash - eq.pct_change().fillna(0))
    print("\n".join(after_tax(eq_cash, trades, tr, market, st, lt, interest)) + "\n")
    if not a.no_capacity:
        print("\n".join(capacity(trades, market, eq)) + "\n")
    print("\n".join(power(r_cash, rb)))


if __name__ == "__main__":
    main()
