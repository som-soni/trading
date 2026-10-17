"""A strategy's trade setups over a stretch of history, for the chart's Trade setups layer.

Generic over every strategy, because it adds no rules of its own: it runs the strategy's own
`prefilter_mask`, `evaluate`, `entry_signal_fired`, `build_plans`, `classify` and drawing, bar by bar,
exactly as the backtest's scan does (backtest._signals_for), and only groups and describes what they
returned. A strategy with a richer story to tell — minervini's bases and contractions — has its own
`bases_live` instead; one that wants to draw its structure better than its `chart_anatomy` does
overrides `Strategy.setup_shapes`.

A setup here is an EPISODE: consecutive bars on which the strategy reported an entry-eligible setup
(gaps of up to EPISODE_GAP bars bridged). It is judged on one bar — the first on which the entry fired
with every hard gate passing, else the first on which it fired, else its last bar — and coloured by
what the strategy would have done there:

  pass   the decision was TRADE - HIGH CONFIDENCE and the entry fired: the strategy trades it
  watch  a valid plan the decision stops short of buying today (TRADE ON TRIGGER: a coil not yet through)
  fail   a hard gate failed, the plan was refused (a reward/risk minimum) or the decision said WATCH/AVOID

Exploration only, like every Trade setups layer: what a backtest actually traded comes from its stored
signals (trade-anatomy), since current code may judge differently from the code that ran.
"""

from __future__ import annotations

import pandas as pd

from ..core import context as ctx_mod
from ..core import sizing

YEARS = 5            # default lookback: the scan is a full evaluate() per bar, so it is bounded
EPISODE_GAP = 3      # setup bars within this many bars of each other are one setup
CONTEXT_BARS = 20    # a setup's frame starts at least this far before its first setup bar
ENTRY_BARS = 20      # how far the illustrated entry levels run past the judged bar


def scan(strategy, raw: pd.DataFrame, cfg, symbol: str, years: int | None = YEARS) -> list[dict]:
    """Every setup episode in the last `years` (None: all history), oldest first."""
    frames = ctx_mod.prepare_frames(raw)
    daily = frames.daily
    if daily.empty:
        return []
    mask = strategy.prefilter_mask(cfg, daily)
    since = daily.index[-1] - pd.DateOffset(years=years) if years else daily.index[0]
    recs = []   # (bar index, date, ctx, result, fired)
    for i, d in enumerate(daily.index):
        if d < since or i + 1 < strategy.min_bars or not bool(mask.get(d, False)):
            continue
        try:
            ctx = ctx_mod.build_context(symbol, raw, earnings_days_away=None, frames=frames, as_of=d)
        except Exception:  # noqa: BLE001 — a bar the context cannot be built for is simply skipped
            continue
        if ctx is None:
            continue
        r = strategy.evaluate(ctx)
        if r.has_setup:
            recs.append((i, d, ctx, r, bool(strategy.entry_signal_fired(ctx, r))))
    episodes, cur = [], []
    for rec in recs:
        if cur and rec[0] - cur[-1][0] > EPISODE_GAP:
            episodes.append(cur)
            cur = []
        cur.append(rec)
    if cur:
        episodes.append(cur)
    return [_episode(strategy, cfg, daily, ep) for ep in episodes]


def _sig(ctx, r, d, symbol) -> dict:
    """The bar as a backtest_signals row, the input `chart_anatomy` is written against."""
    return {"date": d.date(), "symbol": symbol, "hard_gates": dict(r.hard_gates), "first_failed_gate": r.first_hard_fail,
            "setups": dict(r.setups), "h_value": ctx.h_value, "h_index": ctx.h_index.date() if ctx.h_index is not None else None,
            "l_value": ctx.l_value, "p_value": ctx.p_value, "prior_swing_low": ctx.prior_swing_low,
            "overhead_levels": ctx.overhead, "watch_flags": dict(r.watch_flags), "watch_notes": dict(r.watch_notes),
            "extras": dict(ctx.extras or {})}


def _first_sentence(text: str) -> str:
    text = (text or "").strip()
    cut = text.find(". ")
    return text if cut < 0 else text[: cut + 1]


