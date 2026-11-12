"""Trade setups for the portfolio strategies that trade one stock at a time, for the chart's Trade setups layer.

The per-symbol strategies get theirs from `strategies/live_setups.py`, which runs their evaluate / build_plans /
classify bar by bar. A portfolio strategy has none of that contract: its rules live in its runner. So each of
the four that buy or short a single name with an entry and a stop (stage4_shorts, parabolic_short, pead,
etf_swing) has a `setups_live` that runs the runner's OWN signal frame and filters (`symbol_frame`,
`screen_signal`, `qualify`, `entry_checks`) over one symbol, and replays each signal through the runner's own
simulator (`run`, on that one symbol) for its outcome. This module only shapes what they return into the
episodes the chart draws -- the same dict `live_setups._episode` returns -- and adds no rule of its own.

Exploration only, like every Trade setups layer: one symbol on its own, so the portfolio limits (slots, open
risk, gross exposure) never bind, and today's code. What a backtest traded comes from its stored trades.
"""

from __future__ import annotations

import pandas as pd

ENTRY_BARS = 20      # how far the illustrated levels run past the signal bar (as live_setups.ENTRY_BARS)
CONTEXT_BARS = 20    # a setup's frame starts at least this far before its first bar
EPISODE_GAP = 3      # signal bars within this many bars of each other are one setup (as live_setups)

POLICY = "the strategy's own simulator, run on this one symbol"


def market_of(cfg) -> str:
    """The MARKETS key of a market's config (the setups layer is handed the config, as live_setups is)."""
    from ..config import MARKETS
    return next(k for k, v in MARKETS.items() if v is cfg)


def since(daily: pd.DataFrame, years: int | None) -> pd.Timestamp:
    """The first session the layer scans: `years` before the last bar (None: all history)."""
    return daily.index[-1] - pd.DateOffset(years=years) if years else daily.index[0]


def group(bars: list[int]) -> list[list[int]]:
    """Signal bar indices (ascending) grouped into episodes: gaps of up to EPISODE_GAP bars bridged."""
    out, cur = [], []
    for i in bars:
        if cur and i - cur[-1] > EPISODE_GAP:
            out.append(cur)
            cur = []
        cur.append(i)
    if cur:
        out.append(cur)
    return out


def anchor_bars(daily: pd.DataFrame, anchors: list[dict] | None, lag: int = 0) -> set[int]:
    """The signal bar of each of a selected run's trades in this symbol: its fill session less `lag` sessions
    (1 for a runner that fills at the next open, 0 for one that fills at the signal's close)."""
    out = set()
    for a in anchors or []:
        try:
            d = pd.Timestamp(a["entry"])
        except Exception:  # noqa: BLE001 -- a trade with no fill date anchors nothing
            continue
        i = int(daily.index.searchsorted(d))
        if i < len(daily) and daily.index[i] == d and i - lag >= 0:
            out.add(i - lag)
    return out


def parts(ep: list[int], anchored: set[int]) -> list[tuple[list[int], int | None]]:
    """An episode split at each bar a selected run traded, so each of the run's trades has a setup of its own:
    (its bars, the bar it is judged on -- the run's signal -- or None when the run traded none of them).
    The first part keeps the bars before the first traded one, as live_setups.scan does."""
    cuts = [k for k, i in enumerate(ep) if i in anchored]
    if not cuts:
        return [(ep, None)]
    bounds = [0] + cuts[1:] + [len(ep)]
    return [(ep[bounds[n]: bounds[n + 1]], ep[c]) for n, c in enumerate(cuts)]


def rows(checks: list[tuple], fmt=None) -> list[dict]:
    """(code, name, value, limit, ok) tuples as checklist rows; ok None = not reached."""
    show = fmt or (lambda v: "—" if v is None or v != v else f"{v:,.2f}" if isinstance(v, float) else str(v))
    return [{"code": c, "name": n, "value": show(v), "limit": lim,
             "state": "pass" if ok else "fail" if ok is False else "skip"} for c, n, v, lim, ok in checks]


def ordered(names: list[tuple], refused: str) -> list[bool | None]:
    """Each of a runner's filters in the order it applies them: passed before the one that `refused`, failed
    there, not reached after it ("" = every one passed)."""
    keys = [k for k, *_ in names]
    if not refused:
        return [True] * len(keys)
    at = keys.index(refused)
    return [True] * at + [False] + [None] * (len(keys) - at - 1)


def outcome(daily: pd.DataFrame, side: str, trade: dict | None, note: str) -> dict:
    """The setup's outcome from the runner's own trade row (entry/exit date and price, exit reason, initial
    stop), in the shape setup_outcomes.outcome returns. R is from the prices, before costs and carry."""
    if trade is None:
        return {"filled": None, "note": note}
    sign = 1 if side == "long" else -1
    fill, stop = float(trade["entry_price"]), float(trade["initial_stop"])
    risk = abs(fill - stop) or 1e-9
    px = float(trade["exit_price"])
    e0, e1 = pd.Timestamp(trade["entry_date"]), pd.Timestamp(trade["exit_date"])
    open_ = trade.get("exit_reason") == "OPEN"
    return {"filled": str(e0.date()), "fill": round(fill, 4), "stop": round(stop, 4), "policy": POLICY,
            "open": open_, "exit": None if open_ else str(e1.date()), "reason": "hold" if open_ else trade.get("exit_reason"),
            "exit_price": round(px, 4), "r": round(sign * (px - fill) / risk, 2),
            "pct": round(sign * (px / fill - 1) * 100, 2), "days": int(len(daily.loc[e0:e1]) - 1)}


