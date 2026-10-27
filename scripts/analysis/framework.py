"""The stock-analysis framework: pillars, the checks the data answers, and the questions only you can.

Each pillar asks one question about the company ("Are the profits real?") and answers it two ways:

  CHECKS     rules over stored data, graded good / ok / bad (or n/a where the data is missing or the rule
             does not apply — a bank has no inventory days). Every threshold is a module constant and the
             rule text names it as a {PLACEHOLDER}, so the page shows the live value.
  QUESTIONS  judgement the data cannot make (the moat, management, what is priced in). You rate each
             good / ok / bad and write why; an analysis stores your answers.

A pillar's evidence rating comes from its checks only (`summarise`): the share of scored checks that are
good (ok counts half). The framework never decides — the VERDICT (decision, conviction, thesis, what would
prove it wrong) is yours.

Where a rule already exists elsewhere it is reused, not re-written: the Stage 2 Trend Template and the
Established uptrend are the built-in screens' own conditions (`screens/definitions.py`), the valuation
votes are the Quality page's (`fundamentals/quality.py` `assess`), growth direction is Minervini SEPA's F2
and F8 (`fundamentals/sepa.py`), and the turnaround readings are `fundamentals/growth.py`'s.

A change to a check, a threshold or a question bumps VERSION and adds a CHANGELOG entry: each saved
analysis records the version it was made with, so an old analysis is read against the rules it had.
"""

from __future__ import annotations

from fundamentals import quality as _q

VERSION = "1.0"
CHANGELOG = (
    ("1.0", "2026-10-27", "First framework: ten pillars, 42 data checks (3 for information), 15 questions and a verdict."),
)

# ---------------------------------------------------------------- thresholds
# growth
G_SALES_CAGR_GOOD = 0.15        # G1: sales compounded over 3 fiscal years
G_SALES_CAGR_OK = 0.07
G_PROFIT_CAGR_GOOD = 0.15       # G2: net profit compounded over 3 fiscal years
G_PROFIT_CAGR_OK = 0.07
G_SALES_Q_GOOD = 0.20           # G3: latest quarter's sales vs a year earlier
G_SALES_Q_OK = 0.08
G_EPS_Q_GOOD = 0.25             # G4: latest quarter's EPS vs a year earlier
G_EPS_Q_OK = 0.10
G_STREAK_GOOD = 4               # G6: quarters in a row of EPS above the year-ago quarter
G_STREAK_OK = 2
# profitability
P_ROE_GOOD = 0.20               # P1: trailing-twelve-month return on equity
P_ROE_OK = 0.12
P_ROCE_GOOD = 0.20              # P2: latest fiscal year's return on capital employed
P_ROCE_OK = 0.12
P_MARGIN_YEARS = 3              # P3: latest operating margin vs the average of the fiscal years before it ...
P_MARGIN_SLIP_OK = 0.02         # ... may sit this far below it and still be "holding"
P_QUALITY_OK = 50               # P4: Quality score; good from fundamentals/quality.py HIGH_QUALITY_SCORE
# financial health
H_DE_GOOD = 0.5                 # H1: borrowings / equity
H_DE_OK = 1.0
H_COVER_OK = 3.0                # H2: interest cover; good from fundamentals/quality.py INTEREST_COVER_MIN
H_FCF_YEARS = 5                 # H3: free cash flow positive in how many of the last N fiscal years
H_FCF_GOOD = 4
H_FCF_OK = 3
# earnings quality
E_YEARS = 3                     # E1: cash from operations summed over N fiscal years ...
E_CFO_GOOD = 0.9                # ... against net profit over the same years
E_CFO_OK = 0.6
E_DAYS_BACK = 2                 # E2 / E3: debtor and inventory days now vs this many fiscal years earlier
E_DAYS_RISE_OK = 10             # a rise of up to this many days reads as noise
E_DAYS_SMALL = 15               # days this low throughout are immaterial (cash businesses, services)
E_OTHER_INCOME_GOOD = 0.10      # E4: other income as a share of profit before tax
E_OTHER_INCOME_OK = 0.25
E_ONE_OFF_GOOD = 0.05           # E5: exceptional items as a share of profit before tax
E_ONE_OFF_OK = 0.15
E_TAX_MIN = 0.15                # E6: an effective tax rate outside this band is worth a look
E_TAX_MAX = 0.35
# expectations
X_BEATS_OF = 4                  # X2: beats in the last N reported quarters
X_BEATS_GOOD = 3
X_BEATS_OK = 2
X_NEXT_GROWTH_GOOD = 0.15       # X3: next fiscal year's consensus EPS growth
X_NEXT_GROWTH_OK = 0.05
# ownership
O_QUARTERS = 4                  # O1 / O2: shareholding change over this many quarters
O_PROMOTER_DROP_OK = 0.01       # O1: promoters may sell this much (1 point) before it counts against
O_INST_MOVE = 0.01              # O2: institutions (FII + DII) moving by at least 1 point is a trend
# valuation
V_PEER_PE_GOOD = 0.8            # V4: P/E against the peer group's median P/E
V_PEER_PE_OK = 1.25
V_MIN_PEERS = 3                 # ... needs this many peers with a P/E
# trend & strength
T_STAGE2_NEAR = 2               # T1: missing at most this many Trend Template conditions reads as "close"
T_RS_GOOD = 80                  # T2: RS rank (1-99)
T_RS_OK = 50
T_GROUP_RS_GOOD = 70            # T3: the peer group's RS rating
T_GROUP_RS_OK = 40
T_REL_12M_OK = -10.0            # T4: 12-month return vs the market, percentage points
# risk
R_ATR_GOOD = 3.0                # R1: average true range, % of the close
R_ATR_OK = 5.0
R_MDD_GOOD = -30.0              # R2: deepest fall from a high over two years, %
R_MDD_OK = -50.0
R_EARNINGS_SOON = 14            # R4: results due within this many days is event risk
# pillar rating from its checks: share of scored checks that are good (ok counts half)
STRONG_MIN = 0.70
MIXED_MIN = 0.40
MIN_SCORED = 2                  # fewer scored checks than this = "thin" (shown, not rated)

