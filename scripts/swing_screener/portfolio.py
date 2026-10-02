"""Portfolio-construction rules applied AFTER per-symbol decisions.

Strategy-agnostic by design: these operate on decision rows, not on chart
structure, so every strategy gets the same diversification and
risk-budget treatment.
"""

TRADEABLE_LABELS = ("TRADE - HIGH CONFIDENCE", "TRADE ON TRIGGER")


def apply_sector_filter(rows: list[dict], sector_limit: int = 3) -> list[dict]:
    """Keep at most `sector_limit` tradeable names per sector, ranked by
    setup quality, then R-multiple, then relative strength. Mutates and
    returns `rows`, demoting the excess to WATCH - SECTOR LIMIT.

    Note: ranking intentionally ignores the decision tier, so a TRADE ON
    TRIGGER name can displace a TRADE - HIGH CONFIDENCE one in the same
    sector. That mirrors the written rule ("rank the TRADE and TRADE ON
    TRIGGER names by setup quality, then R-multiple, then RS") but is
    worth revisiting — see the defect list in strategies/__init__.py.
    """
    by_sector: dict[str, list[dict]] = {}
    for row in rows:
        if row.get("decision") in TRADEABLE_LABELS:
            by_sector.setdefault(row.get("sector", "Unknown"), []).append(row)

    for _sector, sector_rows in by_sector.items():
        ranked = sorted(
            sector_rows,
            key=lambda r: (
                -(r.get("setup_quality") or 0),
                -(r.get("target_r") or 0),
                -(r.get("rs_vs_benchmark") or 0),
            ),
        )
        kept = [r["symbol"] for r in ranked[:sector_limit]]
        for row in ranked[sector_limit:]:
            row["decision"] = "WATCH - SECTOR LIMIT"
            row["tradeable"] = False
            row["sector_filter_note"] = (
                f"sector cap ({sector_limit}); stronger names: {', '.join(kept)}"
            )
    return rows
