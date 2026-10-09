"""Research: does group strength improve a screen's forward returns?

Asks whether "leaders in leading groups" is worth requiring: on every month-end of the last five years
(the month-end snapshots, with group RS rebuilt point in time — analytics/group_history.py), stocks are
split by the RS of their peer group (sub-industry, else industry group) and by their place in it, and
the forward returns to the following month-ends compared (screens/study.py does the measuring).

Comparisons are paired by date: for two sets A and B, the difference of their average 1-month return on
each month-end where both have at least MIN_EACH stocks; its mean, its t-statistic (1-month windows do
not overlap, so the t is fair; 3- and 6-month windows overlap and their t would overstate, so they are
shown without one) and the share of months A beat B.

Writes research/group-strength-study.md (loaded into the web app's Reports archive).

    PYTHONPATH=. python3 -m swing_screener.screens.group_research            # both markets, writes the report
"""

import argparse
import datetime as dt
import logging
import math

from .. import paths
from ..config import MARKETS
from . import definitions, study
from . import criteria as c

logger = logging.getLogger(__name__)
STRONG, WEAK = 80, 50          # peer-group RS: strong ≥ 80, weak < 50
TOP = 3                        # "leader": top 3 of its peer group by RS rank
MIN_EACH = 3                   # a month-end counts in a paired comparison when both sets have this many stocks
REPORT = paths.RESEARCH_DIR / "group-strength-study.md"

T = {"field": "tradable", "op": "is", "value": True}
STRONG_C = {"field": "peer_rs", "op": ">=", "value": STRONG}
MID_C = [{"field": "peer_rs", "op": ">=", "value": WEAK}, {"field": "peer_rs", "op": "<", "value": STRONG}]
WEAK_C = {"field": "peer_rs", "op": "<", "value": WEAK}
MIN_PEERS = 3                  # "top 3" needs a peer group of at least this many tradable stocks
LEADER_C = [{"field": "peer_rank", "op": "<=", "value": TOP}, {"field": "peer_count", "op": ">=", "value": MIN_PEERS}]
NOT_LEADER_C = [{"field": "peer_rank", "op": ">", "value": TOP}]
SUB_PEER = {"field": "peer_group", "op": "!=", "ref": "industry"}   # peer group is a sub-industry


def sets() -> dict[str, list]:
    stage2 = definitions.builtin()["stage2"]["conditions"]
    uptrend = definitions.builtin()["uptrend"]["conditions"]
    return {
        "All tradable": [T],
        "Tradable · strong group": [T, STRONG_C], "Tradable · middling group": [T, *MID_C], "Tradable · weak group": [T, WEAK_C],
        "Stage 2": stage2,
        "Stage 2 · strong group": [*stage2, STRONG_C], "Stage 2 · weak group": [*stage2, WEAK_C],
        "Stage 2 · top 3 in group": [*stage2, *LEADER_C], "Stage 2 · not top 3": [*stage2, *NOT_LEADER_C],
        "Strong stocks in leading groups": definitions.presets()["leaders"]["conditions"],
        "Uptrend": uptrend, "Uptrend · strong group": [*uptrend, STRONG_C], "Uptrend · weak group": [*uptrend, WEAK_C],
        "Tradable · strong industry group": [T, {"field": "group_rs", "op": ">=", "value": STRONG}],
        "Sub-industry peers · strong sub-industry": [T, SUB_PEER, STRONG_C],
        "Sub-industry peers · strong industry group": [T, SUB_PEER, {"field": "group_rs", "op": ">=", "value": STRONG}],
    }


PAIRS = [
    ("Tradable · strong group", "Tradable · weak group", "Group strength alone"),
    ("Stage 2 · strong group", "Stage 2 · weak group", "Within Stage 2: strong vs weak group"),
    ("Stage 2 · strong group", "Stage 2", "Within Stage 2: requiring a strong group"),
    ("Stage 2 · top 3 in group", "Stage 2 · not top 3", "Within Stage 2: leader of its group or not"),
    ("Strong stocks in leading groups", "Stage 2", "The preset vs Stage 2"),
    ("Uptrend · strong group", "Uptrend · weak group", "Within the established uptrend: strong vs weak group"),
    ("Sub-industry peers · strong sub-industry", "Sub-industry peers · strong industry group", "Sub-industry vs industry group (same stocks)"),
]


