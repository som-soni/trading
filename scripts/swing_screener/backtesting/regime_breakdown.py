"""Every strategy's stored backtest, split by market regime: how did it do in bull, transition and bear markets?

    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.regime_breakdown [--market us] [--out FILE]

Reads stored run directories only (equity.csv) and the market's stored benchmark; runs no strategy.

Two lenses on the same curves.

**1. Dated phases (the main lens; hindsight, for attribution only).** The benchmark's own declines of at least
DECLINE_MIN_PCT % from a closing high, dated after the fact:

    decline     from the closing high to the lowest close before the next new high
    recovery    from that low until the index closes at a new high (an episode still open runs to today)
    advance     every other session

Each decline is also shown on its own (compounded, strategy vs index), so 2020's crash and 2022's bear
market read separately. Hindsight is fine here -- it only says WHEN the market fell, never what to trade.

**2. The 200-day signal (fixed before any figure; what a trader saw that morning).** Each session is labelled
by the benchmark's state at the PREVIOUS close:

    bull        close above its 200-day average, and that average higher than 20 sessions earlier
    bear        close below its 200-day average, and that average lower than 20 sessions earlier
    transition  the two mixed states -- above a falling average (topping) or below a rising one (correction)

Read it as "what this strategy earned while the signal said X", not as "in bear markets": the average lags,
so a crash that starts from a high falls mostly in *transition* and the rebound off the low in *bear* --
in the US since 2013 the index rose fast on *bear* sessions. Lens 1 is the answer to "what works in a
decline"; lens 2 to "what to run when the dashboard says bear".

Which run: the strategy's full-period run (2013 -> today, current rules) when one is stored; otherwise its
best configuration's in-sample run joined to the same configuration's out-of-sample run; otherwise the one
run it has. The source is named in every row, because a stitched or partial curve covers fewer regimes.

Per regime: the strategy's and the benchmark's annualised return over the same sessions (mean daily return
x 252 -- arithmetic, so the regimes add up to the whole, not compounded), the difference, and the share of
those sessions the strategy held at least one position. A strategy in cash through a bear market shows a
return near zero there, which beats a falling index: that is the point of the split.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..marketdata import cache

DECLINE_MIN_PCT = 10.0
EPISODE_MIN_PCT = 15.0     # declines this deep get their own column
SMA_DAYS = 200
SLOPE_BARS = 20
REGIMES = ("bull", "transition", "bear")
PHASES = ("advance", "decline", "recovery")
REPO = Path(__file__).resolve().parents[3]


def regimes(close: pd.Series) -> pd.Series:
    """Label per session from the previous close's state (see the module doc)."""
    c = close.astype(float)
    sma = c.rolling(SMA_DAYS, min_periods=SMA_DAYS).mean()
    above, rising = c > sma, sma > sma.shift(SLOPE_BARS)
    lab = pd.Series("transition", index=c.index, dtype=object)
    lab[above & rising] = "bull"
    lab[~above & ~rising] = "bear"
    lab[sma.isna() | sma.shift(SLOPE_BARS).isna()] = None
    return lab.shift(1)


def episodes(close: pd.Series) -> list[dict]:
    """The benchmark's declines of DECLINE_MIN_PCT % or more: {peak, trough, depth, recovered (or None)}."""
    c = close.astype(float).dropna()
    peak = c.cummax()
    dd = c / peak - 1
    out = []
    for _, s in dd.groupby((c >= peak).cumsum()):
        if s.min() <= -DECLINE_MIN_PCT / 100:
            last = s.index[-1]
            rec = c.index[c.index.get_loc(last) + 1] if last != c.index[-1] else None
            out.append({"peak": s.index[0], "trough": s.idxmin(), "depth": 100 * s.min(), "recovered": rec})
    return out


def phases(close: pd.Series, eps: list[dict]) -> pd.Series:
    """Phase label per session (the return INTO that session's close)."""
    lab = pd.Series("advance", index=close.index, dtype=object)
    for e in eps:
        lab[(lab.index > e["peak"]) & (lab.index <= e["trough"])] = "decline"
        end = e["recovered"] or lab.index[-1]
        lab[(lab.index > e["trough"]) & (lab.index <= end)] = "recovery"
    return lab


def _source_paths(run_ids: list[int]) -> dict[int, str]:
    from ..marketdata import db
    if not run_ids:
        return {}
    cur = db.get_connection().cursor()
    cur.execute("SELECT id, source_path FROM report_runs WHERE id = ANY(%s)", (run_ids,))
    return dict(cur.fetchall())