PILLARS = (
    ("business", "Business", "What does it do, and why will it keep winning?"),
    ("growth", "Growth", "Is it growing — fast, steadily, and speeding up rather than slowing?"),
    ("profitability", "Profitability", "Does it earn a high return on the capital it uses?"),
    ("health", "Financial health", "Could it survive a bad year without diluting or borrowing heavily?"),
    ("earnings_quality", "Earnings quality", "Are the profits real — backed by cash, not by receivables, stock or one-offs?"),
    ("expectations", "Expectations", "What do analysts expect, which way are they moving, and does it beat them?"),
    ("ownership", "Ownership", "Are the people who know it best — promoters, insiders, institutions — buying or selling?"),
    ("valuation", "Valuation", "What is priced in: cheap or dear against its own history, its growth and its peers?"),
    ("trend", "Trend & strength", "Is the market already confirming it — uptrend, leadership, a strong group?"),
    ("risk", "Risk", "How hard can it fall, and what could hurt it soon?"),
)
PILLAR_KEYS = tuple(p[0] for p in PILLARS)

# your judgement: (code, pillar, question, what to think about)
QUESTIONS = (
    ("BQ1", "business", "What does it sell, to whom, and how does it make money?",
     "Segments and their share of revenue and profit; customers; recurring vs one-off revenue."),
    ("BQ2", "business", "What protects it from competitors?",
     "Brand, cost advantage, network effects, switching costs, licences, scale. How would a rival take share?"),
    ("BQ3", "business", "Is its market growing, and is it gaining share?",
     "Industry growth and cycle, the company's growth against its peers', new products or markets."),
    ("BQ4", "business", "Do you trust management?",
     "Track record against its own guidance, capital allocation (buybacks, acquisitions), related-party dealings, governance."),
    ("GQ1", "growth", "What is driving growth now, and can it last two to three years?",
     "Volume vs price, new products, capacity coming on, guidance. Is a one-off flattering the latest quarter?"),
    ("PQ1", "profitability", "Are the margins durable, or at a cyclical peak?",
     "Input costs, pricing power, operating leverage; how margins behaved in the last downturn."),
    ("HQ1", "health", "Could the balance sheet take a bad year?",
     "Debt maturities, working-capital needs, capex commitments, contingent liabilities."),
    ("EQ1", "earnings_quality", "Read the latest results: anything that flatters them?",
     "One-offs, changes in accounting or provisions, capitalised costs, receivables or inventory building up, auditor notes."),
    ("XQ1", "expectations", "What is the market expecting, and where could the company surprise?",
     "Guidance vs consensus, the reaction to the last few results, the next catalyst."),
    ("OQ1", "ownership", "Is anyone with inside knowledge buying, selling or pledging?",
     "Promoter pledges (India), insider buying or selling, large holders entering or leaving, buybacks."),
    ("VQ1", "valuation", "What is it worth on reasonable assumptions, and what is priced in?",
     "The growth the price implies; a bear / base / bull value; how far the price is from your base case."),
    ("TQ1", "trend", "Is the chart buyable now, or extended?",
     "Base and pivot, distance from the 50-day, volume on up vs down days, the market's own trend."),
    ("RQ1", "risk", "What would prove the thesis wrong?",
     "The one or two things to watch; where you would exit; regulation, litigation, concentration, key-person risk."),
    ("RQ2", "risk", "How big a position does this risk justify?",
     "Volatility, liquidity, correlation with what you already hold, conviction."),
    ("RQ3", "risk", "What is the bear case, told as the other side would tell it?",
     "Argue against yourself: why would a smart seller be selling to you today?"),
)
RATINGS = ("good", "ok", "bad")

# the verdict: yours, never computed
DECISIONS = ("Buy", "Accumulate", "Watch", "Hold", "Trim", "Sell", "Avoid")
VERDICT_FIELDS = (
    ("decision", "Decision", "One of: " + ", ".join(DECISIONS) + "."),
    ("conviction", "Conviction", "1 (a hunch) to 5 (would size up)."),
    ("thesis", "Thesis", "Why this stock, in two or three sentences — what you expect to happen and why the market has not priced it."),
    ("invalidation", "What would prove it wrong", "The facts or price action that would make you exit or abandon the idea."),
    ("review_on", "Review on", "When to look at it again — the next results, or a date."),
)

# a bad reading on one of these is listed as a red flag on the summary, whatever the pillar's rating
RED_FLAGS = ("E1", "E2", "E3", "H1", "H2", "O1", "R5")

