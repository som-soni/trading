"""Classic trend following by channel breakouts -- the Turtle pair, traded as it was meant to be.

The claim under test (TODO, 2026-10-22/24): buy a close above the 20- or 55-day high, short a close
below the low, risk about 1% of the account with a 2 ATR stop, exit on the opposite 10- or 20-day
extreme; decades of positive expectancy on futures, a win rate near 45%, the money from a few big
trends, long flat spells. That is a hypothesis here, not a fact.

WHY NOT `donchian`. The `donchian` strategy runs the same channel idea long-only on single stocks,
and its own caveats say why that cannot test this claim: the Turtle edge was a DIVERSIFIED, LONG AND
SHORT book across asset classes, where a bond or a commodity trend pays while equities chop. This
runner trades that book: a small fixed universe of US-listed ETFs standing in for futures (equity
indices, Treasuries, metals, energy, agriculture, the dollar), both directions.

WHY ITS OWN RUNNER. The per-symbol engine (`backtest.py`, `portfolio_sim.py`) is long-only and ranks
a stock universe; `stage4_shorts` has a short-only simulator for stocks. A two-direction book on
thirteen fixed instruments needs a few dozen lines of simulation, so it is written here, and the
pieces of `stage4_shorts` that fit -- the month-end sleeve `blend`, the stats helper, finding the
stored long book of the same stage -- are imported from it rather than copied.

THE FUTURES SERIES ARE NOT USED. `index_series` holds GOLD_FUT, WTI, NATGAS and COPPER, but as
unadjusted front-month CLOSES: no high, low or open (so no ATR, no stop fill), and a roll gap every
month (WTI prints -37.63 in April 2020). A breakout system reads roll gaps as trends. India's
`derivatives_bhav` has NIFTY/BANKNIFTY futures, but no loader that builds a back-adjusted continuous
contract honouring the stage boundary, and two Indian index contracts in rupees are not a
diversified book beside a dollar one. See the caveats.

PRICES ARE NOT DIVIDEND-ADJUSTED. Stored ETF prices are split-adjusted only (SPY's price rose 3.25x
over 2013-2021, the stored S&P 500 total return 3.84x), so each instrument's distribution yield is
credited to a long and charged to a short, from ASSETS.
"""
from __future__ import annotations

import argparse
import logging
import math

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..core import indicators as ind
from ..marketdata import cache, index_data
from ..strategies.base import PortfolioStrategy
from . import metrics
from .stage4_shorts import _stats, blend, find_long_book

logger = logging.getLogger("backtest")

#: (symbol, asset class, distribution yield % a year, 2013-2021 approximately). The yield is credited
#: to a long and charged to a short, because stored prices are not dividend-adjusted. Commodity and
#: currency ETFs pay (almost) nothing; their roll cost is already inside their price.
ASSETS = (
    ("SPY", "equity", 1.9), ("QQQ", "equity", 0.8), ("EFA", "equity", 2.8), ("EEM", "equity", 2.2),
    ("TLT", "bonds", 2.5), ("IEF", "bonds", 1.8),
    ("GLD", "metals", 0.0), ("SLV", "metals", 0.0),
    ("USO", "energy", 0.0), ("UNG", "energy", 0.0), ("DBC", "commodities", 0.3), ("DBA", "commodities", 0.0),
    ("UUP", "currency", 0.0),
)

# ---- the two systems: (entry channel, exit channel), in sessions. A close beyond the prior N
# sessions' extreme enters at the next open; a close beyond the prior M sessions' opposite extreme exits.
S1_ENTRY = 20
S1_EXIT = 10
S2_ENTRY = 55
S2_EXIT = 20
ATR_BARS = 20                 # the Turtles' N: a 20-session average true range
STOP_ATR = 2.0                # initial stop, in N, from the fill; it never moves (the channel exit trails)

# ---- size
RISK_PCT = 1.0                # of equity, from the fill to the 2N stop, per trade
MAX_OPEN_RISK_PCT = 10.0      # initial risk of all open positions together, % of current equity
MAX_POSITION_PCT = 50.0       # one position's notional, % of equity: a bond ETF's N is ~0.5% of price,
                              # so 1% risk would otherwise buy twice the account in IEF
MAX_GROSS_PCT = 200.0         # long plus short notional: Reg T margin, not futures leverage

# ---- costs, explicit; COST_LEVELS scales the trading, borrow and margin costs (not the yields)
COST_BPS = 5.0                # per side: spread and slippage on a liquid ETF
BORROW_PCT = 1.0              # a year, of short notional: general collateral for these ETFs runs under it
MARGIN_RATE_PCT = 2.0         # a year, on cash borrowed when long notional exceeds the cash
COST_LEVELS = (0.5, 1.0, 2.0)

