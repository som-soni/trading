"""Print a stock's analysis (the framework's checks on today's stored data), or the framework itself.

    PYTHONPATH=. python3 -m analysis --market us --symbol NVDA
    PYTHONPATH=. python3 -m analysis --framework
"""

import argparse

from . import evidence, framework as fw

MARK = {"good": "✓", "ok": "~", "bad": "✗", "na": "·", "info": "i"}


def _val(v, kind: str) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return {"pct": f"{v:.1%}", "pp": f"{v * 100:+.1f} pts", "pp_raw": f"{v:+.1f} pts", "x": f"{v:.2f}×",
            "days": f"{v:+.0f} days", "pct_raw": f"{v:.1f}%"}.get(kind, f"{v:g}" if isinstance(v, (int, float)) else str(v))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--market", default="us")
    ap.add_argument("--symbol")
    ap.add_argument("--framework", action="store_true", help="print the framework (pillars, checks, questions)")
    a = ap.parse_args()
    if a.framework or not a.symbol:
        c = fw.criteria()
        print(f"Stock analysis framework v{c['version']}\n")
        for p in c["pillars"]:
            print(f"{p['name'].upper()} — {p['question']}")
            for x in p["checks"]:
                print(f"  {x['code']:4} {x['label']}: {x['rule']}")
            for x in p["questions"]:
                print(f"  {x['code']:4} [you] {x['question']}")
            print()
        print(c["rating_rule"])
        return
    ev = evidence.gather(a.market, a.symbol)
    res, kinds = fw.evaluate(ev), fw.check_formats()
    sm = fw.summarise(res)
    print(f"{ev.get('name') or a.symbol} ({a.symbol}) — evidence as of {ev['asof']}, framework v{fw.VERSION}")
    print(f"Evidence score {sm['score']} across {sm['rated']} rated pillars")
    for f in sm["flags"]:
        print(f"  RED FLAG {f['code']} {f['label']}: {f['detail']}")
    labels = {c[0]: c[2] for c in fw.CHECKS_DOC}
    for k, name, _ in fw.PILLARS:
        p = sm["pillars"][k]
        print(f"\n{name}: {p['rating'] or '—'}" + (f" ({p['score']:.0%})" if p["score"] is not None else ""))
        for code, r in res.items():
            if fw.CHECK_PILLAR[code] == k:
                print(f"  {MARK[r['status']]} {code:3} {labels[code]:28} {_val(r['value'], kinds[code]):>16}  {r['detail']}")


if __name__ == "__main__":
    main()
