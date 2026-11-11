"""What became of each setup on the chart's Trade setups layer: filled or not, and how the trade ended.

A setup is the strategy's view on one bar -- its buy, stop and (when it has one) target. This replays the bars
after it the way the backtest would have traded it, so the panel can show an outcome beside the plan:

  the fill   the order the strategy's own `signal_meta` asks for (Minervini's bases, which record none: the next
             open after the signal, as its MV-01 and cheat orders do), as the portfolio simulator fills it
             (backtesting/portfolio_sim.py): a resting buy-stop at the buy, good for PENDING_EXPIRY_BDAYS
             sessions and cancelled when price trades through the stop first (or closes below
             `cancel_close_below`); `order="open"` buys the next session's open inside `max_fill` /
             `min_open`; `order="close"` buys the signal session's close; `confirm_close_above` fills at the
             close of a session that closes through the level. A fill whose risk is over `max_risk_pct`, or
             that gapped past the target, is skipped.
  the exit   the position, replayed through the strategy's own exit policy (`backtest.exit_policy_for`, from
             its `backtest_args`) by the open-position tracker's `track` -- the same code that manages a
             backtest position: trailing stops, channel and average exits, the Minervini ladder, partials.

It is not a backtest: one setup at a time, no portfolio (slots, cash, one position per stock), no slippage or
costs, and the strategy's current code. Overlapping setups replay the same move. Read it as "what this setup
did", never as a strategy result -- what a run traded comes from its stored trades. Stored data only.
"""

from __future__ import annotations

import math

import pandas as pd

from ..backtesting import portfolio_sim as ps
from ..backtesting import tracker

ORDER_KEYS = ("order", "max_fill", "min_open", "confirm_close_above", "cancel_close_below", "max_risk_pct", "expiry_bdays")
SHARES = 1000   # a notional size, so the exit ladder's partial sales come out as fractions of the position


def order_meta(meta: dict | None) -> dict:
    """The part of a strategy's `signal_meta` that decides the fill, as plain JSON values."""
    out = {}
    for k in ORDER_KEYS:
        v = (meta or {}).get(k)
        if v is None:
            continue
        out[k] = v if isinstance(v, str) else float(v)
    return out


def _entry_zone(s: dict) -> dict | None:
    zones = [z for z in s.get("zones", []) if z.get("key") in ("entry", "cheat")]
    return next((z for z in zones if z.get("state") == "pass"), zones[-1] if zones else None)


def _level(z: dict, role: str):
    for x in z.get("shapes", []):
        if x.get("shape") == "level" and x.get("role") == role and x.get("price") is not None:
            return x
    return None