# ---- the judgement: benchmark, the long book it is blended with, the sleeve weights tried
BENCH_EQUITY_PCT = 60         # a 60/40 of the stored total-return series, rebalanced at month-ends
LONG_BOOK = "momentum_baseline"
SLEEVE_WEIGHTS = (0, 20, 30, 50)
TOP_SHARE_PCT = 10            # "the money comes from a few big trends": gross-profit share of the best this %
MIN_HISTORY = 300             # bars an ETF needs before the window opens


def system_params(system: str) -> tuple[int, int]:
    return {"1": (S1_ENTRY, S1_EXIT), "2": (S2_ENTRY, S2_EXIT)}[system]


def load(market: str) -> dict:
    """{symbol: frame with OHLC, ATR and the four channels}, read through the bounded loaders."""
    if market != "us":
        raise SystemExit(f"{market}: the cross-asset ETF universe is US-listed; no {market} universe is defined")
    out = {}
    for sym, _cls, _y in ASSETS:
        d = cache.load_cached(market, sym)
        if d is None or len(d) < MIN_HISTORY:
            logger.warning("%s: not enough stored history, left out", sym)
            continue
        d = d[["open", "high", "low", "close"]].astype(float)
        f = d.copy()
        f["atr"] = ind.atr(d, ATR_BARS)
        for n in sorted({S1_ENTRY, S1_EXIT, S2_ENTRY, S2_EXIT}):
            f[f"hi{n}"] = d["high"].shift(1).rolling(n).max()   # the PRIOR n sessions, not today
            f[f"lo{n}"] = d["low"].shift(1).rolling(n).min()
        out[sym] = f
    return out


