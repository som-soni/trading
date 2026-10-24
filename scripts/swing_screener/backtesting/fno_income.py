"""Selling index option spreads for income — the first CARRY mechanism measured here.

Every other strategy in this repository is paid for being right about direction. This one is paid
for time passing and for implied volatility exceeding what arrives. That makes it the most
genuinely different thing in the Learn module, and the only one whose P&L has a known shape before
any backtest: many small gains and a few large losses.

WHAT THE STORED DATA SUPPORTS, AND WHAT IT DOES NOT. `derivatives_bhav` holds NSE's daily
bhavcopy: 7.4M NIFTY option rows from 2012, every strike and expiry, with settle, close, open
interest and volume. That is enough to construct spreads, mark them daily and exit them. It does
NOT carry bid/ask, so the one cost that matters most to an option seller -- the spread, paid twice
per leg and four times per condor -- cannot be measured and has to be assumed. See the caveats;
this is the weakest assumption in the whole result.

GREEKS ARE COMPUTED, NOT STORED. The guide selects the short strike by delta (0.15-0.30), so delta
has to come from somewhere. Rather than feed one index-level volatility to every strike, this
inverts Black-Scholes on each leg's own settle price to get that leg's implied volatility, then
takes delta from it. The inversion validates against an independent series: on 2024-06-03 the
recovered at-the-money IVs were 21.2% (call) and 19.4% (put) against a published India VIX of
20.9, with puts above calls at equal delta -- the volatility skew, which a single-vol model cannot
produce and which is exactly what a seller is paid for.

The risk-free rate is the repo rate (`index_series` IN_REPO), not a constant: it ranged 4.0% to
8.0% over the window, which moves a 30-day delta enough to change strike selection.
"""
from __future__ import annotations

import argparse
import logging
import math

import pandas as pd

from ..config import MARKETS
from ..marketdata import asof
from ..marketdata import db
from ..strategies.base import PortfolioStrategy
from . import metrics

logger = logging.getLogger("backtest")

UNDERLYING = "NIFTY"

# ---- when to sell at all (guide §3)
VIX_PERCENTILE = 40.0        # India VIX at or above this percentile of the trailing year
VIX_WINDOW = 252
MIN_OPEN_INTEREST = 500      # contracts, per leg
DTE_MIN, DTE_MAX = 20, 45    # days to expiry at entry

# ---- the structure
SHORT_DELTA = 0.25           # target delta of the sold leg (guide: 0.15-0.30)
DELTA_TOL = 0.10             # accept a leg within this of the target
WIDTH_PCT = 1.5              # strike gap as a percent of the index (guide: 1-2%)
#: The guide asks for "at least one quarter of the spread's width for a short delta near 0.25".
#: MEASURED ON THE STORED CHAINS, THOSE TWO RULES CANNOT BOTH HOLD. Credit/width is close to an
#: identity with the short delta -- it is roughly the risk-neutral chance of finishing beyond the
#: short strike -- so asking for 25% of the width at a 25-delta short is asking the market to
#: misprice itself. Median credit/width over 178 month-starts, 2012-2026:
#:
#:      delta \ width    0.5%    1.0%    1.5%    2.0%
#:      0.15            0.111   0.099   0.089   0.079
#:      0.25            0.202   0.183   0.168   0.147
#:      0.35            0.302   0.274   0.252   0.229
#:
#: The 25% rule is met on 1-7% of days at the guide's delta range, and only becomes normal at
#: delta 0.35 (89% of days at a 0.5% width). The ratio sits consistently at ~0.73x the short
#: delta, the shortfall being the long leg's own value.
#:
#: So the test is expressed RELATIVE to the delta being sold: reject a spread paying materially
#: less than its own probability warrants, which is a live filter, instead of an absolute
#: threshold that rejects 97% of the chain and leaves 23 trades in fourteen years.
MIN_CREDIT_VS_DELTA = 0.65   # credit/width must be at least this multiple of the short delta
TREND_SMA = 50               # above it: sell puts. below and falling: sell calls

# ---- managing it
PROFIT_TARGET_FRAC = 0.50    # close at half the maximum profit
STOP_CREDIT_MULT = 2.0       # close the side when it costs this many times the credit
CLOSE_DAYS_BEFORE = 6        # exit this many days before expiry regardless (guide: 5-7)
RISK_PCT = 1.5               # percent of capital at risk per structure, by MAXIMUM LOSS

