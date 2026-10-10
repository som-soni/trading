"""Quality-company tracker: is it a great business, and is the price right?

Two separate questions, answered separately on purpose — a great company at
the wrong price is a poor investment, and a cheap company that is cheap for a
reason is a value trap.

1. QUALITY (slow-moving; from up to five years of annual statements, refreshed
   by the offline fetch). Points for each test below; banks and insurers are
   scored on ROE/ROA instead of ROIC, margins, FCF and debt ratios, which do
   not mean the same thing for a balance-sheet business. Score is out of 100.

2. PRICE (fast-moving; recomputed from the latest close every time the page is
   opened, so no re-fetch is needed for a new day's price):
   * valuation — free-cash-flow yield, P/E against the company's OWN median
     P/E over the statement years, and PEG;
   * timing — distance below the 52-week high, distance from the 200-day
     average, RSI(14);
   * a falling-knife guard — far below a 200-day average is not a "dip".

Every threshold is a module constant, so the web page shows the live values.
Change a threshold here and the explanation on the page changes with it.

    PYTHONPATH=. python3 -m fundamentals.quality --market us --top 500
    PYTHONPATH=. python3 -m fundamentals.quality --market india --top 300
    PYTHONPATH=. python3 -m fundamentals.quality --tracked      # just your tracked list
    PYTHONPATH=. python3 -m fundamentals.quality --market us --symbols AAPL,MSFT

Fetching uses yfinance (about 1-2 s per company) and skips anything fetched
in the last --max-age days, so re-runs are cheap and an interrupted run resumes.

Not investment advice: these are screening rules of thumb, and annual
statements from a free data source contain errors and gaps.
"""

import argparse
import json
import logging
import math
import statistics
import time

from swing_screener.marketdata import db  # shared price/statement database

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- quality thresholds
ROIC_AVG_MIN = 0.15          # average return on invested capital
ROIC_FLOOR = 0.10            # worst single year
ROE_AVG_MIN_FIN = 0.12       # financials: average return on equity
ROA_MIN_FIN = 0.01           # financials: latest return on assets
REV_CAGR_MIN = 0.07          # revenue growth per year
EPS_CAGR_MIN = 0.07          # diluted EPS growth per year
OP_MARGIN_MIN = 0.15         # operating margin, latest year
MARGIN_SLIP_MAX = 0.01       # latest margin may sit at most this far below the earlier average
FCF_CONVERSION_MIN = 0.80    # free cash flow / net income, summed over the years
NET_DEBT_EBITDA_MAX = 2.0
INTEREST_COVER_MIN = 8.0
SHARE_CAGR_MAX = 0.01        # dilution: share count growth per year
HIGH_QUALITY_SCORE = 70      # score at or above this = "high quality"
MIN_YEARS = 3                # fewer years of statements than this = not scored

# ---------------------------------------------------------------- price thresholds
FCF_YIELD_ATTRACTIVE = 0.05
FCF_YIELD_FAIR = 0.03
PE_DISCOUNT_ATTRACTIVE = 0.20   # P/E at least 20% below the company's own median
PE_PREMIUM_EXPENSIVE = 0.10     # P/E more than 10% above its own median counts against
PEG_ATTRACTIVE = 1.0
PEG_FAIR = 1.5
VOTE_ATTRACTIVE = 1 / 3         # average vote (+1 cheap / 0 fair / -1 expensive) at or above this = Attractive
VOTE_FAIR = -1 / 3              # ... at or above this = Fair; below = Expensive
DRAWDOWN_DIP = 0.15             # at least 15% below the 52-week high
NEAR_200DMA = 0.03              # within 3% of the 200-day average
RSI_OVERSOLD = 35
FALLING_KNIFE = 0.15            # more than 15% below the 200-day average
ACCUMULATE_MAX_ABOVE_200 = 0.10 # "fair price" buying only while within 10% above the 200-day average

