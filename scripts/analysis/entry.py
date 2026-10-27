"""The entry framework: is NOW a good time to buy this stock? Time-bound and market-dependent.

The company framework (framework.py) asks whether the business is worth owning; it changes with each set of
results. This one asks whether the market, the stock's group and its chart make this session a low-risk
entry — it changes daily, so it is always read AS OF one session (`evidence.gather_entry`), and a past
session reads only what was known then (the stock's own fields are recomputed from its bars up to it).

Six pillars, in the order a trader works down to an entry: market → sector & group → trend → setup →
entry point → event risk. As in the company framework each pillar has CHECKS over stored data (good / ok /
bad / n/a, thresholds as module constants rendered into the rule text) and QUESTIONS for your judgement,
and the same rating rule (`framework.summarise`). Checks reuse the app's own rules: the market gates are
the strategies' (`backtesting/spec.py` `market_ok`), distribution days and up/down volume CAN SLIM's
constants, the Trend Template the stage2 screen's conditions, the stage Weinstein's state machine
(`strategies/stage_analysis.py`), patterns the chart_pattern strategy's detectors, levels
`core/sr_levels.py`.

REFERENCE LEVELS (`levels`) list the prices the chart offers for a plan — the base's high, a pattern's
trigger and invalidation, the nearest support and resistance, the 50-day, an ATR stop. They are labelled
as reference, never a recommendation: the PLAN (entry, stop, target, size) and the decision are yours.

A change to a check, threshold or question bumps VERSION and adds a CHANGELOG entry.
"""

from __future__ import annotations

from fundamentals import canslim as _cs

from . import framework as _fw

VERSION = "1.0"
CHANGELOG = (
    ("1.0", "2026-10-27", "First entry framework: six pillars (market, sector & group, trend, setup, entry point, event "
                          "risk), 25 data checks, 8 questions, reference levels and a plan."),
)

# ---------------------------------------------------------------- thresholds
# market
M_BREADTH_GOOD = 60.0          # M3: % of the most-traded stocks above their 50-day
M_BREADTH_OK = 40.0
M_DIST_GOOD = 2                # M4: distribution days in CAN SLIM's window; ok up to its DIST_MAX
M_INDEX_BELOW_HIGH_GOOD = 0.05  # M5: the index at most this far below its 52-week high
M_INDEX_BELOW_HIGH_OK = 0.10
# sector & group
S_GROUP_RS_GOOD = 70           # S1: the peer group's RS rating
S_GROUP_RS_OK = 40
S_GROUP_TREND_PTS = 5          # S2: group RS up (or down) this many points on a month earlier is a trend
S_GROUP_BREADTH_GOOD = 0.60    # S3: share of the group's tradable stocks above their 50-day
S_GROUP_BREADTH_OK = 0.40
S_LEADER_TOP = 3               # S4: among the group's top N by RS rank (good), or its top half (ok)
# trend
T_STAGE2_NEAR = 2              # T1: missing at most this many Trend Template conditions reads as "close"
T_RS_GOOD = 80                 # T3: RS rank
T_RS_OK = 60
T_REL_3M_OK = -5.0             # T4: 3-month return vs the benchmark, points; ok down to this
# setup
P_BASE_MIN_DAYS = 25           # P1: a base of at least this many sessions (about five weeks) ...
P_BASE_MAX_DEPTH = 35.0        # ... no deeper than this % (the snapshot's base window tops out at its own limit)
P_DRYUP_GOOD = 0.8             # P4: volume over the last 10 sessions vs its 50-day average
P_DRYUP_OK = 1.0
P_UPDOWN_GOOD = 1.25           # P5: up-day / down-day volume (CAN SLIM's window); ok from its UPDOWN_MIN
# entry point
L_PIVOT_NEAR = 0.05            # L1: close within this below the pivot (the base's high) is at the pivot (good) ...
L_PIVOT_BELOW_OK = 0.15        # ... at most this far below is still setting up (ok). The base window ends on the
                               # session itself, so the close is never above it: extension is L2's to judge
