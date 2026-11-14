"""Boucher bond and gold timing — long bonds or gold miners only while their weekly models agree; T-bills otherwise.

From Mark Boucher, *The Hedge Fund Edge* (Wiley, 1999), chapter 8 (PDF pages 155-162). Paraphrased,
with his published settings fixed before the first run (see the 1.0 changelog entry). Three models,
each a `--mode`, all on weekly closes (each week's last session):

    bbu     Bond-Bill-Utility (pp. 155-156, Spreadsheet 8.1): long bonds while the 30-year yield is
            below its 10-week average AND either the T-bill yield is below its 38-week average or the
            Dow Jones Utilities are above their 10-week average
    heine   the Heine model as he summarises it (p. 155): one point each for a corporate bond index
            above its 24-week average, the long Treasury yield below its 6-week average, the 13-week
            T-bill yield below its 6-week average, the Dow Jones Utilities above their 10-week average
            and the CRB index below its 20-week average; long bonds on 3 points or more
    gold    Gold-Silver-GMI (p. 162, Spreadsheet 8.2): long gold miners while the miners are above
            their 16-week average AND gold above its 68-week AND silver above its 12-week

The long bond is TLT's total return where it exists (from 2002-07-30) and, before it, a synthetic
total return of a constant-maturity long Treasury built from the stored yield (`synthetic_long_bond`).
Gold miners are GDX's total return; gold is GLD, silver SLV, the CRB index DBC, the utilities ^DJU.
A model trades only once every input it reads has a reading: a run starting earlier is moved to that
date, and says so.
"""
from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd

from ..marketdata import index_data
from ..strategies.base import PortfolioStrategy
from .boucher_stocks import (FILL_DELAY_SESSIONS, MARKET, TBILL, as_of, bond_index, closes, context_boundary,
                             finish, long_yield, simulate, to_sessions, week_ends)

logger = logging.getLogger("backtest")

MODES = ("bbu", "heine", "gold", "hold_bonds", "hold_gold")

LONG_BOND = "BONDS_LONG"        # TLT total return, from 2002-07-30
GOLD_MINERS = "GOLD_MINERS"     # GDX total return, from 2006-05-22
UTILITIES = "^DJU"              # Dow Jones Utility Average, price, from 1992
GDX, GOLD, SILVER, CRB = "GDX", "GLD", "SLV", "DBC"

# ---- Bond-Bill-Utility (pp. 155-156)
BBU_LONG_WEEKS = 10             # 30-year yield below its 10-week average ...
BBU_BILL_WEEKS = 38             # ... and either the T-bill yield below its 38-week average
BBU_UTIL_WEEKS = 10             #     or the utilities above their 10-week average

# ---- Heine (p. 155)
HEINE_BOND_WEEKS = 24           # corporate bond index above its 24-week average
HEINE_LONG_WEEKS = 6            # long Treasury yield below its 6-week average
HEINE_BILL_WEEKS = 6            # 13-week T-bill yield below its 6-week average
HEINE_UTIL_WEEKS = 10           # utilities above their 10-week average
HEINE_CRB_WEEKS = 20            # CRB index below its 20-week average
HEINE_MIN_POINTS = 3            # long bonds on this many points or more
HEINE_BOND_YEARS = 20           # the corporate bond proxy: a constant-maturity Baa bond, price only

# ---- Gold-Silver-GMI (p. 162)
GMI_WEEKS = 16                  # gold miners above their 16-week average
GOLD_WEEKS = 68                 # gold above its 68-week average
SILVER_WEEKS = 12               # silver above its 12-week average

# ---- the pass rule (1.1): against the asset held at the model's own exposure, the rest in T-bills
MATCH_SHARPE_MARGIN = 0.10      # Sharpe over T-bills must beat the exposure-matched mix's by this much

# ---- the synthetic long bond before TLT
SYN_BOND_YEARS = 25             # TLT holds 20+-year Treasuries, average maturity about 25 years
SYN_EXPENSE = 0.0015            # TLT's expense ratio, a year, charged to the synthetic


# ------------------------------------------------------------------ data