FIN_SECTORS = {"Financial Services", "Financials"}

# what each quality test is worth (financials skip the tests marked None and are re-scaled to 100)
TESTS = (
    ("roic", 20, "Return on invested capital averages at least {ROIC_AVG_MIN:.0%} (banks/insurers: return on equity at least {ROE_AVG_MIN_FIN:.0%})"),
    ("roic_floor", 10, "No year below {ROIC_FLOOR:.0%} ROIC (banks/insurers: latest ROA at least {ROA_MIN_FIN:.1%})"),
    ("profitable", 10, "Profitable in every year"),
    ("revenue_growth", 10, "Revenue grows at least {REV_CAGR_MIN:.0%} a year"),
    ("eps_growth", 10, "Diluted EPS grows at least {EPS_CAGR_MIN:.0%} a year"),
    ("margin", 10, "Operating margin at least {OP_MARGIN_MIN:.0%} (not scored for banks/insurers)"),
    ("margin_trend", 5, "Margin is not shrinking: latest within {MARGIN_SLIP_MAX:.0%} of the earlier average (not scored for banks/insurers)"),
    ("cash_conversion", 10, "Free cash flow positive every year and at least {FCF_CONVERSION_MIN:.0%} of net income (not scored for banks/insurers)"),
    ("balance_sheet", 10, "Net debt at most {NET_DEBT_EBITDA_MAX:g}× EBITDA and interest covered {INTEREST_COVER_MIN:g}× (not scored for banks/insurers)"),
    ("no_dilution", 5, "Share count grows no more than {SHARE_CAGR_MAX:.0%} a year"),
)
FIN_SKIPPED = {"margin", "margin_trend", "cash_conversion", "balance_sheet"}


def _fmt(text: str) -> str:
    return text.format(**{k: v for k, v in globals().items() if k.isupper()})


# reference text for the web page (rendered with the live constants above)
DOC = {
    "key": "quality",
    "name": "Quality companies",
    "kind": "long-term",
    "description": "Track businesses with durable fundamentals, and get told when the price makes them worth buying.",
    "status": "Screening aid for long-term investing, not a backtested strategy. Not investment advice.",
    "thesis": "Companies that earn high returns on capital, grow, convert profit to cash and carry little debt compound "
              "value for years; buying them when the price is temporarily depressed improves the return further.",
    "how_it_works": (
        "An offline script fetches up to five years of annual statements per company and scores business quality out of 100.",
        "Every time the page is opened, the latest close is used to value the company (free-cash-flow yield, P/E against its "
        "own history, PEG) and to time an entry (dip from the 52-week high, distance from the 200-day average, RSI).",
        "BUY ZONE: high quality, attractively valued, and in a pullback — without being a falling knife.",
        "ACCUMULATE: high quality at a fair price, not stretched above its 200-day average.",
        "WAIT: everything else — usually a great company that is simply expensive right now.",
        "Your own buy-below price, if you set one, adds AT YOUR PRICE once the close reaches it.",
    ),
    "caveats": (
        "Free statement data has gaps and errors (one-off charges, restatements, missing rows); always check the filings.",
        "Five years is one cycle at best; a cyclical company at its peak can look like a compounder.",
        "P/E against the company's own median uses only the statement years' fiscal year-end prices (4-5 points).",
        "Foreign companies whose statements are in a different currency from the share price are not valued.",
        "Not investment advice: the zones are screening rules of thumb, not recommendations.",
    ),
}


# ---------------------------------------------------------------- statement helpers

def _row(stmt: dict, *names) -> list:
    """Values for the first matching row name, oldest year first (None where missing)."""
    years = sorted(stmt)
    for name in names:
        vals = [stmt[y].get(name) for y in years]
        if any(v is not None for v in vals):
            return vals
    return [None] * len(years)