def episode(daily: pd.DataFrame, bars: list[int], judge: int, *, name: str, side: str, kind: str, why: str,
            gates: list[dict], setup_rows: list[dict], shapes: list[dict], text: str,
            entry: float | None = None, stop: float | None = None, target: float | None = None,
            target_label: str = "", entry_text: str = "", stop_on_close: bool = False,
            outcome_: dict | None = None, anchored: bool = False) -> dict:
    """One setup episode as the chart's Trade setups layer draws it (live_setups._episode's shape).

    `bars`: the episode's signal bar indices; `judge`: the bar it is judged on (`anchored`:
    the bar a selected run traded, whose record the chart then draws instead of the illustration). `kind`: pass (the runner
    takes it), fail (a filter refused it: `why`). `side`: long or short -- a short's stop is above its entry.
    `entry` / `stop` / `target`: the plan's levels (target optional: a rule exit has none). `stop_on_close`:
    the stop is a close beyond it (pead), not a touch."""
    day = lambda k: str(daily.index[k].date())
    px = lambda v: f"{v:,.2f}" if abs(v) >= 1 else f"{v:.4g}"
    first_i, last_bar = bars[0], len(daily) - 1
    frame_from_i = max(0, first_i - CONTEXT_BARS)
    dated = [s.get("from") for s in shapes if s.get("from")]
    frame_from = min([day(frame_from_i)] + dated)
    passed = all(g["state"] != "fail" for g in gates)
    zones = [{"key": "trend", "title": "Gates", "state": "pass" if passed else "fail",
              "from": frame_from, "to": day(first_i), "line": "all passed" if passed else f"failed: {why}",
              "text": f"The strategy's filters on {day(judge)}, in the order its backtest applies them. "
                      + ("Every one passed." if passed else f"The first to refuse: {why}."),
              "checks": gates, "shapes": [s for s in shapes if s.get("role") == "uptrend"]}]
    zones.append({"key": "setup", "title": name if len(name) < 28 else "Setup", "state": "pass",
                  "from": day(first_i), "to": day(judge),
                  "line": f"{len(bars)} signal bar{'s' if len(bars) != 1 else ''}", "text": text, "checks": setup_rows,
                  "shapes": [s for s in shapes if s.get("role") not in ("uptrend", "stop", "target") and s.get("shape") != "note"]})
    top = max([float(daily["high"].iloc[frame_from_i: bars[-1] + 1].max())] + [s["price"] for s in shapes if s.get("price")]
              + [s["top"] for s in shapes if s.get("top")])
    bottom = min([float(daily["low"].iloc[frame_from_i: bars[-1] + 1].min())] + [s["bottom"] for s in shapes if s.get("bottom")])
    frame_to_i, stop_hit = max(judge, bars[-1]), None
    if entry is not None and stop is not None and kind == "pass":
        horizon = min(last_bar, max(judge + ENTRY_BARS, bars[-1]))
        hit = daily["close"] if stop_on_close else daily["high"] if side == "short" else daily["low"]
        beyond = (lambda v: v >= stop) if side == "short" else (lambda v: v < stop) if stop_on_close else (lambda v: v <= stop)
        hv = hit.to_numpy()
        stop_hit = next((j for j in range(judge + 1, horizon + 1) if beyond(hv[j])), None)
        to = day(stop_hit if stop_hit is not None else horizon)
        risk = abs(entry - stop)
        levels = [("buy", entry, f"{'Short' if side == 'short' else 'Buy'} {px(entry)}"),
                  ("stop", stop, f"Stop {px(stop)} ({'+' if side == 'short' else '−'}{risk / entry * 100:.1f}%)")]
        if target is not None:
            levels.append(("target", target, target_label or f"Target {px(target)}"))
        e_shapes = [{"shape": "level", "from": day(judge), "to": to, "price": float(v), "role": role, "label": lab,
                     "dash": role != "buy"} for role, v, lab in levels]
        e_shapes.append({"shape": "dots", "role": "buy",
                         "points": [{"at": day(judge), "price": float(daily["close"].iloc[judge]), "label": "signal"}]})
        zones.append({"key": "entry", "title": "Entry", "state": "pass", "from": day(judge), "to": to, "illustration": True,
                      "line": f"{'short' if side == 'short' else 'buy'} {px(entry)} · stop {px(stop)}"
                              + (f" · stop hit {day(stop_hit)}" if stop_hit is not None else ""),
                      "text": f"Where this strategy's own rules put the trade on {day(judge)}: an illustration, not a "
                              f"recommendation and not a backtest result. {entry_text}",
                      "checks": [], "shapes": e_shapes})
        top, bottom = max(top, entry, stop, target or entry), min(bottom, entry, stop, target or entry)
        frame_to_i = max(stop_hit if stop_hit is not None else horizon, bars[-1])
    live = bars[-1] == last_bar
    title = f"{name} ✓" if kind == "pass" else f"✗ {why[:44]}"
    summary = (f"The strategy takes this: {name} on {day(judge)}." if kind == "pass" else f"Not taken: {why}.")
    if stop_hit is not None:
        summary += f" Price went through the stop on {day(stop_hit)}, so the illustrated trade ends there."
    if live:
        title += " · today"
        summary = f"Still active on today's bar, {day(last_bar)}. " + summary
    out = {"from": frame_from, "base_from": day(first_i), "to": day(frame_to_i), "kind": kind, "anchored": anchored,
           "complete": kind == "pass", "fail": None if kind == "pass" else "filter",
           "breakout": day(judge) if kind == "pass" else None, "live": live, "as_of": day(judge), "expired": False,
           "stopped": day(stop_hit) if stop_hit is not None else None, "title": title, "summary": summary,
           "frame": {"from": frame_from, "to": day(frame_to_i), "top": float(top), "bottom": float(bottom)}, "zones": zones}
    if outcome_ is not None:
        out["outcome"] = {**outcome_, "side": side}
    return out