def synthetic_long_bond() -> pd.Series:
    """A daily total return of a constant-maturity SYN_BOND_YEARS Treasury from the stored long yield:
    each session, yesterday's par bond is re-priced at today's yield, plus the coupon accrued over the
    calendar days, less SYN_EXPENSE. Base 100."""
    idx = bond_index(long_yield(), SYN_BOND_YEARS, carry=True)
    days = idx.index.to_series().diff().dt.days.fillna(0)
    return idx * (1 - SYN_EXPENSE) ** (days.cumsum() / 365.0)


def long_bond() -> pd.Series:
    """TLT's total return, chained onto the synthetic before TLT lists."""
    syn, tlt = synthetic_long_bond(), index_data.load(MARKET, LONG_BOND)
    first = tlt.index[0]
    head = syn[syn.index <= first]
    if head.empty:
        return tlt
    return pd.concat([head.iloc[:-1], tlt * (head.iloc[-1] / tlt.iloc[0])]).sort_index()


def tracking() -> dict:
    """The synthetic long bond against TLT's total return, over every session both have."""
    syn, tlt = synthetic_long_bond(), index_data.load(MARKET, LONG_BOND)
    both = pd.concat([syn, tlt], axis=1, keys=["syn", "tlt"]).dropna()
    rs, rr = both["syn"].pct_change().dropna(), both["tlt"].pct_change().dropna()
    years = (both.index[-1] - both.index[0]).days / 365.25

    def cagr(s):
        return ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100

    from . import metrics
    return {"from": both.index[0].date(), "to": both.index[-1].date(), "years": round(years, 1),
            "synthetic_cagr_pct": round(cagr(both["syn"]), 2), "tlt_cagr_pct": round(cagr(both["tlt"]), 2),
            "tracking_error_pct": round(float((rs - rr).std() * np.sqrt(252) * 100), 2),
            "daily_corr": round(float(rs.corr(rr)), 4),
            "synthetic_max_dd_pct": round(float(metrics.drawdown_series(both["syn"]).min() * 100), 1),
            "tlt_max_dd_pct": round(float(metrics.drawdown_series(both["tlt"]).min() * 100), 1)}


def baa_daily() -> pd.Series:
    """Moody's Baa yield, daily: the stored Baa-over-10-year spread plus the 10-year yield (1986 on)."""
    spread, ten = index_data.load(MARKET, "US_CREDIT_SPREAD"), index_data.load(MARKET, "US_UST_10Y")
    return (spread + ten.reindex(spread.index).ffill()).dropna()


def weekly(s: pd.Series, wk: pd.DatetimeIndex) -> pd.Series:
    return as_of(s, wk)


def above(s: pd.Series, weeks: int) -> pd.Series:
    """True where the weekly series is above its `weeks`-week simple average; NaN with no average yet."""
    ma = s.rolling(weeks).mean()
    return (s > ma).where(ma.notna() & s.notna())


def below(s: pd.Series, weeks: int) -> pd.Series:
    ma = s.rolling(weeks).mean()
    return (s < ma).where(ma.notna() & s.notna())


# ------------------------------------------------------------------ the rules

def bbu_state(wk: pd.DatetimeIndex) -> tuple[pd.Series, pd.DataFrame]:
    lng, tb = weekly(long_yield(), wk), weekly(index_data.load(MARKET, TBILL), wk)
    ut = weekly(closes(UTILITIES), wk)
    t = pd.DataFrame({"long_below": below(lng, BBU_LONG_WEEKS), "bill_below": below(tb, BBU_BILL_WEEKS),
                      "util_above": above(ut, BBU_UTIL_WEEKS)})
    ready = t.notna().all(axis=1)
    state = t["long_below"].eq(True) & (t["bill_below"].eq(True) | t["util_above"].eq(True))
    return state.where(ready), t