L_EXT50_GOOD = 0.10            # L2: close above the 50-day by at most this (good) ...
L_EXT50_OK = 0.20              # ... or this (ok); further is extended
L_RISK_GOOD = 0.07             # L3: close to the nearest support's low, as a share of the close
L_RISK_OK = 0.10
L_REWARD_GOOD = 3.0            # L4: room to the nearest resistance ÷ risk to the nearest support
L_REWARD_OK = 1.5
L_ATR_STOP = 2.0               # reference level: an initial stop this many ATRs below the close
# event risk
R_RESULTS_BAD = 5              # R1: results within this many days is a gap risk (bad) ...
R_RESULTS_OK = 14              # ... within this many, ok; further, good
R_ATR_GOOD = 3.0               # R3: ATR as % of the close
R_ATR_OK = 5.0

PILLARS = (
    ("market", "Market", "Is the market letting breakouts work?"),
    ("sector", "Sector & group", "Is money flowing into its group, and is it one of the group's leaders?"),
    ("trend", "Trend", "Is the stock itself in a confirmed uptrend, and outperforming?"),
    ("setup", "Setup", "Is there a proper base or pattern, with supply drying up?"),
    ("location", "Entry point", "Is the price at a low-risk entry — near the pivot, with a close stop and room above?"),
    ("event", "Event risk", "What could gap it before a stop can work?"),
)
PILLAR_KEYS = tuple(p[0] for p in PILLARS)

QUESTIONS = (
    ("MQ1", "market", "Are breakouts working in this market right now?",
     "Recent breakouts in your watchlist: following through, or failing within days? Leaders holding up?"),
    ("SQ1", "sector", "Why is money moving into this group?",
     "A theme, the cycle, policy, a commodity price, news. Is it early or late in the group's run?"),
    ("TQ1", "trend", "Where is it in its advance — early or late?",
     "Its first or second base since the uptrend began is early; a fourth, wide and loose, is late."),
    ("PQ1", "setup", "Is the base constructive?",
     "Tight weekly closes, contractions getting smaller, shakeouts below a low that recover, volume drying up on the right side."),
    ("LQ1", "location", "Where exactly is your entry, and what invalidates the setup?",
     "The trigger price and the volume you want on it; the price that says the setup has failed."),
    ("LQ2", "location", "What is the reward worth to you against the risk?",
     "Your target or the next resistance; whether the stop is tight enough to size properly."),
    ("RQ1", "event", "What could gap it before your stop works?",
     "Results, a regulator, a trial readout, a macro release, the index's own events."),
    ("RQ2", "event", "How does it fit what you already hold?",
     "Same sector or theme, correlation, how much of your risk is already on."),
)

DECISIONS = ("Buy now", "Buy on trigger", "Wait", "Pass")
PLAN_FIELDS = (
    ("decision", "Decision", "One of: " + ", ".join(DECISIONS) + "."),
    ("conviction", "Conviction", "1 (a hunch) to 5 (would size up)."),
    ("entry", "Entry", "The price you buy at — a trigger above the pivot, or the close."),
    ("stop", "Stop", "Where the setup is wrong: below the base, a support, or the pattern's invalidation."),
    ("target", "Target", "A first target: the next resistance, a measured move, or a multiple of the risk."),
    ("account", "Account size", "To size the position from your risk per trade."),
    ("risk_pct", "Risk per trade %", "The share of the account you lose if the stop is hit."),
    ("note", "Notes", "What you are waiting for, or why you passed."),
    ("valid_until", "Valid until", "When the plan expires if the trigger has not come."),
)
RED_FLAGS = ("M1", "S1", "T2", "L1", "L2", "R1")

