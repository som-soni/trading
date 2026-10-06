"""Strategy reference documentation, assembled from the code.

The web app's Strategy page is built from this, and so is
tests/test_strategy_docs.py — which fails when a strategy's documentation
no longer matches its code. Nothing here is hand-maintained prose about a
strategy: every rule text comes from the strategy class itself (or, for the
momentum baseline, from `backtesting.baseline.DOC`), and every number is
either a live constant substituted into a `{NAME}` placeholder or a live
config value.

    PYTHONPATH=. python3 -m swing_screener.strategies.docs            # print every page as text
    PYTHONPATH=. python3 -m swing_screener.strategies.docs --check    # list documentation problems
"""

import argparse
import datetime as dt
import inspect
from pathlib import Path

from .. import paths
from ..config import MARKETS
from . import _REGISTRY, LABELS

# What each decision label means. Shared by every Strategy subclass: the
# labels and the downgrade ladder are defined once, in strategies/base.py.
DECISIONS = (
    (LABELS["TRADE_HIGH_CONFIDENCE"], "Every hard gate passes, an entry setup is present, the trade plan passes the strategy's "
                                      "risk and reward checks, and nothing caps confidence."),
    (LABELS["TRADE_ON_TRIGGER"], "A valid plan exists, but enter only if price trades through the entry level (a resting "
                                 "buy-stop), or a watch flag / the market regime capped it to this tier."),
    (LABELS["WATCH_WAIT"], "The trend qualifies but there is no valid entry yet — no setup, the plan fails the reward/risk "
                           "test, or a cap applies. Worth watching, not buying."),
    (LABELS["AVOID"], "A hard gate failed (or the plan failed its risk checks). Not tradeable under this strategy."),
)
REGIME_NOTE = ("When the market regime is risk-off, every decision is downgraded one tier "
               "(HIGH CONFIDENCE → ON TRIGGER → WATCH → AVOID); the reason column then says "
               "'market-regime downgrade applied'.")


def _resolve_param(cls, source: str) -> dict:
    """A param_docs source -> its value per market ({"us": .., "india": ..})."""
    if source.startswith("cfg."):
        out = {}
        for market, cfg in MARKETS.items():
            obj = cfg
            for part in source.split(".")[1:]:
                obj = getattr(obj, part)
            out[market] = obj
        return out
    v = cls.doc_namespace()[source]
    return {m: v for m in MARKETS}


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:,.4g}" if abs(v) < 1e4 else f"{v:,.0f}"
    if isinstance(v, int) and not isinstance(v, bool):
        return f"{v:,}"
    return str(v)


def _source_info(obj) -> dict:
    f = Path(inspect.getsourcefile(obj)).resolve()
    return {"file": str(f.relative_to(paths.REPO_ROOT)),
            "modified": dt.datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="minutes")}


def strategy_doc(key: str) -> dict:
    if key == "momentum_baseline":
        return baseline_doc()
    if key == "quality":
        return quality_doc()
    strat = _REGISTRY[key]
    cls = type(strat)
    r = cls.render_doc
    backtest = f"python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --strategy {key}"
    if cls.backtest_args:
        backtest += " " + cls.backtest_args
    return {
        "key": key, "kind": "screener", "name": cls.name, "description": r(cls.description), "status": r(cls.status),
        "thesis": r(cls.thesis), "how_it_works": [r(s) for s in cls.how_it_works], "caveats": [r(s) for s in cls.caveats],
        "gates": [{"code": c, "text": r(cls.gate_docs.get(c, ""))} for c in cls.gate_codes],
        "watch": [{"code": c, "text": r(cls.watch_docs.get(c, ""))} for c in cls.watch_codes],
        "setups": [{"code": c, "text": r(cls.setup_docs.get(c, ""))} for c in cls.setup_codes],
        "entry_rules": [r(s) for s in cls.entry_rules], "exit_rules": [r(s) for s in cls.exit_rules],
        "params": [{"label": label, "source": src, "meaning": r(meaning),
                    "values": {m: _fmt(v) for m, v in _resolve_param(cls, src).items()}} for label, src, meaning in cls.param_docs],
        "decisions": [{"label": l, "text": t} for l, t in DECISIONS], "regime_note": REGIME_NOTE,
        "min_bars": cls.min_bars,
        "commands": {
            "Screen today": f"python3 -m swing_screener.screening.pipeline --market us --strategy {key}",
            "Explain one stock": f"python3 -m swing_screener.screening.inspect --market us --symbol AAPL --strategy {key}",
            "Backtest (its real exit policy)": backtest,
        },
        "source": _source_info(cls),
    }