def run(frames: dict, start: str, system: str, cost_level: float = 1.0, account: float = 50_000.0):
    """Simulate one system. Returns (trades, equity, positions open, gross %, costs paid)."""
    n_in, n_out = system_params(system)
    yld = {s: y / 100 / 252 for s, _c, y in ASSETS}
    cls = {s: c for s, c, _y in ASSETS}
    side = COST_BPS * cost_level / 10_000
    borrow_day = BORROW_PCT * cost_level / 100 / 252
    margin_day = MARGIN_RATE_PCT * cost_level / 100 / 252
    cal = sorted(set().union(*[f.index[f.index >= pd.Timestamp(start)] for f in frames.values()]))
    cash = float(account)
    pos: dict = {}            # symbol -> position
    pending_in: dict = {}     # symbol -> (direction +1 / -1, N at the signal), from yesterday's close
    pending_out: set = set()
    last: dict = {}
    trades, eq_log, held_log, gross_log = [], [], [], []
    costs = 0.0
    skipped = {"risk_budget": 0, "gross_cap": 0}

    def value(sym, p):
        return p["dir"] * p["shares"] * last.get(sym, p["price"])

    def close_out(sym, d, price, reason):
        nonlocal cash, costs
        p = pos.pop(sym)
        fee = p["shares"] * price * side
        cash += p["dir"] * p["shares"] * price - fee
        costs += fee
        pnl = p["dir"] * p["shares"] * (price - p["price"]) - fee - p["fee"] + p["carry"]
        risk = p["shares"] * p["risk_ps"]
        trades.append({
            "symbol": sym, "asset_class": cls[sym], "system": f"S{system}",
            "direction": "long" if p["dir"] > 0 else "short", "setup": f"S{system}",
            "entry_date": p["date"], "entry_price": round(p["price"], 4), "initial_stop": round(p["stop"], 4),
            "exit_date": d, "exit_price": round(price, 4), "shares": round(p["shares"], 4),
            "exit_reason": reason, "pnl": round(pnl, 2), "notional": round(p["shares"] * p["price"], 2),
            "costs": round(fee + p["fee"], 2), "carry": round(p["carry"], 2),
            "holding_days": (d - p["date"]).days, "sessions": p["n"],
            "r_multiple": round(pnl / risk, 4) if risk > 0 else float("nan"),
            "mfe_r": round(p["mfe"] / p["risk_ps"], 3) if p["risk_ps"] > 0 else float("nan"),
        })

    for d in cal:
        equity = cash + sum(value(s, p) for s, p in pos.items())
        # ---- at the open: exits first (a reversal frees its slot), then entries
        for s in list(pending_out):
            f = frames[s]
            if s in pos and d in f.index:
                close_out(s, d, float(f.at[d, "open"]), "CHANNEL")
        pending_out = set()
        for s, (direction, n) in pending_in.items():
            f = frames[s]
            if s in pos or d not in f.index:
                continue
            o = float(f.at[d, "open"])
            risk_ps = STOP_ATR * n
            # INITIAL risk, the Turtles' unit count: the stop is fixed, so risk to it measured at the last
            # close grows as a winner runs and would block new trends for being right about old ones
            open_risk = sum(p["shares"] * p["risk_ps"] for p in pos.values())
            budget = min(equity * RISK_PCT / 100, equity * MAX_OPEN_RISK_PCT / 100 - open_risk)
            gross = sum(abs(value(x, p)) for x, p in pos.items())
            room = equity * MAX_GROSS_PCT / 100 - gross
            if budget <= equity * RISK_PCT / 100 * 0.25:
                skipped["risk_budget"] += 1
                continue
            if room <= equity * 0.01:
                skipped["gross_cap"] += 1
                continue
            shares = min(budget / risk_ps, equity * MAX_POSITION_PCT / 100 / o, room / o)
            fee = shares * o * side
            cash -= direction * shares * o + fee
            costs += fee
            pos[s] = {"dir": direction, "shares": shares, "price": o, "fee": fee, "date": d,
                      "stop": o - direction * risk_ps, "risk_ps": risk_ps, "n": 0, "carry": 0.0, "mfe": 0.0}
        pending_in = {}
        # ---- intraday: the 2N stop. A gap through it fills at the open.
        for s in list(pos):
            f, p = frames[s], pos[s]
            if d not in f.index:
                continue
            p["n"] += 1
            o, hi, lo = float(f.at[d, "open"]), float(f.at[d, "high"]), float(f.at[d, "low"])
            hit = lo <= p["stop"] if p["dir"] > 0 else hi >= p["stop"]
            if hit:
                gapped = o <= p["stop"] if p["dir"] > 0 else o >= p["stop"]
                close_out(s, d, o if (gapped and p["date"] != d) else p["stop"], "STOP")
                continue
            p["mfe"] = max(p["mfe"], (hi - p["price"]) if p["dir"] > 0 else (p["price"] - lo))
        # ---- at the close: carry, then tomorrow's exits and entries
        for s, f in frames.items():
            if d in f.index:
                last[s] = float(f.at[d, "close"])
        for s, p in pos.items():
            notional = p["shares"] * last[s]
            c = notional * yld[s] if p["dir"] > 0 else -notional * (yld[s] + borrow_day)
            cash += c
            p["carry"] += c
            if p["dir"] < 0:
                costs += notional * borrow_day   # the yield a short pays is carry, not a cost
        long_notional = sum(p["shares"] * last[s] for s, p in pos.items() if p["dir"] > 0)
        short_proceeds = sum(p["shares"] * last[s] for s, p in pos.items() if p["dir"] < 0)
        # cash below zero, not counting short proceeds (held as collateral, earning nothing), is a loan
        loan = max(-(cash - short_proceeds), 0.0) if long_notional > 0 else 0.0
        if loan:
            cash -= loan * margin_day
            costs += loan * margin_day
        for s, f in frames.items():
            if d not in f.index:
                continue
            r = f.loc[d]
            cl = float(r["close"])
            if s in pos:
                p = pos[s]
                if (p["dir"] > 0 and cl < r[f"lo{n_out}"]) or (p["dir"] < 0 and cl > r[f"hi{n_out}"]):
                    pending_out.add(s)
                else:
                    continue
            if not (r["atr"] > 0):
                continue
            if cl > r[f"hi{n_in}"]:
                pending_in[s] = (1, float(r["atr"]))
            elif cl < r[f"lo{n_in}"]:
                pending_in[s] = (-1, float(r["atr"]))
        # a reversal: the exit and the opposite entry both go at tomorrow's open, so the entry must not be
        # blocked by the position it replaces -- `pending_in` is processed after `pending_out`
        val = cash + sum(value(s, p) for s, p in pos.items())
        eq_log.append((d, val))
        held_log.append((d, len(pos)))
        gross_log.append((d, sum(abs(value(s, p)) for s, p in pos.items()) / val * 100 if val > 0 else np.nan))
    for s in list(pos):
        close_out(s, cal[-1], last[s], "OPEN")
    return (pd.DataFrame(trades), pd.Series(dict(eq_log)).sort_index(),
            pd.Series(dict(held_log)).sort_index(), pd.Series(dict(gross_log)).sort_index(), costs, skipped)


