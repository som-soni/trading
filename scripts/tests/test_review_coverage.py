"""The Sunday review skill names every part of the repo it has to review.

`.claude/skills/sunday-review/SKILL.md` fans the weekly review out to numbered
dimensions, and its "Coverage map" table says which dimension reviews each
package and each rule section of CLAUDE.md. Nothing at runtime notices when a
new package or a new rule lands without a row there: the review simply never
looks at it. This test is what notices.

Checks:

  1. every package under `scripts/` and `scripts/swing_screener/` (a folder
     holding Python files) has a row;
  2. every `## ` section of CLAUDE.md has a row, by its exact heading;
  3. no row names a package or a section that no longer exists;
  4. every row points at dimensions that exist in the skill's Phase 2 list,
     or says `none` with a reason.

Run: `PYTHONPATH=. .venv/bin/python -m tests.test_review_coverage`
"""

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
REPO = SCRIPTS.parent
SKILL = REPO / ".claude" / "skills" / "sunday-review" / "SKILL.md"
CLAUDE_MD = REPO / "CLAUDE.md"


def packages() -> set[str]:
    """Folders under scripts/ and scripts/swing_screener/ that hold Python files, as `rel/path/`."""
    out = set()
    for root in (SCRIPTS, SCRIPTS / "swing_screener"):
        for d in root.iterdir():
            if d.is_dir() and not d.name.startswith((".", "_")) and any(d.rglob("*.py")):
                out.add(d.relative_to(SCRIPTS).as_posix() + "/")
    return out


def sections() -> set[str]:
    return {m.group(1).strip() for m in re.finditer(r"(?m)^## (.+)$", CLAUDE_MD.read_text())}


def coverage_map(text: str) -> dict[str, str]:
    """Area -> dimensions cell, from the table under `## Coverage map`."""
    m = re.search(r"(?ms)^## Coverage map\n(.*?)(?=^## )", text)
    if not m:
        return {}
    rows = {}
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or cells[0] in ("Area", "") or set(cells[0]) <= set("-: "):
            continue
        rows[cells[0].strip("`")] = cells[1]
    return rows


def dimensions(text: str) -> set[int]:
    m = re.search(r"(?ms)^## Phase 2.*?\n(.*?)(?=^## )", text)
    return {int(n) for n in re.findall(r"(?m)^(\d+)\. \*\*", m.group(1))} if m else set()


def main() -> int:
    if not SKILL.exists():
        print(f"FAIL — no skill at {SKILL}")
        return 1
    text = SKILL.read_text()
    rows, dims = coverage_map(text), dimensions(text)
    problems = []
    if not rows:
        problems.append("the skill has no `## Coverage map` table")
    if not dims:
        problems.append("the skill's Phase 2 has no numbered dimensions")
    pk, sec = packages(), sections()
    for p in sorted(pk - rows.keys()):
        problems.append(f"package `{p}` has no row in the coverage map")
    for s in sorted(sec - rows.keys()):
        problems.append(f"CLAUDE.md section \"{s}\" has no row in the coverage map")
    for area in sorted(rows.keys() - pk - sec):
        problems.append(f"row \"{area}\" names no package or CLAUDE.md section that exists today")
    for area, cell in rows.items():
        if cell.lower().startswith("none"):
            if not re.match(r"(?i)none\s*[—–-]\s*\S", cell):
                problems.append(f"row \"{area}\" says none without a reason")
            continue
        nums = [int(n) for n in re.findall(r"\d+", cell)]
        if not nums:
            problems.append(f"row \"{area}\" names no dimension")
        for n in nums:
            if n not in dims:
                problems.append(f"row \"{area}\" points at dimension {n}, which Phase 2 does not have")
    if problems:
        print("FAIL — the Sunday review's coverage map is out of date:")
        for p in problems:
            print("  " + p)
        print(f"Edit the `## Coverage map` table in {SKILL.relative_to(REPO)}.")
        return 1
    print(f"OK — {len(pk)} packages and {len(sec)} CLAUDE.md sections each map to a review dimension "
          f"({len(dims)} dimensions).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