# (code, pillar, label, rule, why, value format) — formats as in framework.CHECKS_DOC
CHECKS_DOC = (
    ("M1", "market", "Market gate", "The SEPA market test the strategies buy under: the benchmark above its rising "
     "{MKT_INDEX_SMA}-day average, with breadth above {MKT_BREADTH_MIN_PCT:g}% or rising.",
     "Most breakouts fail in a falling market, however good the stock.", "text"),
    ("M2", "market", "Long-term trend", "The benchmark above its 200-day, with the 50-day above the 200-day.",
     "Whether this is a bull market at all, not just a bounce.", "text"),
    ("M3", "market", "Breadth", "Share of the most-traded stocks above their 50-day at least {M_BREADTH_GOOD:g}% "
     "(ok from {M_BREADTH_OK:g}%).", "A rally carried by few stocks gives few winners.", "pct_raw"),
    ("M4", "market", "Distribution days", "Distribution days in the last {DIST_SESSIONS} sessions at most {M_DIST_GOOD} "
     "(ok up to {DIST_MAX}).", "Heavy selling by institutions shows up as down days on rising volume.", "num"),
    ("M5", "market", "Index near its high", "The benchmark at most {M_INDEX_BELOW_HIGH_GOOD:.0%} below its 52-week high "
     "(ok to {M_INDEX_BELOW_HIGH_OK:.0%}).", "Leaders break out when the market itself is near highs.", "pct"),
    ("S1", "sector", "Group strength", "The peer group's RS rating at least {S_GROUP_RS_GOOD} (ok from {S_GROUP_RS_OK}).",
     "Half of a stock's move comes from its group.", "num"),
    ("S2", "sector", "Group momentum", "The group's RS rating up at least {S_GROUP_TREND_PTS} points on a month earlier "
     "(good), down as much (bad), else ok.", "Money rotating in, not out.", "pp_raw"),
    ("S3", "sector", "Group breadth", "At least {S_GROUP_BREADTH_GOOD:.0%} of the group's stocks above their 50-day "
     "(ok from {S_GROUP_BREADTH_OK:.0%}).", "A group move many stocks share is more durable than one stock's.", "pct"),
    ("S4", "sector", "Leader in its group", "Among the group's top {S_LEADER_TOP} by RS rank (good), or its top half (ok).",
     "Buy the group's leader, not its laggard.", "text"),
    ("T1", "trend", "Stage 2 Trend Template", "Passes the Stage 2 — Trend Template screen (good); missing at most "
     "{T_STAGE2_NEAR} of its conditions (ok).", "The stock's own uptrend, by Minervini's checklist.", "text"),
    ("T2", "trend", "Weinstein stage", "Stage 2, an advance (good); stage 1, a base (ok); stage 3 or 4 (bad) — the weekly "
     "stage machine the Stage analysis indicator draws.", "Buy in stage 2, never in 3 or 4.", "text"),
    ("T3", "trend", "RS rank", "Relative strength rank at least {T_RS_GOOD} (ok from {T_RS_OK}).",
     "Leaders are already outperforming before their big move.", "num"),
    ("T4", "trend", "Recent relative strength", "3-month return ahead of the benchmark (good), or no more than "
     "{T_REL_3M_OK:g} points behind (ok).", "Still leading now, not only over the year.", "pp_raw"),
    ("P1", "setup", "Base", "A base of at least {P_BASE_MIN_DAYS} sessions no deeper than {P_BASE_MAX_DEPTH:g}% "
     "(the snapshot's base window).", "A base digests the last advance before the next.", "text"),
    ("P2", "setup", "Contraction", "Price swings contracting into the right side of the base (the snapshot's VCP test).",
     "Tighter swings mean sellers are running out.", "text"),
    ("P3", "setup", "Chart pattern", "A bullish pattern the chart_pattern strategy would trade (good) or one it would "
     "not (ok); a topping pattern is bad.", "A named pattern gives a trigger and an invalidation price.", "text"),
    ("P4", "setup", "Volume drying up", "Volume over the last 10 sessions at most {P_DRYUP_GOOD:.0%} of its 50-day "
     "average (ok to {P_DRYUP_OK:.0%}).", "Quiet volume in the base: no one left wanting to sell.", "pct"),
    ("P5", "setup", "Accumulation", "Up-day volume at least {P_UPDOWN_GOOD:g}× down-day volume over {UPDOWN_SESSIONS} "
     "sessions (ok from {UPDOWN_MIN:g}×).", "Institutions buying leave heavier volume on up days.", "x"),
    ("L1", "location", "Distance from pivot", "Close within {L_PIVOT_NEAR:.0%} of the base's high (good), up to "
     "{L_PIVOT_BELOW_OK:.0%} below it (ok); further below is not at an entry yet (bad).",
     "Buying near the pivot keeps the stop close and the reward large.", "pct"),
    ("L2", "location", "Extension from the 50-day", "Close at most {L_EXT50_GOOD:.0%} above the 50-day (good), "
     "{L_EXT50_OK:.0%} (ok); below the 50-day is ok.", "Far above the average, a normal pullback is a big loss.", "pct"),
    ("L3", "location", "Risk to support", "The nearest support's low at most {L_RISK_GOOD:.0%} below the close "
     "(ok to {L_RISK_OK:.0%}).", "A stop under real support, close enough to keep a loss small.", "pct"),
    ("L4", "location", "Room to resistance", "Room to the nearest resistance at least {L_REWARD_GOOD:g}× the risk to "
     "support (ok from {L_REWARD_OK:g}×); no resistance overhead is good.", "Enough upside before sellers wait.", "x"),
    ("R1", "event", "Results soon", "Next results more than {R_RESULTS_OK} days away (good), more than {R_RESULTS_BAD} "
     "(ok); sooner is bad.", "A results gap jumps straight through a stop.", "num"),
    ("R2", "event", "Liquidity", "Clears the market's tradable floor (price, traded value, a year of history).",
     "Whether your stop fills near its price.", "text"),
    ("R3", "event", "Volatility", "Average true range at most {R_ATR_GOOD:g}% of the price (ok to {R_ATR_OK:g}%).",
     "Sets how wide the stop must be, and so the size.", "pct_raw"),
)
CHECK_PILLAR = {c[0]: c[1] for c in CHECKS_DOC}