STRUCTURES = ("put_spread", "condor", "both_sides")


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs_price(S: float, K: float, T: float, r: float, sig: float, kind: str) -> float:
    """Black-Scholes on a non-dividend-paying index. The dividend yield is omitted deliberately:
    NIFTY's is ~1.2% and enters delta an order of magnitude below the IV uncertainty, while adding
    a second series that would have to be point-in-time."""
    if T <= 0 or sig <= 0:
        return max(0.0, (S - K) if kind == "CE" else (K - S))
    d1 = (math.log(S / K) + (r + sig * sig / 2) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    if kind == "CE":
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def bs_delta(S: float, K: float, T: float, r: float, sig: float, kind: str) -> float:
    if T <= 0 or sig <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + sig * sig / 2) * T) / (sig * math.sqrt(T))
    return _norm_cdf(d1) if kind == "CE" else _norm_cdf(d1) - 1


def implied_vol(price: float, S: float, K: float, T: float, r: float, kind: str) -> float:
    """Bisection rather than Newton: it cannot diverge, and 60 halvings of [1%, 300%] is exact to
    well past the precision the input price carries. Returns NaN below intrinsic value, which is
    where a stale or untradeable settle price shows up."""
    if price <= 0 or T <= 0:
        return float("nan")
    if price < max(0.0, (S - K) if kind == "CE" else (K - S)) * 0.98:
        return float("nan")
    lo, hi = 0.01, 3.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if bs_price(S, K, T, r, mid, kind) > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def load_context(market: str = "india") -> dict:
    """Spot, India VIX and the repo rate -- everything the decision needs that is not the chain."""
    con = db.get_connection()
    q = ("select date, close from index_series where market=%s and series=%s order by date")
    out = {}
    for key, series in (("spot", "NIFTY50"), ("vix", "INDIAVIX"), ("repo", "IN_REPO")):
        d = pd.read_sql(q, con, params=(market, series), parse_dates=["date"])
        out[key] = asof.clip(d.set_index("date")["close"].astype(float))   # a stage's boundary
    out["sma"] = out["spot"].rolling(TREND_SMA).mean()
    # The VIX gate is a trailing PERCENTILE, not a level: a 15 VIX meant something different in
    # 2017 than in 2020, and a fixed threshold would make this a regime bet rather than a rule.
    out["vix_pct"] = out["vix"].rolling(VIX_WINDOW, min_periods=120).rank(pct=True) * 100
    return out


def chain(trade_date, expiry=None) -> pd.DataFrame:
    """One day's NIFTY option chain, optionally one expiry. `settle` is preferred over `close`:
    the bhavcopy's settle is the exchange's own end-of-day mark and is populated for strikes that
    did not trade, where `close` is zero."""
    con = db.get_connection()
    sql = """select trade_date, expiry, strike, option_type, close, settle, open_interest, contracts
               from derivatives_bhav
              where instrument='OPTIDX' and symbol=%s and trade_date=%s"""
    params: list = [UNDERLYING, pd.Timestamp(trade_date).date()]
    if expiry is not None:
        sql += " and expiry=%s"
        params.append(pd.Timestamp(expiry).date())
    df = pd.read_sql(sql, con, params=tuple(params), parse_dates=["trade_date", "expiry"])
    if df.empty:
        return df
    df["price"] = df["settle"].where(df["settle"] > 0, df["close"])
    return df


def enrich(ch: pd.DataFrame, S: float, T: float, r: float) -> pd.DataFrame:
    """Add each leg's own implied volatility and delta, from its own price.

    Per-leg rather than one index vol for the whole chain, because the whole point of selling a
    0.25-delta put is that it is priced on the skew: feeding the at-the-money vol to a far strike
    would mis-state its delta by enough to pick the wrong strike.
    """
    out = ch[ch["open_interest"] >= MIN_OPEN_INTEREST].copy()
    if out.empty:
        return out
    out["iv"] = [implied_vol(p, S, k, T, r, t)
                 for p, k, t in zip(out["price"], out["strike"], out["option_type"])]
    out["delta"] = [bs_delta(S, k, T, r, v, t) if v == v else float("nan")
                    for k, v, t in zip(out["strike"], out["iv"], out["option_type"])]
    return out[out["iv"].notna()]