# ---------------------------------------------------------------- checks
# (code, pillar, label, rule — {CONST} placeholders —, why it matters, value format: pct / pp (a fraction's change) / pct_raw and
#  pp_raw (already in percent) / num / x / days / text)
CHECKS_DOC = (
    ("B1", "business", "Size", "US$ market capitalisation (information, not scored).",
     "Size sets liquidity, coverage and how fast it can still grow.", "text"),
    ("B2", "business", "Industry and peers", "Sector, industry group and the peer group it is compared with (information).",
     "Every other reading means more against the right peers.", "text"),
    ("G1", "growth", "Sales growth, 3 years", "Sales compounded at least {G_SALES_CAGR_GOOD:.0%} a year over three fiscal years "
     "(ok from {G_SALES_CAGR_OK:.0%}).", "Sustained top-line growth is the engine everything else depends on.", "pct"),
    ("G2", "growth", "Profit growth, 3 years", "Net profit compounded at least {G_PROFIT_CAGR_GOOD:.0%} a year over three fiscal "
     "years (ok from {G_PROFIT_CAGR_OK:.0%}).", "Profit growing with sales shows the growth is worth having.", "pct"),
    ("G3", "growth", "Sales growth, latest quarter", "Latest quarter's sales up at least {G_SALES_Q_GOOD:.0%} on a year earlier "
     "(ok from {G_SALES_Q_OK:.0%}).", "The most recent read of demand.", "pct"),
    ("G4", "growth", "EPS growth, latest quarter", "Latest quarter's EPS up at least {G_EPS_Q_GOOD:.0%} on a year earlier "
     "(ok from {G_EPS_Q_OK:.0%}; a turn from a loss to a profit is ok).", "Earnings growth is what the biggest winners have in common.", "pct"),
    ("G5", "growth", "Speeding up or slowing", "Good when EPS growth is accelerating (Minervini SEPA F2) and not slowing (F8); "
     "bad when it has slowed two quarters running (F8 fails).", "The market pays for acceleration and punishes a slowdown.", "text"),
    ("G6", "growth", "Consistency", "EPS above the year-ago quarter for at least {G_STREAK_GOOD} quarters in a row "
     "(ok from {G_STREAK_OK}).", "A run of improving quarters is harder to fake than one good quarter.", "num"),
    ("P1", "profitability", "Return on equity", "Trailing-twelve-month ROE at least {P_ROE_GOOD:.0%} (ok from {P_ROE_OK:.0%}).",
     "How much profit each unit of shareholders' money earns.", "pct"),
    ("P2", "profitability", "Return on capital employed", "Latest fiscal year's ROCE at least {P_ROCE_GOOD:.0%} "
     "(ok from {P_ROCE_OK:.0%}; not for banks).", "ROE flattered by debt shows up as a lower ROCE.", "pct"),
    ("P3", "profitability", "Margin trend", "Latest operating margin (TTM) at or above the average of the previous "
     "{P_MARGIN_YEARS} fiscal years (ok down to {P_MARGIN_SLIP_OK:.0%} points below; not for banks).",
     "Shrinking margins are often the first sign of competition or cost pressure.", "pp"),
    ("P4", "profitability", "Quality score", "The Quality page's score (out of 100) at least {HIGH_QUALITY_SCORE} "
     "(ok from {P_QUALITY_OK}).", "Five years of returns, growth, cash conversion and debt in one number.", "num"),
    ("H1", "health", "Debt to equity", "Borrowings at most {H_DE_GOOD:g}× equity (ok up to {H_DE_OK:g}×; not for banks).",
     "Debt turns a bad year into a dangerous one.", "x"),
    ("H2", "health", "Interest cover", "Profit before interest and tax at least {INTEREST_COVER_MIN:g}× interest "
     "(ok from {H_COVER_OK:g}×; not for banks).", "Whether earnings comfortably carry the debt.", "x"),
    ("H3", "health", "Free cash flow", "Free cash flow positive in at least {H_FCF_GOOD} of the last {H_FCF_YEARS} fiscal years "
     "(ok from {H_FCF_OK}; not for banks).", "A business that consumes cash must keep raising it.", "num"),
    ("H4", "health", "Dilution", "Share count growing no more than {SHARE_CAGR_MAX:.0%} a year (the Quality page's test).",
     "Issuing shares hands part of the growth to new holders.", "text"),
    ("E1", "earnings_quality", "Cash conversion", "Cash from operations at least {E_CFO_GOOD:.0%} of net profit over the last "
     "{E_YEARS} fiscal years (ok from {E_CFO_OK:.0%}; not for banks).",
     "Profits that never arrive as cash are the commonest sign of aggressive accounting.", "pct"),
    ("E2", "earnings_quality", "Receivables vs sales", "Debtor days not up more than {E_DAYS_RISE_OK} days over {E_DAYS_BACK} "
     "fiscal years (immaterial below {E_DAYS_SMALL} days; not for banks).",
     "Sales booked but not collected — customers paid later, or the sales were pushed.", "days"),
    ("E3", "earnings_quality", "Inventory vs sales", "Inventory days not up more than {E_DAYS_RISE_OK} days over {E_DAYS_BACK} "
     "fiscal years (immaterial below {E_DAYS_SMALL} days; not for banks).",
     "Stock piling up faster than sales warns of slowing demand or coming write-downs (Minervini's check).", "days"),
    ("E4", "earnings_quality", "Other income", "Other (non-operating) income at most {E_OTHER_INCOME_GOOD:.0%} of profit before tax "
     "(ok up to {E_OTHER_INCOME_OK:.0%}; not for banks).", "Profit propped up by treasury income or asset sales is not the business.", "pct"),
    ("E5", "earnings_quality", "One-off items", "Exceptional items at most {E_ONE_OFF_GOOD:.0%} of profit before tax "
     "(ok up to {E_ONE_OFF_OK:.0%}).", "One-offs make a quarter look better (or worse) than the business is.", "pct"),
    ("E6", "earnings_quality", "Tax rate", "Effective tax rate (TTM) between {E_TAX_MIN:.0%} and {E_TAX_MAX:.0%}; outside it is "
     "only ok — worth a look.", "An unusually low tax charge lifts EPS without the business earning more.", "pct"),
    ("X1", "expectations", "Estimate revisions", "This fiscal year's EPS consensus raised over 90 days (good), unchanged (ok) "
     "or cut (bad).", "Analysts revising up tends to continue, and the price follows.", "pct"),
    ("X2", "expectations", "Beat record", "Beat the EPS consensus in at least {X_BEATS_GOOD} of the last {X_BEATS_OF} quarters "
     "(ok from {X_BEATS_OK}).", "A company that keeps beating is guiding conservatively, or growing faster than seen.", "text"),
    ("X3", "expectations", "Expected growth", "Next fiscal year's consensus EPS growth at least {X_NEXT_GROWTH_GOOD:.0%} "
     "(ok from {X_NEXT_GROWTH_OK:.0%}).", "What the market already expects — the bar it has to clear.", "pct"),
    ("O1", "ownership", "Promoter holding", "Promoters' stake not down by more than {O_PROMOTER_DROP_OK:.0%} of the shares over "
     "{O_QUARTERS} quarters (India; good when steady or rising).", "Promoters selling is the insiders' vote.", "pp"),
    ("O2", "ownership", "Institutional holding", "FII + DII stake over {O_QUARTERS} quarters: up by at least {O_INST_MOVE:.0%} "
     "of the shares (good), down as much (bad), else ok (India).", "Institutions building a position drive the big moves.", "pp"),
    ("O3", "ownership", "Insiders and institutions", "Insider and institutional ownership (information, not scored).",
     "Who owns it, and so who could buy or sell next.", "text"),
    ("V1", "valuation", "P/E vs its own history", "The Quality page's vote: P/E at least {PE_DISCOUNT_ATTRACTIVE:.0%} below the "
     "company's own median P/E (good), up to {PE_PREMIUM_EXPENSIVE:.0%} above (ok), else bad.",
     "A company is most comparable with itself.", "pct"),
    ("V2", "valuation", "PEG", "The Quality page's vote: P/E ÷ EPS growth at most {PEG_ATTRACTIVE:g} (good), up to {PEG_FAIR:g} (ok).",
     "A high P/E can be cheap if the growth is high enough.", "num"),
    ("V3", "valuation", "Free-cash-flow yield", "The Quality page's vote: free cash flow at least {FCF_YIELD_ATTRACTIVE:.0%} of the "
     "market value (good), {FCF_YIELD_FAIR:.0%} (ok).", "The cash return the business pays on today's price.", "pct"),
    ("V4", "valuation", "P/E vs peers", "P/E at most {V_PEER_PE_GOOD:g}× the peer group's median P/E (good), up to {V_PEER_PE_OK:g}× "
     "(ok); needs {V_MIN_PEERS} peers with a P/E.", "Whether you pay more than for similar businesses.", "x"),
    ("T1", "trend", "Stage 2 Trend Template", "Passes the Stage 2 — Trend Template screen (good); missing at most "
     "{T_STAGE2_NEAR} of its conditions (ok).", "Minervini's precondition: buy what is already in a confirmed uptrend.", "text"),
    ("T2", "trend", "RS rank", "Relative strength rank at least {T_RS_GOOD} (ok from {T_RS_OK}).",
     "Leaders outperform before, during and after their big moves.", "num"),
    ("T3", "trend", "Group strength", "The peer group's RS rating at least {T_GROUP_RS_GOOD} (ok from {T_GROUP_RS_OK}).",
     "Most of a stock's move comes from its group moving.", "num"),
    ("T4", "trend", "vs the market, 12 months", "Return over 12 months ahead of the market benchmark (good), "
     "or no more than {T_REL_12M_OK:g} points behind (ok).", "Whether it has actually been rewarding holders.", "pp_raw"),
    ("T5", "trend", "Established uptrend", "Passes the Established uptrend screen (good); in a weekly uptrend only (ok).",
     "A trend on the weekly chart outlasts one on the daily.", "text"),
    ("R1", "risk", "Volatility", "Average true range at most {R_ATR_GOOD:g}% of the price (ok up to {R_ATR_OK:g}%).",
     "Sets how wide a stop must be, and so how big a position can be.", "pct_raw"),
    ("R2", "risk", "Drawdown, 2 years", "Deepest fall from a high over two years no worse than {R_MDD_GOOD:g}% "
     "(ok to {R_MDD_OK:g}%).", "How much pain a holder has had to sit through.", "pct_raw"),
    ("R3", "risk", "Liquidity", "Clears the market's tradable floor (price, traded value, a year of history).",
     "Whether you can get in and out at the price on the screen.", "text"),
    ("R4", "risk", "Results soon", "Next results more than {R_EARNINGS_SOON} days away (good); sooner is event risk (ok).",
     "A results gap can jump straight through a stop.", "num"),
    ("R5", "risk", "Results current", "Latest results recent (not flagged stale by the Fundamentals page).",
     "Everything above is only as current as the last filing.", "text"),
)
CHECK_PILLAR = {c[0]: c[1] for c in CHECKS_DOC}