# ------------------------------------------------------------------ the measurements the claim is judged on

def trade_profile(t: pd.DataFrame) -> dict:
    """Win rate, average win and loss in R, the top-decile share of gross profit, long vs short P&L."""
    closed = t[t["exit_reason"] != "OPEN"] if len(t) else t
    if not len(closed):
        return {}
    wins, losses = closed[closed["pnl"] > 0], closed[closed["pnl"] <= 0]
    k = max(1, int(math.ceil(len(t) * TOP_SHARE_PCT / 100)))
    total = float(t["pnl"].sum())
    gross_profit = float(t.loc[t["pnl"] > 0, "pnl"].sum())
    top = float(t["pnl"].nlargest(k).sum())
    return {
        "trades": int(len(t)), "win_rate_pct": round(len(wins) / len(closed) * 100, 1),
        "avg_win_r": round(float(wins["r_multiple"].mean()), 2) if len(wins) else float("nan"),
        "avg_loss_r": round(float(losses["r_multiple"].mean()), 2) if len(losses) else float("nan"),
        "avg_r": round(float(closed["r_multiple"].mean()), 3),
        # of GROSS profit (winning trades only): a share of net P&L passes 100% whenever losers eat most of it
        "top_share_pct": round(top / gross_profit * 100, 1) if gross_profit > 0 else float("nan"),
        "top_pnl": round(top, 0), "gross_profit": round(gross_profit, 0), "total_pnl": round(total, 0),
        "long_pnl": round(float(t.loc[t["direction"] == "long", "pnl"].sum()), 0),
        "short_pnl": round(float(t.loc[t["direction"] == "short", "pnl"].sum()), 0),
    }


def sixty_forty() -> pd.Series:
    """The benchmark: 60% S&P 500 / 40% 7-10y Treasuries, both total return, month-end rebalanced."""
    eq = index_data.load("us", "SP500_TR")
    bd = index_data.load("us", "BONDS")
    idx = eq.index.intersection(bd.index)
    return blend(eq.reindex(idx), bd.reindex(idx), 100 - BENCH_EQUITY_PCT)


def monthly_corr(a: pd.Series, b: pd.Series) -> float:
    ra = a.resample("ME").last().pct_change()
    rb = b.resample("ME").last().pct_change()
    j = pd.concat([ra, rb], axis=1).dropna()
    return float(j.iloc[:, 0].corr(j.iloc[:, 1])) if len(j) > 6 else float("nan")


def sleeve_table(long_eq: pd.Series, trend_eq: pd.Series) -> tuple[pd.DataFrame, str]:
    """The long book with the trend book as a sleeve at each weight, beside the same weight in cash --
    the control: a book that is often small dilutes a drawdown by being there, hedge or not."""
    flat = pd.Series(1.0, index=trend_eq.index)
    rows = []
    for w in SLEEVE_WEIGHTS:
        for kind in (("trend",) if w == 0 else ("trend", "cash")):
            e = blend(long_eq, trend_eq if kind == "trend" else flat, w)
            st = _stats(e)
            rows.append({"sleeve_pct": w, "sleeve": "none" if w == 0 else kind,
                         "cagr_pct": round(st["cagr"], 2), "max_dd_pct": round(st["max_dd"], 2),
                         "vol_pct": round(st["vol"], 2), "sharpe": round(st["sharpe"], 3)})
    t = pd.DataFrame(rows)
    md = ["| Sleeve | CAGR | Max DD | Vol | Sharpe |", "|---|---|---|---|---|"]
    md += [f"| {r['sleeve_pct']}% {r['sleeve']} | {r['cagr_pct']:+.2f}% | {r['max_dd_pct']:.1f}% | "
           f"{r['vol_pct']:.1f}% | {r['sharpe']:.2f} |" for r in rows]
    return t, "\n".join(md)


# ------------------------------------------------------------------ documentation