def pick_spread(legs: pd.DataFrame, kind: str, S: float, width_pct: float,
                short_delta: float) -> dict | None:
    """One credit spread: sell near `short_delta`, buy `width_pct` further out.

    Returns None rather than a worse spread when the chain cannot supply one -- a missing strike,
    a delta nowhere near the target, or a credit too thin for the width. Substituting the nearest
    available leg is how a backtest ends up trading structures that were never on offer.
    """
    side = legs[legs["option_type"] == kind]
    if side.empty:
        return None
    near = side.iloc[(side["delta"].abs() - short_delta).abs().argsort()]
    short = near.iloc[0]
    if abs(abs(short["delta"]) - short_delta) > DELTA_TOL:
        return None
    # The nearest strike LISTED at or beyond the target width, not an exact arithmetic strike.
    # NIFTY's listed grid is 50 apart near the money and 100 further out, so requiring an exact
    # `short +/- width` strike failed on 17 of 97 otherwise-valid days -- it rejected spreads that
    # were genuinely on offer, which is a backtest refusing a trade for a reason the market does
    # not have.
    target = S * width_pct / 100
    side = side.sort_values("strike")
    beyond = (side[side["strike"] <= short["strike"] - target] if kind == "PE"
              else side[side["strike"] >= short["strike"] + target])
    if beyond.empty:
        return None
    long_ = beyond.iloc[-1] if kind == "PE" else beyond.iloc[0]
    credit = float(short["price"]) - float(long_["price"])
    gap = abs(float(long_["strike"]) - float(short["strike"]))
    if credit <= 0 or gap <= 0:
        return None
    if credit / gap < MIN_CREDIT_VS_DELTA * abs(float(short["delta"])):
        return None
    return {"kind": kind, "short_strike": float(short["strike"]), "long_strike": float(long_["strike"]),
            "credit": credit, "width": gap, "max_loss": gap - credit,
            "short_delta": float(short["delta"]), "short_iv": float(short["iv"])}


def mark(trade_date, expiry, legs: list, S: float) -> float:
    """What it costs to close the structure now, in index points.

    Priced off the stored chain for the SAME strikes, never re-modelled: a Black-Scholes mark
    would quietly replace the market's own skew with the model's and flatter a short-vol strategy
    exactly when it matters, which is when the skew steepens.
    """
    ch = chain(trade_date, expiry)
    if ch.empty:
        return float("nan")
    idx = {(float(k), t): float(p) for k, t, p in
           zip(ch["strike"], ch["option_type"], ch["price"])}
    total = 0.0
    for leg in legs:
        px = idx.get((leg["strike"], leg["kind"]))
        if px is None:
            # Not quoted today: fall back to intrinsic, which is what it is worth at expiry and a
            # CONSERVATIVE mark for a short leg (it ignores remaining time value we would pay).
            px = max(0.0, (S - leg["strike"]) if leg["kind"] == "CE" else (leg["strike"] - S))
        total += px * (1 if leg["sign"] > 0 else -1)
    return total