# constants the rule texts may name: this module's and the reused ones
_REUSED = {k: getattr(_q, k) for k in ("HIGH_QUALITY_SCORE", "INTEREST_COVER_MIN", "SHARE_CAGR_MAX", "PE_DISCOUNT_ATTRACTIVE",
                                       "PE_PREMIUM_EXPENSIVE", "PEG_ATTRACTIVE", "PEG_FAIR", "FCF_YIELD_ATTRACTIVE", "FCF_YIELD_FAIR")}


def _fmt(text: str) -> str:
    return text.format(**{**_REUSED, **{k: v for k, v in globals().items() if k.isupper() and not k.startswith("_")}})


def criteria() -> dict:
    """The framework as the page explains it, with live thresholds."""
    return {
        "version": VERSION, "changelog": [{"version": v, "date": d, "text": t} for v, d, t in CHANGELOG],
        "pillars": [{"key": k, "name": n, "question": q,
                     "checks": [{"code": c, "label": lab, "rule": _fmt(rule), "why": why}
                                for c, p, lab, rule, why, _ in CHECKS_DOC if p == k],
                     "questions": [{"code": c, "question": qq, "hint": h} for c, p, qq, h in QUESTIONS if p == k]}
                    for k, n, q in PILLARS],
        "verdict": [{"key": k, "label": lab, "hint": h} for k, lab, h in VERDICT_FIELDS],
        "decisions": list(DECISIONS), "ratings": list(RATINGS),
        "rating_rule": _fmt("A pillar's evidence rating counts its scored checks: good = 1, ok = ½, bad = 0. "
                            "Strong from {STRONG_MIN:.0%}, Mixed from {MIXED_MIN:.0%}, else Weak; fewer than {MIN_SCORED} "
                            "scored checks is Thin. The overall evidence score averages the rated pillars."),
        "red_flags": list(RED_FLAGS),
        "caveats": (
            "The checks read stored data: the Fundamentals page's statements, the day's stock snapshot, the Quality page's "
            "scores and Yahoo's analyst consensus. Where those are missing a check is n/a, not bad.",
            "Thresholds are rules of thumb for a growth investor; a utility or a bank will rarely look 'good' on growth.",
            "Banks and insurers skip the checks that do not mean the same for a balance-sheet business (ROCE, margins, "
            "debt, cash flow, working capital).",
            "Statements are as filed — one-offs are not removed, and filings can be restated.",
            "Not investment advice: the framework organises the evidence; the verdict is yours.",
        ),
    }