def heine_state(wk: pd.DatetimeIndex) -> tuple[pd.Series, pd.DataFrame]:
    bond = weekly(bond_index(baa_daily(), HEINE_BOND_YEARS), wk)
    t = pd.DataFrame({
        "bond_above": above(bond, HEINE_BOND_WEEKS),
        "long_below": below(weekly(long_yield(), wk), HEINE_LONG_WEEKS),
        "bill_below": below(weekly(index_data.load(MARKET, TBILL), wk), HEINE_BILL_WEEKS),
        "util_above": above(weekly(closes(UTILITIES), wk), HEINE_UTIL_WEEKS),
        "crb_below": below(weekly(closes(CRB), wk), HEINE_CRB_WEEKS),
    })
    ready = t.notna().all(axis=1)
    points = t.fillna(False).astype(int).sum(axis=1)
    t["points"] = points
    return (points >= HEINE_MIN_POINTS).where(ready), t


def gold_state(wk: pd.DatetimeIndex) -> tuple[pd.Series, pd.DataFrame]:
    t = pd.DataFrame({"gmi_above": above(weekly(closes(GDX), wk), GMI_WEEKS),
                      "gold_above": above(weekly(closes(GOLD), wk), GOLD_WEEKS),
                      "silver_above": above(weekly(closes(SILVER), wk), SILVER_WEEKS)})
    ready = t.notna().all(axis=1)
    return t.eq(True).all(axis=1).where(ready), t


def run(start: str, mode: str = "bbu", cost_bps: float = 5.0):
    """-> (trades, equity, held, cash, costs, bench, bench_name, readings, start actually used)."""
    from ..config import MARKETS
    cfg = MARKETS[MARKET]
    rate = (index_data.load(MARKET, TBILL) / 100.0).clip(lower=0.0)
    gold_side = mode in ("gold", "hold_gold")
    if gold_side:
        price, symbol = index_data.load(MARKET, GOLD_MINERS), GDX
        bench_name = "GDX total return"
    else:
        price, symbol = long_bond(), "TLT"
        bench_name = "Long Treasuries total return (TLT; synthetic before 2002-07-30)"
    readings = pd.DataFrame()
    if mode.startswith("hold"):
        want = pd.Series(1, index=price.index)
        first = price.index[0]
    else:
        wk = week_ends(price.index)
        state, readings = {"bbu": bbu_state, "heine": heine_state, "gold": gold_state}[mode](wk)
        if state.dropna().empty:
            raise SystemExit(f"{mode}: no week has every input before the window's end")
        first = state.dropna().index[0]
        want = to_sessions(state.fillna(False), price.index).astype(int)
    used = max(pd.Timestamp(start), first)
    # the log's prices are the fund's own close; the total-return levels it earns are logged beside them
    tdf, eq, held, csh, costs, _pos = simulate(price, want, rate, used.date().isoformat(), cost_bps,
                                               float(cfg.account_size), symbol, quote=closes(symbol))
    return tdf, eq, held, csh, costs, price, bench_name, readings, used


def matched(eq: pd.Series, held: pd.Series, price: pd.Series, cost_bps: float) -> dict:
    """The pass rule's yardstick (1.1): the model's asset held at the model's own average exposure over
    the run, the rest in T-bills, rebalanced at each month's last session -- and the model's own figures
    beside it, all on the same sessions. A comparison built with the run's exposure, never a trade."""
    from .boucher_book import book_stats, mix
    rate = (index_data.load(MARKET, TBILL) / 100.0).clip(lower=0.0)
    x = float(held.reindex(eq.index).fillna(0).mean())
    start = eq.index[0].date().isoformat()
    one = pd.Series(1, index=price.index)
    asset = simulate(price, one, rate, start, cost_bps, 1.0, "asset")[1]
    bills = simulate(price, one * 0, rate, start, cost_bps, 1.0, "bills")[1]
    mixed, _v, _c = mix({"asset": asset, "bills": bills}, {"asset": x, "bills": 1 - x}, cost_bps)
    return {"exposure": x, "model": book_stats(eq, rate), "matched": book_stats(mixed, rate),
            "asset": book_stats(asset, rate)}