def _curve(path: str) -> pd.DataFrame | None:
    p = REPO / path
    f = (p if p.is_dir() else p.parent) / "equity.csv"
    if not f.exists():
        return None
    df = pd.read_csv(f, index_col=0, parse_dates=True)
    return df if "equity" in df and len(df) > 2 else None


def _returns(frames: list[pd.DataFrame]) -> tuple[pd.Series, pd.Series]:
    """Daily returns and 'holds a position' flags, curves joined end to start (later curve wins overlaps)."""
    rets, held = [], []
    for df in frames:
        eq = df["equity"].astype(float)
        rets.append(eq.pct_change().dropna())
        pos = df["positions_open"] if "positions_open" in df else pd.Series(1, index=df.index)
        held.append((pos.fillna(0) > 0).reindex(rets[-1].index))
    r, h = pd.concat(rets), pd.concat(held)
    keep = ~r.index.duplicated(keep="last")
    return r[keep].sort_index(), h[keep].sort_index()


def pick_runs(entry: dict) -> tuple[list[int], str]:
    """(run ids in time order, source label) for one strategy x market edge entry."""
    full = (entry.get("full") or {}).get("run_id")
    if full:
        return [full], "full run"
    best = entry.get("best") or {}
    ins, oos = best.get("in_sample_run"), (best.get("run_id") if best.get("stage") == "verify" else None)
    if ins and oos:
        return [ins, oos], "best config, in-sample + out-of-sample"
    one = best.get("run_id") or entry.get("run_id")
    return ([one], f"{best.get('stage') or entry.get('stage') or 'one'} run only") if one else ([], "")


def _by_label(r: pd.Series, held: pd.Series, bret: pd.Series, lab: pd.Series, groups) -> dict:
    row = {}
    for g in groups:
        days = r.index[lab.reindex(r.index) == g]
        row[f"{g}_days"] = len(days)
        if len(days) < 20:
            row[f"{g}_ret"] = row[f"{g}_bench"] = row[f"{g}_excess"] = row[f"{g}_held"] = np.nan
            continue
        row[f"{g}_ret"] = 100 * 252 * r.loc[days].mean()
        row[f"{g}_bench"] = 100 * 252 * bret.reindex(days).mean()
        row[f"{g}_excess"] = row[f"{g}_ret"] - row[f"{g}_bench"]
        row[f"{g}_held"] = 100 * held.reindex(days).fillna(False).mean()
    return row


def _episode_return(r: pd.Series, e: dict) -> float:
    """Compounded strategy return from the peak's close to the trough's close; NaN unless the curve covers it."""
    if r.index.min() > e["peak"] or r.index.max() < e["trough"]:
        return np.nan
    seg = r[(r.index > e["peak"]) & (r.index <= e["trough"])]
    return 100 * ((1 + seg).prod() - 1)


def breakdown(market: str, edges: dict) -> dict:
    cfg = MARKETS[market]
    bclose = cache.load_cached(market, cfg.benchmark_ticker)["close"].astype(float)
    bret = bclose.pct_change()
    eps = episodes(bclose.loc["2012-01-01":])
    plab, slab = phases(bclose, eps), regimes(bclose)
    picks = {k: pick_runs(v[market]) for k, v in edges.items() if (v or {}).get(market)}
    paths = _source_paths(sorted({i for ids, _ in picks.values() for i in ids}))
    rows = []
    for key, (ids, source) in sorted(picks.items()):
        frames = [c for c in (_curve(paths[i]) for i in ids if i in paths) if c is not None]
        if not frames:
            continue
        r, held = _returns(frames)
        r = r[r.index.isin(bclose.index)]
        row = {"strategy": key, "source": source, "from": r.index.min().date(), "to": r.index.max().date()}
        row.update(_by_label(r, held, bret, plab, PHASES))
        row.update(_by_label(r, held, bret, slab, REGIMES))
        for i, e in enumerate(eps):
            row[f"ep{i}"] = _episode_return(r, e)
        # downside capture over every decline the curve covers: strategy's summed decline returns / index's
        cov = [i for i, e in enumerate(eps) if pd.notna(row[f"ep{i}"])]
        row["capture"] = (100 * sum(row[f"ep{i}"] for i in cov) / sum(eps[i]["depth"] for i in cov)) if cov else np.nan
        row["declines_covered"] = len(cov)
        rows.append(row)
    return {"rows": pd.DataFrame(rows), "episodes": eps, "signal": slab, "phase": plab}


