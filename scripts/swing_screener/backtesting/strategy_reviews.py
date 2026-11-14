"""Strategy reviews, in Postgres (`strategy_reviews`): which strategy was reviewed, when, against which of its
versions, under which version of the review skill, and with what verdict.

The `backtest-review` skill (.claude/skills/backtest-review) reviews one strategy at a time and writes the review
as markdown. It records each finished review here, so a review is not lost when it was written in a worktree, and
so `status` can say which strategies are due:

  never reviewed        no review on record;
  strategy changed      the strategy's version moved since its last review (the review describes other rules);
  skill updated         the review predates checks the skill has added since (SKILL.md "Skill version");
  current               reviewed at the current strategy version under the current skill version.

One row is one review of one strategy. `verdicts` holds one entry per market:

  code          clean | bugs | unresolved          (step 3, and accidental fidelity gaps from step 7)
  edge          yes | small | no | not enough evidence     (step 4)
  robust        robust | fragile | not enough evidence     (step 5)
  vs_buy_hold   beats | matches with less risk | does not  (step 6)

A family review (one document covering several strategies, as on 2026-11-12) is recorded once per strategy it
covers, with `scope = 'family'` and the same markdown. A review is analysis only; recording it changes no rule.

    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.strategy_reviews status [--due]
    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.strategy_reviews record --strategy donchian \\
        --file ../research/review-donchian-2026-11-14.md --verdicts '{"us": {...}, "india": {...}}' ...
    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.strategy_reviews show --strategy donchian
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from ..marketdata import db

SKILL_MD = Path(__file__).resolve().parents[3] / ".claude" / "skills" / "backtest-review" / "SKILL.md"

SCHEMA = """
CREATE TABLE IF NOT EXISTS strategy_reviews (
    id SERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    spec_id TEXT,                                -- the strategy's spec id when it was reviewed
    version TEXT,                                -- its version number, for reading
    skill_version INTEGER NOT NULL,              -- SKILL.md "Skill version" the review was made under
    scope TEXT NOT NULL DEFAULT 'strategy',      -- 'strategy' | 'family' (one document, several strategies)
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    run_ids JSONB NOT NULL DEFAULT '{}',         -- {market: run id} the review read
    verdicts JSONB NOT NULL DEFAULT '{}',        -- {market: {code, edge, robust, vs_buy_hold}}
    bugs INTEGER,                                -- bugs found (step 3 + accidental fidelity gaps)
    headline TEXT,                               -- the verdict in a sentence or two
    top_changes JSONB NOT NULL DEFAULT '[]',     -- the top changes proposed, in order
    path TEXT,                                   -- where the markdown was written
    markdown TEXT                                -- the review itself
);
CREATE INDEX IF NOT EXISTS strategy_reviews_strategy ON strategy_reviews (strategy, reviewed_at DESC);
"""

VERDICT_VALUES = {
    "code": ("clean", "bugs", "unresolved"),
    "edge": ("yes", "small", "no", "not enough evidence"),
    "robust": ("robust", "fragile", "not enough evidence"),
    "vs_buy_hold": ("beats", "matches with less risk", "does not"),
}
SCOPES = ("strategy", "family")


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def skill_version(path: Path = SKILL_MD) -> int:
    """The review skill's version, from the "Skill version: N" line of its SKILL.md."""
    m = re.search(r"^Skill version:\s*(\d+)", path.read_text(), re.M)
    if not m:
        raise ValueError(f"{path} has no 'Skill version: N' line")
    return int(m.group(1))


def _check_verdicts(verdicts: dict) -> None:
    from ..config import MARKETS
    for market, v in verdicts.items():
        if market not in MARKETS:
            raise ValueError(f"unknown market {market!r}")
        for k, val in (v or {}).items():
            if k not in VERDICT_VALUES:
                raise ValueError(f"{market}: unknown verdict {k!r} (one of {', '.join(VERDICT_VALUES)})")
            if val is not None and val not in VERDICT_VALUES[k]:
                raise ValueError(f"{market}.{k}: {val!r} is not one of {VERDICT_VALUES[k]}")


def current_versions() -> dict:
    """{strategy key: (spec_id, version)} for every strategy on the Strategies page."""
    from ..strategies import docs
    out = {}
    for k in docs.keys():
        d = docs.strategy_doc(k)
        out[k] = (d.get("spec_id") or "", str(d.get("version") or ""))
    return out


def record(strategy: str, *, markdown: str | None, path: str | None, verdicts: dict | None = None,
           run_ids: dict | None = None, bugs: int | None = None, headline: str | None = None,
           top_changes: list | None = None, skill: int | None = None, scope: str = "strategy",
           spec_id: str | None = None, version: str | None = None, reviewed_at: str | None = None) -> int:
    """Store one review. The strategy's spec id and version default to its current ones; the skill version
    to the current SKILL.md's. Returns the row id."""
    init_schema()
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {SCOPES}")
    verdicts = verdicts or {}
    _check_verdicts(verdicts)
    if spec_id is None or version is None:
        cur_spec, cur_ver = current_versions().get(strategy, (None, None))
        if cur_spec is None:
            raise ValueError(f"{strategy!r} is not a registered strategy")
        spec_id = spec_id if spec_id is not None else cur_spec
        version = version if version is not None else cur_ver
    spec_id = spec_id or None          # "" = not known (an old family review): status then compares versions
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO strategy_reviews (strategy, spec_id, version, skill_version, scope, reviewed_at, run_ids,
                           verdicts, bugs, headline, top_changes, path, markdown)
                       VALUES (%s, %s, %s, %s, %s, COALESCE(%s::timestamptz, now()), %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (strategy, spec_id, version, skill if skill is not None else skill_version(), scope, reviewed_at,
                     json.dumps(run_ids or {}), json.dumps(verdicts), bugs, headline, json.dumps(top_changes or []),
                     path, markdown))
        return cur.fetchone()[0]


