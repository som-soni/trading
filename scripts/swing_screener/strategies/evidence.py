"""How credible each strategy's idea is OUTSIDE this repo — the grades of research/strategy-catalog-swing.md.

Two numbers, both about public evidence, never about this repo's own backtests (those are the edge dots):

* **grade** (A–E) — what published tests of the setup found, the catalogue's sort key:
  A works after costs in independent tests outside the original sample; B works in published tests but
  in-sample, before costs or unreplicated; C mixed, or weaker since publication; D never tested (anecdote,
  chart examples, a trader's record); E tested and failed.
* **credibility** (0–5) — computed, not asserted, from four parts:
  ``evidence`` 2 = peer-reviewed study of the underlying effect, 1 = published backtest with full rules,
  0 = examples or track record only; ``replicated`` +1 if it held up independently or after publication;
  ``testable`` +1 if the rules code without judgment; ``costs`` +1 if it still pays after realistic costs.
  A setup tested and failed (grade E) is capped at 1.

A trader's contest win is a record, not a test of one setup: it earns no evidence points. Every strategy
the Strategies page lists must have an entry — docs.check() (tests/test_strategy_docs.py) fails otherwise,
so a new strategy is graded when it is added.
"""

GRADES = {
    "A": "Works after costs in independent tests outside the original sample",
    "B": "Works in published tests, but in-sample, before costs or not replicated",
    "C": "Mixed results, or weaker since it was published",
    "D": "Never properly tested: chart examples, anecdote or a trader's record",
    "E": "Tested and failed",
}

CREDIBILITY_PARTS = (
    ("evidence", "Peer-reviewed study of the effect (2), published backtest with full rules (1), examples only (0)"),
    ("replicated", "Held up in independent tests or after publication"),
    ("testable", "Rules can be coded without judgment calls"),
    ("costs", "Still pays after realistic costs"),
)
FAILED_CAP = 1


def _e(grade: str, evidence: int, replicated: int, testable: int, costs: int, basis: str) -> dict:
    return {"grade": grade, "evidence": evidence, "replicated": replicated, "testable": testable,
            "costs": costs, "basis": basis}


