"""Every Learn guide is registered, and every registration has a guide.

The Learn section is assembled from two places that cannot see each other: the
guides are `research/learn-*.md`, and the menu that lists them is three maps in
`web/static/app.js` plus two in `web/static/learn.js`. Nothing at runtime
objects if they disagree — a guide missing from `GUIDE_TOPIC` falls into a
"more" bucket, and a topic missing from `learn.js` throws only when someone
opens it. Both failures are invisible until a reader finds them.

Checks, in the order a new guide usually breaks them:

  1. every `learn-*.md` appears in GUIDE_ORDER, GUIDE_TOPIC and GUIDE_BLURB;
  2. every registered guide has a file behind it;
  3. every topic a guide claims exists in LEARN_TOPICS;
  4. LEARN_TOPICS, and learn.js's FAMILY_LABEL and FAMILIES, hold the same
     topics — the three together drive the sidebar, its labels and its groups;
  5. no topic is empty (an empty sub-menu renders as a dead end);
  6. each guide file opens with an H1, and its blurb is a sentence rather than
     a placeholder.

Run: `PYTHONPATH=. python3 -m tests.test_learn_guides`
"""

import re
import sys
from pathlib import Path

from swing_screener import paths

STATIC = Path(__file__).resolve().parent.parent / "swing_screener" / "web" / "static"
MIN_BLURB = 40          # characters; shorter than this is a placeholder, not a description


def _literal(js: str, name: str, close: str) -> str:
    """The text of `const <name> = ...` up to its closing bracket."""
    start = js.index(f"const {name}")
    return js[start: js.index(close, start) + 1]


def _registries() -> dict:
    app = (STATIC / "app.js").read_text()
    learn = (STATIC / "learn.js").read_text()
    guide = r'"(learn-[a-z0-9-]+)"'
    return {
        "GUIDE_ORDER": re.findall(guide, _literal(app, "GUIDE_ORDER", "]")),
        "GUIDE_TOPIC": dict(re.findall(guide + r'\s*:\s*"([a-z]+)"',
                                       _literal(app, "GUIDE_TOPIC", "}"))),
        "GUIDE_BLURB": dict(re.findall(guide + r'\s*:\s*"((?:[^"\\]|\\.)*)"',
                                       _literal(app, "GUIDE_BLURB", "}"))),
        "LEARN_TOPICS": re.findall(r'"([a-z]+)"', _literal(app, "LEARN_TOPICS", "]")),
        "FAMILY_LABEL": dict(re.findall(r'(\w+):\s*"([^"]+)"',
                                        _literal(learn, "FAMILY_LABEL", "}"))),
        "FAMILIES": dict(re.findall(r'(\w+):\s*\[([^\]]*)\]",?'.replace('",?', ''),
                                    _literal(learn, "FAMILIES", "}"))),
    }


def check() -> list[str]:
    reg = _registries()
    files = {p.stem for p in paths.RESEARCH_DIR.glob("learn-*.md")}
    problems: list[str] = []

    if not files:
        return [f"no learn-*.md found in {paths.RESEARCH_DIR}"]

    # 1 + 2: the file set and each registry agree, both ways
    for name in ("GUIDE_ORDER", "GUIDE_TOPIC", "GUIDE_BLURB"):
        registered = set(reg[name])
        for run in sorted(files - registered):
            problems.append(f"{run}.md is not in {name} — it will not appear in the menu")
        for run in sorted(registered - files):
            problems.append(f"{name} lists {run}, but research/{run}.md does not exist")

    dupes = [g for g in set(reg["GUIDE_ORDER"]) if reg["GUIDE_ORDER"].count(g) > 1]
    problems += [f"{g} appears twice in GUIDE_ORDER" for g in sorted(dupes)]

    # 3 + 4: the topic vocabulary is the same in all three places
    topics = set(reg["LEARN_TOPICS"])
    for run, topic in sorted(reg["GUIDE_TOPIC"].items()):
        if topic not in topics:
            problems.append(f"{run} claims topic {topic!r}, which is not in LEARN_TOPICS")
    for name in ("FAMILY_LABEL", "FAMILIES"):
        missing = topics - set(reg[name])
        extra = set(reg[name]) - topics
        for t in sorted(missing):
            problems.append(f"topic {t!r} is in LEARN_TOPICS but not in learn.js {name}"
                            + (" — opening it throws" if name == "FAMILIES" else ""))
        for t in sorted(extra):
            problems.append(f"learn.js {name} has topic {t!r}, which is not in LEARN_TOPICS")

    # 5: no empty sub-menu — a topic needs guides, drawn patterns, or both
    for topic in reg["LEARN_TOPICS"]:
        guides = [g for g, t in reg["GUIDE_TOPIC"].items() if t == topic]
        groups = [g for g in reg["FAMILIES"].get(topic, "").split(",") if g.strip()]
        if not guides and not groups:
            problems.append(f"topic {topic!r} has no guides and no pattern groups — "
                            f"its sub-menu would be empty")

    # 6: the files themselves are real guides
    for run in sorted(files):
        text = (paths.RESEARCH_DIR / f"{run}.md").read_text()
        if not text.lstrip().startswith("# "):
            problems.append(f"{run}.md does not open with an H1 title")
        blurb = reg["GUIDE_BLURB"].get(run, "")
        if len(blurb) < MIN_BLURB:
            problems.append(f"{run} has a {len(blurb)}-character blurb; the menu card needs "
                            f"at least {MIN_BLURB}")

    if not problems:
        by_topic = {t: sum(1 for x in reg["GUIDE_TOPIC"].values() if x == t)
                    for t in reg["LEARN_TOPICS"]}
        print(f"{len(files)} guides across {len(topics)} topics:")
        for t in reg["LEARN_TOPICS"]:
            label = reg["FAMILY_LABEL"].get(t, t)
            pats = len([g for g in reg["FAMILIES"].get(t, "").split(",") if g.strip()])
            print(f"  {label:<26} {by_topic[t]} guide(s)"
                  + (f", {pats} pattern group(s)" if pats else ""))
    return problems


if __name__ == "__main__":
    probs = check()
    print("\n".join(probs) or "\nOK — every guide is registered and every topic resolves")
    sys.exit(1 if probs else 0)