def _consts() -> dict:
    from swing_screener.strategies import minervini_spec as ms
    return {"MKT_INDEX_SMA": ms.MKT_INDEX_SMA, "MKT_BREADTH_MIN_PCT": ms.MKT_BREADTH_MIN_PCT,
            **{k: getattr(_cs, k) for k in ("DIST_SESSIONS", "DIST_MAX", "UPDOWN_SESSIONS", "UPDOWN_MIN")},
            **{k: v for k, v in globals().items() if k.isupper() and not k.startswith("_")}}


def _fmt(text: str) -> str:
    return text.format(**_consts())


def criteria() -> dict:
    return {
        "version": VERSION, "changelog": [{"version": v, "date": d, "text": t} for v, d, t in CHANGELOG],
        "pillars": [{"key": k, "name": n, "question": q,
                     "checks": [{"code": c, "label": lab, "rule": _fmt(rule), "why": why} for c, p, lab, rule, why, _ in CHECKS_DOC if p == k],
                     "questions": [{"code": c, "question": qq, "hint": h} for c, p, qq, h in QUESTIONS if p == k]}
                    for k, n, q in PILLARS],
        "plan": [{"key": k, "label": lab, "hint": h} for k, lab, h in PLAN_FIELDS],
        "decisions": list(DECISIONS), "ratings": list(_fw.RATINGS), "red_flags": list(RED_FLAGS),
        "formats": {c[0]: c[5] for c in CHECKS_DOC},
        "caveats": (
            "Read as of one session. The stock's own fields, its group's breadth and the group's RS rating are "
            "point in time; the group is today's classification (a company rarely changes business). RS rank and the "
            "stock's place in its group come from the latest snapshot on or before the date (shown) — month-end only "
            "before the daily snapshots start.",
            "The market gates are the ones the strategies use to allow new buys; breadth starts where the stored breadth does.",
            "Support, resistance and patterns are the chart indicators' own rules on the bars up to that session.",
            "Reference levels are prices the chart offers for a plan, not a recommendation. The plan is yours.",
            "Not investment advice.",
        ),
    }


