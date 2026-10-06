"""Moved to `swing_screener.analytics.breadth` (analytics read stored data only).

Kept so existing imports and `python -m swing_screener.marketdata.breadth` keep working.
"""
from ..analytics.breadth import *  # noqa: F401,F403
from ..analytics.breadth import main  # noqa: F401

if __name__ == "__main__":
    main()
