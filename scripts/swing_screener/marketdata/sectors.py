"""Moved to `swing_screener.analytics.sectors` (analytics read stored data only).

Kept so existing imports and `python -m swing_screener.marketdata.sectors` keep working.
"""
from ..analytics.sectors import *  # noqa: F401,F403
from ..analytics.sectors import main  # noqa: F401

if __name__ == "__main__":
    main()