def baseline_doc() -> dict:
    from ..backtesting import baseline
    d = baseline.DOC
    params = []
    for a in baseline.build_parser()._actions:
        if not a.option_strings or a.dest in ("help", "market", "start"):
            continue
        default = "off" if a.const is True and a.default is False else ("none" if a.default is None else a.default)
        params.append({"label": a.option_strings[-1], "source": "CLI", "meaning": (a.help or "").replace("%%", "%"),
                       "values": {m: _fmt(default) for m in MARKETS}})
    return {
        "key": d["key"], "kind": "benchmark", "name": d["name"], "description": d["description"], "status": d["status"],
        "thesis": d["thesis"], "how_it_works": list(d["how_it_works"]), "caveats": list(d["caveats"]),
        "gates": [], "watch": [], "setups": [], "entry_rules": [], "exit_rules": [],
        "params": params, "decisions": [], "regime_note": "",
        "commands": {"Backtest": "python3 -m swing_screener.backtesting.baseline --market india --start 2013-01-01 --top-n 20 --cost-bps 25"},
        "source": _source_info(baseline),
    }


def quality_doc() -> dict:
    """The long-term quality tracker (scripts/fundamentals/quality.py): its rules ARE its documentation —
    every test and price rule text is rendered from the module's live constants."""
    from fundamentals import quality as qmod
    c = qmod.criteria()
    params = [{"label": k, "source": "scripts/fundamentals/quality.py", "meaning": "", "values": {m: _fmt(v) for m in MARKETS}}
              for k, v in vars(qmod).items() if k.isupper() and isinstance(v, (int, float)) and not isinstance(v, bool)]
    return {
        "key": c["key"], "kind": "long-term", "name": c["name"], "description": c["description"], "status": c["status"],
        "thesis": c["thesis"], "how_it_works": list(c["how_it_works"]), "caveats": list(c["caveats"]),
        "gates": [{"code": f"{t['points']} pts", "text": t["text"]} for t in c["quality_tests"]], "watch": [], "setups": [],
        "entry_rules": list(c["price_rules"]), "exit_rules": [], "params": params, "decisions": [], "regime_note": "",
        "commands": {
            "Score the most liquid US companies": "python3 -m fundamentals.quality --market us --top 500",
            "Score the most liquid India companies": "python3 -m fundamentals.quality --market india --top 300",
            "Refresh your tracked list": "python3 -m fundamentals.quality --tracked",
        },
        "source": _source_info(qmod),
    }


def keys() -> list[str]:
    return sorted(_REGISTRY) + ["momentum_baseline", "quality"]


def check() -> list[str]:
    """Every way a strategy's documentation can fall out of step with its code."""
    problems = []
    for key, strat in sorted(_REGISTRY.items()):
        cls = type(strat)
        where = f"{key} ({cls.__module__}.{cls.__name__})"
        for attr in ("thesis", "status", "how_it_works", "caveats", "entry_rules", "exit_rules", "param_docs"):
            if not getattr(cls, attr):
                problems.append(f"{where}: `{attr}` is empty")
        for codes_attr, docs_attr in (("gate_codes", "gate_docs"), ("watch_codes", "watch_docs"), ("setup_codes", "setup_docs")):
            codes, docs = set(getattr(cls, codes_attr)), getattr(cls, docs_attr)
            for c in sorted(codes - set(docs)):
                problems.append(f"{where}: {codes_attr} has '{c}' but {docs_attr} does not document it")
            if docs_attr in vars(cls):  # a dict defined on this class must not document codes it lacks
                for c in sorted(set(docs) - codes):
                    problems.append(f"{where}: {docs_attr} documents '{c}', which is not in {codes_attr} (stale?)")
        texts = [cls.thesis, cls.status, cls.description, *cls.how_it_works, *cls.caveats, *cls.entry_rules, *cls.exit_rules,
                 *cls.gate_docs.values(), *cls.watch_docs.values(), *cls.setup_docs.values(), *(p[2] for p in cls.param_docs)]
        for t in texts:
            try:
                cls.render_doc(t)
            except (KeyError, IndexError, ValueError) as exc:
                problems.append(f"{where}: placeholder {exc} does not resolve in: {t[:80]!r}")
        for label, src, _ in cls.param_docs:
            try:
                _resolve_param(cls, src)
            except (KeyError, AttributeError):
                problems.append(f"{where}: param '{label}' points at '{src}', which does not exist")
    try:
        from fundamentals import quality as qmod
        c = qmod.criteria()  # renders every rule text with the live constants: a renamed constant fails here
        for k in ("name", "description", "status", "thesis", "how_it_works", "caveats", "quality_tests", "price_rules"):
            if not c.get(k):
                problems.append(f"quality: criteria()['{k}'] is empty")
        if sum(t["points"] for t in c["quality_tests"]) != 100:
            problems.append("quality: test points must add up to 100")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"quality: cannot render its documentation ({exc!r})")
    try:
        from ..backtesting import baseline
        for k in ("key", "name", "description", "status", "thesis", "how_it_works", "caveats"):
            if not baseline.DOC.get(k):
                problems.append(f"momentum_baseline: DOC['{k}'] is empty")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"momentum_baseline: cannot load DOC ({exc})")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        probs = check()
        print("\n".join(probs) or "OK — every strategy is fully documented")
        raise SystemExit(1 if probs else 0)
    for k in keys():
        d = strategy_doc(k)
        print(f"\n=== {d['name']} ({k}) — {d['status']}\n{d['thesis']}")
        for g in d["gates"]:
            print(f"  {g['code']:6s} {g['text']}")


if __name__ == "__main__":
    main()
