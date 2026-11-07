"""Every chart indicator links to the Learn section that explains it, and every link resolves.

The chart's indicators (`CATALOG` in `web/static/studies.js`) and the Learn guides
(`research/learn-*.md`) are written apart, so a new indicator can reach the chart with nothing in
Learn to explain it, and renaming a guide's heading silently breaks the link to it. The link lives
in `studies.js`: `LEARN` maps an indicator to `"<guide>#<section>"`, a trade-setups layer names its
strategy's guide in `learnGuide`. The picker's "Learn" link and the settings dialog's
"Learn about it" open `#/learn/<guide>/<section>`; app.js `showGuideMd` gives each heading the id
`s-<slug>`, slugged as `_slug` below (outline number dropped, so renumbering keeps the links).

Checks:
  1. every CATALOG entry has a LEARN entry, or a `learnGuide` if it is a setups layer;
  2. no LEARN entry names an indicator that is not in CATALOG;
  3. every named guide is a `research/learn-*.md` file;
  4. every named section is a heading (## or ###) of that guide.

Run: `PYTHONPATH=. python3 -m tests.test_study_learn`
"""

import re
import sys
from pathlib import Path

from swing_screener import paths

STUDIES = Path(__file__).resolve().parent.parent / "swing_screener" / "web" / "static" / "studies.js"


def _slug(heading: str) -> str:
    """app.js showGuideMd's slug: outline number dropped, lower-case, runs of anything else -> '-'."""
    t = re.sub(r"^\d+(\.\d+)*\.?\s+", "", heading.strip())
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def _block(js: str, start: str, end: str) -> str:
    a = js.index(start)
    return js[a: js.index(end, a)]


def check() -> list[str]:
    js = STUDIES.read_text()
    cat = _block(js, "const CATALOG = {", "const CATS = ")
    entries = dict.fromkeys(re.findall(r"^    ([a-z_0-9]+): (?:\{|ribbon\(|genericSetups\()", cat, re.M))
    setups = dict(re.findall(r'^    ([a-z_0-9]+): genericSetups\("[a-z_0-9]+", "(learn-[a-z0-9-]+)"', cat, re.M))
    setups.update(re.findall(r'^    ([a-z_0-9]+): \{ setupsFor: "[a-z_0-9]+", learnGuide: "(learn-[a-z0-9-]+)"', cat, re.M))
    learn = dict(re.findall(r'\b([a-z_0-9]+): "([a-z0-9-]+(?:#[a-z0-9-]+)?)"', _block(js, "const LEARN = {", "};")))

    files = {p.stem for p in paths.RESEARCH_DIR.glob("learn-*.md")}
    heads: dict[str, set[str]] = {}

    def sections(guide: str) -> set[str]:
        if guide not in heads:
            text = (paths.RESEARCH_DIR / f"{guide}.md").read_text()
            heads[guide] = {_slug(h) for h in re.findall(r"^#{2,3} (.+)$", text, re.M)}
        return heads[guide]

    problems = []
    for k in entries:
        if k not in learn and k not in setups:
            problems.append(f"chart indicator {k!r} has no Learn section: add it to LEARN in studies.js "
                            f"(and write the section, in the guide of its family, if there is none)")
    for k in learn:
        if k not in entries:
            problems.append(f"LEARN names {k!r}, which is not a chart indicator")
    for k, g in setups.items():
        if g not in files:
            problems.append(f"setups layer {k!r} names guide {g}.md, which does not exist")
    for k, ref in learn.items():
        guide, _, sec = ref.partition("#")
        guide = f"learn-{guide}"
        if guide not in files:
            problems.append(f"{k!r} -> {ref}: no research/{guide}.md")
        elif sec and sec not in sections(guide):
            problems.append(f"{k!r} -> {ref}: {guide}.md has no heading that slugs to {sec!r}")
    if not problems:
        print(f"{len(entries)} chart indicators: {len(learn)} linked to a Learn section, "
              f"{len(setups)} setups layers to their strategy's guide, across "
              f"{len({r.partition('#')[0] for r in learn.values()} | set(setups.values()))} guides")
    return problems


if __name__ == "__main__":
    probs = check()
    print("\n".join(probs) or "OK — every chart indicator links to the Learn section that explains it")
    sys.exit(1 if probs else 0)
