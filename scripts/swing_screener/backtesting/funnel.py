"""Where candidate bars stop on the way to becoming trades.

A backtest that reports "2 trades in 16 years" says nothing about WHICH rule
produced that number, and the difference matters: a strategy that never finds a
base is broken in a different way from one that finds hundreds and rejects them
all on reward-to-risk. Working that out by hand from the signal cache is both
slow and easy to get wrong -- `extras["contractions"]` is written before the
VCP-04 gate, so counting `has_setup` rows overstates complete bases by 10x.

So the run counts it as it goes. Every stage records how many reached it, and
every drop records why, taken from the rule that actually refused: the gate code
for a hard gate, the strategy's own failure code for a setup, and the plan's own
sentence for a trade plan ("projects only 0.90R against the 2:1 minimum").

Reasons are normalised (digits -> N) before counting, so one rejection phrased
with a different number each time is one row rather than thousands.
"""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path

# In order. Each stage counts what REACHED it, so every pair of adjacent rows
# differs by exactly the drops recorded against the lower one.
# (key, label, unit). The unit matters: "lost here" is only meaningful between
# two stages counting the same thing, and this funnel narrows from symbols to
# bars to signals. Subtracting a bar count from a symbol count would print a
# confident, meaningless number.
STAGES: tuple[tuple[str, str, str], ...] = (
    ("symbols", "Symbols in the universe", "symbols"),
    ("candidates", "Pass the pre-filter (point in time)", "symbols"),
    ("bars", "Bars evaluated", "bars"),
    ("hard_gates", "Bars passing every hard gate", "bars"),
    ("setup", "Bars with a complete setup", "bars"),
    ("entry", "Setups whose entry trigger fired", "bars"),
    ("plan", "Setups with a valid trade plan", "bars"),
    ("accepted", "Plans the decision rules accept", "bars"),
    ("ranked", "Signals surviving ranking and RS", "bars"),
    ("taken", "Signals taken as trades", "bars"),
)
_LABEL = {k: lbl for k, lbl, _ in STAGES}
_UNIT = {k: u for k, _, u in STAGES}
_ORDER = [k for k, _, _ in STAGES]

# A gate code (TT-03, VCP-06, MV-01, B3, DC-02) is an identifier, not a quantity:
# normalising its digits away would merge "hard gate TT-03" and "hard gate TT-05"
# into one meaningless row, throwing away exactly what the funnel is for. Match
# codes first and keep them; only free-standing numbers become N.
_CODE = r"[A-Za-z]{1,6}-?\d{1,3}\b"
_NUMBER = r"[-+]?\d[\d,]*(?:\.\d+)?"
_TOKEN = re.compile(f"({_CODE})|({_NUMBER})")


def normalise(reason: object) -> str:
    """One rejection, phrased with a different number every time, is one row —
    but a gate code keeps its digits. The placeholder is "#", not "N": donchian's
    hard gates are called N1 and N2, so "N" would read as one of them."""
    text = str(reason or "unspecified").strip()
    return _TOKEN.sub(lambda m: m.group(1) or "#", text) or "unspecified"


class Funnel:
    """Counts per stage, and the reasons for each drop."""

    MAX_NAMED = 25   # beyond this a list is noise, so only the count is shown

    def __init__(self) -> None:
        self.counts: collections.Counter = collections.Counter()
        self.drops: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        self.symbols: list[str] = []   # the names actually scanned, when few enough to name

    # ---- recording
    def reached(self, stage: str, n: int = 1) -> None:
        self.counts[stage] += n

    def dropped(self, stage: str, reason: object, n: int = 1) -> None:
        """Record n items that reached `stage` but go no further, and why."""
        self.drops[stage][normalise(reason)] += n

    def set_count(self, stage: str, n: int) -> None:
        self.counts[stage] = int(n)

    def merge(self, other: "Funnel") -> None:
        """Fold a per-symbol funnel into the run's, so scanning can stay per symbol."""
        self.counts.update(other.counts)
        for stage, reasons in other.drops.items():
            self.drops[stage].update(reasons)

    # ---- reading
    def rows(self) -> list[dict]:
        out = []
        for key in _ORDER:
            if key not in self.counts and not self.drops.get(key):
                continue
            out.append({
                "stage": key,
                "label": _LABEL[key],
                "unit": _UNIT[key],
                "count": int(self.counts.get(key, 0)),
                "drops": [{"reason": r, "count": int(n)}
                          for r, n in self.drops.get(key, collections.Counter()).most_common()],
            })
        # A funnel whose reasons do not add up to its own losses is worse than no
        # funnel: it reads as a complete account while quietly omitting some of
        # the rule that did the work. Say so instead.
        for i, r in enumerate(out):
            nxt = out[i + 1] if i + 1 < len(out) else None
            if nxt is None or nxt["unit"] != r["unit"]:
                continue
            lost = r["count"] - nxt["count"]
            gap = lost - sum(d["count"] for d in r["drops"])
            if lost > 0 and gap > 0:
                r["drops"].append({"reason": "not attributed to a named rule", "count": int(gap)})
        return out

    def to_dict(self) -> dict:
        return {"stages": self.rows(), "symbols": list(self.symbols)}

    def write(self, run_dir: Path) -> Path:
        path = Path(run_dir) / "funnel.json"
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return path

    def render_md(self, max_reasons: int = 6) -> str:
        """The funnel as Markdown, for the run's report."""
        rows = self.rows()
        if not rows:
            return ""
        out = ["### Funnel — what became a trade, and where the rest stopped", ""]
        # Say plainly what this run covered. A result from three symbols and one
        # from three thousand read identically otherwise.
        scanned = self.counts.get("candidates", 0)
        if self.symbols:
            named = ", ".join(self.symbols[:self.MAX_NAMED])
            more = f" (+{len(self.symbols) - self.MAX_NAMED} more)" if len(self.symbols) > self.MAX_NAMED else ""
            out += [f"**Scanned {len(self.symbols)} symbol{'' if len(self.symbols) == 1 else 's'}:** {named}{more}", ""]
        elif scanned:
            out += [f"**Scanned {scanned:,} symbols** (every name passing the point-in-time pre-filter).", ""]
        out += ["| Stage | Reached | Lost here | Why |", "|---|---:|---:|---|"]
        for i, r in enumerate(rows):
            nxt_row = rows[i + 1] if i + 1 < len(rows) else None
            # only subtract across stages counting the same unit
            same_unit = nxt_row is not None and nxt_row["unit"] == r["unit"]
            lost = (r["count"] - nxt_row["count"]) if same_unit and r["count"] >= nxt_row["count"] else None
            why = " · ".join(f"{d['reason']} ({d['count']:,})" for d in r["drops"][:max_reasons])
            if len(r["drops"]) > max_reasons:
                why += f" · +{len(r['drops']) - max_reasons} more"
            out.append(f"| {r['label']} | {r['count']:,} | {'' if lost is None else format(lost, ',')} | {why} |")
        return "\n".join(out) + "\n"


def load(run_dir: Path) -> dict | None:
    path = Path(run_dir) / "funnel.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None
