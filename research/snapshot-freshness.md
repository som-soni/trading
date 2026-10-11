# Making the latest stock snapshot notice when its inputs move

*2026-10-11. Prompted by a screen that silently returned nothing. **Implemented** the
same day — see "What was built" at the end for what shipped and how it differs.*

The web app's screens filter a stored daily snapshot (`screens/snapshot.py`), built
by the `screens` job. The snapshot is a precomputed row per stock — 54 screenable
fields — and a screen is a list of conditions masked over it.

This asks whether that snapshot needs to exist, concludes that half of it does and
half of it is a cache, and proposes one narrow change: the latest snapshot should
know when the data underneath it has changed, instead of staying wrong until the
next scheduled run.

## The defect that prompted it

The built-in preset **Minervini leaders in Stage 2** (`definitions.presets()`) is the
`stage2` screen plus `sepa_verdict = LEADER`. It returned **0 stocks on both markets**
while six US names — DELL, FTNT, JCI, LNG, NVDA, PAYS — actually qualified.

Nothing was broken. The `fundamental_scores` table gained ~1,580 rows *after* the
snapshot was built, and the snapshot had copied `sepa_verdict` while the table was
still empty, so every one of its 4,985 rows carried `None`. Prices were current (US
0-day lag, India 1-day), so no existing freshness check had anything to complain about.

A screen that computed its fields on request would have shown the six immediately.
That is the actual cost of the snapshot, and it is worth being precise about what it
buys in return.

## What the snapshot is actually for

Measured on the US universe (5,434 symbols, single-threaded, reading stored bars):

| operation | cost |
|---|---|
| load bars + compute all 54 fields | **~48 s** |
| mask a stored snapshot (one screen) | **2.2 ms** |
| check whether the snapshot's inputs are newer | **1.1 ms** |

**For the latest session it is a cache.** 48 s cold, 2.2 ms warm. `web/server.py:_snap`
already memoises it in memory keyed by `(market, date, mtime)`; persisting it to disk
moves the 48 s off the request path and survives a restart. That is a performance
decision, not a correctness one — it could legitimately be computed lazily on first use.

One constraint stops it being computed *per screen* rather than per market:
`rs_rank` is a 1–99 percentile across the whole universe, and `peer_rs` / `peer_rank`
rank a stock inside its industry group. There is no way to answer "is NVDA's RS ≥ 70?"
by computing NVDA. Even a single-screen request has to compute all 5,434 rows, so the
unit of work is the market, not the filter.

**For past sessions it is not a cache — it is a record.** Eleven of the 54 fields cannot
be recomputed for a past date from anything the repo stores:

```
sepa_verdict  sepa_code33  eps_growth_q  sales_growth_q  roe  earnings_days
group_rs  peer_group  peer_rs  peer_rank  peer_count
```

Fundamentals come from filings fetched *now*; the peer-group RS ratings are derived
state that is not versioned. Nothing records what any of them were on 2023-03-31. That
is why `_prune` keeps every month's final session forever and why the screen study
(`screens/study.py`) measures forward returns over month-end snapshots. Delete that
archive and the study cannot be rerun.

Worth noting because it is weaker than expected: survivorship is *not* much of an
argument. Of the 3,754 stocks in the 2021-08-31 snapshot, only 12 are absent from
today's, and all 12 still have stored bars. The price fields of a past date are largely
reconstructible. It is the eleven present-only fields that are not.

## Why this is not an `after=` dependency

The obvious fix — give the `screens` job `after=("fundamental_scores",)` — is a cycle.
The current chain in `jobs/registry.py` is:

```
screens  →  financials  (after=("screens",): the snapshot picks which symbols to fetch)
         →  fundamental_scores  (after=("financials",))
```

and the snapshot *reads* `fundamental_scores`. Declaring the dependency closes the loop.
The one-day-late behaviour is correct and should stay: today's snapshot carries the
scores as they were known when it was built, which is what makes it point-in-time. The
problem is not the ordering, it is that nothing notices when the gap has grown.

## The change

Keep the month-end archive exactly as it is — a job, writing a record that cannot be
regenerated. Change only the latest session, in three steps.

### 1. `snapshot.stale_inputs(market, date) -> list[dict]`

A new function in `screens/snapshot.py` returning the inputs whose last write is newer
than the snapshot file's mtime, empty when the snapshot is current. Every timestamp it
needs already exists:

| input | written by | freshness column |
|---|---|---|
| `fundamental_scores` | `fundamental_scores` job | `computed_at` |
| `quality_scores` | `quality` job | `computed_at` |
| `sector_daily` | `sectors` job | `date` |
| `symbol_industry` | `industries` job | `updated_at` |
| `earnings_cache_<market>.csv` | `earnings` job | `fetched_at` column |

One query plus a `stat()`: **1.1 ms**. Run against today's data it flags
`fundamental_scores` on both markets and stays quiet on the other three — which is
exactly the real defect and no false positives.