def run(market: str) -> dict:
    """Every set's study, and the paired comparisons, for one market."""
    res = {name: study.study(market, conds) for name, conds in sets().items()}
    by_date = {name: {x["date"]: x for x in r.get("series", [])} for name, r in res.items()}
    pairs = []
    for a, b, title in PAIRS:
        row = {"a": a, "b": b, "title": title}
        for h in study.HORIZONS:
            diffs, wins = [], 0
            for d, xa in by_date[a].items():
                xb = by_date[b].get(d)
                if not xb or h not in xa or h not in xb or xa[h]["q"] is None or xb[h]["q"] is None:
                    continue
                if xa["qualifiers"] < MIN_EACH or xb["qualifiers"] < MIN_EACH:
                    continue
                diffs.append(xa[h]["q"] - xb[h]["q"])
                wins += xa[h]["q"] > xb[h]["q"]
            n = len(diffs)
            if n < 6:
                row[h] = None
                continue
            mean = sum(diffs) / n
            sd = math.sqrt(sum((x - mean) ** 2 for x in diffs) / (n - 1)) if n > 1 else 0
            row[h] = {"n": n, "mean": mean, "t": mean / (sd / math.sqrt(n)) if sd else None, "won": wins / n}
        pairs.append(row)
    return {"market": market, "sets": res, "pairs": pairs, "month_ends": len(study.month_end_dates(market))}


def _fmt(v, d=2, sign=True):
    return "—" if v is None else (f"{v:+.{d}f}" if sign else f"{v:.{d}f}")


def report(results: dict) -> str:
    today = dt.date.today().isoformat()
    L = [f"# Does group strength help? — leaders in leading groups", "",
         f"*Generated {today} by `python -m swing_screener.screens.group_research`; re-run it to refresh.*", "",
         "**Question.** Are stocks in strong peer groups (sub-industry, else industry group, rated RS "
         f"{STRONG}+ on the Sectors page's scale) better buys than the same kind of stock in a weak group (RS below {WEAK})? "
         f"Does being one of the top {TOP} in the group add to that?", "",
         "**Method.** On each month-end of the last five years, using only data up to that day — the month-end stock "
         "snapshot, with group RS rebuilt point in time from prices (it matches the Sectors page exactly on the US and to a "
         "Spearman 0.995 on India) — each set below is formed and its average return to the month-end 1, 3 and 6 months "
         "later measured; *excess* is that minus the average tradable stock's. Paired comparisons take the difference of "
         "two sets' 1-month returns on each month-end where both have at least "
         f"{MIN_EACH} stocks: its mean, t-statistic and the share of months won. 3- and 6-month windows overlap, so their "
         "differences are shown for context without a t-statistic.", ""]
    for m, r in results.items():
        L += [f"## {MARKETS[m].name}", "", "### Every set", "",
              "| Set | Stocks per month-end | Excess 1M | Excess 3M | Excess 6M | Hit rate 6M | Months won 6M |", "|---|---:|---:|---:|---:|---:|---:|"]
        for name, s in r["sets"].items():
            summ = {x["horizon"]: x for x in s.get("summary", [])}
            if not summ:
                L.append(f"| {name} | — | {s.get('error', 'not enough history')} | | | | |")
                continue
            L.append(f"| {name} | {summ['1M']['avg_qualifiers']:.0f} | {_fmt(summ['1M']['excess'])}% | {_fmt(summ.get('3M', {}).get('excess'))}% | "
                     f"{_fmt(summ.get('6M', {}).get('excess'))}% | {summ.get('6M', {}).get('hit_rate', 0) * 100:.0f}% | "
                     f"{summ.get('6M', {}).get('pct_dates_beating', 0) * 100:.0f}% |")
        L += ["", "### Head to head", "",
              "| Comparison | A | B | Months | A − B, 1M | t (1M) | A won (1M) | A − B, 3M | A − B, 6M |", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
        for p in r["pairs"]:
            one, three, six = p.get("1M"), p.get("3M"), p.get("6M")
            if not one:
                L.append(f"| {p['title']} | {p['a']} | {p['b']} | too few months | | | | | |")
                continue
            L.append(f"| {p['title']} | {p['a']} | {p['b']} | {one['n']} | {_fmt(one['mean'])}% | {_fmt(one['t'], 1, False) if one['t'] is not None else '—'} | "
                     f"{one['won'] * 100:.0f}% | {_fmt(three['mean']) if three else '—'}% | {_fmt(six['mean']) if six else '—'}% |")
        L.append("")
    L += ["## How to read it", "",
          "- A t-statistic above about 2 (in absolute value) on the 1-month difference is unlikely to be luck; between 1 and 2 is "
          "suggestive; below 1 is noise. Five years is about 60 months — a modest sample, and one market regime.",
          "- *Hit rate*: share of the set's stocks beating the median tradable stock. *Months won*: share of month-ends the set beat "
          "the average tradable stock.", "",
          "## Caveats", "",
          "- **Survivorship**: stocks delisted since are missing; it flatters every set, the weakest most.",
          "- **Classification look-ahead**: today's industry groups and sub-industries are used for every past date.",
          "- **No costs, equal weight, close to close**: a screen is not a strategy; a strategy adds entries, stops and exits, "
          "judged by its own backtest.",
          "- **Overlap**: 3- and 6-month windows overlap month to month, so those columns are not independent observations.", ""]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", choices=["us", "india", "all"], default="all")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    markets = list(MARKETS) if a.market == "all" else [a.market]
    results = {m: run(m) for m in markets}
    text = report(results)
    REPORT.write_text(text)
    print(text)
    print(f"\nWritten to {REPORT}")


if __name__ == "__main__":
    main()