# ---------------------------------------------------------------- reading the evidence

def _res(status: str, value=None, detail: str = "") -> dict:
    return {"status": status, "value": value, "detail": detail}


def _na(detail: str) -> dict:
    return _res("na", None, detail)


def _grade(v, good, ok, higher: bool = True) -> str:
    if higher:
        return "good" if v >= good else "ok" if v >= ok else "bad"
    return "good" if v <= good else "ok" if v <= ok else "bad"


def _num(v):
    return None if v is None or (isinstance(v, float) and v != v) else v


def _table_row(t: dict | None, key: str) -> list[tuple[str, float | None]]:
    """[(column, value)] of one row of a Fundamentals-page table, oldest first ([] when absent)."""
    if not t:
        return []
    for r in t.get("rows") or []:
        if r["key"] == key:
            return list(zip(t["columns"], r["values"]))
    return []


def _fy(t: dict | None, key: str) -> list[float | None]:
    """A fiscal-year row's values, oldest first, without the TTM column."""
    return [v for c, v in _table_row(t, key) if c != "TTM"]


def _latest(t: dict | None, key: str):
    """(value, period) of the TTM column where present, else the latest fiscal year."""
    row = [(c, v) for c, v in _table_row(t, key) if v is not None]
    if not row:
        return None, None
    ttm = [x for x in row if x[0] == "TTM"]
    c, v = ttm[0] if ttm else row[-1]
    return v, c


def _growth_window(co: dict, line: str, label: str):
    for k, v in (co.get("growth") or {}).get(line) or []:
        if k == label:
            return v
    return None


def _shareholding_change(shp: list[dict], keys: tuple) -> tuple[float | None, float | None, str]:
    """(latest level, change over O_QUARTERS quarters, period words) of the summed holders `keys`."""
    rows = [r for r in shp if all(r.get(k) is not None for k in keys)]
    if len(rows) < 2:
        return None, None, ""
    new = rows[-1]
    old = rows[max(0, len(rows) - 1 - O_QUARTERS)]
    lv = sum(new[k] for k in keys)
    return lv, lv - sum(old[k] for k in keys), f"since {str(old['period_end'])[:7]}"


def _screen(ev: dict, key: str) -> tuple[bool | None, list[str]]:
    """Whether the stock passes a built-in screen on the snapshot's day, and the conditions it misses —
    by the screen's own conditions (screens/definitions.py), so the answer is the Screens page's."""
    df = ev.get("frame")
    if df is None or not len(df):
        return None, []
    from swing_screener.screens import definitions, snapshot
    conds = definitions.builtin()[key]["conditions"]
    labels = {f[0]: f[1] for f in snapshot.FIELDS}
    miss = [definitions.describe(c, labels) for c in conds if not bool(definitions.mask(df, [c]).iloc[0])]
    return not miss, miss