The list belongs next to `_add_present`, which is what reads these tables, so the two
cannot drift apart: a new present-only field means a new row in both.

### 2. Detect and enqueue — do not rebuild in the request

A rebuild is 48 s. That does not belong inside a web request, and it must not bypass
the queue (`CLAUDE.md`: the portal only *asks* through `jobs/queue.py`). So:

- `_snap(market)` calls `stale_inputs` for the latest date and attaches the result to
  the response rather than blocking.
- The screens UI shows a line when it is non-empty — *"fundamentals updated since this
  snapshot was built (2026-10-11 15:41); the 11 present-only fields may be out of
  date"* — with a button that enqueues `screens` for that market through
  `jobs/queue.py`'s normal entry point.
- Stale inputs never hide results. Serving slightly old present-only fields with a
  visible flag is better than an empty screen with no explanation, which is what
  happens now.

### 3. Surface it on the Data status page

The Data status page already lists each dataset's freshness. Add the snapshot's own
row: when it was built, and which of its inputs have moved since. That makes this
class of fault visible without having to notice a screen returning zero.

## Open questions

- **Should the flag be per-field?** `stale_inputs` knows that only
  `fundamental_scores` moved, and therefore that exactly `sepa_*`, `eps_growth_q`,
  `sales_growth_q` and `roe` are suspect — `rs_rank` and the price fields are fine.
  Mapping inputs to the fields they feed would let the UI grey out only the affected
  columns. More precise, more to maintain; probably not worth it until a second
  input starts moving often.
- **Auto-enqueue, or ask?** Enqueuing automatically on a stale read is convenient and
  risks a rebuild storm if several tabs are open. A single-flight guard (skip if a
  `screens` job for that market is already queued or running) handles it, and
  `jobs/queue.py` is the right place for that check.
- **India's fundamentals are a separate problem.** Only 8 of 2,352 companies are
  scored there, none `LEADER`, so `minervini_leaders` will stay empty on India no
  matter how fresh the snapshot is. That is a data-coverage bug in the India
  `financials` / `fundamental_scores` path, not a snapshot bug, and wants its own look.

## Cost

Small. One new function, one call in `_snap`, one UI line, one status row; no change to
the snapshot format, the job registry's dependency graph, or any screen's results. The
`screens` job keeps running daily and keeps writing the archive. Nothing here touches
the coded criteria, so no strategy fingerprint moves and no stored signal is invalidated.


## What was built

Shipped as described, with four things that only became clear while writing it.

**Earnings freshness reads a column, not the file.** The first cut used the earnings CSV's
mtime and reported it stale on every build, because the job rewrites the whole file each
run whether or not any row changed. The CSV has a `fetched_at` column; using
`max(fetched_at)` removed the false positive on US and kept the genuine one on India.

**`stale_inputs` refuses to answer for a past snapshot, rather than leaving that to
callers.** Every source is newer than a 2021 month-end file, so the first version called
the whole archive stale. The server happened to guard it; the function now does, which is
the right place — a past snapshot is a record, and nothing about it is out of date. A test
caught this, not a reviewer.

**The status line does not say "up to date" when inputs have moved.** The Data status page
labels every `warn` item "Behind", which read as a contradiction next to "up to date". The
snapshot's text now leads with *covers the latest session, but …* when the date is current
and only the sources moved.

**`PRESENT_INPUTS` is checked against `PRESENT_ONLY`.**
`tests/test_snapshot_freshness.py` fails if a source names a column that is not a
present-only snapshot field, if a present-only field has no source watching it (so a new
field cannot slip in unwatched), if an unreadable table is reported as stale rather than
skipped, if a past snapshot is called stale, or if the check exceeds a 250 ms per-request
budget. Verified against three deliberate breakages.

Measured after the change: 6 ms US, 2 ms India, against a ~48 s rebuild. On the live data
it reports exactly `fundamentals` on US — the actual defect — and `fundamentals` plus
`earnings` on India, with no false positives.

### Files

| file | change |
|---|---|
| `screens/snapshot.py` | `PRESENT_INPUTS`, `_source_changed_at`, `stale_inputs` |
| `web/server.py` | `stale_inputs` on `/api/screens` and `_query`; `POST /api/screens/rebuild` |
| `web/status.py` | `_snapshot_item` — a Data status row for the snapshot |
| `web/static/app.js` | `staleBanner` / `wireStale`, on the overview and a screen's results |
| `web/static/style.css` | `.scr-stale` |
| `tests/test_snapshot_freshness.py` | new |

### Still open

The three questions above are unchanged: per-field flagging is not built (the banner names
the affected fields but the table does not grey them), the rebuild is a button rather than
automatic, and India's fundamentals coverage — 8 of 2,352 companies — is a separate
problem that no amount of snapshot freshness will fix.
