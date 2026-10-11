"""One company's financials, laid out like screener.in's company page — what the Fundamentals page shows.

Reads what `marketdata/financials.py` stores (statement lines, shareholding, profile) and the shared
metrics of `fundamentals/growth.py`, and builds:

  key ratios      market cap, price, 52-week high / low, P/E, book value, dividend yield, ROCE, ROE, face value, debt / equity
  quarters        the last QUARTERS quarters' P&L (sales ... EPS) with OPM % and tax %
  profit & loss   the last ANNUAL_YEARS fiscal years and the trailing twelve months, with dividend payout
  growth          compounded sales growth, profit growth, stock price CAGR and average ROE over 10 / 5 / 3 years
  balance sheet   each fiscal year end (and the latest half / quarter end)
  cash flows      each fiscal year: operating, investing, financing, net, capex, free cash flow
  ratios          debtor days, inventory days, ROCE %, ROE %, OPM % per year
  shareholding    promoters / FII / DII / government / public per quarter (India)
  peers           the stock's peer group (Sectors page), largest first
  views           each strategy's reading of the shared metrics (Minervini SEPA)

Money stays in the market's currency; the page divides by `MarketConfig.money_divisor` (₹ crore, $ million).
EPS and dividends per share are put on today's share basis where the share count jumped by a split or bonus.
"""

from __future__ import annotations

import datetime as dt

from swing_screener.config import MARKETS
from swing_screener.marketdata import db, financials

from . import growth

QUARTERS = 12                 # quarterly results columns
ANNUAL_YEARS = 12             # profit & loss / balance sheet / cash flow columns
GROWTH_WINDOWS = (10, 5, 3)   # compounded growth over these many years (plus TTM / 1 year)
PEERS = 10                    # peers shown, largest by market cap

PL = (("sales", "Sales", "money"), ("expenses", "Expenses", "money"), ("operating_profit", "Operating profit", "money"),
      ("opm", "OPM %", "pct"), ("other_income", "Other income", "money"), ("interest", "Interest", "money"),
      ("depreciation", "Depreciation", "money"), ("exceptional", "Exceptional items", "money"), ("pbt", "Profit before tax", "money"),
      ("tax_pct", "Tax %", "pct"), ("net_profit", "Net profit", "money"), ("eps", "EPS", "per_share"))
PL_LABELS = {   # the same lines, named the way each layout's filings name them
    "bank": {"sales": "Revenue (interest earned)", "expenses": "Expenses (incl. provisions)", "operating_profit": "Financing profit",
             "opm": "Financing margin %"},
    "us": {"operating_profit": "Operating income", "opm": "Operating margin %", "expenses": "Operating expenses"},
}
BS = (("equity_capital", "Equity capital", "money"), ("reserves", "Reserves", "money"), ("deposits", "Deposits", "money"),
      ("borrowings", "Borrowings", "money"), ("other_liabilities", "Other liabilities", "money"), ("total_liabilities", "Total liabilities", "money"),
      ("fixed_assets", "Fixed assets", "money"), ("cwip", "CWIP", "money"), ("investments", "Investments", "money"),
      ("advances", "Advances", "money"), ("cash", "Cash & bank", "money"), ("other_assets", "Other assets", "money"),
      ("total_assets", "Total assets", "money"))
BS_LABELS = {"us": {"equity_capital": "Paid-in capital", "reserves": "Retained earnings & other"}}
CF = (("cfo", "Cash from operating activity", "money"), ("cfi", "Cash from investing activity", "money"),
      ("cff", "Cash from financing activity", "money"), ("net_cash", "Net cash flow", "money"), ("capex", "Capital expenditure", "money"),
      ("fcf", "Free cash flow", "money"))
RATIOS = (("debtor_days", "Debtor days", "num"), ("inventory_days", "Inventory days", "num"), ("roce", "ROCE %", "pct"),
          ("roe", "ROE %", "pct"), ("opm", "OPM %", "pct"))