def _episode(strategy, cfg, daily: pd.DataFrame, ep: list) -> dict:
    day = lambda i: str(daily.index[i].date())
    px = lambda v: f"{v:,.2f}" if abs(v) >= 1 else f"{v:.4g}"
    first_i, last_bar = ep[0][0], len(daily) - 1
    pick = (next((x for x in ep if x[4] and x[3].hard_gates_passed), None)
            or next((x for x in ep if x[4]), None) or ep[-1])
    i, d, ctx, r, fired = pick
    names = getattr(strategy, "setup_names", {}) or {}
    active = r.active_setups
    setup_name = " + ".join(names.get(c, c) for c in active) or "setup"

    # ---- what the strategy itself would do on the judged bar
    plan, dec, refused = None, None, ""
    if r.hard_gates_passed:
        choice = strategy.build_plans(ctx, r, cfg)
        plan = choice.chosen if choice.chosen is not None and choice.chosen.is_valid else None
        refused = "" if plan else (choice.reason or "no valid plan")
        if plan:
            sz = sizing.size_position(cfg, plan.entry, plan.stop, vix_above_threshold=False)
            dec = strategy.classify(ctx, r, plan, sz, None, False)
    label = dec.label_before if dec else ""
    gate_title = lambda c: strategy.render_doc((getattr(strategy, "gate_titles", {}) or {}).get(c) or c)
    if not r.hard_gates_passed:
        kind, why = "fail", (f"{gate_title(r.first_hard_fail)}: {r.hard_notes.get(r.first_hard_fail) or 'failed'}")
    elif plan is None:
        kind, why = "fail", refused
    elif label == "TRADE - HIGH CONFIDENCE" and fired:
        kind, why = "pass", ""
    elif label.startswith("TRADE"):
        kind, why = "watch", "the decision is TRADE ON TRIGGER: valid, but the entry has not fired" if not fired else (dec.reason or label)
    else:
        kind, why = "fail", f"decided {label}" + (f" — {dec.reason}" if dec and dec.reason else "")

    # ---- the checklist: each gate in its own words, then the setup, the watch flags, the plan
    gate_docs = getattr(strategy, "gate_docs", {}) or {}
    gate_rows = []
    for c in strategy.gate_codes:
        ok = r.hard_gates.get(c)
        gate_rows.append({"code": c, "name": gate_title(c),
                          "value": r.hard_notes.get(c) or ("passed" if ok else "failed" if ok is False else "—"),
                          "limit": _first_sentence(strategy.render_doc(gate_docs.get(c, ""))),
                          "state": "pass" if ok else "fail" if ok is False else "skip"})
    setup_rows = [{"code": c, "name": names.get(c, c), "value": "yes" if r.setups.get(c) else "no",
                   "limit": _first_sentence(strategy.render_doc((strategy.setup_docs or {}).get(c, ""))),
                   "state": "pass" if r.setups.get(c) else "skip"} for c in strategy.setup_codes]
    watch_rows = [{"code": c, "name": f"Watch flag {c}", "value": r.watch_notes.get(c) or "raised",
                   "limit": _first_sentence(strategy.render_doc((strategy.watch_docs or {}).get(c, ""))), "state": "warn"}
                  for c in strategy.watch_codes if r.watch_flags.get(c)]

    # ---- the drawing: the strategy's own (setup_shapes, chart_anatomy by default); its "uptrend" shapes
    # belong to zone 1, the rest to zone 2
    shapes = strategy.setup_shapes(ctx, r, _sig(ctx, r, d, ctx.symbol))
    trend_shapes = [s for s in shapes if s.get("role") == "uptrend"]
    setup_shapes = [s for s in shapes if s.get("role") != "uptrend"]

    frame_from_i = max(0, first_i - CONTEXT_BARS)
    dated = [s.get("from") for s in shapes if s.get("from")]
    frame_from = min([day(frame_from_i)] + dated)
    zones = []
    zones.append({"key": "trend", "title": "Gates", "state": "pass" if r.hard_gates_passed else "fail",
                  "from": frame_from, "to": day(first_i),
                  "line": "all passed" if r.hard_gates_passed else f"failed {r.first_hard_fail}",
                  "text": (f"The hard gates on {d.date()}, each in the strategy's own words. "
                           + ("Every one passed." if r.hard_gates_passed else f"The first to fail: {why}.")
                           + " (Historical bars have no earnings calendar, so an earnings gate always passes here.)"),
                  "checks": gate_rows, "shapes": trend_shapes})
    note = next((s.get("text") for s in setup_shapes if s.get("shape") == "note"), "")
    zones.append({"key": "setup", "title": setup_name if len(setup_name) < 28 else "Setup",
                  "state": "pass" if active else "skip", "from": day(first_i), "to": day(i),
                  "line": f"{len(ep)} setup bar{'s' if len(ep) != 1 else ''}" + (" · fired" if fired else " · not fired"),
                  "text": " ".join(x for x in [note] + [strategy.render_doc((strategy.setup_docs or {}).get(c, "")) for c in active] if x),
                  "checks": setup_rows + watch_rows,
                  "shapes": [s for s in setup_shapes if s.get("shape") != "note" and s.get("role") not in ("stop", "target")]})

    top = max([float(daily["high"].iloc[frame_from_i: i + 1].max())] + [s["price"] for s in shapes if "price" in s and s["price"]]
              + [s["top"] for s in shapes if s.get("top")])
    bottom = min([float(daily["low"].iloc[frame_from_i: i + 1].min())] + [s["bottom"] for s in shapes if s.get("bottom")])
    frame_to = day(i)
    if plan:
        to = day(min(last_bar, i + ENTRY_BARS))
        risk = plan.entry - plan.stop
        nominal = bool(getattr(strategy, "nominal_target", False))   # the exit is a rule, not this price
        levels = [("buy", plan.entry, f"Buy {px(plan.entry)}"),
                  ("stop", plan.stop, f"Stop {px(plan.stop)} (−{risk / plan.entry * 100:.1f}%)"),
                  ("target", plan.target, f"Nominal target {px(plan.target)} (sizing only)" if nominal
                   else f"Target {px(plan.target)} · {plan.r_multiple:.1f}R")]
        e_shapes = [{"shape": "level", "from": day(i), "to": to, "price": float(v), "role": role, "label": lab,
                     "dash": role != "buy"} for role, v, lab in levels]
        if fired:
            e_shapes.append({"shape": "dots", "role": "buy",
                             "points": [{"at": day(i), "price": float(daily["close"].iloc[i]), "label": "signal"}]})
        min_r = getattr(strategy, "min_structural_r", None)
        e_checks = [{"code": "R:R", "name": "Reward / risk" + (" (nominal)" if nominal else ""), "value": f"{plan.r_multiple:.2f}R",
                     "limit": f"at least {min_r:g}R" if min_r else "", "state": "pass" if not min_r or plan.r_multiple >= min_r else "fail"},
                    {"code": "decision", "name": "Decision", "value": label or "—",
                     "limit": "TRADE - HIGH CONFIDENCE, with the entry fired",
                     "state": "pass" if kind == "pass" else "warn" if kind == "watch" else "fail"}]
        rules = " ".join(strategy.render_doc(x) for x in (getattr(strategy, "entry_rules", ()) or ()))
        zones.append({"key": "entry", "title": "Entry", "state": "pass" if kind == "pass" else "warn" if kind == "watch" else "fail",
                      "from": day(i), "to": to, "illustration": True,
                      "line": f"buy {px(plan.entry)} · stop {px(plan.stop)}" + ("" if nominal else f" · {plan.r_multiple:.1f}R"),
                      "text": (f"Where this strategy's own build_plans puts the trade on {d.date()}: an illustration, not a "
                               f"recommendation and not a backtest result. Decision: {label}"
                               + (f" ({dec.reason})" if dec and dec.reason else "") + f". {rules}"),
                      "checks": e_checks, "shapes": e_shapes})
        top = max(top, plan.target, plan.entry)
        bottom = min(bottom, plan.stop)
        frame_to = to
    live = ep[-1][0] == last_bar
    # the header names what stopped it in a few words: the gate's short name, or the decision's own reason
    # up to its first dash (breakout: "base projects 0.10R < 2R")
    short = (gate_title(r.first_hard_fail) if not r.hard_gates_passed
             else (dec.reason.split(" — ")[0].split(";")[0] if dec and dec.reason else refused or label))
    title = {"pass": f"{setup_name} ✓", "watch": f"{setup_name} · on trigger"}.get(kind) or f"✗ {short[:44]}"
    summary = {"pass": f"The strategy trades this: {setup_name} on {d.date()}, decided {label}.",
               "watch": f"A valid {setup_name} plan on {d.date()}, but {why}."}.get(kind) or f"Not traded: {why}."
    if live:
        title += " · today"
        summary = f"Still active on today's bar, {day(last_bar)}. " + summary
    return {"from": frame_from, "base_from": day(first_i), "to": frame_to, "kind": kind,
            "complete": kind == "pass", "fail": None if kind == "pass" else (r.first_hard_fail or "plan"),
            "breakout": day(i) if fired else None, "live": live, "as_of": day(i),
            "title": title, "summary": summary,
            "frame": {"from": frame_from, "to": frame_to, "top": float(top), "bottom": float(bottom)}, "zones": zones}
