"""Every filesystem location the project uses, defined once.

Previously each module computed its own `Path(__file__).parent.parent /
"reports"`, which put generated output *inside the code directory* and meant
five copies of the same assumption. Outputs now live at the repository root,
next to the code rather than inside it:

    trading/
      scripts/        code
      data/           inputs (universe lists, caches, overrides)
      reports/        generated output, one directory per run
      logs/           run logs
      research/       written findings

Reports are nested `reports/<market>/<strategy>/<run>/` rather than a single
flat directory, so one run's artefacts (markdown, charts, trades, equity)
sit together and can be found without grepping filenames.
"""

from pathlib import Path

# scripts/swing_screener/paths.py -> scripts/swing_screener -> scripts -> repo root
PACKAGE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PACKAGE_DIR.parent
REPO_ROOT = SCRIPTS_DIR.parent

DATA_DIR = REPO_ROOT / "data"
REPORTS_DIR = REPO_ROOT / "reports"
LOGS_DIR = REPO_ROOT / "logs"
RESEARCH_DIR = REPO_ROOT / "research"

# run history snapshots (the screener's day-to-day diffing, not backtests)
HISTORY_DIR = REPORTS_DIR / "_history"


def slug(text: str) -> str:
    """Filesystem-safe fragment for a run identifier."""
    keep = [c if (c.isalnum() or c in "-_.") else "-" for c in str(text)]
    out = "".join(keep)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "run"


def run_dir(market: str, strategy: str, run: str, create: bool = True) -> Path:
    """`reports/<market>/<strategy>/<run>/` — everything from one run together.

    `run` should describe the configuration (start date, exit policy, ...)
    so two runs of the same strategy don't overwrite each other."""
    # `run` may contain "/" to nest (e.g. "screener/2026-10-03"); slug each
    # segment so the separator survives instead of being flattened to "-"
    parts = [slug(part) for part in str(run).split("/") if part]
    d = REPORTS_DIR.joinpath(slug(market), slug(strategy), *parts)
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_dirs() -> None:
    for d in (DATA_DIR, REPORTS_DIR, LOGS_DIR, RESEARCH_DIR):
        d.mkdir(parents=True, exist_ok=True)