def latest() -> dict:
    """{strategy: the newest review's row as a dict}."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT DISTINCT ON (strategy) id, strategy, spec_id, version, skill_version, scope, reviewed_at,
                              verdicts, bugs, headline, path
                       FROM strategy_reviews ORDER BY strategy, reviewed_at DESC, id DESC""")
        cols = ("id", "strategy", "spec_id", "version", "skill_version", "scope", "reviewed_at", "verdicts", "bugs",
                "headline", "path")
        return {r[1]: dict(zip(cols, r)) for r in cur.fetchall()}


def status() -> list[dict]:
    """Every strategy with its review state, the ones most due first: never reviewed, then strategy changed,
    then skill updated (oldest skill version first), then current."""
    skill = skill_version()
    last = latest()
    order = {"never reviewed": 0, "strategy changed": 1, "skill updated": 2, "current": 3}
    rows = []
    for key, (spec, ver) in current_versions().items():
        r = last.get(key)
        if not r:
            state = "never reviewed"
        elif (r["spec_id"] or None) != spec if r["spec_id"] else r["version"] != ver:
            state = "strategy changed"
        elif r["skill_version"] < skill:
            state = "skill updated"
        else:
            state = "current"
        rows.append({"strategy": key, "version": ver, "state": state, "review": r})
    rows.sort(key=lambda x: (order[x["state"]], (x["review"] or {}).get("skill_version") or 0, x["strategy"]))
    return rows


def _verdict_line(verdicts: dict) -> str:
    parts = []
    for m, v in sorted((verdicts or {}).items()):
        parts.append(f"{m}: " + ", ".join(f"{k} {v[k]}" for k in VERDICT_VALUES if v.get(k)))
    return " | ".join(parts)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status", help="every strategy's review state, most due first")
    s.add_argument("--due", action="store_true", help="only the strategies not current")
    r = sub.add_parser("record", help="store a finished review")
    r.add_argument("--strategy", required=True)
    r.add_argument("--file", help="the review's markdown file (stored in full)")
    r.add_argument("--verdicts", default="{}", help='JSON {market: {code, edge, robust, vs_buy_hold}}')
    r.add_argument("--runs", default="{}", help="JSON {market: run id}")
    r.add_argument("--bugs", type=int)
    r.add_argument("--headline")
    r.add_argument("--changes", default="[]", help="JSON list of the top changes, in order")
    r.add_argument("--scope", default="strategy", choices=SCOPES)
    r.add_argument("--skill-version", type=int, help="default: the current SKILL.md's")
    r.add_argument("--spec-id", help="default: the strategy's current spec id (set it for a review of an older version)")
    r.add_argument("--version")
    r.add_argument("--reviewed-at", help="ISO date/time, default now (for recording an earlier review)")
    sh = sub.add_parser("show", help="print a strategy's newest review")
    sh.add_argument("--strategy", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "status":
        print(f"review skill version {skill_version()}")
        for x in status():
            if a.due and x["state"] == "current":
                continue
            rv = x["review"]
            tail = (f"  reviewed {rv['reviewed_at']:%Y-%m-%d} at v{rv['version']} under skill v{rv['skill_version']}"
                    f"{' (family)' if rv['scope'] == 'family' else ''}"
                    + (f"  {_verdict_line(rv['verdicts'])}" if rv["verdicts"] else "")) if rv else ""
            print(f"  {x['state']:<17} {x['strategy']:<22} v{x['version']:<6}{tail}")
    elif a.cmd == "record":
        md = Path(a.file).read_text() if a.file else None
        rid = record(a.strategy, markdown=md, path=a.file, verdicts=json.loads(a.verdicts), run_ids=json.loads(a.runs),
                     bugs=a.bugs, headline=a.headline, top_changes=json.loads(a.changes), skill=a.skill_version,
                     scope=a.scope, spec_id=a.spec_id, version=a.version, reviewed_at=a.reviewed_at)
        print(f"recorded review #{rid} of {a.strategy}")
    elif a.cmd == "show":
        init_schema()
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT reviewed_at, version, skill_version, headline, markdown FROM strategy_reviews "
                        "WHERE strategy=%s ORDER BY reviewed_at DESC, id DESC LIMIT 1", (a.strategy,))
            row = cur.fetchone()
        if not row:
            print(f"no review of {a.strategy} on record")
        else:
            print(f"# {a.strategy}: reviewed {row[0]:%Y-%m-%d} at v{row[1]} under skill v{row[2]}\n{row[3] or ''}\n")
            print(row[4] or "(markdown not stored)")


if __name__ == "__main__":
    main()