def pass_verdict(m: dict) -> tuple[bool, str]:
    """The 1.1 pass rule, fixed 2026-11-14: Sharpe over T-bills at least MATCH_SHARPE_MARGIN above the
    exposure-matched mix's, and a max drawdown no deeper than the mix's."""
    a, b = m["model"], m["matched"]
    ok = a["sharpe"] >= b["sharpe"] + MATCH_SHARPE_MARGIN and a["max_dd_pct"] >= b["max_dd_pct"]
    return ok, (f"Pass rule (1.1): model Sharpe over T-bills {a['sharpe']:.2f} vs {b['sharpe']:.2f} for "
                f"{m['exposure'] * 100:.0f}% asset / {100 - m['exposure'] * 100:.0f}% T-bills (needs +"
                f"{MATCH_SHARPE_MARGIN:.2f}); max DD {a['max_dd_pct']:.1f}% vs {b['max_dd_pct']:.1f}%; CAGR "
                f"{a['cagr_pct']:.2f}% vs {b['cagr_pct']:.2f}% (asset held {m['asset']['cagr_pct']:.2f}%, "
                f"Sharpe {m['asset']['sharpe']:.2f}) -> {'PASS' if ok else 'FAIL'}.")


# ------------------------------------------------------------------ docs

BG_DOC = {
    "key": "boucher_bonds_gold",
    "name": "Boucher bond and gold timing",
    "description": "Hold long Treasuries while the 30-year yield is below its {BBU_LONG_WEEKS}-week average and "
                   "the T-bill yield or the utilities agree (Bond-Bill-Utility), or on Heine's five-point "
                   "count; hold gold miners while miners, gold and silver are all above their averages. "
                   "T-bills otherwise. Mark Boucher's weekly models.",
    "status": (
        "OPTIMISE STAGE (2013-2021, in-sample) -- NO MODEL PASSES; THE GOLD MODEL FAILS. The pass rule, "
        "re-stated in 1.1 (2026-11-14 review, tracker #76), because the 1.0 rule (excess over the asset held) "
        "could not tell timing from simply holding less of a falling asset: a model passes only if its Sharpe "
        "over T-bills is at least {MATCH_SHARPE_MARGIN} above that of its own asset held at the model's own "
        "average exposure with the rest in T-bills (rebalanced monthly), with a max drawdown no deeper than "
        "that mix's. The asset held and T-bills are reported beside it. Judged on the 1.0 runs (1.1 changes "
        "the trade log only, not the equity): Gold-Silver-GMI FAILS -- -0.81% CAGR, drawdown -40.5%, Sharpe "
        "0.02, against 26% GDX / 74% T-bills at +0.86%, -25.3%, 0.07; GDX returned -3.72% a year in the weeks "
        "it held it and -3.35% in the weeks it did not, so its 1.0 'pass' over GDX (-3.45%) was the 74% of "
        "the time in T-bills. Bond-Bill-Utility FAILS -- 3.88%, -15.7%, Sharpe 0.36, against 50% TLT / 50% "
        "T-bills at 2.91%, -11.1%, 0.36 (TLT held 4.88%, -21.3%, 0.37): the same Sharpe at a deeper drawdown, "
        "so no timing edge. Heine (3.69%, -19.4%, 54 trades) trails Bond-Bill-Utility on every measure; its "
        "exposure-matched mix is printed by its run. Each run now prints its own verdict under this rule. "
        "Context, full stage 1980-2012 (never a verdict): bbu 4.68% against 8.82% for long bonds held, heine "
        "1.65%, gold -7.87%. The models' intended use, as sleeves of one book with Boucher's stock timing, is "
        "tested as boucher_book. No verify run."
    ),
    "thesis": (
        "The same liquidity cycle as his stock timing, applied to the assets it moves first. Bonds rally "
        "when long yields fall, and the move is safer when short rates or rate-sensitive utility stocks "
        "confirm it; rising commodity prices warn of inflation. Gold shares are the most volatile way to own "
        "gold, so own them only when the miners, the metal and silver are all trending up together, and sit "
        "in T-bills through the long bear markets in between."
    ),
    "how_it_works": (
        "Every week's last close. `--mode bbu` (default, pp. 155-156): hold long Treasuries while the 30-year "
        "yield is below its {BBU_LONG_WEEKS}-week simple average AND either the 13-week T-bill yield is below "
        "its {BBU_BILL_WEEKS}-week average or the Dow Jones Utility Average is above its {BBU_UTIL_WEEKS}-week "
        "average.",
        "`--mode heine` (p. 155, as Boucher summarises Heine and Freeburg's model): one point each for a "
        "corporate bond index above its {HEINE_BOND_WEEKS}-week average, the 30-year yield below its "
        "{HEINE_LONG_WEEKS}-week, the T-bill yield below its {HEINE_BILL_WEEKS}-week, the utilities above "
        "their {HEINE_UTIL_WEEKS}-week and the CRB index below its {HEINE_CRB_WEEKS}-week; hold long "
        "Treasuries on {HEINE_MIN_POINTS} points or more.",
        "`--mode gold` (p. 162): hold gold miners (GDX) while GDX is above its {GMI_WEEKS}-week average, gold "
        "(GLD) above its {GOLD_WEEKS}-week and silver (SLV) above its {SILVER_WEEKS}-week.",
        "Out of the asset the money earns the 13-week T-bill rate. `--mode hold_bonds` and `--mode hold_gold` "
        "hold the asset throughout, for comparison; every run's benchmark is its asset's buy-and-hold.",
        "The verdict (1.1): each model run also builds its asset held at the model's own average exposure, "
        "the rest in T-bills, rebalanced at each month's last session, and prints the pass rule against it: "
        "Sharpe over T-bills at least {MATCH_SHARPE_MARGIN} higher, and a drawdown no deeper.",
    ),
    "caveats": (
        "**His figures are not comparable as printed.** He reported price-plus-coupon index returns (bonds) "
        "or price returns (gold shares), some as average rather than compound annual returns, with no costs, "
        "fitted on 1943-1997 (Bond-Bill-Utility), 1957-1995 (Heine) and 1975-1997 (gold). Here returns "
        "compound over the window, use fund total returns and pay {cost_bps}bps a side.",
        "**The long bond before 2002 is synthetic.** TLT lists on 2002-07-30. Before it, a constant-"
        "maturity {SYN_BOND_YEARS}-year Treasury is re-priced daily at the stored 30-year yield (the 10-year "
        "before 1977) plus its coupon, less TLT's {SYN_EXPENSE} expense ratio. `tracking()` compares it with "
        "TLT where both exist: from 2002-07-30 to 2026-11-10 the synthetic returns 3.47% a year against "
        "TLT's 3.48%, with a 4.5% annual tracking error, a 0.949 daily correlation and the same worst "
        "drawdown (-48.1% against -48.4%). His own bond index was the Dow Jones 20 corporate bond index plus the 30-year "
        "coupon, not Treasuries.",
        "**Proxies for discontinued or unavailable indexes.** The Dow Jones 20 Bond index (Heine's first "
        "point) is a price index of a {HEINE_BOND_YEARS}-year bond re-priced daily at Moody's Baa yield "
        "(stored Baa spread plus the 10-year, from 1986). The CRB index is DBC (an ETF on a commodity index, "
        "from 2006), so Heine has no reading before mid-2006. His gold-mining index (GMI) is GDX, gold "
        "bullion is GLD and silver is SLV, so the gold model starts in late 2007.",
        "**Short histories.** The utilities start in 1992, DBC in 2006, GDX and SLV in 2006: a run that "
        "starts before every input of its model has an average is moved to the first week that has one, and "
        "the run's notes say so. The 1980-2012 context runs therefore cover 1992-2012 (bbu) and 2006-2012 "
        "(heine, gold).",
        "**Fills.** Signals on each week's last close fill at the close {FILL_DELAY_SESSIONS} session later.",
        "**The trade log.** The book earns the total-return series (TLT's chained onto the synthetic, base "
        "100; GDX's dividend-adjusted), so `entry_price` / `exit_price` are the fund's own close (blank "
        "before it lists) and the series levels are logged as `entry_tr_level` / `exit_tr_level`. `costs` "
        "is both fees (1.0 logged only the exit fee); `r_multiple` is the trade's fractional return.",
        "**The exposure-matched yardstick uses the run's own exposure,** known only after the run. It is a "
        "comparison that asks whether the timing chose better weeks than chance, never a tradable book.",
    ),
    "entry_rules": (
        "At each week's last close, every condition of the chosen model holds (bbu, gold) or enough of them "
        "do (heine: {HEINE_MIN_POINTS} of 5), and every input it reads has its average.",
        "Fill: the whole book buys the asset's total-return series at the close {FILL_DELAY_SESSIONS} "
        "session later, less {cost_bps}bps.",
    ),
    "exit_rules": (
        "Sold in full at the close {FILL_DELAY_SESSIONS} session after a week's last close at which the "
        "model is no longer bullish, less {cost_bps}bps. No stop and no target.",
        "Out of the asset the money earns the 13-week T-bill rate per calendar day. A holding at the end of "
        "a run is valued at the final close (OPEN).",
    ),
    "commands": {
        "Bond-Bill-Utility (optimise)": "python -m jobs enqueue backtest --market us --strategies boucher_bonds_gold --stage optimise",
        "Heine bond model": "python -m jobs enqueue backtest --market us --strategies boucher_bonds_gold --stage optimise --bt='--mode heine'",
        "Gold-Silver-GMI": "python -m jobs enqueue backtest --market us --strategies boucher_bonds_gold --stage optimise --bt='--mode gold'",
        "Compare: long Treasuries held": "python -m jobs enqueue backtest --market us --strategies boucher_bonds_gold --stage optimise --bt='--mode hold_bonds'",
        "Compare: GDX held": "python -m jobs enqueue backtest --market us --strategies boucher_bonds_gold --stage optimise --bt='--mode hold_gold'",
        "Context: to 2012 (not a verdict)": "python -m jobs enqueue backtest --market us --strategies boucher_bonds_gold --stage full --start 1980-01-01 --bt='--end 2012-12-31'",
    },
}