def _res(st, v=None, d=""):
    return {"status": st, "value": v, "detail": d}


def evaluate(ev: dict) -> dict:
    """evidence.gather_entry() -> {code: {status, value, detail}}."""
    g, n = _fw._grade, _fw._num
    row, xs, mk, grp = ev.get("row") or {}, ev.get("xs") or {}, ev.get("market_state") or {}, ev.get("group") or {}
    close = ev.get("close")
    out: dict[str, dict] = {}
    na = lambda d: _res("na", None, d)  # noqa: E731

    # ---- market
    gate, trend = mk.get("gate"), mk.get("trend")
    out["M1"] = na("no benchmark stored") if gate is None else _res("good" if gate else "bad", "buys allowed" if gate else "risk off",
                                                                    mk.get("index") or "")
    out["M2"] = na("no benchmark stored") if trend is None else _res("good" if trend else "bad", "uptrend" if trend else "not in an uptrend")
    b = mk.get("breadth")
    then = mk.get("breadth_then")
    out["M3"] = na("no breadth stored for the date") if b is None else _res(
        g(b, M_BREADTH_GOOD, M_BREADTH_OK), b, "" if then is None else f"{'rising' if b > then else 'falling' if b < then else 'flat'} "
                                                f"from {then:.0f}% two weeks earlier")
    dd = mk.get("dist_days")
    out["M4"] = na("no benchmark stored") if dd is None else _res(g(dd, M_DIST_GOOD, _cs.DIST_MAX, higher=False), dd,
                                                                  f"in {_cs.DIST_SESSIONS} sessions")
    fh = mk.get("index_from_high")
    out["M5"] = na("no benchmark stored") if fh is None else _res(g(-fh, M_INDEX_BELOW_HIGH_GOOD, M_INDEX_BELOW_HIGH_OK, higher=False), fh,
                                                                  f"{mk.get('index') or 'index'} vs its 52-week high")

    # ---- sector & group (the snapshot on or before the date)
    snapd = xs.get("snapshot_date")
    grs = n(grp.get("rs"))
    out["S1"] = na("no group rating stored for the date" if grp else "no peer group") if grs is None else _res(
        g(grs, S_GROUP_RS_GOOD, S_GROUP_RS_OK), grs, f"{grp.get('name')} on {grp.get('rs_date')}")
    then = grp.get("rs_then")
    if grs is None or then is None:
        out["S2"] = na("no earlier group rating")
    else:
        d = grs - then
        out["S2"] = _res("good" if d >= S_GROUP_TREND_PTS else "bad" if d <= -S_GROUP_TREND_PTS else "ok", d, f"{then:.0f} → {grs:.0f} since {grp.get('then')}")
    ab = grp.get("above50")
    out["S3"] = na("no peer group") if ab is None else _res(g(ab, S_GROUP_BREADTH_GOOD, S_GROUP_BREADTH_OK), ab,
                                                            f"of {grp.get('n')} stocks (the group's members today)")
    pr, pc = n(xs.get("peer_rank")), n(xs.get("peer_count"))
    if pr is None or not pc:
        out["S4"] = na("no rank in a peer group")
    else:
        out["S4"] = _res("good" if pr <= S_LEADER_TOP else "ok" if pr <= pc / 2 else "bad", f"#{int(pr)} of {int(pc)}",
                         f"by RS rank, snapshot {snapd}")

    # ---- trend
    ok1, miss = _fw._screen({"frame": ev.get("frame")}, "stage2")
    if ok1 is None:
        out["T1"] = na("no price history")
    else:
        rs_missing = xs.get("rs_rank") is None
        out["T1"] = _res("good" if ok1 else "ok" if len(miss) <= T_STAGE2_NEAR else "bad", "passes" if ok1 else f"misses {len(miss)}",
                         ("" if ok1 else "fails: " + "; ".join(miss)) + (" (no RS rank on the date)" if rs_missing else ""))
    stg = ev.get("stage") or {}
    s = stg.get("stage")
    out["T2"] = na("needs more weekly history") if not s else _res(
        {2: "good", 1: "ok"}.get(s, "bad"), f"stage {s}", {1: "basing", 2: "advancing", 3: "topping", 4: "declining"}[s]
        + f"; 30-week line {stg.get('line')}")
    rs = n(xs.get("rs_rank"))
    out["T3"] = na("not in the snapshot") if rs is None else _res(g(rs, T_RS_GOOD, T_RS_OK), rs, f"snapshot {snapd}")
    rel = n(row.get("rel_r3m"))
    out["T4"] = na("no benchmark history") if rel is None else _res("good" if rel > 0 else "ok" if rel >= T_REL_3M_OK else "bad", rel,
                                                                    f"return {row['r3m']:+.0f}% over 3 months")

    # ---- setup
    bd, depth = n(row.get("base_days")), n(row.get("base_depth_pct"))
    if not bd:
        out["P1"] = _res("bad", "no base", "price has not held a range")
    else:
        okb = bd >= P_BASE_MIN_DAYS and (depth is None or depth <= P_BASE_MAX_DEPTH)
        out["P1"] = _res("good" if okb else "ok", f"{int(bd)} sessions", f"{depth:.0f}% deep" if depth is not None else "")
    rc = row.get("range_contracting")
    out["P2"] = na("no price history") if rc is None else _res("good" if rc else "ok", "contracting" if rc else "not contracting")
    pats = ev.get("patterns") or []
    bull = [p for p in pats if p.get("direction") == "bullish"]
    bear = [p for p in pats if p.get("direction") != "bullish"]
    if bear and not any(p.get("tradeable") for p in bull):
        out["P3"] = _res("bad", bear[0]["name"], "a topping pattern")
    elif bull:
        p = next((x for x in bull if x.get("tradeable")), bull[0])
        out["P3"] = _res("good" if p.get("tradeable") else "ok", p["name"],
                         f"{p.get('state') or ''}; trigger {p['trigger']:.2f}" if p.get("trigger") else (p.get("state") or ""))
    else:
        out["P3"] = _res("ok", "none", "no pattern the detectors recognise")
    vol = ev.get("volume") or {}
    if vol.get("avg50"):
        r = vol["recent"] / vol["avg50"]
        out["P4"] = _res(g(r, P_DRYUP_GOOD, P_DRYUP_OK, higher=False), r, "last 10 sessions vs the 50-day average")
    else:
        out["P4"] = na("no volume average")
    ud = vol.get("updown")
    out["P5"] = na("no volume") if ud is None else _res(g(min(ud, 99.0), P_UPDOWN_GOOD, _cs.UPDOWN_MIN), min(ud, 99.0),
                                                        f"over {_cs.UPDOWN_SESSIONS} sessions")

    # ---- entry point
    pb = n(row.get("pct_below_base_high"))
    if pb is None:
        out["L1"] = na("no base, so no pivot")
    else:
        d = -pb / 100   # close vs the base's high: negative below it
        out["L1"] = _res(g(d, -L_PIVOT_NEAR, -L_PIVOT_BELOW_OK), d, "close vs the base's high")
    e50 = n(row.get("pct_vs_sma50"))
    if e50 is None:
        out["L2"] = na("no 50-day yet")
    else:
        e = e50 / 100
        out["L2"] = _res("ok" if e < 0 else g(e, L_EXT50_GOOD, L_EXT50_OK, higher=False), e, "below the 50-day" if e < 0 else "above the 50-day")
    sup, res = ev.get("support") or [], ev.get("resistance") or []
    risk = (close - sup[0]["bottom"]) / close if sup and close else None
    out["L3"] = na("no support zone below") if risk is None else _res(g(risk, L_RISK_GOOD, L_RISK_OK, higher=False), risk,
                                                                     f"{sup[0]['tf']} {sup[0]['role']} {sup[0]['bottom']:.2f}–{sup[0]['top']:.2f}")
    if risk is None or risk <= 0:
        out["L4"] = na("needs a support below")
    elif not res:
        out["L4"] = _res("good", None, "no resistance overhead in view")
    else:
        rr = (res[0]["bottom"] - close) / close / risk
        out["L4"] = _res(g(rr, L_REWARD_GOOD, L_REWARD_OK), rr, f"resistance from {res[0]['bottom']:.2f}")

    # ---- event risk
    nd = ev.get("results_in_days")
    out["R1"] = na("no next results date stored") if nd is None else _res(
        "good" if nd > R_RESULTS_OK else "ok" if nd > R_RESULTS_BAD else "bad", nd, "days to the next results")
    tr = row.get("tradable")
    out["R2"] = na("no price history") if tr is None else _res("good" if tr else "bad", "yes" if tr else "no")
    atr = n(row.get("atr_pct"))
    out["R3"] = na("no ATR") if atr is None else _res(g(atr, R_ATR_GOOD, R_ATR_OK, higher=False), atr)
    return out


