"""Load generated reports (reports/**, research/*.md) into Postgres so the web
viewer never has to hunt through the filesystem.

Screening runs are already in Postgres (`universe_history`, written by the
pipeline). This adds the rest: every `report.md` directory — backtests, index
studies, per-day screener reports, the daily review — with its figures,
trades, equity curve and any other CSVs.

    python3 -m swing_screener.web.ingest            # incremental
    python3 -m swing_screener.web.ingest --force    # reload everything

Idempotent: a run is keyed by its source path and re-loaded only when a file
in it changed. Execution of strategies stays offline; this only reads output.
"""

import argparse
import json
import logging
import re
from pathlib import Path

import pandas as pd

from .. import paths
from ..marketdata.db import get_connection, py_value

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS report_runs (
    id SERIAL PRIMARY KEY,
    source_path TEXT NOT NULL UNIQUE,   -- relative to the repo root
    kind VARCHAR(16) NOT NULL,          -- backtest | screener | index | daily | research
    market VARCHAR(16) NOT NULL,        -- us | india | all
    strategy VARCHAR(48) NOT NULL,
    run_name TEXT NOT NULL,
    title TEXT,
    markdown TEXT NOT NULL,
    summary JSONB,
    signature TEXT NOT NULL,            -- mtimes+sizes of the source files
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    generated_at TIMESTAMPTZ            -- report.md modification time: when the run was produced
);
ALTER TABLE report_runs ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ;
ALTER TABLE report_runs ADD COLUMN IF NOT EXISTS spec_id TEXT;   -- "v1.5-75bd22a2": which rule set produced it
-- Archiving hides a run from the Backtests tab's default view without deleting anything: a
-- strategy under active development accumulates runs that are superseded but still worth keeping
-- (minervini has 47 against every other strategy's 4 or fewer). Deliberately NOT in the upsert's
-- DO UPDATE list below, so re-ingesting a report never resurrects an archived run.
ALTER TABLE report_runs ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS report_runs_spec ON report_runs (strategy, spec_id);
-- the backtest stage a run was made in (backtesting/windows.py): optimise, verify or full, read from the
-- run name like spec_id. NULL = a LEGACY run, made before stages existed, on its own mixed window --
-- shown, but never as a verified result.
ALTER TABLE report_runs ADD COLUMN IF NOT EXISTS stage TEXT;
-- what the run changed about the strategy (backtesting/windows.overrides), from the overrides.json the
-- backtest job writes beside the report: {} = the strategy as configured, NULL = not recorded (a run
-- made outside the queue, or before 2026-10-24). A --bt passthrough moves no fingerprint, so without
-- this an experiment shares the spec_id of the real thing and the Strategies page cannot tell them apart.
ALTER TABLE report_runs ADD COLUMN IF NOT EXISTS overrides JSONB;
CREATE TABLE IF NOT EXISTS report_figures (
    run_id INT NOT NULL REFERENCES report_runs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    data BYTEA NOT NULL,
    PRIMARY KEY (run_id, name)
);
CREATE TABLE IF NOT EXISTS report_tables (
    run_id INT NOT NULL REFERENCES report_runs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    columns JSONB NOT NULL,
    rows JSONB NOT NULL,                -- list of row arrays, aligned to columns
    PRIMARY KEY (run_id, name)
);
"""

# The backtester stamps the strategy's spec_id into the run directory name
# (backtesting/backtest.py), which is the only record of WHICH rule set produced a
# report. Lifting it into its own column is what lets the Strategies page group runs
# by version instead of making a reader parse a 70-character directory name.
# Not anchored to the end: a run that found nothing gets a "_NO-SIGNALS" suffix after it.
_SPEC_ID = re.compile(r"_v(\d+(?:\.\d+)*)-([0-9a-f]{8})(?:_|$)")


def spec_id_of(run_name: str) -> str | None:
    m = _SPEC_ID.search(run_name or "")
    return f"v{m.group(1)}-{m.group(2)}" if m else None


_STAGE = re.compile(r"_stage-(optimise|verify|full)(?:-to-(\d{4}-\d{2}-\d{2}))?(?:_|$)")
_START = re.compile(r"^(\d{4}-\d{2}-\d{2})_")


def stage_of(run_name: str) -> dict:
    """{"stage", "start", "end"} for a run, read from the name `paths.run_dir` gave it.

    stage is None for a LEGACY run -- one made before stages, on whatever window it was given -- and
    end is None for a run that went to the latest data. Read from the name, not stored separately,
    so the stage can never disagree with the directory the run lives in.
    """
    m, s = _STAGE.search(run_name or ""), _START.match(run_name or "")
    return {"stage": m.group(1) if m else None, "start": s.group(1) if s else None,
            "end": m.group(2) if m and m.group(2) else None}


_HEADLINE = {
    "total_return": r"Total return",
    "cagr": r"CAGR",
    "max_drawdown": r"Max drawdown",
    "sharpe": r"Sharpe",
    "excess_cagr": r"Excess CAGR",
}


def init_schema() -> None:
    with get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _signature(files: list[Path]) -> str:
    return "|".join(f"{f.name}:{int(f.stat().st_mtime)}:{f.stat().st_size}" for f in sorted(files))


def _title(markdown: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", markdown, re.M)
    return m.group(1).strip() if m else fallback


def _headline(markdown: str) -> dict:
    """Pull the strategy column out of the Headline table, best effort —
    report layouts differ between backtest kinds, so a miss is just empty."""
    out = {}
    for key, label in _HEADLINE.items():
        m = re.search(rf"^\|\s*(?:\*\*)?{label}(?:\*\*)?\s*\|\s*([^|]+?)\s*\|", markdown, re.M)
        if m:
            out[key] = m.group(1).replace("*", "").strip()
    return out


def _csv_payload(path: Path) -> tuple[list, list] | None:
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # unreadable or empty CSV: skip, don't fail the run
        logger.warning("skip %s: %s", path, exc)
        return None
    if df.columns[0].startswith("Unnamed"):  # index column written without a label
        df = df.rename(columns={df.columns[0]: "date"})
    rows = [[py_value(v) for v in r] for r in df.itertuples(index=False, name=None)]
    return [str(c) for c in df.columns], rows


def _classify(rel: Path) -> tuple[str, str, str, str] | None:
    """reports/<market>/<strategy>/<run...>/report.md -> (kind, market, strategy, run)."""
    parts = rel.parent.parts
    if parts and parts[0] == "daily" and len(parts) == 2:
        return "daily", "all", "daily", parts[1]
    if len(parts) >= 3 and parts[0] in ("us", "india"):
        market, strategy, run = parts[0], parts[1], "/".join(parts[2:])
        if strategy == "index_investing":
            kind = "index"
        elif parts[2] == "screener":
            kind = "screener"
        else:
            kind = "backtest"
        return kind, market, strategy, run
    return None


def _overrides(run_dir: Path) -> str | None:
    """The run's overrides.json as stored JSON, or None when the run did not record one."""
    f = run_dir / "overrides.json"
    if not f.exists():
        return None
    try:
        return json.dumps(json.loads(f.read_text()).get("overrides") or {})
    except (ValueError, OSError):
        return None


def _store(cur, source: str, meta: tuple, markdown: str, files: list[Path]) -> None:
    kind, market, strategy, run = meta
    sig = _signature(files)
    cur.execute("SELECT id, signature FROM report_runs WHERE source_path=%s", (source,))
    row = cur.fetchone()
    if row and row[1] == sig:
        return
    # upsert in place rather than delete+insert, so a run keeps its id (and
    # every bookmarked /#/reports/<id> link keeps working) across reloads
    cur.execute(
        """INSERT INTO report_runs
           (source_path, kind, market, strategy, run_name, title, markdown, summary, signature, generated_at, spec_id, stage,
            overrides)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, to_timestamp(%s), %s, %s, %s)
           ON CONFLICT (source_path) DO UPDATE SET
             kind=EXCLUDED.kind, market=EXCLUDED.market, strategy=EXCLUDED.strategy,
             run_name=EXCLUDED.run_name, title=EXCLUDED.title, markdown=EXCLUDED.markdown,
             summary=EXCLUDED.summary, signature=EXCLUDED.signature,
             generated_at=EXCLUDED.generated_at, spec_id=EXCLUDED.spec_id, stage=EXCLUDED.stage,
             overrides=EXCLUDED.overrides, loaded_at=now()
           RETURNING id""",
        (source, kind, market, strategy, run, _title(markdown, run), markdown,
         json.dumps(_headline(markdown)), sig, files[0].stat().st_mtime, spec_id_of(run), stage_of(run)["stage"],
         _overrides(files[0].parent)),
    )
    run_id = cur.fetchone()[0]
    cur.execute("DELETE FROM report_figures WHERE run_id=%s", (run_id,))
    cur.execute("DELETE FROM report_tables WHERE run_id=%s", (run_id,))
    for f in files:
        if f.suffix == ".png":
            cur.execute("INSERT INTO report_figures VALUES (%s,%s,%s)", (run_id, f.name, f.read_bytes()))
        elif f.suffix == ".csv":
            payload = _csv_payload(f)
            if payload:
                cur.execute(
                    "INSERT INTO report_tables VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (run_id, f.stem, json.dumps(payload[0]), json.dumps(payload[1])),
                )
    logger.info("loaded %s (%s)", source, kind)


def ingest(force: bool = False) -> dict:
    init_schema()
    conn = get_connection()
    seen, loaded = set(), 0
    with conn.cursor() as cur:
        if force:
            cur.execute("UPDATE report_runs SET signature=''")
        for md in sorted(paths.REPORTS_DIR.rglob("report.md")):
            rel = md.relative_to(paths.REPORTS_DIR)
            meta = _classify(rel)
            if not meta or "_legacy" in rel.parts or "_experiments" in rel.parts:
                continue
            d = md.parent
            files = [md] + [f for f in d.glob("*.csv")] + [f for f in (d / "figures").glob("*.png")]
            if (d / "overrides.json").exists():
                files.append(d / "overrides.json")   # in the signature, so a later backfill is picked up
            source = str(Path("reports") / rel.parent)
            seen.add(source)
            _store(cur, source, meta, md.read_text(), files)
        for md in sorted(paths.RESEARCH_DIR.glob("*.md")):
            source = str(Path("research") / md.name)
            seen.add(source)
            _store(cur, source, ("research", "all", "research", md.stem), md.read_text(), [md])
        # drop runs whose directory was deleted on disk
        cur.execute("SELECT id, source_path FROM report_runs")
        for rid, src in cur.fetchall():
            if src not in seen:
                cur.execute("DELETE FROM report_runs WHERE id=%s", (rid,))
        after = _count(cur)
    return {"runs": after, "scanned": len(seen)}


def _count(cur) -> int:
    cur.execute("SELECT count(*) FROM report_runs")
    return cur.fetchone()[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true", help="reload every run")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from .. import runlog
    with runlog.track("ingest", label="Load reports into the web viewer") as st:
        res = ingest(force=args.force)
        st.detail = f"{res['runs']} report runs indexed"
    print(res)


if __name__ == "__main__":
    main()


def ingest_after_run(quiet: bool = False) -> None:
    """Load newly written reports into the viewer's database.

    Called at the end of every report-producing command, because the web app
    only ingests at startup: a server left running (especially with
    `--no-ingest`) will never show a run produced after it booted, and the
    report sits on disk looking as though the command failed.

    This NEVER raises. A ten-hour backtest that finished successfully must not
    report failure because Postgres was down or the schema was mid-migration —
    the report is already safely on disk, and `python3 -m
    swing_screener.web.ingest` can always be run by hand afterwards.
    """
    try:
        result = ingest()
        if not quiet:
            print(f"Viewer updated: {result['runs']} runs indexed.")
    except Exception as e:  # noqa: BLE001 - see docstring
        logger.warning(
            "Could not update the viewer database (%s: %s). The report is on "
            "disk; run `python3 -m swing_screener.web.ingest` to index it.",
            type(e).__name__, e,
        )
