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
           (source_path, kind, market, strategy, run_name, title, markdown, summary, signature, generated_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, to_timestamp(%s))
           ON CONFLICT (source_path) DO UPDATE SET
             kind=EXCLUDED.kind, market=EXCLUDED.market, strategy=EXCLUDED.strategy,
             run_name=EXCLUDED.run_name, title=EXCLUDED.title, markdown=EXCLUDED.markdown,
             summary=EXCLUDED.summary, signature=EXCLUDED.signature,
             generated_at=EXCLUDED.generated_at, loaded_at=now()
           RETURNING id""",
        (source, kind, market, strategy, run, _title(markdown, run), markdown,
         json.dumps(_headline(markdown)), sig, files[0].stat().st_mtime),
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
    print(ingest(force=args.force))


if __name__ == "__main__":
    main()