def run(market: str, start: str, structure: str = "put_spread", short_delta: float = SHORT_DELTA,
        width_pct: float = WIDTH_PCT, risk_pct: float = RISK_PCT,
        vix_percentile: float = VIX_PERCENTILE, cost_points: float = 2.0,
        preloaded: dict | None = None):
    """One structure at a time: open when flat and the gate allows, manage daily, repeat.

    `cost_points` is the assumed round-trip slippage per leg in INDEX POINTS, standing in for the
    bid/ask the bhavcopy does not carry. It is the load-bearing assumption here, which is why it
    is a parameter and is swept in the status rather than buried.
    """
    # India only, and said plainly rather than failing obscurely downstream: `derivatives_bhav`
    # holds NSE bhavcopy, so there are no US index option chains to construct anything from. The
    # stored S&P500 OPTIDX rows are NSE's own cross-listed contract, which stopped trading in 2017.
    if market != "india":
        raise SystemExit(
            f"fno_income is India-only: no stored option chains for '{market}'. "
            "derivatives_bhav carries NSE bhavcopy (NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY).")
    cfg = MARKETS[market]
    ctx = preloaded or load_context(market)
    spot, vix_pct, sma, repo = ctx["spot"], ctx["vix_pct"], ctx["sma"], ctx["repo"]
    start_ts = pd.Timestamp(start)
    cal = [d for d in spot.index if d >= start_ts]

    equity_pts = float(cfg.account_size)
    open_trade: dict | None = None
    trades, equity, held_log, risk_log, costs_total = [], [], [], [], 0.0

    for d in cal:
        S = float(spot.loc[d])
        r = float(repo.asof(d)) / 100 if len(repo) else 0.06

        # ---- manage an open structure
        if open_trade is not None:
            t = open_trade
            cost_now = mark(d, t["expiry"], t["legs"], S)
            dte = (t["expiry"] - d).days
            reason = None
            if cost_now == cost_now:
                if cost_now <= t["credit"] * (1 - PROFIT_TARGET_FRAC):
                    reason = "PROFIT_TARGET"
                elif cost_now >= t["credit"] * STOP_CREDIT_MULT:
                    reason = "STOP"
            if reason is None and dte <= CLOSE_DAYS_BEFORE:
                reason = "TIME_EXIT"
            if reason is not None:
                exit_cost = cost_now if cost_now == cost_now else max(
                    0.0, min(t["width"], abs(S - t["short_strike"])))
                slip = cost_points * len(t["legs"])
                pnl_pts = (t["credit"] - exit_cost) * t["lots"] - slip * t["lots"]
                equity_pts += pnl_pts
                costs_total += slip * t["lots"]
                trades.append({
                    "symbol": f"{UNDERLYING} {t['label']}", "entry_date": t["date"],
                    "entry_price": round(t["credit"], 2), "exit_date": d,
                    "exit_price": round(exit_cost, 2), "shares": round(t["lots"], 2),
                    "exit_reason": reason, "pnl": round(pnl_pts, 2),
                    "notional": round(t["max_loss"] * t["lots"], 2),
                    "costs": round(slip * t["lots"], 2), "holding_days": (d - t["date"]).days,
                    "r_multiple": round(pnl_pts / (t["max_loss"] * t["lots"]), 4)
                    if t["max_loss"] * t["lots"] else 0.0,
                })
                open_trade = None

        # ---- open one if flat and the gate allows
        if open_trade is None:
            vp = vix_pct.get(d, float("nan"))
            ma = sma.get(d, float("nan"))
            if vp == vp and vp >= vix_percentile and ma == ma:
                ch_all = chain(d)
                if not ch_all.empty:
                    exps = sorted({pd.Timestamp(e) for e in ch_all["expiry"].unique()
                                   if DTE_MIN <= (pd.Timestamp(e) - d).days <= DTE_MAX})
                    if exps:
                        e = exps[0]
                        T = (e - d).days / 365.25
                        legs_df = enrich(ch_all[ch_all["expiry"] == e], S, T, r)
                        if not legs_df.empty:
                            # Direction is the guide's: above the 50-day sell puts, below it and
                            # falling sell calls. A condor sells both and needs both to exist.
                            falling = ma < float(sma.asof(d - pd.Timedelta(days=20))) if len(sma) else False
                            want = []
                            if structure == "condor":
                                want = ["PE", "CE"]
                            elif S > ma:
                                want = ["PE"]
                            elif falling:
                                want = ["CE"]
                            picks = [pick_spread(legs_df, k, S, width_pct, short_delta) for k in want]
                            picks = [p for p in picks if p]
                            if picks and len(picks) == len(want):
                                credit = sum(p["credit"] for p in picks)
                                # A condor can only lose on ONE side, so its max loss is the worse
                                # side's, not the sum -- summing would halve the position size for
                                # a risk that cannot happen twice.
                                max_loss = max(p["width"] for p in picks) - credit
                                if max_loss > 0:
                                    lots = (equity_pts * risk_pct / 100) / max_loss
                                    legs = []
                                    for p in picks:
                                        legs.append({"strike": p["short_strike"], "kind": p["kind"], "sign": 1})
                                        legs.append({"strike": p["long_strike"], "kind": p["kind"], "sign": -1})
                                    open_trade = {
                                        "date": d, "expiry": e, "legs": legs, "credit": credit,
                                        "width": max(p["width"] for p in picks), "max_loss": max_loss,
                                        "lots": lots, "short_strike": picks[0]["short_strike"],
                                        "label": "+".join(f"{p['kind']}{p['short_strike']:.0f}" for p in picks),
                                    }

        equity.append((d, equity_pts))
        held_log.append((d, 1 if open_trade else 0))
        risk_log.append((d, open_trade["max_loss"] * open_trade["lots"] if open_trade else 0.0))

    eq = pd.Series(dict(equity)).sort_index()
    held = pd.Series(dict(held_log)).sort_index()
    # "Cash" here is the book MINUS the capital genuinely at risk, which for a defined-risk spread
    # is its maximum loss -- not the margin the broker blocks, and not the whole book. That makes
    # the deployment decomposition honest about what this strategy really is: it risks `risk_pct`
    # of capital at a time, so it is ~98% in cash even while "in a trade", and cannot be expected
    # to compete with a fully invested index on return. The SELECTION line is the fair comparison.
    at_risk = pd.Series(dict(risk_log)).sort_index().reindex(eq.index).fillna(0.0)
    cash = (eq - at_risk).clip(lower=0.0)
    return pd.DataFrame(trades), eq, held, cash, costs_total