class BoucherBondsGoldStrategy(PortfolioStrategy):
    """Boucher's weekly bond (Bond-Bill-Utility, Heine) and gold-miner (Gold-Silver-GMI) timing."""

    key = BG_DOC["key"]
    doc = BG_DOC
    family = "boucher_bonds_gold"
    version = "1.1"
    changelog = (
        ("1.1", "2026-11-14",
         "Review 2026-11-14 (tracker #76). (1) The shared trade log (boucher_stocks.simulate): `costs` holds "
         "the entry plus the exit fee (it held only the exit fee); `entry_price` / `exit_price` are TLT's or "
         "GDX's own close, the total-return levels moved to `entry_tr_level` / `exit_tr_level`. Equity "
         "unchanged. (2) The pass rule re-stated: Sharpe over T-bills at least MATCH_SHARPE_MARGIN = 0.10 "
         "above the asset held at the model's own average exposure (rest in T-bills, monthly), and a max "
         "drawdown no deeper; each model run prints that verdict. The 1.0 rule (excess over the asset held) "
         "read 74% of the time in T-bills while GDX fell as a pass. Gold-Silver-GMI marked failing. No rule "
         "of any model changes; bumped by hand because simulate is shared and the fingerprint cannot see it."),
        ("1.0", "2026-11-13",
         "First version, from Mark Boucher's The Hedge Fund Edge (1999), chapter 8. Settings his published "
         "ones, FIXED BEFORE THE FIRST RUN, weekly closes: Bond-Bill-Utility -- 30-year yield < 10-week SMA "
         "and (T-bill yield < 38-week SMA or ^DJU > 10-week SMA); Heine -- a point each for a Baa bond-price "
         "proxy > 24-week SMA, 30-year yield < 6-week, T-bill yield < 6-week, ^DJU > 10-week, DBC < 20-week, "
         "long on >= 3; Gold-Silver-GMI -- GDX > 16-week, GLD > 68-week, SLV > 12-week. Long bond: TLT total "
         "return, a synthetic 25-year constant-maturity Treasury (less 0.15%/yr) before 2002-07-30. Fills "
         "at the next close, 5bps a side, T-bills otherwise. Pass rule written before any result: excess "
         "CAGR > 0 vs the asset's buy-and-hold with a max drawdown no deeper, or a materially shallower "
         "drawdown at a CAGR within 1 point."),
    )
    name = BG_DOC["name"]
    description = BG_DOC["description"]
    status = BG_DOC["status"]
    thesis = BG_DOC["thesis"]
    how_it_works = tuple(BG_DOC["how_it_works"])
    caveats = tuple(BG_DOC["caveats"])
    entry_rules = tuple(BG_DOC["entry_rules"])
    exit_rules = tuple(BG_DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "time_series"
    style = "trend"
    horizon = "positional"
    runner = "boucher_bonds_gold"

    mode = "bbu"
    cost_bps = 5.0

    param_docs = (
        ("Mode", "mode", "bbu / heine: long Treasuries. gold: gold miners. hold_bonds / hold_gold: buy-and-hold."),
        ("BBU long yield", "BBU_LONG_WEEKS", "Weeks in the 30-year yield's average."),
        ("BBU T-bill", "BBU_BILL_WEEKS", "Weeks in the T-bill yield's average."),
        ("BBU utilities", "BBU_UTIL_WEEKS", "Weeks in the Dow Jones Utilities' average."),
        ("Heine bond index", "HEINE_BOND_WEEKS", "Weeks in the corporate bond proxy's average."),
        ("Heine long / T-bill", "HEINE_LONG_WEEKS", "Weeks in the 30-year yield's average; the T-bill's {HEINE_BILL_WEEKS}."),
        ("Heine utilities / CRB", "HEINE_UTIL_WEEKS", "Weeks in the utilities' average; the CRB's {HEINE_CRB_WEEKS}."),
        ("Heine points", "HEINE_MIN_POINTS", "Points of five needed to hold bonds."),
        ("Gold miners", "GMI_WEEKS", "Weeks in GDX's average."),
        ("Gold", "GOLD_WEEKS", "Weeks in GLD's average."),
        ("Silver", "SILVER_WEEKS", "Weeks in SLV's average."),
        ("Pass margin", "MATCH_SHARPE_MARGIN", "Sharpe over T-bills a model must add over its asset held at its own exposure, the rest in T-bills."),
        ("Synthetic bond", "SYN_BOND_YEARS", "Maturity of the constant-maturity Treasury that stands in before TLT."),
        ("Cost per side", "cost_bps", "Basis points per side."),
    )


# ------------------------------------------------------------------ runner

def main(argv: list[str] | None = None) -> dict | None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Boucher bond and gold timing")
    ap.add_argument("--strategy", default=BoucherBondsGoldStrategy.key)
    ap.add_argument("--market", default=MARKET, choices=[MARKET])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", default=None, help="an earlier end than the stage's, for a context run")
    ap.add_argument("--mode", default=BoucherBondsGoldStrategy.mode, choices=list(MODES))
    ap.add_argument("--cost-bps", type=float, default=BoucherBondsGoldStrategy.cost_bps)
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    with context_boundary(a.end):
        tdf, eq, held, csh, costs, bench, bench_name, _r, used = run(a.start, a.mode, a.cost_bps)
        verdict = ""
        if not a.mode.startswith("hold"):
            verdict = " " + pass_verdict(matched(eq, held, bench, a.cost_bps))[1]
            print(verdict.strip())
        what = {"bbu": "Bond-Bill-Utility model, long Treasuries.", "heine": "Heine model, long Treasuries.",
                "gold": "Gold-Silver-GMI model, gold miners (GDX).",
                "hold_bonds": "Comparison: long Treasuries held throughout.",
                "hold_gold": "Comparison: GDX held throughout."}[a.mode] + verdict
        note = ("" if used <= pd.Timestamp(a.start) else
                f"Start moved from {a.start} to {used.date()}: the first week every input of the model has a reading.")
        return finish(a, argv, BoucherBondsGoldStrategy, tdf, eq, held, csh, costs, bench, bench_name, what, a.mode,
                      f"Boucher bond and gold timing ({a.mode}), {a.start} onward", "boucher_bonds_gold",
                      start_note=note)


if __name__ == "__main__":
    main()