def _fmt(x, sign=True):
    return "—" if pd.isna(x) else (f"{x:+.1f}" if sign else f"{x:.0f}")


def _cell(x, g, held=True):
    return (f"{_fmt(x[g + '_ret'])} / {_fmt(x[g + '_bench'])} / **{_fmt(x[g + '_excess'])}**"
            + (f" ({_fmt(x[g + '_held'], False)}%)" if held and pd.notna(x[g + '_held']) else ""))


def to_markdown(market: str, res: dict) -> str:
    cfg = MARKETS[market]
    df, eps, slab, plab = res["rows"], res["episodes"], res["signal"], res["phase"]
    big = [(i, e) for i, e in enumerate(eps) if e["depth"] <= -EPISODE_MIN_PCT]
    ep_head = " | ".join(f"{e['peak']:%b %Y}→{e['trough']:%b %Y} ({e['depth']:.0f}%)" for _, e in big)
    L = [f"### {market.upper()} — benchmark {cfg.benchmark_symbol}", ""]
    L.append(f"Declines of {DECLINE_MIN_PCT:.0f}% or more since 2012: " + "; ".join(
        f"{e['peak']:%Y-%m-%d} → {e['trough']:%Y-%m-%d} ({e['depth']:.1f}%, "
        + (f"recovered {e['recovered']:%Y-%m-%d})" if e["recovered"] else "not yet recovered)") for e in eps) + ".")
    now_p, now_s = plab.dropna().iloc[-1], slab.dropna().iloc[-1]
    L += ["", f"At the last stored close the index is in **{now_p}** (dated phases) and the 200-day signal reads "
          f"**{now_s}**.", ""]
    L += ["**Each deep decline, peak to trough (compounded %, strategy; index in the header).** "
          "*Capture* = the strategy's losses over every decline it covers as a share of the index's (lower is "
          "better; negative = it made money while the index fell). Sorted by capture.", "",
          f"| Strategy | Capture | {ep_head} | Source |",
          "|---|---|" + "---|" * len(big) + "---|"]
    for _, x in df.sort_values("capture", na_position="last").iterrows():
        eps_cells = " | ".join(_fmt(x[f"ep{i}"]) for i, _ in big)
        L.append(f"| `{x['strategy']}` | {_fmt(x['capture'], False)}% ({int(x['declines_covered'])}) | {eps_cells} "
                 f"| {x['source']}, {x['from']} → {x['to']} |")
    L += ["", "**By dated phase** — annualised % a year (arithmetic), strategy / index / **difference**; "
          "(held) = share of those sessions with a position open.", "",
          "| Strategy | Advance | Decline | Recovery |", "|---|---|---|---|"]
    for _, x in df.sort_values("decline_excess", ascending=False, na_position="last").iterrows():
        L.append(f"| `{x['strategy']}` | {_cell(x, 'advance', False)} | {_cell(x, 'decline')} | {_cell(x, 'recovery')} |")
    share = slab.loc["2013-01-01":].value_counts(normalize=True) * 100
    L += ["", f"**By the 200-day signal** (sessions since 2013: bull {share.get('bull', 0):.0f}%, transition "
          f"{share.get('transition', 0):.0f}%, bear {share.get('bear', 0):.0f}%) — what each strategy earned "
          "while the signal said so. The average lags: crashes land mostly in *transition*, rebounds in *bear*.", "",
          "| Strategy | Bull | Transition | Bear |", "|---|---|---|---|"]
    for _, x in df.sort_values("bear_excess", ascending=False, na_position="last").iterrows():
        L.append(f"| `{x['strategy']}` | {_cell(x, 'bull', False)} | {_cell(x, 'transition')} | {_cell(x, 'bear')} |")
    return "\n".join(L)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", action="append", choices=list(MARKETS))
    ap.add_argument("--csv", help="also write the rows to this CSV")
    a = ap.parse_args(argv)
    from ..web.server import strategy_edges
    edges = strategy_edges()
    out, frames = [], []
    for m in a.market or list(MARKETS):
        res = breakdown(m, edges)
        out.append(to_markdown(m, res))
        frames.append(res["rows"].assign(market=m))
    if a.csv:   # episode columns differ by market, so the rows are joined before writing
        pd.concat(frames, ignore_index=True).to_csv(a.csv, index=False)
    print(f"_Computed {dt.date.today()} from stored runs._\n\n" + "\n\n".join(out))


if __name__ == "__main__":
    main()
