# Archive

Superseded material, kept deliberately rather than deleted. Nothing here is
read by the running code — moving or removing any of it cannot break a run.

| directory | what it is | superseded by | size |
|---|---|---|---|
| `prompts/` | The original LLM screener prompts the Python port was built from | the code in `scripts/swing_screener/strategies/` | 52 KB |
| `cache/` | Parquet price cache, one file per symbol | the `prices` table in Postgres | 219 MB |

---

## `prompts/`

Two prompts — `uptrend-daily-v2-swing-review.md` (US) and
`t-trend-up-india-swing-review.md` (India) — written to be run by an LLM
against chart screenshots. `trend_pullback` is a direct port of them.

**They no longer describe what the code does.** The divergences, all of them
deliberate and evidence-driven:

| prompt says | code does | why |
|---|---|---|
| M1 is a hard gate | watch flag X9 | demoted so a recovering stock isn't excluded outright |
| risk capped at 7%/8% of price | capped at 3.0/3.5 ATR **and** 12%/15% | the percent cap was a volatility filter in disguise and rejected trend leaders |
| any overhead level within 3% blocks entry | the setup's own swing high is excluded | measured: 31 of 31 valid momentum entries were vetoed by the level they were breaking out through |
| screener applied to today's data | point-in-time per bar | selecting on today's row discarded 2,167 of 3,290 candidates over 14 years |

Kept because they record the original intent and the definitions section is
still the reference for several formulas (Wilder smoothing, swing structure,
base-vs-drift), which `core/indicators.py` and `core/swings.py` transcribe.

**Treat the code as the source of truth.** If these are ever revived, they
should be regenerated from the code rather than the other way round.

## `cache/`

8,856 parquet files, one per symbol per market, written by the original
file-based cache. Replaced by Postgres (`prices`), which holds the same data
plus the 16-year backfill — 14.6M US bars and 6.2M India bars — and is
queryable directly with psql or pgAdmin.

This copy is **stale**: it predates the backfill, so most symbols have roughly
2 years of history where Postgres now has 13–16. It is kept only as a fallback
in case a Postgres restore is ever needed, and is gitignored for its size.

To read one directly if ever needed:

```python
import pandas as pd
pd.read_parquet("archive/cache/us/AAPL.parquet")
```

It can be deleted at any time to reclaim 219 MB; nothing depends on it.