def _num(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def _cagr(first, last, years):
    if first is None or last is None or first <= 0 or last <= 0 or years < 1:
        return None
    return (last / first) ** (1 / years) - 1


def _cagr_series(vals: list):
    """Growth per year from the earliest to the latest year that actually have a value — the oldest
    column of a free statement feed is often mostly empty, which must not read as "no growth"."""
    idx = [i for i, v in enumerate(vals) if v is not None]
    if len(idx) < 2:
        return None
    return _cagr(vals[idx[0]], vals[idx[-1]], idx[-1] - idx[0])


def compute_metrics(raw: dict) -> dict | None:
    """Multi-year metrics from raw annual statements ({"income": {date: {row: v}}, ...})."""
    inc, bs, cf, info = raw.get("income") or {}, raw.get("balance") or {}, raw.get("cashflow") or {}, raw.get("info") or {}
    years = sorted(set(inc) & set(bs) & set(cf))
    if len(years) < MIN_YEARS:
        return None
    inc, bs, cf = ({y: d[y] for y in years} for d in (inc, bs, cf))
    n = len(years)
    g = lambda stmt, *names: [_num(v) for v in _row(stmt, *names)]
    rev = g(inc, "Total Revenue", "Operating Revenue")
    ni = g(inc, "Net Income Common Stockholders", "Net Income")
    eps = g(inc, "Diluted EPS", "Basic EPS")
    ebit = g(inc, "EBIT", "Operating Income")
    op = g(inc, "Operating Income", "EBIT")
    ebitda = g(inc, "EBITDA", "Normalized EBITDA")
    interest = g(inc, "Interest Expense")
    tax = g(inc, "Tax Rate For Calcs")
    gross = g(inc, "Gross Profit")
    equity = g(bs, "Stockholders Equity", "Common Stock Equity")
    invested = g(bs, "Invested Capital")
    debt = g(bs, "Total Debt")
    cash = g(bs, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents")
    assets = g(bs, "Total Assets")
    cur_a, cur_l = g(bs, "Current Assets"), g(bs, "Current Liabilities")
    lt_debt = g(bs, "Long Term Debt")
    shares = g(bs, "Ordinary Shares Number", "Share Issued")
    cfo = g(cf, "Operating Cash Flow")
    fcf = g(cf, "Free Cash Flow")
    capex = g(cf, "Capital Expenditure")
    fcf = [f if f is not None else (o + c if o is not None and c is not None else None) for f, o, c in zip(fcf, cfo, capex)]

    fin = (info.get("sector") in FIN_SECTORS)
    roic = [e * (1 - (t if t is not None and 0 <= t < 0.6 else 0.25)) / ic if e is not None and ic and ic > 0 else None
            for e, t, ic in zip(ebit, tax, invested)]
    roe = [x / q if x is not None and q and q > 0 else None for x, q in zip(ni, equity)]
    margin = [o / r if o is not None and r and r > 0 else None for o, r in zip(op, rev)]
    vals = lambda xs: [x for x in xs if x is not None]

    m = {
        "years": years, "fiscal_end": years[-1], "financial": fin, "n_years": n,
        "currency": info.get("currency"), "financial_currency": info.get("financialCurrency") or info.get("currency"),
        "name": info.get("longName") or info.get("shortName"), "sector": info.get("sector"), "industry": info.get("industry"),
        "roic_avg": statistics.mean(vals(roic)) if vals(roic) else None, "roic_min": min(vals(roic)) if vals(roic) else None,
        "roe_avg": statistics.mean(vals(roe)) if vals(roe) else None,
        "roa": ni[-1] / assets[-1] if ni[-1] is not None and assets[-1] else None,
        "profitable_years": sum(1 for x in ni if x is not None and x > 0), "ni_years": len(vals(ni)),
        "rev_cagr": _cagr_series(rev), "eps_cagr": _cagr_series(eps),
        "op_margin": margin[-1], "op_margin_prev_avg": statistics.mean(vals(margin[:-1])) if vals(margin[:-1]) else None,
        "fcf_conversion": (sum(vals(fcf)) / sum(vals(ni))) if vals(fcf) and vals(ni) and sum(vals(ni)) > 0 else None,
        "fcf_positive_years": sum(1 for x in fcf if x is not None and x > 0), "fcf_years": len(vals(fcf)),
        "net_debt_ebitda": ((debt[-1] or 0) - (cash[-1] or 0)) / ebitda[-1] if ebitda[-1] and ebitda[-1] > 0 else None,
        "net_cash": (cash[-1] or 0) > (debt[-1] or 0),
        "interest_cover": ebit[-1] / abs(interest[-1]) if ebit[-1] is not None and interest[-1] else None,
        "share_cagr": _cagr_series(shares),
        # latest-year values the live valuation needs
        "eps": eps[-1], "fcf": fcf[-1], "shares": shares[-1], "net_income": ni[-1],
        "eps_by_year": dict(zip(years, eps)),
    }
    # Piotroski F-score (latest year vs the one before)
    def roa(i):
        return ni[i] / assets[i] if ni[i] is not None and assets[i] else None
    def ratio(a, b, i):
        return a[i] / b[i] if a[i] is not None and b[i] else None
    f = [
        (roa(-1) or 0) > 0,
        (cfo[-1] or 0) > 0,
        roa(-1) is not None and roa(-2) is not None and roa(-1) > roa(-2),
        cfo[-1] is not None and ni[-1] is not None and cfo[-1] > ni[-1],
        ratio(lt_debt, assets, -1) is not None and ratio(lt_debt, assets, -2) is not None and ratio(lt_debt, assets, -1) <= ratio(lt_debt, assets, -2),
        ratio(cur_a, cur_l, -1) is not None and ratio(cur_a, cur_l, -2) is not None and ratio(cur_a, cur_l, -1) > ratio(cur_a, cur_l, -2),
        shares[-1] is not None and shares[-2] is not None and shares[-1] <= shares[-2],
        ratio(gross, rev, -1) is not None and ratio(gross, rev, -2) is not None and ratio(gross, rev, -1) > ratio(gross, rev, -2),
        ratio(rev, assets, -1) is not None and ratio(rev, assets, -2) is not None and ratio(rev, assets, -1) > ratio(rev, assets, -2),
    ]
    m["f_score"] = sum(bool(x) for x in f)
    return m


def score(m: dict) -> tuple[int, dict]:
    """Quality score out of 100, and the pass/fail (or skipped) result of every test."""
    fin = m["financial"]
    r = {}
    if fin:
        r["roic"] = m["roe_avg"] is not None and m["roe_avg"] >= ROE_AVG_MIN_FIN
        r["roic_floor"] = m["roa"] is not None and m["roa"] >= ROA_MIN_FIN
    else:
        r["roic"] = m["roic_avg"] is not None and m["roic_avg"] >= ROIC_AVG_MIN
        r["roic_floor"] = m["roic_min"] is not None and m["roic_min"] >= ROIC_FLOOR
    r["profitable"] = m["ni_years"] > 0 and m["profitable_years"] == m["ni_years"]
    r["revenue_growth"] = m["rev_cagr"] is not None and m["rev_cagr"] >= REV_CAGR_MIN
    r["eps_growth"] = m["eps_cagr"] is not None and m["eps_cagr"] >= EPS_CAGR_MIN
    if not fin:
        r["margin"] = m["op_margin"] is not None and m["op_margin"] >= OP_MARGIN_MIN
        r["margin_trend"] = (m["op_margin"] is not None and m["op_margin_prev_avg"] is not None
                             and m["op_margin"] >= m["op_margin_prev_avg"] - MARGIN_SLIP_MAX)
        r["cash_conversion"] = (m["fcf_years"] > 0 and m["fcf_positive_years"] == m["fcf_years"]
                                and m["fcf_conversion"] is not None and m["fcf_conversion"] >= FCF_CONVERSION_MIN)
        r["balance_sheet"] = ((m["net_cash"] or (m["net_debt_ebitda"] is not None and m["net_debt_ebitda"] <= NET_DEBT_EBITDA_MAX))
                              and (m["interest_cover"] is None or m["interest_cover"] >= INTEREST_COVER_MIN))
    r["no_dilution"] = m["share_cagr"] is None or m["share_cagr"] <= SHARE_CAGR_MAX
    possible = sum(w for k, w, _ in TESTS if not (fin and k in FIN_SKIPPED))
    got = sum(w for k, w, _ in TESTS if r.get(k))
    return round(100 * got / possible), r


def red_flags(m: dict) -> list[str]:
    """Disqualifiers no score can outweigh: a great business does not lose money or burn cash."""
    flags = []
    if m.get("ni_years") and m.get("profitable_years", 0) < m["ni_years"]:
        flags.append("a loss-making year")
    if not m.get("financial") and m.get("fcf") is not None and m["fcf"] <= 0:
        flags.append("negative free cash flow in the latest year")
    return flags


def is_high_quality(m: dict) -> bool:
    return m.get("quality_score") is not None and m["quality_score"] >= HIGH_QUALITY_SCORE and not red_flags(m)


def assess(m: dict, price: dict | None, target: float | None = None) -> dict:
    """Live valuation + timing from the latest close. `price` = {close, sma200, high_252, rsi14}."""
    out = {"zone": None, "value": None, "timing": [], "flags": [f"red flag: {f}" for f in red_flags(m)], "high_quality": is_high_quality(m)}
    if not price or price.get("close") is None:
        out["flags"].append("no price data")
        return out
    close = price["close"]
    same_ccy = m.get("financial_currency") == m.get("currency")
    pe = close / m["eps"] if same_ccy and m.get("eps") and m["eps"] > 0 else None
    mcap = m["shares"] * close if m.get("shares") else None
    # free cash flow means nothing for a bank's or insurer's balance sheet, so it is not used for them
    fcf_yield = m["fcf"] / mcap if same_ccy and mcap and m.get("fcf") is not None and not m.get("financial") else None
    pe_med = m.get("pe_hist_median")
    pe_disc = pe / pe_med - 1 if pe and pe_med else None
    peg = pe / (m["eps_cagr"] * 100) if pe and m.get("eps_cagr") and m["eps_cagr"] > 0 else None
    out.update(pe=pe, fcf_yield=fcf_yield, pe_vs_own=pe_disc, peg=peg, market_cap=mcap)
    if not same_ccy:
        out["flags"].append(f"statements in {m.get('financial_currency')}, price in {m.get('currency')} — not valued")
    # each available signal votes +1 (cheap), 0 (fair) or -1 (expensive); one cheap signal cannot
    # outvote the others — a low PEG does not make a stock cheap if it trades far above its own P/E
    votes = {}
    if fcf_yield is not None:
        votes["fcf_yield"] = 1 if fcf_yield >= FCF_YIELD_ATTRACTIVE else 0 if fcf_yield >= FCF_YIELD_FAIR else -1
    if pe_disc is not None:
        votes["pe_vs_own"] = 1 if pe_disc <= -PE_DISCOUNT_ATTRACTIVE else 0 if pe_disc <= PE_PREMIUM_EXPENSIVE else -1
    if peg is not None:
        votes["peg"] = 1 if peg <= PEG_ATTRACTIVE else 0 if peg <= PEG_FAIR else -1
    out["votes"] = votes
    if votes:
        avg = sum(votes.values()) / len(votes)
        out["value"] = "Attractive" if avg >= VOTE_ATTRACTIVE else "Fair" if avg >= VOTE_FAIR else "Expensive"

    dd = close / price["high_252"] - 1 if price.get("high_252") else None
    vs200 = close / price["sma200"] - 1 if price.get("sma200") else None
    rsi = price.get("rsi14")
    out.update(drawdown=dd, vs_200dma=vs200, rsi=rsi)
    if dd is not None and dd <= -DRAWDOWN_DIP:
        out["timing"].append(f"{-dd:.0%} below 52w high")
    if vs200 is not None and abs(vs200) <= NEAR_200DMA:
        out["timing"].append("at 200-day average")
    if rsi is not None and rsi <= RSI_OVERSOLD:
        out["timing"].append(f"RSI {rsi:.0f}")
    knife = vs200 is not None and vs200 < -FALLING_KNIFE
    if knife:
        out["flags"].append(f"falling knife: {-vs200:.0%} below 200-day average")

    high_q = out["high_quality"]
    if high_q and out["value"] == "Attractive" and out["timing"] and not knife:
        out["zone"] = "BUY ZONE"
    elif high_q and out["value"] in ("Attractive", "Fair") and not knife and (vs200 is None or vs200 <= ACCUMULATE_MAX_ABOVE_200):
        out["zone"] = "ACCUMULATE"
    else:
        out["zone"] = "WAIT"
    out["at_your_price"] = target is not None and close <= target
    return out


def criteria() -> dict:
    """Everything the web page needs to explain the signals, with live thresholds."""
    return {
        **DOC,
        "quality_tests": [{"key": k, "points": w, "text": _fmt(t)} for k, w, t in TESTS],
        "high_quality_score": HIGH_QUALITY_SCORE,
        "price_rules": [
            _fmt("Valuation is a vote of up to three signals, each cheap (+1), fair (0) or expensive (−1): free-cash-flow yield "
                 "(cheap ≥ {FCF_YIELD_ATTRACTIVE:.0%}, fair ≥ {FCF_YIELD_FAIR:.0%}; not used for banks/insurers), P/E against the "
                 "company's own median (cheap ≥ {PE_DISCOUNT_ATTRACTIVE:.0%} below it, expensive > {PE_PREMIUM_EXPENSIVE:.0%} above it), "
                 "and PEG (cheap ≤ {PEG_ATTRACTIVE:g}, fair ≤ {PEG_FAIR:g})."),
            _fmt("Attractive when the average vote is at least +{VOTE_ATTRACTIVE:.2f}, Fair when at least {VOTE_FAIR:.2f}, "
                 "otherwise Expensive — so one cheap signal cannot outvote two expensive ones."),
            _fmt("Timing (a pullback) is any of: at least {DRAWDOWN_DIP:.0%} below the 52-week high, within {NEAR_200DMA:.0%} "
                 "of the 200-day average, or RSI(14) at or below {RSI_OVERSOLD}."),
            _fmt("Falling knife: more than {FALLING_KNIFE:.0%} below the 200-day average — excluded from BUY ZONE and ACCUMULATE."),
            _fmt("High quality = score ≥ {HIGH_QUALITY_SCORE} and no red flag. Red flags override the score: a loss in any year, "
                 "or negative free cash flow in the latest year (banks/insurers excepted)."),
            _fmt("BUY ZONE = high quality + Attractive + a pullback + not a falling knife."),
            _fmt("ACCUMULATE = high quality + Fair or better + no more than "
                 "{ACCUMULATE_MAX_ABOVE_200:.0%} above the 200-day average + not a falling knife."),
        ],
    }


# ---------------------------------------------------------------- storage + batch

SCHEMA = """
CREATE TABLE IF NOT EXISTS fundamentals_raw (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw JSONB NOT NULL,                  -- info + annual income / balance / cashflow, as fetched
    error TEXT,
    PRIMARY KEY (market, symbol)
);
CREATE TABLE IF NOT EXISTS quality_scores (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    quality_score INT, tests JSONB, metrics JSONB NOT NULL,
    PRIMARY KEY (market, symbol)
);
CREATE TABLE IF NOT EXISTS quality_watch (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL,
    note TEXT, target_price DOUBLE PRECISION,
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _frame_to_dict(df) -> dict:
    """yfinance statement (rows x fiscal-year columns) -> {"YYYY-MM-DD": {row: value}}."""
    if df is None or df.empty:
        return {}
    return {str(col)[:10]: {str(k): db.py_value(v) for k, v in df[col].items() if db.py_value(v) is not None} for col in df.columns}


def fetch(market: str, symbol: str) -> bool:
    """Fetch and store one company's statements. Returns False (and remembers it) for anything that
    is not an operating company — ETFs, funds and indices have no statements to score."""
    import yfinance as yf
    t = yf.Ticker(symbol)
    info = t.info or {}
    kind = info.get("quoteType")
    if kind and kind != "EQUITY":
        with db.get_connection().cursor() as cur:
            cur.execute("""INSERT INTO fundamentals_raw (market, symbol, raw, error) VALUES (%s, %s, %s, NULL)
                           ON CONFLICT (market, symbol) DO UPDATE SET raw=EXCLUDED.raw, fetched_at=now(), error=NULL""",
                        (market, symbol, json.dumps({"not_equity": kind, "info": {"longName": info.get("longName")}})))
        return False
    keep = ("longName", "shortName", "sector", "industry", "currency", "financialCurrency", "marketCap", "quoteType")
    raw = {"info": {k: info.get(k) for k in keep},
           "income": _frame_to_dict(t.income_stmt), "balance": _frame_to_dict(t.balance_sheet), "cashflow": _frame_to_dict(t.cashflow)}
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO fundamentals_raw (market, symbol, raw, error) VALUES (%s, %s, %s, NULL)
                       ON CONFLICT (market, symbol) DO UPDATE SET raw=EXCLUDED.raw, fetched_at=now(), error=NULL""",
                    (market, symbol, json.dumps(raw)))
    return True


def _pe_history(market: str, symbol: str, eps_by_year: dict) -> float | None:
    """Median P/E at fiscal year-ends: the close on/just before each year-end over that year's EPS."""
    pes = []
    with db.get_connection().cursor() as cur:
        for day, eps in eps_by_year.items():
            if not eps or eps <= 0:
                continue
            cur.execute("SELECT close FROM prices WHERE market=%s AND symbol=%s AND date<=%s ORDER BY date DESC LIMIT 1",
                        (market, symbol, day))
            row = cur.fetchone()
            if row and row[0]:
                pes.append(row[0] / eps)
    return statistics.median(pes) if len(pes) >= 2 else None


def rescore(market: str, symbol: str) -> int | None:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT raw FROM fundamentals_raw WHERE market=%s AND symbol=%s", (market, symbol))
        row = cur.fetchone()
    if not row:
        return None
    m = compute_metrics(row[0])
    if m is None:
        return None
    s, tests = score(m)
    m["quality_score"] = s
    m["pe_hist_median"] = _pe_history(market, symbol, m.pop("eps_by_year"))
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO quality_scores (market, symbol, quality_score, tests, metrics) VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (market, symbol) DO UPDATE SET quality_score=EXCLUDED.quality_score, tests=EXCLUDED.tests,
                       metrics=EXCLUDED.metrics, computed_at=now()""",
                    (market, symbol, s, json.dumps(tests), json.dumps(m, default=str)))
    return s


def candidates(market: str, top: int) -> list[str]:
    """Stocks ranked by 20-day average turnover on the latest date, most liquid first — skipping
    anything already known not to be a company. Over-supplied (3x), because the liquidity ranking
    is crowded with ETFs and funds (in India especially); run() stops once `top` companies are scored."""
    with db.get_connection().cursor() as cur:
        # each stock's OWN latest row from the last 10 days — not one shared "latest date", which can be
        # a market holiday or a partial day holding only a handful of stray rows
        cur.execute("""SELECT l.symbol FROM (
                         SELECT DISTINCT ON (symbol) symbol, dollar_vol_sma20 FROM prices
                         WHERE market=%s AND date >= (SELECT max(date) FROM prices WHERE market=%s) - 10
                           AND dollar_vol_sma20 IS NOT NULL AND symbol NOT LIKE '^%%'
                         ORDER BY symbol, date DESC) l
                       LEFT JOIN fundamentals_raw f ON f.market=%s AND f.symbol=l.symbol
                       WHERE f.raw IS NULL OR NOT (f.raw ? 'not_equity')
                       ORDER BY l.dollar_vol_sma20 DESC LIMIT %s""", (market, market, market, top * 3))
        return [r[0] for r in cur.fetchall()]


def run(market: str | None, symbols: list[str], max_age_days: int, pause: float, want: int | None = None) -> dict:
    """Fetch (unless fresh) and score each symbol. With `want`, stop once that many companies are scored."""
    init_schema()
    done = failed = skipped = not_company = 0
    for i, (mkt, sym) in enumerate(symbols, 1):
        if want and done >= want:
            break
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT now() - fetched_at < %s * interval '1 day' FROM fundamentals_raw WHERE market=%s AND symbol=%s",
                        (max_age_days, mkt, sym))
            fresh = cur.fetchone()
        try:
            if fresh and fresh[0]:
                skipped += 1
            else:
                is_company = fetch(mkt, sym)
                time.sleep(pause)
                if not is_company:
                    not_company += 1
                    logger.info("[%d/%d] %s %s skipped: not a company (ETF / fund / index)", i, len(symbols), mkt, sym)
                    continue
            s = rescore(mkt, sym)
            if s is not None:
                done += 1
            logger.info("[%d/%d] %s %s quality=%s%s", i, len(symbols), mkt, sym, s, "" if s is not None else " (too few years of statements)")
        except Exception as exc:  # noqa: BLE001 — one bad ticker must not stop the batch
            failed += 1
            logger.warning("[%d/%d] %s %s failed: %s", i, len(symbols), mkt, sym, exc)
            with db.get_connection().cursor() as cur:
                cur.execute("""INSERT INTO fundamentals_raw (market, symbol, raw, error) VALUES (%s, %s, '{}', %s)
                               ON CONFLICT (market, symbol) DO UPDATE SET error=EXCLUDED.error, fetched_at=now()""",
                            (mkt, sym, str(exc)[:500]))
    return {"scored": done, "already_fresh": skipped, "not_companies": not_company, "failed": failed}


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch fundamentals and score company quality")
    ap.add_argument("--market", choices=["us", "india"])
    ap.add_argument("--top", type=int, default=0, help="score the N most liquid stocks of --market")
    ap.add_argument("--symbols", default="", help="comma-separated symbols of --market")
    ap.add_argument("--tracked", action="store_true", help="refresh everything on your tracked list")
    ap.add_argument("--max-age", type=int, default=30, help="re-fetch statements older than this many days")
    ap.add_argument("--pause", type=float, default=0.5, help="seconds between fetches (be polite to the data source)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    init_schema()
    todo: list[tuple[str, str]] = []
    if a.tracked:
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT market, symbol FROM quality_watch ORDER BY added_at")
            todo += cur.fetchall()
    if a.market and a.symbols:
        todo += [(a.market, s.strip().upper()) for s in a.symbols.split(",") if s.strip()]
    want = None
    if a.market and a.top:
        want = len(todo) + a.top  # the named/tracked companies, plus `top` from the liquidity ranking
        todo += [(a.market, s) for s in candidates(a.market, a.top)]
    if not todo:
        ap.error("nothing to do: give --tracked, or --market with --top / --symbols")
    seen, unique = set(), []
    for t in todo:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    print(run(a.market, unique, a.max_age, a.pause, want))


if __name__ == "__main__":
    main()