FNO_DOC = {
    "key": "fno_income",
    "name": "Index option credit spreads",
    "description": "Sell a {SHORT_DELTA}-delta NIFTY credit spread {WIDTH_PCT}% wide, "
                   "{DTE_MIN}-{DTE_MAX} days out, only when India VIX is at or above its "
                   "{VIX_PERCENTILE}th percentile: a put spread above the {TREND_SMA}-day average, a "
                   "call spread below a falling one. Take half the credit, stop at "
                   "{STOP_CREDIT_MULT}x it, or close {CLOSE_DAYS_BEFORE} days before expiry.",
    "status": (
        "THE RESULT IS THE COST ASSUMPTION, AND THE DATA CANNOT SUPPLY IT. Swept 24 "
        "configurations on NIFTY from 2012 -- 2 structures x 3 short deltas x 4 slippage "
        "assumptions -- and ALL 24 cross from positive to negative between 2 and 4 index points of "
        "assumed slippage per leg. Not most of them: all of them. A short-premium strategy's "
        "verdict here is a number nobody measured, because `derivatives_bhav` is NSE's bhavcopy "
        "and carries no bid or ask. "
        "Best case, put spreads at a 0.35 delta with 1 point per leg: CAGR 1.06%, SELECTION +0.97, "
        "71.6% win rate over 264 trades, max drawdown -4.4%. Worst case, condors at 0.35 delta with "
        "6 points: CAGR -3.06%, selection -3.20, 48.4% win rate, max drawdown -37.2%. "
        "EVEN THE BEST CASE CANNOT COMPOUND, which is the more useful finding. At the guide's own "
        "sizing -- {RISK_PCT}% of capital at risk, one structure at a time -- the strategy has 0.6% "
        "of the book at risk on an average day. A genuine +1 CAGR point of selection on a 0.6% risk "
        "budget is not a strategy, it is a rounding error with excellent risk control. To matter it "
        "would have to be run at many multiples of this size, and the loss distribution (see the "
        "caveats) is the reason that is how option sellers go broke. "
        "The win rates are the textbook shape and decay the right way: 71-77% at 1-2 points, "
        "falling to 48-50% at 6 points, because slippage eats the many small wins first while the "
        "few large losses were never small. "
        "Condors are worse than single spreads at every delta, and the gap widens with delta "
        "(-0.07 vs +0.97 at 0.35 delta, 1 point). Selling both sides doubles the chance of a "
        "breach for premium that does not double."
    ),
    "thesis": "Index options usually price more movement than arrives, so a seller who stays far "
              "enough from the money collects the difference. This is the only CARRY mechanism in the "
              "Learn module: it is paid for time passing rather than for being right about "
              "direction. That is why it is worth measuring even though the answer turns out to be "
              "a cost assumption.",
    "how_it_works": (
        "The idea. Sell a NIFTY credit spread when options are expensive, on the side the trend "
        "favours, and buy it back early — at half the profit, at a loss of about one credit, or a "
        "{CLOSE_DAYS_BEFORE} days before expiry.",
        "A credit spread. Sell one option close to the money and buy one further out of the money, "
        "same type and expiry. The bought option caps the loss: the most the spread can lose is the "
        "gap between the strikes minus the credit received.",
        "Steps, each session, in order: price the open structure off that day's chain and close it "
        "if an exit applies (see Exit); then, if flat, check the volatility gate, pick the expiry, "
        "the side and the strikes, and sell (see Entry). One structure at a time; a new one can "
        "open on the session the previous one closed.",
        "Data and timing. {UNDERLYING} index options from NSE's daily bhavcopy, India only. Option "
        "prices are the day's exchange settlement price (its close where no settle is given), the "
        "index level is the Nifty 50 close, and the volatility gate reads India VIX. Everything is "
        "end of day. The data has no bid or ask (see Caveats).",
        "Where the rules come from. The Learn guide's income chapter; the credit test departs from "
        "it (see Entry). There is no written spec with row ids for this strategy.",
    ),
    "entry_rules": (
        "Volatility gate. India VIX at or above the {vix_percentile}th percentile of its last "
        "{VIX_WINDOW} sessions, that day included (at least 120 sessions of history needed). A "
        "percentile rather than a level, because a VIX of 15 meant something different in 2017 than "
        "in 2020.",
        "Expiry. The nearest listed expiry, weekly or monthly, between {DTE_MIN} and {DTE_MAX} "
        "calendar days away. None in that range: no trade that day.",
        "Which side. Set by the Nifty 50 against its {TREND_SMA}-day simple average (`structure`, "
        "default {structure}).\n\n"
        "- **Close above the average:** sell a put spread.\n"
        "- **Close below it, the average lower than 20 calendar days earlier:** sell a call "
        "spread.\n"
        "- **Close below it, the average not falling:** no trade.\n"
        "- **`condor`:** sells a put spread and a call spread together whatever the trend; both "
        "sides must pass every test below or neither is sold.\n"
        "- **`both_sides`:** currently behaves exactly like the default.",
        "Open interest. Only strikes with open interest of at least {MIN_OPEN_INTEREST} are "
        "considered, for both legs. The bhavcopy counts open interest in units of the index, not in "
        "contracts, so this is a floor of a few lots — a loose one.",
        "Short strike. The strike whose delta, ignoring sign, is nearest {short_delta}, accepted "
        "only within {DELTA_TOL} of it. Otherwise no trade: the nearest available strike is never "
        "substituted.\n\n"
        "- **Implied volatility:** found per option by inverting Black-Scholes on its own settle "
        "price, searched between 1% and 300%. A price below 98% of intrinsic value is treated as "
        "stale and the strike dropped.\n"
        "- **Delta:** Black-Scholes delta from that volatility. Time to expiry is calendar days ÷ "
        "365.25, the rate is the RBI repo rate on the day, dividends are left out.\n"
        "- **Why per option:** one index-level volatility would ignore the skew, and selling the "
        "skew is the point.",
        "Long (protective) strike. The nearest listed strike at least {width_pct}% of the index level "
        "further out of the money: below the sold put, above the sold call. The width is the actual "
        "gap between the two strikes.",
        "Credit test. Credit is the sold leg's settle minus the bought leg's settle, in index "
        "points. It must be positive, and credit ÷ width at least {MIN_CREDIT_VS_DELTA} times the "
        "sold leg's delta — with a {SHORT_DELTA}-delta short, at least {MIN_CREDIT_VS_DELTA} × "
        "{SHORT_DELTA} of the width.\n\n"
        "- **Differs from the guide:** the guide asks for a credit of at least 25% of the width. "
        "Credit ÷ width runs at roughly 0.73 times the short delta, so that rule and the guide's "
        "delta range cannot both hold; the flat rule admits only 1-7% of chains.",
        "Fill. Both legs trade at that session's settle prices — the prices the decision was made "
        "on. No slippage is charged at entry; the whole round trip's cost is charged at the exit.",
        "Position size. The quantity is set so that the maximum loss is {risk_pct}% of the current "
        "equity.\n\n"
        "- **Maximum loss:** the width minus the credit, in index points. A condor's is the wider "
        "side's width minus the total credit, because the index cannot finish beyond both sold "
        "strikes.\n"
        "- **Quantity:** equity × {risk_pct}% ÷ maximum loss, using realised equity only. It is a "
        "fractional number of index units, not whole exchange lots, and margin is not modelled.",
        "When no trade is taken. A structure is already open; the VIX gate fails; no expiry is in "
        "range; the trend picks neither side; or a leg fails the delta, strike, open-interest or "
        "credit test.",
    ),
    "exit_rules": (
        "Daily mark. Each session after the entry, the structure is priced at what it costs to buy "
        "back: the sold legs' settle minus the bought legs' settle, for the same strikes, from that "
        "day's stored chain — never a model price, which would replace the market's own skew with "
        "the model's and flatter the seller exactly when the skew steepens. A leg with no stored "
        "price that day is valued at its intrinsic value. The first rule below that applies closes "
        "the whole structure at that day's mark.",
        "Profit target. The mark is at or below (1 − {PROFIT_TARGET_FRAC}) times the credit, so at "
        "least {PROFIT_TARGET_FRAC} of the maximum profit is kept. There is no resting order: it is "
        "checked on the day's settle, and the exit is at that settle, which can be better than the "
        "target. The rest of the credit takes longest to earn and carries the most gamma.",
        "Stop. The mark is at or above {STOP_CREDIT_MULT} times the credit received, which is a loss "
        "of about one credit plus costs. It is checked only on the day's settle, so a gap can carry "
        "the mark well past {STOP_CREDIT_MULT} times the credit before it is seen. The loss is then "
        "limited only by the spread's maximum loss (width minus credit).",
        "Time exit. With {CLOSE_DAYS_BEFORE} calendar days or fewer to expiry the structure is "
        "closed regardless, so nothing is held into expiry-week gamma and nothing is held to expiry.",
        "Order. The profit target is tested first, then the stop, then the time exit. On a day with "
        "no stored chain for the expiry, the target and the stop are skipped; only the time exit "
        "can act.",
        "Cost. {cost_points} index points per leg for the round trip (2 legs for a spread, 4 for a "
        "condor), times the quantity, charged at the exit. It stands in for the bid-ask spread and "
        "every other charge, none of which the data carries.",
    ),
    "caveats": (
        "**NO BID/ASK EXISTS IN THE DATA, and it decides the answer.** The bhavcopy carries settle, "
        "close, volume and open interest, not quotes. Sellers pay the spread twice per leg, four "
        "times for a condor, and that cost is assumed here rather than measured. Since all 24 swept "
        "configurations change sign between 2 and 4 points per leg, no configuration of this "
        "strategy can be called profitable or unprofitable from stored data alone. Live quote "
        "capture is the only thing that would settle it.",
        "**The loss distribution is the real risk and a daily backtest understates it.** Marks come "
        "from daily settle prices, so a gap that opens through both strikes is scored at the day's "
        "settle rather than at what it would have cost to get out during the day. Short premium "
        "fails on exactly those days.",
        "**The equity curve counts only closed structures.** An open structure is not marked into "
        "the curve, so a loss that builds and then recovers before the exit never shows as a "
        "drawdown. The measured drawdown is a floor.",
        "**A missing chain on a time-exit day is priced wrongly (a code flaw, noted not fixed).** "
        "If no chain is stored for the expiry on that day, the exit price is the distance from the "
        "index to the first sold strike, capped at the width. That is backwards for a spread still "
        "out of the money: it books a winning spread as a loss of up to the full width. It needs a "
        "day with no stored chain, so it is rare.",
        "**It risks under 1% of the book, so it cannot be compared with a fully invested index on "
        "return.** The headline excess is about -11 CAGR points in every cell and that number is "
        "meaningless; SELECTION is the fair comparison and it ranges +0.97 to -3.20.",
        "**Index options only.** The stored derivatives data is NSE's, so the guide's covered calls "
        "and cash-secured puts on individual stocks are not tested, and there are no US chains. The "
        "stored S&P500 OPTIDX rows are NSE's cross-listed contract, which stopped trading in 2017.",
        "**No event filter.** The guide excludes results, RBI policy and the Budget before expiry. "
        "RBI and Budget dates are not stored as a series, so that filter is absent, which should "
        "make this result slightly WORSE than a faithful implementation, not better.",
        "**Dividends are omitted from the pricing model.** NIFTY's yield is around 1.2% and enters "
        "delta an order of magnitude below the uncertainty in the recovered implied volatility.",
    ),
}