def _div(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def _cagr(new, old, years):
    if new is None or old is None or old <= 0 or new <= 0 or years <= 0:
        return None
    return (new / old) ** (1 / years) - 1


def _factors(dated_shares: list[tuple]) -> dict:
    """{date: split factor} from (date, shares) oldest first — growth.split_factors on a share-count series."""
    rows = [{"shares": s} for _, s in dated_shares]
    return {d: f for (d, _), f in zip(dated_shares, growth.split_factors(rows))}


def _with_derived(p: dict) -> dict:
    """Add OPM %, tax % and (annual) dividend payout and free cash flow to one period's lines."""
    p = dict(p)
    p["opm"] = _div(p.get("operating_profit"), p.get("sales"))
    p["tax_pct"] = _div(p.get("tax"), p.get("pbt")) if (p.get("pbt") or 0) > 0 else None
    if p.get("dividends_paid") is not None and (p.get("net_profit") or 0) > 0:
        p["dividend_payout"] = abs(p["dividends_paid"]) / p["net_profit"]
    if p.get("cfo") is not None and p.get("capex") is not None:
        p["fcf"] = p["cfo"] - abs(p["capex"])
    return p


def _table(periods: list, data: dict, spec: tuple, labels: dict, extra_cols: list | None = None, extra: dict | None = None) -> dict:
    """{columns, rows: [{key, label, kind, values}]}; a row or a period that is empty throughout is dropped."""
    periods = [p for p in periods if any(data.get(p, {}).get(k) is not None for k, _, _ in spec)]
    cols = [*periods, *(extra_cols or [])]
    rows = []
    for key, label, kind in spec:
        vals = [data.get(p, {}).get(key) for p in periods] + [(extra or {}).get(c, {}).get(key) for c in (extra_cols or [])]
        if any(v is not None for v in vals):
            rows.append({"key": key, "label": labels.get(key, label), "kind": kind, "values": vals})
    return {"columns": [str(c) for c in cols], "rows": rows}


def _price_at(market: str, symbol: str, day: dt.date) -> float | None:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT close FROM prices WHERE market=%s AND symbol=%s AND date<=%s ORDER BY date DESC LIMIT 1", (market, symbol, day))
        r = cur.fetchone()
    return r[0] if r else None


def _scores(market: str, symbols: list[str]) -> dict:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT to_regclass('fundamental_scores') IS NOT NULL")
        if not cur.fetchone()[0]:
            return {}
        cur.execute("SELECT symbol, metrics, views FROM fundamental_scores WHERE market=%s AND symbol = ANY(%s)", (market, symbols))
        return {s: (m, v) for s, m, v in cur.fetchall()}


def build(market: str, symbol: str, snap=None) -> dict:
    """Everything the Fundamentals page shows for one company. `snap`: the day's stock snapshot (DataFrame) or None."""
    cfg = MARKETS[market]
    meta = financials.load_meta(market).get(symbol) or {}
    lines = financials.load_lines(market, symbol)
    quarters = financials.load(market, [symbol]).get(symbol, [])
    layout = meta.get("layout") or ("us" if market == "us" else "industrial")
    profile = meta.get("profile") or {}
    srow = {}
    if snap is not None and len(snap) and symbol in set(snap["symbol"]):
        srow = snap[snap["symbol"] == symbol].iloc[0].to_dict()
    scores = _scores(market, [symbol]).get(symbol)
    m = scores[0] if scores else growth.metrics(quarters, meta)
    out = {"market": market, "symbol": symbol, "name": meta.get("name") or profile.get("longName"), "layout": layout,
           "unit": cfg.money_unit, "divisor": cfg.money_divisor, "currency": cfg.currency_symbol,
           "status": {k: meta.get(k) for k in ("status", "source", "basis", "fetched_at", "error", "fallback_reason")},
           "profile": profile, "sector": srow.get("sector") or profile.get("sector"), "industry": srow.get("industry") or profile.get("industry"),
           "peer_group": srow.get("peer_group")}
    if not lines and not quarters:
        return out

    # quarters (EPS on today's share basis, from the quarter rows' share counts)
    qf = _factors([(r["period_end"], r.get("shares")) for r in quarters])
    qdata = {}
    for e, vals in (lines.get("Q") or {}).items():
        p = _with_derived(vals)
        if p.get("eps") is not None and qf.get(e):
            p["eps"] = p["eps"] / qf[e]
        qdata[e] = p
    qends = sorted(qdata)[-QUARTERS:]
    labels = PL_LABELS.get(layout, {})
    out["quarters"] = _table(qends, qdata, PL, labels)

    # fiscal years (per-share figures adjusted from the year-end share counts)
    bsl = lines.get("BS") or {}
    fy = lines.get("FY") or {}
    # the year's share count: filed with the year (NSE) or on the balance sheet at its end (SEC cover page)
    fy_shares = [(e, fy[e].get("shares") or next((bsl[x].get("shares") for x in bsl if abs((x - e).days) <= 5), None)) for e in sorted(fy)]
    ff = _factors([(e, sh) for e, sh in fy_shares if sh])
    fdata = {}
    for e, vals in fy.items():
        p = _with_derived(vals)
        f = ff.get(e)
        for k in ("eps", "dividend_ps"):
            if p.get(k) is not None and f:
                p[k] = p[k] / f
        fdata[e] = p
    fends = sorted(fdata)[-ANNUAL_YEARS:]
    last4 = sorted(qdata)[-4:]
    ttm = {}
    if len(last4) == 4 and (last4[-1] - last4[0]).days <= 290:
        for k in ("sales", "expenses", "operating_profit", "other_income", "interest", "depreciation", "exceptional", "pbt", "tax", "net_profit"):
            vs = [qdata[e].get(k) for e in last4]
            ttm[k] = sum(vs) if all(v is not None for v in vs) else None
        ttm = _with_derived(ttm)
        ttm["eps"] = m.get("eps_ttm")
    pl_spec = PL + (("dividend_payout", "Dividend payout %", "pct"),)
    out["profit_loss"] = _table(fends, fdata, pl_spec, labels, ["TTM"] if ttm else None, {"TTM": ttm})

    # balance sheet: fiscal year ends, and the latest date if newer
    bends = [e for e in sorted(bsl) if any(abs((e - f).days) <= 5 for f in fends)]
    if bsl and max(bsl) not in bends and (not bends or max(bsl) > bends[-1]):
        bends.append(max(bsl))
    bends = bends[-ANNUAL_YEARS:]
    out["balance_sheet"] = _table(bends, bsl, BS, BS_LABELS.get(layout, {}))
    out["cash_flow"] = _table(fends, fdata, CF, {})

    # ratios per fiscal year
    rdata = {}
    for e in fends:
        p, b = fdata[e], next((bsl[x] for x in bsl if abs((x - e).days) <= 5), {})
        sales = p.get("sales")
        capital = None if layout == "bank" else (b.get("equity") or 0) + (b.get("minority") or 0) + (b.get("borrowings") or 0) if b.get("equity") else None
        rdata[e] = {
            "debtor_days": _div(b.get("receivables"), sales) * 365 if layout != "bank" and _div(b.get("receivables"), sales) is not None else None,
            "inventory_days": _div(b.get("inventory"), sales) * 365 if layout != "bank" and _div(b.get("inventory"), sales) is not None else None,
            "roce": _div((p.get("pbt") or 0) + (p.get("interest") or 0), capital) if capital and p.get("pbt") is not None else None,
            "roe": _div(p.get("net_profit"), b.get("equity")) if (b.get("equity") or 0) > 0 else None,
            "opm": p.get("opm"),
        }
    out["ratios"] = _table(fends, rdata, RATIOS, {"opm": labels.get("opm", "OPM %")})

    # compounded growth
    sales_s = [(e, fdata[e].get("sales")) for e in fends]
    profit_s = [(e, fdata[e].get("net_profit")) for e in fends]

    def comp(series, n):
        vals = [v for _, v in series]
        return _cagr(vals[-1], vals[-1 - n], n) if len(vals) > n else None

    prev4 = sorted(qdata)[-8:-4]

    def ttm_growth(k):
        if len(prev4) < 4 or not ttm:
            return None
        old = [qdata[e].get(k) for e in prev4]
        return _div(ttm.get(k), sum(old)) - 1 if all(v is not None for v in old) and sum(old) > 0 and ttm.get(k) is not None else None

    today = dt.date.today()
    price = srow.get("close") or _price_at(market, symbol, today)
    roes = [rdata[e]["roe"] for e in fends]
    out["growth"] = {
        "sales": [*[[f"{n} years", comp(sales_s, n)] for n in GROWTH_WINDOWS], ["TTM", ttm_growth("sales")]],
        "profit": [*[[f"{n} years", comp(profit_s, n)] for n in GROWTH_WINDOWS], ["TTM", ttm_growth("net_profit")]],
        "price": [[f"{n} years", _cagr(price, _price_at(market, symbol, today.replace(year=today.year - n)), n)] for n in GROWTH_WINDOWS]
                 + [["1 year", _cagr(price, _price_at(market, symbol, today.replace(year=today.year - 1)), 1)]],
        "roe": [*[[f"{n} years", (sum(x for x in roes[-n:] if x is not None) / len([x for x in roes[-n:] if x is not None]))
                   if len(roes) >= n and any(x is not None for x in roes[-n:]) else None] for n in GROWTH_WINDOWS],
                ["Last year", roes[-1] if roes else None]],
    }

    # key ratios
    lb = bsl[max(bsl)] if bsl else {}
    shares = lb.get("shares") or (quarters[-1].get("shares") if quarters else None) or profile.get("sharesOutstanding")
    mcap = srow.get("market_cap") or (price * shares if price and shares else None) or profile.get("marketCap")
    last_fy = fdata[fends[-1]] if fends else {}
    divs = abs(last_fy["dividends_paid"]) if last_fy.get("dividends_paid") is not None else None
    dy = _div(divs, mcap) if divs is not None and mcap else profile.get("trailingAnnualDividendYield")
    face = next((qdata[e].get("face_value") for e in reversed(qends) if qdata[e].get("face_value")), None)
    eq = lb.get("equity")
    out["ratios_top"] = {
        "market_cap": mcap, "price": price, "high_52w": srow.get("high_252"), "low_52w": srow.get("low_252"),
        "pe": _div(price, m.get("eps_ttm")) if (m.get("eps_ttm") or 0) > 0 else None,
        "book_value": _div(eq, shares), "dividend_yield": dy,
        "roce": rdata[fends[-1]]["roce"] if fends else None, "roe": m.get("roe"),
        "face_value": face, "debt_to_equity": _div(lb.get("borrowings"), eq) if layout != "bank" else None,
        "sales_ttm": ttm.get("sales") if ttm else None, "profit_ttm": ttm.get("net_profit") if ttm else None,
        "eps_ttm": m.get("eps_ttm"), "rs_rank": srow.get("rs_rank"),
    }

    out["shareholding"] = [{**r, "period_end": str(r["period_end"])} for r in financials.load_shareholding(market, symbol)][-QUARTERS:]
    out["holders"] = {k: profile.get(k) for k in ("heldPercentInsiders", "heldPercentInstitutions") if profile.get(k) is not None}

    # peers
    peers = []
    if snap is not None and srow.get("peer_group"):
        grp = snap[(snap["peer_group"] == srow["peer_group"]) & (snap["tradable"] == True)]  # noqa: E712
        grp = grp.sort_values("market_cap", ascending=False).head(PEERS)
        syms = list(grp["symbol"])
        if symbol not in syms:
            syms.append(symbol)
        sc = _scores(market, syms)
        for _, r in snap[snap["symbol"].isin(syms)].sort_values("market_cap", ascending=False).iterrows():
            pm = (sc.get(r["symbol"]) or ({}, {}))[0]
            et = pm.get("eps_ttm")
            peers.append({"symbol": r["symbol"], "close": r.get("close"), "market_cap": r.get("market_cap"),
                          "pe": _div(r.get("close"), et) if (et or 0) > 0 else None,
                          "sales_g": (pm.get("rev_g") or [None])[0], "eps_g": (pm.get("eps_g") or [None])[0], "roe": pm.get("roe"),
                          "rs_rank": r.get("rs_rank"), "self": r["symbol"] == symbol})
    out["peers"] = peers

    # strategy views
    views = scores[1] if scores else {v.key: v.evaluate(m) for v in growth.views()}
    out["views"] = [{**v.criteria(), "result": views.get(v.key)} for v in growth.views()]
    out["latest"] = {"end": str(m.get("latest_end")) if m.get("latest_end") else None, "fiscal": m.get("latest_fiscal"),
                     "filed": str(m.get("latest_filed")) if m.get("latest_filed") else None, "stale": m.get("stale"),
                     "split_adjusted": m.get("split_adjusted")}
    return out