def evaluate(ev: dict) -> dict:
    """Evidence (evidence.gather) -> {code: {status, value, detail}} for every check."""
    co, m, s = ev.get("company") or {}, ev.get("metrics") or {}, ev.get("snap") or {}
    bank = ev.get("bank")
    rt = co.get("ratios_top") or {}
    pl, cf, ratios = co.get("profit_loss"), co.get("cash_flow"), co.get("ratios")
    has_fin = bool(co.get("quarters"))
    nofin = "no financial statements stored — fetch them on the Fundamentals page"
    out: dict[str, dict] = {}

    # ---- business (information)
    cap = _num(s.get("market_cap_usd"))
    out["B1"] = _res("info", None if cap is None else (f"${cap:,.0f}B" if cap >= 10 else f"${cap:,.1f}B"),
                     "" if cap is None else "large cap" if cap >= 10 else "mid cap" if cap >= 2 else "small cap")
    grp = " › ".join(x for x in (co.get("sector") or s.get("sector"), co.get("industry") or s.get("industry")) if x)
    peers = f"peer group {s['peer_group']} ({int(s['peer_count'])} tradable)" if s.get("peer_group") and _num(s.get("peer_count")) else ""
    out["B2"] = _res("info", grp or None, peers)

    # ---- growth
    for code, line, good, ok in (("G1", "sales", G_SALES_CAGR_GOOD, G_SALES_CAGR_OK), ("G2", "profit", G_PROFIT_CAGR_GOOD, G_PROFIT_CAGR_OK)):
        v = _growth_window(co, line, "3 years")
        out[code] = _res(_grade(v, good, ok), v, "compounded over 3 fiscal years") if v is not None else _na(
            nofin if not has_fin else "needs 4 fiscal years, starting from a profit")
    rg, eg = (m.get("rev_g") or [None])[0], (m.get("eps_g") or [None])[0]
    out["G3"] = _res(_grade(rg, G_SALES_Q_GOOD, G_SALES_Q_OK), rg) if rg is not None else _na(nofin if not has_fin else "no year-ago quarter")
    if eg is not None:
        out["G4"] = _res(_grade(eg, G_EPS_Q_GOOD, G_EPS_Q_OK), eg)
    elif m.get("eps_turned_positive"):
        out["G4"] = _res("ok", None, "turned from a loss to a profit")
    else:
        out["G4"] = _na(nofin if not has_fin else "the year-ago quarter was a loss" if m.get("latest_has_prior") else "no year-ago quarter")
    sepa = ((ev.get("views") or {}).get("sepa") or {}).get("tests") or {}
    f2, f8 = (sepa.get("F2") or {}).get("status"), (sepa.get("F8") or {}).get("status")
    if f2 in (None, "na") and f8 in (None, "na"):
        out["G5"] = _na("needs 4 quarters of EPS growth")
    elif f8 == "fail":
        out["G5"] = _res("bad", "slowing", "EPS growth slowed two quarters running (SEPA F8)")
    elif f2 == "pass":
        out["G5"] = _res("good", "accelerating", (sepa["F2"].get("detail") or "") + " (SEPA F2)")
    else:
        out["G5"] = _res("ok", "steady", "not accelerating, not slowing")
    n = m.get("eps_improving_q")
    out["G6"] = _res(_grade(n, G_STREAK_GOOD, G_STREAK_OK), n, "quarters in a row above the year-ago quarter") if n is not None else _na(
        nofin if not has_fin else "no year-ago quarter")

    # ---- profitability
    r = _num(m.get("roe"))
    out["P1"] = _res(_grade(r, P_ROE_GOOD, P_ROE_OK), r, m.get("roe_source") or "") if r is not None else _na("no equity figure")
    roce = _num(rt.get("roce"))
    out["P2"] = (_na("not used for banks") if bank else _res(_grade(roce, P_ROCE_GOOD, P_ROCE_OK), roce, "latest fiscal year")
                 if roce is not None else _na(nofin if not has_fin else "no balance sheet for the latest year"))
    opm_now, opm_when = _latest(pl, "opm")
    prev = [v for v in _fy(pl, "opm") if v is not None]
    if opm_when != "TTM":
        prev = prev[:-1]
    prev = prev[-P_MARGIN_YEARS:]
    if bank:
        out["P3"] = _na("not used for banks")
    elif opm_now is None or len(prev) < 2:
        out["P3"] = _na(nofin if not has_fin else f"needs {P_MARGIN_YEARS} earlier fiscal years")
    else:
        d = opm_now - sum(prev) / len(prev)
        out["P3"] = _res("good" if d >= 0 else "ok" if d >= -P_MARGIN_SLIP_OK else "bad", d,
                         f"{opm_now:.0%} ({opm_when}) vs {sum(prev) / len(prev):.0%} average")
    qs = (ev.get("quality") or {}).get("score")
    out["P4"] = _res(_grade(qs, _q.HIGH_QUALITY_SCORE, P_QUALITY_OK), qs) if qs is not None else _na("not scored on the Quality page")

    # ---- financial health
    de = _num(rt.get("debt_to_equity"))
    out["H1"] = _na("not used for banks") if bank else _res(_grade(de, H_DE_GOOD, H_DE_OK, higher=False), de) if de is not None else _na(
        nofin if not has_fin else "no balance sheet")
    pbt, intr = _fy(pl, "pbt"), _fy(pl, "interest")
    if bank:
        out["H2"] = _na("not used for banks")
    elif not pbt or pbt[-1] is None:
        out["H2"] = _na(nofin if not has_fin else "no profit before tax")
    elif not intr or not intr[-1] or intr[-1] <= 0:
        out["H2"] = _res("good", None, "no interest expense")
    else:
        cover = (pbt[-1] + intr[-1]) / intr[-1]
        out["H2"] = _res(_grade(cover, _q.INTEREST_COVER_MIN, H_COVER_OK), cover, "latest fiscal year")
    fcf = [v for v in _fy(cf, "fcf") if v is not None][-H_FCF_YEARS:]
    if bank:
        out["H3"] = _na("not used for banks")
    elif len(fcf) < H_FCF_OK:
        out["H3"] = _na(nofin if not has_fin else f"needs {H_FCF_OK}+ years of cash flows")
    else:
        pos = sum(v > 0 for v in fcf)
        out["H3"] = _res(_grade(pos, H_FCF_GOOD if len(fcf) >= H_FCF_YEARS else len(fcf), H_FCF_OK), pos, f"positive in {pos} of {len(fcf)} years")
    dil = ((ev.get("quality") or {}).get("tests") or {}).get("no_dilution")
    sc = ((ev.get("quality") or {}).get("metrics") or {}).get("share_cagr")
    out["H4"] = _na("not scored on the Quality page") if dil is None else _res(
        "good" if dil else "bad", None if sc is None else f"{sc:+.1%} a year", "share count growth")

    # ---- earnings quality
    cfo, npf = _fy(cf, "cfo"), _fy(pl, "net_profit")
    pairs = [(a, b) for a, b in zip(cfo, npf) if a is not None and b is not None][-E_YEARS:]
    if bank:
        out["E1"] = _na("not used for banks")
    elif len(pairs) < 2 or sum(b for _, b in pairs) <= 0:
        out["E1"] = _na(nofin if not has_fin else "needs 2+ profitable years with cash flows")
    else:
        conv = sum(a for a, _ in pairs) / sum(b for _, b in pairs)
        out["E1"] = _res(_grade(conv, E_CFO_GOOD, E_CFO_OK), conv, f"over {len(pairs)} fiscal years")
    for code, key, what in (("E2", "debtor_days", "debtor days"), ("E3", "inventory_days", "inventory days")):
        days = [v for v in _fy(ratios, key)]
        vals = [v for v in days if v is not None]
        if bank:
            out[code] = _na("not used for banks")
        elif len(vals) < E_DAYS_BACK + 1:
            out[code] = _na(nofin if not has_fin else f"needs {E_DAYS_BACK + 1} fiscal years of {what}")
        else:
            now, then = vals[-1], vals[-1 - E_DAYS_BACK]
            chg = now - then
            if max(now, then) < E_DAYS_SMALL:
                out[code] = _res("good", chg, f"{now:.0f} days — immaterial")
            else:
                out[code] = _res("good" if chg <= 0 else "ok" if chg <= E_DAYS_RISE_OK else "bad", chg, f"{then:.0f} → {now:.0f} days")
    oi, oi_when = _latest(pl, "other_income")
    pbt_now, _ = _latest(pl, "pbt")
    if bank:
        out["E4"] = _na("not used for banks (fees are other income)")
    elif oi is None or pbt_now is None or pbt_now <= 0:
        out["E4"] = _na(nofin if not has_fin else "no other income line, or a pre-tax loss")
    else:
        share = max(oi, 0) / pbt_now
        out["E4"] = _res(_grade(share, E_OTHER_INCOME_GOOD, E_OTHER_INCOME_OK, higher=False), share, oi_when or "")
    ex, ex_when = _latest(pl, "exceptional")
    if pbt_now is None or pbt_now <= 0:
        out["E5"] = _na(nofin if not has_fin else "a pre-tax loss")
    elif ex is None:
        out["E5"] = _na("not reported as a separate line")
    else:
        share = abs(ex) / pbt_now
        out["E5"] = _res(_grade(share, E_ONE_OFF_GOOD, E_ONE_OFF_OK, higher=False), share,
                         f"{'a gain' if ex > 0 else 'a charge' if ex < 0 else 'none'} ({ex_when})")
    tax, tax_when = _latest(pl, "tax_pct")
    out["E6"] = _na(nofin if not has_fin else "a pre-tax loss") if tax is None else _res(
        "good" if E_TAX_MIN <= tax <= E_TAX_MAX else "ok", tax,
        f"{tax_when}" + ("" if E_TAX_MIN <= tax <= E_TAX_MAX else " — unusually " + ("low" if tax < E_TAX_MIN else "high")))

    # ---- expectations (marketdata/estimates.py summary)
    est = ev.get("estimates") or {}
    per = {p["period"]: p for p in est.get("periods") or []}
    p0 = per.get("0y") or per.get("0q")
    if not p0 or p0.get("chg_90d") is None:
        out["X1"] = _na("no analyst consensus stored")
    else:
        out["X1"] = _res({"up": "good", "flat": "ok", "down": "bad"}[p0["dir_90d"]], p0["chg_90d"],
                         f"{p0['name'].lower()}'s EPS consensus over 90 days")
    surp = [x for x in est.get("surprises") or [] if x.get("beat") is not None][:X_BEATS_OF]
    if len(surp) < X_BEATS_OK:
        out["X2"] = _na("no surprise history stored")
    else:
        b = sum(x["beat"] for x in surp)
        out["X2"] = _res(_grade(b, X_BEATS_GOOD if len(surp) >= X_BEATS_OF else len(surp), X_BEATS_OK), f"{b} of {len(surp)}",
                         "quarters beating the EPS consensus")
    p1 = per.get("+1y")
    g1 = None if not p1 else p1.get("eps_growth")
    out["X3"] = _res(_grade(g1, X_NEXT_GROWTH_GOOD, X_NEXT_GROWTH_OK), g1,
                     f"{p1.get('eps_analysts') or '?'} analysts") if g1 is not None else _na("no next-year consensus stored")

    # ---- ownership
    shp = co.get("shareholding") or []
    lv, chg, since = _shareholding_change(shp, ("promoters",))
    if lv is None:
        out["O1"] = _na("no shareholding pattern stored (India only)")
    elif lv == 0 and chg == 0:
        out["O1"] = _na("no promoter group")
    else:
        out["O1"] = _res("good" if chg >= 0 else "ok" if chg >= -O_PROMOTER_DROP_OK else "bad", chg, f"{lv:.1%} now, {since}")
    lv, chg, since = _shareholding_change(shp, ("fii", "dii"))
    out["O2"] = _na("no shareholding pattern stored (India only)") if lv is None else _res(
        "good" if chg >= O_INST_MOVE else "bad" if chg <= -O_INST_MOVE else "ok", chg, f"{lv:.1%} now, {since}")
    h = co.get("holders") or {}
    bits = [f"insiders {h['heldPercentInsiders']:.0%}" if h.get("heldPercentInsiders") is not None else "",
            f"institutions {h['heldPercentInstitutions']:.0%}" if h.get("heldPercentInstitutions") is not None else ""]
    if shp:
        last = shp[-1]
        bits = [f"promoters {last['promoters']:.0%}" if last.get("promoters") is not None else "",
                f"FII {last['fii']:.0%}" if last.get("fii") is not None else "", f"DII {last['dii']:.0%}" if last.get("dii") is not None else ""]
    out["O3"] = _res("info", ", ".join(b for b in bits if b) or None)

    # ---- valuation (the Quality page's votes, fundamentals/quality.py assess)
    qa = (ev.get("quality") or {}).get("assess") or {}
    votes = qa.get("votes") or {}
    for code, vk, vv in (("V1", "pe_vs_own", "pe_vs_own"), ("V2", "peg", "peg"), ("V3", "fcf_yield", "fcf_yield")):
        if vk in votes:
            out[code] = _res({1: "good", 0: "ok", -1: "bad"}[votes[vk]], qa.get(vv))
        else:
            out[code] = _na("not scored on the Quality page" if not ev.get("quality") else
                            "not valued (statements in another currency)" if any("not valued" in f for f in qa.get("flags") or [])
                            else "not enough history" if code == "V1" else "no positive earnings growth" if code == "V2"
                            else "not used for banks" if code == "V3" and bank else "no free cash flow figure")
    pe = _num(rt.get("pe"))
    peer_pe = sorted(p["pe"] for p in co.get("peers") or [] if not p.get("self") and p.get("pe") and p["pe"] > 0)
    if pe is None:
        out["V4"] = _na("no P/E (a loss, or statements in another currency)")
    elif len(peer_pe) < V_MIN_PEERS:
        out["V4"] = _na(f"fewer than {V_MIN_PEERS} peers with a P/E")
    else:
        k = len(peer_pe)
        med = peer_pe[k // 2] if k % 2 else (peer_pe[k // 2 - 1] + peer_pe[k // 2]) / 2
        out["V4"] = _res(_grade(pe / med, V_PEER_PE_GOOD, V_PEER_PE_OK, higher=False), pe / med, f"P/E {pe:.1f} vs median {med:.1f} of {k} peers")

    # ---- trend & strength (the day's snapshot; the built-in screens' own conditions)
    nosnap = "not in the day's stock snapshot"
    ok2, miss = _screen(ev, "stage2")
    if ok2 is None:
        out["T1"] = _na(nosnap)
    else:
        out["T1"] = _res("good" if ok2 else "ok" if len(miss) <= T_STAGE2_NEAR else "bad", "passes" if ok2 else f"misses {len(miss)}",
                         "" if ok2 else "fails: " + "; ".join(miss))
    rs = _num(s.get("rs_rank"))
    out["T2"] = _res(_grade(rs, T_RS_GOOD, T_RS_OK), rs) if rs is not None else _na(nosnap)
    grs = _num(s.get("peer_rs"))
    out["T3"] = _res(_grade(grs, T_GROUP_RS_GOOD, T_GROUP_RS_OK), grs,
                     f"{s.get('peer_group')}; #{int(s['peer_rank'])} of {int(s['peer_count'])} in it" if _num(s.get("peer_rank")) else s.get("peer_group") or "") \
        if grs is not None else _na("no peer-group rating")
    rel = _num(s.get("rel_r12m"))
    out["T4"] = _res("good" if rel > 0 else "ok" if rel >= T_REL_12M_OK else "bad", rel,
                     f"return {s.get('r12m'):+.0f}%" if _num(s.get("r12m")) is not None else "") if rel is not None else _na(nosnap)
    ok5, miss5 = _screen(ev, "uptrend")
    if ok5 is None:
        out["T5"] = _na(nosnap)
    else:
        out["T5"] = _res("good" if ok5 else "ok" if s.get("weekly_uptrend") else "bad",
                         "passes" if ok5 else "weekly uptrend" if s.get("weekly_uptrend") else "no", "" if ok5 else "fails: " + "; ".join(miss5))

    # ---- risk
    atr = _num(s.get("atr_pct"))
    out["R1"] = _res(_grade(atr, R_ATR_GOOD, R_ATR_OK, higher=False), atr) if atr is not None else _na(nosnap)
    mdd = _num(s.get("mdd_2y"))
    out["R2"] = _res(_grade(mdd, R_MDD_GOOD, R_MDD_OK), mdd) if mdd is not None else _na(nosnap)
    tr = s.get("tradable")
    out["R3"] = _na(nosnap) if tr is None else _res("good" if tr else "bad", "yes" if tr else "no")
    ed = _num(s.get("earnings_days"))
    out["R4"] = _na("no results date stored") if ed is None or ed < 0 else _res(
        "good" if ed > R_EARNINGS_SOON else "ok", int(ed), "days to the next results")
    if not has_fin:
        out["R5"] = _na(nofin)
    else:
        latest = co.get("latest") or {}
        out["R5"] = _res("bad" if latest.get("stale") else "good", latest.get("end"), "latest quarter's end"
                         + (f", filed {latest['filed']}" if latest.get("filed") else ""))
    return out


def summarise(results: dict) -> dict:
    """Pillar ratings, the overall evidence score and the red flags from evaluate()'s results."""
    pillars = {}
    for k in PILLAR_KEYS:
        st = [r["status"] for c, r in results.items() if CHECK_PILLAR.get(c) == k]
        g, o, b = st.count("good"), st.count("ok"), st.count("bad")
        n = g + o + b
        score = (g + o / 2) / n if n else None
        rating = ("No data" if n == 0 and any(x == "na" for x in st) else None if n == 0
                  else "Thin" if n < MIN_SCORED else "Strong" if score >= STRONG_MIN else "Mixed" if score >= MIXED_MIN else "Weak")
        pillars[k] = {"good": g, "ok": o, "bad": b, "na": st.count("na"), "score": score, "rating": rating}
    rated = [p["score"] for p in pillars.values() if p["rating"] in ("Strong", "Mixed", "Weak")]
    flags = [{"code": c, "label": next(x[2] for x in CHECKS_DOC if x[0] == c), "detail": results[c].get("detail") or ""}
             for c in RED_FLAGS if (results.get(c) or {}).get("status") == "bad"]
    return {"pillars": pillars, "score": round(100 * sum(rated) / len(rated)) if rated else None, "rated": len(rated), "flags": flags}


def check_formats() -> dict:
    return {c[0]: c[5] for c in CHECKS_DOC}