def _fill(daily: pd.DataFrame, i: int, buy: float, stop: float, target: float, meta: dict):
    """(bar index, price, when) of the fill after signal bar `i`, or (None, reason, None)."""
    o, h, l, c = (daily[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(daily)
    kind = meta.get("order")
    if kind == "close":
        return i, float(c[i]), ps.AT_CLOSE
    if kind == "open":
        if i + 1 >= n:
            return None, "the order is for the next session's open", None
        if o[i + 1] > meta.get("max_fill", math.inf):
            return None, "opened above the buy range", None
        if o[i + 1] <= meta.get("min_open", -math.inf):
            return None, "opened at or below the tight low", None
        return i + 1, float(o[i + 1]), ps.AT_OPEN
    expires = daily.index[i] + pd.tseries.offsets.BDay(int(meta.get("expiry_bdays") or ps.PENDING_EXPIRY_BDAYS))
    lvl = meta.get("confirm_close_above")
    for j in range(i + 1, n):
        if daily.index[j] > expires:
            return None, "the buy order expired unfilled", None
        if h[j] >= buy:
            if lvl is not None:
                if c[j] < lvl:
                    continue   # poked through and closed back below: the order keeps resting
                return j, max(buy, float(c[j])), ps.AT_CLOSE
            return j, max(buy, float(o[j])), (ps.AT_OPEN if o[j] >= buy else ps.INTRADAY)
        if l[j] <= stop:
            return None, "price went through the stop before the buy filled", None
        if c[j] < meta.get("cancel_close_below", -math.inf):
            return None, "closed below the setup's low before the buy filled", None
    return None, "the buy has not filled yet", None


def outcome(daily: pd.DataFrame, frame: pd.DataFrame, policy, cfg, symbol: str, s: dict,
            default_order: dict | None = None) -> dict | None:
    """What became of setup `s` (a live_setups / bases_live setup), or None for one the strategy would not
    trade (refused, too young) or one without a buy and a stop. `default_order`: the fill for a setup whose
    entry zone records none (Minervini's own bases)."""
    z = _entry_zone(s)
    if z is None or not (z.get("state") == "pass" or s.get("kind") == "watch"):
        return None
    if s.get("crossed") and not s.get("breakout") and z.get("key") == "entry":
        # it crossed the pivot, but not as a breakout the strategy buys (a weak close, light volume): not bought
        return {"filled": None, "note": "crossed the pivot without a valid breakout, so it was not bought"}
    b, st = _level(z, "buy"), _level(z, "stop")
    if b is None or st is None:
        return None
    t = _level(z, "target")
    nominal = t is not None and str(t.get("label", "")).lower().startswith("nominal")
    buy, stop = float(b["price"]), float(st["price"])
    target = float(t["price"]) if t is not None and not nominal and policy.use_target else math.inf
    # the signal bar: the setup's breakout when it records one (Minervini's bases), else its entry zone's own bar
    at_ = pd.Timestamp(s.get("breakout") if z.get("key") == "entry" and s.get("breakout") else z.get("from") or s.get("as_of"))
    pos = daily.index.searchsorted(at_)
    if pos >= len(daily):
        return None
    meta = z.get("order") if z.get("order") is not None else dict(default_order or {})
    j, fill, when = _fill(daily, int(pos), buy, stop, target, meta)
    if j is None:
        return {"filled": None, "note": fill}
    if fill >= target:
        return {"filled": None, "note": "gapped past the target before it could fill"}
    if fill <= stop:
        return {"filled": None, "note": "filled at or below the stop"}
    if (fill - stop) / fill > meta.get("max_risk_pct", math.inf):
        return {"filled": None, "note": "the risk at the fill was over the strategy's limit"}
    r = tracker.track(daily, policy, cfg, symbol=symbol, entry_date=daily.index[j], entry_price=fill,
                      initial_stop=stop, shares=SHARES, target=target, meta=meta, entry_at=when, frame=frame)
    risk = fill - stop
    out = {"filled": str(daily.index[j].date()), "fill": round(fill, 4), "stop": round(stop, 4), "policy": r["policy"]}
    ex = r.get("exit") or {}
    if ex.get("date") and ex.get("price") is not None:
        sold = sum(p["shares"] * p["price"] for p in r.get("partials", []))
        left = SHARES - sum(p["shares"] for p in r.get("partials", []))
        px = (sold + left * float(ex["price"])) / SHARES   # partial sales folded in, as a backtest trade row does
        end = pd.Timestamp(ex["date"])
        out.update(open=False, exit=ex["date"], reason=ex.get("reason"), exit_price=round(px, 4),
                   r=round((px - fill) / risk, 2), pct=round((px / fill - 1) * 100, 2),
                   days=int(len(daily.loc[daily.index[j]:end]) - 1))
    else:
        last = float(daily["close"].iloc[-1])
        out.update(open=True, exit=None, reason=r.get("status"), exit_price=round(last, 4),
                   r=round((last - fill) / risk, 2), pct=round((last / fill - 1) * 100, 2),
                   days=int(len(daily.loc[daily.index[j]:]) - 1), stop_now=r.get("stop"))
    return out


def attach(strategy, market: str, cfg, daily: pd.DataFrame, symbol: str, setups: list[dict]) -> None:
    """Add `outcome` to each setup in place. `daily`: the enriched daily bars the setups were found on."""
    from ..backtesting.backtest import exit_policy_for
    if not setups or daily is None or daily.empty:
        return
    policy = exit_policy_for(strategy.key, market)
    frame = ps.exit_frames({symbol: daily}, policy)[symbol]
    # Minervini's bases record no order: its MV-01 and cheat entries buy the next session's open after the signal
    # (signal_meta), which stands in for every one of them -- its S2 buys the confirming close, a day earlier
    default = {"order": "open"} if hasattr(strategy, "bases_live") else {}
    for s in setups:
        try:
            s["outcome"] = outcome(daily, frame, policy, cfg, symbol, s, default)
        except Exception as e:  # noqa: BLE001 -- one setup that cannot be replayed is said so, not fatal
            s["outcome"] = {"filled": None, "note": f"could not be replayed ({type(e).__name__})"}
