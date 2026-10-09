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
from . import _REGISTRY, BEHAVIOURS, LABELS, SELECTION, STYLES

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


def _is_current(cls) -> bool:
    """True when no registered sibling in the same family has a higher
    version. A variant (a sibling experiment, not a successor) is never
    "current" for its family."""
    if cls.variant_of:
        return False

    def vkey(v):
        try:
            return tuple(int(x) for x in str(v).split("."))
        except ValueError:
            return (0,)

    fam = cls.family_name()
    peers = [type(s) for s in _REGISTRY.values()
             if type(s).family_name() == fam and not type(s).variant_of]
    return all(vkey(cls.version) >= vkey(p.version) for p in peers)


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
        "style": cls.style, "style_label": STYLES.get(cls.style, ""),
        "selection": cls.selection,
        "selection_label": SELECTION.get(cls.selection, ""),
        "selection_rank": (list(SELECTION).index(cls.selection)
                           if cls.selection in SELECTION else len(SELECTION)),
        "behaviour": cls.behaviour,
        "behaviour_label": BEHAVIOURS.get(cls.behaviour, ""),
        "behaviour_rank": (list(BEHAVIOURS).index(cls.behaviour)
                           if cls.behaviour in BEHAVIOURS else len(BEHAVIOURS)),
        "style_rank": list(STYLES).index(cls.style) if cls.style in STYLES else len(STYLES),
        "variant_of": ({"key": cls.variant_of, "name": type(_REGISTRY[cls.variant_of]).name}
                       if cls.variant_of in _REGISTRY else None),
        "family": cls.family_name(),
        "version": cls.version,
        "spec_id": cls.spec_id(),
        "is_current": _is_current(cls),
        "changelog": [{"version": v, "date": d, "change": c} for v, d, c in cls.changelog],
        "thesis": r(cls.thesis), "how_it_works": [r(s) for s in cls.how_it_works], "caveats": [r(s) for s in cls.caveats],
        "gates": [{"code": c, "text": r(cls.gate_docs.get(c, "")), "screen": cls.screen_gates.get(c)} for c in cls.gate_codes],
        "screen": _screen_ref(cls),
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


def _screen_ref(cls) -> dict | None:
    """The screen a strategy draws its candidates from, and which of its gates are that screen's criteria."""
    if not cls.screen_key:
        return None
    from ..screens import get_screen
    sc = get_screen(cls.screen_key)
    return {"key": sc.key, "name": sc.name, "description": sc.description,
            "gates": {g: c for g, c in cls.screen_gates.items()}}


def screen_doc(key: str) -> dict:
    """A screen's documentation: criteria rendered from screens/criteria.py's live constants, and the strategies that use it."""
    from ..screens import get_screen
    sc = get_screen(key)
    users = [{"key": k, "name": type(s).name, "gates": dict(type(s).screen_gates)} for k, s in sorted(_REGISTRY.items())
             if type(s).screen_key == key]
    return {"key": sc.key, "kind": "screen", "name": sc.name, "description": sc.description, "thesis": sc.thesis,
            "criteria": sc.docs(), "rank_rs": sc.rank_rs, "used_by": users,
            "source": _source_info(type(sc)) | {"file": "scripts/swing_screener/screens/__init__.py"}}


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
        "selection": "cross_sectional", "selection_label": SELECTION["cross_sectional"],
        "selection_rank": list(SELECTION).index("cross_sectional"),
        "behaviour": "trend_momentum", "behaviour_label": BEHAVIOURS["trend_momentum"],
        "behaviour_rank": list(BEHAVIOURS).index("trend_momentum"),
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
        "selection": "fundamental", "selection_label": SELECTION["fundamental"],
        "selection_rank": list(SELECTION).index("fundamental"),
        "behaviour": "quality_value", "behaviour_label": BEHAVIOURS["quality_value"],
        "behaviour_rank": list(BEHAVIOURS).index("quality_value"),
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
        if cls.style not in STYLES:
            problems.append(f"{where}: style {cls.style!r} is not one of {sorted(STYLES)} — every strategy "
                            "declares its trading-style family (strategies/base.py STYLES)")
        if cls.variant_of:
            if cls.variant_of == key:
                problems.append(f"{where}: variant_of points at itself")
            elif cls.variant_of not in _REGISTRY:
                problems.append(f"{where}: variant_of '{cls.variant_of}' is not a registered strategy")
            else:
                parent = type(_REGISTRY[cls.variant_of])
                if parent.variant_of:
                    problems.append(f"{where}: variant_of '{cls.variant_of}' is itself a variant — variants nest one level only")
                if parent.style != cls.style:
                    problems.append(f"{where}: style '{cls.style}' differs from its parent '{cls.variant_of}' "
                                    f"('{parent.style}') — a variant shows under its parent's style group")
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
        if cls.screen_key:
            from ..screens import SCREENS
            if cls.screen_key not in SCREENS:
                problems.append(f"{where}: screen_key '{cls.screen_key}' is not a screen")
            else:
                codes = {c.code for c in SCREENS[cls.screen_key].criteria}
                for g, c in cls.screen_gates.items():
                    if g not in cls.gate_codes:
                        problems.append(f"{where}: screen_gates maps '{g}', which is not in gate_codes")
                    if c not in codes:
                        problems.append(f"{where}: screen_gates maps '{g}' to '{c}', not a criterion of screen '{cls.screen_key}'")
        else:
            problems.append(f"{where}: no screen_key — every strategy draws its candidates from a screen")
        for label, src, _ in cls.param_docs:
            try:
                _resolve_param(cls, src)
            except (KeyError, AttributeError):
                problems.append(f"{where}: param '{label}' points at '{src}', which does not exist")
    from ..screens import SCREENS
    for key, sc in SCREENS.items():  # every screen's criteria must render (placeholders resolve) and be documented
        try:
            for d in sc.docs():
                if not d["text"].strip():
                    problems.append(f"screen {key}: criterion {d['code']} has no description")
        except (KeyError, IndexError, ValueError) as exc:
            problems.append(f"screen {key}: placeholder {exc} does not resolve")
        if not (sc.name and sc.description and sc.thesis):
            problems.append(f"screen {key}: name, description and thesis are required")
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
    ap.add_argument("--write", action="store_true",
                    help="write versioned specs under research/strategies/")
    a = ap.parse_args()
    if a.write:
        for p in write_specs():
            print(f"  {p.relative_to(paths.REPO_ROOT)}")
        return
    if a.check:
        probs = check()
        print("\n".join(probs) or "OK — every strategy is fully documented")
        raise SystemExit(1 if probs else 0)
    for k in keys():
        d = strategy_doc(k)
        print(f"\n=== {d['name']} ({k}) — {d['status']}\n{d['thesis']}")
        for g in d["gates"]:
            print(f"  {g['code']:6s} {g['text']}")



