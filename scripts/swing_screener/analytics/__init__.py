"""Analytics: market-wide measures computed from stored data only (no network).

    breadth   market breadth per day (breadth_daily) + the index/VIX series the Breadth page shows
    sectors   sector / industry-group ranking, rotation and leaders (the Sectors page)

They run after the `prices` job (see `jobs/`), never download prices themselves,
and are safe to re-run.
"""