def summarise(results: dict) -> dict:
    return _fw.summarise(results, CHECKS_DOC, PILLAR_KEYS, RED_FLAGS)


def levels(ev: dict) -> list[dict]:
    """Reference prices for a plan, each with what it is and where it comes from — never a recommendation."""
    row, close, atr = ev.get("row") or {}, ev.get("close"), ev.get("atr")
    out = []
    pb = _fw._num(row.get("pct_below_base_high"))
    if pb is not None and close:
        out.append({"kind": "entry", "label": "Base high (pivot)", "price": close / (1 - pb / 100), "source": "snapshot base window"})
    for p in ev.get("patterns") or []:
        if p.get("direction") == "bullish":
            for k, kind, lab in (("trigger", "entry", "trigger"), ("invalidation", "stop", "invalidation"), ("target", "target", "measured target")):
                if p.get(k):
                    out.append({"kind": kind, "label": f"{p['name']} {lab}", "price": float(p[k]), "source": "chart-pattern detector"})
            break
    for z in (ev.get("support") or [])[:2]:
        out.append({"kind": "stop", "label": f"Support ({z['tf']}, {'strong' if z.get('strong') else 'graded'})", "price": float(z["bottom"]),
                    "source": f"zone {z['bottom']:.2f}–{z['top']:.2f}"})
    for z in (ev.get("resistance") or [])[:2]:
        out.append({"kind": "target", "label": f"Resistance ({z['tf']}, {'strong' if z.get('strong') else 'graded'})", "price": float(z["bottom"]),
                    "source": f"zone {z['bottom']:.2f}–{z['top']:.2f}"})
    if row.get("sma50"):
        out.append({"kind": "stop", "label": "50-day average", "price": float(row["sma50"]), "source": "moving average"})
    if atr and close:
        out.append({"kind": "stop", "label": f"{L_ATR_STOP:g} ATR below the close", "price": close - L_ATR_STOP * atr, "source": "ATR(14)"})
    # a stop belongs below the close and a target above it: a level on the wrong side is not offered as one
    out = [x for x in out if not close or (x["kind"] != "stop" or x["price"] < close) and (x["kind"] != "target" or x["price"] > close)]
    for x in out:
        x["vs_close"] = x["price"] / close - 1 if close else None
    return out