# --- versioned specs on disk -------------------------------------------------

def spec_markdown(key: str) -> str:
    """One strategy version as a readable document.

    Everything here is generated from the class, so a spec cannot drift from
    the code it describes — which is the whole reason it is worth committing.
    The fingerprint at the top is the same one in the run directory names, so
    a result and the spec that produced it can always be matched up.
    """
    from . import _REGISTRY

    cls = type(_REGISTRY[key])
    d = strategy_doc(key)
    L = [f"# {d['name']}", "",
         f"`{key}` · family **{cls.family_name()}** · **v{cls.version}** · "
         f"fingerprint `{cls.fingerprint()}`", "",
         f"> {d['status']}", "", d["description"], ""]

    if d.get("variant_of"):
        L += [f"*A variant of `{d['variant_of']['key']}` "
              f"({d['variant_of']['name']}).*", ""]
    if d["thesis"]:
        L += ["## Thesis", "", d["thesis"], ""]
    if d["how_it_works"]:
        L += ["## How it works", ""]
        L += [f"{i}. {s}" for i, s in enumerate(d["how_it_works"], 1)] + [""]

    for title, items, cols in (
        ("Hard gates (failing any one means AVOID)", d["gates"], ("code", "text")),
        ("Watch flags (these cap confidence)", d["watch"], ("code", "text")),
        ("Setups", d["setups"], ("code", "text")),
    ):
        if items:
            L += [f"## {title}", "", "| code | meaning |", "|---|---|"]
            L += [f"| `{it[cols[0]]}` | {it[cols[1]]} |" for it in items] + [""]

    for title, items in (("Entry", d["entry_rules"]), ("Exit", d["exit_rules"])):
        if items:
            L += [f"## {title}", ""] + [f"- {s}" for s in items] + [""]

    if d["params"]:
        L += ["## Parameters", "", "| parameter | value | meaning |", "|---|---|---|"]
        for p in d["params"]:
            val = p.get("value")
            if isinstance(val, dict):
                val = ", ".join(f"{m}: {v}" for m, v in val.items())
            L.append(f"| {p.get('label', '')} | `{val}` | {p.get('meaning', '')} |")
        L.append("")

    if d["caveats"]:
        L += ["## Known caveats", ""] + [f"- {c}" for c in d["caveats"]] + [""]

    if cls.changelog:
        L += ["## Changelog", "", "| version | date | change |", "|---|---|---|"]
        L += [f"| {v} | {dt} | {what} |" for v, dt, what in cls.changelog] + [""]

    cmds = d.get("commands") or {}
    if cmds:
        L += ["## Commands", "", "```bash"]
        L += [str(c) for c in cmds.values() if c]
        L += ["```", ""]

    src = d.get("source") or {}
    L += ["---", "",
          f"*Generated from `{src.get('file', '?')}`. Do not edit by hand — "
          f"re-run `python3 -m swing_screener.strategies.docs --write`.*"]
    return "\n".join(L)


def write_specs() -> list:
    """Write every registered strategy's spec under research/strategies/."""
    from . import _REGISTRY

    out_root = paths.RESEARCH_DIR / "strategies"
    written = []
    for key in sorted(_REGISTRY):
        cls = type(_REGISTRY[key])
        d = out_root / cls.family_name()
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{key}-v{cls.version}.md"
        path.write_text(spec_markdown(key) + "\n")
        written.append(path)
    return written

if __name__ == "__main__":
    main()