DOC = {
    "key": "turtle_trend",
    "name": "Cross-asset trend following (Turtle breakouts)",
    "description": (
        "Long a close above the prior {S1_ENTRY}-session high (System 1) or {S2_ENTRY}-session high "
        "(System 2), short a close below the low, across {n_assets} ETFs standing in for futures -- "
        "equity indices, Treasuries, metals, energy, agriculture, the dollar. {RISK_PCT}% of equity "
        "risked to a {STOP_ATR} N stop; out on the opposite {S1_EXIT}- or {S2_EXIT}-session extreme."
    ),
    "status": (
        "FAILS ITS PASS CRITERION ON THE OPTIMISE STAGE (2013-2021, US, base costs; measured "
        "2026-10-25, v1.0). Not sent to verify. System 2 (55/20): CAGR +1.4%, max drawdown -35%, "
        "Sharpe 0.17 against the 60/40's +10.8%, -19% and 1.16; 483 trades, 31% winners, average win "
        "+2.8R, loss -1.0R; long +$17.6k, short -$8.8k, and one year (2020, +39%) carries the whole "
        "result. At twice the costs it loses (-0.3%). System 1 (20/10): -8.6% a year, -68% drawdown, "
        "shorts of equity indices lost most. Both, 50/50: -3.5%. What held: monthly correlation to SPY "
        "is near zero (-0.09 to +0.01) and to the momentum book about -0.1, and a 20-50% System 2 sleeve "
        "beat the same weight in cash beside momentum_baseline (Sharpe 0.18-0.21 against 0.16-0.15) -- "
        "but on an 0.17 Sharpe standalone that is a weak diversifier, not an edge. The claim's 45% win "
        "rate did not appear (30-31%); its shape -- many small losses, a few large trends -- did."
    ),
    "thesis": (
        "Prices trend across asset classes more often than chance: a market that has broken out keeps "
        "going for months often enough that a few large winners pay for many small stopped-out losses "
        "(time-series momentum: Moskowitz, Ooi and Pedersen 2012, on 58 futures and forwards; Hurst, "
        "Ooi and Pedersen's century of trend following). The edge lives in the DIVERSIFIED, LONG AND "
        "SHORT book -- a bond, gold or dollar trend pays while equities chop or fall -- which is why it "
        "is tested here across asset classes and both directions, not on stocks (see donchian)."
    ),
    "how_it_works": (
        "The idea. Follow every big move in any of a dozen markets, in either direction, with a stop "
        "small enough that most losers cost about 1% of the account, and let the winners run until the "
        "trend reverses. Expect to lose on more than half the trades.",
        "The universe. {n_assets} US-listed ETFs: SPY, QQQ, EFA, EEM (equities), TLT, IEF (Treasuries), "
        "GLD, SLV (metals), USO, UNG (energy), DBC, DBA (broad commodities, agriculture), UUP (the "
        "dollar). Daily bars, stored, split-adjusted.",
        "Step 1 -- the breakout. After each close: a close above the highest high of the prior N "
        "sessions is a long signal, a close below the lowest low a short signal. System 1: N = "
        "{S1_ENTRY}. System 2: N = {S2_ENTRY}.",
        "Step 2 -- the trade, at the next open, sized so the {STOP_ATR} N stop from the fill risks "
        "{RISK_PCT}% of equity (N = the {ATR_BARS}-session average true range), within the caps on "
        "open risk, one position's size and gross exposure.",
        "Step 3 -- the exit: the stop, intraday; or a close beyond the opposite extreme of the prior "
        "M sessions (System 1: M = {S1_EXIT}, System 2: M = {S2_EXIT}), at the next open. A reversal "
        "exits and enters the other way on the same open.",
        "Judged three ways. Standalone against a {BENCH_EQUITY_PCT}/40 stock/bond blend; by the shape "
        "of its trades (win rate, average win and loss in R, the share of profit from the top "
        "{TOP_SHARE_PCT}% of trades, long against short); and as a sleeve beside the momentum_baseline "
        "run of the same stage, against the same weight held in cash.",
        "Running it. `python -m jobs enqueue backtest --market us --strategies turtle_trend --stage "
        "optimise --bt '--system 2'`; `--system` is 1, 2 or both (50/50, rebalanced monthly).",
    ),
    "entry_rules": (
        "Breakout. Today's close above the highest high of the prior N sessions (long) or below the "
        "lowest low (short); today's bar is not in the channel. N = {S1_ENTRY} for System 1, "
        "{S2_ENTRY} for System 2.\n\n**Claim (TODO):** the same, on a close. Differs from the original "
        "Turtle rules: those entered intraday on the touch, added units every half N up to four, and "
        "skipped a System 1 breakout after a winning one -- none of that is here.",
        "Fill. At the next session's open. One position per instrument per system.",
        "Size. Units = {RISK_PCT}% of equity / ({STOP_ATR} × N at the signal). Cut so that the initial "
        "risk of all open positions stays within {MAX_OPEN_RISK_PCT}% of equity, one position's notional within "
        "{MAX_POSITION_PCT}% and long plus short notional within {MAX_GROSS_PCT}%. Fractional shares.\n\n"
        "**Claim:** risk about 1% with a 2 ATR stop -- the same. The position and gross caps are "
        "added: an ETF account cannot take a futures account's leverage, so a Treasury position is "
        "often capped below its 1%-risk size.",
        "Costs (base case). {COST_BPS} bps a side; shorts pay a borrow fee of {BORROW_PCT}% a year and "
        "the ETF's distribution yield; longs are credited the yield (stored prices exclude it); cash "
        "borrowed when longs exceed it costs {MARGIN_RATE_PCT}% a year. Every run also reports "
        "{COST_LEVELS} times the trading, borrow and margin costs.",
    ),
    "exit_rules": (
        "Each session the stop is checked first, then the channel exit at the close.",
        "Stop. {STOP_ATR} N from the fill, fixed. The day's low (long) or high (short) through it exits "
        "at the stop, or at the open when the open is already past it.",
        "Channel exit. A close below the lowest low of the prior M sessions (long) or above the highest "
        "high (short) exits at the next open. M = {S1_EXIT} for System 1, {S2_EXIT} for System 2.\n\n"
        "**Claim:** exit on the opposite 10- or 20-day extreme -- the same, on a close.",
        "A position open when the backtest ends is closed at its last close and marked OPEN.",
    ),
    "caveats": (
        "**ETFs are not futures.** The claim is about futures; these are their nearest stored stand-ins. "
        "Equity and bond ETFs track their index closely. Commodity ETFs do not: USO, UNG, DBC and DBA "
        "hold rolling futures, and in contango each roll sells cheap and buys dear -- UNG lost most of "
        "its value to roll decay over 2013-2021 while gas prices ended near where they started. That "
        "decay is REAL COST to a long and is inside the price series; a short appears to earn it, which "
        "a real short of UNG partly gives back in a borrow fee that ran far above {BORROW_PCT}% at times. "
        "Read short P&L on USO and UNG with that in mind. An ETF account also has no futures leverage "
        "and no interest on idle collateral: no interest is credited here (T-bills averaged under 1% in "
        "2013-2021, so this costs the book well under a point a year in this window, and much more after).",
        "**Thirteen instruments, not fifty.** The published evidence is on 50-60 futures markets with "
        "low correlation; four of these thirteen are equity indices that move together, two are "
        "Treasuries, and the commodity ETFs overlap. Fewer independent bets means fewer of the big "
        "trends that pay for the losses. The futures series in `index_series` (GOLD_FUT, WTI, NATGAS, "
        "COPPER) are unadjusted front-month closes without highs or lows, with roll gaps a breakout "
        "reads as trends (WTI -37.63 in April 2020), so they are not used; India's NIFTY futures have "
        "no boundary-honouring continuous-contract loader.",
        "**Simplified Turtle rules.** No pyramiding (the originals added up to four units), no System 1 "
        "skip-after-a-winner filter, no correlated-group unit limits, close signals rather than intraday "
        "touches. The claim as written in the TODO is what is tested.",
        "**Dividend yields are flat assumptions** per ETF (ASSETS), because stored prices exclude "
        "distributions; the benchmark uses the stored total-return series.",
        "**PASS CRITERION, written before the first run (2026-10-25).** Judged on the optimise stage, "
        "base cost level, per system (1, 2, both). A system passes to verify only if ALL hold: "
        "(a) standalone CAGR above zero and Sharpe at least 0.3; (b) correlation of monthly returns to "
        "SPY at most 0.3; (c) the 20% trend sleeve beside momentum_baseline has a Sharpe at least the "
        "long book's alone AND a maximum drawdown no deeper than the 20% cash sleeve; (d) CAGR still "
        "above zero at the x2 cost level. The claim's shape (win rate near 45%, most profit from the "
        "top {TOP_SHARE_PCT}% of trades) is reported, not a criterion. If more than one system passes, "
        "only the one with the higher 20% sleeve Sharpe goes to verify, once.",
    ),
}