EVIDENCE = {
    # continuation -- relative-strength rank
    "momentum_baseline": _e("A", 2, 1, 1, 1, "Cross-sectional momentum: Jegadeesh & Titman (1993), replicated across markets and decades."),
    "momentum_vol_scaled": _e("A", 2, 1, 1, 1, "Cross-sectional momentum (Jegadeesh & Titman 1993) with volatility scaling (Barroso & Santa-Clara 2015)."),
    "momentum_dual_combo": _e("B", 2, 0, 1, 1, "Combines cross-sectional momentum (Jegadeesh & Titman 1993) with Antonacci's dual momentum; the blend itself is unpublished."),
    "quality_momentum": _e("B", 2, 0, 1, 1, "Momentum filtered by quality: both effects are documented (Jegadeesh & Titman 1993; Asness et al. on quality), the combination less so."),
    "sector_rotation": _e("B", 2, 1, 1, 0, "Industry momentum: Moskowitz & Grinblatt (1999); Faber's sector rotation."),
    "dual_momentum": _e("C", 1, 0, 1, 1, "Antonacci, Dual Momentum Investing (2014): published backtests, results since publication mixed."),
    "rs_leaders": _e("D", 0, 0, 1, 0, "IBD / Minervini relative-strength leadership: practitioner examples, no published test of the setup."),
    # continuation -- breakout from a base
    "minervini": _e("D", 0, 0, 1, 0, "Minervini's SEPA / VCP: US Investing Championship 1997 record and chart examples; no published test of the setup."),
    "chart_pattern": _e("B", 1, 0, 1, 0, "Classic base patterns: Bulkowski's pattern statistics (own samples, no costs); Lo, Mamaysky & Wang (2000) found some information content."),
    "kullamagi": _e("D", 0, 0, 1, 0, "Kristjan Kullamägi's breakouts: public account statements (not audited) and examples; no published test."),
    "darvas": _e("D", 0, 0, 1, 0, "Nicolas Darvas, How I Made $2,000,000 in the Stock Market (1960): a personal account."),
    "stage_analysis": _e("D", 0, 0, 1, 0, "Stan Weinstein, Secrets for Profiting in Bull and Bear Markets (1988): examples, no published test."),
    "donchian": _e("C", 2, 0, 1, 0, "Channel breakouts: Brock, Lakonishok & LeBaron (1992) found trading-range rules worked; Sullivan, Timmermann & White (1999) found it faded after data-snooping and out of sample."),
    "breakout": _e("E", 1, 0, 1, 0, "The volume-surge breakout of swing blogs: tested here and in public trading-rule studies without a lasting edge after costs."),
    # continuation -- pullback in trend
    "trend_pullback": _e("D", 0, 0, 1, 0, "A common swing rule (dip to the 20-day inside an uptrend): blog and video examples, no published test."),
    "kell_cycle": _e("D", 0, 0, 1, 0, "Oliver Kell, Victory in Stock Trading: US Investing Championship 2020 record and examples; no published test."),
    # continuation -- burst
    "momentum_burst": _e("D", 0, 0, 1, 0, "Pradeep Bonde (Stockbee): the 4% momentum burst, shared as examples and scans; no published test."),
    "etf_swing": _e("D", 0, 0, 1, 0, "A swing breakout system applied to ETFs: practitioner idea, no published test."),
    # trend following
    "turtle_trend": _e("A", 2, 1, 1, 1, "Time-series momentum on futures: Moskowitz, Ooi & Pedersen (2012); Hurst, Ooi & Pedersen (2017), a century of evidence."),
    "ma_trend": _e("C", 2, 0, 1, 1, "Faber (2007) 10-month average timing; Brock, Lakonishok & LeBaron (1992). Strong in published samples, weaker since."),
    "masonson_tqqq": _e("D", 1, 0, 1, 0, "Masonson's leveraged-ETF timing: a book's own backtests, no independent test."),
    "boucher_stocks": _e("D", 1, 0, 1, 0, "Mark Boucher, The Hedge Fund Edge (1999): the author's own model backtests, no independent test."),
    "boucher_bonds_gold": _e("D", 1, 0, 1, 0, "Mark Boucher, The Hedge Fund Edge (1999): the author's own model backtests, no independent test."),
    "boucher_book": _e("D", 1, 0, 1, 0, "Mark Boucher, The Hedge Fund Edge (1999): the author's own model backtests, no independent test."),
    # snap-back
    "stock_reversion": _e("C", 1, 0, 1, 0, "Connors-style oversold buying in single stocks: published backtests; the underlying short-term reversal (Jegadeesh 1990, Lehmann 1990) is real, but costs take most of it."),
    "mean_reversion": _e("C", 1, 0, 1, 1, "Connors & Alvarez, Short Term Trading Strategies That Work (2008): RSI(2), %b and Double 7s on indices; weaker since publication."),
    # event
    "pead": _e("C", 2, 1, 1, 0, "Post-earnings drift: Bernard & Thomas (1989, 1990); Chan, Jegadeesh & Lakonishok (1996). Much weaker in US large caps since the 2000s."),
    "earnings_gaps": _e("B", 2, 0, 1, 0, "Earnings-gap continuation: rests on post-earnings drift (Bernard & Thomas 1989) and Stockbee's episodic pivot."),
    # fade
    "turtle_soup": _e("D", 1, 0, 1, 0, "Raschke & Connors, Street Smarts (1995): full rules and chart examples, no independent published test."),
    # short side
    "parabolic_short": _e("D", 0, 0, 1, 0, "Kullamägi's parabolic short: examples, no published test."),
    "stage4_shorts": _e("D", 0, 0, 1, 0, "Weinstein's stage 4 short (1988): examples, no published test."),
    # income and value
    "fno_income": _e("A", 2, 1, 1, 0, "The variance risk premium: index options price more movement than arrives (Carr & Wu 2009; Bakshi & Kapadia 2003). Tail losses make costs and sizing decisive."),
    "value_ranking": _e("B", 2, 1, 1, 1, "The value premium: Fama & French (1992); Lakonishok, Shleifer & Vishny (1994). Long drawdown since 2007 in the US, hence B."),
    "quality": _e("B", 2, 1, 1, 1, "Quality / profitability: Novy-Marx (2013); Asness, Frazzini & Pedersen, Quality Minus Junk."),
}


def credibility(e: dict) -> int:
    score = e["evidence"] + e["replicated"] + e["testable"] + e["costs"]
    return min(score, FAILED_CAP) if e["grade"] == "E" else score


def evidence_for(key: str) -> dict:
    """The fields the Strategies page shows: grade, its meaning, the computed score and its parts."""
    e = EVIDENCE.get(key)
    if not e:
        return {"evidence": None}
    return {"evidence": {**e, "grade_label": GRADES[e["grade"]], "credibility": credibility(e),
                         "parts": [{"key": k, "label": lab, "points": e[k]} for k, lab in CREDIBILITY_PARTS]}}