class FnoIncomeStrategy(PortfolioStrategy):
    """NIFTY credit spreads and iron condors, as the Learn income guide states them.

    India-only by construction: there are no stored US index option chains. `run()` raises with
    that explanation rather than failing somewhere downstream.
    """

    key = FNO_DOC["key"]
    doc = FNO_DOC
    family = "fno_income"
    version = "1.0"
    changelog = (("1.0", "2026-10-18",
                  "First version. Implied volatility and delta are recovered per leg by inverting "
                  "Black-Scholes on its own settle price; validated against an independent series -- "
                  "on 2024-06-03 the recovered at-the-money IVs were 21.2% (call) and 19.4% (put) "
                  "against a published India VIX of 20.9, with the expected put skew. The guide's "
                  "'credit >= 25% of width' is replaced by a delta-relative test, because measurement "
                  "showed the guide's two rules cannot both hold: credit/width is close to an identity "
                  "with the short delta, so the flat rule admitted 1-7% of chains and left 23 trades "
                  "in fourteen years."),)
    name = FNO_DOC["name"]
    description = FNO_DOC["description"]
    status = FNO_DOC["status"]
    thesis = FNO_DOC["thesis"]
    how_it_works = tuple(FNO_DOC["how_it_works"])
    caveats = tuple(FNO_DOC["caveats"])
    entry_rules = tuple(FNO_DOC["entry_rules"])
    exit_rules = tuple(FNO_DOC["exit_rules"])

    behaviour = "carry"
    selection = "time_series"
    style = "pullback"
    runner = "fno_income"

    structure = "put_spread"
    short_delta = SHORT_DELTA
    width_pct = WIDTH_PCT
    risk_pct = RISK_PCT
    vix_percentile = VIX_PERCENTILE
    cost_points = 2.0

    param_docs = (
        ("Structure", "structure", "put_spread sells one side by trend; condor sells both."),
        ("Short delta", "short_delta", "Target delta of the sold leg; the guide suggests 0.15-0.30."),
        ("Spread width", "width_pct", "Strike gap as a percent of the index."),
        ("Risk per trade", "risk_pct", "Percent of capital at MAXIMUM LOSS, never at margin."),
        ("VIX percentile", "vix_percentile", "India VIX must be at least this percentile of the trailing year."),
        ("Slippage per leg", "cost_points", "Index points assumed per leg. THE load-bearing assumption -- "
                                            "every swept configuration changes sign between 2 and 4."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Selling NIFTY index option credit spreads")
    ap.add_argument("--strategy", default="fno_income")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--structure", default=FnoIncomeStrategy.structure, choices=list(STRUCTURES))
    ap.add_argument("--short-delta", type=float, default=FnoIncomeStrategy.short_delta)
    ap.add_argument("--width-pct", type=float, default=FnoIncomeStrategy.width_pct)
    ap.add_argument("--risk-pct", type=float, default=FnoIncomeStrategy.risk_pct)
    ap.add_argument("--vix-percentile", type=float, default=FnoIncomeStrategy.vix_percentile)
    ap.add_argument("--cost-points", type=float, default=FnoIncomeStrategy.cost_points)
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    cfg = MARKETS[a.market]
    ctx = load_context(a.market)
    tdf, eq, held, csh, costs = run(
        a.market, a.start, structure=a.structure, short_delta=a.short_delta,
        width_pct=a.width_pct, risk_pct=a.risk_pct, vix_percentile=a.vix_percentile,
        cost_points=a.cost_points, preloaded=ctx)

    bc = ctx["spot"].reindex(eq.index).ffill()
    notes = [
        f"{len(tdf):,} structures over the window, one at a time. Marked daily off the stored chain "
        "for the same strikes, never re-modelled.",
        f"THE SIGN OF THIS RESULT IS THE SLIPPAGE ASSUMPTION ({a.cost_points:g} index points per leg). "
        "The bhavcopy carries no bid or ask, and all 24 swept configurations change sign between 2 and "
        "4 points per leg. Treat the headline as conditional on that number.",
        f"Risk is {a.risk_pct:g}% of capital at MAXIMUM LOSS per structure, so under 1% of the book is "
        "at risk on an average day. The headline excess against a fully invested index is therefore "
        "meaningless; read SELECTION.",
        "Each leg's implied volatility and delta come from inverting Black-Scholes on its own settle "
        "price, with the day's repo rate. Dividends are omitted (NIFTY yields ~1.2%).",
        "No event filter: RBI policy and Budget dates are not stored, so the guide's rule to avoid "
        "them before expiry is absent. That makes this slightly worse than a faithful implementation.",
    ]
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=1,
                           costs_paid=costs, bench_close=bc, cash=csh, notes=notes)
    for k, v in metrics.benchmark_stats(bc).items():
        setattr(perf, k, v)
    perf.benchmark_name = "NIFTY50 (^NSEI)"

    name = (f"{a.start}_{a.structure}_d{a.short_delta:g}_w{a.width_pct:g}pct"
            f"_risk{a.risk_pct:g}_vix{a.vix_percentile:g}_slip{a.cost_points:g}pt"
            f"_{FnoIncomeStrategy.spec_id()}")
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "cash": csh, "positions_open": held,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, 1))
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"{cfg.name} — NIFTY option credit spreads ({a.structure}), {a.start} onward",
            perf, eq, held, tdf, cfg.currency_symbol, 1, bc,
            f"python3 -m swing_screener.backtesting.fno_income --market {a.market} --start {a.start}")
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