class TurtleTrendStrategy(PortfolioStrategy):
    """The Turtle channel-breakout pair on a cross-asset ETF book, long and short."""

    key = DOC["key"]
    doc = DOC
    family = "turtle_trend"
    version = "1.0"
    changelog = (("1.0", "2026-10-25",
                  "First version: the TODO's Turtle rules (20/10 and 55/20 channel breakouts, 2N stop, 1% "
                  "risk) on 13 US-listed cross-asset ETFs, long and short, with explicit trading, borrow, "
                  "margin and yield costs at three levels, a 60/40 benchmark, and a month-end sleeve "
                  "blend against momentum_baseline in every run."),)
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"])
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "time_series"
    style = "trend"
    runner = "turtle_trend"

    n_assets = len(ASSETS)

    param_docs = (
        ("System 1 channels", "S1_ENTRY", "Entry channel in sessions; exits on S1_EXIT."),
        ("System 2 channels", "S2_ENTRY", "Entry channel in sessions; exits on S2_EXIT."),
        ("N", "ATR_BARS", "Sessions in the average true range that sizes and stops a trade."),
        ("Stop", "STOP_ATR", "Initial stop distance, in N."),
        ("Risk per trade", "RISK_PCT", "Percent of equity from the fill to the stop."),
        ("Total open risk", "MAX_OPEN_RISK_PCT", "Initial risk of all open positions together, % of equity."),
        ("One position", "MAX_POSITION_PCT", "Largest notional of one position, % of equity."),
        ("Gross exposure", "MAX_GROSS_PCT", "Long plus short notional, % of equity."),
        ("Cost per side", "COST_BPS", "Basis points of notional per fill."),
        ("Borrow fee", "BORROW_PCT", "Percent a year of short notional."),
        ("Margin rate", "MARGIN_RATE_PCT", "Percent a year on cash borrowed for longs."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Turtle trend following on a cross-asset ETF book")
    ap.add_argument("--strategy", default="turtle_trend")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--system", default="2", choices=["1", "2", "both"])
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)
    cfg = MARKETS[a.market]
    frames = load(a.market)
    systems = ["1", "2"] if a.system == "both" else [a.system]

    def one(level):
        rs = {s: run(frames, a.start, s, level, float(cfg.account_size)) for s in systems}
        if len(systems) == 1:
            return rs[systems[0]]
        # two sub-accounts, half each, put back to 50/50 at every month-end
        (t1, e1, h1, g1, c1, k1), (t2, e2, h2, g2, c2, k2) = rs["1"], rs["2"]
        eq = blend(e1, e2, 50) * float(cfg.account_size)
        t = pd.concat([t1, t2], ignore_index=True)
        if len(t):   # an empty concat has no columns (a short window, or every symbol under MIN_HISTORY)
            t[["pnl", "costs", "carry", "shares", "notional"]] *= 0.5   # each system ran on half the account
        return (t, eq, (h1 + h2).reindex(eq.index), ((g1 + g2) / 2).reindex(eq.index), (c1 + c2) / 2,
                {k: k1.get(k, 0) + k2.get(k, 0) for k in k1})

    runs = {lvl: one(lvl) for lvl in COST_LEVELS}
    tdf, eq, held, gross, costs, skipped = runs[1.0]

    bench = sixty_forty().reindex(eq.index).ffill()
    spy = cache.load_cached(a.market, "SPY")["close"].astype(float).reindex(eq.index).ffill()
    prof = trade_profile(tdf)
    sens, sens_md = [], ["| Cost level | CAGR | Max DD | Sharpe | Avg R |", "|---|---|---|---|---|"]
    for lvl, (t, e, *_r) in runs.items():
        st, pr = _stats(e), trade_profile(t)
        sens.append({"level": lvl, "cagr_pct": round(st["cagr"], 2), "max_dd_pct": round(st["max_dd"], 2),
                     "sharpe": round(st["sharpe"], 3), "avg_r": pr.get("avg_r")})
        sens_md.append(f"| ×{lvl:g} | {st['cagr']:+.2f}% | {st['max_dd']:.1f}% | {st['sharpe']:.2f} | "
                       f"{pr.get('avg_r', float('nan')):+.3f} |")

    by_class = (tdf.groupby(["asset_class", "direction"])["pnl"].sum().unstack(fill_value=0).round(0)
                if len(tdf) else pd.DataFrame())
    cls_md = ["| Asset class | Long P&L | Short P&L |", "|---|---|---|"]
    for c, r in by_class.iterrows():
        cls_md.append(f"| {c} | {r.get('long', 0):,.0f} | {r.get('short', 0):,.0f} |")
    by_year = (eq.resample("YE").last().pct_change() * 100).round(1)
    by_year.iloc[0] = round((eq.resample("YE").last().iloc[0] / eq.iloc[0] - 1) * 100, 1)
    st = _stats(eq)
    bst = _stats(bench)
    corr_spy = monthly_corr(eq, spy)
    corr_bench = monthly_corr(eq, bench)
    profile = {**prof, "cagr_pct": round(st["cagr"], 2), "max_dd_pct": round(st["max_dd"], 2),
               "sharpe": round(st["sharpe"], 3), "corr_spy_monthly": round(corr_spy, 3),
               "corr_6040_monthly": round(corr_bench, 3), "bench_cagr_pct": round(bst["cagr"], 2),
               "bench_max_dd_pct": round(bst["max_dd"], 2), "bench_sharpe": round(bst["sharpe"], 3)}
    notes = [
        f"CROSS-ASSET TREND BOOK, system {a.system}: {len(frames)} ETFs, long and short. "
        f"Benchmark: {BENCH_EQUITY_PCT}/40 S&P 500 / 7-10y Treasuries, total return, month-end rebalanced "
        f"(CAGR {bst['cagr']:+.2f}%, max DD {bst['max_dd']:.1f}%, Sharpe {bst['sharpe']:.2f}).",
        f"Trades: {prof.get('trades', 0)}, win rate {prof.get('win_rate_pct')}%, average win "
        f"{prof.get('avg_win_r')}R, average loss {prof.get('avg_loss_r')}R; top {TOP_SHARE_PCT}% of trades "
        f"made {prof.get('top_share_pct')}% of the gross profit. Long P&L {prof.get('long_pnl', 0):,.0f}, "
        f"short P&L {prof.get('short_pnl', 0):,.0f}.",
        f"Correlation of monthly returns: {corr_spy:+.2f} to SPY, {corr_bench:+.2f} to the 60/40.",
        f"Average gross exposure {gross.mean():.0f}% of equity (max {gross.max():.0f}%); "
        f"{(held > 0).mean() * 100:.0f}% of sessions hold a position. Skipped entries: {skipped}.",
        "Cost sensitivity -- " + "; ".join(f"x{s['level']:g}: CAGR {s['cagr_pct']:+.2f}%, DD "
                                          f"{s['max_dd_pct']:.1f}%" for s in sens),
        "By year: " + ", ".join(f"{y.year} {v:+.1f}%" for y, v in by_year.items()),
        "Stored ETF prices exclude distributions: yields are credited to longs and charged to shorts as "
        "flat per-ETF rates. Commodity ETFs' roll decay is inside their prices. No interest on idle cash.",
    ]
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=0,
                           costs_paid=costs, bench_close=bench, cash=None, notes=notes)
    perf.benchmark_name = f"{BENCH_EQUITY_PCT}/40 S&P 500 TR / Treasuries 7-10y TR"

    name = f"{a.start}_system{a.system}_risk{RISK_PCT:g}_{TurtleTrendStrategy.spec_id()}"
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "positions_open": held, "gross_pct": gross,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    pd.DataFrame(sens).to_csv(out / "cost_sensitivity.csv", index=False)
    extra = [("Cost sensitivity", "\n".join(sens_md)), ("P&L by asset class", "\n".join(cls_md))]

    ld = find_long_book(a.market, out)
    if ld is not None:
        leq = pd.read_csv(ld / "equity.csv", index_col=0, parse_dates=True)["equity"]
        profile["corr_long_book_monthly"] = round(monthly_corr(eq, leq), 3)
        profile["long_book"] = ld.name
        tables = []
        for lvl in (1.0, max(COST_LEVELS)):
            t, md = sleeve_table(leq, runs[lvl][1])
            t.insert(0, "cost_level", lvl)
            tables.append(t)
            extra.append((f"As a sleeve beside {LONG_BOOK} (cost x{lvl:g})",
                          f"Long book: `{ld.name}`. Monthly rebalance to the split. Correlation of monthly "
                          f"returns to it: {profile['corr_long_book_monthly']:+.2f}.\n\n{md}"))
        pd.concat(tables).to_csv(out / "sleeve_blend.csv", index=False)
        perf.notes.append(f"Sleeve test against {ld.name} (monthly correlation "
                          f"{profile['corr_long_book_monthly']:+.2f}): see sleeve_blend.csv.")
    else:
        perf.notes.append(f"Sleeve test skipped: no stored {LONG_BOOK} run with this run's stage tag.")
    pd.Series(profile).to_csv(out / "profile.csv", header=["value"])
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, 0))
    for title, body in extra:
        print("\n" + title + "\n" + body)
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"{cfg.name} — cross-asset Turtle trend, system {a.system}, {a.start} onward", perf, eq, held,
            tdf, cfg.currency_symbol, 0, bench,
            f"python3 -m swing_screener.backtesting.turtle_trend --market {a.market} --start {a.start} "
            f"--system {a.system}", extra_sections=extra)
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
